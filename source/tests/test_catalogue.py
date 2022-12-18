import typing
import unittest

from source.foundation.catalogue import Namer, SETL_NAMES, get_heathen_plan, get_heathen, UNIT_PLANS, \
    get_default_unit, get_available_improvements, BLESSINGS, IMPROVEMENTS
from source.foundation.models import Biome, UnitPlan, Heathen, Unit, Player, Faction, Settlement, Improvement


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

    def test_get_default_unit(self):
        """
        Ensure that retrieved default Unit objects have their details correctly extracted from the expected UnitPlan and
        supplied location.
        """
        test_loc = (25, 25)
        # The expected plan is just the default warrior.
        expected_plan: UnitPlan = UNIT_PLANS[0]

        unit: Unit = get_default_unit(test_loc)

        # Make sure the details are extracted and the location is assigned.
        self.assertEqual(expected_plan.max_health, unit.health)
        self.assertEqual(expected_plan.total_stamina, unit.remaining_stamina)
        self.assertEqual(test_loc, unit.location)
        self.assertTrue(unit.garrisoned)
        self.assertEqual(expected_plan, unit.plan)

    def test_available_improvements(self):
        """
        Ensure that the available improvements for a player's settlement are correctly determined.
        """
        # The player is of the Frontiersmen faction as they have special behaviour.
        test_player = Player("Frontiersman", Faction.FRONTIERSMEN, 0, 0, [], [], [], set(), set())
        test_settlement = Settlement("Low", (0, 0), [], [], [])
        test_settlement_high = Settlement("High", (0, 0), [], [], [], level=10)

        # Because the player is of the Frontiersmen faction and the supplied settlement is above level 4, no
        # improvements should be available for construction.
        self.assertFalse(get_available_improvements(test_player, test_settlement_high))

        # Now using a lower level settlement instead, we expect all returned improvements to have no pre-requisite for
        # their construction, and for the returned list to be sorted by construction cost.
        improvements: typing.List[Improvement] = get_available_improvements(test_player, test_settlement)
        self.assertTrue(all(imp.prereq is None for imp in improvements))
        self.assertTrue(all(improvements[i].cost <= improvements[i + 1].cost for i in range(len(improvements) - 1)))

        # If we now add a blessing to the test player, we expect there to be an improvement returned with the very same
        # pre-requisite. Once again, we expect the list to be sorted.
        test_player.blessings.append(BLESSINGS["beg_spl"])
        improvements = get_available_improvements(test_player, test_settlement)
        self.assertTrue(any(imp.prereq is not None for imp in improvements))
        self.assertTrue(all(improvements[i].cost <= improvements[i + 1].cost for i in range(len(improvements) - 1)))

        # Lastly, if we add an improvement to the settlement, we expect there to be one less improvement available in
        # comparison to the previous retrieval. The list should still be sorted, too.
        test_settlement.improvements.append(IMPROVEMENTS[0])
        new_improvements = get_available_improvements(test_player, test_settlement)
        self.assertLess(len(new_improvements), len(improvements))
        self.assertTrue(all(improvements[i].cost <= improvements[i + 1].cost for i in range(len(improvements) - 1)))


if __name__ == '__main__':
    unittest.main()
