import unittest
from unittest.mock import patch, MagicMock

from source.display.board import Board
from source.foundation.catalogue import Namer, UNIT_PLANS, BLESSINGS, get_unlockable_improvements, get_improvement, \
    get_available_improvements, get_unit_plan, IMPROVEMENTS
from source.foundation.models import GameConfig, Faction, Unit, Player, Settlement, AIPlaystyle, AttackPlaystyle, \
    ExpansionPlaystyle, Blessing, Quad, Biome, UnitPlan, SetlAttackData, Construction
from source.game_management.movemaker import search_for_relics_or_move, set_blessing, set_player_construction, \
    set_ai_construction, MoveMaker, move_healer_unit


class MovemakerTest(unittest.TestCase):
    """
    The test class for movemaker.py.
    """
    TEST_CONFIG = GameConfig(2, Faction.NOCTURNE, True, True, True)
    TEST_BOARD = Board(TEST_CONFIG, Namer())

    def setUp(self) -> None:
        """
        Generate the quads to use, locate a relic, and initialise the test models.
        """
        self.TEST_SETTLER_PLAN = UnitPlan(25, 25, 5, "Likes To Roam", None, 25, can_settle=True)
        self.TEST_HEALER_PLAN = UnitPlan(25, 50, 3, "More health please", None, 25, heals=True)
        self.TEST_UNIT_PLAN = UnitPlan(100, 100, 3, "Fighting Man", None, 25)
        self.TEST_UNIT = Unit(1, self.TEST_UNIT_PLAN.total_stamina, (3, 4), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_2 = Unit(5, 6, (7, 8), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_3 = Unit(9, 10, (11, 12), False, self.TEST_UNIT_PLAN)
        self.TEST_SETTLER_UNIT = Unit(13, 5, (14, 15), False, self.TEST_SETTLER_PLAN)
        self.TEST_HEALER_UNIT = Unit(16, 3, (17, 18), False, self.TEST_HEALER_PLAN)
        self.TEST_SETTLEMENT = Settlement("Obstructionville", (0, 0), [], [], [])
        self.TEST_SETTLEMENT_2 = Settlement("EnemyTown", (40, 40), [], [], [])
        self.TEST_PLAYER = Player("TesterMan", Faction.NOCTURNE, 0, 0, [self.TEST_SETTLEMENT], [self.TEST_UNIT], [],
                                  set(), set(),
                                  ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))
        self.TEST_PLAYER_2 = Player("TesterMan2", Faction.AGRICULTURISTS, 0, 0, [self.TEST_SETTLEMENT_2], [], [],
                                    set(), set(),
                                    ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))

        self.movemaker = MoveMaker(Namer())
        self.movemaker.board_ref = self.TEST_BOARD
        self.TEST_BOARD.generate_quads(self.TEST_CONFIG.biome_clustering)
        self.QUADS = self.TEST_BOARD.quads
        # We need to find a relic quad before each test, because the quads are re-generated each time.
        self.relic_coords: (int, int) = -1, -1
        for i in range(2, 90):
            for j in range(2, 80):
                if self.QUADS[i][j].is_relic:
                    self.relic_coords = i, j
                    break
            if self.relic_coords[0] != -1:
                break
        # More than one relic can make the tests unreliable, so remove all others.
        for i in range(90):
            for j in range(80):
                if self.QUADS[i][j].is_relic and self.relic_coords != (i, j):
                    self.QUADS[i][j].is_relic = False
        # Position the other two units and settlement to be surrounding the relic, obstructing its access.
        self.TEST_UNIT_2.location = self.relic_coords[0] - 1, self.relic_coords[1]
        self.TEST_UNIT_3.location = self.relic_coords[0], self.relic_coords[1] + 1
        self.TEST_SETTLEMENT.location = self.relic_coords[0], self.relic_coords[1] - 1

    def test_set_blessing_none_available(self):
        """
        Ensure that an AI player's blessing is not set if there are none available, i.e. they have undergone all of
        them.
        """
        # Give the player every blessing.
        self.TEST_PLAYER.blessings = BLESSINGS.values()

        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        set_blessing(self.TEST_PLAYER, (0, 0, 0, 0))
        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)

    def test_set_blessing_wealth(self):
        """
        Ensure that an AI player's blessing is set to the best possible one for wealth if that is what they are lacking.
        """
        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        set_blessing(self.TEST_PLAYER, (0, 1, 1, 1))
        # The blessing that yields the most wealth is Self-Locking Vaults, with 29.
        new_blessing: Blessing = self.TEST_PLAYER.ongoing_blessing.blessing
        self.assertEqual(BLESSINGS["sl_vau"], new_blessing)

    def test_set_blessing_harvest(self):
        """
        Ensure that an AI player's blessing is set to the best possible one for harvest if that is what they are
        lacking.
        """
        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        set_blessing(self.TEST_PLAYER, (1, 0, 1, 1))
        # The blessing that yields the most harvest is Self-Locking Vaults, with 25.
        new_blessing: Blessing = self.TEST_PLAYER.ongoing_blessing.blessing
        self.assertEqual(BLESSINGS["sl_vau"], new_blessing)

    def test_set_blessing_zeal(self):
        """
        Ensure that an AI player's blessing is set to the best possible one for zeal if that is what they are lacking.
        """
        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        set_blessing(self.TEST_PLAYER, (1, 1, 0, 1))
        # The blessing that yields the most zeal is Robotic Experiments, with 32.
        new_blessing: Blessing = self.TEST_PLAYER.ongoing_blessing.blessing
        self.assertEqual(BLESSINGS["rob_exp"], new_blessing)

    def test_set_blessing_fortune(self):
        """
        Ensure that an AI player's blessing is set to the best possible one for fortune if that is what they are
        lacking.
        """
        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        set_blessing(self.TEST_PLAYER, (1, 1, 1, 0))
        # The blessing that yields the most fortune is Divine Architecture, with 30.
        new_blessing: Blessing = self.TEST_PLAYER.ongoing_blessing.blessing
        self.assertEqual(BLESSINGS["div_arc"], new_blessing)

    def test_set_blessing_aggressive_unit(self):
        """
        Ensure than an aggressive AI player's blessing is set to the first one that unlocks a unit.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE

        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        set_blessing(self.TEST_PLAYER, (0, 0, 0, 0))
        # The first blessing that yields a unit is Beginner Spells.
        new_blessing: Blessing = self.TEST_PLAYER.ongoing_blessing.blessing
        self.assertEqual(BLESSINGS["beg_spl"], new_blessing)

    def test_set_blessing_aggressive_no_units(self):
        """
        Ensure than an aggressive AI player's blessing is set to the best possible one for wealth if that is what they
        are lacking and there are no remaining blessings that unlock units.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        # Technically this will result in duplicates in the list, but that doesn't matter for our purposes.
        self.TEST_PLAYER.blessings = [up.prereq for up in UNIT_PLANS if up.prereq is not None]

        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        set_blessing(self.TEST_PLAYER, (0, 1, 1, 1))
        # The blessing that yields the most wealth excluding those that yield units is Economic Movements, with 20.
        new_blessing: Blessing = self.TEST_PLAYER.ongoing_blessing.blessing
        self.assertEqual(BLESSINGS["eco_mov"], new_blessing)

    def test_set_blessing_defensive_strength(self):
        """
        Ensure than an defensive AI player's blessing is set to the first one that unlocks an improvement that yields
        strength.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE

        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        set_blessing(self.TEST_PLAYER, (0, 0, 0, 0))
        # The first blessing that yields an improvement with strength is Rudimentary Explosives.
        new_blessing: Blessing = self.TEST_PLAYER.ongoing_blessing.blessing
        self.assertEqual(BLESSINGS["rud_exp"], new_blessing)

    def test_set_blessing_defensive_no_strength(self):
        """
        Ensure than a defensive AI player's blessing is set to the best possible one for harvest if that is what they
        are lacking and there are no remaining blessings that unlock improvements with strength.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        # Give the player all the blessings that unlock improvements with strength.
        self.TEST_PLAYER.blessings = [bls for bls in BLESSINGS.values()
                                      if [imp for imp in get_unlockable_improvements(bls) if imp.effect.strength > 0]]

        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        set_blessing(self.TEST_PLAYER, (1, 0, 1, 1))
        # The blessing that yields the most harvest excluding those that yield strength is Metabolic Alterations, with
        # 15.
        new_blessing: Blessing = self.TEST_PLAYER.ongoing_blessing.blessing
        self.assertEqual(BLESSINGS["met_alt"], new_blessing)

    def test_set_player_construction_no_units(self):
        """
        Ensure that when a player has no deployed units nor any in the settlement's garrison, the first available unit
        is selected for construction.
        """
        self.TEST_PLAYER.units = []

        set_player_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        self.assertEqual(UNIT_PLANS[0], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_player_construction_wealth(self):
        """
        Ensure that when a player's settlement is lacking wealth, the correct improvement is selected for construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 0, 100, 1, 1)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())
        # Remove a blessing to create a suitable test environment.
        self.TEST_PLAYER.blessings.remove(BLESSINGS["sl_vau"])

        set_player_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Technically, Planned Economy, which grants 20 wealth is the ideal improvement for this situation. However,
        # that improvement also decreases satisfaction by 2, meaning that the settlement's satisfaction would be lowered
        # to 48, which is not ideal. As such, Federal Museum is selected instead, as it has the next most wealth and
        # does not negatively impact satisfaction.
        self.assertEqual(get_improvement("Federal Museum"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_player_construction_harvest(self):
        """
        Ensure that when a player's settlement is lacking harvest, the correct improvement is selected for construction.
        """
        self.TEST_SETTLEMENT.quads = [Quad(Biome.DESERT, 100, 99, 100, 100)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())
        # Remove a blessing to create a suitable test environment.
        self.TEST_PLAYER.blessings.remove(BLESSINGS["art_pht"])

        set_player_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Technically, Impenetrable Stores, which grants 25 harvest is the ideal improvement for this situation.
        # However, that improvement also decreases satisfaction by 5, meaning that the settlement's satisfaction would
        # be lowered to 45, which is not ideal. As such, Genetic Clinics is selected instead, as it has the next most
        # harvest and does not negatively impact satisfaction.
        self.assertEqual(get_improvement("Genetic Clinics"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_player_construction_zeal(self):
        """
        Ensure that when a player's settlement is lacking zeal, the correct improvement is selected for construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_player_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Technically, Automated Production, which grants 30 zeal is the ideal improvement for this situation.
        # However, that improvement also decreases satisfaction by 10, meaning that the settlement's satisfaction would
        # be lowered to 40, which is not ideal. As such, Endless Mine is selected instead, as it has the next most
        # zeal and does not negatively impact satisfaction.
        self.assertEqual(get_improvement("Endless Mine"), self.TEST_SETTLEMENT.current_work.construction)

    @patch("source.game_management.movemaker.get_available_improvements")
    def test_set_player_construction_fortune(self, imps_mock: MagicMock):
        """
        Ensure that when a player's settlement is lacking fortune, the correct improvement is selected for construction.
        :param imps_mock: The mock implementation of the get_available_improvements() function.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 1, 0)]
        self.TEST_PLAYER.blessings = [BLESSINGS["beg_spl"]]
        # We need to mock out the available improvements so as to achieve full coverage, reaching a block where the
        # improvement with the most fortune is updated. We do this by simply switching the first two improvements in the
        # list, as the eventual selection is normally the first in the list.
        test_imps = get_available_improvements(self.TEST_PLAYER, self.TEST_SETTLEMENT)
        test_imps[0], test_imps[1] = test_imps[1], test_imps[0]
        imps_mock.return_value = test_imps

        set_player_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Technically, Haunted Forest, which grants 8 fortune is the ideal improvement for this situation.
        # However, that improvement also decreases satisfaction by 5, meaning that the settlement's satisfaction would
        # be lowered to 45, which is not ideal. As such, Melting Pot is selected instead, as it has the next most
        # fortune and does not negatively impact satisfaction.
        self.assertEqual(get_improvement("Melting Pot"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_player_construction_unsatisfied_too_expensive(self):
        """
        Ensure that when a player's settlement is below 50 satisfaction, but there are no improvements that would
        increase it without taking too many turns, the ideal improvement is selected for construction instead.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]
        self.TEST_SETTLEMENT.satisfaction = 49
        # Give the settlement all the improvements in the first 'tier' that grant satisfaction.
        self.TEST_SETTLEMENT.improvements = [
            get_improvement("Aqueduct"),
            get_improvement("Collectivised Farms"),
            get_improvement("City Market"),
            get_improvement("Melting Pot"),
            get_improvement("Insurmountable Walls")
        ]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_player_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Since any of the improvements in the second 'tier' take too many turns, we expect the ideal improvement to be
        # selected instead. In this case, the ideal improvement is Local Forge, since zeal is the lowest of the four.
        self.assertEqual(get_improvement("Local Forge"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_player_construction_unsatisfied(self):
        """
        Ensure that when a player's settlement is below 50 satisfaction, the improvement that would grant the most
        combined satisfaction and harvest upon completion without taking too many turns is selected for construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]
        self.TEST_SETTLEMENT.satisfaction = 49
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_player_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the Aqueduct improvement to be selected, as it grants 2 harvest and 5 satisfaction, which is the
        # most combined in the first 'tier' of improvements.
        self.assertEqual(get_improvement("Aqueduct"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_player_construction_harvest_boundary(self):
        """
        Ensure that when a player's settlement is below the harvest boundary, the improvement that would grant the most
        harvest upon completion without taking too many turns is selected for construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 100, 0, 100, 100)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_player_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the Collectivised Farms improvement to be selected, as it grants 10 harvest, which is the most in
        # the first 'tier' of improvements.
        self.assertEqual(get_improvement("Collectivised Farms"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_no_units(self):
        """
        Ensure that when an AI player has no deployed units nor any in the settlement's garrison, the first available
        unit is selected for construction.
        """
        self.TEST_PLAYER.units = []

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        self.assertEqual(UNIT_PLANS[0], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_settler(self):
        """
        Ensure that AI players of different expansion playstyles produce settlers in their settlements at different
        levels.
        """
        # Expansionist AI players should produce a settler when their settlement reaches level 3.
        self.TEST_PLAYER.ai_playstyle.expansion = ExpansionPlaystyle.EXPANSIONIST
        self.TEST_SETTLEMENT.level = 2
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # So, at level 2, we expect the construction to not be the settler unit (UNIT_PLANS[3]).
        self.assertNotEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

        self.TEST_SETTLEMENT.level = 3
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Now at level 3, we expect a settler to be constructed.
        self.assertEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

        # Neutral AI players should produce a settler when their settlement reaches level 5.
        self.TEST_PLAYER.ai_playstyle.expansion = ExpansionPlaystyle.NEUTRAL
        self.TEST_SETTLEMENT.level = 4
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # At level 4, we expect the construction to not be the settler unit.
        self.assertNotEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

        self.TEST_SETTLEMENT.level = 5
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Now at level 5, we expect a settler to be constructed.
        self.assertEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

        # Hermit AI players should only produce a settler once their settlement reaches the maximum level of 10.
        self.TEST_PLAYER.ai_playstyle.expansion = ExpansionPlaystyle.HERMIT
        self.TEST_SETTLEMENT.level = 9
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # At level 9, we expect the construction to not be the settler unit.
        self.assertNotEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

        self.TEST_SETTLEMENT.level = 10
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Now at level 10, we expect a settler to be constructed.
        self.assertEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_settler_concentrated(self):
        """
        Ensure that AI players of the Concentrated faction do not construct settlers at any level.
        """
        self.TEST_SETTLEMENT.level = 10
        self.TEST_PLAYER.faction = Faction.CONCENTRATED
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the construction to not be the settler unit (UNIT_PLANS[3]).
        self.assertNotEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_settler_already_produced(self):
        """
        Ensure that AI player settlements that have already produced a settler cannot produce another one.
        """
        self.TEST_SETTLEMENT.level = 10
        self.TEST_SETTLEMENT.produced_settler = True
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the construction to not be the settler unit (UNIT_PLANS[3]).
        self.assertNotEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_settler_dissatisfied(self):
        """
        Ensure that AI players with only dissatisfied settlements produce settlers as soon as their level increases.
        """
        self.TEST_SETTLEMENT.level = 2
        self.TEST_SETTLEMENT.satisfaction = 0
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the construction to not be the settler unit (UNIT_PLANS[3]).
        self.assertEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_wealth(self):
        """
        Ensure that when an AI player's settlement is lacking wealth, the correct improvement is selected for
        construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 0, 100, 1, 1)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())
        # Remove a blessing to create a suitable test environment.
        self.TEST_PLAYER.blessings.remove(BLESSINGS["sl_vau"])

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Technically, Planned Economy, which grants 20 wealth is the ideal improvement for this situation. However,
        # that improvement also decreases satisfaction by 2, meaning that the settlement's satisfaction would be lowered
        # to 48, which is not ideal. As such, Federal Museum is selected instead, as it has the next most wealth and
        # does not negatively impact satisfaction.
        self.assertEqual(get_improvement("Federal Museum"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_harvest(self):
        """
        Ensure that when an AI player's settlement is lacking harvest, the correct improvement is selected for
        construction.
        """
        self.TEST_SETTLEMENT.quads = [Quad(Biome.DESERT, 100, 99, 100, 100)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())
        # Remove a blessing to create a suitable test environment.
        self.TEST_PLAYER.blessings.remove(BLESSINGS["art_pht"])

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Technically, Impenetrable Stores, which grants 25 harvest is the ideal improvement for this situation.
        # However, that improvement also decreases satisfaction by 5, meaning that the settlement's satisfaction would
        # be lowered to 45, which is not ideal. As such, Genetic Clinics is selected instead, as it has the next most
        # harvest and does not negatively impact satisfaction.
        self.assertEqual(get_improvement("Genetic Clinics"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_zeal(self):
        """
        Ensure that when an AI player's settlement is lacking zeal, the correct improvement is selected for
        construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Technically, Automated Production, which grants 30 zeal is the ideal improvement for this situation.
        # However, that improvement also decreases satisfaction by 10, meaning that the settlement's satisfaction would
        # be lowered to 40, which is not ideal. As such, Endless Mine is selected instead, as it has the next most
        # zeal and does not negatively impact satisfaction.
        self.assertEqual(get_improvement("Endless Mine"), self.TEST_SETTLEMENT.current_work.construction)

    @patch("source.game_management.movemaker.get_available_improvements")
    def test_set_ai_construction_fortune(self, imps_mock: MagicMock):
        """
        Ensure that when an AI player's settlement is lacking fortune, the correct improvement is selected for
        construction.
        :param imps_mock: The mock implementation of the get_available_improvements() function.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 1, 0)]
        self.TEST_PLAYER.blessings = [BLESSINGS["beg_spl"]]
        # We need to mock out the available improvements so as to achieve full coverage, reaching a block where the
        # improvement with the most fortune is updated. We do this by simply switching the first two improvements in the
        # list, as the eventual selection is normally the first in the list.
        test_imps = get_available_improvements(self.TEST_PLAYER, self.TEST_SETTLEMENT)
        test_imps[0], test_imps[1] = test_imps[1], test_imps[0]
        imps_mock.return_value = test_imps

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Technically, Haunted Forest, which grants 8 fortune is the ideal improvement for this situation.
        # However, that improvement also decreases satisfaction by 5, meaning that the settlement's satisfaction would
        # be lowered to 45, which is not ideal. As such, Melting Pot is selected instead, as it has the next most
        # fortune and does not negatively impact satisfaction.
        self.assertEqual(get_improvement("Melting Pot"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_unsatisfied_too_expensive(self):
        """
        Ensure that when an AI player's settlement is below 50 satisfaction, but there are no improvements that would
        increase it without taking too many turns, the ideal improvement is selected for construction instead.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]
        self.TEST_SETTLEMENT.satisfaction = 49
        # Give the settlement all the improvements in the first 'tier' that grant satisfaction.
        self.TEST_SETTLEMENT.improvements = [
            get_improvement("Aqueduct"),
            get_improvement("Collectivised Farms"),
            get_improvement("City Market"),
            get_improvement("Melting Pot"),
            get_improvement("Insurmountable Walls")
        ]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Since any of the improvements in the second 'tier' take too many turns, we expect the ideal improvement to be
        # selected instead. In this case, the ideal improvement is Local Forge, since zeal is the lowest of the four.
        self.assertEqual(get_improvement("Local Forge"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_unsatisfied(self):
        """
        Ensure that when an AI player's settlement is below 50 satisfaction, the improvement that would grant the most
        combined satisfaction and harvest upon completion without taking too many turns is selected for construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]
        self.TEST_SETTLEMENT.satisfaction = 49
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the Aqueduct improvement to be selected, as it grants 2 harvest and 5 satisfaction, which is the
        # most combined in the first 'tier' of improvements.
        self.assertEqual(get_improvement("Aqueduct"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_harvest_boundary(self):
        """
        Ensure that when an AI player's settlement is below the harvest boundary, the improvement that would grant the
        most harvest upon completion without taking too many turns is selected for construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 100, 0, 100, 100)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the Collectivised Farms improvement to be selected, as it grants 10 harvest, which is the most in
        # the first 'tier' of improvements.
        self.assertEqual(get_improvement("Collectivised Farms"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_aggressive_healer(self):
        """
        Ensure that when an aggressive AI player settlement does not have enough healers, the most proficient one is
        selected for construction.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        self.TEST_PLAYER.blessings = BLESSINGS.values()
        # Increase the settlement level so that the player does not have enough units.
        self.TEST_SETTLEMENT.level = 2
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the Narcotician unit plan to be selected, as it has the greatest healing ability of all units.
        self.assertEqual(get_unit_plan("Narcotician"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_aggressive_unit(self):
        """
        Ensure that when an aggressive AI player settlement does not have enough units, the most powerful one is
        selected for construction.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        self.TEST_PLAYER.blessings = BLESSINGS.values()
        # Pretend that the player's unit is a healer so that an attacking unit will be selected instead.
        self.TEST_PLAYER.units[0].plan.heals = True
        # Increase the settlement level so that the player does not have enough units.
        self.TEST_SETTLEMENT.level = 2
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the Haruspex unit plan to be selected, as it has the greatest power of all units.
        self.assertEqual(get_unit_plan("Haruspex"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_aggressive_enough_units(self):
        """
        Ensure that when an aggressive AI player settlement already has enough units, the ideal construction is selected
        instead.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Normally, an aggressive AI would select a healer or a unit, but since they already have enough, their ideal
        # improvement is selected instead. In this case, it is Endless Mine.
        self.assertEqual(get_improvement("Endless Mine"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_defensive_healer(self):
        """
        Ensure that when a defensive AI player settlement does not have enough healers, the most proficient one is
        selected for construction.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.blessings = BLESSINGS.values()
        # Increase the settlement level so that the player does not have enough units.
        self.TEST_SETTLEMENT.level = 3
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the Narcotician unit plan to be selected, as it has the greatest healing ability of all units.
        self.assertEqual(get_unit_plan("Narcotician"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_defensive_unit(self):
        """
        Ensure that when a defensive AI player settlement does not have enough units, the one with the most health is
        selected for construction.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.blessings = BLESSINGS.values()
        # Pretend that the player's unit is a healer so that an attacking unit will be selected instead.
        self.TEST_PLAYER.units[0].plan.heals = True
        # Increase the settlement level so that the player does not have enough units.
        self.TEST_SETTLEMENT.level = 3
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # We expect the Fanatic unit plan to be selected, as it has the greatest health of all units.
        self.assertEqual(get_unit_plan("Fanatic"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_defensive_strength_improvement(self):
        """
        Ensure that when a defensive AI player settlement has enough units, but there are improvements available that
        increase settlement strength, said improvements are selected for construction.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.blessings = BLESSINGS.values()
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Since Insurmountable Walls is the first improvement that increases strength, we expect it to be chosen.
        self.assertEqual(get_improvement("Insurmountable Walls"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_defensive_enough_units_no_strength_improvements(self):
        """
        Ensure that when a defensive AI player settlement already has enough units and there are no improvements
        available that increase strength, the ideal construction is selected instead.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 100, 100, 0, 100)]
        # Give the settlement all the improvements that increase strength.
        self.TEST_SETTLEMENT.improvements = [imp for imp in IMPROVEMENTS if imp.effect.strength > 0]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Normally, a defensive AI would select a healer, a unit, or an improvement that yields strength, but since they
        # already have enough units and there aren't any improvements of that kind available, their ideal improvement is
        # selected instead. In this case, it is Endless Mine.
        self.assertEqual(get_improvement("Endless Mine"), self.TEST_SETTLEMENT.current_work.construction)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_success_left(self):
        """
        Ensure that when a relic is within range and to the left of a unit, the unit investigates and removes it.
        """
        self.TEST_UNIT.location = self.relic_coords[0] - 2, self.relic_coords[1]

        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)

        # The unit should have moved directly to the left of the relic, and the quad should no longer have a relic.
        self.assertTupleEqual((self.relic_coords[0] - 1, self.relic_coords[1]), self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertFalse(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_success_right(self):
        """
        Ensure that when a relic is within range and to the right of a unit, the unit investigates and removes it.
        """
        self.TEST_UNIT.location = self.relic_coords[0] + 2, self.relic_coords[1]

        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)

        # The unit should have moved directly to the right of the relic, and the quad should no longer have a relic.
        self.assertTupleEqual((self.relic_coords[0] + 1, self.relic_coords[1]), self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertFalse(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_obstructed(self):
        """
        Ensure that when the three options for movement for a unit to a relic within range are obstructed, the unit just
        moves randomly instead. The three things that can obstruct a relic are player units, AI units, and settlements.
        In this test, we surround the relic with one of each.
        """
        self.TEST_PLAYER.units.append(self.TEST_UNIT_2)
        self.TEST_UNIT.location = self.relic_coords[0] - 2, self.relic_coords[1]

        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [self.TEST_UNIT_3],
                                  [self.TEST_SETTLEMENT], self.TEST_CONFIG)

        # Normally, the unit would move directly to the left of the relic, but it can't move there, and as such, the
        # quad should still have a relic.
        self.assertNotEqual((self.relic_coords[0] - 1, self.relic_coords[1]), self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_none_found(self):
        """
        Ensure that when there are no available relics, the unit moves randomly.
        """
        # Remove the last relic from the board.
        self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic = False

        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)
        # Make sure the unit exhausted its stamina.
        self.assertFalse(self.TEST_UNIT.remaining_stamina)

    @patch("source.game_management.movemaker.heal")
    def test_move_healer_unit_nothing_within_range(self, heal_mock: MagicMock):
        """
        Ensure that healer units simply move randomly if there are no heal-able units within range.
        :param heal_mock: The mock implementation of heal().
        """
        self.TEST_PLAYER.units = [self.TEST_HEALER_UNIT]
        original_location = self.TEST_HEALER_UNIT.location

        move_healer_unit(self.TEST_PLAYER, self.TEST_HEALER_UNIT, [], [], self.QUADS, self.TEST_CONFIG)
        # We expect no heal to have occurred, but the unit should still have moved.
        heal_mock.assert_not_called()
        self.assertNotEqual(original_location, self.TEST_HEALER_UNIT.location)

    @patch("source.game_management.movemaker.heal")
    def test_move_healer_unit_heal_from_left(self, heal_mock: MagicMock):
        """
        Ensure that healer units to the left of a heal-able unit move next to said unit and heal it.
        :param heal_mock: The mock implementation of heal().
        """
        self.TEST_HEALER_UNIT.location = self.TEST_UNIT.location[0] - 2, self.TEST_UNIT.location[1]
        self.TEST_PLAYER.units.append(self.TEST_HEALER_UNIT)

        move_healer_unit(self.TEST_PLAYER, self.TEST_HEALER_UNIT, [], [], self.QUADS, self.TEST_CONFIG)
        # The healer should have moved directly to the left of the heal-able unit and healed it.
        self.assertTupleEqual((self.TEST_UNIT.location[0] - 1, self.TEST_UNIT.location[1]),
                              self.TEST_HEALER_UNIT.location)
        self.assertFalse(self.TEST_HEALER_UNIT.remaining_stamina)
        heal_mock.assert_called_with(self.TEST_HEALER_UNIT, self.TEST_UNIT)

    @patch("source.game_management.movemaker.heal")
    def test_move_healer_unit_heal_from_right(self, heal_mock: MagicMock):
        """
        Ensure that healer units to the right of a heal-able unit move next to said unit and heal it.
        :param heal_mock: The mock implementation of heal().
        """
        self.TEST_HEALER_UNIT.location = self.TEST_UNIT.location[0] + 2, self.TEST_UNIT.location[1]
        self.TEST_PLAYER.units.append(self.TEST_HEALER_UNIT)

        move_healer_unit(self.TEST_PLAYER, self.TEST_HEALER_UNIT, [], [], self.QUADS, self.TEST_CONFIG)
        # The healer should have moved directly to the right of the heal-able unit and healed it.
        self.assertTupleEqual((self.TEST_UNIT.location[0] + 1, self.TEST_UNIT.location[1]),
                              self.TEST_HEALER_UNIT.location)
        self.assertFalse(self.TEST_HEALER_UNIT.remaining_stamina)
        heal_mock.assert_called_with(self.TEST_HEALER_UNIT, self.TEST_UNIT)

    def test_make_move_blessing(self):
        """
        Ensure that when an AI player is making their move, if they have no ongoing blessing, one is set.
        """
        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False)
        self.assertIsNotNone(self.TEST_PLAYER.ongoing_blessing)

    def test_make_move_set_construction(self):
        """
        Ensure that when an AI player is making their move, if they have a settlement with no current work, a
        construction is set for that settlement.
        """
        self.assertIsNone(self.TEST_SETTLEMENT.current_work)
        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False)
        self.assertIsNotNone(self.TEST_SETTLEMENT.current_work)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_make_move_construction_buyout(self):
        """
        Ensure that when an AI player has more than 3x the required wealth to buyout a current construction, they do so.
        """
        self.TEST_SETTLEMENT.current_work = Construction(IMPROVEMENTS[-1])
        self.TEST_PLAYER.wealth = IMPROVEMENTS[-1].cost * 5

        self.assertFalse(self.TEST_SETTLEMENT.improvements)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False)

        # We expect the settlement to now have the improvement and the player's wealth to have been reduced
        # appropriately.
        self.assertIn(IMPROVEMENTS[-1], self.TEST_SETTLEMENT.improvements)
        self.assertEqual(IMPROVEMENTS[-1].cost * 4, self.TEST_PLAYER.wealth)

    def test_make_move_construction_buyout_satisfaction(self):
        """
        Ensure that when an AI player has a settlement with reduced satisfaction and the means to buyout its current
        construction that will grant satisfaction, they do so.
        """
        self.TEST_SETTLEMENT.satisfaction = 49
        # IMPROVEMENTS[0] is Melting Pot, which grants 2 satisfaction.
        self.TEST_SETTLEMENT.current_work = Construction(IMPROVEMENTS[0])
        self.TEST_PLAYER.wealth = IMPROVEMENTS[0].cost

        self.assertFalse(self.TEST_SETTLEMENT.improvements)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False)

        # We expect the settlement to now have the improvement.
        self.assertIn(IMPROVEMENTS[0], self.TEST_SETTLEMENT.improvements)

    def test_make_move_settler_deployed(self):
        """
        Ensure that when an AI player has a settler unit garrisoned, it is deployed.
        """
        self.TEST_SETTLER_UNIT.garrisoned = True
        self.TEST_SETTLEMENT.garrison = [self.TEST_SETTLER_UNIT]

        self.assertNotIn(self.TEST_SETTLER_UNIT, self.TEST_PLAYER.units)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False)

        self.assertFalse(self.TEST_SETTLER_UNIT.garrisoned)
        self.assertIn(self.TEST_SETTLER_UNIT, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)

    def test_make_move_aggressive_ai_deploy_unit(self):
        """
        Ensure that when an aggressive AI player has a unit garrisoned, it is deployed.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        self.TEST_UNIT_2.garrisoned = True
        self.TEST_SETTLEMENT.garrison = [self.TEST_UNIT_2]

        self.assertNotIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False)

        self.assertFalse(self.TEST_UNIT_2.garrisoned)
        self.assertIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)

    def test_make_move_neutral_ai_deploy_unit(self):
        """
        Ensure that when a neutral AI player has a unit garrisoned, it is deployed.
        """
        # The test player is neutral by default, but we set it here as well for clarity.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.NEUTRAL
        self.TEST_UNIT_2.garrisoned = True
        self.TEST_SETTLEMENT.garrison = [self.TEST_UNIT_2]

        self.assertNotIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False)

        self.assertFalse(self.TEST_UNIT_2.garrisoned)
        self.assertIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)

    def test_make_move_besieged_settlement_deploy_unit(self):
        """
        Ensure that when an AI player has a settlement under siege with a unit in its garrison, the unit is deployed.
        """
        # Set the attack playstyle to defensive, so we guarantee that it is the settlement's besieged nature that is
        # causing the deployment.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_UNIT_2.garrisoned = True
        self.TEST_SETTLEMENT.garrison = [self.TEST_UNIT_2]
        self.TEST_SETTLEMENT.besieged = True

        self.assertNotIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)

        self.movemaker.make_move(self.TEST_PLAYER, [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 self.QUADS, self.TEST_CONFIG, False)

        self.assertFalse(self.TEST_UNIT_2.garrisoned)
        self.assertIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)

    def test_make_move_weakened_settlement_deploy_unit(self):
        """
        Ensure that when an AI player has a weakened settlement with a unit in its garrison, the unit is deployed.
        """
        # Set the attack playstyle to defensive, so we guarantee that it is the settlement's weakened nature that is
        # causing the deployment.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_UNIT_2.garrisoned = True
        self.TEST_SETTLEMENT.garrison = [self.TEST_UNIT_2]
        self.TEST_SETTLEMENT.strength = 1

        self.assertNotIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False)

        self.assertFalse(self.TEST_UNIT_2.garrisoned)
        self.assertIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)

    def test_make_move_garrison_too_full_deploy_unit(self):
        """
        Ensure that when an AI player has more than three units in a settlement's garrison, one is deployed, no matter
        the circumstances.
        """
        extra_unit = Unit(90, 90, (9, 0), True, self.TEST_UNIT_PLAN)

        # Set the attack playstyle to defensive, so we guarantee that nothing else is causing the deployment.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.units = []
        # Give the player enough wealth so the deployed unit is not auto-sold.
        self.TEST_PLAYER.wealth = 999
        self.TEST_UNIT.garrisoned = True
        self.TEST_UNIT_2.garrisoned = True
        self.TEST_UNIT_3.garrisoned = True
        self.TEST_SETTLEMENT.garrison = [self.TEST_UNIT, self.TEST_UNIT_2, self.TEST_UNIT_3, extra_unit]

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False)

        self.assertFalse(extra_unit.garrisoned)
        self.assertIn(extra_unit, self.TEST_PLAYER.units)
        # The remaining three units should still be in the garrison.
        self.assertEqual(3, len(self.TEST_SETTLEMENT.garrison))

    def test_make_move_unit_is_moved(self):
        """
        Ensure that the appropriate moving method is called for each of the AI player units.
        """
        # Give the opposing player a unit so that we can fully test the arguments supplied to the mock.
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_2]
        self.movemaker.move_unit = MagicMock()

        self.movemaker.make_move(self.TEST_PLAYER, [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 self.QUADS, self.TEST_CONFIG, False)

        self.assertEqual(1, self.movemaker.move_unit.call_count)
        self.movemaker.move_unit.assert_called_with(self.TEST_PLAYER, self.TEST_UNIT, [self.TEST_UNIT_2],
                                                    [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                                    [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2],
                                                    self.QUADS, self.TEST_CONFIG)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_make_move_negative_wealth(self):
        """
        Ensure that when an AI player would have negative wealth at the end of their turn, they stay ahead of the curve
        and sell a unit.
        """
        self.assertTrue(self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_PLAYER.wealth)
        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False)
        self.assertEqual(self.TEST_UNIT.plan.cost, self.TEST_PLAYER.wealth)
        self.assertFalse(self.TEST_PLAYER.units)

    def test_move_settler_unit_not_far_enough(self):
        """
        Ensure that when a settler unit has not moved far enough away from its original settlement, it does not found a
        new settlement.
        """
        # We place the settler unit on top of its original settlement. Since its stamina is 5, it will not be able to
        # reach the required 10 quad away distance to found a new settlement.
        self.TEST_SETTLER_UNIT.location = self.TEST_SETTLEMENT.location
        self.TEST_PLAYER.units.append(self.TEST_SETTLER_UNIT)

        self.assertEqual(1, len(self.TEST_PLAYER.settlements))
        self.assertEqual(2, len(self.TEST_PLAYER.units))
        self.movemaker.move_settler_unit(self.TEST_SETTLER_UNIT, self.TEST_PLAYER, [], [self.TEST_SETTLEMENT])
        # The unit should have moved and used its stamina, but should not have founded a settlement.
        self.assertNotEqual(self.TEST_SETTLEMENT.location, self.TEST_SETTLER_UNIT.location)
        self.assertFalse(self.TEST_SETTLER_UNIT.remaining_stamina)
        self.assertEqual(1, len(self.TEST_PLAYER.settlements))
        self.assertEqual(2, len(self.TEST_PLAYER.units))

    def test_move_settler_unit_far_enough_frontiersmen(self):
        """
        Ensure that when a settler unit has moved far enough away from its original Frontiersmen settlement, it founds
        a new settlement.
        """
        # Put the test settlement smack bang in the middle of the board so that we can't be caught out by the unit
        # being too close to the edge of the board to move far enough away.
        self.TEST_SETTLEMENT.location = 50, 50
        # Give the test unit sufficient stamina to always be able to move far enough away.
        self.TEST_SETTLER_PLAN.total_stamina = 50
        self.TEST_SETTLER_UNIT.remaining_stamina = 50
        self.TEST_SETTLER_UNIT.location = self.TEST_SETTLEMENT.location
        self.TEST_PLAYER.units.append(self.TEST_SETTLER_UNIT)
        self.TEST_PLAYER.faction = Faction.FRONTIERSMEN

        self.assertEqual(1, len(self.TEST_PLAYER.settlements))
        self.assertEqual(2, len(self.TEST_PLAYER.units))
        self.movemaker.move_settler_unit(self.TEST_SETTLER_UNIT, self.TEST_PLAYER, [], [self.TEST_SETTLEMENT])
        # The settler should have moved away from the settlement and used all of its stamina.
        self.assertNotEqual(self.TEST_SETTLEMENT.location, self.TEST_SETTLER_UNIT.location)
        self.assertFalse(self.TEST_SETTLER_UNIT.remaining_stamina)
        # However, since it's also now far enough away, a new settlement should have been founded and the unit should
        # have been disassociated with the player.
        self.assertEqual(2, len(self.TEST_PLAYER.settlements))
        self.assertEqual(1, len(self.TEST_PLAYER.units))
        # Since the player is of the Frontiersmen faction, we expect the satisfaction to be initially elevated as well.
        self.assertEqual(75, self.TEST_PLAYER.settlements[1].satisfaction)

    def test_move_settler_unit_far_enough_imperials(self):
        """
        Ensure that when a settler unit has moved far enough away from its original Imperials settlement, it founds a
        new settlement.
        """
        # Put the test settlement smack bang in the middle of the board so that we can't be caught out by the unit
        # being too close to the edge of the board to move far enough away.
        self.TEST_SETTLEMENT.location = 50, 50
        # Give the test unit sufficient stamina to always be able to move far enough away.
        self.TEST_SETTLER_PLAN.total_stamina = 50
        self.TEST_SETTLER_UNIT.remaining_stamina = 50
        self.TEST_SETTLER_UNIT.location = self.TEST_SETTLEMENT.location
        self.TEST_PLAYER.units.append(self.TEST_SETTLER_UNIT)
        self.TEST_PLAYER.faction = Faction.IMPERIALS

        self.assertEqual(1, len(self.TEST_PLAYER.settlements))
        self.assertEqual(2, len(self.TEST_PLAYER.units))
        self.movemaker.move_settler_unit(self.TEST_SETTLER_UNIT, self.TEST_PLAYER, [], [self.TEST_SETTLEMENT])
        # The settler should have moved away from the settlement and used all of its stamina.
        self.assertNotEqual(self.TEST_SETTLEMENT.location, self.TEST_SETTLER_UNIT.location)
        self.assertFalse(self.TEST_SETTLER_UNIT.remaining_stamina)
        # However, since it's also now far enough away, a new settlement should have been founded and the unit should
        # have been disassociated with the player.
        self.assertEqual(2, len(self.TEST_PLAYER.settlements))
        self.assertEqual(1, len(self.TEST_PLAYER.units))
        # Since the player is of the Imperials faction, we expect the strength to be permanently decreased as well.
        self.assertEqual(50, self.TEST_PLAYER.settlements[1].strength)
        self.assertEqual(50, self.TEST_PLAYER.settlements[1].max_strength)

    def test_move_unit_settler(self):
        """
        Ensure that when a settler unit is being moved, the appropriate method is called.
        """
        self.movemaker.move_settler_unit = MagicMock()
        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_SETTLER_UNIT, [], [], [], self.QUADS, self.TEST_CONFIG)
        self.movemaker.move_settler_unit.assert_called_with(self.TEST_SETTLER_UNIT, self.TEST_PLAYER, [], [])

    @patch("source.game_management.movemaker.move_healer_unit")
    def test_move_unit_healer(self, move_healer_mock: MagicMock):
        """
        Ensure that when a healer unit is being moved, the appropriate method is called.
        :param move_healer_mock: The mock implementation of the move_healer_unit() function.
        """
        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_HEALER_UNIT, [], [], [], self.QUADS, self.TEST_CONFIG)
        move_healer_mock.assert_called_with(self.TEST_PLAYER, self.TEST_HEALER_UNIT, [], [],
                                            self.QUADS, self.TEST_CONFIG)

    def test_move_unit_attack_infidel(self):
        """
        Ensure that when a unit is being moved and there is an infidel unit within range, the infidel unit is always
        attacked.
        """
        # By making the test player defensive, we guarantee that the reason for attack is the other unit's faction.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.units.append(self.TEST_UNIT_2)
        infidel_player = Player("Inf", Faction.INFIDELS, 0, 0, [], [self.TEST_UNIT_3], [], set(), set())

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_2, [self.TEST_UNIT_3],
                                 [self.TEST_PLAYER, infidel_player], [], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the infidel unit, and for an attack to have been made, killing both
        # units.
        self.assertTupleEqual((self.TEST_UNIT_3.location[0] - 1, self.TEST_UNIT_3.location[1]),
                              self.TEST_UNIT_2.location)
        self.assertFalse(self.TEST_UNIT_2.remaining_stamina)
        self.assertFalse(infidel_player.units)
        self.assertNotIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)

    def test_move_unit_attack_unit_because_besieged(self):
        """
        Ensure that when a unit is being moved for a player with one or more settlements under siege, the unit will
        always attack anything within range.
        """
        self.TEST_SETTLEMENT.besieged = True
        # By making the test player defensive, we guarantee that the reason for attack is the settlement being under
        # siege.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.units = [self.TEST_UNIT_3]
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_2]

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_3, [self.TEST_UNIT_2],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the other unit, and for an attack to have been made, killing both
        # units.
        self.assertTupleEqual((self.TEST_UNIT_2.location[0] + 1, self.TEST_UNIT_2.location[1]),
                              self.TEST_UNIT_3.location)
        self.assertFalse(self.TEST_UNIT_3.remaining_stamina)
        self.assertFalse(self.TEST_PLAYER_2.units)
        self.assertFalse(self.TEST_PLAYER.units)

    def test_move_unit_attack_unit_because_settlement_weakened(self):
        """
        Ensure that when a unit is being moved for a player with one or more settlements that are significantly
        weakened, the unit will always attack anything within range.
        """
        self.TEST_SETTLEMENT.strength = 1
        # By making the test player defensive, we guarantee that the reason for attack is the settlement weakened.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.units = [self.TEST_UNIT_3]
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_2]

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_3, [self.TEST_UNIT_2],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the other unit, and for an attack to have been made, killing both
        # units.
        self.assertTupleEqual((self.TEST_UNIT_2.location[0] + 1, self.TEST_UNIT_2.location[1]),
                              self.TEST_UNIT_3.location)
        self.assertFalse(self.TEST_UNIT_3.remaining_stamina)
        self.assertFalse(self.TEST_PLAYER_2.units)
        self.assertFalse(self.TEST_PLAYER.units)

    def test_move_unit_attack_unit_aggressive_ai(self):
        """
        Ensure that when a unit is being moved for an aggressive AI player, it will always attack if there are any enemy
        units within range.
        """
        self.TEST_PLAYER_2.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_3]
        self.TEST_PLAYER.units = [self.TEST_UNIT_2]
        self.movemaker.board_ref.overlay.toggle_attack = MagicMock()

        self.movemaker.move_unit(self.TEST_PLAYER_2, self.TEST_UNIT_3, [self.TEST_UNIT_2],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the other unit, and for an attack to have been made, killing both
        # units.
        self.assertTupleEqual((self.TEST_UNIT_2.location[0] + 1, self.TEST_UNIT_2.location[1]),
                              self.TEST_UNIT_3.location)
        self.assertFalse(self.TEST_UNIT_3.remaining_stamina)
        # Because the 'human' player in this test is being attacked, we also expect the overlay to have been toggled.
        self.movemaker.board_ref.overlay.toggle_attack.assert_called()
        self.assertFalse(self.TEST_PLAYER_2.units)
        self.assertFalse(self.TEST_PLAYER.units)

    def test_move_unit_attack_unit_neutral_ai(self):
        """
        Ensure that when a unit is being moved for a neutral AI player, it will attack if it has at least double the
        health of the enemy unit.
        """
        self.TEST_UNIT_3.health = 20
        self.TEST_UNIT_2.health = 10
        self.TEST_PLAYER.units = [self.TEST_UNIT_3]
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_2]

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_3, [self.TEST_UNIT_2],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the other unit, and for an attack to have been made, killing both
        # units.
        self.assertTupleEqual((self.TEST_UNIT_2.location[0] + 1, self.TEST_UNIT_2.location[1]),
                              self.TEST_UNIT_3.location)
        self.assertFalse(self.TEST_UNIT_3.remaining_stamina)
        self.assertFalse(self.TEST_PLAYER_2.units)
        self.assertFalse(self.TEST_PLAYER.units)

    def test_move_unit_attack_settlement_aggressive_ai(self):
        """
        Ensure that when a unit is being moved for an aggressive AI player, it will attack settlements within range if
        its health is at least double the strength of the settlement.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        self.TEST_UNIT.location = self.TEST_SETTLEMENT_2.location[0] - 2, self.TEST_SETTLEMENT_2.location[1]
        self.TEST_UNIT.health = 100
        self.TEST_SETTLEMENT_2.strength = 50
        self.movemaker.board_ref.overlay.toggle_setl_attack = MagicMock()

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER_2, self.TEST_PLAYER],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the settlement, and for an attack to have been made, harming both
        # the unit and the settlement.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertLess(self.TEST_UNIT.health, 100)
        self.assertLess(self.TEST_SETTLEMENT_2.strength, 50)
        # Because the 'human' player in this test is being attacked, we also expect the overlay to have been toggled.
        self.movemaker.board_ref.overlay.toggle_setl_attack.assert_called()

    @patch("source.game_management.movemaker.attack_setl")
    def test_move_unit_attack_settlement_attacker_killed(self, attack_setl_mock: MagicMock):
        """
        Ensure that when an attack occurs between a unit and a settlement and the attacker is killed, the appropriate
        state changes occur.
        :param attack_setl_mock: The mock implementation of the attack_setl() function. This is required because it is
        difficult (and potentially impossible) to recreate a situation where an AI unit will attack a settlement and be
        subsequently killed.
        """
        # Mock the results of the attack to show that the attacker was killed.
        attack_setl_mock.return_value = \
            SetlAttackData(self.TEST_UNIT, self.TEST_SETTLEMENT_2, self.TEST_PLAYER_2, 15, 2, True, True, False)

        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        self.TEST_UNIT.location = self.TEST_SETTLEMENT_2.location[0] - 2, self.TEST_SETTLEMENT_2.location[1]
        self.TEST_UNIT.health = 10
        self.TEST_SETTLEMENT_2.strength = 5
        self.movemaker.board_ref.overlay.toggle_setl_attack = MagicMock()

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER_2, self.TEST_PLAYER],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the settlement, and for an attack to have been made, killing the unit
        # and damaging the settlement.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertFalse(self.TEST_PLAYER.units)
        self.assertLess(self.TEST_SETTLEMENT_2.strength, 50)
        # Because the 'human' player in this test is being attacked, we also expect the overlay to have been toggled.
        self.movemaker.board_ref.overlay.toggle_setl_attack.assert_called()

    def test_move_unit_attack_settlement_neutral_ai(self):
        """
        Ensure that when a unit is being moved for a neutral AI player, it will attack settlements within range if
        its health is at least 10x the strength of the settlement.
        """
        self.TEST_UNIT.location = self.TEST_SETTLEMENT_2.location[0] + 2, self.TEST_SETTLEMENT_2.location[1]
        self.TEST_UNIT.health = 100
        # In this example, the unit is currently placing the settlement under siege.
        self.TEST_UNIT.besieging = True
        self.TEST_SETTLEMENT_2.strength = 10
        self.TEST_SETTLEMENT_2.besieged = True

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the settlement, and for an attack to have been made, taking the
        # settlement for the player and ending the siege.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertFalse(self.TEST_SETTLEMENT_2.besieged)
        self.assertFalse(self.TEST_UNIT.besieging)
        self.assertIn(self.TEST_SETTLEMENT_2, self.TEST_PLAYER.settlements)
        self.assertFalse(self.TEST_PLAYER_2.settlements)

    def test_move_unit_attack_settlement_defensive_ai(self):
        """
        Ensure that when a unit is being moved for a defensive AI player, it will attack settlements within range if
        the settlement has no remaining strength.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_UNIT.location = self.TEST_SETTLEMENT_2.location[0] + 2, self.TEST_SETTLEMENT_2.location[1]
        # In this example, the unit is currently placing the settlement under siege.
        self.TEST_UNIT.besieging = True
        self.TEST_SETTLEMENT_2.strength = 0
        self.TEST_SETTLEMENT_2.besieged = True

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the settlement, and for an attack to have been made, taking the
        # settlement for the player and ending the siege.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertFalse(self.TEST_SETTLEMENT_2.besieged)
        self.assertFalse(self.TEST_UNIT.besieging)
        self.assertIn(self.TEST_SETTLEMENT_2, self.TEST_PLAYER.settlements)
        self.assertFalse(self.TEST_PLAYER_2.settlements)

    def test_move_unit_besiege_settlement_aggressive_ai(self):
        """
        Ensure that when a unit is being moved for an aggressive AI player, it will place settlements within range under
        siege if the unit health to settlement strength ratio is not favourable enough.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        self.TEST_UNIT.location = self.TEST_SETTLEMENT_2.location[0] - 2, self.TEST_SETTLEMENT_2.location[1]
        # 10 vs 50 is clearly not favourable enough to attack, even for aggressive AIs.
        self.TEST_UNIT.health = 10
        self.TEST_SETTLEMENT_2.strength = 50
        self.movemaker.board_ref.overlay.toggle_siege_notif = MagicMock()

        self.assertFalse(self.TEST_UNIT.besieging)
        self.assertFalse(self.TEST_SETTLEMENT_2.besieged)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER_2, self.TEST_PLAYER],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the settlement, and for a siege to have been begun.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.TEST_UNIT.besieging)
        self.assertTrue(self.TEST_SETTLEMENT_2.besieged)
        # Because the 'human' player in this test is having their settlement placed under siege, we also expect the
        # overlay to have been toggled.
        self.movemaker.board_ref.overlay.toggle_siege_notif.assert_called_with(self.TEST_SETTLEMENT_2, self.TEST_PLAYER)

    def test_move_unit_besiege_settlement_neutral_ai(self):
        """
        Ensure that when a unit is being moved for a neutral AI player, it will place settlements within range under
        siege if the unit health to settlement strength ratio is not favourable enough.
        """
        self.TEST_UNIT.location = self.TEST_SETTLEMENT_2.location[0] + 2, self.TEST_SETTLEMENT_2.location[1]
        # For a neutral AI, 2:1 is not good enough to attack.
        self.TEST_UNIT.health = 100
        self.TEST_SETTLEMENT_2.strength = 50

        self.assertFalse(self.TEST_UNIT.besieging)
        self.assertFalse(self.TEST_SETTLEMENT_2.besieged)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG)

        # We expect the unit to have moved next to the settlement, and for a siege to have been begun.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.TEST_UNIT.besieging)
        self.assertTrue(self.TEST_SETTLEMENT_2.besieged)

    @patch("source.game_management.movemaker.search_for_relics_or_move")
    def test_move_unit_nothing_within_range(self, search_or_move_mock: MagicMock):
        """
        Ensure that in cases where a unit is being moved and there are no other units within range that present options
        for an attack or siege, the correct search/move function is called.
        :param search_or_move_mock: The mock implementation of the search_for_relics_or_move() function.
        """
        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [], [], self.QUADS, self.TEST_CONFIG)
        search_or_move_mock.assert_called_with(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)


if __name__ == '__main__':
    unittest.main()
