import unittest
from unittest.mock import patch, MagicMock

from source.foundation.catalogue import UNIT_PLANS, BLESSINGS
from source.foundation.models import Biome, Unit, AttackData, HealData, Settlement, SetlAttackData, Player, Faction, \
    Construction, Improvement, ImprovementType, Effect, UnitPlan, GameConfig, InvestigationResult, OngoingBlessing
from source.util.calculator import calculate_yield_for_quad, clamp, attack, heal, attack_setl, complete_construction, \
    investigate_relic


class CalculatorTest(unittest.TestCase):
    """
    The test class for calculator.py.
    """
    ORIGINAL_WEALTH = 99
    ORIGINAL_HEALTH = 1
    ORIGINAL_STAMINA = 2
    ORIGINAL_PLAN_HEALTH = UNIT_PLANS[0].max_health
    ORIGINAL_PLAN_POWER = UNIT_PLANS[0].power
    ORIGINAL_PLAN_STAMINA = UNIT_PLANS[0].total_stamina
    ORIGINAL_PLAN_COST = UNIT_PLANS[0].cost
    TEST_PLAYER = Player("TestMan", Faction.NOCTURNE, ORIGINAL_WEALTH, 0, [], [], [], set(), set())
    TEST_UNIT = Unit(ORIGINAL_HEALTH, ORIGINAL_STAMINA, (3, 4), False, UNIT_PLANS[0])
    TEST_CONFIG = GameConfig(2, TEST_PLAYER.faction, True, True, True)

    def setUp(self) -> None:
        """
        Reset our test models.
        """
        self.TEST_PLAYER.ongoing_blessing = None
        self.TEST_PLAYER.wealth = self.ORIGINAL_WEALTH
        self.TEST_PLAYER.quads_seen = set()
        self.TEST_UNIT.health = self.ORIGINAL_HEALTH
        self.TEST_UNIT.remaining_stamina = self.ORIGINAL_STAMINA
        self.TEST_UNIT.plan.max_health = self.ORIGINAL_PLAN_HEALTH
        self.TEST_UNIT.plan.power = self.ORIGINAL_PLAN_POWER
        self.TEST_UNIT.plan.total_stamina = self.ORIGINAL_PLAN_STAMINA
        self.TEST_UNIT.plan.cost = self.ORIGINAL_PLAN_COST

    def test_yield_for_quad(self):
        """
        Ensure that the quad yields for each biome do not exceed their pre-defined limits.
        """
        forest_yield = calculate_yield_for_quad(Biome.FOREST)
        self.assertTrue(0 <= forest_yield[0] <= 2)
        self.assertTrue(5 <= forest_yield[1] <= 9)
        self.assertTrue(1 <= forest_yield[2] <= 4)
        self.assertTrue(3 <= forest_yield[3] <= 6)

        sea_yield = calculate_yield_for_quad(Biome.SEA)
        self.assertTrue(1 <= sea_yield[0] <= 4)
        self.assertTrue(3 <= sea_yield[1] <= 6)
        self.assertTrue(0 <= sea_yield[2] <= 1)
        self.assertTrue(5 <= sea_yield[3] <= 9)

        desert_yield = calculate_yield_for_quad(Biome.DESERT)
        self.assertTrue(5 <= desert_yield[0] <= 9)
        self.assertTrue(0 <= desert_yield[1] <= 1)
        self.assertTrue(3 <= desert_yield[2] <= 6)
        self.assertTrue(1 <= desert_yield[3] <= 4)

        mountain_yield = calculate_yield_for_quad(Biome.MOUNTAIN)
        self.assertTrue(3 <= mountain_yield[0] <= 6)
        self.assertTrue(1 <= mountain_yield[1] <= 4)
        self.assertTrue(5 <= mountain_yield[2] <= 9)
        self.assertTrue(0 <= mountain_yield[3] <= 2)

    def test_clamp(self):
        """
        Ensure that the clamp utility function operates as expected.
        """
        test_min = 5
        test_max = 10

        self.assertEqual(test_min, clamp(test_min - 1, test_min, test_max))
        self.assertEqual(test_min, clamp(test_min, test_min, test_max))
        self.assertEqual((test_min + test_max) // 2, clamp((test_min + test_max) // 2, test_min, test_max))
        self.assertEqual(test_max, clamp(test_max, test_min, test_max))
        self.assertEqual(test_max, clamp(test_max + 1, test_min, test_max))

    def test_attack(self):
        """
        Ensure that attack calculations occur correctly and return the appropriate data.
        """
        attacker_health = 200
        defender_health = 5
        attacker = Unit(attacker_health, 10, (0, 0), False, UNIT_PLANS[-1])
        att_power = attacker.plan.power
        defender = Unit(defender_health, 0, (1, 0), False, UNIT_PLANS[0])
        def_power = defender.plan.power
        ai_attack = False

        attack_data: AttackData = attack(attacker, defender, ai_attack)
        self.assertEqual(attacker, attack_data.attacker)
        self.assertEqual(defender, attack_data.defender)
        self.assertEqual(def_power * 0.25, attack_data.damage_to_attacker)
        self.assertEqual(att_power * 0.25 * 1.2, attack_data.damage_to_defender)
        self.assertEqual(defender_health - att_power * 0.25 * 1.2, defender.health)
        self.assertEqual(attacker_health - def_power * 0.25, attacker.health)
        self.assertEqual(not ai_attack, attack_data.player_attack)
        self.assertFalse(attack_data.attacker_was_killed)
        self.assertTrue(attack_data.defender_was_killed)
        self.assertTrue(attacker.has_acted)

    def test_heal(self):
        """
        Ensure that heal calculations occur correctly and return the appropriate data.
        """
        healed_health = 60
        healer = Unit(50, 2, (0, 0), False, UNIT_PLANS[-4])
        healed = Unit(healed_health, 0, (1, 0), False, UNIT_PLANS[0])
        ai_heal = False

        heal_data: HealData = heal(healer, healed, ai_heal)
        # We expect the healed unit to return to their max health, but not exceed it.
        self.assertEqual(healed.plan.max_health, healed.health)
        self.assertTrue(healer.has_acted)
        self.assertEqual(healer, heal_data.healer)
        self.assertEqual(healed, heal_data.healed)
        self.assertEqual(healer.plan.power, heal_data.heal_amount)
        self.assertEqual(healed_health, heal_data.original_health)
        self.assertEqual(not ai_heal, heal_data.player_heal)

    def test_attack_setl(self):
        """
        Ensure that settlement attack calculations occur correctly and return the appropriate data.
        """
        attacker_health = 50
        settlement_strength = 20
        attacker = Unit(attacker_health, 1, (0, 0), False, UNIT_PLANS[-2])
        setl = Settlement("Test", (1, 0), [], [], [], strength=settlement_strength)
        player = Player("Tester", Faction.NOCTURNE, 0, 0, [setl], [], [], set(), set())
        ai_attack = False

        setl_attack_data: SetlAttackData = attack_setl(attacker, setl, player, ai_attack)
        self.assertEqual(attacker_health - settlement_strength / 2, attacker.health)
        # Make sure the settlement's strength does fall below zero, even though the attacker's damage exceeds the
        # remaining strength of the settlement.
        self.assertEqual(0, setl.strength)
        self.assertTrue(attacker.has_acted)
        self.assertEqual(attacker, setl_attack_data.attacker)
        self.assertEqual(setl, setl_attack_data.settlement)
        self.assertEqual(player, setl_attack_data.setl_owner)
        self.assertEqual(settlement_strength / 2, setl_attack_data.damage_to_attacker)
        self.assertEqual(attacker.plan.power * 0.1, setl_attack_data.damage_to_setl)
        self.assertEqual(not ai_attack, setl_attack_data.player_attack)
        self.assertFalse(setl_attack_data.attacker_was_killed)
        self.assertTrue(setl_attack_data.setl_was_taken)

    def test_complete_construction(self):
        """
        Ensure that when completing a construction that yields added strength and satisfaction, the related settlement
        is correctly updated.
        """
        added_strength = 5
        test_improvement = Improvement(ImprovementType.ECONOMICAL, 1, "Money", "Time",
                                       Effect(wealth=1, strength=added_strength, satisfaction=5), None)
        # Note that we set the settlement's satisfaction to 99.
        test_setl = Settlement("Working", (50, 50), [], [], [],
                               current_work=Construction(test_improvement), satisfaction=99)
        test_player = Player("Tester", Faction.NOCTURNE, 0, 0, [test_setl], [], [], set(), set())

        complete_construction(test_setl, test_player)
        self.assertIn(test_improvement, test_setl.improvements)
        # The settlement should have increased strength.
        self.assertEqual(100 + added_strength, test_setl.strength)
        self.assertEqual(100 + added_strength, test_setl.max_strength)
        # However, the settlement's satisfaction should not have the effect fully added to it, as it would exceed 100,
        # which is the maximum.
        self.assertEqual(100, test_setl.satisfaction)
        self.assertIsNone(test_setl.current_work)

    def test_complete_construction_concentrated_negative_satisfaction(self):
        """
        Ensure that when completing a construction that yields added strength and reduced satisfaction, the related
        settlement is correctly updated.
        """
        added_strength = 5
        test_improvement = Improvement(ImprovementType.ECONOMICAL, 1, "Money", "Time",
                                       Effect(wealth=1, strength=added_strength, satisfaction=-5), None)
        # Note that we set the settlement's satisfaction to 1.
        test_setl = Settlement("Working", (50, 50), [], [], [],
                               current_work=Construction(test_improvement), satisfaction=1)
        test_player = Player("Tester", Faction.CONCENTRATED, 0, 0, [test_setl], [], [], set(), set())

        complete_construction(test_setl, test_player)
        self.assertIn(test_improvement, test_setl.improvements)
        # Since the player is of The Concentrated faction, the strength added should be doubled.
        self.assertEqual(100 + 2 * added_strength, test_setl.strength)
        self.assertEqual(100 + 2 * added_strength, test_setl.max_strength)
        # Even though the settlement's satisfaction when combined with the construction's effect is below zero, zero is
        # the minimum, so we expect the satisfaction to be set to that.
        self.assertEqual(0, test_setl.satisfaction)
        self.assertIsNone(test_setl.current_work)

    def test_complete_construction_unit(self):
        """
        Ensure that when completing a construction that yields a unit, the related settlement is correctly updated.
        """
        initial_level = 5
        initial_harvest_reserves = 400
        test_unit_plan = UnitPlan(20, 20, 10, "Settler", None, 1, can_settle=True)
        test_setl = Settlement("Working", (50, 50), [], [], [], current_work=Construction(test_unit_plan),
                               level=initial_level, harvest_reserves=initial_harvest_reserves)
        test_player = Player("Tester", Faction.FRONTIERSMEN, 0, 0, [test_setl], [], [], set(), set())

        complete_construction(test_setl, test_player)
        # Because the unit can settle, we expect the settlement's level and harvest reserves to be reduced.
        self.assertEqual(initial_level - 1, test_setl.level)
        self.assertLess(test_setl.harvest_reserves, initial_harvest_reserves)
        self.assertTrue(test_setl.produced_settler)
        # We also expect the settlement's garrison to now have a unit - the produced one.
        self.assertTrue(test_setl.garrison)
        self.assertIsNone(test_setl.current_work)

    @patch("random.randint")
    def test_investigate_relic_scrutineers(self, random_mock: MagicMock):
        """
        Ensure that players of the Scrutineers faction always succeed in their investigations.
        :param random_mock: The mock representation of random.randint().
        """
        # Normally, investigations only succeed when the returned value is under 70.
        random_mock.return_value = 100
        test_player = Player("Tester", Faction.SCRUTINEERS, 0, 0, [], [], [], set(), set())

        # We don't really care what the result is, just make sure it succeeded.
        self.assertNotEqual(InvestigationResult.NONE,
                            investigate_relic(test_player, self.TEST_UNIT, (9, 9),
                                              GameConfig(2, test_player.faction, False, False, False)))

    @patch("random.randint")
    def test_investigate_relic_without_blessing(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' fortune actually yield wealth when the player has no ongoing blessing.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 5

        self.assertEqual(self.ORIGINAL_WEALTH, self.TEST_PLAYER.wealth)
        result: InvestigationResult = investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG)
        self.assertEqual(InvestigationResult.WEALTH, result)
        self.assertEqual(self.ORIGINAL_WEALTH + 25, self.TEST_PLAYER.wealth)

    @patch("random.randint")
    def test_investigate_relic_fortune(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' fortune progress the current player's ongoing blessing.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 5
        fortune_consumed = 9
        self.TEST_PLAYER.ongoing_blessing = OngoingBlessing(BLESSINGS["beg_spl"], fortune_consumed)

        result: InvestigationResult = investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG)
        self.assertEqual(InvestigationResult.FORTUNE, result)
        self.assertEqual(fortune_consumed + self.TEST_PLAYER.ongoing_blessing.blessing.cost / 5,
                         self.TEST_PLAYER.ongoing_blessing.fortune_consumed)

    @patch("random.randint")
    def test_investigate_relic_vision_no_fog_of_war(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' vision actually yield wealth when the game has fog of war disabled.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 25

        self.assertEqual(self.ORIGINAL_WEALTH, self.TEST_PLAYER.wealth)
        result: InvestigationResult = investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9),
                                                        GameConfig(2, self.TEST_PLAYER.faction, True, False, True))
        self.assertEqual(InvestigationResult.WEALTH, result)
        self.assertEqual(self.ORIGINAL_WEALTH + 25, self.TEST_PLAYER.wealth)

    @patch("random.randint")
    def test_investigate_relic_vision(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' vision add to the player's seen quads.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 25
        relic_location = (30, 40)

        self.assertFalse(self.TEST_PLAYER.quads_seen)
        result: InvestigationResult = \
            investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, relic_location, self.TEST_CONFIG)
        self.assertEqual(InvestigationResult.VISION, result)
        # Vision is granted ten steps vertically and horizontally from the relic's location, making for a 21x21 square.
        self.assertEqual(21 * 21, len(self.TEST_PLAYER.quads_seen))
        # Also make sure the quads in the right locations have been added.
        for i in range(relic_location[1] - 10, relic_location[1] + 11):
            for j in range(relic_location[0] - 10, relic_location[0] + 11):
                self.assertIn((j, i), self.TEST_PLAYER.quads_seen)

    @patch("random.randint")
    def test_investigate_relic_health(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' health add to the unit's current and maximum health.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 35

        result: InvestigationResult = investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG)
        self.assertEqual(InvestigationResult.HEALTH, result)
        self.assertEqual(self.ORIGINAL_HEALTH + 5, self.TEST_UNIT.health)
        self.assertEqual(self.ORIGINAL_PLAN_HEALTH + 5, self.TEST_UNIT.plan.max_health)

    @patch("random.randint")
    def test_investigate_relic_power(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' power add to the unit's plan's power.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 45

        result: InvestigationResult = investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG)
        self.assertEqual(InvestigationResult.POWER, result)
        self.assertEqual(self.ORIGINAL_PLAN_POWER + 5, self.TEST_UNIT.plan.power)

    @patch("random.randint")
    def test_investigate_relic_stamina(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' stamina add to the unit's remaining and total stamina.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 55

        result: InvestigationResult = investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG)
        self.assertEqual(InvestigationResult.STAMINA, result)
        self.assertEqual(self.ORIGINAL_PLAN_STAMINA + 1, self.TEST_UNIT.plan.total_stamina)
        self.assertEqual(self.ORIGINAL_PLAN_STAMINA + 1, self.TEST_UNIT.remaining_stamina)

    @patch("random.randint")
    def test_investigate_relic_upkeep(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' upkeep remove the cost from the unit.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 65

        self.assertTrue(self.TEST_UNIT.plan.cost)
        result: InvestigationResult = investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG)
        self.assertEqual(InvestigationResult.UPKEEP, result)
        self.assertFalse(self.TEST_UNIT.plan.cost)

    @patch("random.randint")
    def test_investigate_relic_failure(self, random_mock: MagicMock):
        """
        Ensure that investigations that fail yield the correct result.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 90

        self.assertEqual(InvestigationResult.NONE,
                         investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG))


if __name__ == '__main__':
    unittest.main()