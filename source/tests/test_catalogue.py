import typing
import unittest

from source.foundation.catalogue import Namer, SETL_NAMES, get_heathen_plan, get_heathen, UNIT_PLANS, \
    get_default_unit, get_available_improvements, BLESSINGS, IMPROVEMENTS, get_available_blessings,\
    get_all_unlockable, get_improvement, PROJECTS, get_project, get_blessing, get_unit_plan
from source.foundation.models import Biome, UnitPlan, Heathen, Unit, Player, Faction, Settlement, Improvement


class CatalogueTest(unittest.TestCase):
    """
    The test class for catalogue.py.
    """
    TEST_PLAYER = Player("Frontiersman", Faction.FRONTIERSMEN, 0, 0, [], [], [], set(), set())
    TEST_BLESSING = BLESSINGS["beg_spl"]
    TEST_IMPROVEMENT = IMPROVEMENTS[0]

    def setUp(self) -> None:
        """
        Reset the test player's faction and blessings before each test.
        """
        self.TEST_PLAYER.faction = Faction.FRONTIERSMEN
        self.TEST_PLAYER.blessings = []

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
        test_settlement = Settlement("Low", (0, 0), [], [], [])
        test_settlement_high = Settlement("High", (0, 0), [], [], [], level=10)

        # Because the player is of the Frontiersmen faction and the supplied settlement is above level 4, no
        # improvements should be available for construction.
        self.assertFalse(get_available_improvements(self.TEST_PLAYER, test_settlement_high))

        # Now using a lower level settlement instead, we expect all returned improvements to have no pre-requisite for
        # their construction, and for the returned list to be sorted by construction cost.
        improvements: typing.List[Improvement] = get_available_improvements(self.TEST_PLAYER, test_settlement)
        self.assertTrue(all(imp.prereq is None for imp in improvements))
        self.assertTrue(all(improvements[i].cost <= improvements[i + 1].cost for i in range(len(improvements) - 1)))

        # If we now add a blessing to the test player, we expect there to be an improvement returned with the very same
        # pre-requisite. Once again, we expect the list to be sorted.
        self.TEST_PLAYER.blessings.append(self.TEST_BLESSING)
        improvements = get_available_improvements(self.TEST_PLAYER, test_settlement)
        self.assertTrue(any(imp.prereq is not None for imp in improvements))
        self.assertTrue(all(improvements[i].cost <= improvements[i + 1].cost for i in range(len(improvements) - 1)))

        # Lastly, if we add an improvement to the settlement, we expect there to be one less improvement available in
        # comparison to the previous retrieval. The list should still be sorted, too.
        test_settlement.improvements.append(self.TEST_IMPROVEMENT)
        new_improvements = get_available_improvements(self.TEST_PLAYER, test_settlement)
        self.assertLess(len(new_improvements), len(improvements))
        self.assertTrue(all(improvements[i].cost <= improvements[i + 1].cost for i in range(len(improvements) - 1)))

    def test_get_available_blessings(self):
        """
        Ensure that the available blessings for a player are correctly determined.
        """
        # To begin with, the player should be able to undertake any of the entire list of blessings, in a sorted order.
        blessings = get_available_blessings(self.TEST_PLAYER)
        self.assertEqual(len(BLESSINGS), len(blessings))
        self.assertTrue(all(blessings[i].cost <= blessings[i + 1].cost for i in range(len(blessings) - 1)))

        # Now if we give the player a blessing, when retrieved again, there should be one less, while still being
        # sorted.
        self.TEST_PLAYER.blessings.append(self.TEST_BLESSING)
        new_blessings = get_available_blessings(self.TEST_PLAYER)
        self.assertEqual(len(BLESSINGS) - 1, len(new_blessings))
        self.assertTrue(all(new_blessings[i].cost <= new_blessings[i + 1].cost for i in range(len(new_blessings) - 1)))

        # If we change the player's faction to be the Godless, who incur blessing penalties, the returned blessings
        # should still be the same, but their costs should be increased.
        self.TEST_PLAYER.faction = Faction.GODLESS
        godless_blessings = get_available_blessings(self.TEST_PLAYER)
        self.assertEqual(len(new_blessings), len(godless_blessings))
        self.assertTrue(all(godless_blessings[i].cost > new_blessings[i].cost for i in range(len(godless_blessings))))

    def test_get_unlockable(self):
        """
        Ensure that the returned unlockable improvements and unit plans for a blessing all really do require the
        supplied blessing as a pre-requisite.
        """
        unlockable = get_all_unlockable(self.TEST_BLESSING)
        self.assertTrue(unlockable)
        self.assertTrue(all(unlocked.prereq is not None for unlocked in unlockable))
        self.assertTrue(all(unlocked.prereq == self.TEST_BLESSING for unlocked in unlockable))

    def test_get_models(self):
        """
        Ensure that improvements, projects, blessings, and unit plans can be successfully retrieved by name.
        """
        test_project = PROJECTS[0]
        test_unit_plan = UNIT_PLANS[0]

        self.assertEqual(self.TEST_IMPROVEMENT, get_improvement(self.TEST_IMPROVEMENT.name))
        self.assertEqual(test_project, get_project(test_project.name))
        self.assertEqual(self.TEST_BLESSING, get_blessing(self.TEST_BLESSING.name))
        self.assertEqual(test_unit_plan, get_unit_plan(test_unit_plan.name))


if __name__ == '__main__':
    unittest.main()
