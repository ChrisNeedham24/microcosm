import typing
import unittest
from itertools import chain

from source.display.board import Board
from source.foundation.achievements import verify_full_house, verify_its_worth_it
from source.foundation.catalogue import ACHIEVEMENTS, IMPROVEMENTS, BLESSINGS, Namer
from source.foundation.models import Player, Faction, Settlement, AIPlaystyle, AttackPlaystyle, ExpansionPlaystyle, \
    Statistics, UnitPlan, Unit, Quad, Biome, Improvement, ImprovementType, Effect, VictoryType, HarvestStatus, \
    EconomicStatus, GameConfig
from source.game_management.game_state import GameState


class AchievementsTest(unittest.TestCase):
    def setUp(self) -> None:
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
        self.TEST_SETTLEMENT = Settlement("Numero Uno", (0, 0), [], [self.TEST_QUAD], [])
        self.TEST_SETTLEMENT_2 = Settlement("Numero Dos", (2, 2), [], [Quad(Biome.SEA, 0, 0, 0, 0, (2, 2))], [])
        self.TEST_SETTLEMENT_3 = Settlement("Numero Tres", (4, 4), [], [], [])
        self.TEST_SETTLEMENT_4 = Settlement("Numero Quattro", (6, 6), [], [], [])
        self.TEST_SETTLEMENT_5 = Settlement("Numero Cinco", (8, 8), [], [], [])
        self.TEST_SETTLEMENT_6 = Settlement("Numero Seis", (10, 10), [], [], [])

        self.game_state = GameState()
        self.game_state.players = [
            Player("Infidel", Faction.INFIDELS, 0, settlements=[self.TEST_SETTLEMENT],
                   units=[self.TEST_UNIT, self.TEST_UNIT_2, self.TEST_UNIT_3, self.TEST_UNIT_4, self.TEST_UNIT_5,
                          self.TEST_UNIT_6, self.TEST_UNIT_7, self.TEST_UNIT_8]),
            Player("Concentrator", Faction.CONCENTRATED, 0,
                   ai_playstyle=AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL),
                   settlements=[self.TEST_SETTLEMENT_2]),
        ]

    def test_full_house(self):
        for u in self.game_state.players[0].units:
            u.besieging = True
        self.TEST_UNIT.location = (self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1] - 1)
        self.TEST_UNIT_2.location = (self.TEST_SETTLEMENT_2.location[0], self.TEST_SETTLEMENT_2.location[1] - 1)
        self.TEST_UNIT_3.location = (self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1] - 1)
        self.TEST_UNIT_4.location = (self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1])
        self.TEST_UNIT_5.location = (self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1])
        self.TEST_UNIT_6.location = (self.TEST_SETTLEMENT_2.location[0] - 1, self.TEST_SETTLEMENT_2.location[1] + 1)
        self.TEST_UNIT_7.location = (self.TEST_SETTLEMENT_2.location[0], self.TEST_SETTLEMENT_2.location[1] + 1)

        self._verify_achievement(verify_full_house, should_pass=False)

        self.TEST_UNIT_8.location = (self.TEST_SETTLEMENT_2.location[0] + 1, self.TEST_SETTLEMENT_2.location[1] + 1)

        self._verify_achievement(verify_full_house, should_pass=True)

    def test_its_worth_it(self):
        self.TEST_SETTLEMENT.improvements = [Improvement(ImprovementType.MAGICAL, 0, "TestImp", "", Effect(), None)]
        self._verify_achievement(verify_its_worth_it, should_pass=False)
        self.TEST_SETTLEMENT.improvements = \
            [Improvement(ImprovementType.MAGICAL, 0, "TestImp", "", Effect(satisfaction=-1), None)]
        self._verify_achievement(verify_its_worth_it, should_pass=True)

    def test_chicken_dinner(self):
        self._verify_victory_type_achievement(ach_idx=0, victory_type=VictoryType.ELIMINATION)

    def test_fully_improved(self):
        self._verify_achievement(ACHIEVEMENTS[1].verification_fn, should_pass=False)
        self.TEST_SETTLEMENT.improvements = IMPROVEMENTS[0:-1]
        self._verify_achievement(ACHIEVEMENTS[1].verification_fn, should_pass=True)

    def test_harvest_galore(self):
        self._verify_achievement(ACHIEVEMENTS[2].verification_fn, should_pass=False)
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_3, self.TEST_SETTLEMENT_4,
                                                  self.TEST_SETTLEMENT_5, self.TEST_SETTLEMENT_6]
        for s in self.game_state.players[0].settlements:
            s.harvest_status = HarvestStatus.PLENTIFUL
        self._verify_achievement(ACHIEVEMENTS[2].verification_fn, should_pass=True)

    def test_mansa_musa(self):
        self._verify_achievement(ACHIEVEMENTS[3].verification_fn, should_pass=False)
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT, self.TEST_SETTLEMENT_3, self.TEST_SETTLEMENT_4,
                                                  self.TEST_SETTLEMENT_5, self.TEST_SETTLEMENT_6]
        for s in self.game_state.players[0].settlements:
            s.economic_status = EconomicStatus.BOOM
        self._verify_achievement(ACHIEVEMENTS[3].verification_fn, should_pass=True)

    def test_last_one_standing(self):
        self._verify_victory_type_achievement(ach_idx=4, victory_type=VictoryType.ELIMINATION)

    def test_they_love_me(self):
        self._verify_victory_type_achievement(ach_idx=5, victory_type=VictoryType.JUBILATION)

    def test_megalopoleis(self):
        self._verify_victory_type_achievement(ach_idx=6, victory_type=VictoryType.GLUTTONY)

    def test_wealth_upon_wealth(self):
        self._verify_victory_type_achievement(ach_idx=7, victory_type=VictoryType.AFFLUENCE)

    def test_sanctum_sanctorum(self):
        self._verify_victory_type_achievement(ach_idx=8, victory_type=VictoryType.VIGOUR)

    def test_arduously_blessed(self):
        self._verify_victory_type_achievement(ach_idx=9, victory_type=VictoryType.SERENDIPITY)

    def test_grow_and_grow(self):
        self._verify_faction_victory_achievement(ach_idx=10, faction=Faction.AGRICULTURISTS)

    def test_money_talks(self):
        self._verify_faction_victory_achievement(ach_idx=11, faction=Faction.CAPITALISTS)

    def test_telescopic(self):
        self._verify_faction_victory_achievement(ach_idx=12, faction=Faction.SCRUTINEERS)

    def test_suitably_skeptical(self):
        self._verify_faction_victory_achievement(ach_idx=13, faction=Faction.GODLESS)

    def test_gallivanting_greed(self):
        self._verify_faction_victory_achievement(ach_idx=14, faction=Faction.RAVENOUS)

    def test_the_clang_of_iron(self):
        self._verify_faction_victory_achievement(ach_idx=15, faction=Faction.FUNDAMENTALISTS)

    def test_the_passionate_eye(self):
        self._verify_faction_victory_achievement(ach_idx=16, faction=Faction.ORTHODOX)

    def test_cloudscrapers(self):
        self._verify_faction_victory_achievement(ach_idx=17, faction=Faction.CONCENTRATED)

    def test_never_rest(self):
        self._verify_faction_victory_achievement(ach_idx=18, faction=Faction.FRONTIERSMEN)

    def test_empirical_evidence(self):
        self._verify_faction_victory_achievement(ach_idx=19, faction=Faction.IMPERIALS)

    def test_the_singular_purpose(self):
        self._verify_faction_victory_achievement(ach_idx=20, faction=Faction.PERSISTENT)

    def test_cartographic_courage(self):
        self._verify_faction_victory_achievement(ach_idx=21, faction=Faction.EXPLORERS)

    def test_sub_human_super_success(self):
        self.game_state.players[0].faction = Faction.AGRICULTURISTS
        self._verify_faction_victory_achievement(ach_idx=22, faction=Faction.INFIDELS)

    def test_shine_in_the_dark(self):
        self._verify_faction_victory_achievement(ach_idx=23, faction=Faction.NOCTURNE)

    def test_the_golden_quad(self):
        self._verify_achievement(ACHIEVEMENTS[24].verification_fn, should_pass=False)
        self.TEST_SETTLEMENT.quads = [Quad(Biome.SEA, wealth=5, harvest=5, zeal=5, fortune=5, location=(0, 0))]
        self._verify_achievement(ACHIEVEMENTS[24].verification_fn, should_pass=True)

    def test_wholly_blessed(self):
        self._verify_achievement(ACHIEVEMENTS[25].verification_fn, should_pass=False)
        self.game_state.players[0].blessings = list(BLESSINGS.values())[0:-4]
        self._verify_achievement(ACHIEVEMENTS[25].verification_fn, should_pass=True)

    def test_unstoppable_force(self):
        self._verify_achievement(ACHIEVEMENTS[26].verification_fn, should_pass=False)
        self.game_state.players[0].units = [self.TEST_UNIT] * 20
        self._verify_achievement(ACHIEVEMENTS[26].verification_fn, should_pass=True)

    def test_sprawling_skyscrapers(self):
        self._verify_achievement(ACHIEVEMENTS[28].verification_fn, should_pass=False)
        self.game_state.players[0].faction = Faction.CONCENTRATED
        self.TEST_SETTLEMENT.level = 10
        self._verify_achievement(ACHIEVEMENTS[28].verification_fn, should_pass=True)

    def test_ready_reservists(self):
        self._verify_achievement(ACHIEVEMENTS[29].verification_fn, should_pass=False)
        self.TEST_SETTLEMENT.garrison = [self.TEST_UNIT] * 10
        self._verify_achievement(ACHIEVEMENTS[29].verification_fn, should_pass=True)

    def test_the_big_wall(self):
        self._verify_achievement(ACHIEVEMENTS[30].verification_fn, should_pass=False)
        self.TEST_SETTLEMENT.strength = 300
        self._verify_achievement(ACHIEVEMENTS[30].verification_fn, should_pass=True)

    def test_utopia(self):
        self._verify_achievement(ACHIEVEMENTS[31].verification_fn, should_pass=False)
        self.TEST_SETTLEMENT.satisfaction = 100
        self._verify_achievement(ACHIEVEMENTS[31].verification_fn, should_pass=True)

    def test_all_grown_up(self):
        self._verify_achievement(ACHIEVEMENTS[32].verification_fn, should_pass=False)
        self.TEST_SETTLEMENT.level = 10
        self._verify_achievement(ACHIEVEMENTS[32].verification_fn, should_pass=True)

    def test_terra_nullius(self):
        self._verify_achievement(ACHIEVEMENTS[33].verification_fn, should_pass=False)
        self.game_state.players[0].settlements = [self.TEST_SETTLEMENT] * 10
        self._verify_achievement(ACHIEVEMENTS[33].verification_fn, should_pass=True)

    def test_all_is_revealed(self):
        self.game_state.board = Board(GameConfig(2, Faction.INFIDELS, True, True, True), Namer())
        self._verify_achievement(ACHIEVEMENTS[34].verification_fn, should_pass=False)
        self.game_state.players[0].quads_seen = list(chain.from_iterable(self.game_state.board.quads))
        self._verify_achievement(ACHIEVEMENTS[34].verification_fn, should_pass=True)

    def test_players_choice(self):
        self._verify_achievement(ACHIEVEMENTS[35].verification_fn, should_pass=False)
        self.game_state.players[0].imminent_victories = \
            {VictoryType.ELIMINATION, VictoryType.AFFLUENCE, VictoryType.VIGOUR}
        self._verify_achievement(ACHIEVEMENTS[35].verification_fn, should_pass=True)

    def test_free_for_all(self):
        self._verify_achievement(ACHIEVEMENTS[36].verification_fn, should_pass=False)
        self.game_state.players = self.game_state.players * 7
        self._verify_achievement(ACHIEVEMENTS[36].verification_fn, should_pass=True)

    def test_sleepwalker(self):
        self._verify_achievement(ACHIEVEMENTS[37].verification_fn, should_pass=False)
        self.game_state.nighttime_left = 1
        # The test player already has eight units for another achievement, so this will pass now that it is nighttime.
        self._verify_achievement(ACHIEVEMENTS[37].verification_fn, should_pass=True)

    def test_just_before_bed(self):
        self._verify_achievement(ACHIEVEMENTS[38].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[38].verification_fn, should_pass=True,
                                 statistics=Statistics(playtime=3600))

    def test_all_nighter(self):
        self._verify_achievement(ACHIEVEMENTS[39].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[39].verification_fn, should_pass=True,
                                 statistics=Statistics(playtime=3600 * 5))

    def test_keep_coming_back(self):
        self._verify_achievement(ACHIEVEMENTS[40].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[40].verification_fn, should_pass=True,
                                 statistics=Statistics(playtime=3600 * 20))

    def test_one_more_turn(self):
        self._verify_achievement(ACHIEVEMENTS[41].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[41].verification_fn, should_pass=True,
                                 statistics=Statistics(turns_played=250))

    def test_what_time_is_it(self):
        self._verify_achievement(ACHIEVEMENTS[42].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[42].verification_fn, should_pass=True,
                                 statistics=Statistics(turns_played=1000))

    def test_the_collector(self):
        self._verify_achievement(ACHIEVEMENTS[43].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[43].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={
                                     VictoryType.ELIMINATION: 1,
                                     VictoryType.VIGOUR: 1,
                                     VictoryType.AFFLUENCE: 1,
                                     VictoryType.GLUTTONY: 1,
                                     VictoryType.JUBILATION: 1,
                                     VictoryType.SERENDIPITY: 1
                                 }))

    def test_globalist(self):
        self._verify_achievement(ACHIEVEMENTS[44].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[44].verification_fn, should_pass=True,
                                 statistics=Statistics(factions={
                                     Faction.INFIDELS: 1,
                                     Faction.CONCENTRATED: 1,
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
        self._verify_achievement(ACHIEVEMENTS[45].verification_fn, should_pass=False)
        self.game_state.nighttime_left = 1
        self.TEST_SETTLEMENT.harvest_status = HarvestStatus.PLENTIFUL
        self._verify_achievement(ACHIEVEMENTS[45].verification_fn, should_pass=True)

    def test_on_the_brink(self):
        self.TEST_SETTLEMENT.location = 50, 50
        self._verify_achievement(ACHIEVEMENTS[47].verification_fn, should_pass=False)
        self.TEST_SETTLEMENT.location = 0, 0
        self._verify_achievement(ACHIEVEMENTS[47].verification_fn, should_pass=True)

    def test_speed_run(self):
        self.game_state.turn = 100
        self._verify_achievement(ACHIEVEMENTS[48].verification_fn, should_pass=False)
        self.game_state.turn = 5
        # There are already only two players for this test class, so no need to change that.
        self._verify_achievement(ACHIEVEMENTS[48].verification_fn, should_pass=True)

    def _verify_victory_type_achievement(self, ach_idx: int, victory_type: VictoryType):
        self._verify_achievement(ACHIEVEMENTS[ach_idx].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[ach_idx].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={victory_type: 1}))

    def _verify_faction_victory_achievement(self, ach_idx: int, faction: Faction):
        self._verify_achievement(ACHIEVEMENTS[ach_idx].verification_fn, should_pass=False)
        self.game_state.players[0].faction = faction
        self._verify_achievement(ACHIEVEMENTS[ach_idx].verification_fn, should_pass=True)

    def _verify_achievement(self, verification_fn: typing.Callable[[GameState, Statistics], bool],
                            should_pass: bool, statistics: Statistics = Statistics()):
        if should_pass:
            self.assertTrue(verification_fn(self.game_state, statistics))
        else:
            self.assertFalse(verification_fn(self.game_state, statistics))


if __name__ == '__main__':
    unittest.main()
