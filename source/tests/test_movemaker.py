import unittest
from unittest.mock import patch, MagicMock

from source.display.board import Board
from source.foundation.catalogue import Namer, UNIT_PLANS, BLESSINGS, get_unlockable_improvements, get_improvement, \
    get_available_improvements, get_unit_plan, IMPROVEMENTS, SETL_NAMES
from source.foundation.models import GameConfig, Faction, Unit, Player, Settlement, AIPlaystyle, AttackPlaystyle, \
    ExpansionPlaystyle, Blessing, Quad, Biome, UnitPlan, SetlAttackData, Construction, DeployerUnitPlan, DeployerUnit, \
    VictoryType, ResourceCollection, MultiplayerStatus
from source.game_management.movemaker import search_for_relics_or_move, set_blessing, set_player_construction, \
    set_ai_construction, MoveMaker, move_healer_unit


class MovemakerTest(unittest.TestCase):
    """
    The test class for movemaker.py.
    """
    TEST_CONFIG = GameConfig(2, Faction.NOCTURNE, True, True, True, MultiplayerStatus.DISABLED)
    TEST_BOARD = Board(TEST_CONFIG, Namer(), {})

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
        self.TEST_UNIT_4 = Unit(19, 20, (21, 22), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_5 = Unit(23, 24, (25, 26), False, self.TEST_UNIT_PLAN)
        self.TEST_DEPLOYER_UNIT_PLAN = DeployerUnitPlan(0, 20, 10, "Big Cube", None, 25, max_capacity=5)
        self.TEST_DEPLOYER_UNIT = DeployerUnit(20, 10, (30, 31), False, self.TEST_DEPLOYER_UNIT_PLAN)

        self.movemaker = MoveMaker(Namer())
        self.movemaker.board_ref = self.TEST_BOARD
        self.TEST_BOARD.generate_quads(self.TEST_CONFIG.biome_clustering, self.TEST_CONFIG.climatic_effects)
        self.QUADS = self.TEST_BOARD.quads
        # We need to find a relic quad before each test, because the quads are re-generated each time.
        self.relic_coords: (int, int) = -1, -1
        for i in range(2, 90):
            for j in range(2, 80):
                if self.QUADS[j][i].is_relic:
                    self.relic_coords = i, j
                    break
            if self.relic_coords[0] != -1:
                break
        # More than one relic can make the tests unreliable, so remove all others.
        for i in range(90):
            for j in range(80):
                if self.QUADS[j][i].is_relic and self.relic_coords != (i, j):
                    self.QUADS[j][i].is_relic = False

        self.TEST_SETTLEMENT = Settlement("Obstructionville", (0, 0), [], [self.QUADS[0][0]], ResourceCollection(), [])
        self.TEST_SETTLEMENT_2 = Settlement("EnemyTown", (40, 40), [], [self.QUADS[40][40]], ResourceCollection(), [])
        self.TEST_SETTLEMENT_3 = Settlement("AlsoEnemyTown", (45, 45), [],
                                            [self.QUADS[45][45]], ResourceCollection(), [])
        self.TEST_SETTLEMENT_4 = Settlement("FarAwayVillage", (80, 80), [],
                                            [self.QUADS[80][80]], ResourceCollection(), [])
        self.TEST_PLAYER = Player("TesterMan", Faction.NOCTURNE, 0,
                                  settlements=[self.TEST_SETTLEMENT], units=[self.TEST_UNIT],
                                  ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))
        self.TEST_PLAYER_2 = Player("TesterMan2", Faction.AGRICULTURISTS, 0, settlements=[self.TEST_SETTLEMENT_2],
                                    ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))
        self.TEST_PLAYER_3 = Player("TesterMan3", Faction.FUNDAMENTALISTS, 0,
                                    ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL))

        # Position the other two units and settlement to be surrounding the relic, obstructing its access.
        self.TEST_UNIT_2.location = self.relic_coords[0] - 1, self.relic_coords[1]
        self.TEST_UNIT_3.location = self.relic_coords[0], self.relic_coords[1] + 1
        self.TEST_SETTLEMENT.location = self.relic_coords[0], self.relic_coords[1] - 1
        self.TEST_SETTLEMENT.quads = [self.QUADS[self.relic_coords[1] - 1][self.relic_coords[0]]]

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
        Ensure than a defensive AI player's blessing is set to the first one that unlocks an improvement that yields
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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 0, 100, 1, 1, self.TEST_SETTLEMENT.location)]
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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.DESERT, 100, 99, 100, 100, self.TEST_SETTLEMENT.location)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())
        # Remove a blessing to create a suitable test environment.
        self.TEST_PLAYER.blessings.remove(BLESSINGS["art_pht"])
        # We need to give the player sufficient resources in order to demonstrate that a lack of resources is not
        # preventing any improvement from being constructed.
        self.TEST_PLAYER.resources = ResourceCollection(ore=20, timber=20, magma=20)

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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 2, 100, 1, 2, self.TEST_SETTLEMENT.location)]
        # We need to make sure the player has sufficient resources to construct the intended improvement.
        self.TEST_PLAYER.resources = ResourceCollection(timber=20)
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_player_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Technically, Automated Production, which grants 30 zeal is the ideal improvement for this situation.
        # However, that improvement also decreases satisfaction by 10, meaning that the settlement's satisfaction would
        # be lowered to 40, which is not ideal. As such, Endless Mine is selected instead, as it has the next most
        # zeal and does not negatively impact satisfaction.
        self.assertEqual(get_improvement("Endless Mine"), self.TEST_SETTLEMENT.current_work.construction)
        # We also expect the player's resources to have been exhausted.
        self.assertFalse(self.TEST_PLAYER.resources)

    @patch("source.game_management.movemaker.get_available_improvements")
    def test_set_player_construction_fortune(self, imps_mock: MagicMock):
        """
        Ensure that when a player's settlement is lacking fortune, the correct improvement is selected for construction.
        :param imps_mock: The mock implementation of the get_available_improvements() function.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 2, 100, 2, 1, self.TEST_SETTLEMENT.location)]
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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1, self.TEST_SETTLEMENT.location)]
        self.TEST_SETTLEMENT.satisfaction = 49
        # Give the settlement all the improvements in the first 'tier' that grant satisfaction.
        self.TEST_SETTLEMENT.improvements = [
            get_improvement("Aqueduct"),
            get_improvement("Collectivised Farms"),
            get_improvement("City Market"),
            get_improvement("Melting Pot"),
            get_improvement("Insurmountable Walls")
        ]
        # We need to make sure the player has sufficient resources to construct the intended improvement.
        self.TEST_PLAYER.resources = ResourceCollection(ore=5)
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_player_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False)
        # Since any of the improvements in the second 'tier' take too many turns, we expect the ideal improvement to be
        # selected instead. In this case, the ideal improvement is Local Forge, since zeal is the lowest of the four.
        self.assertEqual(get_improvement("Local Forge"), self.TEST_SETTLEMENT.current_work.construction)
        # We also expect the player's resources to have been exhausted.
        self.assertFalse(self.TEST_PLAYER.resources)

    def test_set_player_construction_unsatisfied(self):
        """
        Ensure that when a player's settlement is below 50 satisfaction, the improvement that would grant the most
        combined satisfaction and harvest upon completion without taking too many turns is selected for construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1, self.TEST_SETTLEMENT.location)]
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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 100, 0, 100, 100, self.TEST_SETTLEMENT.location)]
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

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        self.assertEqual(UNIT_PLANS[0], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_settler(self):
        """
        Ensure that AI players of different expansion playstyles produce settlers in their settlements at different
        levels.
        """
        # Expansionist AI players should produce a settler when their settlement reaches level 3.
        self.TEST_PLAYER.ai_playstyle.expansion = ExpansionPlaystyle.EXPANSIONIST
        self.TEST_SETTLEMENT.level = 2
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # So, at level 2, we expect the construction to not be the settler unit (UNIT_PLANS[3]).
        self.assertNotEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

        self.TEST_SETTLEMENT.level = 3
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # Now at level 3, we expect a settler to be constructed.
        self.assertEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

        # Neutral AI players should produce a settler when their settlement reaches level 5.
        self.TEST_PLAYER.ai_playstyle.expansion = ExpansionPlaystyle.NEUTRAL
        self.TEST_SETTLEMENT.level = 4
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # At level 4, we expect the construction to not be the settler unit.
        self.assertNotEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

        self.TEST_SETTLEMENT.level = 5
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # Now at level 5, we expect a settler to be constructed.
        self.assertEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

        # Hermit AI players should only produce a settler once their settlement reaches the maximum level of 10.
        self.TEST_PLAYER.ai_playstyle.expansion = ExpansionPlaystyle.HERMIT
        self.TEST_SETTLEMENT.level = 9
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # At level 9, we expect the construction to not be the settler unit.
        self.assertNotEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

        self.TEST_SETTLEMENT.level = 10
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # Now at level 10, we expect a settler to be constructed.
        self.assertEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_settler_concentrated(self):
        """
        Ensure that AI players of the Concentrated faction do not construct settlers at any level.
        """
        self.TEST_SETTLEMENT.level = 10
        self.TEST_PLAYER.faction = Faction.CONCENTRATED
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # We expect the construction to not be the settler unit (UNIT_PLANS[3]).
        self.assertNotEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_settler_already_produced(self):
        """
        Ensure that AI player settlements that have already produced a settler cannot produce another one.
        """
        self.TEST_SETTLEMENT.level = 10
        self.TEST_SETTLEMENT.produced_settler = True
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # We expect the construction to not be the settler unit (UNIT_PLANS[3]).
        self.assertNotEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_settler_dissatisfied(self):
        """
        Ensure that AI players with only dissatisfied settlements produce settlers as soon as their level increases.
        """
        self.TEST_SETTLEMENT.level = 2
        self.TEST_SETTLEMENT.satisfaction = 0
        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # We expect the construction to not be the settler unit (UNIT_PLANS[3]).
        self.assertEqual(UNIT_PLANS[3], self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_wealth(self):
        """
        Ensure that when an AI player's settlement is lacking wealth, the correct improvement is selected for
        construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 0, 100, 1, 1, self.TEST_SETTLEMENT.location)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())
        # Remove a blessing to create a suitable test environment.
        self.TEST_PLAYER.blessings.remove(BLESSINGS["sl_vau"])

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.DESERT, 100, 99, 100, 100, self.TEST_SETTLEMENT.location)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())
        # Remove a blessing to create a suitable test environment.
        self.TEST_PLAYER.blessings.remove(BLESSINGS["art_pht"])
        # We need to give the player sufficient resources in order to demonstrate that a lack of resources is not
        # preventing any improvement from being constructed.
        self.TEST_PLAYER.resources = ResourceCollection(ore=20, timber=20, magma=20)

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 2, 100, 1, 2, self.TEST_SETTLEMENT.location)]
        # We need to make sure the player has sufficient resources to construct the intended improvement.
        self.TEST_PLAYER.resources = ResourceCollection(timber=20)
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # Technically, Automated Production, which grants 30 zeal is the ideal improvement for this situation.
        # However, that improvement also decreases satisfaction by 10, meaning that the settlement's satisfaction would
        # be lowered to 40, which is not ideal. As such, Endless Mine is selected instead, as it has the next most
        # zeal and does not negatively impact satisfaction.
        self.assertEqual(get_improvement("Endless Mine"), self.TEST_SETTLEMENT.current_work.construction)
        # We also expect the player's resources to have been exhausted.
        self.assertFalse(self.TEST_PLAYER.resources)

    @patch("source.game_management.movemaker.get_available_improvements")
    def test_set_ai_construction_fortune(self, imps_mock: MagicMock):
        """
        Ensure that when an AI player's settlement is lacking fortune, the correct improvement is selected for
        construction.
        :param imps_mock: The mock implementation of the get_available_improvements() function.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 2, 100, 2, 1, self.TEST_SETTLEMENT.location)]
        self.TEST_PLAYER.blessings = [BLESSINGS["beg_spl"]]
        # We need to mock out the available improvements so as to achieve full coverage, reaching a block where the
        # improvement with the most fortune is updated. We do this by simply switching the first two improvements in the
        # list, as the eventual selection is normally the first in the list.
        test_imps = get_available_improvements(self.TEST_PLAYER, self.TEST_SETTLEMENT)
        test_imps[0], test_imps[1] = test_imps[1], test_imps[0]
        imps_mock.return_value = test_imps

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1, self.TEST_SETTLEMENT.location)]
        self.TEST_SETTLEMENT.satisfaction = 49
        # Give the settlement all the improvements in the first 'tier' that grant satisfaction.
        self.TEST_SETTLEMENT.improvements = [
            get_improvement("Aqueduct"),
            get_improvement("Collectivised Farms"),
            get_improvement("City Market"),
            get_improvement("Melting Pot"),
            get_improvement("Insurmountable Walls")
        ]
        # We need to make sure that the player has sufficient resources to construct the intended improvement.
        self.TEST_PLAYER.resources = ResourceCollection(ore=5)
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # Since any of the improvements in the second 'tier' take too many turns, we expect the ideal improvement to be
        # selected instead. In this case, the ideal improvement is Local Forge, since zeal is the lowest of the four.
        self.assertEqual(get_improvement("Local Forge"), self.TEST_SETTLEMENT.current_work.construction)
        # We also expect the player's resources to have been exhausted.
        self.assertFalse(self.TEST_PLAYER.resources)

    def test_set_ai_construction_unsatisfied(self):
        """
        Ensure that when an AI player's settlement is below 50 satisfaction, the improvement that would grant the most
        combined satisfaction and harvest upon completion without taking too many turns is selected for construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1, self.TEST_SETTLEMENT.location)]
        self.TEST_SETTLEMENT.satisfaction = 49
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # We expect the Aqueduct improvement to be selected, as it grants 2 harvest and 5 satisfaction, which is the
        # most combined in the first 'tier' of improvements.
        self.assertEqual(get_improvement("Aqueduct"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_harvest_boundary(self):
        """
        Ensure that when an AI player's settlement is below the harvest boundary, the improvement that would grant the
        most harvest upon completion without taking too many turns is selected for construction.
        """
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 100, 0, 100, 100, self.TEST_SETTLEMENT.location)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # We expect the Collectivised Farms improvement to be selected, as it grants 10 harvest, which is the most in
        # the first 'tier' of improvements.
        self.assertEqual(get_improvement("Collectivised Farms"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_other_player_vic_deployer(self):
        """
        Ensure that when another player has an imminent victory, AI players construct deployer units.
        """
        self.TEST_PLAYER.blessings = BLESSINGS.values()
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1, self.TEST_SETTLEMENT.location)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [(self.TEST_PLAYER_2, 1)])
        # We expect a Golden Van to be constructed because it has the highest max capacity for a deployer unit, and the
        # AI player has undergone all blessings, thus unlocking it.
        self.assertEqual(get_unit_plan("Golden Van", Faction.AGRICULTURISTS),
                         self.TEST_SETTLEMENT.current_work.construction)

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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1, self.TEST_SETTLEMENT.location)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # We expect the Narcotician unit plan to be selected, as it has the greatest healing ability of all units.
        self.assertEqual(get_unit_plan("Narcotician", Faction.AGRICULTURISTS),
                         self.TEST_SETTLEMENT.current_work.construction)

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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1, self.TEST_SETTLEMENT.location)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # We expect the Haruspex unit plan to be selected, as it has the greatest power of all units.
        self.assertEqual(get_unit_plan("Haruspex", Faction.AGRICULTURISTS),
                         self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_aggressive_enough_units(self):
        """
        Ensure that when an aggressive AI player settlement already has enough units, the ideal construction is selected
        instead.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 2, 100, 1, 2, self.TEST_SETTLEMENT.location)]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # Normally, an aggressive AI would select a healer or a unit, but since they already have enough, their ideal
        # improvement is selected instead. In this case, it is Genetic Clinics.
        self.assertEqual(get_improvement("Genetic Clinics"), self.TEST_SETTLEMENT.current_work.construction)

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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1, self.TEST_SETTLEMENT.location)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # We expect the Narcotician unit plan to be selected, as it has the greatest healing ability of all units.
        self.assertEqual(get_unit_plan("Narcotician", Faction.AGRICULTURISTS),
                         self.TEST_SETTLEMENT.current_work.construction)

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
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1, self.TEST_SETTLEMENT.location)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # We expect the Fanatic unit plan to be selected, as it has the greatest health of all units.
        self.assertEqual(get_unit_plan("Fanatic", Faction.AGRICULTURISTS),
                         self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_defensive_strength_improvement(self):
        """
        Ensure that when a defensive AI player settlement has enough units, but there are improvements available that
        increase settlement strength, said improvements are selected for construction.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.blessings = BLESSINGS.values()
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 1, 100, 0, 1, self.TEST_SETTLEMENT.location)]

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # Since Insurmountable Walls is the first improvement that increases strength, we expect it to be chosen.
        self.assertEqual(get_improvement("Insurmountable Walls"), self.TEST_SETTLEMENT.current_work.construction)

    def test_set_ai_construction_defensive_enough_units_no_strength_improvements(self):
        """
        Ensure that when a defensive AI player settlement already has enough units and there are no improvements
        available that increase strength, the ideal construction is selected instead.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        # Harvest needs to be higher so that we are above the harvest boundary.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, 100, 100, 0, 100, self.TEST_SETTLEMENT.location)]
        # Give the settlement all the improvements that increase strength.
        self.TEST_SETTLEMENT.improvements = [imp for imp in IMPROVEMENTS if imp.effect.strength > 0]
        self.TEST_PLAYER.blessings = list(BLESSINGS.values())

        set_ai_construction(self.TEST_PLAYER, self.TEST_SETTLEMENT, False, [])
        # Normally, a defensive AI would select a healer, a unit, or an improvement that yields strength, but since they
        # already have enough units and there aren't any improvements of that kind available, their ideal improvement is
        # selected instead. In this case, it is Genetic Clinics.
        self.assertEqual(get_improvement("Genetic Clinics"), self.TEST_SETTLEMENT.current_work.construction)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_success_left(self):
        """
        Ensure that when a relic is within range and to the left of a unit, the unit investigates and removes it.
        """
        self.TEST_UNIT.location = self.relic_coords[0] - 2, self.relic_coords[1]

        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[1]][self.relic_coords[0]].is_relic)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)

        # The unit should have moved directly to the left of the relic, and the quad should no longer have a relic.
        self.assertTupleEqual((self.relic_coords[0] - 1, self.relic_coords[1]), self.TEST_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertFalse(self.QUADS[self.relic_coords[1]][self.relic_coords[0]].is_relic)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_success_right(self):
        """
        Ensure that when a relic is within range and to the right of a unit, the unit investigates and removes it.
        """
        self.TEST_UNIT.location = self.relic_coords[0] + 2, self.relic_coords[1]

        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[1]][self.relic_coords[0]].is_relic)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)

        # The unit should have moved directly to the right of the relic, and the quad should no longer have a relic.
        self.assertTupleEqual((self.relic_coords[0] + 1, self.relic_coords[1]), self.TEST_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertFalse(self.QUADS[self.relic_coords[1]][self.relic_coords[0]].is_relic)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_obstructed(self):
        """
        Ensure that when the three options for movement for a unit to a relic within range are obstructed, the unit just
        moves randomly instead. The three things that can obstruct a relic are player units, AI units, and settlements.
        In this test, we surround the relic with one of each.
        """
        self.TEST_PLAYER.units.append(self.TEST_UNIT_2)
        self.TEST_UNIT.location = self.relic_coords[0] - 2, self.relic_coords[1]

        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[1]][self.relic_coords[0]].is_relic)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [self.TEST_UNIT_3],
                                  [self.TEST_SETTLEMENT], self.TEST_CONFIG)

        # Normally, the unit would move directly to the left of the relic, but it can't move there, and as such, the
        # quad should still have a relic.
        self.assertNotEqual((self.relic_coords[0] - 1, self.relic_coords[1]), self.TEST_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.QUADS[self.relic_coords[1]][self.relic_coords[0]].is_relic)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_search_for_relics_none_found(self):
        """
        Ensure that when there are no available relics, the unit moves randomly.
        """
        # Remove the last relic from the board.
        self.QUADS[self.relic_coords[0]][self.relic_coords[1]].is_relic = False

        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.assertTrue(self.TEST_UNIT.remaining_stamina)
        search_for_relics_or_move(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)
        # The player should now have a few quads added to their set of seen quads, around the unit's new location.
        self.assertTrue(self.TEST_PLAYER.quads_seen)
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

        self.assertFalse(self.TEST_PLAYER.quads_seen)
        move_healer_unit(self.TEST_PLAYER, self.TEST_HEALER_UNIT, [], [], self.QUADS, self.TEST_CONFIG)
        # The healer should have moved directly to the left of the heal-able unit and healed it.
        self.assertTupleEqual((self.TEST_UNIT.location[0] - 1, self.TEST_UNIT.location[1]),
                              self.TEST_HEALER_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
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

        self.assertFalse(self.TEST_PLAYER.quads_seen)
        move_healer_unit(self.TEST_PLAYER, self.TEST_HEALER_UNIT, [], [], self.QUADS, self.TEST_CONFIG)
        # The healer should have moved directly to the right of the heal-able unit and healed it.
        self.assertTupleEqual((self.TEST_UNIT.location[0] + 1, self.TEST_UNIT.location[1]),
                              self.TEST_HEALER_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_HEALER_UNIT.remaining_stamina)
        heal_mock.assert_called_with(self.TEST_HEALER_UNIT, self.TEST_UNIT)

    def test_make_move_blessing(self):
        """
        Ensure that when an AI player is making their move, if they have no ongoing blessing, one is set.
        """
        self.assertIsNone(self.TEST_PLAYER.ongoing_blessing)
        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False, 0)
        self.assertIsNotNone(self.TEST_PLAYER.ongoing_blessing)

    def test_make_move_set_construction(self):
        """
        Ensure that when an AI player is making their move, if they have a settlement with no current work, a
        construction is set for that settlement.
        """
        self.assertIsNone(self.TEST_SETTLEMENT.current_work)
        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False, 0)
        self.assertIsNotNone(self.TEST_SETTLEMENT.current_work)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_make_move_construction_buyout(self):
        """
        Ensure that when an AI player has more than 3x the required wealth to buyout a current construction, they do so.
        """
        self.TEST_SETTLEMENT.current_work = Construction(IMPROVEMENTS[-1])
        self.TEST_PLAYER.wealth = IMPROVEMENTS[-1].cost * 5

        self.assertFalse(self.TEST_SETTLEMENT.improvements)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False, 0)

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

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False, 0)

        # We expect the settlement to now have the improvement.
        self.assertIn(IMPROVEMENTS[0], self.TEST_SETTLEMENT.improvements)

    def test_make_move_settler_deployed(self):
        """
        Ensure that when an AI player has a settler unit garrisoned, it is deployed.
        """
        self.TEST_SETTLER_UNIT.garrisoned = True
        self.TEST_SETTLEMENT.garrison = [self.TEST_SETTLER_UNIT]

        self.assertNotIn(self.TEST_SETTLER_UNIT, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False, 0)

        self.assertFalse(self.TEST_SETTLER_UNIT.garrisoned)
        self.assertIn(self.TEST_SETTLER_UNIT, self.TEST_PLAYER.units)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)

    def test_make_move_aggressive_ai_deploy_unit(self):
        """
        Ensure that when an aggressive AI player has a unit garrisoned, it is deployed.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        self.TEST_UNIT_2.garrisoned = True
        self.TEST_SETTLEMENT.garrison = [self.TEST_UNIT_2]

        self.assertNotIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False, 0)

        self.assertFalse(self.TEST_UNIT_2.garrisoned)
        self.assertIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)
        self.assertTrue(self.TEST_PLAYER.quads_seen)

    def test_make_move_neutral_ai_deploy_unit(self):
        """
        Ensure that when a neutral AI player has a unit garrisoned, it is deployed.
        """
        # The test player is neutral by default, but we set it here as well for clarity.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.NEUTRAL
        self.TEST_UNIT_2.garrisoned = True
        self.TEST_SETTLEMENT.garrison = [self.TEST_UNIT_2]

        self.assertNotIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False, 0)

        self.assertFalse(self.TEST_UNIT_2.garrisoned)
        self.assertIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)
        self.assertTrue(self.TEST_PLAYER.quads_seen)

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
        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.make_move(self.TEST_PLAYER, [self.TEST_PLAYER, self.TEST_PLAYER_2], self.QUADS, self.TEST_CONFIG,
                                 False, 0)

        self.assertFalse(self.TEST_UNIT_2.garrisoned)
        self.assertIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)
        self.assertTrue(self.TEST_PLAYER.quads_seen)

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
        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False, 0)

        self.assertFalse(self.TEST_UNIT_2.garrisoned)
        self.assertIn(self.TEST_UNIT_2, self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)
        self.assertTrue(self.TEST_PLAYER.quads_seen)

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

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False, 0)

        self.assertFalse(extra_unit.garrisoned)
        self.assertIn(extra_unit, self.TEST_PLAYER.units)
        # The remaining three units should still be in the garrison.
        self.assertEqual(3, len(self.TEST_SETTLEMENT.garrison))
        self.assertTrue(self.TEST_PLAYER.quads_seen)

    def test_make_move_deploy_deployer_unit_other_player_vic(self):
        """
        Ensure that when another player has an imminent victory, all deployer units in garrisons are deployed.
        """
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.units = []
        # Give the player enough wealth so the deployed unit is not auto-sold.
        self.TEST_PLAYER.wealth = 999
        self.TEST_DEPLOYER_UNIT.garrisoned = True
        self.TEST_SETTLEMENT.garrison = [self.TEST_DEPLOYER_UNIT]
        self.TEST_PLAYER_2.imminent_victories = [VictoryType.AFFLUENCE]

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.make_move(self.TEST_PLAYER, [self.TEST_PLAYER_2], self.QUADS, self.TEST_CONFIG, False, 0)

        # The deployer unit should no longer be garrisoned, and the garrison itself should be empty.
        self.assertFalse(self.TEST_DEPLOYER_UNIT.garrisoned)
        self.assertIn(self.TEST_DEPLOYER_UNIT, self.TEST_PLAYER.units)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_SETTLEMENT.garrison)

    def test_make_move_unit_is_moved(self):
        """
        Ensure that the appropriate moving method is called for each of the AI player units.
        """
        # Give the opposing player a unit so that we can fully test the arguments supplied to the mock.
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_2]
        self.movemaker.move_unit = MagicMock()

        self.movemaker.make_move(self.TEST_PLAYER, [self.TEST_PLAYER, self.TEST_PLAYER_2], self.QUADS, self.TEST_CONFIG,
                                 False, 0)

        self.assertEqual(1, self.movemaker.move_unit.call_count)
        self.movemaker.move_unit.assert_called_with(self.TEST_PLAYER, self.TEST_UNIT, [self.TEST_UNIT_2],
                                                    [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                                    [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2],
                                                    self.QUADS, self.TEST_CONFIG, [], 0)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_make_move_negative_wealth(self):
        """
        Ensure that when an AI player would have negative wealth at the end of their turn, they stay ahead of the curve
        and sell a unit.
        """
        # Make sure that the settlement is not generating sufficient wealth to give the player positive wealth.
        self.TEST_SETTLEMENT.quads[0].wealth = 0

        self.assertTrue(self.TEST_PLAYER.units)
        self.assertFalse(self.TEST_PLAYER.wealth)
        self.movemaker.make_move(self.TEST_PLAYER, [], self.QUADS, self.TEST_CONFIG, False, 0)
        self.assertEqual(self.TEST_UNIT.plan.cost, self.TEST_PLAYER.wealth)
        self.assertFalse(self.TEST_PLAYER.units)

    @patch("source.game_management.movemaker.investigate_relic", lambda *args: None)
    def test_make_move_negative_wealth_doesnt_remove_already_removed_units(self):
        """
        Ensure that when an AI player would have negative wealth at the end of their turn, the unit will die in
        movement, so we cannot sell on negative wealth after unit dies.
        """
        # By making the test player defensive, we guarantee that the reason for attack is the other unit's faction.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.units[0] = self.TEST_UNIT_2
        wealth_before_combat = self.TEST_PLAYER.wealth
        infidel_player = Player("Inf", Faction.INFIDELS, 0, units=[self.TEST_UNIT_3])

        self.movemaker.make_move(self.TEST_PLAYER, [self.TEST_PLAYER, infidel_player], self.QUADS, self.TEST_CONFIG,
                                 False, 0)

        self.assertEqual(wealth_before_combat, self.TEST_PLAYER.wealth)
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
        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.movemaker.move_settler_unit(self.TEST_SETTLER_UNIT, self.TEST_PLAYER, [], [self.TEST_SETTLEMENT])
        # The unit should have moved and used its stamina, but should not have founded a settlement.
        self.assertNotEqual(self.TEST_SETTLEMENT.location, self.TEST_SETTLER_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_SETTLER_UNIT.remaining_stamina)
        self.assertEqual(1, len(self.TEST_PLAYER.settlements))
        self.assertEqual(2, len(self.TEST_PLAYER.units))

    def test_move_settler_unit_far_enough_but_no_resources(self):
        """
        Ensure that when a settler unit has moved far enough away from its original settlement, but to a quad that would
        not be able to exploit any resources, it does not found a new settlement.
        """
        # To make things consistent, remove resources from all quads to begin with.
        for i in range(90):
            for j in range(100):
                self.QUADS[i][j].resource = None

        # We place the settler unit sufficiently far from its original settlement.
        self.TEST_SETTLER_UNIT.location = self.TEST_SETTLEMENT.location[0] + 20, self.TEST_SETTLEMENT.location[1]
        self.TEST_PLAYER.units.append(self.TEST_SETTLER_UNIT)

        self.assertEqual(1, len(self.TEST_PLAYER.settlements))
        self.assertEqual(2, len(self.TEST_PLAYER.units))
        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.movemaker.move_settler_unit(self.TEST_SETTLER_UNIT, self.TEST_PLAYER, [], [self.TEST_SETTLEMENT])
        # The unit should have moved and used its stamina, but should not have founded a settlement due to the fact that
        # no quads have resources on the board.
        self.assertNotEqual(self.TEST_SETTLEMENT.location, self.TEST_SETTLER_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
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
        # Give every quad a resource, so settler units will settle.
        for i in range(90):
            for j in range(100):
                self.QUADS[i][j].resource = ResourceCollection(magma=1)

        self.assertEqual(1, len(self.TEST_PLAYER.settlements))
        self.assertEqual(2, len(self.TEST_PLAYER.units))
        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.movemaker.move_settler_unit(self.TEST_SETTLER_UNIT, self.TEST_PLAYER, [], [self.TEST_SETTLEMENT])
        # The settler should have moved away from the settlement and used all of its stamina.
        self.assertNotEqual(self.TEST_SETTLEMENT.location, self.TEST_SETTLER_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
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
        # Give every quad a resource, so settler units will settle.
        for i in range(90):
            for j in range(100):
                self.QUADS[i][j].resource = ResourceCollection(magma=1)

        self.assertEqual(1, len(self.TEST_PLAYER.settlements))
        self.assertEqual(2, len(self.TEST_PLAYER.units))
        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.movemaker.move_settler_unit(self.TEST_SETTLER_UNIT, self.TEST_PLAYER, [], [self.TEST_SETTLEMENT])
        # The settler should have moved away from the settlement and used all of its stamina.
        self.assertNotEqual(self.TEST_SETTLEMENT.location, self.TEST_SETTLER_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_SETTLER_UNIT.remaining_stamina)
        # However, since it's also now far enough away, a new settlement should have been founded and the unit should
        # have been disassociated with the player.
        self.assertEqual(2, len(self.TEST_PLAYER.settlements))
        self.assertEqual(1, len(self.TEST_PLAYER.units))
        # Since the player is of the Imperials faction, we expect the strength to be permanently decreased as well.
        self.assertEqual(50, self.TEST_PLAYER.settlements[1].strength)
        self.assertEqual(50, self.TEST_PLAYER.settlements[1].max_strength)

    @patch("random.choice")
    @patch("random.randint")
    def test_move_settler_unit_far_enough_obsidian(self, random_mock: MagicMock, choice_mock: MagicMock):
        """
        Ensure that when a settler unit has moved far enough away from its original settlement and is located next to an
        obsidian resource, the new settlement founded has the correct strength.
        """
        # By mocking out the random values, we guarantee that the settler unit will move ten quads down and ten quads
        # right. Note that we need a second value for the random.choice() mock as it is subsequently called when naming
        # the new settlement.
        random_mock.return_value = 10
        choice_mock.side_effect = [10, SETL_NAMES[self.QUADS[60][60].biome][0]]

        # Put the test settlement smack bang in the middle of the board so that we can't be caught out by the unit
        # being too close to the edge of the board to move far enough away. In combination with our above random mocks,
        # this guarantees that the new settlement will be placed at (60, 60).
        self.TEST_SETTLEMENT.location = 50, 50
        # Give the test unit stamina so that we can see it being reduced. Note that we don't really need to artificially
        # increase this like the other tests anyway because we are mocking out the random calls that normally use the
        # stamina for movement.
        self.TEST_SETTLER_PLAN.total_stamina = 20
        self.TEST_SETTLER_UNIT.remaining_stamina = 20
        self.TEST_SETTLER_UNIT.location = self.TEST_SETTLEMENT.location
        self.TEST_PLAYER.units.append(self.TEST_SETTLER_UNIT)
        # To make things consistent, remove resources from all quads to begin with.
        for i in range(90):
            for j in range(100):
                self.QUADS[i][j].resource = None
        # Put a magma resource and an obsidian resource either side of the location that the new settlement will be
        # founded.
        self.QUADS[59][60].resource = ResourceCollection(magma=1)
        self.QUADS[61][60].resource = ResourceCollection(obsidian=1)

        self.assertEqual(1, len(self.TEST_PLAYER.settlements))
        self.assertEqual(2, len(self.TEST_PLAYER.units))
        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.movemaker.move_settler_unit(self.TEST_SETTLER_UNIT, self.TEST_PLAYER, [], [self.TEST_SETTLEMENT])
        # The settler should have moved away from the settlement and used all of its stamina.
        self.assertNotEqual(self.TEST_SETTLEMENT.location, self.TEST_SETTLER_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_SETTLER_UNIT.remaining_stamina)
        # However, since it's also now far enough away, a new settlement should have been founded and the unit should
        # have been disassociated with the player.
        self.assertEqual(2, len(self.TEST_PLAYER.settlements))
        self.assertEqual(1, len(self.TEST_PLAYER.units))
        # We expect the settlement to have the appropriate resources, and have had the expected obsidian strength
        # effect applied.
        self.assertEqual(ResourceCollection(magma=1, obsidian=1), self.TEST_PLAYER.settlements[1].resources)
        self.assertEqual(150, self.TEST_PLAYER.settlements[1].strength)
        self.assertEqual(150, self.TEST_PLAYER.settlements[1].max_strength)

    def test_move_unit_settler(self):
        """
        Ensure that when a settler unit is being moved, the appropriate method is called.
        """
        self.movemaker.move_settler_unit = MagicMock()
        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_SETTLER_UNIT, [], [], [], self.QUADS, self.TEST_CONFIG, [],
                                 0)
        self.movemaker.move_settler_unit.assert_called_with(self.TEST_SETTLER_UNIT, self.TEST_PLAYER, [], [])

    @patch("source.game_management.movemaker.move_healer_unit")
    def test_move_unit_healer(self, move_healer_mock: MagicMock):
        """
        Ensure that when a healer unit is being moved, the appropriate method is called.
        :param move_healer_mock: The mock implementation of the move_healer_unit() function.
        """
        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_HEALER_UNIT, [], [], [], self.QUADS, self.TEST_CONFIG, [],
                                 0)
        move_healer_mock.assert_called_with(self.TEST_PLAYER, self.TEST_HEALER_UNIT, [], [],
                                            self.QUADS, self.TEST_CONFIG)

    def test_deployer_unit_returns_once_empty(self):
        """
        Ensure that once a deployer unit has deployed all of its passengers, it returns to the nearest settlement.
        """
        self.TEST_PLAYER.settlements = [self.TEST_SETTLEMENT_4, self.TEST_SETTLEMENT_2]
        # TEST_SETTLEMENT_4 is at (80, 80) and TEST_SETTLEMENT_2 is at (40, 40). Thus, by positioning the deployer unit
        # at (49, 49), it is closer to TEST_SETTLEMENT_2, and should go to that settlement.
        self.TEST_DEPLOYER_UNIT.location = 49, 49
        # Reduce the deployer unit's stamina to create suitable conditions for this test.
        self.TEST_DEPLOYER_UNIT.remaining_stamina = 5
        self.TEST_DEPLOYER_UNIT.passengers = []

        self.assertFalse(self.TEST_PLAYER.quads_seen)
        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_DEPLOYER_UNIT, [], [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 [self.TEST_SETTLEMENT_2, self.TEST_SETTLEMENT_4], self.QUADS, self.TEST_CONFIG,
                                 [(self.TEST_PLAYER_2, 2)], 0)
        # After the first move, the deployer unit should have moved in the direction of TEST_SETTLEMENT_2.
        self.assertTupleEqual((45, 45), self.TEST_DEPLOYER_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_DEPLOYER_UNIT.remaining_stamina)

        # Reset stamina, simulating the next turn.
        self.TEST_DEPLOYER_UNIT.remaining_stamina = 5

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_DEPLOYER_UNIT, [], [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 [self.TEST_SETTLEMENT_2, self.TEST_SETTLEMENT_4], self.QUADS, self.TEST_CONFIG,
                                 [(self.TEST_PLAYER_2, 2)], 0)
        # After the second move, the deployer unit should now be diagonally-adjacent to TEST_SETTLEMENT_2.
        self.assertTupleEqual((41, 41), self.TEST_DEPLOYER_UNIT.location)
        self.assertFalse(self.TEST_DEPLOYER_UNIT.remaining_stamina)

        # Reset stamina once more.
        self.TEST_DEPLOYER_UNIT.remaining_stamina = 5

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_DEPLOYER_UNIT, [], [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 [self.TEST_SETTLEMENT_2, self.TEST_SETTLEMENT_4], self.QUADS, self.TEST_CONFIG,
                                 [(self.TEST_PLAYER_2, 2)], 0)
        # Now that the deployer unit is close enough to the nearest settlement, we do not expect it to move any further.
        self.assertTupleEqual((41, 41), self.TEST_DEPLOYER_UNIT.location)
        self.assertTrue(self.TEST_DEPLOYER_UNIT.remaining_stamina)

    def test_deployer_unit_at_capacity_moves_toward_weakest_settlement_imminent_victory(self):
        """
        Ensure that if there is another player with an imminent victory, deployer units at max capacity move towards the
        weakest settlement belonging to said player.
        """
        # We have to verify that not only is the player with the most imminent victories selected, but the weakest
        # settlement of said player is also selected.
        self.TEST_PLAYER_2.settlements = [self.TEST_SETTLEMENT_2, self.TEST_SETTLEMENT_3]
        self.TEST_PLAYER_3.settlements = [self.TEST_SETTLEMENT_4]
        self.TEST_SETTLEMENT_3.strength = 90
        self.TEST_SETTLEMENT_4.strength = 80
        # Based on the above, we expect the deployer unit to move towards TEST_SETTLEMENT_3, as it belongs to
        # TEST_PLAYER_2, who has the most imminent victories, and it is weaker than that player's other settlement.
        self.TEST_SETTLEMENT_2.location = 70, 50
        self.TEST_SETTLEMENT_3.location = 40, 80
        self.TEST_PLAYER.units = [self.TEST_DEPLOYER_UNIT]
        self.TEST_DEPLOYER_UNIT.plan.max_capacity = 1
        self.TEST_DEPLOYER_UNIT.passengers = [self.TEST_UNIT]

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_DEPLOYER_UNIT, [],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2, self.TEST_PLAYER_3],
                                 [self.TEST_SETTLEMENT_2, self.TEST_SETTLEMENT_3, self.TEST_SETTLEMENT_4], self.QUADS,
                                 self.TEST_CONFIG, [(self.TEST_PLAYER_2, 2), (self.TEST_PLAYER_3, 1)], 0)

        # Beginning at (30, 31), we expect the deployer unit to move towards TEST_SETTLEMENT_3.
        self.assertTupleEqual((31, 40), self.TEST_DEPLOYER_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_DEPLOYER_UNIT.remaining_stamina)

    def test_deployer_unit_under_capacity_does_not_move_other_player_vic(self):
        """
        Ensure that when another player has an imminent victory, deployer units that are under capacity do not move.
        """
        self.TEST_DEPLOYER_UNIT.passengers = [self.TEST_UNIT]
        self.TEST_DEPLOYER_UNIT.location = (80, 90)
        self.TEST_PLAYER.units = [self.TEST_DEPLOYER_UNIT]

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_DEPLOYER_UNIT, [], [self.TEST_PLAYER_2], [], self.QUADS,
                                 self.TEST_CONFIG, [(self.TEST_PLAYER_2, 1)], 0)

        # The deployer unit's state should have remained the same.
        self.assertTupleEqual((80, 90), self.TEST_DEPLOYER_UNIT.location)
        self.assertTrue(self.TEST_DEPLOYER_UNIT.remaining_stamina)
        self.assertListEqual([self.TEST_UNIT], self.TEST_DEPLOYER_UNIT.passengers)
        self.assertListEqual([self.TEST_DEPLOYER_UNIT], self.TEST_PLAYER.units)

    def test_deployer_unit_deploys_unit_once_arrived_other_player_vic(self):
        """
        Ensure that when another player has an imminent victory, deployer units that have travelled to an enemy
        settlement deploy units once arrived.
        """
        self.TEST_DEPLOYER_UNIT.passengers = [self.TEST_UNIT]
        # Place the deployer unit within range (not in an attacking sense) of TEST_PLAYER_2's settlement.
        self.TEST_DEPLOYER_UNIT.location = \
            self.TEST_SETTLEMENT_2.location[0] - 2, self.TEST_SETTLEMENT_2.location[1] - 2
        self.TEST_PLAYER.units = [self.TEST_DEPLOYER_UNIT]

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_DEPLOYER_UNIT, [], [self.TEST_PLAYER_2], [], self.QUADS,
                                 self.TEST_CONFIG, [(self.TEST_PLAYER_2, 1)], 0)

        # We expect the deployer unit to not have moved, preserving its stamina.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] - 2, self.TEST_SETTLEMENT_2.location[1] - 2),
                              self.TEST_DEPLOYER_UNIT.location)
        self.assertTrue(self.TEST_DEPLOYER_UNIT.remaining_stamina)
        # However, we also expect its passenger to have been deployed to the right of it.
        self.assertFalse(self.TEST_DEPLOYER_UNIT.passengers)
        self.assertTupleEqual((self.TEST_DEPLOYER_UNIT.location[0] + 1, self.TEST_DEPLOYER_UNIT.location[1]),
                              self.TEST_UNIT.location)
        self.assertIn(self.TEST_UNIT, self.TEST_PLAYER.units)
        self.assertTrue(self.TEST_PLAYER.quads_seen)

    @patch("source.game_management.movemaker.search_for_relics_or_move")
    def test_deployer_unit_no_other_player_vic(self, search_or_move_mock: MagicMock):
        """
        Ensure that deployer units simply explore when no other players have imminent victories.
        """
        self.TEST_PLAYER.units = [self.TEST_DEPLOYER_UNIT]

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_DEPLOYER_UNIT, [], [], [], self.QUADS, self.TEST_CONFIG,
                                 [], 0)

        search_or_move_mock.assert_called_with(self.TEST_DEPLOYER_UNIT, self.QUADS,
                                               self.TEST_PLAYER, [], [], self.TEST_CONFIG)

    def test_move_unit_attack_infidel(self):
        """
        Ensure that when a unit is being moved and there is an infidel unit within range, the infidel unit is always
        attacked.
        """
        # By making the test player defensive, we guarantee that the reason for attack is the other unit's faction.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.units.append(self.TEST_UNIT_4)
        infidel_player = Player("Inf", Faction.INFIDELS, 0, units=[self.TEST_UNIT_5])

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_4, [self.TEST_UNIT_5],
                                 [self.TEST_PLAYER, infidel_player], [], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the infidel unit, and for an attack to have been made, killing both
        # units.
        self.assertTupleEqual((self.TEST_UNIT_5.location[0] - 1, self.TEST_UNIT_5.location[1]),
                              self.TEST_UNIT_4.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT_4.remaining_stamina)
        self.assertFalse(infidel_player.units)
        self.assertNotIn(self.TEST_UNIT_4, self.TEST_PLAYER.units)

    def test_move_unit_attack_close_to_elimination_victory(self):
        """
        Ensure that when a unit is being moved and there is a unit belonging to another player with an imminent
        Elimination victory within range, the unit is attacked.
        """
        # By making the test player defensive, we guarantee that the reason for attack is the AI player's imminent
        # victory.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.units = [self.TEST_UNIT_4]
        self.TEST_PLAYER_2.imminent_victories = [VictoryType.ELIMINATION]
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_5]

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_4, [self.TEST_UNIT_5],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the AI player's unit, and for an attack to have been made, killing
        # both units.
        self.assertTupleEqual((self.TEST_UNIT_5.location[0] - 1, self.TEST_UNIT_5.location[1]),
                              self.TEST_UNIT_4.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT_4.remaining_stamina)
        self.assertFalse(self.TEST_PLAYER_2.units)
        self.assertFalse(self.TEST_PLAYER.units)

    def test_move_unit_attack_unit_because_besieged(self):
        """
        Ensure that when a unit is being moved for a player with one or more settlements under siege, the unit will
        always attack anything within range.
        """
        self.TEST_SETTLEMENT.besieged = True
        # By making the test player defensive, we guarantee that the reason for attack is the settlement being under
        # siege.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_PLAYER.units = [self.TEST_UNIT_5]
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_4]

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_5, [self.TEST_UNIT_4],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the other unit, and for an attack to have been made, killing both
        # units.
        self.assertTupleEqual((self.TEST_UNIT_4.location[0] + 1, self.TEST_UNIT_4.location[1]),
                              self.TEST_UNIT_5.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT_5.remaining_stamina)
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
        self.TEST_PLAYER.units = [self.TEST_UNIT_5]
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_4]

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_5, [self.TEST_UNIT_4],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the other unit, and for an attack to have been made, killing both
        # units.
        self.assertTupleEqual((self.TEST_UNIT_4.location[0] + 1, self.TEST_UNIT_4.location[1]),
                              self.TEST_UNIT_5.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT_5.remaining_stamina)
        self.assertFalse(self.TEST_PLAYER_2.units)
        self.assertFalse(self.TEST_PLAYER.units)

    def test_move_unit_attack_unit_aggressive_ai(self):
        """
        Ensure that when a unit is being moved for an aggressive AI player, it will always attack if there are any enemy
        units within range.
        """
        self.TEST_PLAYER_2.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_5]
        self.TEST_PLAYER.units = [self.TEST_UNIT_4]
        self.movemaker.board_ref.overlay.toggle_attack = MagicMock()
        self.movemaker.board_ref.overlay.selected_unit = self.TEST_UNIT_4
        self.movemaker.board_ref.overlay.toggle_unit = MagicMock()

        self.assertFalse(self.TEST_PLAYER_2.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER_2, self.TEST_UNIT_5, [self.TEST_UNIT_4],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the other unit, and for an attack to have been made, killing both
        # units.
        self.assertTupleEqual((self.TEST_UNIT_4.location[0] + 1, self.TEST_UNIT_4.location[1]),
                              self.TEST_UNIT_5.location)
        self.assertTrue(self.TEST_PLAYER_2.quads_seen)
        self.assertFalse(self.TEST_UNIT_5.remaining_stamina)
        # Because the 'human' player in this test is being attacked, we also expect the overlay to have been toggled.
        self.movemaker.board_ref.overlay.toggle_attack.assert_called()
        # Additionally, since the 'human' player's unit was initially selected on the board and was then killed, we
        # also expect the unit overlay to have been toggled.
        self.movemaker.board_ref.overlay.toggle_unit.assert_called_with(None)
        self.assertIsNone(self.movemaker.board_ref.overlay.selected_unit)
        self.assertFalse(self.TEST_PLAYER_2.units)
        self.assertFalse(self.TEST_PLAYER.units)

    def test_move_unit_attack_unit_neutral_ai(self):
        """
        Ensure that when a unit is being moved for a neutral AI player, it will attack if it has at least double the
        health of the enemy unit.
        """
        self.TEST_UNIT_5.health = 20
        self.TEST_UNIT_4.health = 10
        self.TEST_PLAYER.units = [self.TEST_UNIT_5]
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_4]

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_5, [self.TEST_UNIT_4],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the other unit, and for an attack to have been made, killing both
        # units.
        self.assertTupleEqual((self.TEST_UNIT_4.location[0] + 1, self.TEST_UNIT_4.location[1]),
                              self.TEST_UNIT_5.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT_5.remaining_stamina)
        self.assertFalse(self.TEST_PLAYER_2.units)
        self.assertFalse(self.TEST_PLAYER.units)

    def test_move_unit_attack_unit_without_moving(self):
        """
        Ensure that when a unit finds another unit adjacent to it to attack, it does not move and preserves its stamina.
        """
        # For the sake of the test, the AI has an aggressive attack playstyle to guarantee that an attack will occur.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.AGGRESSIVE
        self.TEST_PLAYER.units = [self.TEST_UNIT_5]
        self.TEST_PLAYER_2.units = [self.TEST_UNIT_4]
        # Place the unit directly to the left of the enemy unit.
        self.TEST_UNIT_5.location = self.TEST_UNIT_4.location[0] - 1, self.TEST_UNIT_4.location[1]

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_5, [self.TEST_UNIT_4],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have remained next to the other unit, and for an attack to have been made, killing both
        # units. However, since the unit did not move, we expect it to still retain stamina.
        self.assertTupleEqual((self.TEST_UNIT_4.location[0] - 1, self.TEST_UNIT_4.location[1]),
                              self.TEST_UNIT_5.location)
        self.assertTrue(self.TEST_UNIT_5.remaining_stamina)
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

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER_2, self.TEST_PLAYER],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the settlement, and for an attack to have been made, harming both
        # the unit and the settlement.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
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

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER_2, self.TEST_PLAYER],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the settlement, and for an attack to have been made, killing the unit
        # and damaging the settlement.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
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

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the settlement, and for an attack to have been made, taking the
        # settlement for the player and ending the siege.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
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

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the settlement, and for an attack to have been made, taking the
        # settlement for the player and ending the siege.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertFalse(self.TEST_SETTLEMENT_2.besieged)
        self.assertFalse(self.TEST_UNIT.besieging)
        self.assertIn(self.TEST_SETTLEMENT_2, self.TEST_PLAYER.settlements)
        self.assertFalse(self.TEST_PLAYER_2.settlements)

    def test_move_unit_attack_settlement_imminent_victory(self):
        """
        Ensure that when a unit is being moved, it will attack settlements within range if the settlement's owner has an
        imminent victory.
        """
        # Note that we are giving the test player a defensive attack playstyle, demonstrating that if the settlement
        # owner has an imminent victory, it overrides all else.
        self.TEST_PLAYER.ai_playstyle.attacking = AttackPlaystyle.DEFENSIVE
        self.TEST_UNIT.location = self.TEST_SETTLEMENT_2.location[0] - 2, self.TEST_SETTLEMENT_2.location[1]
        self.TEST_UNIT.health = 100
        # Note that the settlement's strength is above what even an aggressive AI player would attack, and this test
        # player is defensive.
        self.TEST_SETTLEMENT_2.strength = 55
        self.TEST_PLAYER_2.imminent_victories = [VictoryType.SERENDIPITY]

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the settlement, and for an attack to have been made, harming both
        # the unit and the settlement.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertLess(self.TEST_UNIT.health, 100)
        self.assertLess(self.TEST_SETTLEMENT_2.strength, 50)

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
        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER_2, self.TEST_PLAYER],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the settlement, and for a siege to have been begun.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
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
        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [self.TEST_PLAYER, self.TEST_PLAYER_2],
                                 [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_2], self.QUADS, self.TEST_CONFIG, [], 0)

        # We expect the unit to have moved next to the settlement, and for a siege to have been begun.
        self.assertTupleEqual((self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1]),
                              self.TEST_UNIT.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT.remaining_stamina)
        self.assertTrue(self.TEST_UNIT.besieging)
        self.assertTrue(self.TEST_SETTLEMENT_2.besieged)

    def test_move_into_deployer_unit_imminent_victory(self):
        """
        Ensure that when another player has an imminent victory, units move into nearby deployer units if available.
        """
        self.TEST_PLAYER.units = [self.TEST_UNIT_4, self.TEST_DEPLOYER_UNIT]
        # Place the unit near the deployer unit.
        self.TEST_UNIT_4.location = self.TEST_DEPLOYER_UNIT.location[0] - 2, self.TEST_DEPLOYER_UNIT.location[1]
        self.TEST_DEPLOYER_UNIT.passengers = []

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_4, [self.TEST_DEPLOYER_UNIT],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2], [], self.QUADS, self.TEST_CONFIG,
                                 [(self.TEST_PLAYER_2, 1)], 0)

        # The unit should now be a passenger of the deployer unit.
        self.assertFalse(self.TEST_UNIT_4.remaining_stamina)
        self.assertIn(self.TEST_UNIT_4, self.TEST_DEPLOYER_UNIT.passengers)
        self.assertNotIn(self.TEST_UNIT_4, self.TEST_PLAYER.units)

    def test_move_towards_weakest_settlement_imminent_victory(self):
        """
        Ensure that if there is another player with an imminent victory, units move towards the weakest settlement
        belonging to said player.
        """
        # We have to verify that not only is the player with the most imminent victories selected, but the weakest
        # settlement of said player is also selected.
        self.TEST_PLAYER_2.settlements = [self.TEST_SETTLEMENT_2, self.TEST_SETTLEMENT_3]
        self.TEST_PLAYER_3.settlements = [self.TEST_SETTLEMENT_4]
        self.TEST_SETTLEMENT_3.strength = 90
        self.TEST_SETTLEMENT_4.strength = 80
        # Based on the above, we expect the unit to move towards TEST_SETTLEMENT_3, as it belongs to TEST_PLAYER_2, who
        # has the most imminent victories, and it is weaker than that player's other settlement.
        self.TEST_SETTLEMENT_2.location = 70, 50
        self.TEST_SETTLEMENT_3.location = 40, 80
        self.TEST_PLAYER.units = [self.TEST_UNIT_4]

        self.assertFalse(self.TEST_PLAYER.quads_seen)

        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT_4, [],
                                 [self.TEST_PLAYER, self.TEST_PLAYER_2, self.TEST_PLAYER_3],
                                 [self.TEST_SETTLEMENT_2, self.TEST_SETTLEMENT_3, self.TEST_SETTLEMENT_4], self.QUADS,
                                 self.TEST_CONFIG, [(self.TEST_PLAYER_2, 2), (self.TEST_PLAYER_3, 1)], 0)

        # Beginning at (21, 22), we expect the unit to move towards TEST_SETTLEMENT_3.
        self.assertTupleEqual((27, 41), self.TEST_UNIT_4.location)
        self.assertTrue(self.TEST_PLAYER.quads_seen)
        self.assertFalse(self.TEST_UNIT_4.remaining_stamina)

    @patch("source.game_management.movemaker.search_for_relics_or_move")
    def test_move_unit_nothing_within_range(self, search_or_move_mock: MagicMock):
        """
        Ensure that in cases where a unit is being moved and there are no other units within range that present options
        for an attack or siege, the correct search/move function is called.
        :param search_or_move_mock: The mock implementation of the search_for_relics_or_move() function.
        """
        self.movemaker.move_unit(self.TEST_PLAYER, self.TEST_UNIT, [], [], [], self.QUADS, self.TEST_CONFIG, [], 0)
        search_or_move_mock.assert_called_with(self.TEST_UNIT, self.QUADS, self.TEST_PLAYER, [], [], self.TEST_CONFIG)


if __name__ == '__main__':
    unittest.main()
