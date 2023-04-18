import unittest

import pyxel

from source.display.menu import Menu, SetupOption, WikiOption, MainMenuOption, WikiUnitsOption
from source.foundation.catalogue import BLESSINGS, IMPROVEMENTS, UNIT_PLANS
from source.foundation.models import VictoryType, GameConfig, DeployerUnitPlan


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

    def test_navigate_wiki_options(self):
        """
        Ensure that the player can correctly navigate up and down the wiki options page.
        """
        self.menu.in_wiki = True

        self.assertEqual(WikiOption.VICTORIES, self.menu.wiki_option)
        self.menu.navigate(down=True)
        self.assertEqual(WikiOption.FACTIONS, self.menu.wiki_option)
        self.menu.navigate(down=True)
        self.assertEqual(WikiOption.CLIMATE, self.menu.wiki_option)
        self.menu.navigate(down=True)
        self.assertEqual(WikiOption.BLESSINGS, self.menu.wiki_option)
        self.menu.navigate(down=True)
        self.assertEqual(WikiOption.IMPROVEMENTS, self.menu.wiki_option)
        self.menu.navigate(down=True)
        self.assertEqual(WikiOption.PROJECTS, self.menu.wiki_option)
        self.menu.navigate(down=True)
        self.assertEqual(WikiOption.UNITS, self.menu.wiki_option)
        self.menu.navigate(down=True)
        self.assertEqual(WikiOption.BACK, self.menu.wiki_option)
        # This time, it should wrap around, bringing the player back to the first option.
        self.menu.navigate(down=True)
        self.assertEqual(WikiOption.VICTORIES, self.menu.wiki_option)

        # Immediately, this should wrap around as well, going back to the bottom.
        self.menu.navigate(up=True)
        self.assertEqual(WikiOption.BACK, self.menu.wiki_option)
        self.menu.navigate(up=True)
        self.assertEqual(WikiOption.UNITS, self.menu.wiki_option)
        self.menu.navigate(up=True)
        self.assertEqual(WikiOption.PROJECTS, self.menu.wiki_option)
        self.menu.navigate(up=True)
        self.assertEqual(WikiOption.IMPROVEMENTS, self.menu.wiki_option)
        self.menu.navigate(up=True)
        self.assertEqual(WikiOption.BLESSINGS, self.menu.wiki_option)
        self.menu.navigate(up=True)
        self.assertEqual(WikiOption.CLIMATE, self.menu.wiki_option)
        self.menu.navigate(up=True)
        self.assertEqual(WikiOption.FACTIONS, self.menu.wiki_option)
        self.menu.navigate(up=True)
        self.assertEqual(WikiOption.VICTORIES, self.menu.wiki_option)

    def test_navigate_wiki_blessings(self):
        """
        Ensure that the player can correctly navigate up and down the blessings page in the wiki.
        """
        self.menu.in_wiki = True
        self.menu.wiki_showing = WikiOption.BLESSINGS

        self.assertTupleEqual((0, 3), self.menu.blessing_boundaries)
        # Iterate through each blessing.
        for i in range(4, len(BLESSINGS)):
            self.menu.navigate(down=True)
            self.assertTupleEqual((i - 3, i), self.menu.blessing_boundaries)
        # Once we get down to the bottom, pressing down again shouldn't do anything.
        self.assertTupleEqual((len(BLESSINGS) - 4, len(BLESSINGS) - 1), self.menu.blessing_boundaries)
        self.menu.navigate(down=True)
        self.assertTupleEqual((len(BLESSINGS) - 4, len(BLESSINGS) - 1), self.menu.blessing_boundaries)

        # Go back up the page.
        for i in range(len(BLESSINGS) - 5, -1, -1):
            self.menu.navigate(up=True)
            self.assertTupleEqual((i, i + 3), self.menu.blessing_boundaries)
        # Now at the top, pressing up shouldn't do anything either.
        self.assertTupleEqual((0, 3), self.menu.blessing_boundaries)
        self.menu.navigate(up=True)
        self.assertTupleEqual((0, 3), self.menu.blessing_boundaries)

    def test_navigate_wiki_improvements(self):
        """
        Ensure that the player can correctly navigate up and down the improvements page in the wiki.
        """
        self.menu.in_wiki = True
        self.menu.wiki_showing = WikiOption.IMPROVEMENTS

        self.assertTupleEqual((0, 3), self.menu.improvement_boundaries)
        # Iterate through each improvement.
        for i in range(4, len(IMPROVEMENTS)):
            self.menu.navigate(down=True)
            self.assertTupleEqual((i - 3, i), self.menu.improvement_boundaries)
        # Once we get down to the bottom, pressing down again shouldn't do anything.
        self.assertTupleEqual((len(IMPROVEMENTS) - 4, len(IMPROVEMENTS) - 1), self.menu.improvement_boundaries)
        self.menu.navigate(down=True)
        self.assertTupleEqual((len(IMPROVEMENTS) - 4, len(IMPROVEMENTS) - 1), self.menu.improvement_boundaries)

        # Go back up the page.
        for i in range(len(IMPROVEMENTS) - 5, -1, -1):
            self.menu.navigate(up=True)
            self.assertTupleEqual((i, i + 3), self.menu.improvement_boundaries)
        # Now at the top, pressing up shouldn't do anything either.
        self.assertTupleEqual((0, 3), self.menu.improvement_boundaries)
        self.menu.navigate(up=True)
        self.assertTupleEqual((0, 3), self.menu.improvement_boundaries)

    def test_navigate_wiki_units_attacking(self):
        """
        Ensure that the player can correctly navigate up and down the attacking units page in the wiki.
        """
        self.menu.in_wiki = True
        self.menu.wiki_showing = WikiOption.UNITS
        self.menu.wiki_units_option = WikiUnitsOption.ATTACKING
        expected_unit_plans = [up for up in UNIT_PLANS if not up.heals and not isinstance(up, DeployerUnitPlan)]

        self.assertTupleEqual((0, 8), self.menu.unit_boundaries)
        # Iterate through each unit.
        for i in range(9, len(expected_unit_plans)):
            self.menu.navigate(down=True)
            self.assertTupleEqual((i - 8, i), self.menu.unit_boundaries)
        # Once we get down to the bottom, pressing down again shouldn't do anything.
        self.assertTupleEqual((len(expected_unit_plans) - 9, len(expected_unit_plans) - 1), self.menu.unit_boundaries)
        self.menu.navigate(down=True)
        self.assertTupleEqual((len(expected_unit_plans) - 9, len(expected_unit_plans) - 1), self.menu.unit_boundaries)

        # Go back up the page.
        for i in range(len(expected_unit_plans) - 10, -1, -1):
            self.menu.navigate(up=True)
            self.assertTupleEqual((i, i + 8), self.menu.unit_boundaries)
        # Now at the top, pressing up shouldn't do anything either.
        self.assertTupleEqual((0, 8), self.menu.unit_boundaries)
        self.menu.navigate(up=True)
        self.assertTupleEqual((0, 8), self.menu.unit_boundaries)

    def test_navigate_main_menu(self):
        """
        Ensure that the player can successfully navigate up and down the main menu.
        """
        self.assertEqual(MainMenuOption.NEW_GAME, self.menu.main_menu_option)
        self.menu.navigate(down=True)
        self.assertEqual(MainMenuOption.LOAD_GAME, self.menu.main_menu_option)
        self.menu.navigate(down=True)
        self.assertEqual(MainMenuOption.STATISTICS, self.menu.main_menu_option)
        self.menu.navigate(down=True)
        self.assertEqual(MainMenuOption.WIKI, self.menu.main_menu_option)
        self.menu.navigate(down=True)
        self.assertEqual(MainMenuOption.EXIT, self.menu.main_menu_option)
        # This time, it should wrap around, bringing the player back to the first option.
        self.menu.navigate(down=True)
        self.assertEqual(MainMenuOption.NEW_GAME, self.menu.main_menu_option)

        # Immediately, this should wrap around as well, going back to the bottom.
        self.menu.navigate(up=True)
        self.assertEqual(MainMenuOption.EXIT, self.menu.main_menu_option)
        self.menu.navigate(up=True)
        self.assertEqual(MainMenuOption.WIKI, self.menu.main_menu_option)
        self.menu.navigate(up=True)
        self.assertEqual(MainMenuOption.STATISTICS, self.menu.main_menu_option)
        self.menu.navigate(up=True)
        self.assertEqual(MainMenuOption.LOAD_GAME, self.menu.main_menu_option)
        self.menu.navigate(up=True)
        self.assertEqual(MainMenuOption.NEW_GAME, self.menu.main_menu_option)

    def test_navigate_setup_faction(self):
        """
        Ensure that the player can correctly iterate through the options when choosing their faction.
        """
        self.menu.in_game_setup = True
        self.menu.setup_option = SetupOption.PLAYER_FACTION

        self.assertEqual(0, self.menu.faction_idx)
        # Iterate through each faction.
        for i in range(1, len(self.menu.faction_colours)):
            self.menu.navigate(right=True)
            self.assertEqual(i, self.menu.faction_idx)
        # Once we get to the last faction, pressing right again should have no effect.
        self.assertEqual(len(self.menu.faction_colours) - 1, self.menu.faction_idx)
        self.menu.navigate(right=True)
        self.assertEqual(len(self.menu.faction_colours) - 1, self.menu.faction_idx)

        # Go back to the first faction.
        for i in range(len(self.menu.faction_colours) - 2, -1, -1):
            self.menu.navigate(left=True)
            self.assertEqual(i, self.menu.faction_idx)
        # At the start again, pressing left should also have no effect.
        self.assertEqual(0, self.menu.faction_idx)
        self.menu.navigate(left=True)
        self.assertEqual(0, self.menu.faction_idx)

    def test_navigate_setup_player_count(self):
        """
        Ensure that the player can correctly select the number of players for their game.
        """
        self.menu.in_game_setup = True
        self.menu.setup_option = SetupOption.PLAYER_COUNT

        self.assertEqual(2, self.menu.player_count)
        # Iterate through the count options.
        for i in range(3, 15):
            self.menu.navigate(right=True)
            self.assertEqual(i, self.menu.player_count)
        # Once we get to the maximum number of players (14), pressing right again should have no effect.
        self.assertEqual(14, self.menu.player_count)
        self.menu.navigate(right=True)
        self.assertEqual(14, self.menu.player_count)

        # Revert to the minimum number of players (2).
        for i in range(13, 1, -1):
            self.menu.navigate(left=True)
            self.assertEqual(i, self.menu.player_count)
        # Back at the minimum, we should not be able to decrease the count any further.
        self.assertEqual(2, self.menu.player_count)
        self.menu.navigate(left=True)
        self.assertEqual(2, self.menu.player_count)

    def test_navigate_setup_clustering(self):
        """
        Ensure that the player can correctly enable and disable biome clustering.
        """
        self.menu.in_game_setup = True
        self.menu.setup_option = SetupOption.BIOME_CLUSTERING

        self.assertTrue(self.menu.biome_clustering_enabled)
        # Pressing right when already enabled should have no effect.
        self.menu.navigate(right=True)
        self.assertTrue(self.menu.biome_clustering_enabled)
        self.menu.navigate(left=True)
        self.assertFalse(self.menu.biome_clustering_enabled)
        # Similarly, pressing left when already disabled should have no effect.
        self.menu.navigate(left=True)
        self.assertFalse(self.menu.biome_clustering_enabled)
        self.menu.navigate(right=True)
        self.assertTrue(self.menu.biome_clustering_enabled)

    def test_navigate_setup_fog(self):
        """
        Ensure that the player can correctly enable and disable fog of war.
        """
        self.menu.in_game_setup = True
        self.menu.setup_option = SetupOption.FOG_OF_WAR

        self.assertTrue(self.menu.fog_of_war_enabled)
        # Pressing right when already enabled should have no effect.
        self.menu.navigate(right=True)
        self.assertTrue(self.menu.fog_of_war_enabled)
        self.menu.navigate(left=True)
        self.assertFalse(self.menu.fog_of_war_enabled)
        # Similarly, pressing left when already disabled should have no effect.
        self.menu.navigate(left=True)
        self.assertFalse(self.menu.fog_of_war_enabled)
        self.menu.navigate(right=True)
        self.assertTrue(self.menu.fog_of_war_enabled)

    def test_navigate_setup_climate(self):
        """
        Ensure that the player can correctly enable and disable climatic effects.
        """
        self.menu.in_game_setup = True
        self.menu.setup_option = SetupOption.CLIMATIC_EFFECTS

        self.assertTrue(self.menu.climatic_effects_enabled)
        # Pressing right when already enabled should have no effect.
        self.menu.navigate(right=True)
        self.assertTrue(self.menu.climatic_effects_enabled)
        self.menu.navigate(left=True)
        self.assertFalse(self.menu.climatic_effects_enabled)
        # Similarly, pressing left when already disabled should have no effect.
        self.menu.navigate(left=True)
        self.assertFalse(self.menu.climatic_effects_enabled)
        self.menu.navigate(right=True)
        self.assertTrue(self.menu.climatic_effects_enabled)

    def test_navigate_wiki_victories(self):
        """
        Ensure that the player can correctly navigate through the available victories in the wiki.
        """
        self.menu.in_wiki = True
        self.menu.wiki_showing = WikiOption.VICTORIES

        self.assertEqual(VictoryType.ELIMINATION, self.menu.victory_type)
        self.menu.navigate(right=True)
        self.assertEqual(VictoryType.JUBILATION, self.menu.victory_type)
        self.menu.navigate(right=True)
        self.assertEqual(VictoryType.GLUTTONY, self.menu.victory_type)
        self.menu.navigate(right=True)
        self.assertEqual(VictoryType.AFFLUENCE, self.menu.victory_type)
        self.menu.navigate(right=True)
        self.assertEqual(VictoryType.VIGOUR, self.menu.victory_type)
        self.menu.navigate(right=True)
        self.assertEqual(VictoryType.SERENDIPITY, self.menu.victory_type)
        # Pressing right when already at the last victory should have no effect.
        self.menu.navigate(right=True)
        self.assertEqual(VictoryType.SERENDIPITY, self.menu.victory_type)

        self.menu.navigate(left=True)
        self.assertEqual(VictoryType.VIGOUR, self.menu.victory_type)
        self.menu.navigate(left=True)
        self.assertEqual(VictoryType.AFFLUENCE, self.menu.victory_type)
        self.menu.navigate(left=True)
        self.assertEqual(VictoryType.GLUTTONY, self.menu.victory_type)
        self.menu.navigate(left=True)
        self.assertEqual(VictoryType.JUBILATION, self.menu.victory_type)
        self.menu.navigate(left=True)
        self.assertEqual(VictoryType.ELIMINATION, self.menu.victory_type)
        # Pressing left when already at the first victory should have no effect.
        self.menu.navigate(left=True)
        self.assertEqual(VictoryType.ELIMINATION, self.menu.victory_type)

    def test_navigate_wiki_factions(self):
        """
        Ensure that the player can correctly navigate through the available factions in the wiki.
        """
        self.menu.in_wiki = True
        self.menu.wiki_showing = WikiOption.FACTIONS

        self.assertEqual(0, self.menu.faction_wiki_idx)
        for i in range(1, len(self.menu.faction_colours)):
            self.menu.navigate(right=True)
            self.assertEqual(i, self.menu.faction_wiki_idx)
        # Now at the last faction, pressing right again should do nothing.
        self.assertEqual(len(self.menu.faction_colours) - 1, self.menu.faction_wiki_idx)
        self.menu.navigate(right=True)
        self.assertEqual(len(self.menu.faction_colours) - 1, self.menu.faction_wiki_idx)

        for i in range(len(self.menu.faction_colours) - 2, -1, -1):
            self.menu.navigate(left=True)
            self.assertEqual(i, self.menu.faction_wiki_idx)
        # Returned to the first faction, pressing left should similarly do nothing.
        self.assertEqual(0, self.menu.faction_wiki_idx)
        self.menu.navigate(left=True)
        self.assertEqual(0, self.menu.faction_wiki_idx)

    def test_navigate_wiki_climate(self):
        """
        Ensure that the player can toggle between the two climate types in the wiki.]
        """
        self.menu.in_wiki = True
        self.menu.wiki_showing = WikiOption.CLIMATE

        self.assertFalse(self.menu.showing_night)
        # Pressing left when already on daytime should have no effect.
        self.menu.navigate(left=True)
        self.assertFalse(self.menu.showing_night)
        self.menu.navigate(right=True)
        self.assertTrue(self.menu.showing_night)
        # Similarly, pressing right when already on night should have no effect.
        self.menu.navigate(right=True)
        self.assertTrue(self.menu.showing_night)
        self.menu.navigate(left=True)
        self.assertFalse(self.menu.showing_night)

    def test_get_game_config(self):
        """
        Ensure that the menu correctly returns the game configuration.
        """
        # Set up our test data.
        test_player_count = self.menu.player_count = 5
        self.menu.faction_idx = 12
        test_player_faction = self.menu.faction_colours[self.menu.faction_idx][0]
        test_clustering = self.menu.biome_clustering_enabled = False
        test_fog_of_war = self.menu.fog_of_war_enabled = True
        test_climate = self.menu.climatic_effects_enabled = False

        test_config: GameConfig = self.menu.get_game_config()

        # Make sure everything is as expected.
        self.assertEqual(test_player_count, test_config.player_count)
        self.assertEqual(test_player_faction, test_config.player_faction)
        self.assertEqual(test_clustering, test_config.biome_clustering)
        self.assertEqual(test_fog_of_war, test_config.fog_of_war)
        self.assertEqual(test_climate, test_config.climatic_effects)

    def test_option_colouring(self):
        """
        Ensure that options are correctly coloured when displayed on the menu.
        """
        self.menu.setup_option = SetupOption.FOG_OF_WAR
        # Since it's selected, the fog of war option should be red.
        self.assertEqual(pyxel.COLOR_RED, self.menu.get_option_colour(SetupOption.FOG_OF_WAR))
        # Since it's not selected, the climate option should be white.
        self.assertEqual(pyxel.COLOR_WHITE, self.menu.get_option_colour(SetupOption.CLIMATIC_EFFECTS))

        self.menu.wiki_option = WikiOption.BLESSINGS
        self.assertEqual(pyxel.COLOR_RED, self.menu.get_option_colour(WikiOption.BLESSINGS))
        self.assertEqual(pyxel.COLOR_WHITE, self.menu.get_option_colour(WikiOption.VICTORIES))

        self.menu.main_menu_option = MainMenuOption.WIKI
        self.assertEqual(pyxel.COLOR_RED, self.menu.get_option_colour(MainMenuOption.WIKI))
        self.assertEqual(pyxel.COLOR_WHITE, self.menu.get_option_colour(MainMenuOption.EXIT))


if __name__ == '__main__':
    unittest.main()
