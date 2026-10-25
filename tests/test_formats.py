import unittest
from app.formats import is_supported_audio
class FormatTests(unittest.TestCase):
    def test_supported(self):
        for name in ("song.mp3", "song.WAV", "song.ogg", "song.oga", "song.m4a", "song.MP4"):
            self.assertTrue(is_supported_audio(name))
    def test_unsupported(self):
        self.assertFalse(is_supported_audio("song.txt"))
if __name__ == "__main__":
    unittest.main()
