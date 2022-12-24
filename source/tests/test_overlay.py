import unittest

from source.display.overlay import Overlay
from source.foundation.catalogue import UNIT_PLANS
from source.foundation.models import OverlayType, Settlement, Player, Faction, ConstructionMenu, Project, ProjectType, \
    Improvement, Effect, ImprovementType, UnitPlan, Blessing, Unit, CompletedConstruction, AttackData, HealData, \
    SetlAttackData, Victory, VictoryType, SettlementAttackType


class OverlayTest(unittest.TestCase):
    """
    The test class for overlay.py.
    """
    TEST_SETTLEMENT = Settlement("Testville", (0, 0), [], [], [])
    TEST_UNIT = Unit(1, 2, (3, 4), False, UNIT_PLANS[0])
    TEST_UNIT_2 = Unit(5, 6, (7, 8), False, UNIT_PLANS[0])
    TEST_BLESSING = Blessing("Cool", "Magic", 0)
    TEST_IMPROVEMENT = Improvement(ImprovementType.BOUNTIFUL, 0, "More", "Food", Effect(), None)
    TEST_PLAYER = Player("Bob", Faction.NOCTURNE, 0, 0, [TEST_SETTLEMENT], [], [], set(), set())

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
        Ensure that the Construction overlay can be toggled correctly.
        """
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
        self.overlay.toggle_construction([self.TEST_IMPROVEMENT], [test_project], [test_unit_plan])
        self.assertTrue(self.overlay.is_constructing())
        self.assertEqual([self.TEST_IMPROVEMENT], self.overlay.available_constructions)
        self.assertEqual([test_project], self.overlay.available_projects)
        self.assertEqual([test_unit_plan], self.overlay.available_unit_plans)
        # Since an improvement has been supplied, the Improvements tab should be displayed, with the supplied
        # improvement selected and the boundaries reset.
        self.assertEqual(ConstructionMenu.IMPROVEMENTS, self.overlay.current_construction_menu)
        self.assertEqual(self.TEST_IMPROVEMENT, self.overlay.selected_construction)
        self.assertTupleEqual((0, 5), self.overlay.construction_boundaries)

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
        self.assertEqual([self.TEST_BLESSING], self.overlay.available_blessings)
        self.assertEqual(self.TEST_BLESSING, self.overlay.selected_blessing)
        self.assertTupleEqual((0, 5), self.overlay.blessing_boundaries)

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
        extra_settlement = Settlement("Extra", (1, 1), [], [], [])

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

    def test_update_turn(self):
        """
        Ensure that the turn can be successfully updated.
        """
        test_turn = 999
        self.overlay.current_turn = 1
        self.overlay.update_turn(test_turn)
        self.assertEqual(test_turn, self.overlay.current_turn)

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
        self.assertEqual([self.TEST_SETTLEMENT], self.overlay.problematic_settlements)
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
        self.assertEqual([test_completed], self.overlay.completed_constructions)

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
        self.assertEqual([self.TEST_SETTLEMENT], self.overlay.levelled_up_settlements)

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
        test_vic = Victory(self.TEST_PLAYER, VictoryType.VIGOUR)
        self.assertFalse(self.overlay.is_victory())
        self.overlay.toggle_victory(test_vic)
        self.assertTrue(self.overlay.is_victory())
        self.assertEqual(test_vic, self.overlay.current_victory)

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


if __name__ == '__main__':
    unittest.main()
