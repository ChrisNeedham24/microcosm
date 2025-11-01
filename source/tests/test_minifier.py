import unittest
from copy import deepcopy
from datetime import datetime, timezone
from typing import Set, List

from source.foundation.catalogue import BLESSINGS, IMPROVEMENTS, UNIT_PLANS, PROJECTS
from source.foundation.models import ResourceCollection, Quad, Biome, UnitPlan, Unit, DeployerUnit, Improvement, \
    Settlement, HarvestStatus, EconomicStatus, Construction, Project, ProjectType, Player, Faction, VictoryType, \
    OngoingBlessing, AIPlaystyle, AttackPlaystyle, ExpansionPlaystyle, Heathen, SaveDetails, Location
from source.util.minifier import minify_resource_collection, minify_quad, minify_unit_plan, minify_unit, \
    minify_improvement, minify_settlement, minify_player, minify_quads_seen, minify_heathens, \
    inflate_resource_collection, inflate_quad, inflate_unit_plan, inflate_unit, inflate_improvement, \
    inflate_settlement, inflate_player, inflate_quads_seen, inflate_heathens, minify_save_details, inflate_save_details


class MinifierTest(unittest.TestCase):
    """
    The test class for minifier.py.
    """

    # Below we declare a number of test models, along with their expected minified equivalents. These are used for both
    # minification and inflation tests.

    TEST_RESOURCE_COLLECTION: ResourceCollection = \
        ResourceCollection(ore=1, timber=2, magma=3, aurora=4, bloodstone=5, obsidian=6, sunstone=7, aquamarine=8)
    MINIFIED_RESOURCE_COLLECTION: str = "1+2+3+4+5+6+7+8"
    TEST_UNIT_PLAN: UnitPlan = UNIT_PLANS[0]
    MINIFIED_UNIT_PLAN: str = "100.0/100.0/3/25.0/Warrior"
    TEST_IMPROVEMENT: Improvement = IMPROVEMENTS[-1]
    MINIFIED_IMPROVEMENT: str = "HS"
    TEST_UNIT: Unit = Unit(10.0, 20, (30, 40), False, TEST_UNIT_PLAN, has_acted=True, besieging=True)
    TEST_GARRISONED_UNIT: Unit = Unit(10.0, 20, (30, 40), True, TEST_UNIT_PLAN, has_acted=True, besieging=True)
    MINIFIED_UNIT: str = f"10.0|20|30-40|{MINIFIED_UNIT_PLAN}|True|True"
    # Yes, technically the unit plan used here isn't one for a deployer, but it doesn't matter in this case.
    TEST_DEPLOYER_UNIT: DeployerUnit = DeployerUnit(50.0, 60, (70, 80), False, TEST_UNIT_PLAN, True, True,
                                                    passengers=[TEST_UNIT])
    MINIFIED_DEPLOYER_UNIT: str = f"50.0|60|70-80|{MINIFIED_UNIT_PLAN}|True|True|{MINIFIED_UNIT}^"
    TEST_QUAD: Quad = Quad(Biome.DESERT, 1, 2, 3, 4, (0, 0))
    MINIFIED_QUAD: str = "D1234"
    TEST_HEATHEN_PLAN: UnitPlan = UnitPlan(10.0, 20.0, 30, "Forty", None, 0.0)
    # We don't actually need to have multiple heathens here because the joining comma is added even if there's only
    # the one.
    TEST_HEATHENS: List[Heathen] = [Heathen(50.0, 60, (70, 80), TEST_HEATHEN_PLAN, True)]
    MINIFIED_HEATHENS: str = "50.0*60*70-80*10.0*20.0*30*Forty*True,"
    TEST_LEGACY_SAVE_DETAILS: SaveDetails = SaveDetails(datetime(1992, 3, 4, 5, 6, 7), auto=False)
    MINIFIED_LEGACY_SAVE_DETAILS: str = "save-1992-03-04T05.06.07"
    TEST_LEGACY_AUTOSAVE_DETAILS: SaveDetails = SaveDetails(datetime(1993, 4, 5, 6, 7, 8), auto=True)
    MINIFIED_LEGACY_AUTOSAVE_DETAILS: str = "autosave-1993-04-05T06.07.08"

    def setUp(self):
        """
        Set up our test models that may change during the course of tests.
        """
        # We break a few rules here by having the same improvement, quad, and garrisoned unit copied twice. Obviously
        # this isn't exactly realistic, but we want to show how each are separated within the minified string when
        # multiple are present.
        self.TEST_SETTLEMENT: Settlement = \
            Settlement("Setl", (0, 0), [self.TEST_IMPROVEMENT] * 2, [self.TEST_QUAD] * 2, self.TEST_RESOURCE_COLLECTION,
                       [self.TEST_GARRISONED_UNIT] * 2, 150.0, 200.0, 60.0, None, 10, 1.5, HarvestStatus.PLENTIFUL,
                       EconomicStatus.BOOM, False, True)
        self.MINIFIED_SETTLEMENT: str = (f"Setl;0-0;{self.MINIFIED_IMPROVEMENT}${self.MINIFIED_IMPROVEMENT};0-0,0-0;"
                                         f"{self.MINIFIED_RESOURCE_COLLECTION};"
                                         f"{self.MINIFIED_UNIT},{self.MINIFIED_UNIT};"
                                         f"150.0;200.0;60.0;;10;1.5;PLENTIFUL;BOOM;False;True")
        self.TEST_QUAD_RESOURCE_RELIC: Quad = \
            Quad(Biome.DESERT, 1, 2, 3, 4, (5, 6), resource=self.TEST_RESOURCE_COLLECTION, is_relic=True)
        self.MINIFIED_QUAD_RESOURCE_RELIC: str = f"D1234{self.MINIFIED_RESOURCE_COLLECTION}ir"
        self.TEST_PLAYER: Player = Player("Ace", Faction.AGRICULTURISTS, 3, 1.0, [self.TEST_SETTLEMENT] * 2,
                                          [self.TEST_UNIT] * 2, [BLESSINGS["beg_spl"], BLESSINGS["div_arc"]],
                                          self.TEST_RESOURCE_COLLECTION, set(),
                                          {VictoryType.ELIMINATION, VictoryType.AFFLUENCE},
                                          OngoingBlessing(BLESSINGS["inh_luc"], 3.4),
                                          AIPlaystyle(AttackPlaystyle.AGGRESSIVE, ExpansionPlaystyle.HERMIT), 4, 8.9,
                                          False)
        self.MINIFIED_PLAYER: str = (f"Ace~Agriculturists~1.0~{self.MINIFIED_SETTLEMENT}!{self.MINIFIED_SETTLEMENT}~"
                                     f"{self.MINIFIED_UNIT}&{self.MINIFIED_UNIT}~Beginner Spells,Divine Architecture~"
                                     f"{self.MINIFIED_RESOURCE_COLLECTION}~AFFLUENCE,ELIMINATION~Inherent Luck>3.4~"
                                     f"AGGRESSIVE-HERMIT~4~8.9~False")
        # Note that we have to specify the time zone for the current saves to guarantee consistent epoch conversion.
        self.TEST_SAVE_DETAILS: SaveDetails = \
            SaveDetails(datetime(1990, 1, 2, 3, 4, 5, tzinfo=timezone.utc), auto=False,
                        turn=6, player_count=7, faction=Faction.GODLESS, multiplayer=False)
        self.MINIFIED_SAVE_DETAILS: str = "save_631249445_6_7_3"
        self.TEST_AUTOSAVE_DETAILS: SaveDetails = \
            SaveDetails(datetime(1991, 2, 3, 4, 5, 6, tzinfo=timezone.utc), auto=True,
                        turn=7, player_count=8, faction=None, multiplayer=True)
        self.MINIFIED_AUTOSAVE_DETAILS: str = "autosave_665553906_7_8_M"

    def test_minify_resource_collection(self):
        """
        Ensure that resource collections are correctly minified.
        """
        self.assertEqual(self.MINIFIED_RESOURCE_COLLECTION, minify_resource_collection(self.TEST_RESOURCE_COLLECTION))

    def test_minify_quad(self):
        """
        Ensure that quads are correctly minified.
        """
        # Since the quad initially doesn't have any resources or a relic, it should be minified to just its biome and
        # yield.
        self.assertEqual(self.MINIFIED_QUAD, minify_quad(self.TEST_QUAD))
        # However now that the quad has resources and a relic, the minified string should contain that information too.
        self.assertEqual(self.MINIFIED_QUAD_RESOURCE_RELIC, minify_quad(self.TEST_QUAD_RESOURCE_RELIC))

    def test_minify_unit_plan(self):
        """
        Ensure that unit plans are correctly minified.
        """
        self.assertEqual(self.MINIFIED_UNIT_PLAN, minify_unit_plan(self.TEST_UNIT_PLAN))

    def test_minify_unit(self):
        """
        Ensure that both standard and deployer units are correctly minified.
        """
        self.assertEqual(self.MINIFIED_UNIT, minify_unit(self.TEST_UNIT))
        # Whether a unit is garrisoned has no bearing on its minification.
        self.assertEqual(self.MINIFIED_UNIT, minify_unit(self.TEST_GARRISONED_UNIT))
        # We expect minified deployer units to include their passengers as well.
        self.assertEqual(self.MINIFIED_DEPLOYER_UNIT, minify_unit(self.TEST_DEPLOYER_UNIT))

    def test_minify_improvement(self):
        """
        Ensure that improvements are correctly minified.
        """
        self.assertEqual(self.MINIFIED_IMPROVEMENT, minify_improvement(self.TEST_IMPROVEMENT))

    def test_minify_settlement(self):
        """
        Ensure that settlements are correctly minified, with and without current work.
        """
        self.assertEqual(self.MINIFIED_SETTLEMENT, minify_settlement(self.TEST_SETTLEMENT))

        # For the below three cases, when the settlement is currently constructing an improvement, project, or unit
        # plan, we expect those details to be included as well. Note that with the expected strings, we can just replace
        # ';;' in the original string because that signifies that there was no current work.

        self.TEST_SETTLEMENT.current_work = Construction(self.TEST_IMPROVEMENT, zeal_consumed=1.1)
        expected_minification_improvement: str = \
            self.MINIFIED_SETTLEMENT.replace(";;", ";Improvement%Holy Sanctum%1.1;")
        self.assertEqual(expected_minification_improvement, minify_settlement(self.TEST_SETTLEMENT))

        self.TEST_SETTLEMENT.current_work = Construction(Project(ProjectType.ECONOMICAL, "Cash", ""), zeal_consumed=1.1)
        expected_minification_project: str = \
            self.MINIFIED_SETTLEMENT.replace(";;", ";Project%Cash%1.1;")
        self.assertEqual(expected_minification_project, minify_settlement(self.TEST_SETTLEMENT))

        self.TEST_SETTLEMENT.current_work = Construction(self.TEST_UNIT_PLAN, zeal_consumed=1.1)
        expected_minification_unit_plan: str = \
            self.MINIFIED_SETTLEMENT.replace(";;", ";UnitPlan%Warrior%1.1;")
        self.assertEqual(expected_minification_unit_plan, minify_settlement(self.TEST_SETTLEMENT))

    def test_minify_player(self):
        """
        Ensure that players are correctly minified.
        """
        self.assertEqual(self.MINIFIED_PLAYER, minify_player(self.TEST_PLAYER))

    def test_minify_quads_seen(self):
        """
        Ensure that sets of seen quads are correctly minified.
        """
        test_quads_seen: Set[Location] = {(1, 2), (3, 4), (5, 6), (-1, 7), (8, -1)}
        # We expect the tuples with negative values to have been excluded.
        expected_minification: str = "1-2,3-4,5-6"
        self.assertEqual(expected_minification, minify_quads_seen(test_quads_seen))

    def test_minify_heathens(self):
        """
        Ensure that heathens are correctly minified.
        """
        self.assertEqual(self.MINIFIED_HEATHENS, minify_heathens(self.TEST_HEATHENS))

    def test_minify_save_details(self):
        """
        Ensure that SaveDetails objects are correctly minified.
        """
        # Case 1: A current manual save.
        self.assertEqual(self.MINIFIED_SAVE_DETAILS, minify_save_details(self.TEST_SAVE_DETAILS))
        # Case 2: A current multiplayer autosave.
        self.assertEqual(self.MINIFIED_AUTOSAVE_DETAILS, minify_save_details(self.TEST_AUTOSAVE_DETAILS))
        # Case 3: A legacy manual save.
        self.assertEqual(self.MINIFIED_LEGACY_SAVE_DETAILS, minify_save_details(self.TEST_LEGACY_SAVE_DETAILS))
        # Case 4: A legacy autosave.
        self.assertEqual(self.MINIFIED_LEGACY_AUTOSAVE_DETAILS, minify_save_details(self.TEST_LEGACY_AUTOSAVE_DETAILS))

    def test_inflate_resource_collection(self):
        """
        Ensure that resource collections are correctly inflated.
        """
        self.assertEqual(self.TEST_RESOURCE_COLLECTION, inflate_resource_collection(self.MINIFIED_RESOURCE_COLLECTION))

    def test_inflate_quad(self):
        """
        Ensure that quads are correctly inflated.
        """
        # The standard quad with no resources or relic.
        self.assertEqual(self.TEST_QUAD, inflate_quad(self.MINIFIED_QUAD, self.TEST_QUAD.location))
        # The quad with both resources and a relic.
        self.assertEqual(self.TEST_QUAD_RESOURCE_RELIC,
                         inflate_quad(self.MINIFIED_QUAD_RESOURCE_RELIC, self.TEST_QUAD_RESOURCE_RELIC.location))
        # For coverage purposes, we also validate quads of different biomes by changing the quad's biome and replacing
        # the first character of the minified string.
        self.TEST_QUAD_RESOURCE_RELIC.biome = Biome.FOREST
        self.assertEqual(self.TEST_QUAD_RESOURCE_RELIC,
                         inflate_quad(f"F{self.MINIFIED_QUAD_RESOURCE_RELIC[1:]}",
                                      self.TEST_QUAD_RESOURCE_RELIC.location))
        self.TEST_QUAD_RESOURCE_RELIC.biome = Biome.SEA
        self.assertEqual(self.TEST_QUAD_RESOURCE_RELIC,
                         inflate_quad(f"S{self.MINIFIED_QUAD_RESOURCE_RELIC[1:]}",
                                      self.TEST_QUAD_RESOURCE_RELIC.location))
        self.TEST_QUAD_RESOURCE_RELIC.biome = Biome.MOUNTAIN
        self.assertEqual(self.TEST_QUAD_RESOURCE_RELIC,
                         inflate_quad(f"M{self.MINIFIED_QUAD_RESOURCE_RELIC[1:]}",
                                      self.TEST_QUAD_RESOURCE_RELIC.location))

    def test_inflate_unit_plan(self):
        """
        Ensure that unit plans are correctly inflated.
        """
        self.assertEqual(self.TEST_UNIT_PLAN, inflate_unit_plan(self.MINIFIED_UNIT_PLAN, Faction.AGRICULTURISTS))

    def test_inflate_unit(self):
        """
        Ensure that units are correctly inflated.
        """
        # The standard unit.
        self.assertEqual(self.TEST_UNIT,
                         inflate_unit(self.MINIFIED_UNIT, self.TEST_UNIT.garrisoned, Faction.AGRICULTURISTS))
        # The deployer unit, which has one passenger unit.
        self.assertEqual(self.TEST_DEPLOYER_UNIT, inflate_unit(self.MINIFIED_DEPLOYER_UNIT,
                                                               self.TEST_DEPLOYER_UNIT.garrisoned,
                                                               Faction.AGRICULTURISTS))

    def test_inflate_improvement(self):
        """
        Ensure that improvements are correctly inflated.
        """
        self.assertEqual(self.TEST_IMPROVEMENT, inflate_improvement(self.MINIFIED_IMPROVEMENT))

    def test_inflate_settlement(self):
        """
        Ensure that settlements are correctly inflated.
        """
        self.assertEqual(self.TEST_SETTLEMENT, inflate_settlement(self.MINIFIED_SETTLEMENT,
                                                                  quads=[[self.TEST_QUAD]],
                                                                  faction=Faction.AGRICULTURISTS))

        # For the below three cases, when the settlement is currently constructing an improvement, project, or unit
        # plan, we expect those details to be transferred to the Settlement object as well. Note that with the expected
        # strings, we can just replace ';;' in the original string because that signifies that there was no current
        # work.

        self.TEST_SETTLEMENT.current_work = Construction(self.TEST_IMPROVEMENT, zeal_consumed=1.1)
        minified_setl_improvement: str = \
            self.MINIFIED_SETTLEMENT.replace(";;", ";Improvement%Holy Sanctum%1.1;")
        self.assertEqual(self.TEST_SETTLEMENT, inflate_settlement(minified_setl_improvement,
                                                                  quads=[[self.TEST_QUAD]],
                                                                  faction=Faction.AGRICULTURISTS))

        self.TEST_SETTLEMENT.current_work = Construction(PROJECTS[1], zeal_consumed=1.1)
        minified_setl_project: str = \
            self.MINIFIED_SETTLEMENT.replace(";;", ";Project%Inflation by Design%1.1;")
        self.assertEqual(self.TEST_SETTLEMENT, inflate_settlement(minified_setl_project,
                                                                  quads=[[self.TEST_QUAD]],
                                                                  faction=Faction.AGRICULTURISTS))

        # Because our test settlement has five bloodstone, the power and max health of the inflated unit under
        # construction is scaled.
        scaled_unit_plan: UnitPlan = deepcopy(self.TEST_UNIT_PLAN)
        scaled_unit_plan.power *= (1 + self.TEST_RESOURCE_COLLECTION.bloodstone * 0.5)
        scaled_unit_plan.max_health *= (1 + self.TEST_RESOURCE_COLLECTION.bloodstone * 0.5)
        self.TEST_SETTLEMENT.current_work = Construction(scaled_unit_plan, zeal_consumed=1.1)
        minified_setl_unit_plan: str = \
            self.MINIFIED_SETTLEMENT.replace(";;", ";UnitPlan%Warrior%1.1;")
        self.assertEqual(self.TEST_SETTLEMENT, inflate_settlement(minified_setl_unit_plan,
                                                                  quads=[[self.TEST_QUAD]],
                                                                  faction=Faction.AGRICULTURISTS))

    def test_inflate_player(self):
        """
        Ensure that players are correctly inflated.
        """
        self.assertEqual(self.TEST_PLAYER, inflate_player(self.MINIFIED_PLAYER, quads=[[self.TEST_QUAD]]))

    def test_inflate_quads_seen(self):
        """
        Ensure that seen quads are correctly inflated.
        """
        test_minified_quads_seen: str = "1-2,3-4,5-6"
        expected_quads_seen: Set[Location] = {(1, 2), (3, 4), (5, 6)}
        self.assertSetEqual(expected_quads_seen, inflate_quads_seen(test_minified_quads_seen))

    def test_inflate_heathens(self):
        """
        Ensure that heathens are correctly inflated.
        """
        self.assertListEqual(self.TEST_HEATHENS, inflate_heathens(self.MINIFIED_HEATHENS))

    def test_inflate_save_details(self):
        """
        Ensure that SaveDetails objects are correctly inflated.
        """
        def strip_tzinfo(save: SaveDetails):
            """
            Remove the datetime tzinfo for the given save. We need to do this for current saves because they have UTC
            specified as their time zone, in order to guarantee consistent epoch conversion.
            """
            save.date_time = save.date_time.replace(tzinfo=None)

        # Case 1: A current manual save.
        self.assertEqual(strip_tzinfo(self.TEST_SAVE_DETAILS),
                         strip_tzinfo(inflate_save_details(self.MINIFIED_SAVE_DETAILS, auto=False)))
        # Case 2: A current multiplayer autosave.
        self.assertEqual(strip_tzinfo(self.TEST_AUTOSAVE_DETAILS),
                         strip_tzinfo(inflate_save_details(self.MINIFIED_AUTOSAVE_DETAILS, auto=True)))
        # Case 3: A legacy manual save.
        self.assertEqual(self.TEST_LEGACY_SAVE_DETAILS,
                         inflate_save_details(self.MINIFIED_LEGACY_SAVE_DETAILS, auto=False))
        # Case 4: A legacy autosave.
        self.assertEqual(self.TEST_LEGACY_AUTOSAVE_DETAILS,
                         inflate_save_details(self.MINIFIED_LEGACY_AUTOSAVE_DETAILS, auto=True))
        # Case 5: A formatted legacy name from a multiplayer game server.
        save_name: str = "2077-07-07 07.07.07 (auto)"
        expected_save_details: SaveDetails = SaveDetails(datetime(2077, 7, 7, 7, 7, 7), auto=True)
        self.assertEqual(expected_save_details, inflate_save_details(save_name, auto=True))


if __name__ == '__main__':
    unittest.main()
