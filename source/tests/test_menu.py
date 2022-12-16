import unittest

from source.display.menu import Menu, SetupOption


class MenuTest(unittest.TestCase):
    """
    The test class for menu.py.
    """

    def setUp(self) -> None:
        """
        Instantiate a standard Menu object before each test.
        """
        self.menu = Menu()

    def test_navigate_setup(self):
        """
        Ensure that the player can correctly navigate down and up the game setup page.
        """
        self.menu.in_game_setup = True

        self.assertEqual(SetupOption.PLAYER_FACTION, self.menu.setup_option)
        self.menu.navigate(down=True)
        self.assertEqual(SetupOption.PLAYER_COUNT, self.menu.setup_option)
        self.menu.navigate(down=True)
        self.assertEqual(SetupOption.BIOME_CLUSTERING, self.menu.setup_option)
        self.menu.navigate(down=True)
        self.assertEqual(SetupOption.FOG_OF_WAR, self.menu.setup_option)
        self.menu.navigate(down=True)
        self.assertEqual(SetupOption.CLIMATIC_EFFECTS, self.menu.setup_option)
        self.menu.navigate(down=True)
        self.assertEqual(SetupOption.START_GAME, self.menu.setup_option)
        # This time, it should wrap around, bringing the player back to the first option.
        self.menu.navigate(down=True)
        self.assertEqual(SetupOption.PLAYER_FACTION, self.menu.setup_option)

        # Immediately, this should wrap around as well, going back to the bottom.
        self.menu.navigate(up=True)
        self.assertEqual(SetupOption.START_GAME, self.menu.setup_option)
        self.menu.navigate(up=True)
        self.assertEqual(SetupOption.CLIMATIC_EFFECTS, self.menu.setup_option)
        self.menu.navigate(up=True)
        self.assertEqual(SetupOption.FOG_OF_WAR, self.menu.setup_option)
        self.menu.navigate(up=True)
        self.assertEqual(SetupOption.BIOME_CLUSTERING, self.menu.setup_option)
        self.menu.navigate(up=True)
        self.assertEqual(SetupOption.PLAYER_COUNT, self.menu.setup_option)
        self.menu.navigate(up=True)
        self.assertEqual(SetupOption.PLAYER_FACTION, self.menu.setup_option)

    def test_navigate_saves(self):
        """
        Ensure that the player can correctly navigate down and up the load game page.
        """
        self.menu.loading_game = True
        self.menu.saves = ["a"] * 11  # Just some fake save data.

        self.assertEqual(0, self.menu.save_idx)
        self.assertTupleEqual((0, 9), self.menu.load_game_boundaries)
        # Iterate through each of the saves.
        for i in range(1, 10):
            self.menu.navigate(down=True)
            self.assertEqual(i, self.menu.save_idx)
            self.assertTupleEqual((0, 9), self.menu.load_game_boundaries)
        # Now that we have reached the lowest displayed save, the next navigation should push the boundaries down.
        self.menu.navigate(down=True)
        self.assertEqual(10, self.menu.save_idx)
        self.assertTupleEqual((1, 10), self.menu.load_game_boundaries)
        # Now at the bottom, pressing down should not do anything.
        self.menu.navigate(down=True)
        self.assertEqual(10, self.menu.save_idx)
        self.assertTupleEqual((1, 10), self.menu.load_game_boundaries)

        # Iterate back up the menu.
        for i in range(9, 0, -1):
            self.menu.navigate(up=True)
            self.assertEqual(i, self.menu.save_idx)
            self.assertTupleEqual((1, 10), self.menu.load_game_boundaries)
        # Conversely, at the highest displayed save, the next navigation should push the boundaries back up.
        self.menu.navigate(up=True)
        self.assertEqual(0, self.menu.save_idx)
        self.assertTupleEqual((0, 9), self.menu.load_game_boundaries)
        # Now at the top, pressing up should not do anything.
        self.menu.navigate(up=True)
        self.assertEqual(0, self.menu.save_idx)
        self.assertTupleEqual((0, 9), self.menu.load_game_boundaries)


if __name__ == '__main__':
    unittest.main()
