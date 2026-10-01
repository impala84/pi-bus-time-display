import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "pi-bus-system-action"


def load_helper():
    loader = importlib.machinery.SourceFileLoader("pi_bus_system_action", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class SystemActionQueueTests(unittest.TestCase):
    def test_drains_requests_in_order(self):
        helper = load_helper()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            queue = state / "system-action-queue"
            queue.mkdir()
            (queue / "0002.json").write_text(json.dumps({"action": "display_on"}), encoding="utf-8")
            (queue / "0001.json").write_text(json.dumps({"action": "display_off"}), encoding="utf-8")
            with patch.object(helper, "STATE", state), patch.object(helper, "REQUEST", state / "legacy.json"), patch.object(helper, "QUEUE", queue), patch.object(helper, "STATUS", state / "status"), patch.object(helper, "execute") as execute:
                helper.main()
            self.assertEqual([call.args[0]["action"] for call in execute.call_args_list], ["display_off", "display_on"])
            self.assertFalse(list(queue.glob("*.json")))

    def test_failed_request_does_not_strand_later_wake(self):
        helper = load_helper()
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory)
            queue = state / "system-action-queue"
            queue.mkdir()
            (queue / "0001.json").write_text(json.dumps({"action": "bad"}), encoding="utf-8")
            (queue / "0002.json").write_text(json.dumps({"action": "display_on"}), encoding="utf-8")
            seen = []

            def execute(data):
                seen.append(data["action"])
                if data["action"] == "bad":
                    raise ValueError("broken request")

            with patch.object(helper, "STATE", state), patch.object(helper, "REQUEST", state / "legacy.json"), patch.object(helper, "QUEUE", queue), patch.object(helper, "STATUS", state / "status"), patch.object(helper, "execute", side_effect=execute):
                helper.main()
            self.assertEqual(seen, ["bad", "display_on"])
            self.assertFalse(list(queue.glob("*.json")))


if __name__ == "__main__":
    unittest.main()
