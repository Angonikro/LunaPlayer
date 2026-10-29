"""LunaPlayer GTK 4 interface."""
import os, subprocess
from pathlib import Path
import gi
gi.require_version('Gtk','4.0')
from gi.repository import Gtk, Gio, GLib, Gdk, Pango
from app.player import PlayerEngine
from app.playlist import Playlist
from app.settings import load_settings, save_settings
from app.metadata import read_metadata, write_metadata, read_cover_bytes
from app.formats import AUDIO_FILTER_LABEL, scan_folder, find_default_music_folder
from app.audio_cd import AudioCD
from app.cddb import lookup_cd
import threading
from app.controller_client import send_command
from app.equalizer import PRESETS
from app.i18n import tr
from app.vlc_player import VIDEO_EXTENSIONS, VIDEO_FILTER_LABEL, play_video, play_disc

def fmt_time(seconds):
    seconds=max(0,int(seconds)); return f'{seconds//60}:{seconds%60:02d}'

class LunaPlayerWindow(Gtk.ApplicationWindow):
    def __init__(self, application):
        # Do not call self._t() until settings have been loaded. GTK's parent
        # constructor may need the title before the instance has settings.
        super().__init__(application=application, title='LunaPlayer')
        self.settings=load_settings()
        self.set_default_size(1120,740); self.playlist=Playlist(); self._mp3_playlist_snapshot=None; self._cd_playlist_mode=False; self.cd_queue=None; self.cd_queue_index=0; self.cd_metadata=None; self.cd_playlist_meta={}; self.is_seeking=False; self._quitting=False
        try:self.engine=PlayerEngine(on_eos=self._on_eos,on_error=self._on_error); self.startup_error=''
        except Exception as exc:self.engine=None; self.startup_error=str(exc)
        self._build_ui(); self._set_theme(bool(self.settings.get('dark_mode', True))); self._update_volume_label(); GLib.timeout_add(400,self._tick); self.connect('close-request',self._on_close)
        if self.engine:
            self._restore_equalizer_settings()
        if self.engine and self.settings.get('audio_device'):
            try: self.engine.set_audio_device(self.settings.get('audio_device', ''))
            except Exception as exc: self._set_status(f'Audiogerät nicht verfügbar: {exc}')
        self.tray_toggle.set_active(bool(self.settings.get('tray_enabled', False)))
        if self.engine is None:
            self._set_status(self.startup_error)
        else:
            self._load_default_music_folder()
            if not self.engine.equalizer_available:
                self._set_status(self._t('Musikordner geprüft · Equalizer-Plugin nicht gefunden; Grundwiedergabe verfügbar'))

    def _t(self, text):
        return tr(text, self.settings.get("language", "de"))

    def _install_menu(self, root):
        """Restore the application menu with File, Settings, and Help actions."""
        menu = Gio.Menu()
        file_menu = Gio.Menu()
        file_menu.append(self._t("Dateien hinzufügen…"), "win.add-files")
        file_menu.append(self._t("Ordner auswählen…"), "win.choose-folder")
        file_menu.append(self._t("CD abspielen…"), "win.play-cd")
        file_menu.append(self._t("Videos öffnen…"), "win.open-videos")
        file_menu.append(self._t("DVD / Blu-ray abspielen…"), "win.play-disc")
        file_menu.append(self._t("Beenden"), "win.quit")
        menu.append_submenu(self._t("Datei"), file_menu)
        settings_menu = Gio.Menu()
        settings_menu.append(self._t("Audiogerät auswählen…"), "win.audio-device")
        settings_menu.append(self._t("CDDB-Anbieter…"), "win.cddb-settings")
        settings_menu.append(self._t("Design: Dunkel"), "win.theme-dark")
        settings_menu.append(self._t("Design: Hell"), "win.theme-light")
        settings_menu.append(self._t("System-Tray aktivieren/deaktivieren"), "win.tray-toggle")
        language_menu = Gio.Menu()
        language_menu.append("Deutsch", "win.language-de")
        language_menu.append("English", "win.language-en")
        settings_menu.append_submenu(self._t("Sprache / Language"), language_menu)
        menu.append_submenu(self._t("Einstellungen"), settings_menu)
        help_menu = Gio.Menu()
        help_menu.append(self._t("Anleitung"), "win.help")
        help_menu.append(self._t("Info über LunaPlayer"), "win.about")
        menu.append_submenu(self._t("Hilfe"), help_menu)
        bar = Gtk.PopoverMenuBar.new_from_model(menu)
        root.append(bar)
        actions = [
            ("add-files", lambda *_: self._choose_files()),
            ("choose-folder", lambda *_: self._choose_folder()),
            ("play-cd", lambda *_: self._cd_dialog()),
            ("open-videos", lambda *_: self._choose_videos()),
            ("play-disc", lambda *_: self._disc_dialog()),
            ("quit", lambda *_: self._quit_app()),
            ("audio-device", lambda *_: self._audio_device_dialog()),
            ("cddb-settings", lambda *_: self._cddb_settings_dialog()),
            ("theme-dark", lambda *_: self._set_theme(True)),
            ("theme-light", lambda *_: self._set_theme(False)),
            ("tray-toggle", lambda *_: self.tray_toggle.set_active(not self.tray_toggle.get_active())),
            ("language-de", lambda *_: self._set_language("de")),
            ("language-en", lambda *_: self._set_language("en")),
            ("help", lambda *_: self._help_dialog()),
            ("about", lambda *_: self._about_dialog()),
        ]
        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

    def _set_language(self, language):
        if language not in ("de", "en"):
            return
        if self.settings.get("language", "de") == language:
            return
        self.settings["language"] = language
        save_settings(self.settings)
        # Rebuild the current window so every visible label changes immediately.
        # Playback state is retained in settings where available; avoid restarting
        # the whole application just to change the language.
        self._rebuild_for_language_change()

    def _rebuild_for_language_change(self):
        try:
            was_maximized = self.is_maximized()
            width, height = self.get_default_size()
            app = self.get_application()
            # Preserve playback-related settings before rebuilding the UI.
            self.settings["volume"] = self.volume.get_value() / 100.0
            save_settings(self.settings)
            self._quitting = True
            if self.engine:
                self.engine.close()
            replacement = LunaPlayerWindow(application=app)
            app.main_window = replacement
            if was_maximized:
                replacement.maximize()
            else:
                replacement.set_default_size(width, height)
            replacement.present()
            self.destroy()
        except Exception as exc:
            self._set_status(f"Sprache gespeichert; bitte neu starten: {exc}")

    def _language_changed(self, dropdown, _pspec):
        self._set_language("en" if dropdown.get_selected() == 1 else "de")

    def _restore_equalizer_settings(self):
        """Restore saved equalizer bands at startup."""
        bands = self.settings.get('equalizer_bands', [0] * 10)
        try:
            for index, value in enumerate(bands):
                self.engine.set_equalizer_band(index, float(value))
        except Exception:
            pass

    def _quit_app(self):
        self._quitting = True
        self.settings['volume'] = self.volume.get_value() / 100.0
        save_settings(self.settings)
        send_command("CHILD_QUIT")
        if self.engine: self.engine.close()
        self.get_application().quit()

    def _help_dialog(self, *_args):
        """Show a structured, non-modal help window so the player stays usable."""
        if getattr(self, "_help_window", None) is not None:
            try:
                self._help_window.present()
                return
            except Exception:
                self._help_window = None
        win = Gtk.Window(title=self._t("LunaPlayer – Anleitung"), transient_for=self, modal=False)
        win.set_default_size(680, 620)
        win.set_destroy_with_parent(True)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_margin_top(18); outer.set_margin_bottom(18)
        outer.set_margin_start(20); outer.set_margin_end(20)
        heading = Gtk.Label(label=self._t("LunaPlayer – Anleitung"), xalign=0)
        heading.add_css_class("title-1")
        outer.append(heading)
        subtitle = Gtk.Label(label=self._t("Deine Musik. Dein Klang."), xalign=0)
        subtitle.add_css_class("dim-label")
        outer.append(subtitle)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        sections = [
            ("1. Musik starten", "Beim Start sucht LunaPlayer automatisch nach Musik in Musik oder Music. Über Datei → Dateien hinzufügen… kannst du einzelne Dateien auswählen. Mit Ordner auswählen… wählst du einen Musikordner samt Unterordnern."),
            ("2. Wiedergabeliste", "Klicke einen Titel in der Liste doppelt an, um ihn abzuspielen. Die Suchleiste filtert die angezeigten Titel. Mit Speichern und Laden kannst du M3U-Playlists sichern und wieder öffnen. Über Aus Playlist entfernen oder Leeren kannst du die Liste ändern."),
            ("3. Wiedergabe und Lautstärke", "Verwende die Schaltflächen für vorherigen Titel, Wiedergabe/Pause, Stopp und nächsten Titel. Der Schieberegler zeigt die Position im Titel; der Lautstärkeregler steuert die Wiedergabelautstärke."),
            ("4. Audio-CD", "Lege eine Audio-CD ein und öffne Datei → CD abspielen… oder die Schaltfläche CD abspielen. Wähle das Laufwerk und klicke CD erkennen. Wenn Titelinformationen online gefunden werden, zeigt LunaPlayer Album und Interpret an. Wähle eine Tracknummer und starte die Wiedergabe."),
            ("5. CDDB und Cover", "Unter Einstellungen → CDDB-Anbieter… kannst du fre:ac oder dBpoweramp als bevorzugte Quelle auswählen und Server, CDDB-Pfad sowie Port bearbeiten. MusicBrainz und Cover Art Archive werden für ergänzende Album- und Coverinformationen verwendet. Online-Treffer hängen von der Datenbank und der Netzwerkverbindung ab."),
            ("6. Tags bearbeiten", "Wähle einen Titel in der Playlist aus und klicke Tags bearbeiten, um Titel, Interpret, Album, Jahr, Genre und Tracknummer zu bearbeiten. Speichern schreibt die Änderungen in die Musikdatei."),
            ("7. Equalizer", "Öffne Equalizer und wähle ein Klangprofil oder passe die Frequenzbänder an. Jede Änderung wird automatisch gespeichert und beim nächsten Start wiederhergestellt. Über „Klangprofil speichern…“ kannst du eigene Profile benennen und später wieder auswählen. Falls das benötigte GStreamer-Equalizer-Plugin fehlt, meldet LunaPlayer, dass der Equalizer nicht verfügbar ist."),
            ("8. Design und System-Tray", "Unter Einstellungen kannst du zwischen hellem und dunklem Design wechseln. Aktiviere System-Tray, wenn LunaPlayer beim Schließen im Hintergrund weiterlaufen soll. Ohne aktivierten Tray beendet das Schließen das Programm. Die Tray-Anzeige hängt von der Desktop-Unterstützung ab."),
            ("9. Beenden", "Wähle Datei → Beenden, um LunaPlayer vollständig zu schließen. Wenn der System-Tray aktiviert ist, beendet ein normales Schließen des Fensters die Anwendung nicht, sondern blendet sie aus; nutze dann Beenden im Programm oder im Tray-Menü."),
        ]
        for title, body in sections:
            label = Gtk.Label(label=self._t(title), xalign=0)
            label.add_css_class("heading")
            label.set_wrap(True)
            text = Gtk.Label(label=self._t(body), xalign=0, yalign=0)
            text.set_wrap(True)
            # Help text is informational; it must not appear selected when the
            # window opens. Keep it out of the keyboard focus chain as well.
            text.set_selectable(False)
            text.set_can_focus(False)
            label.set_can_focus(False)
            content.append(label); content.append(text)
        scroll.set_child(content)
        outer.append(scroll)
        close = Gtk.Button(label=self._t("Schließen"))
        close.set_halign(Gtk.Align.END)
        close.connect("clicked", lambda *_: win.close())
        outer.append(close)
        win.set_child(outer)
        self._help_window = win
        win.connect("close-request", lambda *_: (setattr(self, "_help_window", None), False)[1])
        win.present()

    def _about_dialog(self, *_args):
        dialog = Gtk.AboutDialog(transient_for=self, modal=False)
        dialog.set_program_name("LunaPlayer")
        dialog.set_version("1.4.0")
        dialog.set_comments("Deine Musik. Dein Klang.")
        dialog.set_copyright("© Goldisoft 2026")
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.present()

    def _set_theme(self, dark):
        self.settings['dark_mode'] = bool(dark)
        save_settings(self.settings)
        if hasattr(self, 'root_box'):
            self.root_box.remove_css_class('light-theme')
            self.root_box.remove_css_class('dark-theme')
            self.root_box.add_css_class('dark-theme' if dark else 'light-theme')
        self._set_status('Dunkles Design aktiviert' if dark else 'Helles Design aktiviert')

    def _audio_device_dialog(self, *_args):
        """Choose and persist a GStreamer-discovered audio output device."""
        dialog = Gtk.Dialog(title=self._t("Audiogerät auswählen"), transient_for=self, modal=True)
        dialog.add_button(self._t("Abbrechen"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._t("Übernehmen"), Gtk.ResponseType.ACCEPT)
        dialog.set_default_size(520, 180)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(18); box.set_margin_bottom(18)
        box.set_margin_start(18); box.set_margin_end(18)
        box.append(Gtk.Label(label=self._t("Audio-Ausgabe für Musik und Audio-CDs"), xalign=0))
        combo = Gtk.ComboBoxText()
        combo.append("", "Automatisch (Systemstandard)")
        outputs = self.engine.list_audio_outputs() if self.engine else []
        for name, _device in outputs:
            combo.append(name, name)
        selected = self.settings.get("audio_device", "") or ""
        if selected and not any(name == selected for name, _device in outputs):
            combo.append(selected, f"{selected} (derzeit nicht verfügbar)")
        combo.set_active_id(selected)
        if combo.get_active() < 0:
            combo.set_active(0)
        box.append(combo)
        if not outputs:
            note = Gtk.Label(label=self._t("Keine auswählbaren Audiogeräte gefunden. Der Systemstandard bleibt verfügbar."), xalign=0)
            note.set_wrap(True); note.add_css_class("dim-label"); box.append(note)
        dialog.get_content_area().append(box)
        dialog.connect("response", self._audio_device_response, combo)
        dialog.present()

    def _audio_device_response(self, dialog, response, combo):
        if response == Gtk.ResponseType.ACCEPT:
            selected = combo.get_active_id() or ""
            try:
                if self.engine:
                    self.engine.set_audio_device(selected)
                self.settings["audio_device"] = selected
                save_settings(self.settings)
                self._set_status("Audiogerät: " + (selected if selected else "Automatisch (Systemstandard)"))
            except Exception as exc:
                self._set_status(f"Audiogerät konnte nicht ausgewählt werden: {exc}")
                error = Gtk.AlertDialog(message=f"Das Audiogerät konnte nicht aktiviert werden.\\n{exc}")
                error.show(self)
        dialog.destroy()

    def _cddb_settings_dialog(self):
        dialog = Gtk.Dialog(title=self._t("CDDB-Anbieter einstellen"), transient_for=self, modal=True)
        dialog.add_button(self._t("Abbrechen"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._t("Speichern"), Gtk.ResponseType.ACCEPT)
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        grid.set_margin_top(16); grid.set_margin_bottom(16); grid.set_margin_start(16); grid.set_margin_end(16)
        grid.attach(Gtk.Label(label=self._t("Bevorzugter CDDB-Anbieter"), xalign=0), 0, 0, 1, 1)
        provider = Gtk.DropDown.new_from_strings(["fre:ac", "dBpoweramp"])
        provider.set_selected(1 if self.settings.get('cddb_provider', 'fre:ac') == 'dBpoweramp' else 0)
        grid.attach(provider, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label=self._t("Server fre:ac"), xalign=0), 0, 1, 1, 1)
        freac = Gtk.Entry(); freac.set_text(self.settings.get('cddb_freac_host', 'freedb.freac.org')); freac.set_hexpand(True); grid.attach(freac, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label=self._t("Server dBpoweramp"), xalign=0), 0, 2, 1, 1)
        dbp = Gtk.Entry(); dbp.set_text(self.settings.get('cddb_dbpoweramp_host', 'freedb.dbpoweramp.com')); dbp.set_hexpand(True); grid.attach(dbp, 1, 2, 1, 1)
        grid.attach(Gtk.Label(label=self._t("CDDB-Pfad"), xalign=0), 0, 3, 1, 1)
        path = Gtk.Entry(); path.set_text(self.settings.get('cddb_path', '/~cddb/cddb.cgi')); path.set_hexpand(True); grid.attach(path, 1, 3, 1, 1)
        grid.attach(Gtk.Label(label=self._t("Port"), xalign=0), 0, 4, 1, 1)
        port = Gtk.Entry(); port.set_text(str(self.settings.get('cddb_port', '80'))); grid.attach(port, 1, 4, 1, 1)
        dialog.get_content_area().append(grid)
        def response(d, result):
            if result == Gtk.ResponseType.ACCEPT:
                if not freac.get_text().strip() or not dbp.get_text().strip() or not path.get_text().strip().startswith('/') or not port.get_text().strip().isdigit():
                    self._set_status(self._t('Bitte Server, gültigen Pfad und Port eintragen.'))
                else:
                    self.settings.update({'cddb_provider': 'dBpoweramp' if provider.get_selected() == 1 else 'fre:ac', 'cddb_freac_host': freac.get_text().strip(), 'cddb_dbpoweramp_host': dbp.get_text().strip(), 'cddb_path': path.get_text().strip(), 'cddb_port': port.get_text().strip()})
                    save_settings(self.settings); self._set_status(self._t('CDDB-Einstellungen gespeichert.'))
            d.destroy()
        dialog.connect('response', response); dialog.present()

    def _build_ui(self):
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0); root.add_css_class('app-root'); self.root_box=root; self.set_child(root)
        self._install_menu(root)
        header=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=12); header.add_css_class('header')
        logo=Gtk.Label(label=self._t('☾')); logo.add_css_class('moon-logo')
        titlebox=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        name=Gtk.Label(label=self._t('LunaPlayer'),xalign=0); name.add_css_class('brand')
        subtitle=Gtk.Label(label=self._t('Deine Musik. Dein Klang.') + ' · Version 1.4.0',xalign=0); subtitle.add_css_class('muted')
        titlebox.append(name);titlebox.append(subtitle);header.append(logo);header.append(titlebox)
        spacer=Gtk.Box();spacer.set_hexpand(True);header.append(spacer)
        language_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        language_box.append(Gtk.Label(label=self._t("Sprache")))
        self.language_selector = Gtk.DropDown.new_from_strings(["Deutsch", "English"])
        self.language_selector.set_selected(1 if self.settings.get("language", "de") == "en" else 0)
        self.language_selector.connect("notify::selected", self._language_changed)
        language_box.append(self.language_selector); header.append(language_box)
        for label,callback in [('＋ Dateien',self._choose_files),('Ordner',self._choose_folder),('CD abspielen',self._cd_dialog),('Videos',self._choose_videos),('DVD / Blu-ray',self._disc_dialog),('Equalizer',self._equalizer_dialog),('Tags bearbeiten',self._edit_tags_dialog)]:
            b=Gtk.Button(label=self._t(label));b.connect('clicked',callback);header.append(b)
        self.tray_toggle=Gtk.CheckButton(label=self._t('System-Tray'))
        self.tray_toggle.set_tooltip_text(self._t('System-Tray aktivieren: Fenster beim Schließen im Tray behalten'))
        self.tray_toggle.connect('toggled', self._tray_toggle_changed)
        header.append(self.tray_toggle)
        root.append(header)
        content=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=0);content.set_vexpand(True);root.append(content)
        left=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=13);left.set_hexpand(True);left.set_size_request(440,-1)
        for prop,val in [('margin_top',24),('margin_bottom',20),('margin_start',28),('margin_end',24)]:setattr(left,'set_'+prop,val)
        content.append(left)
        self.cover_picture=Gtk.Picture();self.cover_picture.set_content_fit(Gtk.ContentFit.CONTAIN);self.cover_picture.set_size_request(310,310);self.cover_picture.set_halign(Gtk.Align.CENTER);self.cover_picture.add_css_class('cover-picture')
        self.cover_fallback=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=5);self.cover_fallback.set_size_request(310,310);self.cover_fallback.set_halign(Gtk.Align.CENTER);self.cover_fallback.set_valign(Gtk.Align.CENTER);self.cover_fallback.add_css_class('cover')
        moon=Gtk.Label(label=self._t('☾'));moon.add_css_class('cover-moon');cap=Gtk.Label(label=self._t('LUNAPLAYER'));cap.add_css_class('cover-caption');self.cover_fallback.append(moon);self.cover_fallback.append(cap)
        self.cover_stack=Gtk.Stack();self.cover_stack.set_size_request(310,310);self.cover_stack.add_named(self.cover_fallback,'fallback');self.cover_stack.add_named(self.cover_picture,'picture');self.cover_stack.set_visible_child_name('fallback');left.append(self.cover_stack)
        self.track_title=Gtk.Label(label=self._t('Noch kein Titel ausgewählt'),xalign=.5);self.track_title.add_css_class('track-title');self.track_title.set_ellipsize(Pango.EllipsizeMode.END)
        self.artist_label=Gtk.Label(label=self._t('Füge Musik hinzu, um zu beginnen'),xalign=.5);self.artist_label.add_css_class('muted');left.append(self.track_title);left.append(self.artist_label)
        timeline=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=10);self.elapsed=Gtk.Label(label=self._t('0:00'));self.total=Gtk.Label(label=self._t('0:00'))
        for time_label in (self.elapsed, self.total):
            time_label.set_width_chars(5)
            time_label.set_max_width_chars(5)
            time_label.set_xalign(0.5)
            time_label.set_justify(Gtk.Justification.CENTER)
            time_label.add_css_class('time-label')
        self.seek=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,100,1);self.seek.set_draw_value(False);self.seek.set_hexpand(True);self.seek.connect('change-value',self._seek)
        timeline.append(self.elapsed);timeline.append(self.seek);timeline.append(self.total);left.append(timeline)
        controls=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=12);controls.set_halign(Gtk.Align.CENTER)
        for label,cb in [('|◀',lambda *_:self._play_path(self.playlist.previous())),('▶',self._toggle_play),('■',self._stop_playback),('▶|',lambda *_:self._play_path(self.playlist.next()))]:
            b=Gtk.Button(label=label)
            if label=='▶':b.add_css_class('play-button');self.play_button=b
            b.connect('clicked',cb);controls.append(b)
        left.append(controls)
        volume_row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=10);volume_row.append(Gtk.Label(label=self._t('🔊')))
        self.volume=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,100,1);self.volume.set_value(float(self.settings.get('volume',.75))*100);self.volume.set_draw_value(False);self.volume.set_hexpand(True);self.volume.connect('value-changed',self._volume_changed);self.volume_label=Gtk.Label(label=self._t('75%'));volume_row.append(self.volume);volume_row.append(self.volume_label);left.append(volume_row)
        listcol=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);listcol.set_size_request(400,-1)
        for prop,val in [('margin_top',22),('margin_bottom',20),('margin_start',4),('margin_end',22)]:setattr(listcol,'set_'+prop,val)
        listcol.add_css_class('playlist-panel');content.append(listcol)
        phead=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8);ptitle=Gtk.Label(label=self._t('Wiedergabeliste'),xalign=0);ptitle.add_css_class('section-title');phead.append(ptitle);sp=Gtk.Box();sp.set_hexpand(True);phead.append(sp)
        self.count_label=Gtk.Label(label=self._t('0 Titel'));self.count_label.add_css_class('muted');phead.append(self.count_label);listcol.append(phead)
        searchrow=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=6);self.search=Gtk.SearchEntry();self.search.set_placeholder_text(self._t('Playlist durchsuchen…'));self.search.connect('search-changed',self._filter_playlist);self.search.set_hexpand(True);searchrow.append(self.search)
        self.return_mp3_button=Gtk.Button(label=self._t('Zur MP3-Bibliothek'));self.return_mp3_button.set_tooltip_text(self._t('CD-Modus verlassen und die vorherige MP3-Playlist wiederherstellen'));self.return_mp3_button.set_visible(False);self.return_mp3_button.connect('clicked',self._return_to_mp3_library);searchrow.append(self.return_mp3_button)
        saveb=Gtk.Button(label=self._t('Speichern'));saveb.connect('clicked',self._save_playlist_dialog);loadb=Gtk.Button(label=self._t('Laden'));loadb.connect('clicked',self._load_playlist_dialog);searchrow.append(saveb);searchrow.append(loadb);listcol.append(searchrow)
        self.listbox=Gtk.ListBox();self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE);self.listbox.add_css_class('track-list');self.listbox.connect('row-activated',self._row_activated)
        scroll=Gtk.ScrolledWindow();scroll.set_child(self.listbox);scroll.set_vexpand(True);listcol.append(scroll)
        rowbuttons=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=6)
        rem=Gtk.Button(label=self._t('Aus Playlist entfernen'));rem.connect('clicked',self._remove_selected);clear=Gtk.Button(label=self._t('Leeren'));clear.connect('clicked',self._clear_playlist);rowbuttons.append(rem);rowbuttons.append(clear);listcol.append(rowbuttons)
        self.status=Gtk.Label(label=self._t('Bereit'),xalign=0);self.status.add_css_class('status');root.append(self.status)
        css=Gtk.CssProvider();css.load_from_path(str(Path(__file__).parent/'style.css'));Gtk.StyleContext.add_provider_for_display(self.get_display(),css,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _file_dialog(self,title,action,callback,multiple=False,filters=True):
        dialog=Gtk.FileChooserNative.new(self._t(title),self,action,self._t('Auswählen'),self._t('Abbrechen'))
        if multiple:dialog.set_select_multiple(True)
        if filters:
            filt=Gtk.FileFilter();filt.set_name(AUDIO_FILTER_LABEL)
            for pat in ('*.mp3','*.MP3','*.wav','*.WAV','*.ogg','*.OGG','*.oga','*.OGA','*.m4a','*.M4A','*.mp4','*.MP4'):filt.add_pattern(pat)
            dialog.add_filter(filt)
        dialog.connect('response',callback);dialog.show()
    def _choose_files(self,*_):self._file_dialog('Musikdateien hinzufügen',Gtk.FileChooserAction.OPEN,self._files_chosen,True)
    def _files_chosen(self,dialog,response):
        if response==Gtk.ResponseType.ACCEPT:
            paths=[f.get_path() for f in dialog.get_files() if f.get_path()];added=self.playlist.add_paths(paths);self._refresh_playlist()
            self._set_status(f'{added} Audiodatei(en) hinzugefügt')
            if self.playlist.current() and self.engine and not self.engine.current_path:self._play_path(self.playlist.current())
        dialog.destroy()
    def _choose_videos(self, *_):
        dialog = Gtk.FileChooserNative.new(self._t("Videodateien öffnen"), self, Gtk.FileChooserAction.OPEN, self._t("Abspielen"), self._t("Abbrechen"))
        dialog.set_select_multiple(True)
        filt = Gtk.FileFilter(); filt.set_name(VIDEO_FILTER_LABEL)
        for ext in sorted(VIDEO_EXTENSIONS):
            filt.add_pattern("*" + ext); filt.add_pattern("*" + ext.upper())
        dialog.add_filter(filt)
        dialog.connect("response", self._videos_chosen); dialog.show()

    def _videos_chosen(self, dialog, response):
        if response == Gtk.ResponseType.ACCEPT:
            paths = [f.get_path() for f in dialog.get_files() if f.get_path()]
            try:
                proc = play_video(paths)
                self._set_status(f"VLC gestartet: {len(paths)} Video(s) · PID {proc.pid}")
            except Exception as exc:
                self._set_status(f"Video-Wiedergabe fehlgeschlagen: {exc}")
        dialog.destroy()

    def _disc_dialog(self, *_):
        dialog = Gtk.Dialog(title=self._t("DVD / Blu-ray abspielen"), transient_for=self, modal=True)
        dialog.add_button(self._t("Abbrechen"), Gtk.ResponseType.CANCEL)
        dialog.add_button(self._t("Abspielen"), Gtk.ResponseType.ACCEPT)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(14); box.set_margin_bottom(14); box.set_margin_start(14); box.set_margin_end(14)
        kind = Gtk.ComboBoxText(); kind.append("dvd", "DVD"); kind.append("bluray", "Blu-ray"); kind.set_active_id("dvd")
        device = Gtk.Entry(); device.set_text("/dev/sr0"); device.set_placeholder_text("/dev/sr0")
        box.append(Gtk.Label(label=self._t("Disc-Typ"), xalign=0)); box.append(kind)
        box.append(Gtk.Label(label=self._t("Optisches Laufwerk"), xalign=0)); box.append(device)
        note = Gtk.Label(label=self._t("Blu-ray-Wiedergabe hängt von VLC, libbluray und dem Disc-Schutz ab."), xalign=0, wrap=True); note.add_css_class("dim-label"); box.append(note)
        dialog.get_content_area().append(box)
        def response(d, result):
            if result == Gtk.ResponseType.ACCEPT:
                try:
                    proc = play_disc(kind.get_active_id(), device.get_text().strip() or "/dev/sr0")
                    self._set_status(f"VLC für {kind.get_active_text()} gestartet · PID {proc.pid}")
                except Exception as exc:
                    self._set_status(f"Disc-Wiedergabe fehlgeschlagen: {exc}")
            d.destroy()
        dialog.connect("response", response); dialog.present()

    def _load_default_music_folder(self):
        # Use a previously selected folder if it still exists; otherwise discover Musik/Music.
        saved = self.settings.get('music_folder') or self.settings.get('last_folder')
        folder = saved if saved and Path(saved).is_dir() else find_default_music_folder()
        self.settings['music_folder'] = folder
        self.settings['last_folder'] = folder
        paths = scan_folder(folder)
        self.playlist.add_paths(paths)
        self._refresh_playlist()
        if paths:
            self._set_status(f'Musikordner: {folder} · {len(paths)} Titel gefunden')
            if self.engine and not self.engine.current_path:
                self._play_path(self.playlist.current())
        else:
            self._set_status(f'Musikordner: {folder} · Noch keine unterstützten Audiodateien gefunden')

    def _choose_folder(self,*_):
        start = self.settings.get('music_folder') or find_default_music_folder()
        self._file_dialog('Musikordner auswählen',Gtk.FileChooserAction.SELECT_FOLDER,self._folder_chosen,False,False)
    def _folder_chosen(self,dialog,response):
        if response==Gtk.ResponseType.ACCEPT:
            folder=dialog.get_file().get_path()
            paths=scan_folder(folder)
            self.playlist=Playlist()
            added=self.playlist.add_paths(paths)
            self.settings['last_folder']=folder
            self.settings['music_folder']=folder
            save_settings(self.settings)
            self._refresh_playlist()
            self._set_status(f'Musikordner gesetzt: {folder} · {added} Audiodatei(en)')
            if self.playlist.current() and self.engine:
                self._play_path(self.playlist.current())
        dialog.destroy()
    def _refresh_playlist(self):
        child=self.listbox.get_first_child()
        while child:
            nxt=child.get_next_sibling();self.listbox.remove(child);child=nxt
        query=self.search.get_text().casefold() if hasattr(self,'search') else ''
        for i,path in enumerate(self.playlist.items):
            if path.startswith('cdda://'):
                try:
                    dev, track_text = path[len('cdda://'):].rsplit('#', 1); number=int(track_text)
                except Exception:
                    dev, number = '/dev/sr0', i + 1
                cdmeta=self.cd_playlist_meta.get(path, {})
                titles=cdmeta.get('tracks', [])
                title=(titles[number-1] if number <= len(titles) and titles[number-1] else f'Audio-CD · Track {number:02d}')
                artist=' — '.join(x for x in (cdmeta.get('artist',''),cdmeta.get('album','')) if x) or 'Audio-CD'
            else:
                meta=read_metadata(path);title=meta.get('title') or Path(path).stem;artist=meta.get('artist') or Path(path).suffix[1:].upper()
            if query and query not in (title+' '+artist+' '+path).casefold():continue
            rb=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=3);rb.set_margin_top(9);rb.set_margin_bottom(9);rb.set_margin_start(12);rb.set_margin_end(12)
            t=Gtk.Label(label=title,xalign=0);t.add_css_class('row-title');t.set_ellipsize(Pango.EllipsizeMode.END);a=Gtk.Label(label=artist,xalign=0);a.add_css_class('muted');a.set_ellipsize(Pango.EllipsizeMode.END);rb.append(t);rb.append(a)
            row=Gtk.ListBoxRow();row.set_child(rb);row.set_activatable(True);row.set_tooltip_text(path);row._playlist_index=i;self.listbox.append(row)
        self.count_label.set_text(f"{len(self.playlist.items)} {self._t('Titel')}")
    def _filter_playlist(self,*_):self._refresh_playlist()
    def _row_activated(self,listbox,row):self._play_path(self.playlist.select(getattr(row,'_playlist_index',row.get_index())))
    def _return_to_mp3_library(self, *_):
        """Stop CD playback and restore the untouched MP3 playlist."""
        if self.engine:
            self.engine.stop()
        self.cd_queue = None
        self.cd_queue_index = 0
        if self._mp3_playlist_snapshot is not None:
            items, index = self._mp3_playlist_snapshot
            self.playlist = Playlist()
            self.playlist.items = list(items)
            self.playlist.index = index if 0 <= index < len(items) else (-1 if not items else 0)
        self._mp3_playlist_snapshot = None
        self._cd_playlist_mode = False
        self.return_mp3_button.set_visible(False)
        self.play_button.set_label('▶')
        self.elapsed.set_text(self._t('0:00')); self.total.set_text(self._t('0:00'))
        self.seek.set_range(0, 1); self.seek.set_value(0); self.seek.set_sensitive(True)
        self.track_title.set_text(self._t('MP3-Bibliothek'))
        self.artist_label.set_text(self._t('Wähle einen Titel aus deiner Wiedergabeliste'))
        self.cover_stack.set_visible_child_name('fallback')
        self._refresh_playlist()
        self._set_status(self._t('Zur MP3-Bibliothek zurückgekehrt · Wiedergabe gestoppt'))

    def _enter_cd_playlist(self, dev, count, meta=None, selected_track=1):
        """Show only the CD tracks while in CD mode; preserve the MP3 playlist."""
        if not self._cd_playlist_mode:
            self._mp3_playlist_snapshot = (list(self.playlist.items), self.playlist.index)
        meta = dict(meta or {})
        virtual_tracks = [f'cdda://{dev}#{n}' for n in range(1, count + 1)]
        for virtual in virtual_tracks:
            self.cd_playlist_meta[virtual] = meta
        self.playlist = Playlist()
        self.playlist.items = virtual_tracks
        self.playlist.index = max(0, min(selected_track - 1, len(virtual_tracks) - 1)) if virtual_tracks else -1
        self._cd_playlist_mode = True
        self.return_mp3_button.set_visible(True)
        self.cd_queue = None
        self._refresh_playlist()

    def _play_path(self,path):
        if not path or not self.engine:return
        try:
            self.cd_queue = None
            if path.startswith('cdda://'):
                dev, track_text = path[len('cdda://'):].rsplit('#', 1); number=int(track_text)
                self.engine.play_cd_track(dev, number)
                self._show_metadata(path)
                self.play_button.set_label('Ⅱ'); self.seek.set_sensitive(False); self._set_status(f'Audio-CD · Track {number}')
            else:
                self.engine.load(path);self.engine.play();self.play_button.set_label('Ⅱ');self.seek.set_sensitive(True);self._show_metadata(path);self._set_status(self._t('Wiedergabe'))
            self._refresh_playlist()
            row=self.listbox.get_first_child()
            while row is not None and getattr(row, '_playlist_index', -1) != self.playlist.index:
                row = row.get_next_sibling()
            if row:self.listbox.select_row(row)
        except Exception as exc:self._on_error(str(exc),'')
    def _show_metadata(self,path):
        if path.startswith('cdda://'):
            try:
                dev, track_text = path[len('cdda://'):].rsplit('#', 1); number=int(track_text)
            except Exception: dev, number='/dev/sr0', 1
            meta=self.cd_playlist_meta.get(path, {})
            titles=meta.get('tracks', [])
            self.track_title.set_text(titles[number-1] if number <= len(titles) and titles[number-1] else f'Audio-CD · Track {number:02d}')
            self.artist_label.set_text(' — '.join(x for x in (meta.get('artist',''),meta.get('album','')) if x) or dev)
            data=meta.get('cover_bytes')
        else:
            meta=read_metadata(path);self.track_title.set_text(meta.get('title') or Path(path).stem);self.artist_label.set_text(meta.get('artist') or Path(path).suffix[1:].upper())
            data=read_cover_bytes(path)
        try:
            if data:
                tex=Gdk.Texture.new_from_bytes(GLib.Bytes.new(data));self.cover_picture.set_paintable(tex);self.cover_stack.set_visible_child_name('picture')
            else:self.cover_stack.set_visible_child_name('fallback')
        except Exception:self.cover_stack.set_visible_child_name('fallback')
    def _stop_playback(self,*_):
        if self.engine:
            self.engine.stop()
        self.play_button.set_label('▶')
        self.elapsed.set_text(self._t('0:00'))
        self.total.set_text(self._t('0:00'))
        self.seek.set_range(0, 1)
        self.seek.set_value(0)
        self.seek.set_sensitive(True)
        self._set_status(self._t('Wiedergabe gestoppt'))

    def _toggle_play(self,*_):
        if not self.engine:return
        if not self.engine.current_path:self._play_path(self.playlist.current());return
        from gi.repository import Gst
        state=(self.engine.cd_pipeline.get_state(0).state if self.engine.cd_pipeline else self.engine.playbin.get_state(0).state)
        if state==Gst.State.PLAYING:self.engine.pause();self.play_button.set_label('▶')
        else:self.engine.play();self.play_button.set_label('Ⅱ')
    def _volume_changed(self,scale):
        value=scale.get_value()/100.;self.settings['volume']=value
        if self.engine:self.engine.set_volume(value)
        self._update_volume_label()
        # Persist immediately so the chosen volume survives a crash or power-off.
        save_settings(self.settings)
    def _update_volume_label(self):
        if hasattr(self,'volume_label'):self.volume_label.set_text(f'{int(self.settings.get("volume",.75)*100)}%')
        if self.engine:self.engine.set_volume(self.settings.get('volume',.75))
    def _seek(self,scale,scroll_type,value):
        if self.engine and self.engine.current_path and not str(self.engine.current_path).startswith('CD Track'):
            self.engine.seek_seconds(value)
        return True
    def _tick(self):
        if self.engine and self.engine.current_path and not str(self.engine.current_path).startswith('CD Track'):
            pos=self.engine.position_seconds();dur=self.engine.duration_seconds();self.elapsed.set_text(fmt_time(pos));self.total.set_text(fmt_time(dur))
            self.seek.set_range(0,max(1,dur));self.seek.set_value(min(pos,max(1,dur)))
        return True
    def _on_eos(self):
        if self.cd_queue:
            def next_cd_track():
                queue = self.cd_queue
                if not queue: return False
                if self.cd_queue_index < queue['count']:
                    self.cd_queue_index += 1
                    try:
                        self.engine.play_cd_track(queue['device'], self.cd_queue_index)
                        meta = queue.get('meta') or {}
                        titles = meta.get('tracks', [])
                        n = self.cd_queue_index
                        self.track_title.set_text(titles[n-1] if n <= len(titles) and titles[n-1] else f'Audio-CD · Track {n:02d}')
                        self.artist_label.set_text(' — '.join(x for x in (meta.get('artist',''), meta.get('album','')) if x) or queue['device'])
                        self._set_status(f'Audio-CD-Wiedergabe · Track {n} von {queue["count"]}')
                    except Exception as exc:
                        self.cd_queue = None; self._set_status(f'CD-Folge-Wiedergabe fehlgeschlagen: {exc}')
                else:
                    self.cd_queue = None; self._set_status(self._t('Audio-CD vollständig abgespielt.'))
                return False
            GLib.idle_add(next_cd_track)
        else:
            GLib.idle_add(lambda:(self._play_path(self.playlist.next()),False)[1])
    def _on_error(self,error,debug):GLib.idle_add(self._set_status,f'Wiedergabefehler: {error}')
    def _set_status(self,text):
        if self.settings.get("language", "de") == "en":
            # Translate common dynamic status messages while preserving file paths, counts and errors.
            for source, target in (("Musikordner: ", "Music folder: "), ("Musikordner gesetzt: ", "Music folder set: "), ("Audiogerät nicht verfügbar: ", "Audio device unavailable: "), ("Audiogerät konnte nicht ausgewählt werden: ", "Could not select audio device: "), ("Audio-CD · Track ", "Audio CD · Track "), ("Wiedergabe gestoppt", "Playback stopped"), ("Playlist geleert", "Playlist cleared"), ("Playlist gespeichert", "Playlist saved"), ("Metadaten gespeichert", "Metadata saved"), ("Fehler beim Laden:", "Could not load:"), ("Fehler beim Speichern:", "Could not save:"), ("Metadaten konnten nicht gespeichert werden:", "Could not save metadata:"), ("CD-Wiedergabe fehlgeschlagen:", "CD playback failed:")):
                if text.startswith(source):
                    text = target + text[len(source):]
                    break
        self.status.set_text(self._t(text))
    def _remove_selected(self,*_):
        row=self.listbox.get_selected_row()
        if row:self.playlist.remove(getattr(row,'_playlist_index',row.get_index()));self._refresh_playlist()
    def _clear_playlist(self,*_):self.playlist=Playlist();self._refresh_playlist();self._set_status(self._t('Playlist geleert'))
    def _save_playlist_dialog(self,*_):self._file_dialog('Playlist speichern',Gtk.FileChooserAction.SAVE,self._save_playlist_response,False,False)
    def _save_playlist_response(self,dialog,response):
        if response==Gtk.ResponseType.ACCEPT:
            path=dialog.get_file().get_path()
            if not path.endswith('.m3u'):path+='.m3u'
            try:self.playlist.save_m3u(path);self._set_status(self._t('Playlist gespeichert'))
            except Exception as exc:self._set_status(f'Fehler beim Speichern: {exc}')
        dialog.destroy()
    def _load_playlist_dialog(self,*_):self._file_dialog('Playlist laden',Gtk.FileChooserAction.OPEN,self._load_playlist_response,False,False)
    def _load_playlist_response(self,dialog,response):
        if response==Gtk.ResponseType.ACCEPT:
            try:n=self.playlist.load_m3u(dialog.get_file().get_path());self._refresh_playlist();self._set_status(f'{n} Titel aus Playlist geladen')
            except Exception as exc:self._set_status(f'Fehler beim Laden: {exc}')
        dialog.destroy()
    def _edit_tags_dialog(self,*_):
        row=self.listbox.get_selected_row()
        if not row:self._set_status(self._t('Bitte zuerst einen Titel in der Playlist auswählen.'));return
        path=self.playlist.items[getattr(row,'_playlist_index',row.get_index())];meta=read_metadata(path)
        dialog=Gtk.Dialog(title=self._t('ID3-Tags bearbeiten'),transient_for=self,modal=True);dialog.add_button(self._t('Abbrechen'),Gtk.ResponseType.CANCEL);dialog.add_button(self._t('Speichern'),Gtk.ResponseType.ACCEPT)
        grid=Gtk.Grid(column_spacing=12,row_spacing=10);grid.set_margin_top(18);grid.set_margin_bottom(18);grid.set_margin_start(18);grid.set_margin_end(18)
        fields=[('title','Titel'),('artist','Interpret'),('album','Album'),('date','Jahr'),('genre','Genre'),('tracknumber','Tracknummer')];entries={}
        for i,(key,label) in enumerate(fields):
            grid.attach(Gtk.Label(label=label,xalign=0),0,i,1,1);e=Gtk.Entry();e.set_text(meta.get(key,''));e.set_hexpand(True);grid.attach(e,1,i,1,1);entries[key]=e
        dialog.get_content_area().append(grid)
        def response(d,r):
            if r==Gtk.ResponseType.ACCEPT:
                try:write_metadata(path,{k:e.get_text() for k,e in entries.items()});self._show_metadata(path);self._refresh_playlist();self._set_status(self._t('Metadaten gespeichert'))
                except Exception as exc:self._set_status(f'Metadaten konnten nicht gespeichert werden: {exc}')
            d.destroy()
        dialog.connect('response',response);dialog.present()
    def _equalizer_dialog(self,*_):
        if not self.engine or not self.engine.equalizer_available:
            self._set_status(self._t('Equalizer nicht verfügbar: GStreamer-Equalizer-Plugin installieren.'))
            return
        dialog=Gtk.Dialog(title=self._t('LunaPlayer Equalizer'),transient_for=self,modal=True)
        dialog.set_default_size(720, 440)
        dialog.add_button(self._t('Schließen'),Gtk.ResponseType.CLOSE)
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10)
        box.set_margin_top(16);box.set_margin_bottom(16);box.set_margin_start(18);box.set_margin_end(18)
        box.append(Gtk.Label(label=self._t('Klangprofil'),xalign=0))
        profiles=dict(PRESETS)
        profiles.update(self.settings.get('equalizer_profiles', {}))
        # Keep the dropdown in sync with the last-used profile. If the user
        # had adjusted sliders manually, show the dedicated custom entry.
        current_name=self.settings.get('equalizer_preset', 'Neutral')
        if current_name == 'Benutzerdefiniert' and current_name not in profiles:
            profiles[current_name]=list(self.settings.get('equalizer_bands', [0]*10))
        names=list(profiles)
        preset=Gtk.DropDown.new_from_strings(names)
        preset.set_selected(names.index(current_name) if current_name in names else 0)
        box.append(preset)
        # Keep profile actions near the top so they remain visible on small screens.
        controls=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        save_button=Gtk.Button(label=self._t('Eigenes Profil speichern…'))
        reset_button=Gtk.Button(label=self._t('Standardwerte'))
        delete_button=Gtk.Button(label=self._t('Eigenes Profil löschen'))
        controls.append(save_button);controls.append(reset_button);controls.append(delete_button);box.append(controls)
        grid=Gtk.Grid(column_spacing=10,row_spacing=8);box.append(grid)
        bands=self.engine._eq_bands
        sliders=[]
        saved_bands=self.settings.get('equalizer_bands', [0]*bands)
        labels=['Bass','Bass+','Tiefmitten','Mitten','Mitten+','Präsenz','Höhen','Höhen+','Brillanz','Luft']
        for i in range(bands):
            col=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
            scale=Gtk.Scale.new_with_range(Gtk.Orientation.VERTICAL,-12,12,1)
            scale.set_inverted(True);scale.set_size_request(34,125);scale.set_draw_value(False)
            scale.set_value(float(saved_bands[i]) if i<len(saved_bands) else 0)
            scale.set_tooltip_text(labels[i] if i<len(labels) else f'Band {i+1}')
            scale.connect('value-changed',lambda widget,idx=i:self._equalizer_band_changed(idx,widget.get_value(),sliders))
            col.append(scale)
            col.append(Gtk.Label(label=labels[i] if i<len(labels) else f'{i+1}'))
            grid.attach(col,i,0,1,1);sliders.append(scale)
        def apply_profile(name):
            values=profiles.get(name, [0]*bands)
            for i,slider in enumerate(sliders):
                slider.set_value(float(values[i]) if i<len(values) else 0)
            self.settings['equalizer_preset']=name
            self.settings['equalizer_bands']=[int(round(slider.get_value())) for slider in sliders]
            save_settings(self.settings)
            self._set_status(f'Klangprofil: {name}')
        def preset_changed(dd,*_):
            idx=dd.get_selected()
            if idx < len(names): apply_profile(names[idx])
        preset.connect('notify::selected',preset_changed)
        def save_profile(*_):
            name_dialog=Gtk.Dialog(title=self._t('Klangprofil speichern'),transient_for=dialog,modal=True)
            name_dialog.add_button(self._t('Abbrechen'),Gtk.ResponseType.CANCEL)
            name_dialog.add_button(self._t('Speichern'),Gtk.ResponseType.ACCEPT)
            entry=Gtk.Entry();entry.set_placeholder_text(self._t('Name des Klangprofils'));entry.set_hexpand(True)
            entry.set_margin_top(12);entry.set_margin_bottom(12);entry.set_margin_start(12);entry.set_margin_end(12)
            name_dialog.get_content_area().append(entry)
            def response(d,response_id):
                name=entry.get_text().strip()
                if response_id==Gtk.ResponseType.ACCEPT and name:
                    values=[int(round(slider.get_value())) for slider in sliders]
                    custom=self.settings.setdefault('equalizer_profiles', {})
                    custom[name]=values
                    self.settings['equalizer_bands']=values
                    self.settings['equalizer_preset']=name
                    save_settings(self.settings)
                    if name not in names:
                        names.append(name);profiles[name]=values
                        preset.set_model(Gtk.StringList.new(names))
                    preset.set_selected(names.index(name))
                    self._set_status(f'Klangprofil „{name}“ gespeichert')
                d.destroy()
            name_dialog.connect('response',response);name_dialog.present()
        save_button.connect('clicked',save_profile)
        def reset_profile_defaults(*_):
            # Built-in presets always return to their factory values, even if
            # the user previously adjusted their sliders. For custom profiles,
            # restore the last saved version of that profile.
            idx=preset.get_selected()
            name=names[idx] if idx < len(names) else 'Neutral'
            if name in PRESETS:
                values=list(PRESETS[name])
            elif name in self.settings.get('equalizer_profiles', {}):
                values=list(self.settings['equalizer_profiles'][name])
            else:
                values=[0]*bands
            for i,slider in enumerate(sliders):
                slider.set_value(float(values[i]) if i<len(values) else 0)
            self.settings['equalizer_preset']=name
            self.settings['equalizer_bands']=[int(round(slider.get_value())) for slider in sliders]
            save_settings(self.settings)
            self._set_status(f'Standardwerte für Klangprofil „{name}“ wiederhergestellt')
        reset_button.connect('clicked',reset_profile_defaults)
        def delete_profile(*_):
            idx=preset.get_selected()
            name=names[idx] if idx < len(names) else 'Neutral'
            custom=self.settings.get('equalizer_profiles', {})
            if name not in custom:
                self._set_status(self._t('Nur eigene Klangprofile können gelöscht werden'))
                return
            del custom[name]
            names.remove(name); profiles.pop(name, None)
            self.settings['equalizer_profiles']=custom
            fallback='Neutral'
            self.settings['equalizer_preset']=fallback
            self.settings['equalizer_bands']=list(PRESETS[fallback])
            save_settings(self.settings)
            preset.set_model(Gtk.StringList.new(names))
            preset.set_selected(names.index(fallback) if fallback in names else 0)
            for i,slider in enumerate(sliders):
                slider.set_value(float(PRESETS[fallback][i] if i < len(PRESETS[fallback]) else 0))
            self._set_status(f'Eigenes Klangprofil „{name}“ gelöscht')
        delete_button.connect('clicked',delete_profile)
        dialog.get_content_area().append(box)
        dialog.connect('response',lambda d,r:d.destroy());dialog.present()

    def _equalizer_band_changed(self,index,value,sliders):
        if self.engine:
            self.engine.set_equalizer_band(index,value)
        self.settings['equalizer_bands']=[int(round(slider.get_value())) for slider in sliders]
        self.settings['equalizer_preset']='Benutzerdefiniert'
        save_settings(self.settings)

    def _cd_dialog(self,*_):
        dialog=Gtk.Dialog(title=self._t('Audio-CD erkennen und abspielen'),transient_for=self,modal=True)
        dialog.add_button(self._t('Abbrechen'),Gtk.ResponseType.CANCEL)
        dialog.add_button(self._t('Track abspielen'),Gtk.ResponseType.ACCEPT)
        dialog.add_button(self._t('CD abspielen (alle Tracks)'),Gtk.ResponseType.APPLY)
        dialog.set_default_size(600,380)
        grid=Gtk.Grid(column_spacing=10,row_spacing=10)
        grid.set_margin_top(18);grid.set_margin_bottom(18);grid.set_margin_start(18);grid.set_margin_end(18)
        grid.attach(Gtk.Label(label=self._t('CD-Laufwerk'),xalign=0),0,0,1,1)
        drives=AudioCD.discover_drives()
        saved_device=self.settings.get('cd_device','/dev/sr0')
        if saved_device not in drives and Path(saved_device).exists(): drives.insert(0,saved_device)
        if not drives: drives=[saved_device]
        device=Gtk.ComboBoxText()
        for drive in drives: device.append_text(drive)
        device.set_active(max(0,drives.index(saved_device) if saved_device in drives else 0))
        grid.attach(device,1,0,1,1)
        detect_button=Gtk.Button(label=self._t('CD erkennen'))
        grid.attach(detect_button,2,0,1,1)
        grid.attach(Gtk.Label(label=self._t('Tracknummer (Einzeltrack)'),xalign=0),0,1,1,1)
        track=Gtk.SpinButton.new_with_range(1,99,1);track.set_value(1);grid.attach(track,1,1,1,1)
        cover_buttons=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        choose_online=Gtk.Button(label=self._t('Online-Cover auswählen'))
        choose_local=Gtk.Button(label=self._t('Eigenes Cover laden…'))
        cover_buttons.append(choose_online); cover_buttons.append(choose_local)
        grid.attach(cover_buttons,0,4,3,1)
        info=Gtk.Label(label=self._t('CD-Erkennung wird beim Klick auf „CD erkennen“ ausgeführt.'),wrap=True,xalign=0)
        cd_metadata = {'data': None, 'device': None, 'cover_bytes': None, 'cover_candidates': []}
        grid.attach(info,0,2,3,1)
        eject_button=Gtk.Button(label=self._t('CD auswerfen'))
        grid.attach(eject_button,0,3,1,1)
        refresh_button=Gtk.Button(label=self._t('Laufwerke suchen'))
        grid.attach(refresh_button,1,3,1,1)
        dialog.get_content_area().append(grid)

        def selected_device():
            return device.get_active_text() or saved_device
        def detect(*_):
            dev=selected_device()
            ok,count,message=AudioCD.inspect(dev)
            info.set_text(message)
            track.set_range(1,max(1,count))
            track.set_sensitive(ok)
            dialog.set_response_sensitive(Gtk.ResponseType.ACCEPT,ok)
            cd_metadata['data'] = None
            cd_metadata['device'] = dev
            if ok:
                self.settings['cd_device']=dev
                info.set_text(message + '\nSuche Album- und Titeldaten bei GNUDB, danach MusicBrainz …')
                detect_button.set_sensitive(False)
                def lookup_worker():
                    try:
                        result = lookup_cd(dev, self.settings)
                        GLib.idle_add(metadata_ready, result, None)
                    except Exception as exc:
                        GLib.idle_add(metadata_ready, None, str(exc))
                threading.Thread(target=lookup_worker, daemon=True).start()
        def metadata_ready(result, error):
            detect_button.set_sensitive(True)
            if result:
                cd_metadata['data'] = result
                title = result.get('album') or 'Album unbekannt'
                artist = result.get('artist') or 'Interpret unbekannt'
                info.set_text(f"{AudioCD.inspect(cd_metadata['device'])[2]}\n{result['provider']}: {artist} — {title}" + (f" ({result['year']})" if result.get('year') else ""))
                cd_metadata['cover_candidates'] = result.get('cover_candidates', [])
                cover_bytes = result.get('cover_bytes')
                if cover_bytes:
                    # Keep the lookup result scoped to this CD dialog. Do not
                    # replace the cover currently chosen for the MP3 library:
                    # metadata lookup runs asynchronously and may finish seconds
                    # after the user has selected a different/custom cover.
                    cd_metadata['cover_bytes'] = cover_bytes
                elif result.get('cover_error'):
                    info.set_text(info.get_text() + '\nCover-Suche: ' + result['cover_error'])
            else:
                info.set_text(f"Audio-CD erkannt, aber keine CDDB-Metadaten gefunden.\n{error or ''}")
            return False
        def refresh(*_):
            found=AudioCD.discover_drives()
            if not found:
                info.set_text(self._t('Keine optischen Laufwerke unter /dev/sr* oder /dev/cdrom gefunden.'))
                return
            device.remove_all()
            for drive in found:device.append_text(drive)
            device.set_active(0)
            info.set_text(f'{len(found)} Laufwerk(e) gefunden. Lege eine Audio-CD ein und klicke „CD erkennen“.')
        def eject(*_):
            try:
                AudioCD(selected_device()).eject()
                info.set_text(self._t('Auswerfen angefordert.'))
            except Exception as exc:info.set_text(f'Auswerfen fehlgeschlagen: {exc}')
        def choose_online_cover_cb(*_):
            candidates = cd_metadata.get('cover_candidates') or []
            if not candidates:
                data = cd_metadata.get('cover_bytes')
                if data:
                    try:
                        self.cover_picture.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(data)))
                        self.cover_stack.set_visible_child_name('picture')
                        self._set_status(self._t('Online-Cover ausgewählt.'))
                    except Exception as exc: info.set_text(f'Cover konnte nicht angezeigt werden: {exc}')
                else:
                    info.set_text(self._t('Kein Online-Cover gefunden. Bitte CD erkennen und auf eine funktionierende Internetverbindung achten; alternativ eigenes Bild laden.'))
                return
            labels=[]
            for c in candidates:
                label=self._t(' — ').join(x for x in (c.get('artist',''),c.get('title',''),c.get('date','')) if x)
                labels.append(label or c.get('release_id','MusicBrainz-Release'))
            chooser=Gtk.Dialog(title=self._t('Online-Cover auswählen'),transient_for=self,modal=True)
            chooser.add_button(self._t('Abbrechen'),Gtk.ResponseType.CANCEL);chooser.add_button(self._t('Cover übernehmen'),Gtk.ResponseType.ACCEPT)
            chooser.set_default_size(520,130)
            box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=10);box.set_margin_top(16);box.set_margin_bottom(16);box.set_margin_start(16);box.set_margin_end(16)
            box.append(Gtk.Label(label=self._t('Gefundene Veröffentlichungen (Cover Art Archive):'),xalign=0))
            dropdown=Gtk.DropDown.new_from_strings(labels);dropdown.set_hexpand(True);box.append(dropdown);chooser.get_content_area().append(box)
            def selected(dlg, response_id):
                if response_id==Gtk.ResponseType.ACCEPT:
                    idx=dropdown.get_selected()
                    if idx < len(candidates):
                        chosen=candidates[idx];data=chosen['cover_bytes'];cd_metadata['cover_bytes']=data
                        try:
                            self.cover_picture.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(data)));self.cover_stack.set_visible_child_name('picture')
                            info.set_text('Online-Cover ausgewählt: '+labels[idx]);self._set_status(self._t('Online-Cover ausgewählt.'))
                        except Exception as exc:info.set_text(f'Cover konnte nicht angezeigt werden: {exc}')
                dlg.destroy()
            chooser.connect('response',selected);chooser.present()
        def choose_local_cover_cb(*_):
            chooser = Gtk.FileChooserNative.new('Eigenes Cover-Bild auswählen', self, Gtk.FileChooserAction.OPEN, 'Öffnen', 'Abbrechen')
            filt = Gtk.FileFilter(); filt.set_name('Bilder (JPEG, PNG, WebP)')
            for pattern in ('*.jpg','*.jpeg','*.png','*.webp','*.JPG','*.JPEG','*.PNG','*.WEBP'): filt.add_pattern(pattern)
            chooser.add_filter(filt)
            def picked(dlg, response_id):
                if response_id == Gtk.ResponseType.ACCEPT:
                    f = dlg.get_file()
                    try:
                        path = Path(f.get_path()) if f and f.get_path() else None
                        if path and path.is_file() and path.stat().st_size <= 20*1024*1024:
                            data = path.read_bytes(); self.cover_picture.set_paintable(Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))); self.cover_stack.set_visible_child_name('picture'); cd_metadata['cover_bytes'] = data
                            info.set_text(f'Eigenes Cover ausgewählt: {path.name}')
                        else: info.set_text(self._t('Cover-Datei ist ungültig oder größer als 20 MB.'))
                    except Exception as exc: info.set_text(f'Cover konnte nicht geladen werden: {exc}')
                dlg.destroy()
            chooser.connect('response', picked); chooser.show()
        choose_online.connect('clicked', choose_online_cover_cb); choose_local.connect('clicked', choose_local_cover_cb)
        detect_button.connect('clicked',detect)
        refresh_button.connect('clicked',refresh)
        eject_button.connect('clicked',eject)
        dialog.set_response_sensitive(Gtk.ResponseType.ACCEPT,False)
        def response(d,r):
            if r in (Gtk.ResponseType.ACCEPT, Gtk.ResponseType.APPLY):
                dev=selected_device();number=1 if r == Gtk.ResponseType.APPLY else int(track.get_value())
                self.settings['cd_device']=dev
                try:
                    self.engine.play_cd_track(dev,number)
                    meta = cd_metadata.get('data') if cd_metadata.get('device') == dev else None
                    if r == Gtk.ResponseType.APPLY:
                        ok, count, msg = AudioCD.inspect(dev)
                        if not ok or count < 1: raise RuntimeError(msg)
                        if not meta:
                            meta = {'artist': '', 'album': '', 'tracks': [], 'cover_bytes': cd_metadata.get('cover_bytes')}
                        meta = dict(meta)
                        meta['cover_bytes'] = cd_metadata.get('cover_bytes') or meta.get('cover_bytes')
                        self._enter_cd_playlist(dev, count, meta, selected_track=1)
                        self.engine.play_cd_track(dev, 1)
                        self._show_metadata(f'cdda://{dev}#1')
                        number = 1
                    else:
                        ok, count, msg = AudioCD.inspect(dev)
                        if not ok or count < 1: raise RuntimeError(msg)
                        meta = cd_metadata.get('data') if cd_metadata.get('device') == dev else None
                        self._enter_cd_playlist(dev, count, meta, selected_track=number)
                    track_title = ''
                    if meta and number <= len(meta.get('tracks', [])):
                        track_title = meta['tracks'][number - 1]
                    album = meta.get('album', '') if meta else ''
                    artist = meta.get('artist', '') if meta else ''
                    self.track_title.set_text(track_title or f'Audio-CD · Track {number:02d}')
                    self.artist_label.set_text(' — '.join(x for x in (artist, album) if x) or dev)
                    self.play_button.set_label('Ⅱ')
                    self.seek.set_sensitive(False)
                    provider = f" · Metadaten: {meta['provider']}" if meta else ''
                    self._set_status((f'Audio-CD-Wiedergabe gestartet · Track 1 von {self.cd_queue["count"]}' if r == Gtk.ResponseType.APPLY else f'Audio-CD-Wiedergabe gestartet · {dev}, Track {number}') + provider)
                except Exception as exc:self._set_status(f'CD-Wiedergabe fehlgeschlagen: {exc}')
            d.destroy()
        dialog.connect('response',response);dialog.present()
    def _tray_toggle_changed(self, button):
        self._set_tray_enabled(button.get_active())

    def _set_tray_enabled(self, enabled, show_message=True):
        enabled = bool(enabled)
        command = "TRAY_ON" if enabled else "TRAY_OFF"
        if not send_command(command):
            enabled = False
            if self.tray_toggle.get_active():
                self.tray_toggle.set_active(False)
            if show_message:
                self._set_status(self._t("Tray-Steuerung ist nicht erreichbar. Bitte LunaPlayer neu starten."))
        self.settings['tray_enabled'] = enabled
        save_settings(self.settings)
        if show_message and enabled:
            self._set_status(self._t('System-Tray wird aktiviert …'))
        elif show_message:
            self._set_status(self._t('System-Tray deaktiviert. Schließen beendet LunaPlayer.'))
        return enabled

    def _tray_ready(self):
        self._set_status(self._t('System-Tray aktiviert. Beim Schließen bleibt LunaPlayer im Tray.'))

    def _tray_failed(self):
        self.settings['tray_enabled'] = False
        save_settings(self.settings)
        if self.tray_toggle.get_active():
            self.tray_toggle.set_active(False)
        self._set_status(self._t('System-Tray konnte nicht gestartet werden. Prüfe GTK 3 und die Desktop-Unterstützung.'))

    def _on_close(self,*_):
        self.settings['volume']=self.volume.get_value()/100.;save_settings(self.settings)
        if self.settings.get('tray_enabled', False) and not self._quitting:
            self.set_visible(False)
            self._set_status(self._t('LunaPlayer läuft im System-Tray weiter.'))
            return True
        self._quitting = True
        send_command("CHILD_QUIT")
        if self.engine:self.engine.close()
        return False
