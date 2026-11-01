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
    def test_iptv_extinf_names(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            m3u=Path(d)/'tv.m3u'
            m3u.write_text('#EXTM3U\n#EXTINF:-1 tvg-name="Das Erste HD",Das Erste HD\nhttps://example.test/master.m3u8\n#EXTINF:-1,ZDF HD\nhttps://example.test/index.m3u8\n', encoding='utf-8')
            pl=Playlist(); pl.load_m3u(m3u)
            self.assertEqual(pl.display_names[pl.items[0]], 'Das Erste HD')
            self.assertEqual(pl.display_names[pl.items[1]], 'ZDF HD')

if __name__=='__main__':unittest.main()
