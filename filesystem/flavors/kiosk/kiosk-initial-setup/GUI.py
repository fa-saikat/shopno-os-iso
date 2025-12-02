#!/usr/bin/env python3

"""
Unified Touch Control Panel - A 3-page touch-friendly GUI application combining:
1. Wi-Fi Manager - NetworkManager frontend
2. Audio/Brightness Controls - System controls
3. Link Manager - Link saver and opener

Dependencies (Debian/Ubuntu):
  sudo apt update
  sudo apt install -y python3-gi gir1.2-gtk-3.0 network-manager brightnessctl alsa-utils

Run:
  python3 unified_control_panel.py

Author: Fahim Abrar Saikat <fahim.saikat@jadupc.com> (JaduPc)
"""

import gi
import subprocess
import shlex
import threading
import time
import webbrowser

gi.require_version('Gtk', '3.0')
gi.require_version('GLib', '2.0')

from gi.repository import Gtk, GLib

LINK_FILE_PATH = ".kiosk_link"  # File to save links


def run_cmd(cmd):
    try:
        parts = shlex.split(cmd)
        p = subprocess.Popen(parts, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(timeout=30)
        return p.returncode, out.decode(errors='ignore').strip(), err.decode(errors='ignore').strip()
    except Exception as e:
        return 1, '', str(e)


class WifiRow(Gtk.Box):
    def __init__(self, ssid, security, signal, parent_window, active=False):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.ssid = ssid
        self.security = security
        self.signal = signal
        self.active = active
        self.parent_window = parent_window

        lbl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.ssid_label = Gtk.Label(xalign=0)
        if not active:
            # For non-active networks, set SSID normally
            safe_ssid = GLib.markup_escape_text(ssid)
            self.ssid_label.set_markup(f"<b>{safe_ssid}</b>")
        # For active networks, SSID will be set in the active block below
        self.info_label = Gtk.Label(label=f"{security} • {signal}%", xalign=0)
        lbl_box.pack_start(self.ssid_label, False, False, 0)
        lbl_box.pack_start(self.info_label, False, False, 0)

        self.pack_start(lbl_box, True, True, 0)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        if active:
            # Add connected indicator to the SSID label instead
            safe_ssid = GLib.markup_escape_text(ssid)
            self.ssid_label.set_markup(f"<b>{safe_ssid}</b> 🟢")
            
            btn = Gtk.Button(label="Disconnect")
            btn.connect('clicked', self.on_disconnect_clicked)
            btn.set_size_request(140, 60) 
            btn_box.pack_start(btn, False, False, 0)
        else:
            btn = Gtk.Button(label="Connect")
            btn.connect('clicked', self.on_connect_clicked)
            btn.set_size_request(140, 60)
            btn_box.pack_start(btn, False, False, 0)

        self.pack_end(btn_box, False, False, 0)
        
        # Set touch-friendly margins for better spacing
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(24)
        self.set_margin_end(24)

    def on_connect_clicked(self, btn):
        if self.security and self.security.lower() != 'none' and self.security != '--':
            dlg = Gtk.Dialog(title=f"Connect to {self.ssid}", transient_for=self.parent_window, flags=0)
            dlg.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
            content = dlg.get_content_area()
            pw_entry = Gtk.Entry()
            pw_entry.set_visibility(False)
            pw_entry.set_placeholder_text('Password')
            pw_entry.set_activates_default(True)
            content.pack_start(Gtk.Label(label=f"Enter password for {self.ssid}"), False, False, 6)
            content.pack_start(pw_entry, False, False, 6)
            dlg.set_default_size(300, 80)
            dlg.show_all()
            resp = dlg.run()
            password = pw_entry.get_text()
            dlg.destroy()
            if resp != Gtk.ResponseType.OK:
                return
        else:
            password = None

        threading.Thread(target=self.connect_thread, args=(password,), daemon=True).start()

    def on_disconnect_clicked(self, btn):
        threading.Thread(target=self.disconnect_thread, daemon=True).start()

    def connect_thread(self, password):
        GLib.idle_add(self._set_connecting_state, True)
        if password:
            if 'WPA' in self.security.upper():
                cmd = f"nmcli device wifi connect '{self.ssid}' password '{password}'"
            elif 'WEP' in self.security.upper():
                cmd = f"nmcli device wifi connect '{self.ssid}' password '{password}' --wep"
            else:
                cmd = f"nmcli device wifi connect '{self.ssid}' password '{password}'"
        else:
            cmd = f"nmcli device wifi connect '{self.ssid}'"
        
        rc, out, err = run_cmd(cmd)
        
        if rc != 0 and 'key-mgmt' in err.lower():
            if password:
                profile_cmd = f"nmcli connection add type wifi con-name '{self.ssid}' ifname '*' ssid '{self.ssid}'"
                if 'WPA' in self.security.upper() or 'RSN' in self.security.upper():
                    profile_cmd += f" wifi-sec.key-mgmt wpa-psk wifi-sec.psk '{password}'"
                elif 'WEP' in self.security.upper():
                    profile_cmd += f" wifi-sec.key-mgmt wep wifi-sec.wep-key0 '{password}'"
                else:
                    profile_cmd += f" wifi-sec.key-mgmt wpa-psk wifi-sec.psk '{password}'"
                
                rc2, out2, err2 = run_cmd(profile_cmd)
                if rc2 == 0:
                    rc, out, err = run_cmd(f"nmcli connection up '{self.ssid}'")
                else:
                    out, err = out2, err2
        
        msg = out if out else err
        GLib.idle_add(self._show_result, rc == 0, msg)
        GLib.idle_add(self._set_connecting_state, False)

    def disconnect_thread(self):
        cmd = "nmcli -t -f NAME,TYPE connection show --active"
        rc, out, err = run_cmd(cmd)
        if rc != 0:
            GLib.idle_add(self._show_result, False, err or 'Failed to list active connections')
            return
        conn_name = None
        for line in out.splitlines():
            if not line:
                continue
            parts = line.split(':')
            name, typ = parts if len(parts) > 1 else (line, '')
            if name == self.ssid or name.startswith(self.ssid + ' '):
                conn_name = name
                break
        if conn_name:
            rc, out, err = run_cmd(f"nmcli connection down '{conn_name}'")
            GLib.idle_add(self._show_result, rc == 0, out or err)
        else:
            rc, out, err = run_cmd("nmcli device disconnect wlan0")
            GLib.idle_add(self._show_result, rc == 0, out or err)

    def _set_connecting_state(self, connecting):
        pass

    def _show_result(self, ok, msg):
        md = Gtk.MessageDialog(
            transient_for=self.parent_window, 
            flags=0, 
            message_type=(Gtk.MessageType.INFO if ok else Gtk.MessageType.ERROR), 
            buttons=Gtk.ButtonsType.OK, 
            text=("Success" if ok else "Error")
        )
        md.format_secondary_text(msg)
        md.run()
        md.destroy()


class UnifiedControlPanel(Gtk.Window):
    def __init__(self):
        super().__init__(title="ShopnoOS Kiosk Setup Wizard")
        self.set_default_size(700, 500)
        # self.set_border_width(8)
        self.maximize()

        # Main container
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(main_box)

        # Navigation header
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        main_box.pack_start(nav_box, False, False, 0)

        # Navigation buttons
        self.wifi_btn = Gtk.Button(label="📶 Wi-Fi")
        self.wifi_btn.set_size_request(180, 60)  # Larger touch-friendly size
        self.wifi_btn.connect('clicked', lambda x: self.show_page(0))
        nav_box.pack_start(self.wifi_btn, True, True, 0)

        self.audio_btn = Gtk.Button(label="🔊 Controls")
        self.audio_btn.set_size_request(180, 60)  # Larger touch-friendly size
        self.audio_btn.connect('clicked', lambda x: self.show_page(1))
        nav_box.pack_start(self.audio_btn, True, True, 0)

        self.link_btn = Gtk.Button(label="🔗 Links")
        self.link_btn.set_size_request(180, 60)  # Larger touch-friendly size
        self.link_btn.connect('clicked', lambda x: self.show_page(2))
        nav_box.pack_start(self.link_btn, True, True, 0)

        # Exit button
        exit_btn = Gtk.Button(label="❌ Exit")
        exit_btn.set_size_request(120, 60)  # Touch-friendly size
        exit_btn.connect('clicked', lambda x: Gtk.main_quit())
        nav_box.pack_end(exit_btn, False, False, 0)

        # Pages container
        self.stack = Gtk.Stack()
        main_box.pack_start(self.stack, True, True, 0)

        # Create pages
        self.create_wifi_page()
        self.create_audio_page()
        self.create_link_page()

        # Show initial page
        self.show_page(0)

    def create_wifi_page(self):
        """Create Wi-Fi management page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label()
        title.set_markup("<span size='xx-large'><b>Wi-Fi Networks</b></span>")
        title.set_xalign(0)
        header.pack_start(title, True, True, 0)

        scan_btn = Gtk.Button(label="🔄 Refresh")
        scan_btn.set_size_request(140, 60)  # Touch-friendly size
        scan_btn.connect('clicked', self.on_scan_clicked)
        header.pack_end(scan_btn, False, False, 0)

        page.pack_start(header, False, False, 0)

        # Networks list
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.listbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scrolled.add(self.listbox)
        page.pack_start(scrolled, True, True, 0)

        # Status
        self.wifi_status_lbl = Gtk.Label(label="Status: idle", xalign=0)
        page.pack_start(self.wifi_status_lbl, False, False, 0)

        self.stack.add_named(page, "wifi")

        # Auto-refresh and initial load
        self.scan_interval = 8
        self.refresh_networks()
        GLib.timeout_add_seconds(self.scan_interval, self.refresh_networks)

    def create_audio_page(self):
        """Create audio and brightness controls page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_margin_top(30)
        page.set_margin_bottom(30)
        page.set_margin_start(30)
        page.set_margin_end(30)

        # Title
        title = Gtk.Label()
        title.set_markup("<span size='xx-large'><b>System Controls</b></span>")
        page.pack_start(title, False, False, 0)

        # Brightness
        brightness_label = Gtk.Label(label="🔆 Brightness")
        brightness_label.set_xalign(0)
        page.pack_start(brightness_label, False, False, 0)

        self.brightness_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.brightness_slider.set_value(self.get_brightness())
        self.brightness_slider.set_hexpand(True)
        self.brightness_slider.connect("value-changed", self.on_brightness_changed)
        page.pack_start(self.brightness_slider, False, False, 0)

        # Volume
        volume_label = Gtk.Label(label="🔊 Volume")
        volume_label.set_xalign(0)
        page.pack_start(volume_label, False, False, 0)

        hbox_volume = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        page.pack_start(hbox_volume, False, False, 0)

        self.volume_slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self.volume_slider.set_value(self.get_volume())
        self.volume_slider.set_hexpand(True)
        self.volume_slider.connect("value-changed", self.on_volume_changed)
        hbox_volume.pack_start(self.volume_slider, True, True, 0)

        self.mute_button = Gtk.Button(label="🔇 Mute")
        self.mute_button.set_size_request(120, 60)
        self.mute_button.connect("clicked", self.on_toggle_mute)
        hbox_volume.pack_start(self.mute_button, False, False, 0)

        self.update_mute_button()

        self.stack.add_named(page, "audio")

    def create_link_page(self):
        """Create link manager page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_margin_top(30)
        page.set_margin_bottom(30)
        page.set_margin_start(30)
        page.set_margin_end(30)

        # Title
        title = Gtk.Label()
        title.set_markup("<span size='xx-large'><b>Link Manager</b></span>")
        page.pack_start(title, False, False, 0)

        # Entry for link input
        self.link_entry = Gtk.Entry()
        self.link_entry.set_placeholder_text("Enter your link here...")
        self.link_entry.set_size_request(400, 50)
        page.pack_start(self.link_entry, False, False, 0)

        # Button box
        hbox = Gtk.Box(spacing=20)
        page.pack_start(hbox, False, False, 0)

        # Dry Run button
        btn_dry = Gtk.Button(label="👁️ Preview")
        btn_dry.set_size_request(160, 60)
        btn_dry.connect("clicked", self.on_dry_run)
        hbox.pack_start(btn_dry, True, True, 0)

        # Save button
        btn_save = Gtk.Button(label="💾 Save & Open")
        btn_save.set_size_request(160, 60)
        btn_save.connect("clicked", self.on_save_link)
        hbox.pack_start(btn_save, True, True, 0)

        # Recent links (if file exists)
        try:
            with open(LINK_FILE_PATH, 'r') as f:
                recent_link = f.read().strip()
                if recent_link:
                    recent_label = Gtk.Label(label="Recent Link:")
                    recent_label.set_xalign(0)
                    page.pack_start(recent_label, False, False, 0)
                    
                    recent_btn = Gtk.Button(label=f"🔗 {recent_link[:50]}...")
                    recent_btn.connect("clicked", lambda x: webbrowser.open(recent_link))
                    page.pack_start(recent_btn, False, False, 0)
        except FileNotFoundError:
            pass

        self.stack.add_named(page, "links")

    def show_page(self, page_num):
        """Show the specified page and update navigation buttons"""
        pages = ["wifi", "audio", "links"]
        buttons = [self.wifi_btn, self.audio_btn, self.link_btn]
        
        # Reset all button styles
        for btn in buttons:
            btn.get_style_context().remove_class("suggested-action")
        
        # Highlight active button
        buttons[page_num].get_style_context().add_class("suggested-action")
        
        # Show page
        self.stack.set_visible_child_name(pages[page_num])

    # Wi-Fi Methods
    def on_scan_clicked(self, btn):
        threading.Thread(target=self._scan_and_update, daemon=True).start()

    def refresh_networks(self):
        threading.Thread(target=self._scan_and_update, daemon=True).start()
        return True

    def _scan_and_update(self):
        GLib.idle_add(self._set_wifi_status, 'Scanning...')
        run_cmd('nmcli device wifi rescan')
        time.sleep(1)
        rc, out, err = run_cmd("nmcli -t -f SSID,SECURITY,SIGNAL device wifi list")
        if rc != 0:
            GLib.idle_add(self._set_wifi_status, 'Scan failed: ' + (err or ''))
            return
        networks = []
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split(':')
            if len(parts) >= 3:
                ssid, security, signal = parts[0], parts[1], parts[2]
                networks.append((ssid, security, signal))
        rc2, out2, err2 = run_cmd("nmcli -t -f ACTIVE,SSID device wifi list")
        active_ssid = None
        if rc2 == 0:
            for line in out2.splitlines():
                if not line:
                    continue
                act, ss = line.split(':', 1) if ':' in line else (None, line)
                if act == 'yes':
                    active_ssid = ss
                    break
        GLib.idle_add(self._populate_list, networks, active_ssid)
        GLib.idle_add(self._set_wifi_status, 'Idle')

    def _populate_list(self, networks, active_ssid):
        for child in self.listbox.get_children():
            self.listbox.remove(child)
        seen = set()
        for ssid, security, signal in networks:
            if ssid in seen:
                continue
            seen.add(ssid)
            is_active = (ssid == active_ssid)
            row = WifiRow(ssid or '<hidden>', security or '--', signal or '0', self, active=is_active)
            self.listbox.pack_start(row, False, False, 0)
        self.listbox.show_all()

    def _set_wifi_status(self, s):
        self.wifi_status_lbl.set_text('Status: ' + s)

    # Audio/Brightness Methods
    def get_brightness(self):
        try:
            out = subprocess.check_output(["brightnessctl", "g"], stderr=subprocess.DEVNULL).decode().strip()
            max_out = subprocess.check_output(["brightnessctl", "m"], stderr=subprocess.DEVNULL).decode().strip()
            return (int(out) / int(max_out)) * 100
        except Exception:
            return 50.0

    def on_brightness_changed(self, slider):
        val = int(slider.get_value())
        subprocess.call(["brightnessctl", "s", f"{val}%"], stderr=subprocess.DEVNULL)

    def get_volume(self):
        try:
            out = subprocess.check_output(["amixer", "get", "Master"], stderr=subprocess.DEVNULL).decode()
            for line in out.splitlines():
                if "Mono:" in line or "Front Left:" in line or "Playback" in line:
                    if "[" in line and "%" in line:
                        return float(line.split("[")[1].split("%")[0])
        except Exception:
            return 50.0

    def on_volume_changed(self, slider):
        val = int(slider.get_value())
        subprocess.call(["amixer", "set", "Master", f"{val}%"], stderr=subprocess.DEVNULL)
        self.update_mute_button()

    def is_muted(self):
        try:
            out = subprocess.check_output(["amixer", "get", "Master"], stderr=subprocess.DEVNULL).decode()
            return "[off]" in out
        except Exception:
            return False

    def on_toggle_mute(self, button):
        subprocess.call(["amixer", "set", "Master", "toggle"], stderr=subprocess.DEVNULL)
        self.update_mute_button()

    def update_mute_button(self):
        if self.is_muted():
            self.mute_button.set_label("🔈 Unmute")
        else:
            self.mute_button.set_label("🔇 Mute")

    # Link Manager Methods
    def on_dry_run(self, widget):
        link = self.link_entry.get_text().strip()
        if link:
            webbrowser.open(link)
        else:
            self.show_message("Error", "Please enter a link first!")

    def on_save_link(self, widget):
        link = self.link_entry.get_text().strip()
        if link:
            try:
                with open(LINK_FILE_PATH, "w") as f:
                    f.write(link + "\n")
                webbrowser.open(link)
                self.link_entry.set_text("")  # Clear entry after saving
                self.show_message("Success", "Link saved and opened!")
            except Exception as e:
                self.show_message("Error", f"Failed to save link: {str(e)}")
        else:
            self.show_message("Error", "Please enter a link first!")

    def show_message(self, title, message):
        """Show a message dialog"""
        md = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO if title == "Success" else Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=title
        )
        md.format_secondary_text(message)
        md.run()
        md.destroy()


if __name__ == '__main__':
    app = UnifiedControlPanel()
    app.connect('destroy', Gtk.main_quit)
    app.show_all()
    Gtk.main()
