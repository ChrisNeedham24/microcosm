import typing
import unittest
from unittest.mock import MagicMock

from source.display.board import Board
from source.foundation.catalogue import Namer, UNIT_PLANS, get_heathen_plan, IMPROVEMENTS, BLESSINGS
from source.foundation.models import GameConfig, Faction, Player, AIPlaystyle, AttackPlaystyle, ExpansionPlaystyle, \
    Unit, Heathen, Settlement, Victory, VictoryType, Construction, OngoingBlessing, EconomicStatus, UnitPlan
from source.game_management.game_state import GameState
from source.game_management.movemaker import MoveMaker


class GameStateTest(unittest.TestCase):
    """
    The test class for game_state.py.
    """
    TEST_CONFIG = GameConfig(5, Faction.NOCTURNE, True, False, True)
    TEST_NAMER = Namer()
    TEST_UNIT_PLAN = UnitPlan(100, 100, 3, "Plan Man", None, 25)
    TEST_UNIT_PLAN_2 = UnitPlan(100, 100, 3, "Man With Plan", None, 25)
    TEST_UNIT = Unit(1, 2, (3, 4), False, TEST_UNIT_PLAN)
    TEST_UNIT_2 = Unit(5, 6, (7, 8), True, TEST_UNIT_PLAN_2)
    TEST_HEATHEN = Heathen(40, 6, (3, 3), get_heathen_plan(1))
    TEST_SETTLEMENT = Settlement("Numero Uno", (0, 0), [], [], [TEST_UNIT_2])
    TEST_SETTLEMENT_2 = Settlement("Numero Duo", (1, 1), [], [], [])

    def setUp(self) -> None:
        """
        Initialise a standard GameState object with players and a board before each test. Also reset the test models.
        """
        self.game_state = GameState()
        self.game_state.players = [
            Player("Infidel", Faction.INFIDELS, 0, 0, [], [self.TEST_UNIT], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
            Player("Concentrator", Faction.CONCENTRATED, 0, 0, [], [], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
            Player("Man", Faction.FRONTIERSMEN, 0, 0, [], [], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
            Player("Royal", Faction.IMPERIALS, 0, 0, [], [], [], set(), set(),
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)),
        ]
        self.game_state.board = Board(self.TEST_CONFIG, self.TEST_NAMER)
        self.game_state.heathens = [self.TEST_HEATHEN]
        self.TEST_UNIT.location = 3, 4
        self.TEST_UNIT.health = 1
        self.TEST_UNIT_2.health = 5
        self.TEST_HEATHEN.location = 3, 3
        self.TEST_HEATHEN.health = 40
        self.TEST_HEATHEN.remaining_stamina = 6
        self.TEST_HEATHEN.plan = get_heathen_plan(1)
        self.TEST_SETTLEMENT.satisfaction = 50
        self.TEST_SETTLEMENT.level = 1
        self.TEST_SETTLEMENT.current_work = None
        self.TEST_SETTLEMENT.improvements = []
        self.TEST_SETTLEMENT.economic_status = EconomicStatus.STANDARD
        self.TEST_UNIT_PLAN.power = 100
        self.TEST_UNIT_PLAN.max_health = 100
        self.TEST_UNIT_PLAN.total_stamina = 3
        self.TEST_UNIT_PLAN_2.power = 100
        self.TEST_UNIT_PLAN_2.max_health = 100
        self.TEST_UNIT_PLAN_2.total_stamina = 3

    def test_gen_players(self):
        """
        Ensure that players are generated for a game according to the supplied game configuration.
        """
        self.game_state.players = []
        self.game_state.gen_players(self.TEST_CONFIG)

        non_ai_players: typing.List[Player] = \
            list(filter(lambda player: player.name == "The Chosen One", self.game_state.players))
        self.assertEqual(1, len(non_ai_players))
        self.assertEqual(self.TEST_CONFIG.player_faction, non_ai_players[0].faction)
        self.assertEqual(self.TEST_CONFIG.player_count, len(self.game_state.players))

    def test_check_for_warnings_no_issues(self):
        """
        Ensure that no warning is generated when all of a player's settlements are busy, the player is undergoing a
        blessing, and they have wealth.
        """
        self.TEST_SETTLEMENT.current_work = Construction(IMPROVEMENTS[0])
        # For coverage purposes, let's say this settlement is in an economic boom.
        self.TEST_SETTLEMENT.economic_status = EconomicStatus.BOOM
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT]
        self.game_state.players[0].ongoing_blessing = OngoingBlessing(BLESSINGS["beg_spl"])
        self.game_state.players[0].wealth = 1000
        # Again for coverage purposes, let's say the player is of the Godless faction.
        self.game_state.players[0].faction = Faction.GODLESS

        self.assertFalse(self.game_state.check_for_warnings())

    def test_check_for_warnings_no_construction(self):
        """
        Ensure that when at least one of the player's settlements is idle, a warning is generated.
        """
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT]
        # Make sure the player has an ongoing blessing and wealth, so that we know it is the construction that is
        # causing the warning.
        self.game_state.players[0].ongoing_blessing = OngoingBlessing(BLESSINGS["beg_spl"])
        self.game_state.players[0].wealth = 1000

        self.assertIsNone(self.TEST_SETTLEMENT.current_work)
        self.assertTrue(self.game_state.check_for_warnings())

    def test_check_for_warnings_no_blessing(self):
        """
        Ensure that when the player is not undergoing a blessing, a warning is generated.
        """
        # Make sure the player has only busy settlements and wealth, so we know it is the blessing that is causing the
        # warning.
        self.TEST_SETTLEMENT.current_work = Construction(IMPROVEMENTS[0])
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT]
        self.game_state.players[0].wealth = 1000

        self.assertIsNone(self.game_state.players[0].ongoing_blessing)
        self.assertTrue(self.game_state.check_for_warnings())

    def test_check_for_warnings_negative_wealth(self):
        """
        Ensure that when the player will go into negative wealth next turn, a warning is generated.
        """
        # Make sure the player has only busy settlements and an ongoing blessing, so we know it is the wealth that is
        # causing the warning.
        self.TEST_SETTLEMENT.current_work = Construction(IMPROVEMENTS[0])
        # For coverage purposes, let's say this settlement is in a recession.
        self.TEST_SETTLEMENT.economic_status = EconomicStatus.RECESSION
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT]
        self.game_state.players[0].ongoing_blessing = OngoingBlessing(BLESSINGS["beg_spl"])
        # Again for coverage purposes, let's say the player is of the Orthodox faction.
        self.game_state.players[0].faction = Faction.ORTHODOX

        self.assertFalse(self.game_state.players[0].wealth)
        self.assertTrue(self.game_state.check_for_warnings())

    """
    Process player cases to test
    
    5 settlements - each of one category of satisfaction
    4 settlements - one besieged, one previously besieged, one recovering, one killed all besiegers
    Garrison units and deployed units reset
    Satisfaction adjusted by harvest - compare capitalists to others
    Current work is completed, overlay shown
    Harvest reserves added to and levelled up - compare ravenous to others, overlay shown
    Blessing is completed, overlay shown
    Player units auto-sold and accumulated wealth increased
    """

    def test_process_climatic_effects_daytime_continue(self):
        """
        Ensure that when a turn is ended and daytime is to continue, the nighttime tracking variables are updated
        correctly.
        """
        self.game_state.nighttime_left = 0
        original_turns_left = 5
        self.game_state.until_night = original_turns_left

        self.game_state.process_climatic_effects()
        self.assertEqual(original_turns_left - 1, self.game_state.until_night)

    def test_process_climatic_effects_night_begins(self):
        """
        Ensure that when a turn is ended and nighttime is to begin, the nighttime tracking variables are updated
        correctly and heathen and Nocturne unit's power is increased.
        """
        self.game_state.nighttime_left = 0
        self.game_state.until_night = 1
        self.game_state.board.overlay.toggle_night = MagicMock()
        # We need to know the original powers for the heathen and the two units so that we can compare them later.
        original_heathen_power = self.TEST_HEATHEN.plan.power
        self.game_state.players[0].faction = Faction.NOCTURNE
        original_unit_power = self.TEST_UNIT.plan.power
        original_unit_2_power = self.TEST_SETTLEMENT.garrison[0].plan.power
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT]

        self.game_state.process_climatic_effects()

        self.game_state.board.overlay.toggle_night.assert_called_with(True)
        # The nighttime left variable should now be initialised to some number between 5 and 20.
        self.assertTrue(self.game_state.nighttime_left)
        # Each unit should now have their power doubled.
        self.assertEqual(2 * original_heathen_power, self.TEST_HEATHEN.plan.power)
        self.assertEqual(2 * original_unit_power, self.TEST_UNIT.plan.power)
        self.assertEqual(2 * original_unit_2_power, self.TEST_SETTLEMENT.garrison[0].plan.power)

    def test_process_climatic_effects_night_continues(self):
        """
        Ensure that when a turn is ended and nighttime is to continue, the nighttime tracking variables are updated
        correctly.
        """
        original_turns_left = 5
        self.game_state.nighttime_left = original_turns_left
        self.game_state.until_night = 0

        self.game_state.process_climatic_effects()
        self.assertEqual(original_turns_left - 1, self.game_state.nighttime_left)

    def test_process_climatic_effects_daytime_begins(self):
        """
        Ensure that when a turn is ended and daytime is to begin, the nighttime tracking variables are updated
        correctly and heathen and Nocturne unit's power, health, and stamina is decreased.
        """
        self.game_state.nighttime_left = 1
        self.game_state.until_night = 0
        self.game_state.board.overlay.toggle_night = MagicMock()
        self.game_state.players[0].faction = Faction.NOCTURNE
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT]

        # Keep track of the heathen's power, and the units' power, health and maximum health, and total stamina for
        # later comparison.
        original_heathen_power = self.TEST_HEATHEN.plan.power
        original_unit_power = self.TEST_UNIT.plan.power
        original_unit_health = self.TEST_UNIT.health
        original_unit_max_health = self.TEST_UNIT.plan.max_health
        original_unit_total_stamina = self.TEST_UNIT.plan.total_stamina
        original_unit_2_power = self.TEST_SETTLEMENT.garrison[0].plan.power
        original_unit_2_health = self.TEST_UNIT_2.health
        original_unit_2_max_health = self.TEST_UNIT_2.plan.max_health
        original_unit_2_total_stamina = self.TEST_UNIT_2.plan.total_stamina

        self.game_state.process_climatic_effects()
        # The until night variable should now be initialised to some number between 10 and 20.
        self.assertTrue(self.game_state.until_night)
        self.game_state.board.overlay.toggle_night.assert_called_with(False)
        # Each unit should now have their power reduced. Heathens are brought back to their standard level, whereas
        # Nocturne units should have their power (and health, maximum health, and total stamina) reduced to half of the
        # usual nighttime level.
        self.assertEqual(round(original_heathen_power / 2), self.TEST_HEATHEN.plan.power)
        self.assertEqual(round(original_unit_power / 4), self.TEST_UNIT.plan.power)
        self.assertEqual(round(original_unit_health / 2), self.TEST_UNIT.health)
        self.assertEqual(round(original_unit_max_health / 2), self.TEST_UNIT.plan.max_health)
        self.assertEqual(round(original_unit_total_stamina / 2), self.TEST_UNIT.plan.total_stamina)
        self.assertEqual(round(original_unit_2_power / 4), self.TEST_SETTLEMENT.garrison[0].plan.power)
        self.assertEqual(round(original_unit_2_health / 2), self.TEST_UNIT_2.health)
        self.assertEqual(round(original_unit_2_max_health / 2), self.TEST_UNIT_2.plan.max_health)
        self.assertEqual(round(original_unit_2_total_stamina / 2), self.TEST_UNIT_2.plan.total_stamina)

    def test_check_for_victory_close(self):
        """
        Ensure that when a player is close to achieving a victory, their state is updated and the correct overlay is
        displayed. For our purposes, the player will be close to every victory.
        """
        # To aid the Jubilation, Gluttony, and Vigour victories, the test settlement will become a sort of super
        # settlement, with high satisfaction and level, and a current construction of the Holy Sanctum.
        self.TEST_SETTLEMENT.satisfaction = 100
        self.TEST_SETTLEMENT.level = 10
        self.TEST_SETTLEMENT.current_work = Construction(IMPROVEMENTS[-1])
        # We give the player eight copies of the settlement to get close to the ten required for a Gluttony victory.
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT] * 8
        # We have to make sure the main player isn't the only one with a settlement, which would trigger an Elimination
        # victory. Conveniently, as there is only one other settlement in the game, the main player is also considered
        # to be close to an Elimination victory.
        self.game_state.players[1].settlements = [self.TEST_SETTLEMENT_2]
        # 75000 is close to the 100000 required for an Affluence victory.
        self.game_state.players[0].accumulated_wealth = 75000
        # We give the player two of the three required pieces of ardour for a Serendipity victory.
        self.game_state.players[0].blessings = [BLESSINGS["ard_one"], BLESSINGS["ard_two"]]
        self.game_state.board.overlay.toggle_close_to_vic = MagicMock()

        # No actual victory should have been detected.
        self.assertIsNone(self.game_state.check_for_victory())

        # We expect the overlay to have been called six times, for each victory type.
        self.game_state.board.overlay.toggle_close_to_vic.assert_called()
        close_to_vics = self.game_state.board.overlay.toggle_close_to_vic.call_args[0][0]
        self.assertEqual(6, len(close_to_vics))

        # Ensure each type is represented in the mock calls.
        self.assertEqual(Victory(self.game_state.players[0], VictoryType.ELIMINATION), close_to_vics[0])
        self.assertEqual(Victory(self.game_state.players[0], VictoryType.VIGOUR), close_to_vics[1])
        self.assertEqual(Victory(self.game_state.players[0], VictoryType.JUBILATION), close_to_vics[2])
        self.assertEqual(Victory(self.game_state.players[0], VictoryType.GLUTTONY), close_to_vics[3])
        self.assertEqual(Victory(self.game_state.players[0], VictoryType.AFFLUENCE), close_to_vics[4])
        self.assertEqual(Victory(self.game_state.players[0], VictoryType.SERENDIPITY), close_to_vics[5])

        # Also make sure the player's state is updated.
        self.assertIn(VictoryType.ELIMINATION, self.game_state.players[0].imminent_victories)
        self.assertIn(VictoryType.VIGOUR, self.game_state.players[0].imminent_victories)
        self.assertIn(VictoryType.JUBILATION, self.game_state.players[0].imminent_victories)
        self.assertIn(VictoryType.GLUTTONY, self.game_state.players[0].imminent_victories)
        self.assertIn(VictoryType.AFFLUENCE, self.game_state.players[0].imminent_victories)
        self.assertIn(VictoryType.SERENDIPITY, self.game_state.players[0].imminent_victories)

    def test_check_for_victory_jubilation(self):
        """
        Ensure that when the conditions are met for a Jubilation victory, it is detected.
        """
        # Five duplicate settlements at 100 satisfaction are required for this victory.
        self.TEST_SETTLEMENT.satisfaction = 100
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT] * 5
        # We have to make sure the main player isn't the only one with a settlement, which would trigger an Elimination
        # victory.
        self.game_state.players[1].settlements = [self.TEST_SETTLEMENT_2]
        # The required number of turns in a row with five settlements at 100 satisfaction is 25. As such, we set it as
        # 24 to let it be incremented by the method, and then validated.
        self.game_state.players[0].jubilation_ctr = 24

        self.assertEqual(Victory(self.game_state.players[0], VictoryType.JUBILATION),
                         self.game_state.check_for_victory())

    def test_check_for_victory_gluttony(self):
        """
        Ensure that when the conditions are met for a Gluttony victory, it is detected.
        """
        # Ten settlements at level 10 are required for this victory.
        self.TEST_SETTLEMENT.level = 10
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT] * 10
        # We have to make sure the main player isn't the only one with a settlement, which would trigger an Elimination
        # victory.
        self.game_state.players[1].settlements = [self.TEST_SETTLEMENT_2]

        self.assertEqual(Victory(self.game_state.players[0], VictoryType.GLUTTONY), self.game_state.check_for_victory())

    def test_check_for_victory_vigour(self):
        """
        Ensure that when the conditions are met for a Vigour victory, it is detected.
        """
        # The Holy Sanctum having been constructed is required for this victory.
        self.TEST_SETTLEMENT.improvements = [IMPROVEMENTS[-1]]
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT]
        # We have to make sure the main player isn't the only one with a settlement, which would trigger an Elimination
        # victory.
        self.game_state.players[1].settlements = [self.TEST_SETTLEMENT_2]

        self.assertEqual(Victory(self.game_state.players[0], VictoryType.VIGOUR), self.game_state.check_for_victory())

    def test_check_for_victory_affluence(self):
        """
        Ensure that when the conditions are met for an Affluence victory, it is detected.
        """
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT]
        # We have to make sure the main player isn't the only one with a settlement, which would trigger an Elimination
        # victory.
        self.game_state.players[1].settlements = [self.TEST_SETTLEMENT_2]
        # Over the course of the game, an accumulation of 100000 wealth is required for this victory.
        self.game_state.players[0].accumulated_wealth = 100000

        self.assertEqual(Victory(self.game_state.players[0], VictoryType.AFFLUENCE),
                         self.game_state.check_for_victory())

    def test_check_for_victory_serendipity(self):
        """
        Ensure that when the conditions are met for a Serendipity victory, it is detected.
        """
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT]
        # We have to make sure the main player isn't the only one with a settlement, which would trigger an Elimination
        # victory.
        self.game_state.players[1].settlements = [self.TEST_SETTLEMENT_2]
        # The undergoing of the three pieces of ardour as blessings is required for this victory.
        self.game_state.players[0].blessings = [BLESSINGS["ard_one"], BLESSINGS["ard_two"], BLESSINGS["ard_three"]]

        self.assertEqual(Victory(self.game_state.players[0], VictoryType.SERENDIPITY),
                         self.game_state.check_for_victory())

    def test_check_for_victory_elimination(self):
        """
        Ensure that when the conditions are met for an Elimination victory, it is detected.
        """
        # Let us imagine that the first player has just taken the second settlement from the second player. Now, there
        # is only one player with one or more settlements, which is the requirement for this victory.
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2]
        self.game_state.board.overlay.toggle_elimination = MagicMock()

        # The other players should not be eliminated before the check.
        self.assertFalse(self.game_state.players[1].eliminated)
        self.assertFalse(self.game_state.players[2].eliminated)
        self.assertFalse(self.game_state.players[3].eliminated)
        self.assertEqual(Victory(self.game_state.players[0], VictoryType.ELIMINATION),
                         self.game_state.check_for_victory())
        # The other players should now each be eliminated, and the elimination overlay should have been called for each
        # of them.
        self.assertTrue(self.game_state.players[1].eliminated)
        self.assertTrue(self.game_state.players[2].eliminated)
        self.assertTrue(self.game_state.players[3].eliminated)
        self.assertEqual(3, self.game_state.board.overlay.toggle_elimination.call_count)

    def test_check_for_victory_reset_jubilation_counter(self):
        """
        Ensure that when a player is on the brink of achieving a Jubilation victory, but the satisfaction of one or more
        of their settlements drops, their cumulative turn counter resets to 0.
        """
        # 99 is not enough for a Jubilation victory - it must be 100.
        self.TEST_SETTLEMENT.satisfaction = 99
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT] * 5
        # We have to make sure the main player isn't the only one with a settlement, which would trigger an Elimination
        # victory.
        self.game_state.players[1].settlements = [self.TEST_SETTLEMENT_2]
        # If the settlement's satisfaction was at 100, this 24 would be incremented to 25 and the victory triggered.
        self.game_state.players[0].jubilation_ctr = 24

        # As such, no victory should have been achieved, and the counter should have been reset for the relevant player.
        self.assertIsNone(self.game_state.check_for_victory())
        self.assertFalse(self.game_state.players[0].jubilation_ctr)

    def test_check_for_victory_settler_preventing_elimination(self):
        """
        Ensure that when the human player has a settler unit remaining despite losing all of their settlements, they are
        protected from being eliminated. Because of this, the only AI player with one or more settlements should also
        not be granted victory.
        """
        # Let us imagine that the AI player has just taken the second settlement from the human player. Now, there
        # is only one player with one or more settlements, which is the requirement for this victory.
        self.game_state.players[1].settlements = [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2]
        # However! The human player has a settler unit leftover, protecting them from elimination.
        self.game_state.players[0].units = [Unit(0, 0, (0, 0), False, next(up for up in UNIT_PLANS if up.can_settle))]
        self.game_state.board.overlay.toggle_elimination = MagicMock()

        # To begin with, the other players should not be eliminated.
        self.assertFalse(self.game_state.players[0].eliminated)
        self.assertFalse(self.game_state.players[2].eliminated)
        self.assertFalse(self.game_state.players[3].eliminated)
        # Due to the human player's protection, no victory should have been achieved.
        self.assertIsNone(self.game_state.check_for_victory())
        # Despite the human player not being eliminated, the other two players should still have been eliminated, and
        # the elimination overlay displayed for them.
        self.assertFalse(self.game_state.players[0].eliminated)
        self.assertTrue(self.game_state.players[2].eliminated)
        self.assertTrue(self.game_state.players[3].eliminated)
        self.assertEqual(2, self.game_state.board.overlay.toggle_elimination.call_count)

    def test_process_heathens_infidel(self):
        """
        Ensure that units owned by players of the Infidels faction are not attacked by heathens.
        """
        self.game_state.board.overlay.toggle_attack = MagicMock()

        self.assertFalse(self.game_state.players[0].quads_seen)
        self.game_state.process_heathens()

        # We make sure that an attack does not occur using the toggle_attack mock. This would normally be called because
        # the player being attacked is the first player, i.e. the human player, meaning an overlay is displayed to alert
        # them to the attack.
        self.game_state.board.overlay.toggle_attack.assert_not_called()
        self.assertFalse(self.TEST_HEATHEN.remaining_stamina)
        # We also check here that the Infidels player has their vision updated by the heathen's movement.
        self.assertTrue(self.game_state.players[0].quads_seen)

    def test_process_heathens_not_within_range(self):
        """
        Ensure that heathens move randomly when there are no units in range to attack.
        """
        # Move the test unit away from the heathen, and make the player a non-protected faction.
        self.TEST_UNIT.location = 50, 50
        self.game_state.players[0].faction = Faction.AGRICULTURISTS
        self.game_state.board.overlay.toggle_attack = MagicMock()

        self.game_state.process_heathens()

        # We make sure that an attack does not occur using the toggle_attack mock. This would normally be called because
        # the player being attacked is the first player, i.e. the human player, meaning an overlay is displayed to alert
        # them to the attack.
        self.game_state.board.overlay.toggle_attack.assert_not_called()
        self.assertFalse(self.TEST_HEATHEN.remaining_stamina)

    def test_process_heathens_too_much_health(self):
        """
        Ensure that heathens do not attack units that have too much more health than them.
        """
        # Increase the test unit's health, and make the player a non-protected faction.
        self.TEST_UNIT.health = 100
        self.game_state.players[0].faction = Faction.AGRICULTURISTS
        self.game_state.board.overlay.toggle_attack = MagicMock()

        self.game_state.process_heathens()

        # We make sure that an attack does not occur using the toggle_attack mock. This would normally be called because
        # the player being attacked is the first player, i.e. the human player, meaning an overlay is displayed to alert
        # them to the attack.
        self.game_state.board.overlay.toggle_attack.assert_not_called()
        self.assertFalse(self.TEST_HEATHEN.remaining_stamina)

    def test_process_heathens_attack_left_unit_killed(self):
        """
        Ensure that the correct state and overlay changes occur when a heathen attacks and kills a unit.
        """
        # Make the player a non-protected faction.
        self.game_state.players[0].faction = Faction.AGRICULTURISTS
        self.game_state.board.overlay.toggle_attack = MagicMock()
        self.game_state.board.selected_unit = self.game_state.players[0].units[0]
        self.game_state.board.overlay.toggle_unit = MagicMock()

        self.game_state.process_heathens()

        # Because the heathen was initially positioned below the unit, it should be moved to its left.
        self.assertTupleEqual((self.TEST_UNIT.location[0] - 1, self.TEST_UNIT.location[1]), self.TEST_HEATHEN.location)
        self.assertFalse(self.TEST_HEATHEN.remaining_stamina)
        self.game_state.board.overlay.toggle_attack.assert_called()
        # Because the unit was killed, the attacked player should no longer have any units.
        self.assertFalse(self.game_state.players[0].units)
        # Additionally, the unit overlay should be removed because the selected unit is no longer present.
        self.assertIsNone(self.game_state.board.selected_unit)
        self.game_state.board.overlay.toggle_unit.assert_called_with(None)
        # Make sure the heathen was not killed.
        self.assertTrue(self.game_state.heathens)

    def test_process_heathens_attack_right_heathen_killed(self):
        """
        Ensure that the correct state and overlay changes occur when a heathen attacks a unit, but is killed itself.
        """
        # Make the player a non-protected faction.
        self.game_state.players[0].faction = Faction.AGRICULTURISTS
        self.game_state.board.overlay.toggle_attack = MagicMock()
        # Move the heathen to the units right, and set up the healths so that the heathen will attack the unit, but die
        # nevertheless.
        self.TEST_HEATHEN.location = 5, 3
        self.TEST_UNIT.health = 50
        self.TEST_HEATHEN.health = 25

        self.game_state.process_heathens()

        # The heathen should have moved next to the unit, on the right.
        self.assertTupleEqual((self.TEST_UNIT.location[0] + 1, self.TEST_UNIT.location[1]), self.TEST_HEATHEN.location)
        self.assertFalse(self.TEST_HEATHEN.remaining_stamina)
        self.game_state.board.overlay.toggle_attack.assert_called()
        # Make sure the unit was not killed.
        self.assertTrue(self.game_state.players[0].units)
        # Because the heathen was killed, the game state should no longer have any heathens.
        self.assertFalse(self.game_state.heathens)

    def test_initialise_ais(self):
        """
        Ensure that AI players have their settlements correctly initialised.
        """
        # To begin with, make sure that the settlements are created at all.
        self.assertFalse(any(player.settlements for player in self.game_state.players))
        self.game_state.initialise_ais(self.TEST_NAMER)
        self.assertTrue(all(player.settlements for player in self.game_state.players))

        # The first player is of the Infidels faction, so their settlement should have no modifiers applied.
        self.assertEqual(100, self.game_state.players[0].settlements[0].strength)
        self.assertEqual(100, self.game_state.players[0].settlements[0].max_strength)
        self.assertEqual(50, self.game_state.players[0].settlements[0].satisfaction)

        # The second player is of the Concentrated faction, so their settlement should have double the strength.
        self.assertEqual(200, self.game_state.players[1].settlements[0].strength)
        self.assertEqual(200, self.game_state.players[1].settlements[0].max_strength)
        self.assertEqual(50, self.game_state.players[0].settlements[0].satisfaction)

        # The third player is of the Frontiersmen faction, so their settlement should have increased satisfaction.
        self.assertEqual(100, self.game_state.players[2].settlements[0].strength)
        self.assertEqual(100, self.game_state.players[2].settlements[0].max_strength)
        self.assertEqual(75, self.game_state.players[2].settlements[0].satisfaction)

        # The final player is of the Imperials faction, so their settlement should have half the strength.
        self.assertEqual(50, self.game_state.players[3].settlements[0].strength)
        self.assertEqual(50, self.game_state.players[3].settlements[0].max_strength)
        self.assertEqual(50, self.game_state.players[0].settlements[0].satisfaction)

    def test_process_ais(self):
        """
        Ensure that when processing AI turns, a move is made for each player.
        """
        test_movemaker = MoveMaker(self.TEST_NAMER)
        test_movemaker.make_move = MagicMock()

        self.game_state.process_ais(test_movemaker)
        self.assertEqual(len(self.game_state.players), test_movemaker.make_move.call_count)


if __name__ == '__main__':
    unittest.main()
