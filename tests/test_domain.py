import unittest
from datetime import datetime, timezone

from pi_bus_time_display.domain import minutes_until, normalise


class DomainTests(unittest.TestCase):
    def test_route_order_and_colours_do_not_depend_on_reporting_order_or_day(self):
        now = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        for numbers in (("401", "42", "40"), ("42", "40"), ("401", "40")):
            result = normalise({"Services": [{"ServiceNo": number} for number in numbers]}, now, (), 7)
            expected = [number for number in ("40", "42", "401") if number in numbers]
            self.assertEqual([item["service"] for item in result], expected)
            self.assertEqual([item["colour"] for item in result], [{"40": "blue", "42": "green", "401": "violet"}[number] for number in expected])

    def test_minutes_round_down_as_lta_advises(self):
        now = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        self.assertEqual(minutes_until("2026-01-01T06:07:59+00:00", now), 7)

    def test_late_bus_is_due_not_negative(self):
        now = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        self.assertEqual(minutes_until("2026-01-01T05:59:00+00:00", now), 0)

    def test_filters_services_and_calculates_leave_time(self):
        now = datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)
        payload = {"Services": [{"ServiceNo": "15", "NextBus": {"EstimatedArrival": "2026-01-01T06:09:01+00:00", "Monitored": 1, "Load": "SEA"}}, {"ServiceNo": "99"}]}
        result = normalise(payload, now, ("15",), 7)
        self.assertEqual(result[0]["leave_in"], 2)
        self.assertEqual(result[0]["arrivals"][0]["load_label"], "Seats")
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
