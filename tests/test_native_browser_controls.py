"""Exercise native control logic without requiring GTK on the test host."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


SOURCE = Path(__file__).parents[1] / "native-display" / "pi_bus_native.py"


def native_method(name):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = {}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace[name]


class Entry:
    def __init__(self, text, position, selection=(False, 0, 0)):
        self.text, self.position, self.selection = text, position, selection
    def get_text(self): return self.text
    def get_position(self): return self.position
    def get_selection_bounds(self): return self.selection
    def set_text(self, text): self.text = text
    def set_position(self, position): self.position = position


class NativeBrowserControlsTests(unittest.TestCase):
    def test_keyboard_edits_at_cursor_and_replaces_selection(self):
        entry = Entry("ac", 1)
        owner = SimpleNamespace(browser_search_entry=entry)
        key = native_method("browser_keyboard_key")
        key(owner, "B"); self.assertEqual(entry.text, "abc")
        key(owner, "BACKSPACE"); self.assertEqual(entry.text, "ac")
        entry.selection = (True, 0, 2)
        key(owner, "Z"); self.assertEqual(entry.text, "z")
        key(owner, "CLEAR"); self.assertEqual(entry.text, "")

    def test_letter_tracks_actual_thumb_bounds_at_both_ends(self):
        margins = []
        label = SimpleNamespace(get_allocated_height=lambda:34, set_margin_top=margins.append)
        owner = SimpleNamespace(browser_scrub_letter=label, browser_scrub_scale=SimpleNamespace(get_slider_range=lambda:(8, 26)))
        track = native_method("track_browser_scrub_letter")
        self.assertTrue(track(owner, None, None)); self.assertEqual(margins[-1], 0)
        owner.browser_scrub_scale.get_slider_range = lambda:(374, 392)
        track(owner, None, None); self.assertEqual(margins[-1], 366)

    def test_latest_jump_is_retained_while_results_are_loading(self):
        owner = SimpleNamespace(browser_loading=True)
        request = native_method("request_browser")
        request(owner, "jump", letter="D"); request(owner, "jump", letter="F")
        self.assertEqual(owner.browser_pending_request, ("jump", {"letter":"F"}))

    def test_result_sync_cannot_move_scrubber_during_drag(self):
        owner = SimpleNamespace(browser_state={"alpha_scrub":True}, browser_scrub_dragging=True)
        native_method("sync_browser_scrubber")(owner)


if __name__ == "__main__":
    unittest.main()
