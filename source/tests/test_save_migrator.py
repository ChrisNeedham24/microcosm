import unittest

import pyxel

from source.foundation.catalogue import UNIT_PLANS, IMPROVEMENTS
from source.foundation.models import UnitPlan, Unit, AttackPlaystyle, ExpansionPlaystyle, VictoryType, Faction, \
    Settlement, Biome, Quad, GameConfig, DeployerUnitPlan, DeployerUnit, ResourceCollection
from source.game_management.game_state import GameState
from source.saving.save_encoder import ObjectConverter
from source.saving.save_migrator import migrate_unit_plan, migrate_unit, migrate_player, migrate_climatic_effects, \
    migrate_quad, migrate_settlement, migrate_game_config, migrate_game_version


class SaveMigratorTest(unittest.TestCase):
    """
    The test class for save_migrator.py.
    """

    def test_unit_plan(self):
        """
        Ensure that migrations occur correctly for UnitPlans.
        """
        test_power = 100.0
        test_max_health = 200.0
        test_total_stamina = 4
        test_name = "Bob"
        test_cost = 350.0

        # Simulate an up-to-date loaded unit plan.
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

        migrated_plan: UnitPlan = migrate_unit_plan(test_loaded_plan, Faction.AGRICULTURISTS)

        # For up-to-date unit plans, the attributes should all map across directly.
        self.assertEqual(test_power, migrated_plan.power)
        self.assertEqual(test_max_health, migrated_plan.max_health)
        self.assertEqual(test_total_stamina, migrated_plan.total_stamina)
        self.assertEqual(test_name, migrated_plan.name)
        self.assertIsNone(migrated_plan.prereq)
        self.assertEqual(test_cost, migrated_plan.cost)
        self.assertFalse(migrated_plan.can_settle)
        self.assertTrue(migrated_plan.heals)

        # Now delete the heals attribute, to simulate an outdated save.
        delattr(test_loaded_plan, "heals")

        outdated_plan: UnitPlan = migrate_unit_plan(test_loaded_plan, Faction.AGRICULTURISTS)
        # Old unit plans should be mapped to False.
        self.assertFalse(outdated_plan.heals)

    def test_deployer_unit_plan(self):
        """
        Ensure that migrations occur correctly for DeployerUnitPlans.
        """
        test_power = 100.0
        test_max_health = 200.0
        test_total_stamina = 4
        test_name = "Bob"
        test_cost = 350.0
        test_max_capacity = 7

        # Simulate a loaded deployer unit plan.
        test_loaded_plan: ObjectConverter = ObjectConverter({
            "power": test_power,
            "max_health": test_max_health,
            "total_stamina": test_total_stamina,
            "name": test_name,
            "prereq": None,
            "cost": test_cost,
            "can_settle": False,
            "heals": False,
            "max_capacity": test_max_capacity
        })

        migrated_plan: UnitPlan = migrate_unit_plan(test_loaded_plan, Faction.AGRICULTURISTS)

        # The attributes should all map across directly, and the right class should be used.
        self.assertTrue(isinstance(migrated_plan, DeployerUnitPlan))
        self.assertEqual(test_power, migrated_plan.power)
        self.assertEqual(test_max_health, migrated_plan.max_health)
        self.assertEqual(test_total_stamina, migrated_plan.total_stamina)
        self.assertEqual(test_name, migrated_plan.name)
        self.assertIsNone(migrated_plan.prereq)
        self.assertEqual(test_cost, migrated_plan.cost)
        self.assertFalse(migrated_plan.can_settle)
        self.assertFalse(migrated_plan.heals)
        self.assertEqual(test_max_capacity, migrated_plan.max_capacity)

    def test_unit(self):
        """
        Ensure that migrations occur correctly for Units.
        """
        test_health = 300.0
        test_remaining_stamina = 3
        test_location = [1, 2]

        # Simulate an up-to-date loaded unit.
        test_loaded_unit: ObjectConverter = ObjectConverter({
            "health": test_health,
            "remaining_stamina": test_remaining_stamina,
            "location": test_location,
            "garrisoned": False,
            "plan": UNIT_PLANS[0],
            "has_acted": True,
            "besieging": False
        })

        migrated_unit: Unit = migrate_unit(test_loaded_unit, Faction.AGRICULTURISTS)

        # For up-to-date units, the attributes should all map across directly.
        self.assertEqual(test_health, migrated_unit.health)
        self.assertEqual(test_remaining_stamina, migrated_unit.remaining_stamina)
        self.assertTupleEqual((test_location[0], test_location[1]), migrated_unit.location)
        self.assertFalse(migrated_unit.garrisoned)
        self.assertEqual(UNIT_PLANS[0], migrated_unit.plan)
        self.assertTrue(migrated_unit.has_acted)
        self.assertFalse(migrated_unit.besieging)

        # Now delete the has_acted and besieging attributes, replacing them with the outdated has_attacked and sieging
        # attributes.
        delattr(test_loaded_unit, "has_acted")
        delattr(test_loaded_unit, "besieging")
        test_loaded_unit.__dict__["has_attacked"] = True
        test_loaded_unit.__dict__["sieging"] = False

        outdated_unit: Unit = migrate_unit(test_loaded_unit, Faction.AGRICULTURISTS)
        # We expect the outdated attributes to be mapped to the new ones.
        self.assertTrue(outdated_unit.has_acted)
        self.assertFalse(outdated_unit.besieging)
        # We also expect that the old attributes are deleted.
        self.assertFalse(hasattr(outdated_unit, "has_attacked"))
        self.assertFalse(hasattr(outdated_unit, "sieging"))

    def test_deployer_unit(self):
        """
        Ensure that migrations occur correctly for DeployerUnits.
        """
        test_health = 300.0
        test_remaining_stamina = 3
        test_location = [1, 2]
        test_health_passenger = 600
        test_remaining_stamina_passenger = 4
        test_location_passenger = [3, 4]

        # Simulate a deployer unit.
        test_loaded_unit: ObjectConverter = ObjectConverter({
            "health": test_health,
            "remaining_stamina": test_remaining_stamina,
            "location": test_location,
            "garrisoned": False,
            "plan": UNIT_PLANS[-4],
            "has_acted": True,
            "besieging": False,
            "passengers": [ObjectConverter({
                "health": test_health_passenger,
                "remaining_stamina": test_remaining_stamina_passenger,
                "location": test_location_passenger,
                "garrisoned": False,
                "plan": UNIT_PLANS[0],
                "has_acted": True,
                "besieging": False,
            })]
        })

        migrated_unit: Unit = migrate_unit(test_loaded_unit, Faction.AGRICULTURISTS)

        # The attributes should all map across directly, and the right class should be used.
        self.assertTrue(isinstance(migrated_unit, DeployerUnit))
        self.assertEqual(test_health, migrated_unit.health)
        self.assertEqual(test_remaining_stamina, migrated_unit.remaining_stamina)
        self.assertTupleEqual((test_location[0], test_location[1]), migrated_unit.location)
        self.assertFalse(migrated_unit.garrisoned)
        self.assertEqual(UNIT_PLANS[-4], migrated_unit.plan)
        self.assertTrue(migrated_unit.has_acted)
        self.assertFalse(migrated_unit.besieging)
        self.assertEqual(1, len(migrated_unit.passengers))

        # The passenger unit should also have been successfully migrated.
        migrated_passenger: Unit = migrated_unit.passengers[0]
        self.assertEqual(test_health_passenger, migrated_passenger.health)
        self.assertEqual(test_remaining_stamina_passenger, migrated_passenger.remaining_stamina)
        self.assertTupleEqual((test_location_passenger[0], test_location_passenger[1]), migrated_passenger.location)
        self.assertFalse(migrated_passenger.garrisoned)
        self.assertEqual(UNIT_PLANS[0], migrated_passenger.plan)
        self.assertTrue(migrated_passenger.has_acted)
        self.assertFalse(migrated_passenger.besieging)

    def test_player(self):
        """
        Ensure that migrations occur correctly for players.
        """
        test_attack_playstyle = AttackPlaystyle.AGGRESSIVE.value
        test_expansion_playstyle = ExpansionPlaystyle.HERMIT.value
        test_imminent_victories = [VictoryType.SERENDIPITY.value]
        test_faction = Faction.FUNDAMENTALISTS.value

        # Simulate an up-to-date loaded AI playstyle, an up-to-date loaded resource collection, and an up-to-date loaded
        # player.
        test_loaded_ai_playstyle: ObjectConverter = ObjectConverter({
            "attacking": test_attack_playstyle,
            "expansion": test_expansion_playstyle
        })
        test_loaded_resources: ObjectConverter = ObjectConverter({
            "ore": 1,
            "timber": 2,
            "magma": 3,
            "aurora": 4,
            "bloodstone": 5,
            "obsidian": 6,
            "sunstone": 7,
            "aquamarine": 8
        })
        test_loaded_player: ObjectConverter = ObjectConverter({
            "ai_playstyle": test_loaded_ai_playstyle,
            "imminent_victories": test_imminent_victories,
            "faction": test_faction,
            "colour": pyxel.COLOR_ORANGE,
            "eliminated": False,
            "settlements": [Settlement("A", (1, 2), [], [], ResourceCollection(), [])],
            "resources": test_loaded_resources
        })

        migrate_player(test_loaded_player)

        # For up-to-date players, the attributes should all map across directly.
        self.assertEqual(test_attack_playstyle, test_loaded_player.ai_playstyle.attacking)
        self.assertEqual(test_expansion_playstyle, test_loaded_player.ai_playstyle.expansion)
        self.assertSetEqual(set(test_imminent_victories), test_loaded_player.imminent_victories)
        self.assertEqual(test_faction, test_loaded_player.faction)
        self.assertEqual(ResourceCollection(ore=1, timber=2, magma=3,
                                            aurora=4, bloodstone=5, obsidian=6, sunstone=7, aquamarine=8),
                         test_loaded_player.resources)

        # Now, convert the object to be like an outdated save, where AI playstyle only consisted of attacking, and the
        # imminent victories, faction, eliminated, and resources attributes did not exist.
        test_loaded_player.__dict__["ai_playstyle"] = test_attack_playstyle
        delattr(test_loaded_player, "imminent_victories")
        delattr(test_loaded_player, "faction")
        delattr(test_loaded_player, "eliminated")
        delattr(test_loaded_player, "resources")

        migrate_player(test_loaded_player)

        # We expect the attacking playstyle to be mapped across, and the expansion playstyle to be set to neutral.
        self.assertEqual(test_attack_playstyle, test_loaded_player.ai_playstyle.attacking)
        self.assertEqual(ExpansionPlaystyle.NEUTRAL, test_loaded_player.ai_playstyle.expansion)
        # Imminent victories should be initialised to an empty set, since it'll be populated next turn anyway.
        self.assertSetEqual(set(), test_loaded_player.imminent_victories)
        # The player's faction should have been determined based on the player's colour.
        self.assertEqual(test_faction, test_loaded_player.faction)
        # The player should not be eliminated, since they have a settlement.
        self.assertFalse(test_loaded_player.eliminated)
        # Lastly, the player should have an empty resource collection.
        self.assertEqual(ResourceCollection(), test_loaded_player.resources)

    def test_climatic_effects(self):
        """
        Ensure that migrations occur correctly for climatic effects.
        """
        test_until_night = 3
        test_nighttime_left = 0

        # Simulate an up-to-date loaded save.
        test_loaded_night_status: ObjectConverter = ObjectConverter({
            "until": test_until_night,
            "remaining": test_nighttime_left
        })
        test_loaded_save: ObjectConverter = ObjectConverter({
            "night_status": test_loaded_night_status
        })
        test_game_state = GameState()

        migrate_climatic_effects(test_game_state, test_loaded_save)

        # For up-to-date saves, the attributes should be mapped directly.
        self.assertEqual(test_game_state.until_night, test_until_night)
        self.assertEqual(test_game_state.nighttime_left, test_nighttime_left)

        # Now delete the night_status attribute, to simulate an outdated save from before the introduction of climatic
        # effects.
        delattr(test_loaded_save, "night_status")

        migrate_climatic_effects(test_game_state, test_loaded_save)

        # Since the day-night flow will not occur, we expect both to be initialised to zero.
        self.assertFalse(test_game_state.until_night)
        self.assertFalse(test_game_state.nighttime_left)

    def test_quad(self):
        """
        Ensure that migrations occur correctly for quads.
        """
        # TODO update to include minified format
        test_biome = Biome.FOREST.value

        # Simulate an up-to-date loaded resource collection and an up-to-date loaded quad.
        test_loaded_resource: ObjectConverter = ObjectConverter({
            "ore": 1,
            "timber": 0,
            "magma": 0,
            "aurora": 0,
            "bloodstone": 0,
            "obsidian": 0,
            "sunstone": 0,
            "aquamarine": 0
        })
        test_loaded_quad: ObjectConverter = ObjectConverter({
            "biome": test_biome,
            "is_relic": True,
            "location": [1, 2],
            "resource": test_loaded_resource,
            "wealth": 1,
            "harvest": 2,
            "zeal": 3,
            "fortune": 4
        })

        migrated_quad: Quad = migrate_quad(test_loaded_quad, (0, 0))

        # For up-to-date quads, we expect the attributes to be mapped over directly.
        self.assertEqual(test_biome, migrated_quad.biome)
        self.assertTrue(migrated_quad.is_relic)
        # Note that we passed in (0, 0) as the backup location, but since the save had the location, we don't need it.
        self.assertTupleEqual((1, 2), migrated_quad.location)
        self.assertEqual(ResourceCollection(ore=1), migrated_quad.resource)
        self.assertEqual(1, migrated_quad.wealth)
        self.assertEqual(2, migrated_quad.harvest)
        self.assertEqual(3, migrated_quad.zeal)
        self.assertEqual(4, migrated_quad.fortune)

        # Now if we delete the is_relic, location, and resource attributes, and use float values for the quad's yield,
        # we are replicating an outdated save.
        delattr(test_loaded_quad, "is_relic")
        delattr(test_loaded_quad, "location")
        delattr(test_loaded_quad, "resource")
        test_loaded_quad.wealth = 1.1
        test_loaded_quad.harvest = 1.5
        test_loaded_quad.zeal = 2.5
        test_loaded_quad.fortune = 3.7

        outdated_quad: Quad = migrate_quad(test_loaded_quad, (0, 0))

        # Even without the attribute, outdated quads should have is_relic set to False.
        self.assertFalse(outdated_quad.is_relic)
        # Similarly, the backup location passed through should be used instead.
        self.assertTupleEqual((0, 0), outdated_quad.location)
        self.assertIsNone(outdated_quad.resource)
        # We expect the quad's yield values to have been appropriately rounded as well.
        self.assertEqual(1, migrated_quad.wealth)
        self.assertEqual(2, migrated_quad.harvest)
        self.assertEqual(3, migrated_quad.zeal)
        self.assertEqual(4, migrated_quad.fortune)

    def test_settlement(self):
        """
        Ensure that migrations occur correctly for settlements.
        """
        # Simulate an outdated loaded settlement under siege.
        test_loaded_besieged_settlement: ObjectConverter = ObjectConverter({
            "under_siege_by": Unit(1, 2, (3, 4), False, UNIT_PLANS[0]),
            "location": [1, 2],
            "quads": [ObjectConverter({
                "biome": Biome.FOREST.value,
                "wealth": 1.1,
                "harvest": 2.2,
                "zeal": 3.3,
                "fortune": 4.4
            })]
        })

        migrate_settlement(test_loaded_besieged_settlement)

        # The besieged attribute should have been determined based on the outdated under_siege_by attribute, which
        # itself should also have been removed.
        self.assertTrue(test_loaded_besieged_settlement.besieged)
        self.assertFalse(hasattr(test_loaded_besieged_settlement, "under_siege_by"))
        # Since the settlement's quad did not have a specified location, it should have been given the location of the
        # settlement.
        self.assertTupleEqual((1, 2), test_loaded_besieged_settlement.quads[0].location)

        # Simulate an outdated loaded settlement that is not under siege.
        test_loaded_settlement = ObjectConverter({
            "under_siege_by": None,
            "location": [1, 2],
            "quads": [ObjectConverter({
                "biome": Biome.FOREST.value,
                "wealth": 1.1,
                "harvest": 2.2,
                "zeal": 3.3,
                "fortune": 4.4
            })]
        })

        migrate_settlement(test_loaded_settlement)

        # Once again, the besieged attribute should have been determined based on the under_siege_by attribute, which
        # itself should also have been removed.
        self.assertFalse(test_loaded_settlement.besieged)
        self.assertFalse(hasattr(test_loaded_settlement, "under_siege_by"))
        # Once again, the settlement's location should have been passed through to the quad.
        self.assertTupleEqual((1, 2), test_loaded_besieged_settlement.quads[0].location)
        self.assertEqual(ResourceCollection(), test_loaded_settlement.resources)

        # Lastly, simulate an up-to-date settlement with resources.
        test_loaded_resources: ObjectConverter = ObjectConverter({
            "ore": 1,
            "timber": 0,
            "magma": 2,
            "aurora": 0,
            "bloodstone": 0,
            "obsidian": 0,
            "sunstone": 1,
            "aquamarine": 0
        })
        test_loaded_settlement = ObjectConverter({
            "besieged": False,
            "location": [1, 2],
            "quads": [ObjectConverter({
                "biome": Biome.FOREST.value,
                "wealth": 1,
                "harvest": 2,
                "zeal": 3,
                "fortune": 4
            })],
            "resources": test_loaded_resources
        })

        migrate_settlement(test_loaded_settlement)

        self.assertEqual(ResourceCollection(ore=1, magma=2, sunstone=1), test_loaded_settlement.resources)

    def test_game_config(self):
        """
        Ensure that migrations occur correctly for game configuration.
        """
        test_player_count = 9

        # Simulate an outdated loaded game configuration.
        test_loaded_config: ObjectConverter = ObjectConverter({
            "player_count": test_player_count,
            "player_colour": pyxel.COLOR_ORANGE,
            "biome_clustering": True,
            "fog_of_war": True
        })

        outdated_config: GameConfig = migrate_game_config(test_loaded_config)

        # Since this save was from before the introduction of climatic effects and multiplayer, both should have been
        # mapped to False.
        self.assertFalse(outdated_config.climatic_effects)
        self.assertFalse(outdated_config.multiplayer)
        # The player faction should have been determined from the player_colour attribute, which should have been
        # deleted.
        self.assertEqual(Faction.FUNDAMENTALISTS, outdated_config.player_faction)
        self.assertFalse(hasattr(outdated_config, "player_colour"))
        # The other three unchanged attributes should have been mapped across directly.
        self.assertEqual(test_player_count, outdated_config.player_count)
        self.assertTrue(outdated_config.biome_clustering)
        self.assertTrue(outdated_config.fog_of_war)

    def test_game_version(self):
        """
        Ensure that migrations occur correctly for the game version.
        """
        test_game_version = 3.0
        test_old_version = 0.0

        # Simulate an up-to-date loaded save.
        test_loaded_save: ObjectConverter = ObjectConverter({
            "game_version": test_game_version
        })
        test_game_state = GameState()

        migrate_game_version(test_game_state, test_loaded_save)

        # For up-to-date saves, the attribute should be mapped directly.
        self.assertEqual(test_game_state.game_version, test_game_version)

        # Now simulate an older save that has since been loaded in, a few turns have been played, and then saved again.
        test_loaded_save: ObjectConverter = ObjectConverter({
            "game_version": test_old_version
        })
        test_game_state = GameState()

        migrate_game_version(test_game_state, test_loaded_save)

        # For older saves, all improvements should have their required resources removed, and the attribute should have
        # been set to 0.0, despite already being that value.
        self.assertTrue(all(imp.req_resources is None for imp in IMPROVEMENTS))
        self.assertEqual(test_game_state.game_version, test_old_version)

        # Now delete the game_version attribute, to simulate an outdated save from before the introduction of resources.
        delattr(test_loaded_save, "game_version")

        migrate_game_version(test_game_state, test_loaded_save)

        # For saves without a version altogether, we still expect the same changes to improvements, and for the version
        # to be set to 0.0.
        self.assertTrue(all(imp.req_resources is None for imp in IMPROVEMENTS))
        self.assertEqual(test_game_state.game_version, test_old_version)


if __name__ == '__main__':
    unittest.main()
