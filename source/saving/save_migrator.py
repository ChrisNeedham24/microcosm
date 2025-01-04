from source.foundation.catalogue import get_blessing, FACTION_COLOURS, IMPROVEMENTS
from source.foundation.models import UnitPlan, Unit, Faction, AIPlaystyle, AttackPlaystyle, ExpansionPlaystyle, Quad, \
    Biome, GameConfig, DeployerUnitPlan, DeployerUnit, ResourceCollection

"""
The following migrations have occurred during Microcosm's development:

v1.1
- AI players had their playstyle expanded to not only include attacking, but also expansion.
  This is migrated by mapping directly to the attacking attribute, and setting the expansion attribute to neutral.
- Relics were added, adding the is_relic attribute to Quads. This is migrated by setting all quads without the attribute
  to False.
- Imminent victories were added for players, telling players when they or others are close to winning the game. This can
  be migrated by simpling setting them to an empty set if the attribute is not present, as it will be populated next
  turn.
- The eliminated attribute was added for players, which can be determined by checking the number of settlements the
  player has.

v1.2
- Climatic effects were added to the game as a part of its configuration. This can be mapped to False, and night
  counters can be mapped to zero.

v2.0
- Factions were added for players. As it would be difficult for players to choose, their faction can be determined from
  the colour they chose.
- The player faction was also added to the game configuration, replacing player colour, which can be determined in the
  same way as above.

v2.2
- Healing units were added. All existing unit plans can be mapped to False for the heals attribute.
- The has_attacked attribute was changed to has_acted for units, and this can be directly mapped across.
- The sieging attribute for units was changed to besieging, and this can also be mapped directly.
- The under_siege_by attribute keeping track of the optional unit besieging the settlement was changed to a simple
  boolean attribute called besieged. Migration can occur by mapping to True if the value is not None.

v2.3
- The location of quads became recorded. All existing quads can be mapped to their index if they are for the board, or
  mapped to their settlement's location if they are for a settlement.

v2.4
- Deploying units and their plans were added. Since they had their own unique properties, no migration for existing
  units is required, and the new deploying units can be identified by these properties.

v3.0
- Resources were added, adding the resource attribute to Quads, and the resources attribute to Settlements and Players.
  These are migrated by setting Quads without the attribute to have None and Settlements and Players without the
  attribute to have empty ResourceCollections. In addition to these, the req_resources attribute was added to
  Improvements, which is migrated and removed for old saves, as they would have no way of obtaining the necessary
  resources.

v4.0
- Quad yields were adjusted to be integer values rather than float ones. Float values from previous versions are rounded
  to the closest integer.
- Multiplayer games were introduced; GameConfig objects from previous versions are naturally mapped to False.
"""


def migrate_unit_plan(unit_plan, faction: Faction) -> UnitPlan:
    """
    Apply the heals attribute migration for UnitPlans, if required.
    :param unit_plan: The loaded unit plan object.
    :param faction: The faction unit plan belongs to.
    :return: An optionally-migrated UnitPlan representation.
    """
    plan_prereq = None if unit_plan.prereq is None else get_blessing(unit_plan.prereq.name, faction)
    will_heal: bool = unit_plan.heals if hasattr(unit_plan, "heals") else False

    if hasattr(unit_plan, "max_capacity"):
        return DeployerUnitPlan(float(unit_plan.power), float(unit_plan.max_health), unit_plan.total_stamina,
                                unit_plan.name, plan_prereq, unit_plan.cost, unit_plan.can_settle, will_heal,
                                unit_plan.max_capacity)
    return UnitPlan(float(unit_plan.power), float(unit_plan.max_health), unit_plan.total_stamina, unit_plan.name,
                    plan_prereq, unit_plan.cost, unit_plan.can_settle, will_heal)


def migrate_unit(unit, faction: Faction) -> Unit:
    """
    Apply the has_attacked to has_acted and sieging to besieging migrations for Units, if required.
    :param unit: The loaded unit object.
    :param faction: The faction the unit belongs to.
    :return: An optionally-migrated Unit representation.
    """
    # Note for the below migrations that if we detect an outdated attribute, we migrate it and then delete it so that it
    # does not pollute future saves.
    will_have_acted: bool
    if hasattr(unit, "has_acted"):
        will_have_acted = unit.has_acted
    else:
        will_have_acted = unit.has_attacked
        delattr(unit, "has_attacked")
    will_be_besieging: bool
    if hasattr(unit, "besieging"):
        will_be_besieging = unit.besieging
    else:
        will_be_besieging = unit.sieging
        delattr(unit, "sieging")
    if hasattr(unit, "passengers"):
        # We need to migrate each of the passengers for DeployerUnits as well.
        for idx, p in enumerate(unit.passengers):
            unit.passengers[idx] = migrate_unit(p, faction)
        return DeployerUnit(float(unit.health), unit.remaining_stamina, (unit.location[0], unit.location[1]),
                            unit.garrisoned, migrate_unit_plan(unit.plan, faction), will_have_acted, will_be_besieging,
                            unit.passengers)
    return Unit(float(unit.health), unit.remaining_stamina, (unit.location[0], unit.location[1]), unit.garrisoned,
                migrate_unit_plan(unit.plan, faction), will_have_acted, will_be_besieging)


