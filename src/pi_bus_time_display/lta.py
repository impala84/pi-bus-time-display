from __future__ import annotations

import json
from datetime import datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = "https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival"


class LTAError(RuntimeError):
    pass


def fetch(account_key: str, stop: str, timeout: float = 10) -> dict:
    if not account_key:
        raise LTAError("LTA_ACCOUNT_KEY is not configured")
    url = f"{ENDPOINT}?{urlencode({'BusStopCode': stop})}"
    request = Request(url, headers={"AccountKey": account_key, "accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise LTAError(f"LTA request failed: {exc}") from exc


def simulated(now: datetime, services: tuple[str, ...]) -> dict:
    numbers = services or ("40", "42", "401")
    if now.weekday() < 5:
        numbers = tuple(number for number in numbers if number != "401")
    offsets = ((5, 14, 27), (9, 18, 31), (12, 23, 38))
    loads = ("SEA", "SDA", "LSD")
    result = []
    for index, number in enumerate(numbers):
        arrivals = {}
        for bus_index, key in enumerate(("NextBus", "NextBus2", "NextBus3")):
            arrival = now + timedelta(minutes=offsets[index % len(offsets)][bus_index], seconds=35)
            arrivals[key] = {
                "EstimatedArrival": arrival.isoformat(), "Monitored": 1,
                "Load": loads[(index + bus_index) % 3], "Feature": "WAB", "Type": "DD" if index == 1 else "SD",
            }
        result.append({"ServiceNo": number, "Operator": "DEMO", **arrivals})
    return {"BusStopCode": "DEMO", "Services": result}
