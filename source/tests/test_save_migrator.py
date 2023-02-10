import unittest

from source.foundation.models import UnitPlan
from source.saving.save_encoder import ObjectConverter
from source.saving.save_migrator import migrate_unit_plan


class SaveMigratorTest(unittest.TestCase):
    def test_unit_plan(self):
        test_power = 100
        test_max_health = 200
        test_total_stamina = 4
        test_name = "Bob"
        test_cost = 350

        test_loaded_plan: ObjectConverter = ObjectConverter({
            "power": test_power,
            "max_health": test_max_health,
            "total_stamina": test_total_stamina,
            "name": test_name,
            "prereq": None,
            "cost": test_cost,
            "can_settle": False,
            "heals": True
        })

        migrated_plan: UnitPlan = migrate_unit_plan(test_loaded_plan)

        self.assertEqual(test_power, migrated_plan.power)
        self.assertEqual(test_max_health, migrated_plan.max_health)
        self.assertEqual(test_total_stamina, migrated_plan.total_stamina)
        self.assertEqual(test_name, migrated_plan.name)
        self.assertIsNone(migrated_plan.prereq)
        self.assertEqual(test_cost, migrated_plan.cost)
        self.assertFalse(migrated_plan.can_settle)
        self.assertTrue(migrated_plan.heals)

        delattr(test_loaded_plan, "heals")

        outdated_plan: UnitPlan = migrate_unit_plan(test_loaded_plan)
        self.assertFalse(outdated_plan.heals)



if __name__ == '__main__':
    unittest.main()
