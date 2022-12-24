import unittest

from source.display.overlay import Overlay
from source.foundation.catalogue import UNIT_PLANS
from source.foundation.models import OverlayType, Settlement, Player, Faction, ConstructionMenu, Project, ProjectType, \
    Improvement, Effect, ImprovementType, UnitPlan, Blessing, Unit


class OverlayTest(unittest.TestCase):
    """
    The test class for overlay.py.
    """
    
    TEST_SETTLEMENT = Settlement("Testville", (0, 0), [], [], [])
    TEST_UNIT = Unit(1, 2, (3, 4), False, UNIT_PLANS[0])

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

    def test_toggle_blessing(self):
        """
        Ensure that the player can toggle the Blessing overlay correctly.
        """
        test_blessing = Blessing("Cool", "Magic", 0)

        # When the Blessing overlay is displayed, toggling should remove it.
        self.overlay.showing = [OverlayType.BLESSING]
        self.overlay.toggle_blessing([])
        self.assertFalse(self.overlay.is_blessing())

        # When displaying the Level Notification overlay (or a number of others), toggling should not add the Blessing
        # overlay.
        self.overlay.showing = [OverlayType.LEVEL_NOTIF]
        self.overlay.toggle_blessing([])
        self.assertFalse(self.overlay.is_blessing())

        # Now not showing any other overlays, toggling should display the Blessing overlay, while updating the available
        # and selected blessings, as well as the corresponding boundaries.
        self.overlay.showing = []
        self.overlay.toggle_blessing([test_blessing])
        self.assertTrue(self.overlay.is_blessing())
        self.assertEqual([test_blessing], self.overlay.available_blessings)
        self.assertEqual(test_blessing, self.overlay.selected_blessing)
        self.assertTupleEqual((0, 5), self.overlay.blessing_boundaries)

    def test_toggle_settlement(self):
        """
        Ensure that the player can toggle the Settlement overlay correctly.
        """
        test_player = Player("Bob", Faction.NOCTURNE, 0, 0, [self.TEST_SETTLEMENT], [], [], set(), set())

        # When the Settlement and Construction overlays are both displayed, toggling the Settlement overlay should do
        # nothing.
        self.overlay.showing = [OverlayType.SETTLEMENT, OverlayType.CONSTRUCTION]
        self.overlay.toggle_settlement(None, test_player)
        self.assertTrue(self.overlay.is_setl())

        # However, when only the Settlement overlay is displayed, toggling should remove it.
        self.overlay.showing = [OverlayType.SETTLEMENT]
        self.overlay.toggle_settlement(None, test_player)
        self.assertFalse(self.overlay.is_setl())

        # When displaying the Investigation overlay (or a number of others), toggling should not add the Settlement
        # overlay.
        self.overlay.showing = [OverlayType.INVESTIGATION]
        self.overlay.toggle_settlement(None, test_player)
        self.assertFalse(self.overlay.is_setl())

        # When not showing any other overlays, toggling should display the Settlement overlay, while updating the
        # current settlement and player.
        self.overlay.showing = []
        self.overlay.toggle_settlement(self.TEST_SETTLEMENT, test_player)
        self.assertTrue(self.overlay.is_setl())
        self.assertEqual(self.TEST_SETTLEMENT, self.overlay.current_settlement)
        self.assertEqual(test_player, self.overlay.current_player)

    def test_update_settlement(self):
        """
        Ensure that the overlay's current settlement can be updated.
        """
        extra_settlement = Settlement("Extra", (1, 1), [], [], [])

        self.overlay.current_settlement = self.TEST_SETTLEMENT
        self.overlay.update_settlement(extra_settlement)
        self.assertEqual(extra_settlement, self.overlay.current_settlement)

    def test_update_unit(self):
        """
        Ensure that the overlay's current unit can be updated.
        """
        second_unit = Unit(5, 6, (7, 8), False, UNIT_PLANS[0])

        self.overlay.selected_unit = self.TEST_UNIT
        self.overlay.update_unit(second_unit)
        self.assertEqual(second_unit, self.overlay.selected_unit)

    def test_toggle_deployment(self):
        """
        Ensure that the player can toggle the Deployment overlay correctly.
        """
        self.overlay.showing = [OverlayType.DEPLOYMENT]
        self.overlay.toggle_deployment()
        self.assertFalse(self.overlay.is_deployment())

        self.overlay.showing = []
        self.overlay.toggle_deployment()
        self.assertTrue(self.overlay.is_deployment())

    def test_toggle_unit(self):
        """
        Ensure that the player can toggle the Unit overlay correctly.
        """
        # When the Unit and Settlement Click overlays are both displayed, toggling the Settlement overlay should do
        # nothing.
        self.overlay.showing = [OverlayType.UNIT, OverlayType.SETL_CLICK]
        self.overlay.toggle_unit(None)
        self.assertTrue(self.overlay.is_unit())

        # However, when only the Unit overlay is displayed, toggling should remove it.
        self.overlay.showing = [OverlayType.UNIT]
        self.overlay.toggle_unit(None)
        self.assertFalse(self.overlay.is_unit())

        # When displaying the Warning overlay (or a number of others), toggling should not add the Unit overlay.
        self.overlay.showing = [OverlayType.WARNING]
        self.overlay.toggle_unit(None)
        self.assertFalse(self.overlay.is_unit())

        # When not showing any other overlays, toggling should display the Unit overlay, while updating the selected
        # unit.
        self.overlay.showing = []
        self.overlay.toggle_unit(self.TEST_UNIT)
        self.assertTrue(self.overlay.is_unit())
        self.assertEqual(self.TEST_UNIT, self.overlay.selected_unit)


if __name__ == '__main__':
    unittest.main()
