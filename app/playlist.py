"""Playlist model with M3U import/export."""
from pathlib import Path
from app.formats import is_supported_audio
class Playlist:
    def __init__(self):
        self.items=[]; self.index=-1; self.display_names={}
    def add_paths(self, paths):
        before=len(self.items)
        for path in paths:
            if path and is_supported_audio(path) and path not in self.items and Path(path).is_file(): self.items.append(str(Path(path).resolve()))
        if self.index < 0 and self.items: self.index=0
        return len(self.items)-before
    def current(self): return self.items[self.index] if 0 <= self.index < len(self.items) else None
    def select(self,index):
        if 0 <= index < len(self.items): self.index=index; return self.current()
        return None
    def next(self):
        if self.items: self.index=(self.index+1)%len(self.items); return self.current()
        return None
    def previous(self):
        if self.items: self.index=(self.index-1)%len(self.items); return self.current()
        return None
    def remove(self,index):
        if 0 <= index < len(self.items):
            removed=self.items[index]; self.display_names.pop(removed, None)
            del self.items[index]
            if not self.items: self.index=-1
            elif self.index >= len(self.items): self.index=len(self.items)-1
            elif index < self.index: self.index-=1
    def save_m3u(self, filename):
        Path(filename).write_text('#EXTM3U\n'+'\n'.join(self.items)+'\n',encoding='utf-8')
    def load_m3u(self, filename):
        """Load ordinary audio M3U files and IPTV-style M3U files.

        #EXTINF entries are associated with the next media URL/path.  The media
        item itself remains the playlist value, so existing MP3 playback and
        all callers using ``items`` continue to work unchanged.
        """
        path=Path(filename); entries=[]; pending_name=None
        for raw_line in path.read_text(encoding='utf-8-sig',errors='replace').splitlines():
            line=raw_line.strip()
            if not line: continue
            if line.upper().startswith('#EXTINF:'):
                # The display name is the text after the final comma. This also
                # works with IPTV attributes such as tvg-name and group-title.
                pending_name=line.rsplit(',', 1)[-1].strip() if ',' in line else None
                continue
            if line.startswith('#'): continue
            if line.lower().startswith(('http://','https://','rtsp://','udp://')):
                item=line
            else:
                media_path=Path(line)
                item=str((path.parent/media_path).resolve() if not media_path.is_absolute() else media_path)
            entries.append((item, pending_name))
            pending_name=None
        before=len(self.items)
        for item, display_name in entries:
            if item.lower().startswith(('http://','https://','rtsp://','udp://')):
                if item not in self.items:
                    self.items.append(item)
                    if display_name: self.display_names[item]=display_name
            elif is_supported_audio(item) and Path(item).is_file() and item not in self.items:
                self.items.append(item)
                if display_name: self.display_names[item]=display_name
        if self.index < 0 and self.items: self.index=0
        return len(self.items)-before
