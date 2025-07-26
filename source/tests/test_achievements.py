import typing
import unittest
from itertools import chain

from source.display.board import Board
from source.foundation.achievements import verify_full_house, verify_its_worth_it, verify_the_third_x
from source.foundation.catalogue import ACHIEVEMENTS, IMPROVEMENTS, BLESSINGS, Namer
from source.foundation.models import Player, Faction, Settlement, AIPlaystyle, AttackPlaystyle, ExpansionPlaystyle, \
    Statistics, UnitPlan, Unit, Quad, Biome, Improvement, ImprovementType, Effect, VictoryType, HarvestStatus, \
    EconomicStatus, GameConfig, ResourceCollection, MultiplayerStatus
from source.game_management.game_state import GameState


class AchievementsTest(unittest.TestCase):
    """
    The test class responsible for ensuring that the verification functions for all achievements function as expected.
    """
    def setUp(self) -> None:
        """
        Initialise some test models, as well as the game state and its players.
        """
        self.TEST_UNIT_PLAN = UnitPlan(100, 100, 3, "Plan Man", None, 25)
        self.TEST_UNIT = Unit(1, 2, (3, 4), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_2 = Unit(5, 6, (7, 8), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_3 = Unit(9, 10, (11, 12), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_4 = Unit(13, 14, (15, 16), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_5 = Unit(17, 18, (19, 20), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_6 = Unit(21, 22, (23, 24), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_7 = Unit(25, 26, (27, 28), False, self.TEST_UNIT_PLAN)
        self.TEST_UNIT_8 = Unit(29, 30, (31, 32), False, self.TEST_UNIT_PLAN)
        self.TEST_QUAD = Quad(Biome.SEA, 0, 0, 0, 0, (0, 0))
        self.TEST_SETTLEMENT = Settlement("Numero Uno", (0, 0), [], [self.TEST_QUAD], ResourceCollection(), [])
        self.TEST_SETTLEMENT_2 = Settlement("Numero Dos", (2, 2), [],
                                            [Quad(Biome.SEA, 0, 0, 0, 0, (2, 2))], ResourceCollection(), [])
        self.TEST_SETTLEMENT_3 = Settlement("Numero Tres", (4, 4), [], [], ResourceCollection(), [])
        self.TEST_SETTLEMENT_4 = Settlement("Numero Quattro", (6, 6), [], [], ResourceCollection(), [])
        self.TEST_SETTLEMENT_5 = Settlement("Numero Cinco", (8, 8), [], [], ResourceCollection(), [])
        self.TEST_SETTLEMENT_6 = Settlement("Numero Seis", (10, 10), [], [], ResourceCollection(), [])

        self.game_state = GameState()
        self.game_state.players = [
            Player("Infidel", Faction.INFIDELS, 0, settlements=[self.TEST_SETTLEMENT],
                   units=[self.TEST_UNIT, self.TEST_UNIT_2, self.TEST_UNIT_3, self.TEST_UNIT_4, self.TEST_UNIT_5,
                          self.TEST_UNIT_6, self.TEST_UNIT_7, self.TEST_UNIT_8]),
            Player("Concentrator", Faction.CONCENTRATED, 0,
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL),
                   settlements=[self.TEST_SETTLEMENT_2]),
        ]
        self.game_state.player_idx = 0

    def test_full_house(self):
        """
        Ensure that verification for the 'Full House' achievement functions as expected.
        """
        # Make each of the test player's units besieging.
        for u in self.game_state.players[0].units:
            u.besieging = True
        # Position all but one of the test player's units around an enemy settlement.
        self.TEST_UNIT.location = (self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1] - 1)
        self.TEST_UNIT_2.location = (self.TEST_SETTLEMENT_2.location[0], self.TEST_SETTLEMENT_2.location[1] - 1)
        self.TEST_UNIT_3.location = (self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1] - 1)
        self.TEST_UNIT_4.location = (self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1])
        self.TEST_UNIT_5.location = (self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1])
        self.TEST_UNIT_6.location = (self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1] + 1)
        self.TEST_UNIT_7.location = (self.TEST_SETTLEMENT_2.location[0], self.TEST_SETTLEMENT_2.location[1] + 1)

        # Because the enemy settlement is not fully surrounded, the achievement should not be obtained.
        self._verify_achievement(verify_full_house, should_pass=False)

        # However, if we now position the last unit to fill the last gap around the settlement, the achievement should
        # be obtained.
        self.TEST_UNIT_8.location = (self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1] + 1)
        self._verify_achievement(verify_full_house, should_pass=True)

    def test_its_worth_it(self):
        """
        Ensure that verification for the 'It's Worth It' achievement functions as expected.
        """
        # A standard improvement with no effect should not result in the player obtaining the achievement.
        self.TEST_SETTLEMENT.improvements = [Improvement(ImprovementType.MAGICAL, 0, "TestImp", "", Effect(), None)]
        self._verify_achievement(verify_its_worth_it, should_pass=False)
        # However, an improvement that yields negative satisfaction should result in the player obtaining the
        # achievement.
        self.TEST_SETTLEMENT.improvements = \
            [Improvement(ImprovementType.MAGICAL, 0, "TestImp", "", Effect(satisfaction=-1), None)]
        self._verify_achievement(verify_its_worth_it, should_pass=True)

    def test_chicken_dinner(self):
        """
        Ensure that verification for the 'Chicken Dinner' achievement functions as expected.
        """
        self._verify_victory_type_achievement(ach_idx=0, victory_type=VictoryType.ELIMINATION)

    def test_fully_improved(self):
        """
        Ensure that verification for the 'Fully Improved' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[1].verification_fn, should_pass=False)
        # Once the settlement has all improvements apart from the final victory-related one, the achievement should be
        # obtained.
        self.TEST_SETTLEMENT.improvements = IMPROVEMENTS[0:-1]
        self._verify_achievement(ACHIEVEMENTS[1].verification_fn, should_pass=True)

    def test_harvest_galore(self):
        """
        Ensure that verification for the 'Harvest Galore' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[2].verification_fn, should_pass=False)
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_3, self.TEST_SETTLEMENT_4,
                                                  self.TEST_SETTLEMENT_5, self.TEST_SETTLEMENT_6]
        for s in self.game_state.players[0].settlements:
            s.harvest_status = HarvestStatus.PLENTIFUL
        # Five settlements with plentiful harvests should result in the player obtaining the achievement.
        self._verify_achievement(ACHIEVEMENTS[2].verification_fn, should_pass=True)

    def test_mansa_musa(self):
        """
        Ensure that verification for the 'Mansa Musa' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[3].verification_fn, should_pass=False)
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_3, self.TEST_SETTLEMENT_4,
                                                  self.TEST_SETTLEMENT_5, self.TEST_SETTLEMENT_6]
        for s in self.game_state.players[0].settlements:
            s.economic_status = EconomicStatus.BOOM
        # Five settlements with boom economies should result in the player obtaining the achievement.
        self._verify_achievement(ACHIEVEMENTS[3].verification_fn, should_pass=True)

    def test_last_one_standing(self):
        """
        Ensure that verification for the 'Last One Standing' achievement functions as expected.
        """
        self._verify_victory_type_achievement(ach_idx=4, victory_type=VictoryType.ELIMINATION)

    def test_they_love_me(self):
        """
        Ensure that verification for the 'They Love Me' achievement functions as expected.
        """
        self._verify_victory_type_achievement(ach_idx=5, victory_type=VictoryType.JUBILATION)

    def test_megalopoleis(self):
        """
        Ensure that verification for the 'Megalopoleis' achievement functions as expected.
        """
        self._verify_victory_type_achievement(ach_idx=6, victory_type=VictoryType.GLUTTONY)

    def test_wealth_upon_wealth(self):
        """
        Ensure that verification for the 'Wealth Upon Wealth' achievement functions as expected.
        """
        self._verify_victory_type_achievement(ach_idx=7, victory_type=VictoryType.AFFLUENCE)

    def test_sanctum_sanctorum(self):
        """
        Ensure that verification for the 'Sanctum Sanctorum' achievement functions as expected.
        """
        self._verify_victory_type_achievement(ach_idx=8, victory_type=VictoryType.VIGOUR)

    def test_arduously_blessed(self):
        """
        Ensure that verification for the 'Arduously Blessed' achievement functions as expected.
        """
        self._verify_victory_type_achievement(ach_idx=9, victory_type=VictoryType.SERENDIPITY)

    def test_grow_and_grow(self):
        """
        Ensure that verification for the 'Grow And Grow' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=10, faction=Faction.AGRICULTURISTS)

    def test_money_talks(self):
        """
        Ensure that verification for the 'Money Talks' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=11, faction=Faction.CAPITALISTS)

    def test_telescopic(self):
        """
        Ensure that verification for the 'Telescopic' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=12, faction=Faction.SCRUTINEERS)

    def test_suitably_skeptical(self):
        """
        Ensure that verification for the 'Suitably Skeptical' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=13, faction=Faction.GODLESS)

    def test_gallivanting_greed(self):
        """
        Ensure that verification for the 'Gallivanting Greed' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=14, faction=Faction.RAVENOUS)

    def test_the_clang_of_iron(self):
        """
        Ensure that verification for the 'The Clang Of Iron' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=15, faction=Faction.FUNDAMENTALISTS)

    def test_the_passionate_eye(self):
        """
        Ensure that verification for the 'The Passionate Eye' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=16, faction=Faction.ORTHODOX)

    def test_cloudscrapers(self):
        """
        Ensure that verification for the 'Cloudscrapers' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=17, faction=Faction.CONCENTRATED)

    def test_never_rest(self):
        """
        Ensure that verification for the 'Never Rest' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=18, faction=Faction.FRONTIERSMEN)

    def test_empirical_evidence(self):
        """
        Ensure that verification for the 'Empirical Evidence' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=19, faction=Faction.IMPERIALS)

    def test_the_singular_purpose(self):
        """
        Ensure that verification for the 'The Singular Purpose' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=20, faction=Faction.PERSISTENT)

    def test_cartographic_courage(self):
        """
        Ensure that verification for the 'Cartographic Courage' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=21, faction=Faction.EXPLORERS)

    def test_sub_human_super_success(self):
        """
        Ensure that verification for the 'Sub-Human, Super-Success' achievement functions as expected.
        """
        # We have to set the test player's faction to be a non-Infidel one to begin with, otherwise the expected failure
        # at the beginning of the helper method used will not occur.
        self.game_state.players[0].faction = Faction.AGRICULTURISTS
        self._verify_faction_victory_achievement(ach_idx=22, faction=Faction.INFIDELS)

    def test_shine_in_the_dark(self):
        """
        Ensure that verification for the 'Shine In The Dark' achievement functions as expected.
        """
        self._verify_faction_victory_achievement(ach_idx=23, faction=Faction.NOCTURNE)

    def test_the_golden_quad(self):
        """
        Ensure that verification for the 'The Golden Quad' achievement functions as expected.
        """
        # The default quad for the test settlement has no yield at all, so we expect the achievement to not be obtained.
        self._verify_achievement(ACHIEVEMENTS[24].verification_fn, should_pass=False)
        # However, if we swap out the quad for another with a total of 20 yield, we expect the achievement to be
        # obtained.
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, wealth=5, harvest=5, zeal=5, fortune=5, location=(0, 0))]
        self._verify_achievement(ACHIEVEMENTS[24].verification_fn, should_pass=True)

    def test_wholly_blessed(self):
        """
        Ensure that verification for the 'Wholly Blessed' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[25].verification_fn, should_pass=False)
        # Once the player has all blessings apart from the victory-related ones, the achievement should be obtained.
        self.game_state.players[0].blessings = list(BLESSINGS.values())[0:-4]
        self._verify_achievement(ACHIEVEMENTS[25].verification_fn, should_pass=True)

    def test_unstoppable_force(self):
        """
        Ensure that verification for the 'Unstoppable Force' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[26].verification_fn, should_pass=False)
        # Once the player has 20 deployed units, the achievement should be obtained.
        self.game_state.players[0].units = [self.TEST_UNIT] * 20
        self._verify_achievement(ACHIEVEMENTS[26].verification_fn, should_pass=True)

    def test_sprawling_skyscrapers(self):
        """
        Ensure that verification for the 'Sprawling Skyscrapers' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[28].verification_fn, should_pass=False)
        # If the player is of The Concentrated faction and has a settlement of level 10, the achievement should be
        # obtained.
        self.game_state.players[0].faction = Faction.CONCENTRATED
        self.TEST_SETTLEMENT.level = 10
        self._verify_achievement(ACHIEVEMENTS[28].verification_fn, should_pass=True)

    def test_ready_reservists(self):
        """
        Ensure that verification for the 'Ready Reservists' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[29].verification_fn, should_pass=False)
        # Once the player has 10 units in the garrison of their settlement, the achievement should be obtained.
        self.TEST_SETTLEMENT.garrison = [self.TEST_UNIT] * 10
        self._verify_achievement(ACHIEVEMENTS[29].verification_fn, should_pass=True)

    def test_the_big_wall(self):
        """
        Ensure that verification for the 'The Big Wall' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[30].verification_fn, should_pass=False)
        # Once the settlement has reached 300 strength, the achievement should be obtained.
        self.TEST_SETTLEMENT.strength = 300
        self._verify_achievement(ACHIEVEMENTS[30].verification_fn, should_pass=True)

    def test_utopia(self):
        """
        Ensure that verification for the 'Utopia' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[31].verification_fn, should_pass=False)
        # Once the settlement has reached 100 satisfaction, the achievement should be obtained.
        self.TEST_SETTLEMENT.satisfaction = 100
        self._verify_achievement(ACHIEVEMENTS[31].verification_fn, should_pass=True)

    def test_all_grown_up(self):
        """
        Ensure that verification for the 'All Grown Up' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[32].verification_fn, should_pass=False)
        # Once the settlement has reached level 10, the achievement should be obtained.
        self.TEST_SETTLEMENT.level = 10
        self._verify_achievement(ACHIEVEMENTS[32].verification_fn, should_pass=True)

    def test_terra_nullius(self):
        """
        Ensure that verification for the 'Terra Nullius' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[33].verification_fn, should_pass=False)
        # Once the player has 10 settlements, the achievement should be obtained.
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT] * 10
        self._verify_achievement(ACHIEVEMENTS[33].verification_fn, should_pass=True)

    def test_all_is_revealed(self):
        """
        Ensure that verification for the 'All Is Revealed' achievement functions as expected.
        """
        # To make things easier in terms of quad counting, we initialise a real Board for this test.
        self.game_state.board = Board(GameConfig(2, Faction.INFIDELS, True, True, True, MultiplayerStatus.DISABLED),
                                      Namer(), {})
        self._verify_achievement(ACHIEVEMENTS[34].verification_fn, should_pass=False)
        # If we give the player all of the quads on the board as seen, the achievement should be obtained.
        self.game_state.players[0].quads_seen = list(chain.from_iterable(self.game_state.board.quads))
        self._verify_achievement(ACHIEVEMENTS[34].verification_fn, should_pass=True)

    def test_players_choice(self):
        """
        Ensure that verification for the 'Player's Choice' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[35].verification_fn, should_pass=False)
        # Once the player has three imminent victories, the achievement should be obtained.
        self.game_state.players[0].imminent_victories = \
            {VictoryType.ELIMINATION, VictoryType.AFFLUENCE, VictoryType.VIGOUR}
        self._verify_achievement(ACHIEVEMENTS[35].verification_fn, should_pass=True)

    def test_free_for_all(self):
        """
        Ensure that verification for the 'Free For All' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[36].verification_fn, should_pass=False)
        # Since this is a post-victory achievement, all that needs to occur is that there are 14 players in the game.
        # Due to the fact that there are 2 by default, we can just multiply by 7.
        self.game_state.players = self.game_state.players * 7
        self._verify_achievement(ACHIEVEMENTS[36].verification_fn, should_pass=True)

    def test_sleepwalker(self):
        """
        Ensure that verification for the 'Sleepwalker' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[37].verification_fn, should_pass=False)
        self.game_state.nighttime_left = 1
        # The test player already has eight units for another achievement, so this will pass now that it is nighttime.
        self._verify_achievement(ACHIEVEMENTS[37].verification_fn, should_pass=True)

    def test_just_before_bed(self):
        """
        Ensure that verification for the 'Just Before Bed' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[38].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[38].verification_fn, should_pass=True,
                                 statistics=Statistics(playtime=3600))

    def test_all_nighter(self):
        """
        Ensure that verification for the 'All Nighter' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[39].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[39].verification_fn, should_pass=True,
                                 statistics=Statistics(playtime=3600 * 5))

    def test_keep_coming_back(self):
        """
        Ensure that verification for the 'Keep Coming Back' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[40].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[40].verification_fn, should_pass=True,
                                 statistics=Statistics(playtime=3600 * 20))

    def test_one_more_turn(self):
        """
        Ensure that verification for the 'One More Turn' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[41].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[41].verification_fn, should_pass=True,
                                 statistics=Statistics(turns_played=250))

    def test_what_time_is_it(self):
        """
        Ensure that verification for the 'What Time Is It?' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[42].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[42].verification_fn, should_pass=True,
                                 statistics=Statistics(turns_played=1000))

    def test_the_collector(self):
        """
        Ensure that verification for the 'The Collector' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[43].verification_fn, should_pass=False)
        # At least one victory of each type should result in the player obtaining the achievement.
        self._verify_achievement(ACHIEVEMENTS[43].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={
                                     VictoryType.ELIMINATION: 1,
                                     VictoryType.VIGOUR: 2,
                                     VictoryType.AFFLUENCE: 1,
                                     VictoryType.GLUTTONY: 1,
                                     VictoryType.JUBILATION: 1,
                                     VictoryType.SERENDIPITY: 1
                                 }))

    def test_globalist(self):
        """
        Ensure that verification for the 'Globalist' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[44].verification_fn, should_pass=False)
        # At least one usage of each faction should result in the player obtaining the achievement.
        self._verify_achievement(ACHIEVEMENTS[44].verification_fn, should_pass=True,
                                 statistics=Statistics(factions={
                                     Faction.INFIDELS: 1,
                                     Faction.CONCENTRATED: 2,
                                     Faction.GODLESS: 1,
                                     Faction.NOCTURNE: 1,
                                     Faction.CAPITALISTS: 1,
                                     Faction.AGRICULTURISTS: 1,
                                     Faction.EXPLORERS: 1,
                                     Faction.PERSISTENT: 1,
                                     Faction.IMPERIALS: 1,
                                     Faction.FRONTIERSMEN: 1,
                                     Faction.ORTHODOX: 1,
                                     Faction.FUNDAMENTALISTS: 1,
                                     Faction.RAVENOUS: 1,
                                     Faction.SCRUTINEERS: 1
                                 }))

    def test_midnight_feast(self):
        """
        Ensure that verification for the 'Midnight Feast' achievement functions as expected.
        """
        self._verify_achievement(ACHIEVEMENTS[45].verification_fn, should_pass=False)
        # Having a settlement with a plentiful harvest during nighttime should result in the player obtaining this
        # achievement.
        self.game_state.nighttime_left = 1
        self.TEST_SETTLEMENT.harvest_status = HarvestStatus.PLENTIFUL
        self._verify_achievement(ACHIEVEMENTS[45].verification_fn, should_pass=True)

    def test_on_the_brink(self):
        """
        Ensure that verification for the 'On The Brink' achievement functions as expected.
        """
        # We have to reposition the test settlement since it's actually on the edge by default.
        self.TEST_SETTLEMENT.location = 50, 50
        # A settlement in the middle of the board should not result in the player obtaining this achievement.
        self._verify_achievement(ACHIEVEMENTS[47].verification_fn, should_pass=False)
        # However, if we relocate it once more to its original position on the very top left corner, the achievement
        # should be obtained.
        self.TEST_SETTLEMENT.location = 0, 0
        self._verify_achievement(ACHIEVEMENTS[47].verification_fn, should_pass=True)

    def test_speed_run(self):
        """
        Ensure that verification for the 'Speed Run' achievement functions as expected.
        """
        # We have to set the turn to 100 to begin with since it starts at 1.
        self.game_state.turn = 100
        self._verify_achievement(ACHIEVEMENTS[48].verification_fn, should_pass=False)
        # As a post-victory achievement, all that needs to occur is that the turn be less than 25, and there be two
        # players in the game (which there already are for this test class).
        self.game_state.turn = 5
        self._verify_achievement(ACHIEVEMENTS[48].verification_fn, should_pass=True)

    def test_mighty_miner(self):
        """
        Ensure that verification for the 'Mighty Miner' achievement functions as expected.
        """
        # Players start with zero of each resource, so this should fail.
        self._verify_achievement(ACHIEVEMENTS[49].verification_fn, should_pass=False)
        # However, now with 100 ore, we expect the achievement to be obtained.
        self.game_state.players[0].resources = ResourceCollection(ore=100)
        self._verify_achievement(ACHIEVEMENTS[49].verification_fn, should_pass=True)

    def test_lofty_lumberjack(self):
        """
        Ensure that verification for the 'Lofty Lumberjack' achievement functions as expected.
        """
        # Players start with zero of each resource, so this should fail.
        self._verify_achievement(ACHIEVEMENTS[50].verification_fn, should_pass=False)
        # However, now with 100 timber, we expect the achievement to be obtained.
        self.game_state.players[0].resources = ResourceCollection(timber=100)
        self._verify_achievement(ACHIEVEMENTS[50].verification_fn, should_pass=True)

    def test_molten_multitude(self):
        """
        Ensure that verification for the 'Molten Multitude' achievement functions as expected.
        """
        # Players start with zero of each resource, so this should fail.
        self._verify_achievement(ACHIEVEMENTS[51].verification_fn, should_pass=False)
        # However, now with 100 magma, we expect the achievement to be obtained.
        self.game_state.players[0].resources = ResourceCollection(magma=100)
        self._verify_achievement(ACHIEVEMENTS[51].verification_fn, should_pass=True)

    def test_the_third_x(self):
        """
        Ensure that verification for the 'The Third X' achievement functions as expected.
        """
        # The test settlement has no resources to begin with, so this should fail.
        self._verify_achievement(verify_the_third_x, should_pass=False)
        # However, if we give the test settlement one of each resource, that should more than qualify for this
        # achievement.
        self.TEST_SETTLEMENT.resources = \
            ResourceCollection(ore=1, timber=1, magma=1, aurora=1, bloodstone=1, obsidian=1, sunstone=1, aquamarine=1)
        self._verify_achievement(verify_the_third_x, should_pass=True)

    def test_luxuries_abound(self):
        """
        Ensure that verification for the 'Luxuries Abound' achievement functions as expected.
        """
        # Players start with zero of each resource, so this should fail.
        self._verify_achievement(ACHIEVEMENTS[53].verification_fn, should_pass=False)
        # However, now with 1 of each rare resource, we expect the achievement to be obtained.
        self.game_state.players[0].resources = \
            ResourceCollection(aurora=1, bloodstone=1, obsidian=1, sunstone=1, aquamarine=1)
        self._verify_achievement(ACHIEVEMENTS[53].verification_fn, should_pass=True)

    def test_going_online(self):
        """
        Ensure that verification for the 'Going Online' achievement functions as expected.
        """
        # We need to use a real board for this test, since we'll be reading the game config from it.
        self.game_state.board = Board(GameConfig(2, Faction.INFIDELS, True, True, True, MultiplayerStatus.DISABLED),
                                      Namer(), {})
        # The above config does not have multiplayer enabled, so this should fail.
        self._verify_achievement(ACHIEVEMENTS[54].verification_fn, should_pass=False)
        # However, now with multiplayer enabled, we expect the achievement to be obtained.
        self.game_state.board.game_config.multiplayer = MultiplayerStatus.GLOBAL
        self._verify_achievement(ACHIEVEMENTS[54].verification_fn, should_pass=True)

    def test_big_game_hunter(self):
        """
        Ensure that verification for the 'Big Game Hunter' achievement functions as expected.
        """
        # We need to use a real board for this test, since we'll be reading the game config from it.
        self.game_state.board = Board(GameConfig(2, Faction.INFIDELS, True, True, True, MultiplayerStatus.DISABLED),
                                      Namer(), {})
        # The above config does not have multiplayer enabled, so this should fail.
        self._verify_achievement(ACHIEVEMENTS[55].verification_fn, should_pass=False)
        # Since this is a post-victory achievement, all that needs to occur is that there are 14 players in the
        # multiplayer game. Due to the fact that there are 2 by default, we can just multiply by 7 and enable
        # multiplayer.
        self.game_state.players = self.game_state.players * 7
        self.game_state.board.game_config.multiplayer = MultiplayerStatus.GLOBAL
        # With these changes, we expect the achievement to be obtained.
        self._verify_achievement(ACHIEVEMENTS[55].verification_fn, should_pass=True)

    def test_focus_victim(self):
        """
        Ensure that verification for the 'Focus Victim' achievement functions as expected.
        """
        # We need to use a real board for this test, since we'll be reading the game config from it.
        self.game_state.board = Board(GameConfig(2, Faction.INFIDELS, True, True, True, MultiplayerStatus.DISABLED),
                                      Namer(), {})
        # The above config does not have multiplayer enabled, so this should fail.
        self._verify_achievement(ACHIEVEMENTS[56].verification_fn, should_pass=False)
        # A number of things need to occur for this achievement to be obtained. Firstly, multiplayer must be enabled. In
        # addition to this, the game must have over 2 players, with the only eliminated player being the human player on
        # this machine.
        self.game_state.board.game_config.multiplayer = MultiplayerStatus.GLOBAL
        self.game_state.players.append(Player("Farmer", Faction.AGRICULTURISTS, 0,
                                       ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL),
                                       settlements=[self.TEST_SETTLEMENT_3]))
        self.game_state.players[self.game_state.player_idx].eliminated = True
        # With these changes, we expect the achievement to be obtained.
        self._verify_achievement(ACHIEVEMENTS[56].verification_fn, should_pass=True)

    def test_greetings_fellow_robots(self):
        """
        Ensure that verification for the 'Greetings Fellow Robots' achievement functions as expected.
        """
        # We need to use a real board for this test, since we'll be reading the game config from it.
        self.game_state.board = Board(GameConfig(2, Faction.INFIDELS, True, True, True, MultiplayerStatus.DISABLED),
                                      Namer(), {})
        # The above config does not have multiplayer enabled, so this should fail.
        self._verify_achievement(ACHIEVEMENTS[57].verification_fn, should_pass=False)
        # However, now with multiplayer enabled, we expect the achievement to be obtained, since the default test state
        # has one human and one AI player.
        self.game_state.board.game_config.multiplayer = MultiplayerStatus.GLOBAL
        self._verify_achievement(ACHIEVEMENTS[57].verification_fn, should_pass=True)

    def test_50_hours_later(self):
        """
        Ensure that verification for the '50 Hours Later' achievement functions as expected.
        """
        # We need to use a real board for this test, since we'll be reading the game config from it.
        self.game_state.board = Board(GameConfig(2, Faction.INFIDELS, True, True, True, MultiplayerStatus.DISABLED),
                                      Namer(), {})
        # The above config does not have multiplayer enabled, so this should fail.
        self._verify_achievement(ACHIEVEMENTS[58].verification_fn, should_pass=False)
        # However, now with multiplayer enabled and the game at a later turn, we expect the achievement to be obtained.
        self.game_state.board.game_config.multiplayer = MultiplayerStatus.GLOBAL
        self.game_state.turn = 200
        self._verify_achievement(ACHIEVEMENTS[58].verification_fn, should_pass=True)

    def _verify_victory_type_achievement(self, ach_idx: int, victory_type: VictoryType):
        """
        Verify that the achievement at the supplied index is only achieved once the supplied victory type is included in
        the statistics.
        :param ach_idx: The index of the achievement in the ACHIEVEMENTS list.
        :param victory_type: The type of victory to include in the player statistics.
        """
        self._verify_achievement(ACHIEVEMENTS[ach_idx].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[ach_idx].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={victory_type: 1}))

    def _verify_faction_victory_achievement(self, ach_idx: int, faction: Faction):
        """
        Verify that the achievement at the supplied index is only achieved when the player is of the supplied faction.
        :param ach_idx: The index of the achievement in the ACHIEVEMENTS list.
        :param faction: The faction to assign to the player.
        """
        self._verify_achievement(ACHIEVEMENTS[ach_idx].verification_fn, should_pass=False)
        # Since all faction victory achievements are post-victory, all that is required is that the player be of a
        # certain faction when the victory occurs.
        self.game_state.players[0].faction = faction
        self._verify_achievement(ACHIEVEMENTS[ach_idx].verification_fn, should_pass=True)

    def _verify_achievement(self, verification_fn: typing.Callable[[GameState, Statistics], bool],
                            should_pass: bool, statistics: Statistics = Statistics()):
        """
        Verify that the expected outcome dictated by the should_pass parameter occurs when running the supplied
        verification function with the supplied statistics.
        :param verification_fn: The verification function to call with the test class' game state and the given
        statistics.
        :param should_pass: Whether the verification function should return True.
        :param statistics: The Statistics object to pass to the verification function.
        """
        self.assertEqual(should_pass, verification_fn(self.game_state, statistics))


if __name__ == '__main__':
    unittest.main()
