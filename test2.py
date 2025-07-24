import unittest
from audio_player import AudioPlayerManager

class TestToggleShuffle(unittest.TestCase):
    def setUp(self):
        self.manager = AudioPlayerManager(None, None)
        self.manager.original_playlist = [
            {"url": "track1.mp3", "title": "track1"},
            {"url": "track2.mp3", "title": "track2"},
            {"url": "track3.mp3", "title": "track3"}
        ]
        self.manager.playlist = self.manager.original_playlist.copy()
        self.manager.current_track_index = 1

    def test_toggle_shuffle(self):
        self.manager.toggle_shuffle(None, None, None)
        self.assertTrue(self.manager.shuffle_mode, "перемешивание должно быть включено")
        self.assertEqual(self.manager.playlist[1]["title"], "track2", "текущий трек должен быть track2")
        self.assertNotEqual(self.manager.playlist, self.manager.original_playlist, "плейлист должен измениться")

if __name__ == "__main__":
    unittest.main()