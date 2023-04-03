import typing
import unittest

from source.foundation.catalogue import Namer, SETL_NAMES, get_heathen_plan, get_heathen, UNIT_PLANS, \
    get_default_unit, get_available_improvements, BLESSINGS, IMPROVEMENTS, get_available_blessings, \
    get_all_unlockable, get_improvement, PROJECTS, get_project, get_blessing, get_unit_plan, get_available_unit_plans
from source.foundation.models import Biome, UnitPlan, Heathen, Unit, Player, Faction, Settlement, Improvement


class CatalogueTest(unittest.TestCase):
    """
    The test class for catalogue.py.
    """
    TEST_BLESSING = BLESSINGS["beg_spl"]
    TEST_IMPROVEMENT = IMPROVEMENTS[0]

    def setUp(self) -> None:
        """
        Initialise the test players before each test.
        """
        self.TEST_PLAYER = Player("Frontiersman", Faction.FRONTIERSMEN, 0)
        self.TEST_PLAYER_2 = Player("Farmer Man", Faction.AGRICULTURISTS, 0)

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

    def test_get_available_unit_plans_concentrated(self):
        """
        Ensure that players of the Concentrated faction do not have settler units available even if the settlement is
        above level 1.
        """
        test_player = Player("Concentrate Man", Faction.CONCENTRATED, 0)
        unit_plans: typing.List[UnitPlan] = get_available_unit_plans(test_player, 2)
        self.assertTrue(all(not up.can_settle for up in unit_plans))

    def test_get_available_unit_plans_low_level(self):
        """
        Ensure that level 1 settlements do not have settler units available.
        """
        unit_plans: typing.List[UnitPlan] = get_available_unit_plans(self.TEST_PLAYER, 1)
        self.assertTrue(all(not up.can_settle for up in unit_plans))

    def test_get_available_unit_plans_frontiersmen(self):
        """
        Ensure that players of the Frontiersmen faction have only settler units available once settlements exceed level
        5.
        """
        self.assertFalse(all(up.can_settle for up in get_available_unit_plans(self.TEST_PLAYER, 3)))
        self.assertTrue(all(up.can_settle for up in get_available_unit_plans(self.TEST_PLAYER, 6)))

    def test_get_available_unit_plans_imperials(self):
        """
        Ensure that players of the Imperials faction have units with higher power available.
        """
        imperial_player = Player("Empire Man", Faction.IMPERIALS, 0)

        # We compare the Imperial units with units for a player of the Agriculturists faction, which has no bonuses or
        # penalties applied. Also note that the settlement levels are the same.
        standard_plans: typing.List[UnitPlan] = get_available_unit_plans(self.TEST_PLAYER_2, 10)
        imperial_plans: typing.List[UnitPlan] = get_available_unit_plans(imperial_player, 10)

        # The unit plans should be identical bar the power difference.
        self.assertEqual(len(standard_plans), len(imperial_plans))
        for standard_plan, imperial_plan in zip(standard_plans, imperial_plans):
            self.assertEqual(imperial_plan.power, 1.5 * standard_plan.power)
            self.assertEqual(imperial_plan.max_health, standard_plan.max_health)
            self.assertEqual(imperial_plan.total_stamina, standard_plan.total_stamina)

    def test_get_available_unit_plans_persistent(self):
        """
        Ensure that players of The Persistent faction have units with increased health and reduced power available.
        """
        persistent_player = Player("Persistence Man", Faction.PERSISTENT, 0)

        # We compare The Persistent units with units for a player of the Agriculturists faction, which has no bonuses or
        # penalties applied. Also note that the settlement levels are the same.
        standard_plans: typing.List[UnitPlan] = get_available_unit_plans(self.TEST_PLAYER_2, 10)
        persistent_plans: typing.List[UnitPlan] = get_available_unit_plans(persistent_player, 10)

        # The unit plans should be identical bar the power and health differences.
        self.assertEqual(len(standard_plans), len(persistent_plans))
        for standard_plan, persistent_plan in zip(standard_plans, persistent_plans):
            self.assertEqual(persistent_plan.power, 0.75 * standard_plan.power)
            self.assertEqual(persistent_plan.max_health, 1.5 * standard_plan.max_health)
            self.assertEqual(persistent_plan.total_stamina, standard_plan.total_stamina)

    def test_get_available_unit_plans_explorers(self):
        """
        Ensure that players of the Explorers faction have units with increased stamina and reduced health available.
        """
        explorer_player = Player("Exploration Man", Faction.EXPLORERS, 0)

        # We compare the Explorer units with units for a player of the Agriculturists faction, which has no bonuses or
        # penalties applied. Also note that the settlement levels are the same.
        standard_plans: typing.List[UnitPlan] = get_available_unit_plans(self.TEST_PLAYER_2, 10)
        explorer_plans: typing.List[UnitPlan] = get_available_unit_plans(explorer_player, 10)

        # The unit plans should be identical bar the health and stamina differences.
        self.assertEqual(len(standard_plans), len(explorer_plans))
        for standard_plan, explorer_plan in zip(standard_plans, explorer_plans):
            self.assertEqual(explorer_plan.power, standard_plan.power)
            self.assertEqual(explorer_plan.max_health, 0.75 * standard_plan.max_health)
            self.assertEqual(explorer_plan.total_stamina, round(1.5 * standard_plan.total_stamina))

    def test_get_available_unit_plans(self):
        """
        Ensure that the available unit plans for a player of a faction with no penalties or bonuses are returned
        correctly, taking plan pre-requisites and sorting into account.
        """
        initial_unit_plans: typing.List[UnitPlan] = get_available_unit_plans(self.TEST_PLAYER_2, 5)
        # Since the player has no blessings, all of the returned plans should have no pre-requisite.
        self.assertTrue(all(up.prereq is None for up in initial_unit_plans))
        # The plans should also be sorted by cost in ascending order.
        self.assertTrue(all(initial_unit_plans[i].cost <= initial_unit_plans[i + 1].cost
                            for i in range(len(initial_unit_plans) - 1)))

        # Add a test blessing to unlock some new unit plans.
        self.TEST_PLAYER_2.blessings.append(self.TEST_BLESSING)
        new_unit_plans: typing.List[UnitPlan] = get_available_unit_plans(self.TEST_PLAYER_2, 5)
        # Following the addition of the blessing, the player should now have new plans available with the blessing as
        # their pre-requisite, while still being sorted.
        self.assertLess(len(initial_unit_plans), len(new_unit_plans))
        self.assertTrue(any(up.prereq == self.TEST_BLESSING for up in new_unit_plans))
        self.assertTrue(all(new_unit_plans[i].cost <= new_unit_plans[i + 1].cost
                            for i in range(len(new_unit_plans) - 1)))

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
