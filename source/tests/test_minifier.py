import unittest

from source.foundation.models import ResourceCollection, Quad, Biome, UnitPlan, Unit, DeployerUnit, Improvement, \
    ImprovementType, Effect, Settlement, HarvestStatus, EconomicStatus, Construction, Project, ProjectType
from source.util.minifier import minify_resource_collection, minify_quad, minify_unit_plan, minify_unit, \
    minify_improvement, minify_settlement


class MinifierTest(unittest.TestCase):
    """
    The test class for minifier.py.
    """
    TEST_RESOURCE_COLLECTION: ResourceCollection = \
        ResourceCollection(ore=1, timber=2, magma=3, aurora=4, bloodstone=5, obsidian=6, sunstone=7, aquamarine=8)
    MINIFIED_RESOURCE_COLLECTION: str = "1+2+3+4+5+6+7+8"
    TEST_UNIT_PLAN: UnitPlan = UnitPlan(10, 20, 30, "Forty", None, 0)
    MINIFIED_UNIT_PLAN: str = "10/20/30/Forty"
    TEST_IMPROVEMENT: Improvement = Improvement(ImprovementType.MAGICAL, 0, "A big Castle dome", "", Effect(), None)
    MINIFIED_IMPROVEMENT: str = "AbCd"
    TEST_UNIT: Unit = Unit(10, 20, (30, 40), False, TEST_UNIT_PLAN, has_acted=True, besieging=True)
    MINIFIED_UNIT: str = f"10|20|30-40|{MINIFIED_UNIT_PLAN}|True|True"

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
        test_quad: Quad = Quad(Biome.DESERT, 1, 2, 3, 4, (5, 6))
        expected_minification: str = "D1234"
        self.assertEqual(expected_minification, minify_quad(test_quad))

        # However now that the quad has resources and a relic, the minified string should contain that information too.
        test_quad = Quad(Biome.DESERT, 1, 2, 3, 4, (5, 6), resource=self.TEST_RESOURCE_COLLECTION, is_relic=True)
        expected_minification: str = f"D1234{self.MINIFIED_RESOURCE_COLLECTION}ir"
        self.assertEqual(expected_minification, minify_quad(test_quad))

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

        # Yes, technically this unit plan isn't one for a deployer, but it doesn't matter in this case.
        test_deployer_unit: DeployerUnit = DeployerUnit(50, 60, (70, 80), False, self.TEST_UNIT_PLAN, True, True,
                                                        passengers=[self.TEST_UNIT])
        # We expect minified deployer units to include their passengers as well.
        expected_deployer_minification: str = \
            f"50|60|70-80|{self.MINIFIED_UNIT_PLAN}|True|True|{self.MINIFIED_UNIT}^"
        self.assertEqual(expected_deployer_minification, minify_unit(test_deployer_unit))

    def test_minify_improvement(self):
        """
        Ensure that improvements are correctly minified.
        """
        self.assertEqual(self.MINIFIED_IMPROVEMENT, minify_improvement(self.TEST_IMPROVEMENT))

    def test_minify_settlement(self):
        """
        Ensure that settlements are correctly minified, with and without current work.
        """
        test_quad: Quad = Quad(Biome.MOUNTAIN, 0, 0, 0, 0, (1, 2))
        # We break a few rules here by having the same improvement, quad, and unit copied twice. Obviously this isn't
        # realistic, but we want to show how each are separated within the minified string when multiple are present.
        test_settlement: Settlement = \
            Settlement("Setl", (1, 2), [self.TEST_IMPROVEMENT, self.TEST_IMPROVEMENT], [test_quad, test_quad],
                       self.TEST_RESOURCE_COLLECTION, [self.TEST_UNIT, self.TEST_UNIT], 150, 200, 60, None, 10, 1.5,
                       HarvestStatus.PLENTIFUL, EconomicStatus.BOOM, False, True)
        expected_minification: str = (f"Setl;1-2;{self.MINIFIED_IMPROVEMENT}${self.MINIFIED_IMPROVEMENT};1-2,1-2;"
                                      f"{self.MINIFIED_RESOURCE_COLLECTION};{self.MINIFIED_UNIT},{self.MINIFIED_UNIT};"
                                      f"150;200;60;;10;1.5;PLENTIFUL;BOOM;False;True")
        self.assertEqual(expected_minification, minify_settlement(test_settlement))

        # For the below three cases, when the settlement is currently constructing an improvement, project, or unit
        # plan, we expect those details to be included as well. Note that with the expected strings, we can just replace
        # ';;' in the original string because that signifies that there was no current work.

        test_settlement.current_work = Construction(self.TEST_IMPROVEMENT, zeal_consumed=1.1)
        expected_minification_improvement: str = \
            expected_minification.replace(";;", ";Improvement%A big Castle dome%1.1;")
        self.assertEqual(expected_minification_improvement, minify_settlement(test_settlement))

        test_settlement.current_work = Construction(Project(ProjectType.ECONOMICAL, "Cash", ""), zeal_consumed=1.1)
        expected_minification_project: str = \
            expected_minification.replace(";;", ";Project%Cash%1.1;")
        self.assertEqual(expected_minification_project, minify_settlement(test_settlement))

        test_settlement.current_work = Construction(self.TEST_UNIT_PLAN, zeal_consumed=1.1)
        expected_minification_unit_plan: str = \
            expected_minification.replace(";;", ";UnitPlan%Forty%1.1;")
        self.assertEqual(expected_minification_unit_plan, minify_settlement(test_settlement))


if __name__ == '__main__':
    unittest.main()
