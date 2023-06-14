import typing
import unittest

from source.foundation.achievements import verify_full_house, verify_its_worth_it
from source.foundation.catalogue import ACHIEVEMENTS, IMPROVEMENTS
from source.foundation.models import Player, Faction, Settlement, AIPlaystyle, AttackPlaystyle, ExpansionPlaystyle, \
    Statistics, UnitPlan, Unit, Quad, Biome, Improvement, ImprovementType, Effect, VictoryType, HarvestStatus, \
    EconomicStatus
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
        self.TEST_SETTLEMENT = Settlement("Numero Uno", (0, 0), [], [], [])
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
        self._verify_achievement(ACHIEVEMENTS[0].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[0].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={VictoryType.ELIMINATION: 1}))

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
        self._verify_achievement(ACHIEVEMENTS[4].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[4].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={VictoryType.ELIMINATION: 1}))

    def test_they_love_me(self):
        self._verify_achievement(ACHIEVEMENTS[5].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[5].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={VictoryType.JUBILATION: 1}))

    def test_megalopoleis(self):
        self._verify_achievement(ACHIEVEMENTS[6].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[6].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={VictoryType.GLUTTONY: 1}))

    def test_wealth_upon_wealth(self):
        self._verify_achievement(ACHIEVEMENTS[7].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[7].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={VictoryType.AFFLUENCE: 1}))

    def test_sanctum_sanctorum(self):
        self._verify_achievement(ACHIEVEMENTS[8].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[8].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={VictoryType.VIGOUR: 1}))

    def test_arduously_blessed(self):
        self._verify_achievement(ACHIEVEMENTS[9].verification_fn, should_pass=False)
        self._verify_achievement(ACHIEVEMENTS[9].verification_fn, should_pass=True,
                                 statistics=Statistics(victories={VictoryType.SERENDIPITY: 1}))

    def _verify_achievement(self, verification_fn: typing.Callable[[GameState, Statistics], bool],
                            should_pass: bool, statistics: Statistics = Statistics()):
        if should_pass:
            self.assertTrue(verification_fn(self.game_state, statistics))
        else:
            self.assertFalse(verification_fn(self.game_state, statistics))


if __name__ == '__main__':
    unittest.main()
