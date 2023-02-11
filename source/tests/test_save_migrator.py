import unittest

import pyxel

from source.foundation.catalogue import UNIT_PLANS
from source.foundation.models import UnitPlan, Unit, AttackPlaystyle, ExpansionPlaystyle, VictoryType, Faction, \
    Settlement, Biome, Quad
from source.game_management.game_state import GameState
from source.saving.save_encoder import ObjectConverter
from source.saving.save_migrator import migrate_unit_plan, migrate_unit, migrate_player, migrate_climatic_effects, \
    migrate_quad


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

    def test_unit(self):
        test_health = 300
        test_remaining_stamina = 3
        test_location = [1, 2]

        test_loaded_unit: ObjectConverter = ObjectConverter({
            "health": test_health,
            "remaining_stamina": test_remaining_stamina,
            "location": test_location,
            "garrisoned": False,
            "plan": UNIT_PLANS[0],
            "has_acted": True,
            "besieging": False
        })

        migrated_unit: Unit = migrate_unit(test_loaded_unit)

        self.assertEqual(test_health, migrated_unit.health)
        self.assertEqual(test_remaining_stamina, migrated_unit.remaining_stamina)
        self.assertTupleEqual((test_location[0], test_location[1]), migrated_unit.location)
        self.assertFalse(migrated_unit.garrisoned)
        self.assertEqual(UNIT_PLANS[0], migrated_unit.plan)
        self.assertTrue(migrated_unit.has_acted)
        self.assertFalse(migrated_unit.besieging)

        delattr(test_loaded_unit, "has_acted")
        delattr(test_loaded_unit, "besieging")
        test_loaded_unit.__dict__["has_attacked"] = True
        test_loaded_unit.__dict__["sieging"] = False

        outdated_unit: Unit = migrate_unit(test_loaded_unit)
        self.assertTrue(outdated_unit.has_acted)
        self.assertFalse(outdated_unit.besieging)

    def test_player(self):
        test_attack_playstyle = AttackPlaystyle.AGGRESSIVE.value
        test_expansion_playstyle = ExpansionPlaystyle.HERMIT.value
        test_imminent_victories = [VictoryType.SERENDIPITY.value]
        test_faction = Faction.FUNDAMENTALISTS.value

        test_loaded_ai_playstyle: ObjectConverter = ObjectConverter({
            "attacking": test_attack_playstyle,
            "expansion": test_expansion_playstyle
        })
        test_loaded_player: ObjectConverter = ObjectConverter({
            "ai_playstyle": test_loaded_ai_playstyle,
            "imminent_victories": test_imminent_victories,
            "faction": test_faction,
            "colour": pyxel.COLOR_ORANGE,
            "eliminated": False,
            "settlements": [Settlement("A", (1, 2), [], [], [])]
        })

        migrate_player(test_loaded_player)

        self.assertEqual(test_attack_playstyle, test_loaded_player.ai_playstyle.attacking)
        self.assertEqual(test_expansion_playstyle, test_loaded_player.ai_playstyle.expansion)
        self.assertSetEqual(set(test_imminent_victories), test_loaded_player.imminent_victories)
        self.assertEqual(test_faction, test_loaded_player.faction)

        test_loaded_player.__dict__["ai_playstyle"] = test_attack_playstyle
        delattr(test_loaded_player, "imminent_victories")
        delattr(test_loaded_player, "faction")
        delattr(test_loaded_player, "eliminated")

        migrate_player(test_loaded_player)

        self.assertEqual(test_attack_playstyle, test_loaded_player.ai_playstyle.attacking)
        self.assertEqual(ExpansionPlaystyle.NEUTRAL, test_loaded_player.ai_playstyle.expansion)
        self.assertSetEqual(set(), test_loaded_player.imminent_victories)
        self.assertEqual(test_faction, test_loaded_player.faction)
        self.assertFalse(test_loaded_player.eliminated)

    def test_climatic_effects(self):
        test_until_night = 3
        test_nighttime_left = 0

        test_loaded_night_status: ObjectConverter = ObjectConverter({
            "until": test_until_night,
            "remaining": test_nighttime_left
        })
        test_loaded_save: ObjectConverter = ObjectConverter({
            "night_status": test_loaded_night_status
        })
        test_game_state = GameState()

        migrate_climatic_effects(test_game_state, test_loaded_save)

        self.assertEqual(test_game_state.until_night, test_until_night)
        self.assertEqual(test_game_state.nighttime_left, test_nighttime_left)

        delattr(test_loaded_save, "night_status")

        migrate_climatic_effects(test_game_state, test_loaded_save)

        self.assertFalse(test_game_state.until_night)
        self.assertFalse(test_game_state.nighttime_left)

    def test_quad(self):
        test_biome = Biome.FOREST.value

        test_loaded_quad: ObjectConverter = ObjectConverter({
            "biome": test_biome,
            "is_relic": True
        })

        migrated_quad: Quad = migrate_quad(test_loaded_quad)

        self.assertEqual(test_biome, migrated_quad.biome)
        self.assertTrue(migrated_quad.is_relic)

        delattr(test_loaded_quad, "is_relic")

        outdated_quad: Quad = migrate_quad(test_loaded_quad)

        self.assertFalse(outdated_quad.is_relic)


if __name__ == '__main__':
    unittest.main()
