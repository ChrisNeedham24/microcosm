from source.foundation.catalogue import get_blessing, FACTION_COLOURS
from source.foundation.models import UnitPlan, Unit, Faction, AIPlaystyle, AttackPlaystyle, ExpansionPlaystyle, Quad, \
    Biome, GameConfig

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
"""


def migrate_unit_plan(unit_plan) -> UnitPlan:
    """
    Apply the heals attribute migration for UnitPlans, if required.
    :param unit_plan: The loaded unit plan object.
    :return: An optionally-migrated UnitPlan representation.
    """
    plan_prereq = None if unit_plan.prereq is None else get_blessing(unit_plan.prereq.name)
    will_heal: bool = unit_plan.heals if hasattr(unit_plan, "heals") else False

    return UnitPlan(unit_plan.power, unit_plan.max_health, unit_plan.total_stamina,
                    unit_plan.name, plan_prereq, unit_plan.cost, unit_plan.can_settle,
                    will_heal)


def migrate_unit(unit) -> Unit:
    """
    Apply the has_attacked to has_acted and sieging to besieging migrations for Units, if required.
    :param unit: The loaded unit object.
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
    return Unit(unit.health, unit.remaining_stamina, (unit.location[0], unit.location[1]), unit.garrisoned,
                migrate_unit_plan(unit.plan), will_have_acted, will_be_besieging)


def migrate_player(player):
    """
    Apply the ai_playstyle, imminent_victories, faction, and eliminated migrations for Players, if required.
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


def migrate_climatic_effects(game_state, save):
    """
    Apply the night_status migrations for the game state, if required.
    :param game_state: The state of the game being loaded in.
    :param save: The loaded save data.
    """
    game_state.until_night = save.night_status.until if hasattr(save, "night_status") else 0
    game_state.nighttime_left = save.night_status.remaining if hasattr(save, "night_status") else 0


def migrate_quad(quad, location: (int, int)) -> Quad:
    """
    Apply the is_relic migration for Quads, if required.
    :param quad: The loaded quad object.
    :param location: The backup location to use for the quad if it is from an outdated save.
    :return: An optionally-migrated Quad representation.
    """
    new_quad = quad
    # The biomes require special loading.
    new_quad.biome = Biome[new_quad.biome]
    new_quad.is_relic = new_quad.is_relic if hasattr(new_quad, "is_relic") else False
    new_quad.location = (new_quad.location[0], new_quad.location[1]) if hasattr(new_quad, "location") else location
    return new_quad


def migrate_settlement(settlement):
    """
    Apply the besieged migration for Settlements, if required.
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


def migrate_game_config(config) -> GameConfig:
    """
    Apply the climatic_effects and player_faction migrations for game configuration, if required.
    :param config: The loaded game configuration.
    :return: An optionally-migrated GameConfig representation.
    """
    if not hasattr(config, "climatic_effects"):
        config.climatic_effects = False
    if not hasattr(config, "player_faction"):
        config.player_faction = get_faction_for_colour(config.player_colour)
        # We now delete the old attribute so that it does not pollute future saves.
        delattr(config, "player_colour")
    return config


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
