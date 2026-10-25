import tempfile
import unittest
from pathlib import Path
from app.playlist import Playlist
class PlaylistTests(unittest.TestCase):
    def test_add_and_next(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.mp3'; b=Path(d)/'b.wav'; bad=Path(d)/'no.txt'
            a.touch(); b.touch(); bad.touch()
            p=Playlist(); p.add_paths([str(a),str(b),str(bad)])
            self.assertEqual(len(p.items),2)
            self.assertEqual(p.current(),str(a.resolve()))
            self.assertEqual(p.next(),str(b.resolve()))
    def test_m3u_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'song.ogg';a.touch(); pl=Playlist();pl.add_paths([str(a)])
            m3u=Path(d)/'list.m3u';pl.save_m3u(m3u)
            pl2=Playlist();pl2.load_m3u(m3u);self.assertEqual(pl2.items,[str(a.resolve())])
if __name__=='__main__':unittest.main()
