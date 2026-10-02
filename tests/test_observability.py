import json
import os
import unittest
from unittest.mock import MagicMock, patch

from pi_bus_time_display.config import Config
from pi_bus_time_display.observability import OpenObserveLogger, openobserve_endpoint


class OpenObserveTests(unittest.TestCase):
    def test_endpoint_uses_configured_org_and_stream(self):
        config = Config(
            openobserve_enabled=True,
            openobserve_url="http://observe.local:5080/",
            openobserve_org="home lab",
            openobserve_stream="pi events",
        )
        self.assertEqual(
            openobserve_endpoint(config),
            "http://observe.local:5080/api/home%20lab/pi%20events/_json",
        )

    def test_test_event_uses_basic_auth_without_putting_password_in_payload(self):
        config = Config(
            openobserve_enabled=True,
            openobserve_url="https://observe.example",
            openobserve_org="default",
            openobserve_stream="pi_home",
            openobserve_username="phil@example.com",
        )
        response = MagicMock(status=200)
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with patch.dict(os.environ, {"OPENOBSERVE_PASSWORD": "very-secret"}), patch(
            "pi_bus_time_display.observability.urllib.request.urlopen", return_value=response
        ) as open_url:
            logger = OpenObserveLogger(lambda: config)
            try:
                logger.test()
            finally:
                logger.close()
        request = open_url.call_args.args[0]
        records = json.loads(request.data)
        self.assertEqual(records[0]["event"], "openobserve.test")
        self.assertNotIn("very-secret", request.data.decode())
        self.assertTrue(request.headers["Authorization"].startswith("Basic "))

    def test_disabled_logger_does_not_enqueue(self):
        logger = OpenObserveLogger(lambda: Config())
        try:
            self.assertFalse(logger.emit("example"))
        finally:
            logger.close()


if __name__ == "__main__":
    unittest.main()
