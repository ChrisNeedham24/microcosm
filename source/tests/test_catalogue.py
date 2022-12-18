import unittest

from source.foundation.catalogue import Namer, SETL_NAMES, get_heathen_plan, get_heathen
from source.foundation.models import Biome, UnitPlan, Heathen


class CatalogueTest(unittest.TestCase):
    """
    The test class for catalogue.py.
    """

    def test_namer(self):
        """
        Ensure that the Namer class operates as expected, retrieving and removing names correctly, as well as being
        able to reset its name bank.
        """
        namer = Namer()
        self.assertTrue(namer.names)

        settlement_name: str = namer.get_settlement_name(Biome.SEA)
        # The name that was retrieved should be valid, but should no longer be in the Namer's bank.
        self.assertIn(settlement_name, SETL_NAMES[Biome.SEA])
        self.assertNotIn(settlement_name, namer.names[Biome.SEA])

        # Get a valid test name from the dictionary.
        name_to_remove: str = SETL_NAMES[Biome.DESERT][0]
        # The Namer should know of this name, and after removing it, should no longer have it in its bank.
        self.assertIn(name_to_remove, namer.names[Biome.DESERT])
        namer.remove_settlement_name(name_to_remove, Biome.DESERT)
        self.assertNotIn(name_to_remove, namer.names[Biome.DESERT])

        # Remove all names from the Namer.
        namer.names = {}
        # After resetting, the names should be back.
        namer.reset()
        self.assertTrue(namer.names)

    def test_heathen_plan(self):
        """
        Ensure that a heathen UnitPlan from the later stages of the game is more powerful, has more health, and has more
        '+' characters in its name.
        """
        beginning_heathen: UnitPlan = get_heathen_plan(1)
        end_heathen: UnitPlan = get_heathen_plan(100)

        self.assertGreater(end_heathen.power, beginning_heathen.power)
        self.assertGreater(end_heathen.max_health, beginning_heathen.max_health)
        self.assertGreater(len(end_heathen.name), len(beginning_heathen.name))

    def test_get_heathen(self):
        """
        Ensure that retrieved Heathen objects have their details correctly extracted from the expected UnitPlan and
        supplied location.
        """
        test_loc = (25, 25)
        test_turn = 1
        # Get what we expect the plan to look like.
        expected_plan: UnitPlan = get_heathen_plan(test_turn)

        heathen: Heathen = get_heathen(test_loc, test_turn)

        # Make sure the details are extracted and the location is assigned.
        self.assertEqual(expected_plan.max_health, heathen.health)
        self.assertEqual(expected_plan.total_stamina, heathen.remaining_stamina)
        self.assertTupleEqual(test_loc, heathen.location)
        self.assertEqual(expected_plan, heathen.plan)


if __name__ == '__main__':
    unittest.main()
