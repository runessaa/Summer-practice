import unittest
import os
from audio_player import AudioPlayerManager

class TestLoadLocalTracks(unittest.TestCase):
    def setUp(self):
        self.manager = AudioPlayerManager(None, None)
        self.manager.tracks_folder = "test_tracks"
        os.makedirs(self.manager.tracks_folder, exist_ok=True)
        open(os.path.join(self.manager.tracks_folder, "track1.mp3"), "w").close()
        open(os.path.join(self.manager.tracks_folder, "track2.mp3"), "w").close()

    def test_load_tracks(self):
        tracks = self.manager.load_local_tracks()
        self.assertEqual(len(tracks), 2, "должно загрузиться 2 трека")
        self.assertEqual(tracks[0]["title"], "track1", "первый трек должен быть track1")
        self.assertEqual(tracks[1]["title"], "track2", "второй трек должен быть track2")

    def tearDown(self):
        for file in os.listdir(self.manager.tracks_folder):
            os.remove(os.path.join(self.manager.tracks_folder, file))
        os.rmdir(self.manager.tracks_folder)

if __name__ == "__main__":
    unittest.main()