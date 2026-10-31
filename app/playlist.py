"""Playlist model with M3U import/export."""
from pathlib import Path
from app.formats import is_supported_audio
class Playlist:
    def __init__(self): self.items=[]; self.index=-1
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
            del self.items[index]
            if not self.items: self.index=-1
            elif self.index >= len(self.items): self.index=len(self.items)-1
            elif index < self.index: self.index-=1
    def save_m3u(self, filename):
        Path(filename).write_text('#EXTM3U\n'+'\n'.join(self.items)+'\n',encoding='utf-8')
    def load_m3u(self, filename):
        path=Path(filename); items=[]
        for line in path.read_text(encoding='utf-8-sig',errors='replace').splitlines():
            line=line.strip()
            if not line or line.startswith('#'): continue
            
            if line.lower().startswith(('http://','https://','rtsp://','udp://')):
                items.append(line)
            else:
                p=Path(line); items.append(str((path.parent/p).resolve() if not p.is_absolute() else p))
        before=len(self.items)
        for item in items:
            if item.lower().startswith(('http://','https://','rtsp://','udp://')):
                if item not in self.items: self.items.append(item)
            elif is_supported_audio(item) and Path(item).is_file() and item not in self.items:
                self.items.append(item)
        if self.index < 0 and self.items: self.index=0
        return len(self.items)-before
