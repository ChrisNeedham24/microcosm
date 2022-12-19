import unittest

from source.foundation.catalogue import UNIT_PLANS
from source.foundation.models import Biome, Unit, AttackData
from source.util.calculator import calculate_yield_for_quad, clamp, attack


class CalculatorTest(unittest.TestCase):
    """
    The test class for calculator.py.
    """

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
        attacker = Unit(200, 10, (0, 0), False, UNIT_PLANS[-1])
        att_power = attacker.plan.power
        defender = Unit(5, 0, (1, 0), False, UNIT_PLANS[0])
        def_power = defender.plan.power
        ai_attack = False

        attack_data: AttackData = attack(attacker, defender, ai_attack)
        self.assertEqual(attacker, attack_data.attacker)
        self.assertEqual(defender, attack_data.defender)
        self.assertEqual(def_power * 0.25, attack_data.damage_to_attacker)
        self.assertEqual(att_power * 0.25 * 1.2, attack_data.damage_to_defender)
        self.assertEqual(not ai_attack, attack_data.player_attack)
        self.assertFalse(attack_data.attacker_was_killed)
        self.assertTrue(attack_data.defender_was_killed)


if __name__ == '__main__':
    unittest.main()
