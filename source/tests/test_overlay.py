import typing
import unittest

from source.display.overlay import Overlay
from source.foundation.catalogue import UNIT_PLANS, ACHIEVEMENTS
from source.foundation.models import OverlayType, Settlement, Player, Faction, ConstructionMenu, Project, ProjectType, \
    Improvement, Effect, ImprovementType, UnitPlan, Blessing, Unit, CompletedConstruction, AttackData, HealData, \
    SetlAttackData, Victory, VictoryType, SettlementAttackType, PauseOption, InvestigationResult, DeployerUnitPlan, \
    DeployerUnit, GameConfig, ResourceCollection, StandardOverlayView


class OverlayTest(unittest.TestCase):
    """
    The test class for overlay.py.
    """

    def setUp(self) -> None:
        """
        Instantiate a standard Overlay object before each test and initialise test models.
        """
        self.TEST_CONFIG = GameConfig(14, Faction.INFIDELS, True, True, True, False)
        self.overlay = Overlay(self.TEST_CONFIG)
        self.TEST_SETTLEMENT = Settlement("Testville", (0, 0), [], [], ResourceCollection(), [])
        self.TEST_UNIT = Unit(1, 2, (3, 4), False, UNIT_PLANS[0])
        self.TEST_UNIT_2 = Unit(5, 6, (7, 8), False, UNIT_PLANS[0])
        self.TEST_BLESSING = Blessing("Cool", "Magic", 0)
        self.TEST_BLESSING_2 = Blessing("Uncool", "Science", 0)
        self.TEST_IMPROVEMENT = Improvement(ImprovementType.BOUNTIFUL, 0, "More", "Food", Effect(), None)
        self.TEST_IMPROVEMENT_2 = Improvement(ImprovementType.MAGICAL, 0, "Magic", "Time", Effect(), None)
        self.TEST_PLAYER = Player("Bob", Faction.NOCTURNE, 0, settlements=[self.TEST_SETTLEMENT])
        self.TEST_VICTORY = Victory(self.TEST_PLAYER, VictoryType.VIGOUR)
        self.TEST_PROJECT = Project(ProjectType.MAGICAL, "Magic", "Project")
        self.TEST_PROJECT_2 = Project(ProjectType.BOUNTIFUL, "Food", "Project")
        self.TEST_UNIT_PLAN = UnitPlan(0, 0, 1, "Weakling", None, 0)
        self.TEST_UNIT_PLAN_2 = UnitPlan(999, 999, 999, "Strongman", None, 0)

    def test_toggle_standard(self):
        """
        Ensure that the overlay correctly toggles the Standard overlay.
        """
        # When the Standard and Blessing overlays are being displayed, toggling should not remove the Standard overlay.
        self.overlay.showing = [OverlayType.STANDARD, OverlayType.BLESSING]
        self.overlay.toggle_standard()
        self.assertTrue(self.overlay.is_standard())

        # Now with only the Standard overlay, toggling should remove it.
        self.overlay.showing = [OverlayType.STANDARD]
        self.overlay.toggle_standard()
        self.assertFalse(self.overlay.is_standard())

        # When displaying the Pause overlay (or a number of others), toggling should not add the Standard overlay.
        self.overlay.showing = [OverlayType.PAUSE]
        self.overlay.toggle_standard()
        self.assertFalse(self.overlay.is_standard())

        # When no overlay is being displayed, toggling should add the Standard overlay.
        self.overlay.showing = []
        self.overlay.toggle_standard()
        self.assertTrue(self.overlay.is_standard())

    def test_navigate_standard(self):
        """
        Ensure that the standard overlay can be successfully navigated.
        """
        self.overlay.current_player = Player("Tester", Faction.NOCTURNE, 0)

        # Begin by testing that the various standard overlay views can be toggled between.
        self.assertEqual(StandardOverlayView.BLESSINGS, self.overlay.current_standard_overlay_view)

        self.overlay.navigate_standard(right=True)
        self.assertEqual(StandardOverlayView.VAULT, self.overlay.current_standard_overlay_view)
        self.overlay.navigate_standard(right=True)
        self.assertEqual(StandardOverlayView.SETTLEMENTS, self.overlay.current_standard_overlay_view)
        self.overlay.navigate_standard(right=True)
        self.assertEqual(StandardOverlayView.VICTORIES, self.overlay.current_standard_overlay_view)
        # Pressing right when already on the last view should have no effect.
        self.overlay.navigate_standard(right=True)
        self.assertEqual(StandardOverlayView.VICTORIES, self.overlay.current_standard_overlay_view)

        self.overlay.navigate_standard(left=True)
        self.assertEqual(StandardOverlayView.SETTLEMENTS, self.overlay.current_standard_overlay_view)
        self.overlay.navigate_standard(left=True)
        self.assertEqual(StandardOverlayView.VAULT, self.overlay.current_standard_overlay_view)
        self.overlay.navigate_standard(left=True)
        self.assertEqual(StandardOverlayView.BLESSINGS, self.overlay.current_standard_overlay_view)
        # Pressing left when already on the first view should have no effect.
        self.overlay.navigate_standard(left=True)
        self.assertEqual(StandardOverlayView.BLESSINGS, self.overlay.current_standard_overlay_view)

        # To begin with, the current player has no settlements at all. As such, navigating downwards shouldn't do
        # anything.
        self.assertTupleEqual((0, 9), self.overlay.settlement_status_boundaries)
        self.overlay.navigate_standard(down=True)
        self.assertTupleEqual((0, 9), self.overlay.settlement_status_boundaries)

        # Now give the player some settlements.
        self.overlay.current_player.settlements = [Settlement("Test", (0, 0), [], [], ResourceCollection(), [])] * 10
        self.overlay.navigate_standard(down=True)
        # However! We still expect no change because the player is not on the settlements view.
        self.assertTupleEqual((0, 9), self.overlay.settlement_status_boundaries)

        self.overlay.current_standard_overlay_view = StandardOverlayView.SETTLEMENTS
        # Now on the settlements view, the player should be able to navigate now.
        self.overlay.navigate_standard(down=True)
        self.assertTupleEqual((1, 10), self.overlay.settlement_status_boundaries)
        # However, since they only have one more than the threshold, they should only be able to navigate down once.
        self.overlay.navigate_standard(down=True)
        self.assertTupleEqual((1, 10), self.overlay.settlement_status_boundaries)

        # Navigating upwards should work initially, but once the player has reached the top again, should then do
        # nothing.
        self.overlay.navigate_standard(up=True)
        self.assertTupleEqual((0, 9), self.overlay.settlement_status_boundaries)
        self.overlay.navigate_standard(up=True)
        self.assertTupleEqual((0, 9), self.overlay.settlement_status_boundaries)

    def test_toggle_construction(self):
        """
        Ensure that the Construction overlay can be toggled correctly.
        """
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
        self.overlay.toggle_construction([], [self.TEST_PROJECT], [])
        self.assertTrue(self.overlay.is_constructing())
        self.assertFalse(self.overlay.available_constructions)
        self.assertListEqual([self.TEST_PROJECT], self.overlay.available_projects)
        self.assertFalse(self.overlay.available_unit_plans)
        # However, since there are no improvements to construct, the overlay is initialised on the Projects tab, with
        # the supplied project selected.
        self.assertEqual(ConstructionMenu.PROJECTS, self.overlay.current_construction_menu)
        self.assertEqual(self.TEST_PROJECT, self.overlay.selected_construction)

        # Toggle from the beginning once again, this time with an available construction for each category.
        self.overlay.showing = []
        self.overlay.toggle_construction([self.TEST_IMPROVEMENT], [self.TEST_PROJECT], [self.TEST_UNIT_PLAN])
        self.assertTrue(self.overlay.is_constructing())
        self.assertListEqual([self.TEST_IMPROVEMENT], self.overlay.available_constructions)
        self.assertListEqual([self.TEST_PROJECT], self.overlay.available_projects)
        self.assertListEqual([self.TEST_UNIT_PLAN], self.overlay.available_unit_plans)
        # Since an improvement has been supplied, the Improvements tab should be displayed, with the supplied
        # improvement selected and the boundaries reset.
        self.assertEqual(ConstructionMenu.IMPROVEMENTS, self.overlay.current_construction_menu)
        self.assertEqual(self.TEST_IMPROVEMENT, self.overlay.selected_construction)
        self.assertTupleEqual((0, 5), self.overlay.construction_boundaries)

    def test_navigate_constructions_improvements(self):
        """
        Ensure that the player can effectively navigate through their available improvements for a settlement.
        """
        self.overlay.toggle_construction([self.TEST_IMPROVEMENT, self.TEST_IMPROVEMENT_2], [], [])
        # Note that we set some odd boundaries here - this is so we don't require several test improvements.
        self.overlay.construction_boundaries = 0, 0

        self.assertEqual(self.TEST_IMPROVEMENT, self.overlay.selected_construction)
        self.overlay.navigate_constructions(down=True)
        # Navigating down once should select the second improvement, and shift the boundaries down.
        self.assertEqual(self.TEST_IMPROVEMENT_2, self.overlay.selected_construction)
        self.assertTupleEqual((1, 1), self.overlay.construction_boundaries)

        self.overlay.navigate_constructions(down=True)
        # Navigating down again should select the cancel button, leaving the boundaries unaffected.
        self.assertIsNone(self.overlay.selected_construction)
        self.assertTupleEqual((1, 1), self.overlay.construction_boundaries)

        self.overlay.navigate_constructions(down=True)
        # When the cancel button is already selected, pressing down again has no effect.
        self.assertIsNone(self.overlay.selected_construction)
        self.assertTupleEqual((1, 1), self.overlay.construction_boundaries)

        self.overlay.navigate_constructions(down=False)
        # Now if we navigate upwards, the second improvement should be selected again.
        self.assertEqual(self.TEST_IMPROVEMENT_2, self.overlay.selected_construction)
        self.assertTupleEqual((1, 1), self.overlay.construction_boundaries)

        self.overlay.navigate_constructions(down=False)
        # Going up again should select the first improvement and shift the boundaries up.
        self.assertEqual(self.TEST_IMPROVEMENT, self.overlay.selected_construction)
        self.assertTupleEqual((0, 0), self.overlay.construction_boundaries)

        self.overlay.navigate_constructions(down=False)
        # If we are at the top, pressing up should have no effect.
        self.assertEqual(self.TEST_IMPROVEMENT, self.overlay.selected_construction)
        self.assertTupleEqual((0, 0), self.overlay.construction_boundaries)

    def test_navigate_constructions_projects(self):
        """
        Ensure that the player can effectively navigate through their available projects for a settlement.
        :return:
        """
        self.overlay.toggle_construction([], [self.TEST_PROJECT, self.TEST_PROJECT_2], [])

        self.assertEqual(self.TEST_PROJECT, self.overlay.selected_construction)
        self.overlay.navigate_constructions(down=True)
        # Navigating down once should select the second project.
        self.assertEqual(self.TEST_PROJECT_2, self.overlay.selected_construction)

        self.overlay.navigate_constructions(down=True)
        # Navigating down again should select the cancel button.
        self.assertIsNone(self.overlay.selected_construction)

        self.overlay.navigate_constructions(down=True)
        # When the cancel button is already selected, pressing down again has no effect.
        self.assertIsNone(self.overlay.selected_construction)

        self.overlay.navigate_constructions(down=False)
        # Now if we navigate upwards, the second project should be selected again.
        self.assertEqual(self.TEST_PROJECT_2, self.overlay.selected_construction)

        self.overlay.navigate_constructions(down=False)
        # Going up again should select the first project.
        self.assertEqual(self.TEST_PROJECT, self.overlay.selected_construction)

        self.overlay.navigate_constructions(down=False)
        # If we are at the top, pressing up should have no effect.
        self.assertEqual(self.TEST_PROJECT, self.overlay.selected_construction)

    def test_navigate_constructions_units(self):
        """
        Ensure that the player can effectively navigate through their available units for a settlement.
        """
        # We have to do a few things here to set up the test. Firstly, when toggling the construction overlay, we also
        # have to supply a project in addition to our unit plans since when no improvements are supplied, projects are
        # initially displayed. We then simulate the player going to the units menu. Lastly, we set the boundaries for
        # the unit plans menu, so as to not require several test unit plans.
        self.overlay.toggle_construction([], [self.TEST_PROJECT], [self.TEST_UNIT_PLAN, self.TEST_UNIT_PLAN_2])
        self.overlay.current_construction_menu = ConstructionMenu.UNITS
        self.overlay.selected_construction = self.TEST_UNIT_PLAN
        self.overlay.unit_plan_boundaries = 0, 0

        self.assertEqual(self.TEST_UNIT_PLAN, self.overlay.selected_construction)
        self.overlay.navigate_constructions(down=True)
        # Navigating down once should select the second unit plan, and shift the boundaries down.
        self.assertEqual(self.TEST_UNIT_PLAN_2, self.overlay.selected_construction)
        self.assertTupleEqual((1, 1), self.overlay.unit_plan_boundaries)

        self.overlay.navigate_constructions(down=True)
        # Navigating down again should select the cancel button, leaving the boundaries unaffected.
        self.assertIsNone(self.overlay.selected_construction)
        self.assertTupleEqual((1, 1), self.overlay.unit_plan_boundaries)

        self.overlay.navigate_constructions(down=True)
        # When the cancel button is already selected, pressing down again has no effect.
        self.assertIsNone(self.overlay.selected_construction)
        self.assertTupleEqual((1, 1), self.overlay.unit_plan_boundaries)

        self.overlay.navigate_constructions(down=False)
        # Now if we navigate upwards, the second unit plan should be selected again.
        self.assertEqual(self.TEST_UNIT_PLAN_2, self.overlay.selected_construction)
        self.assertTupleEqual((1, 1), self.overlay.unit_plan_boundaries)

        self.overlay.navigate_constructions(down=False)
        # Going up again should select the first unit plan and shift the boundaries up.
        self.assertEqual(self.TEST_UNIT_PLAN, self.overlay.selected_construction)
        self.assertTupleEqual((0, 0), self.overlay.unit_plan_boundaries)

        self.overlay.navigate_constructions(down=False)
        # If we are at the top, pressing up should have no effect.
        self.assertEqual(self.TEST_UNIT_PLAN, self.overlay.selected_construction)
        self.assertTupleEqual((0, 0), self.overlay.unit_plan_boundaries)

    def test_toggle_blessing(self):
        """
        Ensure that the player can toggle the Blessing overlay correctly.
        """
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
        self.overlay.toggle_blessing([self.TEST_BLESSING])
        self.assertTrue(self.overlay.is_blessing())
        self.assertListEqual([self.TEST_BLESSING], self.overlay.available_blessings)
        self.assertEqual(self.TEST_BLESSING, self.overlay.selected_blessing)
        self.assertTupleEqual((0, 5), self.overlay.blessing_boundaries)

    def test_navigate_blessings(self):
        """
        Ensure that the player can effectively navigate through their available blessings.
        """
        self.overlay.toggle_blessing([self.TEST_BLESSING, self.TEST_BLESSING_2])
        # Note that we set some odd boundaries here - this is so we don't require several test blessings.
        self.overlay.blessing_boundaries = 0, 0

        self.assertEqual(self.TEST_BLESSING, self.overlay.selected_blessing)
        self.overlay.navigate_blessings(down=True)
        # Navigating down once should select the second blessing, and shift the boundaries down.
        self.assertEqual(self.TEST_BLESSING_2, self.overlay.selected_blessing)
        self.assertTupleEqual((1, 1), self.overlay.blessing_boundaries)

        self.overlay.navigate_blessings(down=True)
        # Navigating down again should select the cancel button, leaving the boundaries unaffected.
        self.assertIsNone(self.overlay.selected_blessing)
        self.assertTupleEqual((1, 1), self.overlay.blessing_boundaries)

        self.overlay.navigate_blessings(down=True)
        # When the cancel button is already selected, pressing down again has no effect.
        self.assertIsNone(self.overlay.selected_blessing)
        self.assertTupleEqual((1, 1), self.overlay.blessing_boundaries)

        self.overlay.navigate_blessings(down=False)
        # Now if we navigate upwards, the second blessing should be selected again.
        self.assertEqual(self.TEST_BLESSING_2, self.overlay.selected_blessing)
        self.assertTupleEqual((1, 1), self.overlay.blessing_boundaries)

        self.overlay.navigate_blessings(down=False)
        # Going up again should select the first blessing and shift the boundaries up.
        self.assertEqual(self.TEST_BLESSING, self.overlay.selected_blessing)
        self.assertTupleEqual((0, 0), self.overlay.blessing_boundaries)

        self.overlay.navigate_blessings(down=False)
        # If we are at the top, pressing up should have no effect.
        self.assertEqual(self.TEST_BLESSING, self.overlay.selected_blessing)
        self.assertTupleEqual((0, 0), self.overlay.blessing_boundaries)

    def test_toggle_settlement(self):
        """
        Ensure that the Settlement overlay can be toggled correctly.
        """
        # When the Settlement and Construction overlays are both displayed, toggling the Settlement overlay should do
        # nothing.
        self.overlay.showing = [OverlayType.SETTLEMENT, OverlayType.CONSTRUCTION]
        self.overlay.toggle_settlement(None, self.TEST_PLAYER)
        self.assertTrue(self.overlay.is_setl())

        # However, when only the Settlement overlay is displayed, toggling should remove it.
        self.overlay.showing = [OverlayType.SETTLEMENT]
        self.overlay.toggle_settlement(None, self.TEST_PLAYER)
        self.assertFalse(self.overlay.is_setl())

        # When displaying the Investigation overlay (or a number of others), toggling should not add the Settlement
        # overlay.
        self.overlay.showing = [OverlayType.INVESTIGATION]
        self.overlay.toggle_settlement(None, self.TEST_PLAYER)
        self.assertFalse(self.overlay.is_setl())

        # When not showing any other overlays, toggling should display the Settlement overlay, while updating the
        # current settlement and player.
        self.overlay.showing = []
        self.overlay.toggle_settlement(self.TEST_SETTLEMENT, self.TEST_PLAYER)
        self.assertTrue(self.overlay.is_setl())
        self.assertEqual(self.TEST_SETTLEMENT, self.overlay.current_settlement)
        self.assertEqual(self.TEST_PLAYER, self.overlay.current_player)

    def test_update_settlement(self):
        """
        Ensure that the overlay's current settlement can be updated.
        """
        extra_settlement = Settlement("Extra", (1, 1), [], [], ResourceCollection(), [])

        self.overlay.current_settlement = self.TEST_SETTLEMENT
        self.overlay.update_settlement(extra_settlement)
        self.assertEqual(extra_settlement, self.overlay.current_settlement)

    def test_update_unit(self):
        """
        Ensure that the overlay's current unit can be updated.
        """
        self.overlay.selected_unit = self.TEST_UNIT
        self.overlay.update_unit(self.TEST_UNIT_2)
        self.assertEqual(self.TEST_UNIT_2, self.overlay.selected_unit)

    def test_toggle_deployment(self):
        """
        Ensure that the Deployment overlay can be toggled correctly.
        """
        self.overlay.showing = [OverlayType.DEPLOYMENT]
        self.overlay.toggle_deployment()
        self.assertFalse(self.overlay.is_deployment())

        self.overlay.showing = []
        self.overlay.toggle_deployment()
        self.assertTrue(self.overlay.is_deployment())

    def test_toggle_unit(self):
        """
        Ensure that the Unit overlay can be toggled correctly.
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

    def test_toggle_tutorial(self):
        """
        Ensure that the Tutorial overlay can be toggled correctly.
        """
        self.overlay.showing = [OverlayType.TUTORIAL]
        self.overlay.toggle_tutorial()
        self.assertFalse(self.overlay.is_tutorial())

        self.overlay.showing = []
        self.overlay.toggle_tutorial()
        self.assertTrue(self.overlay.is_tutorial())

    def test_setl_unit_iteration(self):
        """
        Ensure that the correct responses are returned when determining if a player can iterate through their
        settlements or units.
        """
        # Naturally, when no overlays are displayed, iteration can occur.
        self.overlay.showing = []
        self.assertTrue(self.overlay.can_iter_settlements_units())

        # Similarly, when a non-intrusive overlay such as the Attack overlay is displayed, iteration can still occur.
        self.overlay.showing = [OverlayType.ATTACK]
        self.assertTrue(self.overlay.can_iter_settlements_units())

        # However, when an obstructive overlay is displayed alongside a non-intrusive one, iteration should be
        # prevented.
        self.overlay.showing = [OverlayType.VICTORY, OverlayType.ATTACK]
        self.assertFalse(self.overlay.can_iter_settlements_units())

        # Of course, when a single obstructive overlay is displayed, iteration should also be prevented.
        self.overlay.showing = [OverlayType.STANDARD]
        self.assertFalse(self.overlay.can_iter_settlements_units())

    def test_jump_to_setl(self):
        """
        Ensure that the correct responses are returned when determining if a player can jump to their idle settlements.
        """
        # Naturally, when no overlays are displayed, iteration can occur.
        self.overlay.showing = []
        self.assertTrue(self.overlay.can_jump_to_setl())

        # Similarly, when a non-intrusive overlay such as the Attack overlay is displayed, iteration can still occur.
        self.overlay.showing = [OverlayType.ATTACK]
        self.assertTrue(self.overlay.can_jump_to_setl())

        # However, when an obstructive overlay is displayed alongside a non-intrusive one, iteration should be
        # prevented.
        self.overlay.showing = [OverlayType.VICTORY, OverlayType.ATTACK]
        self.assertFalse(self.overlay.can_jump_to_setl())

        # Of course, when a single obstructive overlay is displayed, iteration should also be prevented.
        self.overlay.showing = [OverlayType.INVESTIGATION]
        self.assertFalse(self.overlay.can_jump_to_setl())

    def test_toggle_warning(self):
        """
        Ensure that the Warning overlay can be toggled correctly.
        """
        self.overlay.showing = [OverlayType.WARNING]
        self.overlay.toggle_warning([], False, False)
        self.assertFalse(self.overlay.is_warning())

        # When there are no overlays displayed and a toggle occurs, the warning overlay should be displayed, along with
        # the supplied details.
        self.overlay.showing = []
        self.overlay.toggle_warning([self.TEST_SETTLEMENT], True, True)
        self.assertTrue(self.overlay.is_warning())
        self.assertListEqual([self.TEST_SETTLEMENT], self.overlay.problematic_settlements)
        self.assertTrue(self.overlay.has_no_blessing)
        self.assertTrue(self.overlay.will_have_negative_wealth)

    def test_remove_warning_if_possible(self):
        """
        Ensure that the Warning overlay is removed, if possible, in the two distinct situations.
        """
        # Even though the Warning overlay is not currently displayed, the method should still execute without error,
        # maintaining the current state of the array of shown overlays.
        self.overlay.showing = []
        self.overlay.remove_warning_if_possible()
        self.assertFalse(self.overlay.showing)

        # In its primary use case, the Warning overlay should be removed when displayed.
        self.overlay.showing = [OverlayType.WARNING]
        self.overlay.remove_warning_if_possible()
        self.assertFalse(self.overlay.is_warning())

    def test_toggle_blessing_notification(self):
        """
        Ensure that the Blessing Notification overlay can be toggled correctly.
        """
        self.overlay.showing = [OverlayType.BLESS_NOTIF]
        self.overlay.toggle_blessing_notification(None)
        self.assertFalse(self.overlay.is_bless_notif())

        # When not being shown, toggling should display the Blessing Notification overlay, along with the supplied
        # Blessing.
        self.overlay.showing = []
        self.overlay.toggle_blessing_notification(self.TEST_BLESSING)
        self.assertTrue(self.overlay.is_bless_notif())
        self.assertEqual(self.TEST_BLESSING, self.overlay.completed_blessing)

    def test_toggle_construction_notification(self):
        """
        Ensure that the Construction Notification overlay can be toggled correctly.
        """
        test_completed = CompletedConstruction(self.TEST_IMPROVEMENT, self.TEST_SETTLEMENT)

        self.overlay.showing = [OverlayType.CONSTR_NOTIF]
        self.overlay.toggle_construction_notification([])
        self.assertFalse(self.overlay.is_constr_notif())

        # When not being shown, toggling should display the Construction Notification overlay, with the supplied
        # completed construction.
        self.overlay.showing = []
        self.overlay.toggle_construction_notification([test_completed])
        self.assertTrue(self.overlay.is_constr_notif())
        self.assertListEqual([test_completed], self.overlay.completed_constructions)

    def test_toggle_level_up_notification(self):
        """
        Ensure that the Level Up Notification overlay can be toggled correctly.
        """
        self.overlay.showing = [OverlayType.LEVEL_NOTIF]
        self.overlay.toggle_level_up_notification([])
        self.assertFalse(self.overlay.is_lvl_notif())

        # When not being shown, toggling should display the Level Up Notification overlay, and the affected settlement.
        self.overlay.showing = []
        self.overlay.toggle_level_up_notification([self.TEST_SETTLEMENT])
        self.assertTrue(self.overlay.is_lvl_notif())
        self.assertListEqual([self.TEST_SETTLEMENT], self.overlay.levelled_up_settlements)

    def test_toggle_attack(self):
        """
        Ensure that the Attack overlay can be toggled correctly.
        """
        test_data = AttackData(self.TEST_UNIT, self.TEST_UNIT_2, 50, 20, True, True, False)

        # If an attack is currently being displayed, and a toggle occurs with None provided, the overlay should be
        # removed.
        self.overlay.showing = [OverlayType.ATTACK]
        self.overlay.toggle_attack(None)
        self.assertFalse(self.overlay.is_attack())

        # However, if the overlay is active and toggled with new data, the overlay should remain displayed with the new
        # data.
        self.overlay.showing = [OverlayType.ATTACK]
        self.overlay.toggle_attack(test_data)
        self.assertTrue(self.overlay.is_attack())
        self.assertEqual(test_data, self.overlay.attack_data)

        # Lastly, if the overlay is not being displayed, toggling it should display it and the supplied data.
        self.overlay.showing = []
        self.overlay.attack_data = None
        self.overlay.toggle_attack(test_data)
        self.assertTrue(self.overlay.is_attack())
        self.assertEqual(test_data, self.overlay.attack_data)

    def test_toggle_heal(self):
        """
        Ensure that the Heal overlay can be toggled correctly.
        """
        test_data = HealData(self.TEST_UNIT, self.TEST_UNIT_2, 9000, 1, True)

        # If a heal is currently being displayed, and a toggle occurs with None provided, the overlay should be
        # removed.
        self.overlay.showing = [OverlayType.HEAL]
        self.overlay.toggle_heal(None)
        self.assertFalse(self.overlay.is_heal())

        # However, if the overlay is active and toggled with new data, the overlay should remain displayed with the new
        # data.
        self.overlay.showing = [OverlayType.HEAL]
        self.overlay.toggle_heal(test_data)
        self.assertTrue(self.overlay.is_heal())
        self.assertEqual(test_data, self.overlay.heal_data)

        # Lastly, if the overlay is not being displayed, toggling it should display it and the supplied data.
        self.overlay.showing = []
        self.overlay.heal_data = None
        self.overlay.toggle_heal(test_data)
        self.assertTrue(self.overlay.is_heal())
        self.assertEqual(test_data, self.overlay.heal_data)

    def test_toggle_setl_attack(self):
        """
        Ensure that the Settlement Attack overlay can be toggled correctly.
        """
        test_data = SetlAttackData(self.TEST_UNIT, self.TEST_SETTLEMENT, self.TEST_PLAYER, 5000, 1, True, True, False)

        # If an attack is currently being displayed, and a toggle occurs with None provided, the overlay should be
        # removed.
        self.overlay.showing = [OverlayType.SETL_ATTACK]
        self.overlay.toggle_setl_attack(None)
        self.assertFalse(self.overlay.is_setl_attack())

        # However, if the overlay is active and toggled with new data, the overlay should remain displayed with the new
        # data.
        self.overlay.showing = [OverlayType.SETL_ATTACK]
        self.overlay.toggle_setl_attack(test_data)
        self.assertTrue(self.overlay.is_setl_attack())
        self.assertEqual(test_data, self.overlay.setl_attack_data)

        # Lastly, if the overlay is not being displayed, toggling it should display it and the supplied data.
        self.overlay.showing = []
        self.overlay.setl_attack_data = None
        self.overlay.toggle_setl_attack(test_data)
        self.assertTrue(self.overlay.is_setl_attack())
        self.assertEqual(test_data, self.overlay.setl_attack_data)

    def test_toggle_siege_notif(self):
        """
        Ensure that the Siege Notification overlay can be toggled correctly.
        """
        self.overlay.showing = [OverlayType.SIEGE_NOTIF]
        self.overlay.toggle_siege_notif(None, None)
        self.assertFalse(self.overlay.is_siege_notif())

        # When not shown, toggling should display it along with the supplied settlement and player.
        self.overlay.showing = []
        self.overlay.toggle_siege_notif(self.TEST_SETTLEMENT, self.TEST_PLAYER)
        self.assertTrue(self.overlay.is_siege_notif())
        self.assertEqual(self.TEST_SETTLEMENT, self.overlay.sieged_settlement)
        self.assertEqual(self.TEST_PLAYER, self.overlay.sieger_of_settlement)

    def test_toggle_victory(self):
        """
        Ensure that the Victory overlay can be toggled on correctly. Note that the Victory overlay is a special
        case - it can only be toggled on.
        """
        self.assertFalse(self.overlay.is_victory())
        self.overlay.toggle_victory(self.TEST_VICTORY)
        self.assertTrue(self.overlay.is_victory())
        self.assertEqual(self.TEST_VICTORY, self.overlay.current_victory)

    def test_toggle_setl_click(self):
        """
        Ensure that the Settlement Click overlay can be toggled correctly.
        """
        # When being shown, toggling should remove the overlay.
        self.overlay.showing = [OverlayType.SETL_CLICK]
        self.overlay.toggle_setl_click(None, None)
        self.assertFalse(self.overlay.is_setl_click())

        # When displaying the Pause overlay (or a number of others), toggling should not add the Settlement Click
        # overlay.
        self.overlay.showing = [OverlayType.PAUSE]
        self.overlay.toggle_setl_click(None, None)
        self.assertFalse(self.overlay.is_setl_click())

        # But when no overlays are being displayed, toggling should add the overlay and set the affected parties.
        self.overlay.showing = []
        self.overlay.toggle_setl_click(self.TEST_SETTLEMENT, self.TEST_PLAYER)
        self.assertTrue(self.overlay.is_setl_click())
        self.assertEqual(SettlementAttackType.ATTACK, self.overlay.setl_attack_opt)
        self.assertEqual(self.TEST_SETTLEMENT, self.overlay.attacked_settlement)
        self.assertEqual(self.TEST_PLAYER, self.overlay.attacked_settlement_owner)

    def test_navigate_setl_click(self):
        """
        Ensure that the player can successfully navigate the Settlement Click overlay.
        """
        # Pressing the down arrow key should select the Cancel option (represented as None).
        self.overlay.setl_attack_opt = SettlementAttackType.ATTACK
        self.overlay.navigate_setl_click(down=True)
        self.assertIsNone(self.overlay.setl_attack_opt)

        # Pressing the up arrow key should select the Attack option.
        self.overlay.setl_attack_opt = None
        self.overlay.navigate_setl_click(up=True)
        self.assertEqual(SettlementAttackType.ATTACK, self.overlay.setl_attack_opt)

        # Similarly, the left arrow key should also select the Attack option.
        self.overlay.setl_attack_opt = None
        self.overlay.navigate_setl_click(left=True)
        self.assertEqual(SettlementAttackType.ATTACK, self.overlay.setl_attack_opt)

        # Lastly, pressing the right arrow key should select the Besiege option.
        self.overlay.setl_attack_opt = None
        self.overlay.navigate_setl_click(right=True)
        self.assertEqual(SettlementAttackType.BESIEGE, self.overlay.setl_attack_opt)

    def test_toggle_pause(self):
        """
        Ensure that the Pause overlay can be toggled correctly.
        """
        # When the Controls overlay is shown along with the Pause overlay, toggling it should have no effect.
        self.overlay.showing = [OverlayType.PAUSE, OverlayType.CONTROLS]
        self.overlay.toggle_pause()
        self.assertTrue(self.overlay.is_pause())

        # However, when only the Pause overlay is displayed, toggling should remove it.
        self.overlay.showing = [OverlayType.PAUSE]
        self.overlay.toggle_pause()
        self.assertFalse(self.overlay.is_pause())

        # When either of the Victory or Tutorial overlays are displayed, the Pause overlay should not be able to be
        # toggled on.
        self.overlay.showing = [OverlayType.VICTORY]
        self.overlay.toggle_pause()
        self.assertFalse(self.overlay.is_pause())

        # Lastly, when not being shown, the Pause overlay should be displayed when toggled on, setting the pause option.
        self.overlay.showing = []
        self.overlay.toggle_pause()
        self.assertTrue(self.overlay.is_pause())
        self.assertEqual(PauseOption.RESUME, self.overlay.pause_option)
        self.assertFalse(self.overlay.has_saved)

    def test_navigate_pause(self):
        """
        Ensure that the player can successfully navigate the Pause overlay.
        """
        self.overlay.pause_option = PauseOption.RESUME
        self.overlay.has_saved = True

        # Iterating down through the overlay should change the option.
        self.overlay.navigate_pause(down=True)
        self.assertEqual(PauseOption.SAVE, self.overlay.pause_option)
        self.assertFalse(self.overlay.has_saved)
        self.overlay.navigate_pause(down=True)
        self.assertEqual(PauseOption.CONTROLS, self.overlay.pause_option)
        self.overlay.navigate_pause(down=True)
        self.assertEqual(PauseOption.QUIT, self.overlay.pause_option)
        # Once we're at the bottom, navigating downwards should do nothing.
        self.overlay.navigate_pause(down=True)
        self.assertEqual(PauseOption.QUIT, self.overlay.pause_option)

        self.overlay.has_saved = True

        # Going back up the overlay should change the option in the reverse order.
        self.overlay.navigate_pause(down=False)
        self.assertEqual(PauseOption.CONTROLS, self.overlay.pause_option)
        self.overlay.navigate_pause(down=False)
        self.assertEqual(PauseOption.SAVE, self.overlay.pause_option)
        self.assertFalse(self.overlay.has_saved)
        self.overlay.navigate_pause(down=False)
        self.assertEqual(PauseOption.RESUME, self.overlay.pause_option)
        # Once again at the top, navigating upwards shouldn't do anything.
        self.overlay.navigate_pause(down=False)
        self.assertEqual(PauseOption.RESUME, self.overlay.pause_option)

    def test_toggle_controls(self):
        """
        Ensure that the Controls overlay can be toggled correctly.
        """
        # When displayed, toggling should remove the overlay.
        self.overlay.showing = [OverlayType.CONTROLS]
        self.overlay.toggle_controls()
        self.assertFalse(self.overlay.is_controls())

        # If the Victory overlay is displayed, toggling the controls overlay should do nothing. Note that unlike many of
        # the other overlay types, only the Victory overlay prevents the Controls overlay from being toggled.
        self.overlay.showing = [OverlayType.VICTORY]
        self.overlay.toggle_controls()
        self.assertFalse(self.overlay.is_controls())

        # When nothing is displayed, toggling should display the overlay.
        self.overlay.showing = []
        self.overlay.toggle_controls()
        self.assertTrue(self.overlay.is_controls())

    def test_toggle_elimination(self):
        """
        Ensure that the Elimination overlay can be toggled correctly.
        """
        self.overlay.showing = [OverlayType.ELIMINATION]
        self.overlay.toggle_elimination(None)
        self.assertFalse(self.overlay.is_elimination())

        # When nothing is being displayed, toggling the overlay should display it and set the eliminated player.
        self.overlay.showing = []
        self.overlay.toggle_elimination(self.TEST_PLAYER)
        self.assertTrue(self.overlay.is_elimination())
        self.assertEqual(self.TEST_PLAYER, self.overlay.just_eliminated)

    def test_toggle_close_to_vic(self):
        """
        Ensure that the Close To Victory overlay can be toggled correctly.
        """
        self.overlay.showing = [OverlayType.CLOSE_TO_VIC]
        self.overlay.toggle_close_to_vic([])
        self.assertFalse(self.overlay.is_close_to_vic())

        # When nothing is being displayed, toggling the overlay should display it and set the relevant victories.
        self.overlay.showing = []
        self.overlay.toggle_close_to_vic([self.TEST_VICTORY])
        self.assertTrue(self.overlay.is_close_to_vic())
        self.assertListEqual([self.TEST_VICTORY], self.overlay.close_to_vics)

    def test_toggle_investigation(self):
        """
        Ensure that the Investigation overlay can be toggled correctly.
        """
        test_result = InvestigationResult.VISION

        # When the overlay is being displayed, toggling should remove it.
        self.overlay.showing = [OverlayType.INVESTIGATION]
        self.overlay.toggle_investigation(None)
        self.assertFalse(self.overlay.is_investigation())

        # When the Deployment overlay (or a multitude of others) are displayed, toggling the investigation overlay
        # should not do anything.
        self.overlay.showing = [OverlayType.DEPLOYMENT]
        self.overlay.toggle_investigation(None)
        self.assertFalse(self.overlay.is_investigation())

        # When not displayed, toggling should add the overlay and set the investigation result.
        self.overlay.showing = []
        self.overlay.toggle_investigation(test_result)
        self.assertTrue(self.overlay.is_investigation())
        self.assertEqual(test_result, self.overlay.investigation_result)

    def test_toggle_night(self):
        """
        Ensure that the Night overlay can be toggled correctly.
        """
        night_beginning = True

        # When the overlay is displayed, toggling should remove it.
        self.overlay.showing = [OverlayType.NIGHT]
        self.overlay.toggle_night(None)
        self.assertFalse(self.overlay.is_night())

        # When not displayed, toggling should add the overlay and set whether night is beginning or ending.
        self.overlay.showing = []
        self.overlay.toggle_night(night_beginning)
        self.assertTrue(self.overlay.is_night())
        self.assertEqual(night_beginning, self.overlay.night_beginning)

    def test_toggle_ach_notif(self):
        """
        Ensure that the Achievement Notification overlay can be toggled correctly.
        """
        self.overlay.showing = []

        # When not displayed, toggling should add the overlay and updated the new achievements.
        self.overlay.toggle_ach_notif(ACHIEVEMENTS[0:2])
        self.assertTrue(self.overlay.is_ach_notif())
        self.assertListEqual(ACHIEVEMENTS[0:2], self.overlay.new_achievements)

        # When toggled off, one achievement should be popped off the list. In this case, since there is still one to
        # display, the overlay remains displayed.
        self.overlay.toggle_ach_notif([])
        self.assertTrue(self.overlay.is_ach_notif())
        self.assertListEqual([ACHIEVEMENTS[0]], self.overlay.new_achievements)

        # Toggling off again, there are now no longer any achievements to display, removing the overlay.
        self.overlay.toggle_ach_notif([])
        self.assertFalse(self.overlay.is_ach_notif())
        self.assertFalse(self.overlay.new_achievements)

    def test_remove_layer(self):
        """
        Ensure that a layer from the overlay can be successfully removed.
        """
        def set_and_remove(test_class: OverlayTest,
                           overlay_type: OverlayType,
                           verification_fn: typing.Callable[[], bool],
                           should_return_none=True):
            """
            A helper method that sets the currently-shown overlay, removes a layer, and verifies that the layer has been
            removed.
            :param test_class: The OverlayTest class.
            :param overlay_type: The type of overlay being added and removed.
            :param verification_fn: The function to use to verify that the overlay has been removed.
            :param should_return_none: Whether the remove_layer() function should return None or not.
            """
            test_class.overlay.showing = [overlay_type]
            if should_return_none:
                test_class.assertIsNone(self.overlay.remove_layer())
            else:
                test_class.assertEqual(overlay_type, self.overlay.remove_layer())
            test_class.assertFalse(verification_fn())

        # We need to give the overlay a new achievement so that the toggle can pop it off the list.
        self.overlay.new_achievements = [ACHIEVEMENTS[0]]

        # Check that each overlay type can be successfully removed.
        set_and_remove(self, OverlayType.ACH_NOTIF, self.overlay.is_ach_notif)
        set_and_remove(self, OverlayType.NIGHT, self.overlay.is_night)
        set_and_remove(self, OverlayType.CLOSE_TO_VIC, self.overlay.is_close_to_vic)
        set_and_remove(self, OverlayType.BLESS_NOTIF, self.overlay.is_bless_notif)
        set_and_remove(self, OverlayType.CONSTR_NOTIF, self.overlay.is_constr_notif)
        set_and_remove(self, OverlayType.LEVEL_NOTIF, self.overlay.is_lvl_notif)
        set_and_remove(self, OverlayType.WARNING, self.overlay.is_warning)
        set_and_remove(self, OverlayType.INVESTIGATION, self.overlay.is_close_to_vic)
        set_and_remove(self, OverlayType.CONTROLS, self.overlay.is_controls)
        set_and_remove(self, OverlayType.PAUSE, self.overlay.is_pause)
        set_and_remove(self, OverlayType.BLESSING, self.overlay.is_blessing)
        set_and_remove(self, OverlayType.SETL_CLICK, self.overlay.is_setl_click)
        set_and_remove(self, OverlayType.STANDARD, self.overlay.is_standard)
        set_and_remove(self, OverlayType.CONSTRUCTION, self.overlay.is_constructing)
        # The Unit and Settlement overlays return their overlay type because in production code, the caller needs to
        # reset the selected unit/settlement as well.
        set_and_remove(self, OverlayType.UNIT, self.overlay.is_unit, should_return_none=False)
        set_and_remove(self, OverlayType.SETTLEMENT, self.overlay.is_setl, should_return_none=False)

    def test_navigate_unit(self):
        """
        Ensure that navigating the unit overlay restricts the passenger index to within the bounds of the selected
        deployer unit's number of passengers.
        """
        test_deployer_unit_plan = DeployerUnitPlan(0, 1, 2, "3", None, 4)
        test_deployer_unit = DeployerUnit(1, 2, (3, 4), False, test_deployer_unit_plan,
                                          passengers=[self.TEST_UNIT, self.TEST_UNIT_2])
        self.overlay.selected_unit = test_deployer_unit
        self.overlay.unit_passengers_idx = 0

        # Navigating down once should increase the index.
        self.overlay.navigate_unit(down=True)
        self.assertEqual(1, self.overlay.unit_passengers_idx)
        # Since there are only two passenger units, navigating down again should have no effect.
        self.overlay.navigate_unit(down=True)
        self.assertEqual(1, self.overlay.unit_passengers_idx)
        # Navigating up once should decrease the index.
        self.overlay.navigate_unit(down=False)
        self.assertEqual(0, self.overlay.unit_passengers_idx)
        # Since the index is at 0, navigating up again should have no effect.
        self.overlay.navigate_unit(down=False)
        self.assertEqual(0, self.overlay.unit_passengers_idx)


if __name__ == '__main__':
    unittest.main()
