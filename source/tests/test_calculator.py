import unittest
from typing import List, Tuple, Generator
from unittest.mock import patch, MagicMock

from source.foundation.catalogue import UNIT_PLANS, BLESSINGS, PROJECTS
from source.foundation.models import Biome, Unit, AttackData, HealData, Settlement, SetlAttackData, Player, Faction, \
    Construction, Improvement, ImprovementType, Effect, UnitPlan, GameConfig, InvestigationResult, OngoingBlessing, \
    Quad, EconomicStatus, HarvestStatus, DeployerUnitPlan, DeployerUnit, ResourceCollection
from source.util.calculator import calculate_yield_for_quad, clamp, attack, heal, attack_setl, complete_construction, \
    investigate_relic, get_player_totals, get_setl_totals, gen_spiral_indices, get_resources_for_settlement, \
    player_has_resources_for_improvement, subtract_player_resources_for_improvement, split_list_into_chunks, \
    update_player_quads_seen_around_point


class CalculatorTest(unittest.TestCase):
    """
    The test class for calculator.py.
    """
    ORIGINAL_WEALTH = 99
    ORIGINAL_HEALTH = 1
    ORIGINAL_STAMINA = 2

    def setUp(self) -> None:
        """
        Initialise our test models.
        """
        self.TEST_PLAYER = Player("TestMan", Faction.NOCTURNE, 0, wealth=self.ORIGINAL_WEALTH)
        self.TEST_CONFIG = GameConfig(2, self.TEST_PLAYER.faction, True, True, True, False)
        self.TEST_UNIT_PLAN = UnitPlan(100, 100, 3, "TesterUnit", None, 25)
        self.ORIGINAL_PLAN_HEALTH = self.TEST_UNIT_PLAN.max_health
        self.ORIGINAL_PLAN_POWER = self.TEST_UNIT_PLAN.power
        self.ORIGINAL_PLAN_STAMINA = self.TEST_UNIT_PLAN.total_stamina
        self.ORIGINAL_PLAN_COST = self.TEST_UNIT_PLAN.cost
        self.TEST_UNIT = Unit(self.ORIGINAL_HEALTH, self.ORIGINAL_STAMINA, (3, 4), False, self.TEST_UNIT_PLAN)

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
        healer = Unit(50, 2, (0, 0), False, UNIT_PLANS[-5])
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
        setl = Settlement("Test", (1, 0), [], [], ResourceCollection(), [], strength=settlement_strength)
        player = Player("Tester", Faction.NOCTURNE, 0, settlements=[setl])
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

    def test_get_player_totals_agriculturists(self):
        """
        Ensure that the zeal yield is calculated correctly for players of the Agriculturists faction.
        """
        quad_imp_zeal = 4
        imp = Improvement(ImprovementType.INDUSTRIAL, 0, "Test", "Improvement", Effect(zeal=quad_imp_zeal), None)
        quad = Quad(Biome.FOREST, 0, 0, quad_imp_zeal, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [])
        player = Player("Tester", Faction.AGRICULTURISTS, 0, settlements=[setl])

        _, _, zeal, _ = get_player_totals(player, False)
        # Agriculturists receive 75% of the zeal that players of other factions do.
        self.assertEqual(2 * quad_imp_zeal * 0.75, zeal)

    def test_get_player_totals_fundamentalists(self):
        """
        Ensure that the zeal yield is calculated correctly for players of the Fundamentalists faction.
        """
        quad_imp_zeal = 4
        imp = Improvement(ImprovementType.INDUSTRIAL, 0, "Test", "Improvement", Effect(zeal=quad_imp_zeal), None)
        quad = Quad(Biome.FOREST, 0, 0, quad_imp_zeal, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [])
        player = Player("Tester", Faction.FUNDAMENTALISTS, 0, settlements=[setl])

        _, _, zeal, _ = get_player_totals(player, False)
        # Fundamentalists receive 125% of the zeal that players of other factions do.
        self.assertEqual(2 * quad_imp_zeal * 1.25, zeal)

    def test_get_player_totals_economical_project(self):
        """
        Ensure that the wealth yield is calculated correctly when a settlement is working on the economical project.
        """
        quad_imp_zeal = 4
        quad_imp_wealth = 2

        imp = Improvement(ImprovementType.INDUSTRIAL, 0, "Test", "Improvement",
                          Effect(zeal=quad_imp_zeal, wealth=quad_imp_wealth), None)
        quad = Quad(Biome.FOREST, quad_imp_wealth, 0, quad_imp_zeal, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [],
                          current_work=Construction(PROJECTS[1]))
        player = Player("Tester", Faction.INFIDELS, 0, settlements=[setl])

        wealth, _, _, _ = get_player_totals(player, False)
        # We expect the standard quad and improvement wealth to be supplemented with a quarter of the produced zeal.
        self.assertEqual(2 * quad_imp_wealth + 2 * quad_imp_zeal / 4, wealth)

    def test_get_player_totals_recession(self):
        """
        Ensure that the wealth yield is calculated correctly when a settlement is in recession.
        """
        quad_imp_wealth = 4
        imp = Improvement(ImprovementType.ECONOMICAL, 0, "Test", "Improvement", Effect(wealth=quad_imp_wealth), None)
        quad = Quad(Biome.FOREST, quad_imp_wealth, 0, 0, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [],
                          level=10, economic_status=EconomicStatus.RECESSION)
        player = Player("Tester", Faction.INFIDELS, 0, settlements=[setl])

        wealth, _, _, _ = get_player_totals(player, False)
        # The wealth would normally be 26, but is instead 0 due to the recession.
        self.assertFalse(wealth)

    def test_get_player_totals_boom(self):
        """
        Ensure that the wealth yield is calculated correctly when a settlement is in an economic boom.
        """
        quad_imp_wealth = 4
        imp = Improvement(ImprovementType.ECONOMICAL, 0, "Test", "Improvement", Effect(wealth=quad_imp_wealth), None)
        quad = Quad(Biome.FOREST, quad_imp_wealth, 0, 0, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [],
                          level=10, economic_status=EconomicStatus.BOOM)
        player = Player("Tester", Faction.INFIDELS, 0, settlements=[setl])

        wealth, _, _, _ = get_player_totals(player, False)
        # Add the quad and improvement wealth together to begin with.
        expected_wealth = 2 * quad_imp_wealth
        # Then, add the level bonus.
        expected_wealth += (setl.level - 1) * 0.25 * expected_wealth
        # Lastly, being in an economic boom grants an extra 50% on top.
        expected_wealth *= 1.5
        self.assertEqual(expected_wealth, wealth)

    def test_get_player_totals_godless(self):
        """
        Ensure that the wealth yield is calculated correctly for players of the Godless faction.
        """
        quad_imp_wealth = 4
        imp = Improvement(ImprovementType.ECONOMICAL, 0, "Test", "Improvement", Effect(wealth=quad_imp_wealth), None)
        quad = Quad(Biome.FOREST, quad_imp_wealth, 0, 0, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [])
        player = Player("Tester", Faction.GODLESS, 0, settlements=[setl])

        wealth, _, _, _ = get_player_totals(player, False)
        # The Godless receive 125% of the wealth that players of other factions do.
        self.assertEqual(2 * quad_imp_wealth * 1.25, wealth)

    def test_get_player_totals_orthodox(self):
        """
        Ensure that the wealth and fortune yields are calculated correctly for players of the Orthodox faction.
        """
        quad_imp_wealth = 4
        quad_imp_fortune = 2
        imp = Improvement(ImprovementType.ECONOMICAL, 0, "Test", "Improvement",
                          Effect(wealth=quad_imp_wealth, fortune=quad_imp_fortune), None)
        quad = Quad(Biome.FOREST, quad_imp_wealth, 0, 0, quad_imp_fortune, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [])
        player = Player("Tester", Faction.ORTHODOX, 0, settlements=[setl])

        wealth, _, _, fortune = get_player_totals(player, False)
        # The Orthodox receive 75% of the wealth and 125% of the fortune that players of other factions do.
        self.assertEqual(2 * quad_imp_wealth * 0.75, wealth)
        self.assertEqual(2 * quad_imp_fortune * 1.25, fortune)

    def test_get_player_totals_aurora(self):
        """
        Ensure that the wealth yield is calculated correctly for players with settlements with aurora resources.
        """
        quad_imp_wealth = 4
        imp = Improvement(ImprovementType.ECONOMICAL, 0, "Test", "Improvement", Effect(wealth=quad_imp_wealth), None)
        quad = Quad(Biome.FOREST, quad_imp_wealth, 0, 0, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(aurora=2), [])
        player = Player("Tester", Faction.AGRICULTURISTS, 0, settlements=[setl])

        wealth, _, _, _ = get_player_totals(player, False)
        # Since the player's settlement has two aurora resources, we expect wealth to be doubled.
        self.assertEqual(2 * quad_imp_wealth * 2, wealth)

    def test_get_player_totals_bountiful_project(self):
        """
        Ensure that the harvest yield is calculated correctly when a settlement is working on the bountiful project.
        """
        quad_imp_zeal = 4
        quad_imp_harvest = 2

        imp = Improvement(ImprovementType.INDUSTRIAL, 0, "Test", "Improvement",
                          Effect(zeal=quad_imp_zeal, harvest=quad_imp_harvest), None)
        quad = Quad(Biome.FOREST, 0, quad_imp_harvest, quad_imp_zeal, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [],
                          current_work=Construction(PROJECTS[0]))
        player = Player("Tester", Faction.INFIDELS, 0, settlements=[setl])

        _, harvest, _, _ = get_player_totals(player, False)
        # We expect the standard quad and improvement harvest to be supplemented with a quarter of the produced zeal.
        self.assertEqual(2 * quad_imp_harvest + 2 * quad_imp_zeal / 4, harvest)

    def test_get_player_totals_poor_harvest(self):
        """
        Ensure that the harvest yield is calculated correctly when a settlement has a poor harvest.
        """
        quad_imp_harvest = 4
        imp = Improvement(ImprovementType.BOUNTIFUL, 0, "Test", "Improvement", Effect(harvest=quad_imp_harvest), None)
        quad = Quad(Biome.FOREST, 0, quad_imp_harvest, 0, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [],
                          level=10, harvest_status=HarvestStatus.POOR)
        player = Player("Tester", Faction.INFIDELS, 0, settlements=[setl])

        _, harvest, _, _ = get_player_totals(player, False)
        # The harvest would normally be 26, but is instead 0 due to the poor harvest.
        self.assertFalse(harvest)

    def test_get_player_totals_besieged(self):
        """
        Ensure that the harvest yield is calculated correctly when a settlement is under siege.
        """
        quad_imp_harvest = 4
        imp = Improvement(ImprovementType.BOUNTIFUL, 0, "Test", "Improvement", Effect(harvest=quad_imp_harvest), None)
        quad = Quad(Biome.FOREST, 0, quad_imp_harvest, 0, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [], level=10, besieged=True)
        player = Player("Tester", Faction.INFIDELS, 0, settlements=[setl])

        _, harvest, _, _ = get_player_totals(player, False)
        # The harvest would normally be 26, but is instead 0 due to the siege.
        self.assertFalse(harvest)

    def test_get_player_totals_plentiful_harvest(self):
        """
        Ensure that the harvest yield is calculated correctly when a settlement has a plentiful harvest.
        """
        quad_imp_harvest = 4
        imp = Improvement(ImprovementType.BOUNTIFUL, 0, "Test", "Improvement", Effect(harvest=quad_imp_harvest), None)
        quad = Quad(Biome.FOREST, 0, quad_imp_harvest, 0, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [],
                          level=10, harvest_status=HarvestStatus.PLENTIFUL)
        player = Player("Tester", Faction.INFIDELS, 0, settlements=[setl])

        _, harvest, _, _ = get_player_totals(player, False)
        # Add the quad and improvement harvest together to begin with.
        expected_harvest = 2 * quad_imp_harvest
        # Then, add the level bonus.
        expected_harvest += (setl.level - 1) * 0.25 * expected_harvest
        # Lastly, having a plentiful harvest grants an extra 50% on top.
        expected_harvest *= 1.5
        self.assertEqual(expected_harvest, harvest)

    def test_get_player_totals_ravenous(self):
        """
        Ensure that the harvest yield is calculated correctly for players of the Ravenous faction.
        """
        quad_imp_harvest = 4
        imp = Improvement(ImprovementType.BOUNTIFUL, 0, "Test", "Improvement", Effect(harvest=quad_imp_harvest), None)
        quad = Quad(Biome.FOREST, 0, quad_imp_harvest, 0, 0, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [])
        player = Player("Tester", Faction.RAVENOUS, 0, settlements=[setl])

        _, harvest, _, _ = get_player_totals(player, False)
        # The Ravenous receive 125% of the harvest that players of other factions do.
        self.assertEqual(2 * quad_imp_harvest * 1.25, harvest)

    def test_get_player_totals_magical_project(self):
        """
        Ensure that the fortune yield is calculated correctly when a settlement is working on the magical project.
        """
        quad_imp_zeal = 4
        quad_imp_fortune = 2

        imp = Improvement(ImprovementType.INDUSTRIAL, 0, "Test", "Improvement",
                          Effect(zeal=quad_imp_zeal, fortune=quad_imp_fortune), None)
        quad = Quad(Biome.FOREST, 0, 0, quad_imp_zeal, quad_imp_fortune, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [],
                          current_work=Construction(PROJECTS[2]))
        player = Player("Tester", Faction.INFIDELS, 0, settlements=[setl])

        _, _, _, fortune = get_player_totals(player, False)
        # We expect the standard quad and improvement fortune to be supplemented with a quarter of the produced zeal.
        self.assertEqual(2 * quad_imp_fortune + 2 * quad_imp_zeal / 4, fortune)

    def test_get_player_totals_scrutineers(self):
        """
        Ensure that the fortune yield is calculated correctly for players of the Scrutineers faction.
        """
        quad_imp_fortune = 4
        imp = Improvement(ImprovementType.MAGICAL, 0, "Test", "Improvement", Effect(fortune=quad_imp_fortune), None)
        quad = Quad(Biome.SEA, 0, 0, 0, quad_imp_fortune, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [])
        player = Player("Tester", Faction.SCRUTINEERS, 0, settlements=[setl])

        _, _, _, fortune = get_player_totals(player, False)
        # Scrutineers receive 75% of the fortune that players of other factions do.
        self.assertEqual(2 * quad_imp_fortune * 0.75, fortune)

    def test_get_player_totals_aquamarine(self):
        """
        Ensure that the fortune yield is calculated correctly for players with settlements with aquamarine resources.
        """
        quad_imp_fortune = 4
        imp = Improvement(ImprovementType.MAGICAL, 0, "Test", "Improvement", Effect(fortune=quad_imp_fortune), None)
        quad = Quad(Biome.SEA, 0, 0, 0, quad_imp_fortune, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(aquamarine=2), [])
        player = Player("Tester", Faction.AGRICULTURISTS, 0, settlements=[setl])

        _, _, _, fortune = get_player_totals(player, False)
        # Since the player's settlement has two aquamarine resources, we expect fortune to be doubled.
        self.assertEqual(2 * quad_imp_fortune * 2, fortune)

    def test_get_player_totals_night(self):
        """
        Ensure that harvest and fortune yields are calculated correctly when it is nighttime.
        """
        quad_imp_fortune = 5
        quad_imp_harvest = 4
        imp = Improvement(ImprovementType.MAGICAL, 0, "Test", "Improvement",
                          Effect(harvest=quad_imp_harvest, fortune=quad_imp_fortune), None)
        quad = Quad(Biome.SEA, 0, quad_imp_harvest, 0, quad_imp_fortune, (0, 0))
        setl = Settlement("Testville", (0, 0), [imp], [quad], ResourceCollection(), [])
        player = Player("Tester", Faction.INFIDELS, 0, settlements=[setl])

        _, harvest, _, fortune = get_player_totals(player, True)
        # For players of all factions but The Nocturne, nighttime results in 50% of the usual harvest, and 110% of the
        # usual fortune.
        self.assertEqual(2 * quad_imp_harvest / 2, harvest)
        self.assertEqual(2 * quad_imp_fortune * 1.1, fortune)

        setl.resources = ResourceCollection(sunstone=1)
        _, harvest, _, fortune = get_player_totals(player, True)
        # However, settlements with sunstone do not suffer the harvest penalty, and still receive the fortune bonus.
        self.assertEqual(2 * quad_imp_harvest, harvest)
        self.assertEqual(2 * quad_imp_fortune * 1.1, fortune)

        player.faction = Faction.NOCTURNE
        _, harvest, _, fortune = get_player_totals(player, True)
        # In the same way, players of the Nocturne do not suffer the harvest penalty, and still receive the fortune
        # bonus.
        self.assertEqual(2 * quad_imp_harvest, harvest)
        self.assertEqual(2 * quad_imp_fortune * 1.1, fortune)

    def test_get_player_totals_standard(self):
        """
        Ensure that player totals are calculated correctly in a situation with no penalties or bonuses.
        """
        quad_wealth = 2
        imp_harvest = 4
        quad_zeal = 6
        imp_fortune = 8
        imp = Improvement(ImprovementType.MAGICAL, 0, "Standard", "Improvement",
                          Effect(harvest=imp_harvest, fortune=imp_fortune), None)
        quad = Quad(Biome.MOUNTAIN, quad_wealth, 0, quad_zeal, 0, (0, 0))
        setl = Settlement("Pleasantville", (0, 0), [imp], [quad], ResourceCollection(), [], level=10)
        player = Player("Johnny Appleseed", Faction.INFIDELS, 0, settlements=[setl])

        wealth, harvest, zeal, fortune = get_player_totals(player, False)
        # Each yield should be the base quad/improvement value, with the level bonus added on.
        self.assertEqual(quad_wealth + 2.25 * quad_wealth, wealth)
        self.assertEqual(imp_harvest + 2.25 * imp_harvest, harvest)
        self.assertEqual(quad_zeal + 2.25 * quad_zeal, zeal)
        self.assertEqual(imp_fortune + 2.25 * imp_fortune, fortune)

    def test_get_setl_totals_strict(self):
        """
        Ensure that the strict parameter functions correctly when retrieving settlement totals.
        """
        setl = Settlement("Test Town", (0, 0), [], [], ResourceCollection(), [])
        player = Player("Testerman", Faction.INFIDELS, 0, settlements=[setl])

        _, _, zeal, fortune = get_setl_totals(player, setl, False)
        # A settlement will always produce at least 1 zeal and fortune when strict is False.
        self.assertEqual(1, zeal)
        self.assertEqual(1, fortune)

        _, _, zeal, fortune = get_setl_totals(player, setl, False, strict=True)
        # However, when strict is True, settlements can produce 0 zeal and fortune.
        self.assertFalse(zeal)
        self.assertFalse(fortune)

    def test_complete_construction(self):
        """
        Ensure that when completing a construction that yields added strength and satisfaction, the related settlement
        is correctly updated.
        """
        added_strength = 5
        test_improvement = Improvement(ImprovementType.ECONOMICAL, 1, "Money", "Time",
                                       Effect(wealth=1, strength=added_strength, satisfaction=5), None)
        # Note that we set the settlement's satisfaction to 99.
        test_setl = Settlement("Working", (50, 50), [], [], ResourceCollection(), [],
                               current_work=Construction(test_improvement), satisfaction=99)
        test_player = Player("Tester", Faction.NOCTURNE, 0, settlements=[test_setl])

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
        test_setl = Settlement("Working", (50, 50), [], [], ResourceCollection(), [],
                               current_work=Construction(test_improvement), satisfaction=1)
        test_player = Player("Tester", Faction.CONCENTRATED, 0, settlements=[test_setl])

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
        test_setl = Settlement("Working", (50, 50), [], [], ResourceCollection(), [],
                               current_work=Construction(test_unit_plan), level=initial_level,
                               harvest_reserves=initial_harvest_reserves)
        test_player = Player("Tester", Faction.FRONTIERSMEN, 0, settlements=[test_setl])

        complete_construction(test_setl, test_player)
        # Because the unit can settle, we expect the settlement's level and harvest reserves to be reduced.
        self.assertEqual(initial_level - 1, test_setl.level)
        self.assertLess(test_setl.harvest_reserves, initial_harvest_reserves)
        self.assertTrue(test_setl.produced_settler)
        # We also expect the settlement's garrison to now have a unit - the produced one.
        self.assertTrue(test_setl.garrison)
        self.assertIsNone(test_setl.current_work)

    def test_complete_construction_deployer_unit(self):
        """
        Ensure that when completing a construction that yields a deployer unit, the related settlement is correctly
        updated.
        """
        test_deployer_unit_plan = DeployerUnitPlan(20, 20, 10, "DeployerMan", None, 1)
        test_setl = Settlement("Working", (50, 50), [], [], ResourceCollection(), [],
                               current_work=Construction(test_deployer_unit_plan))
        test_player = Player("Tester", Faction.FRONTIERSMEN, 0, settlements=[test_setl])

        complete_construction(test_setl, test_player)
        # We expect the settlement's garrison to now have a deployer unit - the produced one.
        self.assertTrue(test_setl.garrison)
        self.assertTrue(isinstance(test_setl.garrison[0], DeployerUnit))
        self.assertIsNone(test_setl.current_work)

    @patch("random.randint")
    def test_investigate_relic_scrutineers(self, random_mock: MagicMock):
        """
        Ensure that players of the Scrutineers faction always succeed in their investigations.
        :param random_mock: The mock representation of random.randint().
        """
        # Normally, investigations only succeed when the returned value is under 100.
        random_mock.return_value = 140
        test_player = Player("Tester", Faction.SCRUTINEERS, 0)

        # We don't really care what the result is, just make sure it succeeded.
        self.assertNotEqual(InvestigationResult.NONE,
                            investigate_relic(test_player, self.TEST_UNIT, (9, 9),
                                              GameConfig(2, test_player.faction, False, False, False, False)))

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
        result: InvestigationResult = \
            investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9),
                              GameConfig(2, self.TEST_PLAYER.faction, True, False, True, False))
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
    def test_investigate_relic_ore(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' ore add 10 ore resources to the player.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 75

        self.assertFalse(self.TEST_PLAYER.resources)
        result: InvestigationResult = investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG)
        self.assertEqual(InvestigationResult.ORE, result)
        self.assertEqual(10, self.TEST_PLAYER.resources.ore)

    @patch("random.randint")
    def test_investigate_relic_timber(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' timber add 10 timber resources to the player.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 85

        self.assertFalse(self.TEST_PLAYER.resources)
        result: InvestigationResult = investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG)
        self.assertEqual(InvestigationResult.TIMBER, result)
        self.assertEqual(10, self.TEST_PLAYER.resources.timber)

    @patch("random.randint")
    def test_investigate_relic_magma(self, random_mock: MagicMock):
        """
        Ensure that investigations that 'roll' magma add 10 magma resources to the player.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 95

        self.assertFalse(self.TEST_PLAYER.resources)
        result: InvestigationResult = investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG)
        self.assertEqual(InvestigationResult.MAGMA, result)
        self.assertEqual(10, self.TEST_PLAYER.resources.magma)

    @patch("random.randint")
    def test_investigate_relic_failure(self, random_mock: MagicMock):
        """
        Ensure that investigations that fail yield the correct result.
        :param random_mock: The mock representation of random.randint().
        """
        random_mock.return_value = 120

        self.assertEqual(InvestigationResult.NONE,
                         investigate_relic(self.TEST_PLAYER, self.TEST_UNIT, (9, 9), self.TEST_CONFIG))

    def test_gen_spiral_indices(self):
        """
        Ensure that when spiral indices are generated around a fixed point, at least all eight directly adjacent
        locations are generated.
        """
        central_loc: (int, int) = 5, 5
        expected_indices: List[Tuple[int, int]] = [
            central_loc,
            (central_loc[0] + 1, central_loc[1]),
            (central_loc[0] + 1, central_loc[1] + 1),
            (central_loc[0], central_loc[1] + 1),
            (central_loc[0] - 1, central_loc[1] + 1),
            (central_loc[0] - 1, central_loc[1]),
            (central_loc[0] - 1, central_loc[1] - 1),
            (central_loc[0], central_loc[1] - 1),
            (central_loc[0] + 1, central_loc[1] - 1)
        ]
        # The test does not have to be as thorough as verifying each and every index, we just want to make sure this
        # function is working at a basic level.
        self.assertTrue(all(index in gen_spiral_indices(central_loc) for index in expected_indices))

    def test_get_resources_for_settlement(self):
        """
        Ensure that resource counts are determined correctly for settlements.
        """
        test_quads: List[List[Quad]] = [
            [Quad(Biome.DESERT, 0, 0, 0, 0, (0, 0), ResourceCollection(ore=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (1, 0), ResourceCollection(timber=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (2, 0), ResourceCollection(magma=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (3, 0), ResourceCollection(aurora=1))],
            [Quad(Biome.DESERT, 0, 0, 0, 0, (0, 1), ResourceCollection(bloodstone=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (1, 1), ResourceCollection(obsidian=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (2, 1), ResourceCollection(sunstone=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (3, 1), ResourceCollection(aurora=1))],
            [Quad(Biome.DESERT, 0, 0, 0, 0, (0, 2), ResourceCollection(ore=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (1, 2), ResourceCollection(timber=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (2, 2), ResourceCollection(magma=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (3, 2), ResourceCollection(aurora=1))],
            [Quad(Biome.DESERT, 0, 0, 0, 0, (0, 3), ResourceCollection(bloodstone=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (1, 3), ResourceCollection(obsidian=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (2, 3), ResourceCollection(sunstone=1)),
             Quad(Biome.DESERT, 0, 0, 0, 0, (3, 3), ResourceCollection(aurora=1))]
        ]
        # Simulating a settlement belonging to The Concentrated, to ensure that there is no resource double-up.
        test_setl_locs: List[Tuple[int, int]] = [(1, 1), (1, 2)]
        # We expect the settlement to have the resources from all of the above quads apart from the ones at (3, 0),
        # (3, 1), (3, 2), and (3, 3), as they are one quad away. As such, the resources should have no aurora since
        # those quads are one away, nor any aquamarine, as none of the quads have that.
        expected_resources: ResourceCollection = \
            ResourceCollection(ore=2, timber=2, magma=2, aurora=0, bloodstone=2, obsidian=2, sunstone=2, aquamarine=0)
        resources = get_resources_for_settlement(test_setl_locs, test_quads)
        self.assertEqual(expected_resources, resources)

    def test_player_has_resources_for_improvement(self):
        """
        Ensure that whether a player meets the resource requirements for an improvement is correctly determined.
        """
        test_no_resource_improvement: Improvement = \
            Improvement(ImprovementType.MAGICAL, 0, "No", "Resources", Effect(), None, req_resources=None)
        test_all_resources_improvement: Improvement = \
            Improvement(ImprovementType.MAGICAL, 0, "All", "Resources", Effect(), None,
                        req_resources=ResourceCollection(ore=1, timber=1, magma=1))

        # With no resources, the player should be able to construct the improvement with no required resources, but not
        # the one that requires one of each of the core resources.
        self.TEST_PLAYER.resources = ResourceCollection()
        self.assertTrue(player_has_resources_for_improvement(self.TEST_PLAYER, test_no_resource_improvement))
        self.assertFalse(player_has_resources_for_improvement(self.TEST_PLAYER, test_all_resources_improvement))

        # We expect the player to only be able to construct the improvement requiring all three core resources once they
        # themselves have one of each of the core resources.
        self.TEST_PLAYER.resources = ResourceCollection(ore=1)
        self.assertFalse(player_has_resources_for_improvement(self.TEST_PLAYER, test_all_resources_improvement))
        self.TEST_PLAYER.resources = ResourceCollection(ore=1, timber=1)
        self.assertFalse(player_has_resources_for_improvement(self.TEST_PLAYER, test_all_resources_improvement))
        self.TEST_PLAYER.resources = ResourceCollection(ore=1, timber=1, magma=1)
        self.assertTrue(player_has_resources_for_improvement(self.TEST_PLAYER, test_all_resources_improvement))

    def test_subtract_player_resources_for_improvement(self):
        """
        Ensure that player resources are correctly subtracted when constructing an improvement requiring them.
        """
        test_improvement: Improvement = \
            Improvement(ImprovementType.MAGICAL, 0, "All", "Resources", Effect(), None,
                        req_resources=ResourceCollection(ore=1, timber=2, magma=3))
        self.TEST_PLAYER.resources = ResourceCollection(ore=5, timber=4, magma=10)
        subtract_player_resources_for_improvement(self.TEST_PLAYER, test_improvement)
        # Naturally the player's resources should have been subtracted by the required values for the test improvement.
        self.assertEqual(ResourceCollection(ore=4, timber=2, magma=7), self.TEST_PLAYER.resources)

    def test_split_list_into_chunks(self):
        """
        Ensure that lists are split into chunks correctly.
        """
        test_list: List[str] = ["a", "b", "c", "d", "e", "f", "g"]
        chunked_list: Generator[list, None, None] = split_list_into_chunks(test_list, chunk_length=2)
        # The created generator should yield sub-lists of two elements each time next() is called until the original
        # elements are exhausted.
        self.assertListEqual(["a", "b"], next(chunked_list))
        self.assertListEqual(["c", "d"], next(chunked_list))
        self.assertListEqual(["e", "f"], next(chunked_list))
        # Because there aren't sufficient elements to fill out a whole two-element chunk, we only expect one.
        self.assertListEqual(["g"], next(chunked_list))
        # Since there are no elements left, calling next() should raise a StopIteration exception.
        self.assertRaises(StopIteration, lambda: next(chunked_list))

    def test_update_player_quads_seen_around_point(self):
        """
        Ensure that the seen quads for a player are correctly updated around a point with the specified range.
        """
        self.TEST_PLAYER.quads_seen = set()
        update_player_quads_seen_around_point(self.TEST_PLAYER, point=(1, 1), vision_range=2)
        # We expect the quads that would have been in the negatives, e.g. (-1, -1), which were technically within range,
        # to not have been added because those quads don't exist.
        self.assertSetEqual({(0, 0), (1, 0), (2, 0), (3, 0),
                             (0, 1), (1, 1), (2, 1), (3, 1),
                             (0, 2), (1, 2), (2, 2), (3, 2),
                             (0, 3), (1, 3), (2, 3), (3, 3)}, self.TEST_PLAYER.quads_seen)

        self.TEST_PLAYER.quads_seen = set()
        update_player_quads_seen_around_point(self.TEST_PLAYER, point=(98, 88), vision_range=2)
        # We expect the quads that would have been off the board, e.g. (100, 90), which were technically within range,
        # to not have been added because those quads don't exist.
        self.assertSetEqual({(96, 86), (97, 86), (98, 86), (99, 86),
                             (96, 87), (97, 87), (98, 87), (99, 87),
                             (96, 88), (97, 88), (98, 88), (99, 88),
                             (96, 89), (97, 89), (98, 89), (99, 89)}, self.TEST_PLAYER.quads_seen)


if __name__ == '__main__':
    unittest.main()
