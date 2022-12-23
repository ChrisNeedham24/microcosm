import unittest

from source.display.overlay import Overlay
from source.foundation.models import OverlayType, Settlement, Player, Faction, ConstructionMenu, Project, ProjectType, \
    Improvement, Effect, ImprovementType, UnitPlan


class OverlayTest(unittest.TestCase):
    """
    The test class for overlay.py.
    """

    def setUp(self) -> None:
        """
        Instantiate a standard Overlay object before each test.
        """
        self.overlay = Overlay()

    def test_toggle_standard(self):
        """
        Ensure that the overlay correctly toggles the Standard overlay.
        """
        # When the Standard and Blessing overlays are being displayed, toggling should not remove the Standard overlay.
        self.overlay.showing = [OverlayType.STANDARD, OverlayType.BLESSING]
        self.overlay.toggle_standard(0)
        self.assertTrue(self.overlay.is_standard())

        # Now with only the Standard overlay, toggling should remove it.
        self.overlay.showing = [OverlayType.STANDARD]
        self.overlay.toggle_standard(0)
        self.assertFalse(self.overlay.is_standard())

        # When displaying the Pause overlay (or a number of others), toggling should not add the Standard overlay.
        self.overlay.showing = [OverlayType.PAUSE]
        self.overlay.toggle_standard(5)
        self.assertFalse(self.overlay.is_standard())

        # When no overlay is being displayed, toggling should add the Standard overlay and set the current turn.
        self.overlay.showing = []
        self.overlay.toggle_standard(5)
        self.assertTrue(self.overlay.is_standard())
        self.assertEqual(5, self.overlay.current_turn)

    def test_navigate_standard(self):
        """
        Ensure that the standard overlay can be successfully navigated.
        """
        self.overlay.current_player = Player("Tester", Faction.NOCTURNE, 0, 0, [], [], [], set(), set())

        # To begin with, the current player has no settlements at all. As such, navigating downwards shouldn't do
        # anything.
        self.assertTupleEqual((0, 7), self.overlay.settlement_status_boundaries)
        self.overlay.navigate_standard(down=True)
        self.assertTupleEqual((0, 7), self.overlay.settlement_status_boundaries)

        # Now if we give the player some settlements, they should be able to navigate down.
        self.overlay.current_player.settlements = [Settlement("Test", (0, 0), [], [], [])] * 8
        self.overlay.navigate_standard(down=True)
        self.assertTupleEqual((1, 8), self.overlay.settlement_status_boundaries)
        # However, since they only have one more than the threshold, they should only be able to navigate down once.
        self.overlay.navigate_standard(down=True)
        self.assertTupleEqual((1, 8), self.overlay.settlement_status_boundaries)

        # Navigating upwards should work initially, but once the player has reached the top again, should then do
        # nothing.
        self.overlay.navigate_standard(down=False)
        self.assertTupleEqual((0, 7), self.overlay.settlement_status_boundaries)
        self.overlay.navigate_standard(down=False)
        self.assertTupleEqual((0, 7), self.overlay.settlement_status_boundaries)

    def test_toggle_construction(self):
        """
        Ensure that the player can toggle the Construction overlay correctly.
        """
        test_improvement = Improvement(ImprovementType.BOUNTIFUL, 0, "More", "Food", Effect(), None)
        test_project = Project(ProjectType.MAGICAL, "Magic", "Project")
        test_unit_plan = UnitPlan(0, 0, 1, "Weakling", None, 0)

        # When the Construction overlay is displayed, toggling should remove it.
        self.overlay.showing = [OverlayType.CONSTRUCTION]
        self.overlay.toggle_construction([], [], [])
        self.assertFalse(self.overlay.is_constructing())

        # When displaying the Blessing Notification overlay (or a number of others), toggling should not add the
        # Construction overlay.
        self.overlay.showing = [OverlayType.BLESS_NOTIF]
        self.overlay.toggle_construction([], [], [])
        self.assertFalse(self.overlay.is_constructing())

        # Now with a clean slate, we toggle again with only one available Project. The overlay should be displayed, and
        # the available options passed down correctly.
        self.overlay.showing = []
        self.overlay.toggle_construction([], [test_project], [])
        self.assertTrue(self.overlay.is_constructing())
        self.assertFalse(self.overlay.available_constructions)
        self.assertEqual([test_project], self.overlay.available_projects)
        self.assertFalse(self.overlay.available_unit_plans)
        # However, since there are no improvements to construct, the overlay is initialised on the Projects tab, with
        # the supplied project selected.
        self.assertEqual(ConstructionMenu.PROJECTS, self.overlay.current_construction_menu)
        self.assertEqual(test_project, self.overlay.selected_construction)

        # Toggle from the beginning once again, this time with an available construction for each category.
        self.overlay.showing = []
        self.overlay.toggle_construction([test_improvement], [test_project], [test_unit_plan])
        self.assertTrue(self.overlay.is_constructing())
        self.assertEqual([test_improvement], self.overlay.available_constructions)
        self.assertEqual([test_project], self.overlay.available_projects)
        self.assertEqual([test_unit_plan], self.overlay.available_unit_plans)
        # Since an improvement has been supplied, the Improvements tab should be displayed, with the supplied
        # improvement selected and the boundaries reset.
        self.assertEqual(ConstructionMenu.IMPROVEMENTS, self.overlay.current_construction_menu)
        self.assertEqual(test_improvement, self.overlay.selected_construction)
        self.assertTupleEqual((0, 5), self.overlay.construction_boundaries)


if __name__ == '__main__':
    unittest.main()
