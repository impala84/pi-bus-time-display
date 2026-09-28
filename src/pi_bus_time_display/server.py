from __future__ import annotations

import argparse
import hmac
import json
import os
import secrets
import threading
import time
from http.cookies import SimpleCookie
from datetime import datetime, time as wall_time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

from .config import Config, load_config, load_env
from .domain import normalise
from .lta import LTAError, fetch, simulated


class State:
    def __init__(self, config: Config):
        self.config = config
        self.lock = threading.Lock()
        self.data: dict = {"status": "starting", "services": []}
        self.last_success: datetime | None = None

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
        return result


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
        return mode if mode in {"auto", "bus", "roon", "sleep"} else "auto"
    except OSError:
        return "auto"


def display_target(config: Config, mode_path: Path) -> str:
    mode = read_display_mode(mode_path)
    if mode == "sleep":
        return "/sleep.html"
    if mode == "roon":
        return "http://127.0.0.1:8766/"
    if mode == "auto":
        now = datetime.now(ZoneInfo(config.timezone))
        if within_sleep_window(config, now):
            return "/sleep.html"
        if not within_window(config, now):
            return "http://127.0.0.1:8766/"
    return "/"


def make_handler(state: State, config_path: Path, env_path: Path, mode_path: Path):
    static = Path(__file__).with_name("static")
    sessions: dict[str, float] = {}

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(static), **kwargs)

        def do_GET(self):
            if self.path.startswith("/login.html?"):
                self.path = "/login.html"
            if self.path == "/api/display-target":
                self.send_json(200, json.dumps({"target": display_target(state.config, mode_path)}).encode())
                return
            if self.path == "/display":
                self.send_response(302)
                self.send_header("Location", display_target(state.config, mode_path))
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
                    "display_mode": read_display_mode(mode_path),
                    "has_lta_key": bool(os.getenv("LTA_ACCOUNT_KEY")),
                }).encode()
                self.send_json(200, body)
                return
            if self.path == "/api/status":
                body = json.dumps(state.snapshot()).encode()
                self.send_json(200, body)
                return
            super().do_GET()

        def do_POST(self):
            if self.path == "/login":
                length = min(int(self.headers.get("Content-Length", "0")), 4096)
                form = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
                username = form.get("username", [""])[0]
                supplied = form.get("password", [""])[0]
                expected = os.getenv("ADMIN_PASSWORD", "")
                if username == "admin" and expected and hmac.compare_digest(supplied, expected):
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
            if self.path not in {"/api/admin/config", "/api/admin/display-mode"}:
                self.send_error(404)
                return
            if not self.authorised():
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 16_384:
                    raise ValueError("Request is too large")
                data = json.loads(self.rfile.read(length))
                if self.path == "/api/admin/display-mode":
                    mode = str(data.get("mode", ""))
                    if mode not in {"auto", "bus", "roon", "sleep"}:
                        raise ValueError("Display mode must be auto, bus, roon or sleep")
                    mode_path.parent.mkdir(parents=True, exist_ok=True)
                    mode_path.write_text(mode + "\n", encoding="utf-8")
                    self.send_json(200, json.dumps({"ok": True, "display_mode": mode}).encode())
                    return
                current = state.config
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
                    end_action="display", simulate=current.simulate,
                )
                if not candidate.bus_stop_code.isdigit() or len(candidate.bus_stop_code) != 5:
                    raise ValueError("Bus stop code must be five digits")
                if candidate.walking_minutes < 0 or candidate.walking_minutes > 60:
                    raise ValueError("Walking time must be between 0 and 60 minutes")
                if not (5 <= candidate.poll_seconds <= 300):
                    raise ValueError("Polling must be between 5 and 300 seconds")
                wall_time.fromisoformat(candidate.morning_start)
                wall_time.fromisoformat(candidate.morning_end)
                wall_time.fromisoformat(candidate.sleep_start)
                wall_time.fromisoformat(candidate.sleep_end)
                write_config(config_path, candidate)
                account_key = str(data.get("lta_account_key", "")).strip()
                if account_key:
                    update_secret(env_path, "LTA_ACCOUNT_KEY", account_key)
                state.config = candidate
                self.send_json(200, json.dumps({"ok": True}).encode())
            except (KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
                self.send_json(400, json.dumps({"error": str(exc)}).encode())

        def is_authorised(self) -> bool:
            if self.client_address[0] in {"127.0.0.1", "::1"}:
                return True
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            token = cookie.get("pi_bus_session")
            if token and sessions.get(token.value, 0) > time.time():
                return True
            return False

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
    state = State(config)
    stop = threading.Event()
    threading.Thread(target=poll, args=(state, stop), daemon=True).start()
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
