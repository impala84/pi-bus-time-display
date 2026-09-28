#!/usr/bin/env python3
import json
import urllib.request
import gi

gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib

BUS_STATUS='http://127.0.0.1:8765/api/status'
ROON_STATE='http://127.0.0.1:8766/api/state'

class Display(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='uk.co.dallabs.PiBusNative')
        self.window=None

    def do_activate(self):
        self.window=Gtk.ApplicationWindow(application=self)
        self.window.set_decorated(False)
        self.window.fullscreen()
        self.window.set_default_size(800,480)
        self.stack=Gtk.Stack()
        self.window.set_child(self.stack)
        self.bus=Gtk.Label(label='Loading bus times…')
        self.bus.set_wrap(True)
        self.bus.set_justify(Gtk.Justification.CENTER)
        self.roon=Gtk.Label(label='Waiting for Roon…')
        self.roon.set_wrap(True)
        self.roon.set_justify(Gtk.Justification.CENTER)
        self.sleep=Gtk.Box()
        self.stack.add_named(self.bus,'bus')
        self.stack.add_named(self.roon,'roon')
        self.stack.add_named(self.sleep,'sleep')
        self.window.present()
        GLib.timeout_add_seconds(2,self.refresh)
        self.refresh()

    def get_json(self,url):
        try:
            with urllib.request.urlopen(url,timeout=0.5) as r:
                return json.load(r)
        except Exception:
            return None

    def refresh(self):
        status=self.get_json(BUS_STATUS)
        if status:
            if status.get('window_active'):
                lines=[status.get('stop_name','Bus times')]
                for svc in status.get('services',[]):
                    arr=[]
                    for a in svc.get('arrivals',[]):
                        mins=a.get('minutes')
                        arr.append('Arr' if mins==0 else f'{mins} min')
                    if arr:
                        lines.append(f"{svc.get('service','')}   {'   '.join(arr[:3])}")
                self.bus.set_text('\n\n'.join(lines))
                self.stack.set_visible_child_name('bus')
                return True
        roon=self.get_json(ROON_STATE)
        if roon and roon.get('zone'):
            zone=roon['zone']
            title=zone.get('now_playing',{}).get('three_line',{}).get('line1') or zone.get('display_name') or 'Roon'
            artist=zone.get('now_playing',{}).get('three_line',{}).get('line2') or ''
            self.roon.set_text(f'{title}\n{artist}')
            self.stack.set_visible_child_name('roon')
        else:
            self.roon.set_text('Roon\nWaiting for player…')
            self.stack.set_visible_child_name('roon')
        return True

if __name__=='__main__':
    Display().run(None)
