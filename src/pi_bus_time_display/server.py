from __future__ import annotations

import argparse
import json
import os
import threading
from datetime import datetime, time as wall_time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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
            "stale": bool(self.last_success and (now - self.last_success).total_seconds() > self.config.stale_after_seconds),
        })
        return result


def within_window(config: Config, now: datetime) -> bool:
    start = wall_time.fromisoformat(config.morning_start)
    end = wall_time.fromisoformat(config.morning_end)
    return start <= now.timetz().replace(tzinfo=None) < end


def poll(state: State, stop: threading.Event) -> None:
    config = state.config
    timezone = ZoneInfo(config.timezone)
    while not stop.is_set():
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


def make_handler(state: State):
    static = Path(__file__).with_name("static")

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(static), **kwargs)

        def do_GET(self):
            if self.path == "/api/status":
                body = json.dumps(state.snapshot()).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            super().do_GET()

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
    args = parser.parse_args()
    load_env(args.env)
    config = load_config(args.config)
    if args.simulate:
        config = Config(**{**config.__dict__, "simulate": True})
    state = State(config)
    stop = threading.Event()
    threading.Thread(target=poll, args=(state, stop), daemon=True).start()
    server = ThreadingHTTPServer((args.host, args.port), make_handler(state))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()


if __name__ == "__main__":
    main()
