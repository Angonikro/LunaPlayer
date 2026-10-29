import unittest
from pathlib import Path
from app.vlc_player import VIDEO_EXTENSIONS, is_supported_video

class VLCVideoTests(unittest.TestCase):
    def test_supported_extensions(self):
        for ext in (".mkv", ".MP4", ".avi", ".webm", ".m2ts"):
            self.assertTrue(is_supported_video("movie" + ext))
    def test_unsupported_extension(self):
        self.assertFalse(is_supported_video("track.mp3"))
        self.assertFalse(is_supported_video("notes.txt"))
    def test_extensions_are_defined(self):
        self.assertIn(".mp4", VIDEO_EXTENSIONS)
        self.assertIn(".mkv", VIDEO_EXTENSIONS)

if __name__ == "__main__":
    unittest.main()