def migrate_player(player):
    """
    Apply the ai_playstyle, imminent_victories, faction, eliminated, and resources migrations for Players, if required.
    :param player: The loaded player object.
    """
    if player.ai_playstyle is not None:
        if hasattr(player.ai_playstyle, "attacking"):
            player.ai_playstyle = AIPlaystyle(AttackPlaystyle[player.ai_playstyle.attacking],
                                              ExpansionPlaystyle[player.ai_playstyle.expansion])
        else:
            player.ai_playstyle = AIPlaystyle(AttackPlaystyle[player.ai_playstyle], ExpansionPlaystyle.NEUTRAL)
    player.imminent_victories = set(player.imminent_victories) if hasattr(player, "imminent_victories") else set()
    player.faction = Faction(player.faction) if hasattr(player, "faction") else get_faction_for_colour(player.colour)
    if not hasattr(player, "eliminated"):
        player.eliminated = len(player.settlements) == 0
    if hasattr(player, "resources") and (res := player.resources):
        # We need to convert it back to a ResourceCollection object in order to take advantage of our custom truth value
        # testing operator.
        player.resources = ResourceCollection(res.ore, res.timber, res.magma,
                                              res.aurora, res.bloodstone, res.obsidian, res.sunstone, res.aquamarine)
    else:
        player.resources = ResourceCollection()


def migrate_climatic_effects(game_state, save):
    """
    Apply the night_status migration for the game state, if required.
    :param game_state: The state of the game being loaded in.
    :param save: The loaded save data.
    """
    game_state.until_night = save.night_status.until if hasattr(save, "night_status") else 0
    game_state.nighttime_left = save.night_status.remaining if hasattr(save, "night_status") else 0


def migrate_quad(quad, location: (int, int)) -> Quad:
    """
    Apply the is_relic, location, resource, and yield migrations for Quads, if required.
    :param quad: The loaded quad object.
    :param location: The backup location to use for the quad if it is from an outdated save.
    :return: An optionally-migrated Quad representation.
    """
    new_quad: Quad = quad
    # The biomes require special loading.
    new_quad.biome = Biome[new_quad.biome]
    new_quad.is_relic = new_quad.is_relic if hasattr(new_quad, "is_relic") else False
    new_quad.location = (new_quad.location[0], new_quad.location[1]) if hasattr(new_quad, "location") else location
    if hasattr(new_quad, "resource") and (res := new_quad.resource):
        # We need to convert it back to a ResourceCollection object in order to take advantage of our custom truth value
        # testing operator.
        new_quad.resource = ResourceCollection(res.ore, res.timber, res.magma,
                                               res.aurora, res.bloodstone, res.obsidian, res.sunstone, res.aquamarine)
    else:
        new_quad.resource = None
    new_quad.wealth = round(new_quad.wealth)
    new_quad.harvest = round(new_quad.harvest)
    new_quad.zeal = round(new_quad.zeal)
    new_quad.fortune = round(new_quad.fortune)
    return Quad(new_quad.biome, new_quad.wealth, new_quad.harvest, new_quad.zeal, new_quad.fortune, new_quad.location,
                new_quad.resource, is_relic=new_quad.is_relic)


def migrate_settlement(settlement):
    """
    Apply the besieged and resources migrations for Settlements, if required.
    :param settlement: The loaded settlement object.
    """
    if not hasattr(settlement, "besieged"):
        if settlement.under_siege_by is not None:
            settlement.besieged = True
        else:
            settlement.besieged = False
        # We now delete the old attribute so that it does not pollute future saves.
        delattr(settlement, "under_siege_by")
    for i in range(len(settlement.quads)):
        settlement.quads[i] = migrate_quad(settlement.quads[i], (settlement.location[0], settlement.location[1]))
    if hasattr(settlement, "resources") and (res := settlement.resources):
        # We need to convert it back to a ResourceCollection object in order to take advantage of our custom truth value
        # testing operator.
        settlement.resources = \
            ResourceCollection(res.ore, res.timber, res.magma,
                               res.aurora, res.bloodstone, res.obsidian, res.sunstone, res.aquamarine)
    else:
        settlement.resources = ResourceCollection()


def migrate_game_config(config) -> GameConfig:
    """
    Apply the climatic_effects, player_faction, and multiplayer migrations for game configuration, if required.
    :param config: The loaded game configuration.
    :return: An optionally-migrated GameConfig representation.
    """
    if not hasattr(config, "climatic_effects"):
        config.climatic_effects = False
    if not hasattr(config, "player_faction"):
        config.player_faction = get_faction_for_colour(config.player_colour)
        # We now delete the old attribute so that it does not pollute future saves.
        delattr(config, "player_colour")
    if not hasattr(config, "multiplayer"):
        config.multiplayer = False
    return config


def migrate_game_version(game_state, save):
    """
    Apply the game_version migration for the game state, if required.
    :param game_state: The state of the game being loaded in.
    :param save: The loaded save data.
    """
    # If the save file is from a version of the game prior to 3.0 in which resources were introduced, remove the
    # resource requirements for the construction of all improvements.
    if not hasattr(save, "game_version") or save.game_version == 0.0:
        for i in range(len(IMPROVEMENTS)):
            IMPROVEMENTS[i].req_resources = None
        # We need to set the game version here regardless so that if this loaded save is saved again after some
        # turns, we can still tell that it was originally from before resources were introduced.
        game_state.game_version = 0.0
    else:
        game_state.game_version = save.game_version


def get_faction_for_colour(colour: int) -> Faction:
    """
    Utility function that retrieves the faction for the supplied colour. Used for colour-to-faction migrations.
    :param colour: The colour to retrieve the faction for.
    :return: The faction for the supplied colour.
    """
    factions = list(FACTION_COLOURS.keys())
    colours = list(FACTION_COLOURS.values())
    idx = colours.index(colour)
    return factions[idx]
