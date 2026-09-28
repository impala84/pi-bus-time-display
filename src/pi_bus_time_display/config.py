from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    bus_stop_code: str = "83249"
    bus_stop_name: str = "Flamingo Valley · Siglap Rd"
    services: tuple[str, ...] = ()
    walking_minutes: int = 7
    poll_seconds: int = 20
    stale_after_seconds: int = 75
    morning_start: str = "06:00"
    morning_end: str = "10:00"
    sleep_start: str = "23:00"
    sleep_end: str = "06:00"
    timezone: str = "Asia/Singapore"
    roon_display_url: str = ""
    end_action: str = "display"
    simulate: bool = False


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def load_config(path: Path) -> Config:
    data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    allowed = set(Config.__dataclass_fields__)
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"Unknown configuration: {', '.join(sorted(unknown))}")
    if "services" in data:
        data["services"] = tuple(str(item) for item in data["services"])
    config = Config(**data)
    if not (5 <= config.poll_seconds <= 300):
        raise ValueError("poll_seconds must be between 5 and 300")
    if config.end_action not in {"display", "shutdown", "reboot"}:
        raise ValueError("end_action must be display, shutdown or reboot")
    return config
