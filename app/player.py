"""GStreamer playback engine for files, equalizer and direct CD tracks."""
import os
from urllib.parse import quote
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None)
class PlayerEngine:
    def __init__(self,on_eos=None,on_error=None):
        self.playbin=Gst.ElementFactory.make('playbin','lunaplayer')
        if not self.playbin: raise RuntimeError('GStreamer playbin fehlt; installiere gstreamer1.0-plugins-base.')
        self.on_eos=on_eos; self.on_error=on_error; self.current_path=None; self.cd_pipeline=None; self._volume=.75; self._eq=None; self._eq_bands=0
        self.bus=self.playbin.get_bus(); self.bus.add_signal_watch(); self.bus.connect('message',self._on_message)
        self.playbin.set_property('volume',self._volume)
        self._setup_equalizer()
        self.selected_audio_device = ''
    @staticmethod
    def list_audio_outputs():
        """Return current GStreamer audio output devices as (display_name, device)."""
        monitor = Gst.DeviceMonitor.new()
        monitor.add_filter("Audio/Sink", None)
        if not monitor.start():
            return []
        try:
            result = []
            for device in monitor.get_devices():
                name = device.get_display_name() or "Audiogerät"
                result.append((name, device))
            return result
        finally:
            monitor.stop()

    def set_audio_device(self, display_name):
        """Select an output device by its displayed name; empty means system default."""
        self.selected_audio_device = display_name or ''
        if not self.selected_audio_device:
            try:
                self.playbin.set_property('audio-sink', None)
            except Exception:
                pass
            return True
        for name, device in self.list_audio_outputs():
            if name == self.selected_audio_device:
                sink = device.create_element("lunaplayer-audio-sink")
                if sink is None:
                    raise RuntimeError(f"Audio-Ausgang „{name}“ konnte nicht geöffnet werden.")
                self.playbin.set_state(Gst.State.NULL)
                self.playbin.set_property('audio-sink', sink)
                return True
        raise RuntimeError(f"Das Audiogerät „{self.selected_audio_device}“ ist nicht mehr verfügbar.")

    def _make_audio_sink(self):
        if self.selected_audio_device:
            for name, device in self.list_audio_outputs():
                if name == self.selected_audio_device:
                    sink = device.create_element("lunaplayer-cd-audio-sink")
                    if sink is not None:
                        return sink
                    break
        return Gst.ElementFactory.make('autoaudiosink', 'sink')

    def _setup_equalizer(self):
        for factory in ('equalizer-10bands','equalizer-3bands'):
            eq=Gst.ElementFactory.make(factory,'lunaplayer-equalizer')
            if eq:
                self._eq=eq; self._eq_bands=10 if factory=='equalizer-10bands' else 3; self.playbin.set_property('audio-filter',eq); break
    @property
    def equalizer_available(self): return self._eq is not None
    def set_equalizer_band(self,band,value):
        if self._eq and 0 <= band < self._eq_bands:
            bands=self._eq_bands
            if bands == 10: self._eq.set_property(f'band{band}',float(value))
            elif bands == 3: self._eq.set_property(('band0','band1','band2')[band],float(value))
    def reset_equalizer(self):
        if not self._eq:return
        n=self._eq_bands
        for i in range(n):
            try:self._eq.set_property(f'band{i}',0.0)
            except Exception:
                try:self._eq.set_property(('band0','band1','band2')[i],0.0)
                except Exception:pass
    def _on_message(self,bus,msg):
        if msg.type==Gst.MessageType.EOS:
            if self.cd_pipeline: self.cd_pipeline.set_state(Gst.State.NULL); self.cd_pipeline=None
            if self.on_eos:self.on_eos()
        elif msg.type==Gst.MessageType.ERROR:
            err,debug=msg.parse_error()
            if self.on_error:self.on_error(str(err),debug or '')
    def _stop_cd(self):
        if self.cd_pipeline:
            self.cd_pipeline.set_state(Gst.State.NULL); self.cd_pipeline=None
    def load(self,path):
        self.stop(); self.current_path=path
        self.playbin.set_property('uri','file://'+quote(os.path.abspath(path)))
    def play_cd_track(self,device,track):
        self.stop(); self.current_path=f'CD Track {track}'
        source=Gst.ElementFactory.make('cdparanoiasrc','cdsource')
        if not source: raise RuntimeError('CDDA-Plugin fehlt. Installiere gstreamer1.0-plugins-good bzw. prüfe CDDA-Unterstützung.')
        if source.find_property('device'): source.set_property('device',device)
        if source.find_property('track'): source.set_property('track',int(track))
        conv=Gst.ElementFactory.make('audioconvert','conv'); res=Gst.ElementFactory.make('audioresample','resample'); sink=self._make_audio_sink()
        if not all((conv,res,sink)): raise RuntimeError('GStreamer-Audioelement fehlt.')
        pipe=Gst.Pipeline.new('lunaplayer-cd');
        for el in (source,conv,res,sink): pipe.add(el)
        if not source.link(conv) or not conv.link(res) or not res.link(sink): raise RuntimeError('CD-Audiopipeline konnte nicht verbunden werden.')
        bus=pipe.get_bus(); bus.add_signal_watch(); bus.connect('message',self._on_cd_message)
        self.cd_pipeline=pipe; pipe.set_state(Gst.State.PLAYING)
    def _on_cd_message(self,bus,msg):
        if msg.type==Gst.MessageType.EOS:
            self._stop_cd()
            if self.on_eos:self.on_eos()
        elif msg.type==Gst.MessageType.ERROR:
            err,debug=msg.parse_error()
            if self.on_error:self.on_error(str(err),debug or '')
    def play(self):
        if self.cd_pipeline:self.cd_pipeline.set_state(Gst.State.PLAYING)
        else:self.playbin.set_state(Gst.State.PLAYING)
    def pause(self):
        if self.cd_pipeline:self.cd_pipeline.set_state(Gst.State.PAUSED)
        else:self.playbin.set_state(Gst.State.PAUSED)
    def stop(self):
        self._stop_cd()
        self.playbin.set_state(Gst.State.NULL)
        # Never leave an old MP3 URI armed after stopping a CD pipeline.
        try: self.playbin.set_property('uri', None)
        except Exception: pass
        self.current_path = None
    def set_volume(self,value):
        self._volume=max(0.0,min(1.0,float(value))); self.playbin.set_property('volume',self._volume)
    def position_seconds(self):
        ok,pos=self.playbin.query_position(Gst.Format.TIME); return pos/Gst.SECOND if ok else 0
    def duration_seconds(self):
        ok,dur=self.playbin.query_duration(Gst.Format.TIME); return dur/Gst.SECOND if ok else 0
    def seek_seconds(self,seconds):
        # CDDA uses a separate pipeline; seeking playbin here could seek a stale MP3.
        if self.cd_pipeline or not self.current_path or str(self.current_path).startswith('CD Track'):
            return False
        return self.playbin.seek_simple(Gst.Format.TIME,Gst.SeekFlags.FLUSH|Gst.SeekFlags.KEY_UNIT,int(max(0,seconds)*Gst.SECOND))
    def close(self): self.stop(); self.bus.remove_signal_watch()
