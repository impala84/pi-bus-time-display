from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import socket
import subprocess
import threading
import time
import urllib.request
import urllib.error
from http.cookies import SimpleCookie
from datetime import datetime, time as wall_time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from .config import Config, load_config, load_env
from .domain import normalise
from .lta import LTAError, fetch, simulated
from . import __version__


class State:
    def __init__(self, config: Config, state_dir: Path | None = None):
        self.config = config
        self.lock = threading.Lock()
        self.data: dict = {"status": "starting", "services": []}
        self.last_success: datetime | None = None
        self.last_roon_playing = 0.0
        self.awake_until = 0.0
        self.awake_view = "bus"
        self.state_dir = state_dir or Path(".state")
        try:
            saved_services = set(json.loads((self.state_dir / "enabled-services.json").read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            saved_services = set(config.services)
        self.enabled_services: set[str] = saved_services.intersection(config.services)
        self.home_data: dict = {"status": "disabled", "entities": []}

    def snapshot(self) -> dict:
        with self.lock:
            result = dict(self.data)
        now = datetime.now(ZoneInfo(self.config.timezone))
        result.update({
            "now": now.isoformat(), "stop_name": self.config.bus_stop_name,
            "stop_code": self.config.bus_stop_code, "walking_minutes": self.config.walking_minutes,
            "window_active": within_window(self.config, now),
            "roon_display_url": self.config.roon_display_url,
            "stale": bool(self.last_success and (now - self.last_success).total_seconds() > self.config.stale_after_seconds),
        })
        if self.config.services:
            result["services"] = [item for item in result.get("services", []) if item.get("service") in self.enabled_services]
        return result

    def controls_snapshot(self) -> dict:
        return {
            "services": [{"name": service, "enabled": service in self.enabled_services} for service in self.config.services],
            "home": self.home_data,
        }

    def save_enabled_services(self) -> None:
        self.state_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.state_dir / "enabled-services.tmp"
        temporary.write_text(json.dumps(sorted(self.enabled_services)), encoding="utf-8")
        temporary.replace(self.state_dir / "enabled-services.json")


def within_window(config: Config, now: datetime) -> bool:
    start = wall_time.fromisoformat(config.morning_start)
    end = wall_time.fromisoformat(config.morning_end)
    return start <= now.timetz().replace(tzinfo=None) < end


def within_sleep_window(config: Config, now: datetime) -> bool:
    current = now.timetz().replace(tzinfo=None)
    start = wall_time.fromisoformat(config.sleep_start)
    end = wall_time.fromisoformat(config.sleep_end)
    return start <= current < end if start < end else current >= start or current < end


def poll(state: State, stop: threading.Event) -> None:
    while not stop.is_set():
        config = state.config
        timezone = ZoneInfo(config.timezone)
        now = datetime.now(timezone)
        try:
            payload = simulated(now, config.services) if config.simulate else fetch(os.getenv("LTA_ACCOUNT_KEY", ""), config.bus_stop_code)
            services = normalise(payload, now, config.services, config.walking_minutes)
            with state.lock:
                state.data = {"status": "ok", "services": services, "updated_at": now.isoformat(), "error": None}
                state.last_success = now
        except LTAError as exc:
            with state.lock:
                state.data = {**state.data, "status": "offline", "error": str(exc)}

        stop.wait(config.poll_seconds)


def home_assistant_request(config: Config, path: str, payload: dict | None = None) -> object:
    base = config.home_assistant_url.rstrip("/")
    token = os.getenv("HOME_ASSISTANT_TOKEN", "")
    if not base or not token:
        raise ValueError("Home Assistant URL or token is missing")
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        base + path, data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=2.5) as response:
        return json.load(response)


def home_assistant_set_value(config: Config, entity_id: str, value: int) -> object:
    domain = entity_id.split(".", 1)[0]
    value = max(0, min(100, int(value)))
    if domain == "fan":
        return home_assistant_request(config, "/api/services/fan/set_percentage", {"entity_id": entity_id, "percentage": value})
    if domain == "light":
        return home_assistant_request(config, "/api/services/light/turn_on", {"entity_id": entity_id, "brightness_pct": value})
    raise ValueError("This device has no adjustable level")


def home_assistant_set_state(config: Config, entity_id: str, enabled: bool) -> object:
    domain = entity_id.split(".", 1)[0]
    if domain not in {"fan", "light", "switch", "input_boolean"}:
        raise ValueError("This entity type cannot be controlled")
    service = "turn_on" if enabled else "turn_off"
    return home_assistant_request(config, f"/api/services/{domain}/{service}", {"entity_id": entity_id})


def home_assistant_poll(state: State, stop: threading.Event) -> None:
    while not stop.is_set():
        config = state.config
        if not config.home_assistant_enabled or not config.home_assistant_entities:
            state.home_data = {"status": "disabled", "entities": []}
            stop.wait(5)
            continue
        try:
            raw = home_assistant_request(config, "/api/states")
            selected = set(config.home_assistant_entities)
            entities = []
            for item in raw if isinstance(raw, list) else []:
                entity_id = str(item.get("entity_id", ""))
                if entity_id not in selected:
                    continue
                domain = entity_id.split(".", 1)[0]
                attributes = item.get("attributes") or {}
                entities.append({
                    "entity_id": entity_id, "domain": domain, "state": item.get("state", "unknown"),
                    "name": attributes.get("friendly_name") or entity_id.split(".", 1)[-1].replace("_", " ").title(),
                    "percentage": attributes.get("percentage"), "brightness": attributes.get("brightness"),
                    "supports_level": bool(
                        (domain == "fan" and (attributes.get("percentage") is not None or attributes.get("percentage_step") is not None))
                        or (domain == "light" and attributes.get("supported_color_modes") not in (None, [], ["onoff"]))
                    ),
                })
            order = {entity_id: index for index, entity_id in enumerate(config.home_assistant_entities)}
            entities.sort(key=lambda item: order.get(item["entity_id"], 99))
            state.home_data = {"status": "ok", "entities": entities, "updated_at": datetime.now(ZoneInfo(config.timezone)).isoformat()}
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
            state.home_data = {"status": "offline", "entities": [], "error": str(exc)}
        stop.wait(3)


def write_config(path: Path, config: Config) -> None:
    services = ", ".join(json.dumps(item) for item in config.services)
    content = "\n".join((
        f"bus_stop_code = {json.dumps(config.bus_stop_code)}",
        f"bus_stop_name = {json.dumps(config.bus_stop_name)}",
        f"services = [{services}]",
        f"walking_minutes = {config.walking_minutes}",
        f"poll_seconds = {config.poll_seconds}",
        f"stale_after_seconds = {config.stale_after_seconds}",
        f"morning_start = {json.dumps(config.morning_start)}",
        f"morning_end = {json.dumps(config.morning_end)}",
        f"sleep_start = {json.dumps(config.sleep_start)}",
        f"sleep_end = {json.dumps(config.sleep_end)}",
        f"timezone = {json.dumps(config.timezone)}",
        f"roon_display_url = {json.dumps(config.roon_display_url)}",
        f"roon_zone_name = {json.dumps(config.roon_zone_name)}",
        f"sleep_when_roon_idle = {str(config.sleep_when_roon_idle).lower()}",
        f"roon_show_controls = {str(config.roon_show_controls).lower()}",
        f"roon_show_clock = {str(config.roon_show_clock).lower()}",
        f"sleep_show_clock = {str(config.sleep_show_clock).lower()}",
        f"auto_switch_to_roon = {str(config.auto_switch_to_roon).lower()}",
        f"roon_idle_return_seconds = {config.roon_idle_return_seconds}",
        f"outside_hours_wake_seconds = {config.outside_hours_wake_seconds}",
        f"home_assistant_enabled = {str(config.home_assistant_enabled).lower()}",
        f"home_assistant_url = {json.dumps(config.home_assistant_url)}",
        "home_assistant_entities = [" + ", ".join(json.dumps(item) for item in config.home_assistant_entities) + "]",
        f"end_action = {json.dumps(config.end_action)}",
        "",
    ))
    temporary = path.with_suffix(".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, 0o640)
    temporary.replace(path)


def update_secret(path: Path, key: str, value: str) -> None:
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                name, current = line.split("=", 1)
                values[name.strip()] = current.strip()
    values[key] = value
    temporary = path.with_suffix(".tmp")
    temporary.write_text("".join(f"{name}={current}\n" for name, current in values.items()), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(path)
    os.environ[key] = value


def read_display_mode(path: Path) -> str:
    try:
        mode = path.read_text(encoding="utf-8").strip()
        return mode if mode in {"auto", "bus", "roon", "home", "sleep"} else "auto"
    except OSError:
        return "auto"


def roon_status() -> dict | None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/api/state", timeout=0.35) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


_CHECK_ROON = object()


def display_target(
    config: Config,
    mode_path: Path,
    roon: dict | None | object = _CHECK_ROON,
    now: datetime | None = None,
) -> str:
    mode = read_display_mode(mode_path)
    if mode == "sleep":
        return "/sleep.html"
    if mode == "home":
        return "/home"
    if mode in {"roon", "auto"} and roon is _CHECK_ROON:
        roon = roon_status()
    if mode == "roon":
        return "http://127.0.0.1:8766/" if roon is not None else "/roon-unavailable.html"
    if mode == "auto":
        now = now or datetime.now(ZoneInfo(config.timezone))
        if within_sleep_window(config, now):
            return "/sleep.html"
        if not within_window(config, now):
            if roon is None:
                return "/roon-unavailable.html"
            if config.sleep_when_roon_idle and isinstance(roon, dict) and roon.get("zone", {}).get("state") != "playing":
                return "/sleep.html"
            return "http://127.0.0.1:8766/"
    return "/"


def automatic_display_target(state: State, mode_path: Path, roon: dict | None, now: datetime | None = None) -> str:
    """Resolve Automatic mode with playback grace and temporary touch wake."""
    mode = read_display_mode(mode_path)
    now = now or datetime.now(ZoneInfo(state.config.timezone))
    monotonic = time.monotonic()
    if mode == "sleep" and monotonic < state.awake_until:
        return "http://127.0.0.1:8766/" if state.awake_view == "roon" and roon is not None else "/"
    if mode != "auto":
        return display_target(state.config, mode_path, roon, now)
    zone_state = ((roon or {}).get("zone") or {}).get("state")
    if zone_state == "playing":
        state.last_roon_playing = monotonic
    playback_recent = bool(
        state.last_roon_playing
        and monotonic - state.last_roon_playing <= state.config.roon_idle_return_seconds
    )
    if state.config.auto_switch_to_roon and (zone_state == "playing" or playback_recent):
        return "http://127.0.0.1:8766/" if roon is not None else "/roon-unavailable.html"
    if monotonic < state.awake_until:
        return "http://127.0.0.1:8766/" if state.awake_view == "roon" and roon is not None else "/"
    if within_sleep_window(state.config, now):
        return "/sleep.html"
    if state.config.auto_switch_to_roon:
        return "/"
    if within_window(state.config, now):
        return "/"
    if state.config.sleep_when_roon_idle:
        return "/sleep.html"
    return "http://127.0.0.1:8766/" if roon is not None else "/roon-unavailable.html"


def command_output(command: list[str]) -> str:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=2, check=False).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def diagnostics_snapshot() -> dict:
    memory: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            name, value = line.split(":", 1)
            memory[name] = int(value.strip().split()[0])
    except (OSError, ValueError, IndexError):
        pass
    total = memory.get("MemTotal", 0)
    available = memory.get("MemAvailable", memory.get("MemFree", 0))
    swap_total = memory.get("SwapTotal", 0)
    swap_free = memory.get("SwapFree", 0)
    groups = {
        "display": {"label": "GTK display + Cage", "rss_kb": 0, "cpu_percent": 0.0, "pids": [], "active": False},
        "api": {"label": "Bus data service", "rss_kb": 0, "cpu_percent": 0.0, "pids": [], "active": False},
        "controller": {"label": "Roon controller", "rss_kb": 0, "cpu_percent": 0.0, "pids": [], "active": False},
        "bridge": {"label": "Roon Bridge", "rss_kb": 0, "cpu_percent": 0.0, "pids": [], "active": False},
    }
    for line in command_output(["ps", "-eo", "pid=,rss=,pcpu=,args="]).splitlines():
        parts = line.strip().split(None, 3)
        if len(parts) != 4:
            continue
        pid, rss, cpu, args = parts
        lowered = args.lower()
        group = None
        if "pi_bus_native.py" in lowered or "/cage" in lowered:
            group = "display"
        elif "roon-controller/server.js" in lowered:
            group = "controller"
        elif "roonbridge" in lowered or "roon bridge" in lowered:
            group = "bridge"
        elif "pi-bus-time-display" in lowered and "native" not in lowered:
            group = "api"
        if group:
            try:
                groups[group]["rss_kb"] += int(rss)
                groups[group]["cpu_percent"] += float(cpu)
                groups[group]["pids"].append(int(pid))
                groups[group]["active"] = True
            except ValueError:
                pass
    groups["controller"]["active"] = command_output(["systemctl", "is-active", "pi-bus-roon-controller.service"]) == "active" or groups["controller"]["active"]
    groups["api"]["active"] = command_output(["systemctl", "is-active", "pi-bus-time-display.service"]) == "active" or groups["api"]["active"]
    groups["display"]["active"] = command_output(["systemctl", "is-active", "pi-bus-native.service"]) == "active" or groups["display"]["active"]
    groups["bridge"]["active"] = any(command_output(["systemctl", "is-active", name]) == "active" for name in ("roonbridge.service", "RoonBridge.service")) or groups["bridge"]["active"]
    try:
        uptime = float(Path("/proc/uptime").read_text(encoding="ascii").split()[0])
    except (OSError, ValueError, IndexError):
        uptime = 0
    try:
        load = list(os.getloadavg())
    except OSError:
        load = [0, 0, 0]
    try:
        temperature = round(int(Path("/sys/class/thermal/thermal_zone0/temp").read_text(encoding="ascii")) / 1000, 1)
    except (OSError, ValueError):
        temperature = None
    throttled = command_output(["vcgencmd", "get_throttled"])
    return {
        "memory": {
            "total_kb": total, "available_kb": available,
            "used_kb": max(0, total - available),
            "used_percent": round((total - available) * 100 / total, 1) if total else 0,
        },
        "swap": {"total_kb": swap_total, "used_kb": max(0, swap_total - swap_free)},
        "load": load, "cpu_count": os.cpu_count() or 1, "uptime_seconds": round(uptime),
        "temperature_c": temperature,
        "throttled": throttled.split("=", 1)[-1] if "=" in throttled else "unknown",
        "processes": list(groups.values()),
    }


def active_wifi_ssid() -> str:
    connections = command_output(["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"])
    profile = next((line.rsplit(":", 1)[0] for line in connections.splitlines() if line.rsplit(":", 1)[-1] in {"802-11-wireless", "wifi"}), "")
    if not profile:
        return ""
    ssid = command_output(["nmcli", "--escape", "no", "-g", "802-11-wireless.ssid", "connection", "show", profile])
    return ssid or profile


def system_snapshot(state_dir: Path) -> dict:
    roon_service = "unknown"
    for name in ("roonbridge.service", "RoonBridge.service"):
        status = command_output(["systemctl", "is-active", name])
        if status and status != "unknown":
            roon_service = status
            break
    active_wifi = active_wifi_ssid()
    try:
        update_status = (state_dir / "system-action-status").read_text(encoding="utf-8").strip()
    except OSError:
        update_status = "Ready"
    try:
        display_rotation = Path("/etc/pi-bus-time-display/display-transform").read_text(encoding="utf-8").strip()
    except OSError:
        display_rotation = "normal"
    try:
        display_profile = Path("/etc/pi-bus-time-display/display-profile").read_text(encoding="utf-8").strip()
    except OSError:
        display_profile = "original"
    try:
        with urllib.request.urlopen("http://127.0.0.1:8766/api/state", timeout=.5) as response:
            controller = json.load(response)
        if controller.get("connected"):
            zone = controller.get("zone") or {}
            roon_controller = f"Connected · {zone.get('name')}" if zone.get("name") else "Connected · no zones"
        else:
            roon_controller = "Waiting for authorisation"
    except (OSError, ValueError, json.JSONDecodeError):
        roon_controller = "Unavailable"
    return {
        "hostname": socket.gethostname(),
        "wifi_ssid": active_wifi,
        "roon_bridge": roon_service,
        "roon_controller": roon_controller,
        "update_status": update_status,
        "display_rotation": display_rotation,
        "display_profile": display_profile,
        "app_version": __version__,
        "diagnostics": diagnostics_snapshot(),
    }


def write_control_request(state_dir: Path, request: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    temporary = state_dir / "system-action-request.tmp"
    target = state_dir / "system-action-request.json"
    temporary.write_text(json.dumps(request), encoding="utf-8")
    os.chmod(temporary, 0o600)
    temporary.replace(target)


def make_handler(state: State, config_path: Path, env_path: Path, mode_path: Path):
    static = Path(__file__).with_name("static")
    sessions: dict[str, float] = {}

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(static), **kwargs)

        def do_GET(self):
            if self.path == "/home":
                self.send_response(302)
                self.send_header("Location", "/home.html")
                self.end_headers()
                return
            if self.path == "/roon":
                self.send_response(302)
                self.send_header("Location", "/roon/")
                self.end_headers()
                return
            if self.path.startswith("/roon/"):
                self.proxy_roon("GET")
                return
            if self.path.startswith("/login.html?"):
                self.path = "/login.html"
            if self.path == "/api/display-target":
                self.send_json(200, json.dumps({"target": automatic_display_target(state, mode_path, roon_status())}).encode())
                return
            if self.path == "/display":
                self.send_response(302)
                self.send_header("Location", automatic_display_target(state, mode_path, roon_status()))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return
            if self.path == "/admin":
                if not self.is_authorised():
                    self.send_response(302)
                    self.send_header("Location", "/login.html")
                    self.end_headers()
                    return
                self.send_response(302)
                self.send_header("Location", "/admin.html")
                self.end_headers()
                return
            if self.path == "/admin.html" and not self.is_authorised():
                self.send_response(302)
                self.send_header("Location", "/login.html")
                self.end_headers()
                return
            if self.path == "/api/admin/config":
                if not self.authorised():
                    return
                config = state.config
                body = json.dumps({
                    "bus_stop_code": config.bus_stop_code, "bus_stop_name": config.bus_stop_name,
                    "services": list(config.services), "walking_minutes": config.walking_minutes,
                    "poll_seconds": config.poll_seconds, "morning_start": config.morning_start,
                    "morning_end": config.morning_end, "sleep_start": config.sleep_start,
                    "sleep_end": config.sleep_end, "roon_display_url": config.roon_display_url,
                    "roon_zone_name": config.roon_zone_name,
                    "sleep_when_roon_idle": config.sleep_when_roon_idle,
                    "roon_show_controls": config.roon_show_controls,
                    "roon_show_clock": config.roon_show_clock,
                    "sleep_show_clock": config.sleep_show_clock,
                    "auto_switch_to_roon": config.auto_switch_to_roon,
                    "roon_idle_return_seconds": config.roon_idle_return_seconds,
                    "outside_hours_wake_seconds": config.outside_hours_wake_seconds,
                    "home_assistant_enabled": config.home_assistant_enabled,
                    "home_assistant_url": config.home_assistant_url,
                    "home_assistant_entities": list(config.home_assistant_entities),
                    "has_home_assistant_token": bool(os.getenv("HOME_ASSISTANT_TOKEN")),
                    "app_version": __version__,
                    "admin_username": os.getenv("ADMIN_USERNAME", "admin"),
                    "admin_auth_enabled": os.getenv("ADMIN_AUTH_ENABLED", "true").lower() != "false",
                    "display_mode": read_display_mode(mode_path),
                    "has_lta_key": bool(os.getenv("LTA_ACCOUNT_KEY")),
                }).encode()
                self.send_json(200, body)
                return
            if self.path == "/api/admin/system":
                if not self.authorised():
                    return
                body = json.dumps(system_snapshot(mode_path.parent)).encode()
                self.send_json(200, body)
                return
            if self.path == "/api/status":
                body = json.dumps(state.snapshot()).encode()
                self.send_json(200, body)
                return
            if self.path == "/api/home/status":
                self.send_json(200, json.dumps(state.home_data).encode())
                return
            if self.path == "/api/device/controls":
                if self.client_address[0] not in {"127.0.0.1", "::1"}:
                    self.send_json(403, b'{"error":"Touchscreen only"}')
                    return
                self.send_json(200, json.dumps(state.controls_snapshot()).encode())
                return
            super().do_GET()

        def do_POST(self):
            if self.path.startswith("/roon/"):
                self.proxy_roon("POST")
                return
            if self.path == "/login":
                length = min(int(self.headers.get("Content-Length", "0")), 4096)
                form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
                username = form.get("username", [""])[0]
                supplied = form.get("password", [""])[0]
                expected = os.getenv("ADMIN_PASSWORD", "")
                expected_username = os.getenv("ADMIN_USERNAME", "admin")
                if hmac.compare_digest(username, expected_username) and expected and hmac.compare_digest(supplied, expected):
                    token = secrets.token_urlsafe(32)
                    sessions[token] = time.time() + 30 * 24 * 60 * 60
                    self.send_response(302)
                    self.send_header("Location", "/admin")
                    self.send_header("Set-Cookie", f"pi_bus_session={token}; Max-Age=2592000; Path=/; HttpOnly; SameSite=Strict")
                    self.end_headers()
                else:
                    self.send_response(302)
                    self.send_header("Location", "/login.html?error=1")
                    self.end_headers()
                return
            if self.path == "/api/device/update":
                if self.client_address[0] not in {"127.0.0.1", "::1"}:
                    self.send_json(403, b'{"error":"Touchscreen only"}')
                    return
                write_control_request(mode_path.parent, {"action": "update"})
                self.send_json(202, b'{"ok":true}')
                return
            if self.path == "/api/device/screen-power":
                if self.client_address[0] not in {"127.0.0.1", "::1"}:
                    self.send_json(403, b'{"error":"Touchscreen only"}')
                    return
                length = min(int(self.headers.get("Content-Length", "0")), 4096)
                data = json.loads(self.rfile.read(length) or b"{}")
                write_control_request(mode_path.parent, {"action": "display_on" if data.get("powered") else "display_off"})
                self.send_json(202, b'{"ok":true}')
                return
            if self.path == "/api/device/wake":
                if self.client_address[0] not in {"127.0.0.1", "::1"}:
                    self.send_json(403, b'{"error":"Touchscreen only"}')
                    return
                length = min(int(self.headers.get("Content-Length", "0")), 4096)
                data = json.loads(self.rfile.read(length) or b"{}")
                state.awake_view = "roon" if data.get("view") == "roon" else "bus"
                state.awake_until = time.monotonic() + state.config.outside_hours_wake_seconds
                self.send_json(200, json.dumps({"ok": True, "awake_seconds": state.config.outside_hours_wake_seconds}).encode())
                return
            if self.path in {"/api/device/service-visibility", "/api/device/roon-bridge", "/api/device/home-toggle", "/api/device/home-state", "/api/device/home-value"}:
                if self.client_address[0] not in {"127.0.0.1", "::1"}:
                    self.send_json(403, b'{"error":"Touchscreen only"}')
                    return
                length = min(int(self.headers.get("Content-Length", "0")), 4096)
                data = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/api/device/service-visibility":
                    service = str(data.get("service", ""))
                    if service not in state.config.services:
                        self.send_json(400, b'{"error":"Unknown bus service"}')
                        return
                    if data.get("enabled"): state.enabled_services.add(service)
                    else: state.enabled_services.discard(service)
                    state.save_enabled_services()
                elif self.path == "/api/device/roon-bridge":
                    write_control_request(mode_path.parent, {"action": "roon_start" if data.get("enabled") else "roon_stop"})
                else:
                    entity_id = str(data.get("entity_id", ""))
                    if entity_id not in state.config.home_assistant_entities:
                        self.send_json(400, b'{"error":"Entity is not available on this display"}')
                        return
                    domain = entity_id.split(".", 1)[0]
                    if domain not in {"fan", "light", "switch", "input_boolean"}:
                        self.send_json(400, b'{"error":"This entity type cannot be toggled"}')
                        return
                    try:
                        if self.path == "/api/device/home-value":
                            home_assistant_set_value(state.config, entity_id, int(data.get("value", 0)))
                        elif self.path == "/api/device/home-state":
                            home_assistant_set_state(state.config, entity_id, bool(data.get("enabled")))
                        else:
                            home_assistant_request(state.config, f"/api/services/{domain}/toggle", {"entity_id": entity_id})
                    except (OSError, ValueError, urllib.error.URLError) as exc:
                        self.send_json(502, json.dumps({"error": str(exc)}).encode())
                        return
                self.send_json(200, b'{"ok":true}')
                return
            if self.path in {"/api/home/toggle", "/api/home/state", "/api/home/value"}:
                if not self.authorised():
                    return
                try:
                    length = min(int(self.headers.get("Content-Length", "0")), 4096)
                    data = json.loads(self.rfile.read(length) or b"{}")
                    entity_id = str(data.get("entity_id", ""))
                    if entity_id not in state.config.home_assistant_entities:
                        raise ValueError("Entity is not available on this dashboard")
                    domain = entity_id.split(".", 1)[0]
                    if self.path == "/api/home/value":
                        home_assistant_set_value(state.config, entity_id, int(data.get("value", 0)))
                    elif self.path == "/api/home/state":
                        home_assistant_set_state(state.config, entity_id, bool(data.get("enabled")))
                    else:
                        home_assistant_request(state.config, f"/api/services/{domain}/toggle", {"entity_id": entity_id})
                    self.send_json(200, b'{"ok":true}')
                except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
                    self.send_json(400, json.dumps({"error": str(exc)}).encode())
                return
            if self.path not in {"/api/admin/config", "/api/admin/display-mode", "/api/admin/system-action", "/api/admin/password"}:
                self.send_error(404)
                return
            if not self.authorised():
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 16_384:
                    raise ValueError("Request is too large")
                data = json.loads(self.rfile.read(length))
                if self.path == "/api/admin/password":
                    username = str(data.get("username", "")).strip()
                    password = str(data.get("password", ""))
                    enabled = bool(data.get("enabled", True))
                    if not (3 <= len(username) <= 32) or not all(character.isalnum() or character in "-_" for character in username):
                        raise ValueError("Username must be 3–32 letters, numbers, hyphens or underscores")
                    if password and len(password) < 10:
                        raise ValueError("Password must contain at least 10 characters")
                    if enabled and not password and not os.getenv("ADMIN_PASSWORD", ""):
                        raise ValueError("Set a password before enabling web sign-in")
                    update_secret(env_path, "ADMIN_USERNAME", username)
                    if password:
                        update_secret(env_path, "ADMIN_PASSWORD", password)
                    update_secret(env_path, "ADMIN_AUTH_ENABLED", "true" if enabled else "false")
                    sessions.clear()
                    body = b'{"ok":true}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Cache-Control", "no-store")
                    self.send_header("Set-Cookie", "pi_bus_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if self.path == "/api/admin/system-action":
                    action = str(data.get("action", ""))
                    allowed = {"update", "roon_start", "roon_stop", "roon_restart", "set_hostname", "set_wifi", "set_rotation", "set_display"}
                    if action not in allowed:
                        raise ValueError("Unknown system action")
                    request = {"action": action}
                    if action == "set_hostname":
                        request["hostname"] = str(data.get("hostname", "")).strip()
                    if action == "set_wifi":
                        request["ssid"] = str(data.get("ssid", "")).strip()
                        request["password"] = str(data.get("password", ""))
                    if action == "set_rotation":
                        request["transform"] = "180" if data.get("rotated") else "normal"
                    if action == "set_display":
                        profile = str(data.get("profile", ""))
                        transform = str(data.get("transform", ""))
                        if profile not in {"original", "touch2-5-7", "touch2-10"}:
                            raise ValueError("Unknown display profile")
                        if transform not in {"normal", "90", "180", "270"}:
                            raise ValueError("Unknown display orientation")
                        request.update({"profile": profile, "transform": transform})
                    write_control_request(mode_path.parent, request)
                    self.send_json(202, json.dumps({"ok": True, "status": "queued"}).encode())
                    return
                if self.path == "/api/admin/display-mode":
                    mode = str(data.get("mode", ""))
                    if mode not in {"auto", "bus", "roon", "home", "sleep"}:
                        raise ValueError("Display mode must be auto, bus, roon, home or sleep")
                    mode_path.parent.mkdir(parents=True, exist_ok=True)
                    mode_path.write_text(mode + "\n", encoding="utf-8")
                    self.send_json(200, json.dumps({"ok": True, "display_mode": mode}).encode())
                    return
                current = state.config
                requested_home_entities = tuple(item.strip() for item in str(data.get("home_assistant_entities", "")).split(",") if item.strip())
                if len(requested_home_entities) > 8:
                    raise ValueError("Choose no more than eight Home Assistant entities")
                unsupported = [item for item in requested_home_entities if item.split(".", 1)[0] not in {"fan", "light", "switch", "input_boolean"}]
                if unsupported:
                    raise ValueError("Unsupported Home Assistant entity: " + unsupported[0])
                home_url = str(data.get("home_assistant_url", "")).strip()
                if home_url and not home_url.startswith(("http://", "https://")):
                    raise ValueError("Home Assistant address must start with http:// or https://")
                candidate = Config(
                    bus_stop_code=str(data["bus_stop_code"]).strip(),
                    bus_stop_name=str(data["bus_stop_name"]).strip(),
                    services=tuple(item.strip() for item in str(data["services"]).split(",") if item.strip()),
                    walking_minutes=int(data["walking_minutes"]), poll_seconds=int(data["poll_seconds"]),
                    stale_after_seconds=current.stale_after_seconds,
                    morning_start=str(data["morning_start"]), morning_end=str(data["morning_end"]),
                    sleep_start=str(data["sleep_start"]), sleep_end=str(data["sleep_end"]),
                    timezone=current.timezone, roon_display_url=current.roon_display_url,
                    roon_zone_name=str(data.get("roon_zone_name", "")).strip(),
                    sleep_when_roon_idle=bool(data.get("sleep_when_roon_idle", False)),
                    roon_show_controls=bool(data.get("roon_show_controls", True)),
                    roon_show_clock=bool(data.get("roon_show_clock", True)),
                    sleep_show_clock=bool(data.get("sleep_show_clock", False)),
                    auto_switch_to_roon=bool(data.get("auto_switch_to_roon", True)),
                    roon_idle_return_seconds=int(data.get("roon_idle_return_seconds", 300)),
                    outside_hours_wake_seconds=int(data.get("outside_hours_wake_seconds", 600)),
                    home_assistant_enabled=bool(data.get("home_assistant_enabled", False)),
                    home_assistant_url=home_url,
                    home_assistant_entities=requested_home_entities,
                    end_action="display", simulate=current.simulate,
                )
                if not candidate.bus_stop_code.isdigit() or len(candidate.bus_stop_code) != 5:
                    raise ValueError("Bus stop code must be five digits")
                if candidate.walking_minutes < 0 or candidate.walking_minutes > 60:
                    raise ValueError("Walking time must be between 0 and 60 minutes")
                if not (5 <= candidate.poll_seconds <= 300):
                    raise ValueError("Polling must be between 5 and 300 seconds")
                if not (0 <= candidate.roon_idle_return_seconds <= 7200):
                    raise ValueError("Roon return delay must be between 0 and 7200 seconds")
                if not (30 <= candidate.outside_hours_wake_seconds <= 7200):
                    raise ValueError("Wake timeout must be between 30 and 7200 seconds")
                wall_time.fromisoformat(candidate.morning_start)
                wall_time.fromisoformat(candidate.morning_end)
                wall_time.fromisoformat(candidate.sleep_start)
                wall_time.fromisoformat(candidate.sleep_end)
                write_config(config_path, candidate)
                account_key = str(data.get("lta_account_key", "")).strip()
                if account_key:
                    update_secret(env_path, "LTA_ACCOUNT_KEY", account_key)
                home_token = str(data.get("home_assistant_token", "")).strip()
                if home_token:
                    update_secret(env_path, "HOME_ASSISTANT_TOKEN", home_token)
                state.enabled_services.intersection_update(candidate.services)
                state.enabled_services.update(service for service in candidate.services if service not in current.services)
                state.save_enabled_services()
                state.config = candidate
                self.send_json(200, json.dumps({"ok": True}).encode())
            except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
                self.send_json(400, json.dumps({"error": str(exc)}).encode())

        def is_authorised(self) -> bool:
            if self.client_address[0] in {"127.0.0.1", "::1"}:
                return True
            if os.getenv("ADMIN_AUTH_ENABLED", "true").lower() == "false":
                return True
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            token = cookie.get("pi_bus_session")
            if token and sessions.get(token.value, 0) > time.time():
                return True
            return False

        def proxy_roon(self, method: str) -> None:
            upstream_path = self.path[len("/roon"):] or "/"
            body = None
            if method == "POST":
                length = min(int(self.headers.get("Content-Length", "0")), 1_048_576)
                body = self.rfile.read(length)
            request = urllib.request.Request(
                "http://127.0.0.1:8766" + upstream_path,
                data=body,
                headers={"Content-Type": self.headers.get("Content-Type", "application/octet-stream")},
                method=method,
            )
            response_started = False
            try:
                with urllib.request.urlopen(request, timeout=35) as response:
                    self.send_response(response.status)
                    for name in ("Content-Type", "Cache-Control"):
                        value = response.headers.get(name)
                        if value:
                            self.send_header(name, value)
                    self.end_headers()
                    response_started = True
                    while chunk := response.read(64 * 1024):
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except urllib.error.HTTPError as exc:
                self.send_json(exc.code, exc.read())
            except (OSError, urllib.error.URLError):
                # Event streams reconnect normally and clients can close a page at any time.
                if not response_started:
                    self.send_json(502, b'{"error":"Roon controller is unavailable"}')

        def authorised(self) -> bool:
            if self.is_authorised():
                return True
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            return False

        def send_json(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--env", type=Path, default=Path(".env"))
    parser.add_argument("--simulate", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--state-dir", type=Path, default=Path(".state"))
    args = parser.parse_args()
    load_env(args.env)
    config = load_config(args.config)
    if args.simulate:
        config = Config(**{**config.__dict__, "simulate": True})
    state = State(config, args.state_dir)
    stop = threading.Event()
    threading.Thread(target=poll, args=(state, stop), daemon=True).start()
    threading.Thread(target=home_assistant_poll, args=(state, stop), daemon=True).start()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state, args.config, args.env, args.state_dir / "display-mode"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
