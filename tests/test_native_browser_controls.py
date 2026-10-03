"""Exercise native control logic without requiring GTK on the test host."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


SOURCE = Path(__file__).parents[1] / "native-display" / "pi_bus_native.py"


def native_method(name, dependencies=None):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)
    namespace = dict(dependencies or {})
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
    def test_back_swipe_requires_rightward_horizontal_motion_and_back_destination(self):
        swipe = native_method("browser_swipe_back")
        calls = []
        owner = SimpleNamespace(browser_state={"can_back":True}, request_browser=calls.append)
        for x, y in ((150,0),(-150,0),(60,0),(150,120),(0,150)): swipe(owner,None,x,y)
        self.assertEqual(calls, ["back"])
        owner.browser_state = {"can_back":False}; swipe(owner,None,800,0)
        self.assertEqual(calls, ["back"])

    def test_artist_panel_keeps_portrait_and_name_without_biography(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "render_artist_profile")
        code = ast.unparse(method)
        self.assertIn('Gtk.Picture()', code)
        self.assertIn("'artist-name'", code)
        self.assertNotIn('artist_bio', code)
        self.assertNotIn('get_json', code)
        self.assertIn('self.render_artist_profile(data.get("artist_profile"))', SOURCE.read_text(encoding="utf-8"))
        web = (SOURCE.parents[1] / "roon-controller" / "static" / "app.js").read_text(encoding="utf-8")
        self.assertIn('renderArtistProfile(data.artist_profile)', web)
        self.assertNotIn('Artist background is unavailable.', web)

    def test_theme_updates_the_selector_without_triggering_a_save(self):
        calls = []
        owner = SimpleNamespace(settings_data={},window=SimpleNamespace(add_css_class=calls.append,remove_css_class=calls.append),browser_scrubber=SimpleNamespace(queue_draw=lambda:calls.append('draw')))
        owner.touch_theme_buttons = {value: SimpleNamespace(add_css_class=lambda cls, value=value:calls.append((value,cls)),remove_css_class=lambda cls:None) for value in ('fresh-mint','roon')}
        native_method('apply_theme')(owner, 'roon')
        self.assertEqual(owner.settings_data['display_theme'], 'roon')
        self.assertEqual(calls, ['theme-roon',('roon','active'),'draw'])
        self.assertFalse(owner.theme_updating)
        native_method('change_theme')(SimpleNamespace(theme_updating=True), 'roon')

    def test_native_search_passes_the_selected_source(self):
        for selected, expected in ((0,'library'),(1,'tidal')):
            calls = []
            owner = SimpleNamespace(browser_search_entry=SimpleNamespace(get_text=lambda:' Radiohead '),browser_search_source=SimpleNamespace(get_selected=lambda:selected),set_roon_view=lambda view:calls.append(view),request_browser=lambda action,**data:calls.append((action,data)))
            native_method('submit_browser_search')(owner)
            self.assertEqual(calls, ['browse',('search',{'query':'Radiohead','source':'all'})])

    def test_surprise_selection_and_bottom_back_are_present_in_both_interfaces(self):
        code = SOURCE.read_text(encoding='utf-8')
        self.assertIn('and not data.get("surprise_preview")', code)
        self.assertIn('active_section = "surprise" if data.get("surprise_preview")',code)
        self.assertIn('spacer.set_vexpand(True); sidebar.append(spacer); sidebar.append(self.browser_back)',code)
        self.assertIn('self.button("BACK"', code)
        web = (SOURCE.parents[1] / 'roon-controller/static/app.js').read_text(encoding='utf-8')
        self.assertIn("const activeSection = data.surprise_preview ? 'surprise'", web)
        self.assertIn('!data.can_back || Boolean(data.surprise_preview)',web)

    def test_grid_minimums_fit_physical_monitor_without_using_expanded_content(self):
        metrics = native_method("browser_grid_metrics", {"Gdk": SimpleNamespace(Display=SimpleNamespace(get_default=lambda: display))})
        for width in (480, 720, 800, 1024, 1280):
            monitor = SimpleNamespace(get_geometry=lambda:SimpleNamespace(width=width))
            display = SimpleNamespace(get_monitors=lambda:SimpleNamespace(get_n_items=lambda:1,get_item=lambda _:monitor))
            for genres in (True, False):
                columns, size = metrics(SimpleNamespace(), genres)
                self.assertLessEqual(columns * (size + 12) + (columns - 1) * 16, width - 266)
                self.assertLessEqual(size, 212)

    def test_playback_handoff_requires_successful_navigation_response(self):
        for data, expected in (({"navigate":"now"}, ["render", "now"]), ({}, ["render"]), ({"navigate":"now","error":"failed"}, ["render"])):
            calls = []
            owner = SimpleNamespace(render_browser=lambda _:calls.append("render"),set_roon_view=calls.append)
            native_method("apply_browser_response")(owner, data)
            self.assertEqual(calls, expected)

    def test_keyboard_edits_at_cursor_and_replaces_selection(self):
        entry = Entry("ac", 1)
        owner = SimpleNamespace(browser_search_entry=entry)
        key = native_method("browser_keyboard_key")
        key(owner, "B"); self.assertEqual(entry.text, "abc")
        key(owner, "BACKSPACE"); self.assertEqual(entry.text, "ac")
        entry.selection = (True, 0, 2)
        key(owner, "Z"); self.assertEqual(entry.text, "z")
        key(owner, "CLEAR"); self.assertEqual(entry.text, "")

    def test_dot_and_letter_ink_have_identical_centres_at_every_letter(self):
        class Canvas:
            def __getattr__(self, name): return lambda *_: None
            def arc(self, _x, y, *_): self.dot_y = y
            def move_to(self, _x, y): self.text_baseline = y
            def text_extents(self, _text): return (0, -13, 12, 13, 12, 0)
        draw = native_method("draw_browser_scrubber")
        for height in (240, 480, 720):
            for value in range(26):
                owner = SimpleNamespace(browser_scrub_scale=SimpleNamespace(get_value=lambda:value))
                canvas = Canvas(); draw(owner, None, canvas, 74, height)
                self.assertAlmostEqual(canvas.dot_y, canvas.text_baseline - 13 + 6.5)
                self.assertGreaterEqual(canvas.dot_y, 16); self.assertLessEqual(canvas.dot_y, height - 16)

    def test_scrubber_touch_mapping_matches_drawing_at_every_letter(self):
        at = native_method("browser_scrub_at")
        for height in (240, 480, 720):
            values = []
            owner = SimpleNamespace(browser_scrubber=SimpleNamespace(get_allocated_height=lambda:height), browser_scrub_scale=SimpleNamespace(set_value=values.append))
            for value in range(26): at(owner, 16 + (height - 32) * value / 25)
            self.assertEqual(values, list(range(26)))

    def test_latest_jump_is_retained_while_results_are_loading(self):
        owner = SimpleNamespace(browser_loading=True)
        request = native_method("request_browser")
        request(owner, "jump", letter="D"); request(owner, "jump", letter="F")
        self.assertEqual(owner.browser_pending_request, ("jump", {"letter":"F"}))

    def test_result_sync_cannot_move_scrubber_during_drag(self):
        owner = SimpleNamespace(browser_state={"alpha_scrub":True}, browser_scrub_dragging=True)
        native_method("sync_browser_scrubber")(owner)

    def test_section_switch_remembers_the_old_scroll_and_restores_the_new_one(self):
        thread = SimpleNamespace(Thread=lambda **_: SimpleNamespace(start=lambda:None))
        owner = SimpleNamespace(browser_loading=False, browser_state={"section":"artists"}, browser_section_scrolls={"albums":72}, browser_scroll=SimpleNamespace(get_vadjustment=lambda:SimpleNamespace(get_value=lambda:350)), browser_message=SimpleNamespace(set_visible=lambda _:None), _request_browser=lambda *_:None)
        native_method("request_browser", {"threading":thread})(owner, "section", section="albums")
        self.assertEqual(owner.browser_section_scrolls["artists"], 350)
        self.assertEqual(owner.browser_scroll_restore, 72)

    def test_old_scroll_restore_finishes_before_the_next_queued_request(self):
        calls = []
        owner = SimpleNamespace(browser_scroll_restore=350, restore_browser_scroll=lambda:calls.append("restore"), sync_browser_scrubber=lambda:calls.append("sync"), maybe_load_more_browser=lambda:None, browser_pending_request=("section", {"section":"albums"}), request_browser=lambda *_args, **_kwargs:calls.append("request"))
        native_method("finish_browser_render", {"GLib":SimpleNamespace(timeout_add=lambda *_:None)})(owner)
        self.assertEqual(calls, ["restore", "sync", "request"])
        self.assertFalse(owner.browser_loading); self.assertFalse(owner.browser_rendering)


if __name__ == "__main__":
    unittest.main()
