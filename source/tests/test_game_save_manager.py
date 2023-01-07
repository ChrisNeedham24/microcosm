import json
import os
import unittest
from datetime import datetime
from itertools import chain
from unittest.mock import patch, MagicMock, mock_open

from source.display.board import Board
from source.foundation.catalogue import Namer, get_heathen_plan
from source.foundation.models import GameConfig, Faction, Heathen
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.saving.game_save_manager import save_game, SAVES_DIR, get_saves
from source.saving.save_encoder import SaveEncoder


class GameSaveManagerTest(unittest.TestCase):
    """
    The test class for game_save_manager.py.
    """
    TEST_CONFIG = GameConfig(4, Faction.NOCTURNE, True, True, True)

    @patch("source.game_management.game_controller.MusicPlayer")
    def setUp(self, _: MagicMock) -> None:
        """
        Initialise the test game state and controller objects. Note that we also mock out the MusicPlayer class that
        is used when constructing the GameController. This is because it will try to play music if not mocked.
        :param _: The unused MusicPlayer mock.
        """
        self.game_state = GameState()
        self.game_state.board = Board(self.TEST_CONFIG, Namer())
        self.game_state.gen_players(self.TEST_CONFIG)
        self.game_state.heathens = [Heathen(1, 2, (3, 4), get_heathen_plan(1))]
        self.game_controller = GameController()

    @patch("source.saving.game_save_manager.datetime")
    @patch("os.remove")
    @patch("os.listdir")
    @patch("source.saving.game_save_manager.open", new_callable=mock_open)
    def test_save_game(self,
                       open_mock: MagicMock,
                       listdir_mock: MagicMock,
                       remove_mock: MagicMock,
                       datetime_mock: MagicMock):
        """
        Ensure that when saving a game state, the correct autosave modifications occur, and the correct data is written.
        :param open_mock: The mock representation of the open() builtin, which is used to open the save file for
        writing.
        :param listdir_mock: The mock representation of os.listdir(), which is used to retrieve previous autosaves.
        :param remove_mock: The mock representation of os.remove(), which is used to delete old autosaves.
        :param datetime_mock: The mock representation of datetime.datetime, which is used to retrieve the current time.
        """
        test_saves = [
            "autosave-2023-01-07T13.35.00.json",
            "autosave-2023-01-07T13.30.00.json",
            "autosave-2023-01-07T13.40.00.json"
        ]
        test_time = datetime(2023, 1, 7, hour=13, minute=35, second=24)

        listdir_mock.return_value = test_saves
        datetime_mock.now.return_value = test_time

        # We expect the second save to be deleted because it is the oldest autosave.
        expected_deleted_autosave = os.path.join(SAVES_DIR, test_saves[1])
        # The save name should also be according to our test time.
        expected_save_name = os.path.join(SAVES_DIR, "autosave-2023-01-07T13.35.24.json")
        # Also determine the data we expect to be saved.
        expected_save_data = {
            "quads": list(chain.from_iterable(self.game_state.board.quads)),
            "players": self.game_state.players,
            "heathens": self.game_state.heathens,
            "turn": self.game_state.turn,
            "cfg": self.game_state.board.game_config,
            "night_status": {"until": self.game_state.until_night, "remaining": self.game_state.nighttime_left}
        }

        save_game(self.game_state, auto=True)
        # After saving, we expect the oldest autosave to have been deleted, a new save with the correct name to have
        # been created, and the correct data to have been written to said save.
        remove_mock.assert_called_with(expected_deleted_autosave)
        self.assertEqual(expected_save_name, open_mock.call_args[0][0])
        open_mock.return_value.write.assert_called_with(json.dumps(expected_save_data, cls=SaveEncoder))
        open_mock.return_value.close.assert_called()

    @patch("os.listdir")
    def test_get_saves(self, listdir_mock: MagicMock):
        """
        Ensure that when retrieving existing save files, the correct filters and ordering are applied before displaying
        them on the menu.
        :param listdir_mock: The mock representation of os.listdir(), which is used to retrieve file names from the
        saves directory.
        """
        # Set some fake data for the menu that we expect to be overwritten.
        self.game_controller.menu.saves = ["a", "b", "c"]
        self.game_controller.menu.save_idx = 999
        # In our first example, there are no existing save files.
        listdir_mock.return_value = []

        get_saves(self.game_controller)
        # As such, we expect the menu saves to be reset and the save index to be negative (which is used to select the
        # cancel button).
        self.assertFalse(self.game_controller.menu.saves)
        self.assertEqual(-1, self.game_controller.menu.save_idx)

        # Now return some mock files from the listdir() call.
        test_saves = [
            "README.md",
            ".secret_file",
            "save-2023-01-07T13.36.00.json",
            "autosave-2023-01-07T13.37.00.json"
        ]
        listdir_mock.return_value = test_saves
        # We expect the README and the dotfile to be filtered out, and the saves to have their names formatted.
        expected_saves = [
            "2023-01-07 13.37.00 (auto)",
            "2023-01-07 13.36.00"
        ]

        get_saves(self.game_controller)
        self.assertListEqual(expected_saves, self.game_controller.menu.saves)


if __name__ == '__main__':
    unittest.main()
