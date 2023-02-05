import unittest
from unittest.mock import MagicMock

from source.util.music_player import MusicPlayer


class MusicPlayerTest(unittest.TestCase):
    """
    The test class for music_player.py.
    """

    def setUp(self) -> None:
        """
        Instantiate a standard MusicPlayer before each test.
        """
        self.music_player = MusicPlayer()

    def test_play_menu(self):
        """
        Ensure that playing the menu music sets the volume and plays the menu player accordingly.
        """
        self.music_player.menu_player.audio_set_volume = MagicMock()
        self.music_player.menu_player.play = MagicMock()

        self.music_player.play_menu_music()
        self.music_player.menu_player.audio_set_volume.assert_called_with(70)
        self.music_player.menu_player.play.assert_called()

    def test_stop_menu(self):
        """
        Ensure that stopping the menu music gradually reduces the volume and pauses the menu player.
        """
        self.music_player.menu_player.audio_set_volume = MagicMock()
        self.music_player.menu_player.pause = MagicMock()

        self.music_player.stop_menu_music()
        # 7 is the number of steps before the player is paused.
        self.assertEqual(7, self.music_player.menu_player.audio_set_volume.call_count)
        self.music_player.menu_player.pause.assert_called()

    def test_play_game(self):
        """
        Ensure that playing the game music sets the volume and plays the correct game player.
        """
        test_idx = 3
        self.music_player.current_idx = test_idx
        self.music_player.game_players[self.music_player.current_idx].audio_set_volume = MagicMock()
        self.music_player.game_players[self.music_player.current_idx].play = MagicMock()

        self.music_player.play_game_music()
        self.music_player.game_players[test_idx].audio_set_volume.assert_called_with(70)
        self.music_player.game_players[test_idx].play.assert_called()

    def test_stop_game(self):
        """
        Ensure that stopping the game music gradually reduces the volume of and pauses the current game player.
        """
        test_idx = 4
        self.music_player.current_idx = test_idx
        self.music_player.game_players[self.music_player.current_idx].audio_set_volume = MagicMock()
        self.music_player.game_players[self.music_player.current_idx].pause = MagicMock()

        self.music_player.stop_game_music()
        self.assertEqual(7, self.music_player.game_players[test_idx].audio_set_volume.call_count)
        self.music_player.game_players[test_idx].pause.assert_called()

    def test_next_song(self):
        """
        Ensure that going to the next song stops the current one, adjusts the index, and plays the next song.
        """
        test_idx = 2
        self.music_player.current_idx = test_idx
        self.music_player.game_players[self.music_player.current_idx].stop = MagicMock()
        self.music_player.play_game_music = MagicMock()

        self.music_player.next_song()
        self.music_player.game_players[test_idx].stop.assert_called()
        # Because our current game player is somewhere in the middle of the list, the current index should just be
        # incremented.
        self.assertEqual(test_idx + 1, self.music_player.current_idx)
        self.music_player.play_game_music.assert_called()

        # Now set the current index to the last game player.
        self.music_player.current_idx = len(self.music_player.game_players) - 1
        self.music_player.game_players[self.music_player.current_idx].stop = MagicMock()

        self.music_player.next_song()
        self.music_player.game_players[len(self.music_player.game_players) - 1].stop.assert_called()
        # The current index should now be reset to 0, rather than incremented.
        self.assertEqual(0, self.music_player.current_idx)
        self.music_player.play_game_music.assert_called()

    def test_is_playing(self):
        """
        Ensure that the music player correctly reports if any of the game players are playing.
        """
        self.assertFalse(self.music_player.is_playing())
        self.music_player.game_players[3].is_playing = MagicMock(return_value=True)
        self.assertTrue(self.music_player.is_playing())

    def test_restart(self):
        """
        Ensure that the music player only restarts the menu music if it has finished.
        """
        self.music_player.menu_player.stop = MagicMock()
        self.music_player.menu_player.play = MagicMock()
        self.music_player.menu_player.is_playing = MagicMock(return_value=True)

        self.music_player.restart_menu_if_necessary()
        self.music_player.menu_player.stop.assert_not_called()
        self.music_player.menu_player.play.assert_not_called()

        self.music_player.menu_player.is_playing.return_value = False
        self.music_player.restart_menu_if_necessary()
        self.music_player.menu_player.stop.assert_called()
        self.music_player.menu_player.play.assert_called()


if __name__ == '__main__':
    unittest.main()
