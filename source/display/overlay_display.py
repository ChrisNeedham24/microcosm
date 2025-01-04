import typing

import math
import pyxel

from source.display.display_utils import draw_paragraph
from source.util.calculator import get_setl_totals, player_has_resources_for_improvement, get_player_totals
from source.foundation.catalogue import get_all_unlockable, get_unlockable_improvements, get_unlockable_units, \
    ACHIEVEMENTS, BLESSINGS, FACTION_COLOURS
from source.foundation.models import VictoryType, InvestigationResult, Heathen, EconomicStatus, ImprovementType, \
    OverlayType, SettlementAttackType, PauseOption, Faction, HarvestStatus, ConstructionMenu, ProjectType, Project, \
    DeployerUnitPlan, DeployerUnit, StandardOverlayView
from source.display.overlay import Overlay


def display_overlay(overlay: Overlay, is_night: bool):
    """
    Display the given overlay to the screen.
    :param overlay: The Overlay to display.
    :param is_night: Whether it is night.
    """
    pyxel.load("resources/sprites.pyxres")
    # The achievement notification overlay displays any achievements that the player has obtained since the last turn.
    if OverlayType.ACH_NOTIF in overlay.showing:
        pyxel.load("resources/achievements.pyxres")
        pyxel.rectb(12, 50, 176, 58, pyxel.COLOR_YELLOW)
        pyxel.rect(13, 51, 174, 56, pyxel.COLOR_BLACK)
        pyxel.text(60, 55, "Achievement unlocked!", pyxel.COLOR_YELLOW)
        idx = ACHIEVEMENTS.index(overlay.new_achievements[-1])
        pyxel.blt(35, 70, 0, (idx // 32) * 16, idx * 8 - (idx // 32) * 256, 8, 8)
        pyxel.text(50, 68, overlay.new_achievements[-1].name, pyxel.COLOR_WHITE)
        draw_paragraph(50, 76, overlay.new_achievements[-1].description, 30, pyxel.COLOR_WHITE)
        pyxel.text(70, 95, "SPACE: Dismiss", pyxel.COLOR_WHITE)
    # The desync overlay alerts the player to the fact that they have lost sync with the server in a multiplayer game.
    elif OverlayType.DESYNC in overlay.showing:
        pyxel.rectb(12, 60, 176, 38, pyxel.COLOR_WHITE)
        pyxel.rect(13, 61, 174, 36, pyxel.COLOR_BLACK)
        pyxel.text(46, 65, "Desync with server detected!", pyxel.COLOR_RED)
        pyxel.text(41, 80, "Press ENTER to rejoin the game.", pyxel.COLOR_WHITE)
    # The victory overlay displays the player who achieved the victory, as well as the type.
    elif OverlayType.VICTORY in overlay.showing:
        pyxel.rectb(12, 60, 176, 38, pyxel.COLOR_WHITE)
        pyxel.rect(13, 61, 174, 36, pyxel.COLOR_BLACK)
        if overlay.current_victory.player is overlay.current_player:
            beginning = "You have"
            pyxel.text(82, 65, "Victory!", pyxel.COLOR_GREEN)
        else:
            beginning = f"{overlay.current_victory.player.name} has"
            pyxel.text(82, 65, "Game over!", pyxel.COLOR_RED)

        match overlay.current_victory.type:
            case VictoryType.ELIMINATION:
                pyxel.text(22, 75, f"{beginning} achieved an ELIMINATION victory.", pyxel.COLOR_RED)
            case VictoryType.JUBILATION | VictoryType.GLUTTONY:
                pyxel.text(22, 75, f"{beginning} achieved a {overlay.current_victory.type.value} victory.",
                           pyxel.COLOR_GREEN)
            case VictoryType.AFFLUENCE:
                pyxel.text(22, 75, f"{beginning} achieved an AFFLUENCE victory.", pyxel.COLOR_YELLOW)
            case VictoryType.VIGOUR:
                pyxel.text(30, 75, f"{beginning} achieved a VIGOUR victory.", pyxel.COLOR_ORANGE)
            case _:
                pyxel.text(22, 75, f"{beginning} achieved a SERENDIPITY victory.", pyxel.COLOR_PURPLE)

        pyxel.text(35, 85, "Press ENTER to return to the menu.", pyxel.COLOR_WHITE)
    # The deployment overlay displays a message instructing the player.
    elif OverlayType.DEPLOYMENT in overlay.showing:
        pyxel.rectb(12, 150, 176, 15, pyxel.COLOR_WHITE)
        pyxel.rect(13, 151, 174, 13, pyxel.COLOR_BLACK)
        pyxel.text(20, 153, "Click any white-bordered quad to deploy!", pyxel.COLOR_WHITE)
    # The elimination overlay displays either game over if the player has been eliminated, or alternatively, any other
    # players that have been eliminated since the last turn.
    elif OverlayType.ELIMINATION in overlay.showing:
        pyxel.rectb(12, 60, 176, 38, pyxel.COLOR_WHITE)
        pyxel.rect(13, 61, 174, 36, pyxel.COLOR_BLACK)
        if overlay.just_eliminated is overlay.current_player:
            pyxel.text(82, 65, "Game Over!", pyxel.COLOR_RED)
            pyxel.text(32, 75, "Defeat has arrived at your doorstep.", pyxel.COLOR_WHITE)
            pyxel.text(35, 85, "Press ENTER to return to the menu.", pyxel.COLOR_WHITE)
        else:
            pyxel.text(56, 65, "Consigned to folklore", pyxel.COLOR_RED)
            pyxel.text(50, 75, f"{overlay.just_eliminated.name} has been eliminated.", overlay.just_eliminated.colour)
            pyxel.text(70, 85, "SPACE: Dismiss", pyxel.COLOR_WHITE)
    # The night overlay alerts the player that night is either beginning or ending, and the effects of that.
    elif OverlayType.NIGHT in overlay.showing:
        pyxel.rectb(12, 50, 176, 58, pyxel.COLOR_WHITE)
        pyxel.rect(13, 51, 174, 56, pyxel.COLOR_BLACK)
        if overlay.night_beginning:
            pyxel.text(35, 55, "The everlasting night begins...", pyxel.COLOR_YELLOW)
            pyxel.text(63, 75, "Increased fortune", pyxel.COLOR_PURPLE)
            pyxel.text(55, 85, "Strengthened heathens", pyxel.COLOR_RED)
            if overlay.current_player.faction == Faction.NOCTURNE:
                pyxel.text(52, 65, "Nocturne bonus to units", pyxel.COLOR_GREEN)
            else:
                pyxel.text(45, 65, "Reduced vision and harvest", pyxel.COLOR_RED)
        else:
            pyxel.text(42, 55, "The sun returns once more...", pyxel.COLOR_YELLOW)
            pyxel.text(67, 75, "Regular fortune", pyxel.COLOR_PURPLE)
            pyxel.text(62, 85, "Standard heathens", pyxel.COLOR_GREEN)
            if overlay.current_player.faction == Faction.NOCTURNE:
                pyxel.text(45, 65, "Nocturne unit bonus removed", pyxel.COLOR_RED)
            else:
                pyxel.text(45, 65, "Restored vision and harvest", pyxel.COLOR_GREEN)
        pyxel.text(70, 95, "SPACE: Dismiss", pyxel.COLOR_WHITE)
    # The close-to-victory overlay displays any players who are close to achieving a victory, and the type of
    # victory they are close to achieving.
    elif OverlayType.CLOSE_TO_VIC in overlay.showing:
        extension = 20 * (len(overlay.close_to_vics) - 1)
        pyxel.rectb(12, 60, 176, 48 + extension, pyxel.COLOR_WHITE)
        pyxel.rect(13, 61, 174, 46 + extension, pyxel.COLOR_BLACK)
        pyxel.text(68, 65, "Nearing greatness", pyxel.COLOR_WHITE)
        for idx, vic in enumerate(overlay.close_to_vics):
            qualifier = "an" if vic.type is VictoryType.ELIMINATION or vic.type is VictoryType.AFFLUENCE else "a"
            beginning = "You are" if vic.player is overlay.current_player else f"{vic.player.name} is"
            vic_x = 32 if vic.type is VictoryType.VIGOUR else 22
            pyxel.text(vic_x, 75 + idx * 20, f"{beginning} close to {qualifier} {vic.type.value} victory.",
                       vic.player.colour)
            match vic.type:
                case VictoryType.ELIMINATION:
                    pyxel.text(25, 85 + idx * 20, "(Needs to control one more settlement)", pyxel.COLOR_RED)
                case VictoryType.JUBILATION:
                    pyxel.text(20, 85 + idx * 20, "(Needs 25 turns of current satisfaction)", pyxel.COLOR_GREEN)
                case VictoryType.GLUTTONY:
                    pyxel.text(28, 85 + idx * 20, "(Needs 2 more level 10 settlements)", pyxel.COLOR_GREEN)
                case VictoryType.AFFLUENCE:
                    pyxel.text(27, 85 + idx * 20, "(Needs to accumulate 25k more wealth)", pyxel.COLOR_YELLOW)
                case VictoryType.VIGOUR:
                    pyxel.text(25, 85 + idx * 20, "(Needs to complete begun Holy Sanctum)", pyxel.COLOR_ORANGE)
                case VictoryType.SERENDIPITY:
                    pyxel.text(20, 85 + idx * 20, "(Needs to undergo final ardour blessing)", pyxel.COLOR_PURPLE)
        pyxel.text(70, 95 + extension, "SPACE: Dismiss", pyxel.COLOR_WHITE)
    # The blessing notification overlay displays any blessing completed by the player in the last turn, and what has
    # been unlocked as a result.
    elif OverlayType.BLESS_NOTIF in overlay.showing:
        unlocked = get_all_unlockable(overlay.completed_blessing)
        pyxel.rectb(12, 60, 176, 45 + max(1, len(unlocked)) * 10, pyxel.COLOR_WHITE)
        pyxel.rect(13, 61, 174, 43 + max(1, len(unlocked)) * 10, pyxel.COLOR_BLACK)
        pyxel.text(60, 63, "Blessing completed!", pyxel.COLOR_PURPLE)
        pyxel.text(20, 73, overlay.completed_blessing.name, pyxel.COLOR_WHITE)
        pyxel.text(20, 83, "Unlocks:", pyxel.COLOR_WHITE)
        if len(unlocked) > 0:
            for idx, imp in enumerate(unlocked):
                pyxel.text(25, 93 + idx * 10, imp.name, pyxel.COLOR_RED)
        # Blessings that do not unlock any improvements are for meeting victory criteria.
        else:
            pyxel.text(25, 93, "victory", pyxel.COLOR_GREEN)
        pyxel.text(70, 93 + max(1, len(unlocked)) * 10, "SPACE: Dismiss", pyxel.COLOR_WHITE)
    # The construction notification overlay displays any constructions completed by the player in the last turn, and
    # the settlements they were constructed in.
    elif OverlayType.CONSTR_NOTIF in overlay.showing:
        pyxel.rectb(12, 60, 176, 25 + len(overlay.completed_constructions) * 20, pyxel.COLOR_WHITE)
        pyxel.rect(13, 61, 174, 23 + len(overlay.completed_constructions) * 20, pyxel.COLOR_BLACK)
        pluralisation = "s" if len(overlay.completed_constructions) > 1 else ""
        pyxel.text(60, 63, f"Construction{pluralisation} completed!", pyxel.COLOR_RED)
        for idx, constr in enumerate(overlay.completed_constructions):
            pyxel.text(20, 73 + idx * 20, constr.settlement.name, pyxel.COLOR_WHITE)
            pyxel.text(25, 83 + idx * 20, constr.construction.name, pyxel.COLOR_RED)
        pyxel.text(70, 73 + len(overlay.completed_constructions) * 20, "SPACE: Dismiss", pyxel.COLOR_WHITE)
    # The level up notification overlay displays any player settlements that levelled up in the last turn.
    elif OverlayType.LEVEL_NOTIF in overlay.showing:
        pyxel.rectb(12, 60, 176, 25 + len(overlay.levelled_up_settlements) * 20, pyxel.COLOR_WHITE)
        pyxel.rect(13, 61, 174, 23 + len(overlay.levelled_up_settlements) * 20, pyxel.COLOR_BLACK)
        pluralisation = "s" if len(overlay.levelled_up_settlements) > 1 else ""
        pyxel.text(60, 63, f"Settlement{pluralisation} level up!", pyxel.COLOR_WHITE)
        for idx, setl in enumerate(overlay.levelled_up_settlements):
            pyxel.text(20, 73 + idx * 20, setl.name, pyxel.COLOR_WHITE)
            pyxel.text(25, 83 + idx * 20, f"{setl.level - 1} -> {setl.level}", pyxel.COLOR_WHITE)
        pyxel.text(70, 73 + len(overlay.levelled_up_settlements) * 20, "SPACE: Dismiss", pyxel.COLOR_WHITE)
    # The warning overlay displays if the player is not undergoing a blessing, has any settlements without a
    # current construction, or if the player's wealth will be depleted.
    elif OverlayType.WARNING in overlay.showing:
        extension = 0
        if overlay.will_have_negative_wealth:
            extension += 20
        if overlay.has_no_blessing:
            extension += 10
        if len(overlay.problematic_settlements) > 0:
            extension += len(overlay.problematic_settlements) * 10 + 1
        pyxel.rectb(12, 60, 176, 20 + extension, pyxel.COLOR_WHITE)
        pyxel.rect(13, 61, 174, 18 + extension, pyxel.COLOR_BLACK)
        pyxel.text(85, 63, "Warning!", pyxel.COLOR_WHITE)
        offset = 0
        if overlay.will_have_negative_wealth:
            pyxel.text(32, 73, "Your treasuries will be depleted!", pyxel.COLOR_YELLOW)
            pyxel.text(20, 83, "Units will be auto-sold to recoup losses.", pyxel.COLOR_WHITE)
            offset += 20
        if overlay.has_no_blessing:
            pyxel.text(20, 73 + offset, "You are currently undergoing no blessing!", pyxel.COLOR_PURPLE)
            offset += 10
        if len(overlay.problematic_settlements) > 0:
            pyxel.text(15, 73 + offset, "The below settlements have no construction:", pyxel.COLOR_RED)
            offset += 10
            for setl in overlay.problematic_settlements:
                pyxel.text(80, 73 + offset, setl.name, pyxel.COLOR_WHITE)
                offset += 10
    # The investigation overlay displays the results of a just-executed investigation on a relic by one of the
    # player's units.
    elif OverlayType.INVESTIGATION in overlay.showing:
        pyxel.rectb(12, 60, 176, 48, pyxel.COLOR_WHITE)
        pyxel.rect(13, 61, 174, 46, pyxel.COLOR_BLACK)
        pyxel.text(60, 65, "Relic investigation", pyxel.COLOR_ORANGE)
        match overlay.investigation_result:
            case InvestigationResult.WEALTH:
                pyxel.text(15, 75, "Your unit found a chest bursting with gold.", pyxel.COLOR_WHITE)
                pyxel.text(77, 85, "+25 wealth", pyxel.COLOR_YELLOW)
            case InvestigationResult.FORTUNE:
                pyxel.text(18, 75, "Your unit found a temple with holy texts.", pyxel.COLOR_WHITE)
                pyxel.text(55, 85, "+25% blessing progress", pyxel.COLOR_PURPLE)
            case InvestigationResult.VISION:
                pyxel.text(20, 75, "A vantage point was found, giving sight.", pyxel.COLOR_WHITE)
                pyxel.text(22, 85, "10 quads of vision around unit granted", pyxel.COLOR_GREEN)
            case InvestigationResult.HEALTH:
                pyxel.text(22, 75, "A concoction found yields constitution.", pyxel.COLOR_WHITE)
                pyxel.text(44, 85, "Permanent +5 health to unit", pyxel.COLOR_GREEN)
            case InvestigationResult.POWER:
                pyxel.text(20, 75, "An exhilarant aura strengthens the unit.", pyxel.COLOR_WHITE)
                pyxel.text(45, 85, "Permanent +5 power to unit", pyxel.COLOR_GREEN)
            case InvestigationResult.STAMINA:
                pyxel.text(25, 75, "A mixture found invigorates the unit.", pyxel.COLOR_WHITE)
                pyxel.text(42, 85, "Permanent +1 stamina to unit", pyxel.COLOR_GREEN)
            case InvestigationResult.UPKEEP:
                pyxel.text(20, 75, "Returning their coin, the unit walks on.", pyxel.COLOR_WHITE)
                pyxel.text(45, 85, "Permanent 0 upkeep for unit", pyxel.COLOR_YELLOW)
            case InvestigationResult.ORE:
                pyxel.text(28, 75, "Your unit found an ancient minesite.", pyxel.COLOR_WHITE)
                pyxel.text(85, 85, "+10 ore", pyxel.COLOR_GRAY)
            case InvestigationResult.TIMBER:
                pyxel.text(28, 75, "Freshly cut logs encircle the relic.", pyxel.COLOR_WHITE)
                pyxel.text(79, 85, "+10 timber", pyxel.COLOR_BROWN)
            case InvestigationResult.MAGMA:
                pyxel.text(34, 75, "Pools of lava surround the relic.", pyxel.COLOR_WHITE)
                pyxel.text(80, 85, "+10 magma", pyxel.COLOR_RED)
            case InvestigationResult.NONE:
                pyxel.text(40, 80, "Nothing of interest was found.", pyxel.COLOR_GRAY)
        pyxel.text(70, 95, "SPACE: Dismiss", pyxel.COLOR_WHITE)
    else:
        # The attack overlay displays the results of an attack that occurred involving one of the player's units,
        # whether player-initiated or not.
        if OverlayType.ATTACK in overlay.showing:
            pyxel.rectb(12, 10, 176, 26, pyxel.COLOR_WHITE)
            pyxel.rect(13, 11, 174, 24, pyxel.COLOR_BLACK)
            att_name = overlay.attack_data.attacker.plan.name
            att_dmg = round(overlay.attack_data.damage_to_attacker)
            def_name = overlay.attack_data.defender.plan.name
            def_dmg = round(overlay.attack_data.damage_to_defender)
            if overlay.attack_data.attacker_was_killed and overlay.attack_data.player_attack:
                pyxel.text(35, 15, f"Your {att_name} (-{att_dmg}) was killed by", pyxel.COLOR_WHITE)
            elif overlay.attack_data.defender_was_killed and not overlay.attack_data.player_attack:
                pyxel.text(35, 15, f"Your {def_name} (-{def_dmg}) was killed by", pyxel.COLOR_WHITE)
            elif overlay.attack_data.attacker_was_killed and not overlay.attack_data.player_attack:
                pyxel.text(50, 15, f"Your {def_name} (-{def_dmg}) killed", pyxel.COLOR_WHITE)
            elif overlay.attack_data.defender_was_killed and overlay.attack_data.player_attack:
                pyxel.text(50, 15, f"Your {att_name} (-{att_dmg}) killed", pyxel.COLOR_WHITE)
            elif overlay.attack_data.player_attack:
                pyxel.text(46, 15, f"Your {att_name} (-{att_dmg}) attacked", pyxel.COLOR_WHITE)
            else:
                pyxel.text(32, 15, f"Your {def_name} (-{def_dmg}) was attacked by", pyxel.COLOR_WHITE)
            pyxel.text(72, 25, f"a {def_name if overlay.attack_data.player_attack else att_name} "
                               f"(-{def_dmg if overlay.attack_data.player_attack else att_dmg})", pyxel.COLOR_WHITE)
        # The heal overlay displays the results of a healing action that occurred involving one of the player's units.
        if OverlayType.HEAL in overlay.showing:
            pyxel.rectb(12, 10, 176, 26, pyxel.COLOR_WHITE)
            pyxel.rect(13, 11, 174, 24, pyxel.COLOR_BLACK)
            healer_name = overlay.heal_data.healer.plan.name
            healed_name = overlay.heal_data.healed.plan.name
            heal_amt = overlay.heal_data.heal_amount
            orig_health = round(overlay.heal_data.original_health)
            new_health = round(overlay.heal_data.healed.health)
            pyxel.text(35, 15, f"Your {healer_name} healed your {healed_name}", pyxel.COLOR_WHITE)
            pyxel.text(70, 25, f"by {heal_amt} ({orig_health} -> {new_health})", pyxel.COLOR_WHITE)
        # The settlement attack overlay displays the results of an attack on one of the player's settlements, or on
        # a settlement that has been attacked by the player.
        if OverlayType.SETL_ATTACK in overlay.showing:
            pyxel.rectb(12, 10, 176, 26, pyxel.COLOR_WHITE)
            pyxel.rect(13, 11, 174, 24, pyxel.COLOR_BLACK)
            att_name = overlay.setl_attack_data.attacker.plan.name
            att_dmg = round(overlay.setl_attack_data.damage_to_attacker)
            setl_name = overlay.setl_attack_data.settlement.name
            setl_dmg = round(overlay.setl_attack_data.damage_to_setl)
            if overlay.setl_attack_data.attacker_was_killed and overlay.setl_attack_data.player_attack:
                pyxel.text(35, 15, f"Your {att_name} (-{att_dmg}) was killed by", pyxel.COLOR_WHITE)
            elif overlay.setl_attack_data.attacker_was_killed:
                pyxel.text(38, 15, f"A {att_name} (-{att_dmg}) was killed by", pyxel.COLOR_WHITE)
            elif overlay.setl_attack_data.setl_was_taken and overlay.setl_attack_data.player_attack:
                pyxel.text(50, 15, f"Your {att_name} (-{att_dmg}) sacked", pyxel.COLOR_WHITE)
            elif overlay.setl_attack_data.setl_was_taken:
                pyxel.text(70, 15, f"A {att_name} sacked", pyxel.COLOR_WHITE)
            elif overlay.setl_attack_data.player_attack:
                pyxel.text(46, 15, f"Your {att_name} (-{att_dmg}) attacked", pyxel.COLOR_WHITE)
            else:
                pyxel.text(54, 15, f"A {att_name} (-{att_dmg}) attacked", pyxel.COLOR_WHITE)
            pyxel.text(72, 25, f"{setl_name} (-{setl_dmg})", overlay.setl_attack_data.setl_owner.colour)
        # The siege notification overlay notifies the player that one of their settlements has been placed under
        # siege by another player.
        if OverlayType.SIEGE_NOTIF in overlay.showing:
            pyxel.rectb(12, 10, 176, 16, pyxel.COLOR_WHITE)
            pyxel.rect(13, 11, 174, 14, pyxel.COLOR_BLACK)
            att_name = overlay.sieger_of_settlement.name
            setl_name = overlay.sieged_settlement.name
            pyxel.text(22, 15, f"{setl_name} was placed under siege by {att_name}", pyxel.COLOR_RED)
        # The player change overlay notifies the player when another player leaves or joins their multiplayer game.
        if OverlayType.PLAYER_CHANGE in overlay.showing:
            pyxel.rectb(12, 10, 176, 16, pyxel.COLOR_WHITE)
            pyxel.rect(13, 11, 174, 14, pyxel.COLOR_BLACK)
            if overlay.changed_player_is_leaving:
                pyxel.text(22, 15, f"{overlay.player_changing.name} has left the game, replaced by AI",
                           FACTION_COLOURS[overlay.player_changing.faction])
            else:
                pyxel.text(46, 15, f"{overlay.player_changing.name} has joined the game",
                           FACTION_COLOURS[overlay.player_changing.faction])
        # The settlement overlay displays the currently-selected settlements name, statistics, current construction,
        # garrison, and resources.
        if OverlayType.SETTLEMENT in overlay.showing:
            pyxel.rectb(12, 10, 176, 26, pyxel.COLOR_WHITE)
            pyxel.rect(13, 11, 174, 24, pyxel.COLOR_BLACK)
            pyxel.text(20, 14, f"{overlay.current_settlement.name} ({overlay.current_settlement.level})",
                       overlay.current_player.colour)
            pyxel.blt(80, 12, 0, 24 if overlay.current_settlement.besieged else 0, 28, 8, 8)
            pyxel.text(90, 14, str(round(overlay.current_settlement.strength)),
                       pyxel.COLOR_RED if overlay.current_settlement.besieged else pyxel.COLOR_WHITE)
            satisfaction_u = 8 if overlay.current_settlement.satisfaction >= 50 else 16
            pyxel.blt(105, 12, 0, satisfaction_u, 28, 8, 8)
            pyxel.text(115, 14, str(round(overlay.current_settlement.satisfaction)), pyxel.COLOR_WHITE)

            total_wealth, total_harvest, total_zeal, total_fortune = get_setl_totals(overlay.current_player,
                                                                                     overlay.current_settlement,
                                                                                     is_night,
                                                                                     strict=True)

            pyxel.text(138, 14, str(round(total_wealth)), pyxel.COLOR_YELLOW)
            pyxel.text(150, 14, str(round(total_harvest)), pyxel.COLOR_GREEN)
            pyxel.text(162, 14, str(round(total_zeal)), pyxel.COLOR_RED)
            pyxel.text(174, 14, str(round(total_fortune)), pyxel.COLOR_PURPLE)

            pyxel.text(20, 24, "Resources:", pyxel.COLOR_WHITE)
            if res := overlay.current_settlement.resources:
                x_offset = 0
                for _ in range(res.ore):
                    pyxel.text(62 + x_offset, 24, "Ore", pyxel.COLOR_GRAY)
                    x_offset += 15
                for _ in range(res.timber):
                    pyxel.text(62 + x_offset, 24, "Timber", pyxel.COLOR_BROWN)
                    x_offset += 27
                for _ in range(res.magma):
                    pyxel.text(62 + x_offset, 24, "Magma", pyxel.COLOR_RED)
                    x_offset += 23
                for _ in range(res.aurora):
                    pyxel.text(62 + x_offset, 24, "Aurora", pyxel.COLOR_YELLOW)
                    x_offset += 27
                for _ in range(res.bloodstone):
                    pyxel.text(62 + x_offset, 24, "Bloodstone", pyxel.COLOR_RED)
                    x_offset += 44
                for _ in range(res.obsidian):
                    pyxel.text(62 + x_offset, 24, "Obsidian", pyxel.COLOR_GRAY)
                    x_offset += 36
                for _ in range(res.sunstone):
                    pyxel.text(62 + x_offset, 24, "Sunstone", pyxel.COLOR_ORANGE)
                    x_offset += 36
                for _ in range(res.aquamarine):
                    pyxel.text(62 + x_offset, 24, "Aquamarine", pyxel.COLOR_LIGHT_BLUE)
                    x_offset += 50
            else:
                pyxel.text(62, 24, "None", pyxel.COLOR_GRAY)

            y_offset = 0
            curr_work = overlay.current_settlement.current_work
            if curr_work is not None and not isinstance(curr_work.construction, Project) and \
                    overlay.current_player.wealth >= \
                    (overlay.current_settlement.current_work.construction.cost -
                     overlay.current_settlement.current_work.zeal_consumed) and \
                    overlay.current_player.faction != Faction.FUNDAMENTALISTS:
                y_offset = 10
            pyxel.rectb(12, 130 - y_offset, 176, 40 + y_offset, pyxel.COLOR_WHITE)
            pyxel.rect(13, 131 - y_offset, 174, 38 + y_offset, pyxel.COLOR_BLACK)
            pyxel.line(100, 130 - y_offset, 100, 168, pyxel.COLOR_WHITE)
            pyxel.text(20, 134 - y_offset, "Construction", pyxel.COLOR_RED)
            if curr_work is not None:
                if not isinstance(curr_work.construction, Project):
                    pyxel.text(20, 145 - y_offset, curr_work.construction.name, pyxel.COLOR_WHITE)
                    remaining_work = curr_work.construction.cost - curr_work.zeal_consumed
                    total_zeal = max(sum(quad.zeal for quad in overlay.current_settlement.quads) +
                                     sum(imp.effect.zeal for imp in overlay.current_settlement.improvements), 1)
                    total_zeal += (overlay.current_settlement.level - 1) * 0.25 * total_zeal
                    if overlay.current_player.faction == Faction.AGRICULTURISTS:
                        total_zeal *= 0.75
                    elif overlay.current_player.faction == Faction.FUNDAMENTALISTS:
                        total_zeal *= 1.25
                    remaining_turns = math.ceil(remaining_work / total_zeal)
                    pyxel.text(20, 155 - y_offset, f"{remaining_turns} turns remaining", pyxel.COLOR_WHITE)
                    if overlay.current_player.wealth >= remaining_work and \
                            overlay.current_player.faction != Faction.FUNDAMENTALISTS:
                        pyxel.blt(20, 153, 0, 0, 52, 8, 8)
                        pyxel.text(30, 155, "Buyout:", pyxel.COLOR_WHITE)
                        pyxel.blt(60, 153, 0, 0, 44, 8, 8)
                        pyxel.text(70, 155, str(round(remaining_work)), pyxel.COLOR_WHITE)
                        pyxel.text(87, 155, "(B)", pyxel.COLOR_WHITE)
                else:
                    project_colour: int
                    match curr_work.construction.type:
                        case ProjectType.BOUNTIFUL:
                            project_colour = pyxel.COLOR_GREEN
                        case ProjectType.ECONOMICAL:
                            project_colour = pyxel.COLOR_YELLOW
                        case _:
                            project_colour = pyxel.COLOR_PURPLE
                    pyxel.text(20, 145 - y_offset, curr_work.construction.name, project_colour)
                    pyxel.text(20, 155 - y_offset, "Press C to cease.", pyxel.COLOR_WHITE)
            else:
                pyxel.text(20, 145 - y_offset, "None", pyxel.COLOR_RED)
                if overlay.show_auto_construction_prompt:
                    pyxel.text(20, 155 - y_offset, "Press A for auto!", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(20, 155 - y_offset, "Press C to add one!", pyxel.COLOR_WHITE)
            pyxel.text(110, 134 - y_offset, "Garrison", pyxel.COLOR_RED)
            if len(overlay.current_settlement.garrison) > 0:
                pluralisation = "s" if len(overlay.current_settlement.garrison) > 1 else ""
                pyxel.text(110, 145 - y_offset, f"{len(overlay.current_settlement.garrison)} unit{pluralisation}",
                           pyxel.COLOR_WHITE)
                pyxel.text(110, 155 - y_offset, "Press D to deploy!", pyxel.COLOR_WHITE)
            else:
                pyxel.text(110, 145 - y_offset, "No units.", pyxel.COLOR_RED)
        # The unit overlay displays the statistics for the selected unit, along with a notification if the selected
        # unit is the player's and they are currently placing an enemy settlement under siege.
        if OverlayType.UNIT in overlay.showing:
            y_offset = 0 if overlay.selected_unit in overlay.current_player.units else 20
            x_offset = 8 if round(overlay.selected_unit.plan.cost / 10) >= 10 and \
                overlay.selected_unit in overlay.current_player.units else 0
            if overlay.selected_unit in overlay.current_player.units and \
                    isinstance(overlay.selected_unit, DeployerUnit):
                if overlay.show_unit_passengers:
                    pyxel.rectb(70 + x_offset, 110 + y_offset, 56 + x_offset, 60 - y_offset, pyxel.COLOR_WHITE)
                    pyxel.rect(71 + x_offset, 111 + y_offset, 54 + x_offset, 58 - y_offset, pyxel.COLOR_BLACK)
                    for idx, unit in enumerate(overlay.selected_unit.passengers):
                        pyxel.text(75 + x_offset, 115 + y_offset + 10 * idx, unit.plan.name, pyxel.COLOR_WHITE)
                        if idx == overlay.unit_passengers_idx:
                            pyxel.blt(110 + x_offset, 115 + y_offset + 10 * idx, 0, 64, 36, 8, 8)
                        else:
                            pyxel.blt(110 + x_offset, 115 + y_offset + 10 * idx, 0, 56, 36, 8, 8)
                    pyxel.text(83, 162, "Close (D)", pyxel.COLOR_WHITE)
                else:
                    pyxel.rectb(17, 105 + y_offset, 56 + x_offset, 60 - y_offset, pyxel.COLOR_WHITE)
                    pyxel.rect(18, 106 + y_offset, 54 + x_offset, 58 - y_offset, pyxel.COLOR_BLACK)
            pyxel.rectb(12, 110 + y_offset, 56 + x_offset, 60 - y_offset, pyxel.COLOR_WHITE)
            pyxel.rect(13, 111 + y_offset, 54 + x_offset, 58 - y_offset, pyxel.COLOR_BLACK)
            pyxel.text(20, 114 + y_offset, overlay.selected_unit.plan.name, pyxel.COLOR_WHITE)
            if overlay.selected_unit.plan.can_settle:
                pyxel.blt(55, 113 + y_offset, 0, 24, 36, 8, 8)
            if not isinstance(overlay.selected_unit, Heathen) and overlay.selected_unit.besieging and \
                    overlay.selected_unit in overlay.current_player.units:
                pyxel.blt(55, 113, 0, 32, 36, 8, 8)
                pyxel.rectb(12, 10, 176, 16, pyxel.COLOR_WHITE)
                pyxel.rect(13, 11, 174, 14, pyxel.COLOR_BLACK)
                pyxel.text(18, 14, "Remember: the siege will end if all leave!", pyxel.COLOR_RED)
            pyxel.blt(20, 120 + y_offset, 0, 8, 36, 8, 8)
            pyxel.text(30, 122 + y_offset, str(round(overlay.selected_unit.health)), pyxel.COLOR_WHITE)
            power_u: int
            if overlay.selected_unit.plan.heals:
                power_u = 40
            elif isinstance(overlay.selected_unit.plan, DeployerUnitPlan):
                power_u = 48
            else:
                power_u = 0
            pyxel.blt(20, 130 + y_offset, 0, power_u, 36, 8, 8)
            power_text: str
            if isinstance(overlay.selected_unit.plan, DeployerUnitPlan):
                power_text = f"{len(overlay.selected_unit.passengers)}/{overlay.selected_unit.plan.max_capacity}"
                if overlay.selected_unit in overlay.current_player.units:
                    power_text += " (D)"
            else:
                power_text = str(round(overlay.selected_unit.plan.power))
            pyxel.text(30, 132 + y_offset, power_text, pyxel.COLOR_WHITE)
            pyxel.blt(20, 140 + y_offset, 0, 16, 36, 8, 8)
            pyxel.text(30, 142 + y_offset,
                       f"{overlay.selected_unit.remaining_stamina}/{overlay.selected_unit.plan.total_stamina}",
                       pyxel.COLOR_WHITE)
            if overlay.selected_unit in overlay.current_player.units:
                pyxel.blt(20, 150, 0, 0, 44, 8, 8)
                cost: float = overlay.selected_unit.plan.cost
                pyxel.text(30, 152, f"{round(cost)} (-{round(cost / 10)}/T)", pyxel.COLOR_WHITE)
                pyxel.blt(20, 160, 0, 8, 52, 8, 8)
                pyxel.text(30, 162, "Disb. (X)", pyxel.COLOR_RED)
        # The construction overlay displays the available improvements and unit plans available for construction in
        # the currently-selected settlement, along with their effects.
        if OverlayType.CONSTRUCTION in overlay.showing:
            pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
            pyxel.text(55, 25, "Available constructions", pyxel.COLOR_RED)
            total_zeal = 0
            total_zeal += sum(quad.zeal for quad in overlay.current_settlement.quads)
            total_zeal += sum(imp.effect.zeal for imp in overlay.current_settlement.improvements)
            total_zeal = max(1, total_zeal) + (overlay.current_settlement.level - 1) * 0.25 * total_zeal
            if overlay.current_player.faction == Faction.AGRICULTURISTS:
                total_zeal *= 0.75
            elif overlay.current_player.faction == Faction.FUNDAMENTALISTS:
                total_zeal *= 1.25
            if overlay.current_construction_menu is ConstructionMenu.IMPROVEMENTS:
                for idx, construction in enumerate(overlay.available_constructions):
                    if overlay.construction_boundaries[0] <= idx <= overlay.construction_boundaries[1]:
                        adj_idx = idx - overlay.construction_boundaries[0]
                        pyxel.text(30, 35 + adj_idx * 18,
                                   f"{construction.name} ({math.ceil(construction.cost / total_zeal)})",
                                   pyxel.COLOR_WHITE)
                        if construction.req_resources and \
                                not player_has_resources_for_improvement(overlay.current_player, construction):
                            pyxel.text(146, 35 + adj_idx * 18, "Blocked",
                                       pyxel.COLOR_RED if overlay.selected_construction is construction
                                       else pyxel.COLOR_GRAY)
                        else:
                            pyxel.text(150, 35 + adj_idx * 18, "Build",
                                       pyxel.COLOR_RED if overlay.selected_construction is construction
                                       else pyxel.COLOR_WHITE)
                        effects = 0
                        if construction.effect.wealth != 0:
                            sign = "+" if construction.effect.wealth > 0 else "-"
                            pyxel.text(30 + effects * 25, 42 + adj_idx * 18,
                                       f"{sign}{abs(round(construction.effect.wealth))}", pyxel.COLOR_YELLOW)
                            effects += 1
                        if construction.effect.harvest != 0:
                            sign = "+" if construction.effect.harvest > 0 else "-"
                            pyxel.text(30 + effects * 25, 42 + adj_idx * 18,
                                       f"{sign}{abs(round(construction.effect.harvest))}", pyxel.COLOR_GREEN)
                            effects += 1
                        if construction.effect.zeal != 0:
                            sign = "+" if construction.effect.zeal > 0 else "-"
                            pyxel.text(30 + effects * 25, 42 + adj_idx * 18,
                                       f"{sign}{abs(round(construction.effect.zeal))}", pyxel.COLOR_RED)
                            effects += 1
                        if construction.effect.fortune != 0:
                            sign = "+" if construction.effect.fortune > 0 else "-"
                            pyxel.text(30 + effects * 25, 42 + adj_idx * 18,
                                       f"{sign}{abs(round(construction.effect.fortune))}", pyxel.COLOR_PURPLE)
                            effects += 1
                        if construction.effect.strength != 0:
                            sign = "+" if construction.effect.strength > 0 else "-"
                            pyxel.blt(30 + effects * 25, 42 + adj_idx * 18, 0, 0, 28, 8, 8)
                            pyxel.text(40 + effects * 25, 42 + adj_idx * 18,
                                       f"{sign}{abs(round(construction.effect.strength))}", pyxel.COLOR_WHITE)
                            effects += 1
                        if construction.effect.satisfaction != 0:
                            sign = "+" if construction.effect.satisfaction > 0 else "-"
                            satisfaction_u = 8 if construction.effect.satisfaction >= 0 else 16
                            pyxel.blt(30 + effects * 25, 42 + adj_idx * 18, 0, satisfaction_u, 28, 8, 8)
                            pyxel.text(40 + effects * 25, 42 + adj_idx * 18,
                                       f"{sign}{abs(round(construction.effect.satisfaction))}", pyxel.COLOR_WHITE)
                if overlay.selected_construction is not None and overlay.selected_construction.req_resources:
                    idx = overlay.available_constructions.index(overlay.selected_construction)
                    adj_idx = idx - overlay.construction_boundaries[0]
                    res = overlay.selected_construction.req_resources
                    if res.ore:
                        pyxel.rectb(130, 45 + adj_idx * 18, 60, 12, pyxel.COLOR_WHITE)
                        pyxel.rect(131, 46 + adj_idx * 18, 58, 10, pyxel.COLOR_BLACK)
                        if res.ore < 10:
                            pyxel.text(139, 48 + adj_idx * 18, f"Needs {res.ore} ore", pyxel.COLOR_GRAY)
                        else:
                            pyxel.text(136, 48 + adj_idx * 18, f"Needs {res.ore} ore", pyxel.COLOR_GRAY)
                    if res.timber:
                        pyxel.rectb(125, 45 + adj_idx * 18, 70, 12, pyxel.COLOR_WHITE)
                        pyxel.rect(126, 46 + adj_idx * 18, 68, 10, pyxel.COLOR_BLACK)
                        if res.timber < 10:
                            pyxel.text(134, 48 + adj_idx * 18, f"Needs {res.timber} timber", pyxel.COLOR_BROWN)
                        else:
                            pyxel.text(131, 48 + adj_idx * 18, f"Needs {res.timber} timber", pyxel.COLOR_BROWN)
                    if res.magma:
                        pyxel.rectb(127, 45 + adj_idx * 18, 66, 12, pyxel.COLOR_WHITE)
                        pyxel.rect(128, 46 + adj_idx * 18, 64, 10, pyxel.COLOR_BLACK)
                        if res.magma < 10:
                            pyxel.text(135, 48 + adj_idx * 18, f"Needs {res.magma} magma", pyxel.COLOR_RED)
                        else:
                            pyxel.text(133, 48 + adj_idx * 18, f"Needs {res.magma} magma", pyxel.COLOR_RED)
            elif overlay.current_construction_menu is ConstructionMenu.PROJECTS:
                for idx, project in enumerate(overlay.available_projects):
                    pyxel.text(30, 35 + idx * 18, project.name, pyxel.COLOR_WHITE)
                    pyxel.text(150, 35 + idx * 18, "Begin",
                               pyxel.COLOR_RED if overlay.selected_construction is project else pyxel.COLOR_WHITE)
                    match project.type:
                        case ProjectType.BOUNTIFUL:
                            pyxel.text(30, 42 + idx * 18, "Converts 25% of zeal to harvest.", pyxel.COLOR_GREEN)
                        case ProjectType.ECONOMICAL:
                            pyxel.text(30, 42 + idx * 18, "Converts 25% of zeal to wealth.", pyxel.COLOR_YELLOW)
                        case ProjectType.MAGICAL:
                            pyxel.text(30, 42 + idx * 18, "Converts 25% of zeal to fortune.", pyxel.COLOR_PURPLE)
                pyxel.text(32, 110, "All projects continue indefinitely.", pyxel.COLOR_WHITE)
            else:
                for idx, unit_plan in enumerate(overlay.available_unit_plans):
                    if overlay.unit_plan_boundaries[0] <= idx <= overlay.unit_plan_boundaries[1]:
                        adj_idx = idx - overlay.unit_plan_boundaries[0]
                        pyxel.text(30, 35 + adj_idx * 18,
                                   f"{unit_plan.name} ({math.ceil(unit_plan.cost / total_zeal)})",
                                   pyxel.COLOR_WHITE)
                        pyxel.text(146, 35 + adj_idx * 18, "Recruit",
                                   pyxel.COLOR_RED if overlay.selected_construction is unit_plan
                                   else pyxel.COLOR_WHITE)
                        pyxel.blt(30, 42 + adj_idx * 18, 0, 8, 36, 8, 8)
                        pyxel.text(45, 42 + adj_idx * 18, str(round(unit_plan.max_health)), pyxel.COLOR_WHITE)
                        power_u: int
                        if unit_plan.heals:
                            power_u = 40
                        elif isinstance(unit_plan, DeployerUnitPlan):
                            power_u = 48
                        else:
                            power_u = 0
                        pyxel.blt(60, 42 + adj_idx * 18, 0, power_u, 36, 8, 8)
                        pyxel.text(75, 42 + adj_idx * 18,
                                   str(unit_plan.max_capacity if isinstance(unit_plan, DeployerUnitPlan)
                                       else round(unit_plan.power)),
                                   pyxel.COLOR_WHITE)
                        pyxel.blt(90, 42 + adj_idx * 18, 0, 16, 36, 8, 8)
                        pyxel.text(105, 42 + adj_idx * 18, str(unit_plan.total_stamina), pyxel.COLOR_WHITE)
                        if unit_plan.can_settle:
                            pyxel.text(115, 42 + adj_idx * 18, "-1 LVL", pyxel.COLOR_WHITE)
            pyxel.text(90, 150, "Cancel",
                       pyxel.COLOR_RED if overlay.selected_construction is None else pyxel.COLOR_WHITE)
            match overlay.current_construction_menu:
                case ConstructionMenu.IMPROVEMENTS:
                    pyxel.text(130, 150, "Projects ->", pyxel.COLOR_WHITE)
                case ConstructionMenu.PROJECTS:
                    if len(overlay.available_constructions) > 0:
                        pyxel.text(25, 150, "<- Improvements", pyxel.COLOR_WHITE)
                    pyxel.text(140, 150, "Units ->", pyxel.COLOR_WHITE)
                case _:
                    pyxel.text(25, 150, "<- Projects", pyxel.COLOR_WHITE)
        # The standard overlay contains four separate views: blessings, vault (wealth and resources), settlements, and
        # victories.
        if OverlayType.STANDARD in overlay.showing:
            pyxel.load("resources/sprites.pyxres")
            pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
            pyxel.text(80, 30, "Game status", pyxel.COLOR_WHITE)
            match overlay.current_standard_overlay_view:
                case StandardOverlayView.BLESSINGS:
                    pyxel.text(84, 40, "Blessings", pyxel.COLOR_PURPLE)
                    pyxel.text(30, 55, "Ongoing", pyxel.COLOR_PURPLE)
                    if overlay.current_player.ongoing_blessing is not None:
                        ong_blessing = overlay.current_player.ongoing_blessing
                        remaining_work = ong_blessing.blessing.cost - ong_blessing.fortune_consumed
                        _, _, _, total_fortune = get_player_totals(overlay.current_player, is_night)
                        remaining_turns = math.ceil(remaining_work / total_fortune)
                        pyxel.text(30, 65, ong_blessing.blessing.name, pyxel.COLOR_WHITE)
                        pyxel.text(30, 75, f"{remaining_turns} turns remaining", pyxel.COLOR_WHITE)
                    else:
                        pyxel.text(30, 65, "None", pyxel.COLOR_RED)
                        pyxel.text(30, 75, "Press F to add one!", pyxel.COLOR_WHITE)
                    pyxel.text(30, 90, "Recently completed", pyxel.COLOR_PURPLE)
                    if overlay.current_player.blessings:
                        # This for loop will give us the five most recently completed blessings.
                        for idx, bls in enumerate(overlay.current_player.blessings[-1:-6:-1]):
                            pyxel.text(30, 100 + idx * 10, bls.name, pyxel.COLOR_WHITE)
                    else:
                        pyxel.text(30, 100, "None", pyxel.COLOR_GRAY)
                    pyxel.text(144, 150, "Vault ->", pyxel.COLOR_YELLOW)
                case StandardOverlayView.VAULT:
                    pyxel.text(91, 40, "Vault", pyxel.COLOR_YELLOW)
                    pyxel.text(30, 55, "Wealth", pyxel.COLOR_YELLOW)
                    wealth_per_turn = 0
                    for setl in overlay.current_player.settlements:
                        wealth_to_add, _, _, _ = get_setl_totals(overlay.current_player, setl, is_night, strict=True)
                        wealth_per_turn += wealth_to_add
                    for unit in overlay.current_player.units:
                        if not unit.garrisoned:
                            wealth_per_turn -= unit.plan.cost / 10
                    sign = "+" if wealth_per_turn > 0 else "-"
                    pyxel.text(30, 65,
                               f"{round(overlay.current_player.wealth)} ({sign}{abs(round(wealth_per_turn, 2))})",
                               pyxel.COLOR_WHITE)
                    pyxel.text(30, 80, "Resources", pyxel.COLOR_YELLOW)
                    pyxel.text(30, 90, "Ore", pyxel.COLOR_GRAY)
                    pyxel.text(70, 90, str(overlay.current_player.resources.ore), pyxel.COLOR_WHITE)
                    pyxel.text(30, 100, "Timber", pyxel.COLOR_BROWN)
                    pyxel.text(70, 100, str(overlay.current_player.resources.timber), pyxel.COLOR_WHITE)
                    pyxel.text(30, 110, "Magma", pyxel.COLOR_RED)
                    pyxel.text(70, 110, str(overlay.current_player.resources.magma), pyxel.COLOR_WHITE)
                    pyxel.text(95, 90, "Aurora", pyxel.COLOR_YELLOW)
                    pyxel.text(150, 90, f"x{overlay.current_player.resources.aurora}", pyxel.COLOR_WHITE)
                    pyxel.text(95, 100, "Bloodstone", pyxel.COLOR_RED)
                    pyxel.text(150, 100, f"x{overlay.current_player.resources.bloodstone}", pyxel.COLOR_WHITE)
                    pyxel.text(95, 110, "Obsidian", pyxel.COLOR_GRAY)
                    pyxel.text(150, 110, f"x{overlay.current_player.resources.obsidian}", pyxel.COLOR_WHITE)
                    if overlay.current_game_config.climatic_effects:
                        pyxel.text(95, 120, "Sunstone", pyxel.COLOR_ORANGE)
                        pyxel.text(150, 120, f"x{overlay.current_player.resources.sunstone}", pyxel.COLOR_WHITE)
                        pyxel.text(95, 130, "Aquamarine", pyxel.COLOR_LIGHT_BLUE)
                        pyxel.text(150, 130, f"x{overlay.current_player.resources.aquamarine}", pyxel.COLOR_WHITE)
                    else:
                        pyxel.text(95, 120, "Aquamarine", pyxel.COLOR_LIGHT_BLUE)
                        pyxel.text(150, 120, f"x{overlay.current_player.resources.aquamarine}", pyxel.COLOR_WHITE)
                    pyxel.text(25, 150, "<- Blessings", pyxel.COLOR_PURPLE)
                    pyxel.text(120, 150, "Settlements ->", pyxel.COLOR_LIME)
                case StandardOverlayView.SETTLEMENTS:
                    pyxel.text(80, 40, "Settlements", pyxel.COLOR_LIME)
                    pyxel.blt(100, 55, 0, 8, 28, 8, 8)
                    pyxel.blt(117, 55, 0, 0, 28, 8, 8)
                    pyxel.blt(130, 55, 0, 0, 116, 8, 8)
                    pyxel.blt(140, 55, 0, 0, 36, 8, 8)
                    if 9 < len(overlay.current_player.settlements) != overlay.settlement_status_boundaries[1]:
                        pyxel.blt(21, 135, 0, 0, 76, 8, 8)
                    if len(overlay.current_player.settlements) > 9 and overlay.settlement_status_boundaries[0] != 0:
                        pyxel.blt(21, 55, 0, 8, 76, 8, 8)
                    start_idx = overlay.settlement_status_boundaries[0]
                    end_idx = overlay.settlement_status_boundaries[1]
                    player_setls = overlay.current_player.settlements
                    player_setls.sort(key=lambda s: s.level, reverse=True)
                    for idx, setl in enumerate(player_setls[start_idx:end_idx]):
                        pyxel.text(30, 65 + idx * 8, f"{setl.name} ({setl.level})",
                                   pyxel.COLOR_RED if setl.besieged else pyxel.COLOR_WHITE)
                        pyxel.text(100, 65 + idx * 8, str(round(setl.satisfaction)),
                                   pyxel.COLOR_RED if setl.satisfaction < 50 else pyxel.COLOR_GREEN)
                        pyxel.text(115, 65 + idx * 8, str(round(setl.strength)),
                                   pyxel.COLOR_RED if setl.besieged else pyxel.COLOR_WHITE)

                        current_work = setl.current_work
                        if current_work is not None and not isinstance(current_work.construction, Project):
                            remaining_work = current_work.construction.cost - current_work.zeal_consumed
                            total_zeal = max(sum(quad.zeal for quad in setl.quads) +
                                             sum(imp.effect.zeal for imp in setl.improvements), 1)
                            total_zeal += (setl.level - 1) * 0.25 * total_zeal
                            if overlay.current_player.faction == Faction.AGRICULTURISTS:
                                total_zeal *= 0.75
                            elif overlay.current_player.faction == Faction.FUNDAMENTALISTS:
                                total_zeal *= 1.25
                            remaining_turns = math.ceil(remaining_work / total_zeal)
                            pyxel.text(130, 65 + idx * 8, str(remaining_turns), pyxel.COLOR_WHITE)
                        else:
                            pyxel.text(130, 65 + idx * 8, "-", pyxel.COLOR_WHITE)

                        pyxel.text(140, 65 + idx * 8, str(len(setl.garrison)), pyxel.COLOR_WHITE)

                        harvest_u: int
                        match setl.harvest_status:
                            case HarvestStatus.STANDARD:
                                harvest_u = 0
                            case HarvestStatus.PLENTIFUL:
                                harvest_u = 8
                            case _:
                                harvest_u = 16
                        pyxel.blt(155, 63 + idx * 8, 0, harvest_u, 100, 8, 8)

                        wealth_u: int
                        match setl.economic_status:
                            case EconomicStatus.RECESSION:
                                wealth_u = 0
                            case EconomicStatus.STANDARD:
                                wealth_u = 8
                            case _:
                                wealth_u = 16
                        pyxel.blt(165, 63 + idx * 8, 0, wealth_u, 108, 8, 8)
                    pyxel.text(25, 150, "<- Vault", pyxel.COLOR_YELLOW)
                    pyxel.text(128, 150, "Victories ->", pyxel.COLOR_GREEN)
                case StandardOverlayView.VICTORIES:
                    pyxel.text(83, 40, "Victories", pyxel.COLOR_GREEN)
                    pyxel.text(30, 55, "Elimination", pyxel.COLOR_RED)
                    if VictoryType.ELIMINATION in overlay.current_player.imminent_victories:
                        pyxel.blt(76, 53, 0, 16, 124, 8, 8)
                    pyxel.text(140, 55,
                               f"{len(overlay.current_player.settlements)}/{overlay.total_settlement_count}",
                               pyxel.COLOR_WHITE)
                    if overlay.current_player.faction != Faction.CONCENTRATED:
                        pyxel.text(30, 70, "Jubilation", pyxel.COLOR_GREEN)
                        if VictoryType.JUBILATION in overlay.current_player.imminent_victories:
                            pyxel.blt(72, 68, 0, 16, 124, 8, 8)
                        pyxel.text(130, 70,
                                   f"{len([s for s in overlay.current_player.settlements if s.satisfaction == 100])}/5,"
                                   f" {overlay.current_player.jubilation_ctr}/25",
                                   pyxel.COLOR_WHITE)
                        pyxel.text(30, 85, "Gluttony", pyxel.COLOR_GREEN)
                        if VictoryType.GLUTTONY in overlay.current_player.imminent_victories:
                            pyxel.blt(64, 83, 0, 16, 124, 8, 8)
                        pyxel.text(140, 85,
                                   f"{len([s for s in overlay.current_player.settlements if s.level == 10])}/10",
                                   pyxel.COLOR_WHITE)
                    else:
                        pyxel.text(30, 70, "Jubilation", pyxel.COLOR_GRAY)
                        pyxel.text(115, 70, "N/A for faction", pyxel.COLOR_GRAY)
                        pyxel.text(30, 85, "Gluttony", pyxel.COLOR_GRAY)
                        pyxel.text(115, 85, "N/A for faction", pyxel.COLOR_GRAY)
                    pyxel.text(30, 100, "Affluence", pyxel.COLOR_YELLOW)
                    if VictoryType.AFFLUENCE in overlay.current_player.imminent_victories:
                        pyxel.blt(68, 98, 0, 16, 124, 8, 8)
                    pyxel.text(128, 100, f"{round(overlay.current_player.accumulated_wealth)}/100000",
                               pyxel.COLOR_WHITE)
                    pyxel.text(30, 115, "Vigour", pyxel.COLOR_ORANGE)
                    if VictoryType.VIGOUR in overlay.current_player.imminent_victories:
                        pyxel.blt(56, 113, 0, 16, 124, 8, 8)
                    pyxel.text(132, 115,
                               # We can hard-code the second part of this to be 0/1, since once the player builds the
                               # Holy Sanctum, the game ends.
                               f"{1 if BLESSINGS['anc_his'] in overlay.current_player.blessings else 0}/1, 0/1",
                               pyxel.COLOR_WHITE)
                    pyxel.text(30, 130, "Serendipity", pyxel.COLOR_PURPLE)
                    if VictoryType.SERENDIPITY in overlay.current_player.imminent_victories:
                        pyxel.blt(76, 128, 0, 16, 124, 8, 8)
                    pyxel.text(142, 130,
                               f"{len([b for b in overlay.current_player.blessings if 'Piece of' in b.name])}/3",
                               pyxel.COLOR_WHITE)
                    pyxel.text(25, 150, "<- Settlements", pyxel.COLOR_LIME)
        # The settlement click overlay displays the two options available to the player when interacting with an
        # enemy settlement: attack or besiege.
        if OverlayType.SETL_CLICK in overlay.showing:
            pyxel.rectb(50, 60, 100, 70, pyxel.COLOR_WHITE)
            pyxel.rect(51, 61, 98, 68, pyxel.COLOR_BLACK)
            name_len = len(overlay.attacked_settlement.name)
            x_offset = 11 - name_len
            pyxel.text(82 + x_offset, 70, str(overlay.attacked_settlement.name),
                       overlay.attacked_settlement_owner.colour)
            pyxel.blt(90, 78, 0, 0, 28, 8, 8)
            pyxel.text(100, 80, str(round(overlay.attacked_settlement.strength)), pyxel.COLOR_WHITE)
            pyxel.text(68, 95, "Attack",
                       pyxel.COLOR_RED
                       if overlay.setl_attack_opt is SettlementAttackType.ATTACK else pyxel.COLOR_WHITE)
            pyxel.text(110, 95, "Besiege",
                       pyxel.COLOR_RED
                       if overlay.setl_attack_opt is SettlementAttackType.BESIEGE else pyxel.COLOR_WHITE)
            pyxel.text(90, 115, "Cancel", pyxel.COLOR_RED if overlay.setl_attack_opt is None else pyxel.COLOR_WHITE)
        # The blessing overlay displays the available blessings that the player can undergo, along with the types of
        # improvements that they unlock.
        if OverlayType.BLESSING in overlay.showing:
            pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
            pyxel.text(65, 25, "Available blessings", pyxel.COLOR_PURPLE)
            _, _, _, total_fortune = get_player_totals(overlay.current_player, is_night)
            for idx, blessing in enumerate(overlay.available_blessings):
                if overlay.blessing_boundaries[0] <= idx <= overlay.blessing_boundaries[1]:
                    adj_idx = idx - overlay.blessing_boundaries[0]
                    pyxel.text(30, 35 + adj_idx * 18,
                               f"{blessing.name} ({math.ceil(blessing.cost / total_fortune)})", pyxel.COLOR_WHITE)
                    pyxel.text(145, 35 + adj_idx * 18, "Undergo",
                               pyxel.COLOR_RED if overlay.selected_blessing is blessing else pyxel.COLOR_WHITE)
                    imps = get_unlockable_improvements(blessing)
                    units = get_unlockable_units(blessing)
                    pyxel.text(30, 42 + adj_idx * 18, "Unlocks:", pyxel.COLOR_WHITE)
                    types_unlockable: typing.List[ImprovementType] = []
                    if len(imps) > 0:
                        for imp in imps:
                            if imp.effect.wealth > 0:
                                types_unlockable.append(ImprovementType.ECONOMICAL)
                            if imp.effect.harvest > 0:
                                types_unlockable.append(ImprovementType.BOUNTIFUL)
                            if imp.effect.zeal > 0:
                                types_unlockable.append(ImprovementType.INDUSTRIAL)
                            if imp.effect.fortune > 0:
                                types_unlockable.append(ImprovementType.MAGICAL)
                            if imp.effect.strength > 0:
                                types_unlockable.append(ImprovementType.INTIMIDATORY)
                            if imp.effect.satisfaction > 0:
                                types_unlockable.append(ImprovementType.PANDERING)
                        if len(types_unlockable) > 0:
                            for type_idx, unl_type in enumerate(set(types_unlockable)):
                                uv_coords: (int, int)
                                match unl_type:
                                    case ImprovementType.ECONOMICAL:
                                        uv_coords = 0, 44
                                    case ImprovementType.BOUNTIFUL:
                                        uv_coords = 8, 44
                                    case ImprovementType.INDUSTRIAL:
                                        uv_coords = 16, 44
                                    case ImprovementType.MAGICAL:
                                        uv_coords = 24, 44
                                    case ImprovementType.INTIMIDATORY:
                                        uv_coords = 0, 28
                                    case _:
                                        uv_coords = 8, 28
                                pyxel.blt(65 + type_idx * 10, 41 + adj_idx * 18, 0, uv_coords[0], uv_coords[1], 8, 8)
                            if units:
                                pyxel.blt(65 + len(set(types_unlockable)) * 10, 41 + adj_idx * 18, 0, 0, 36, 8, 8)
                        else:
                            pyxel.text(65, 41 + adj_idx * 18, "victory", pyxel.COLOR_GREEN)
                    else:
                        pyxel.text(65, 41 + adj_idx * 18, "victory", pyxel.COLOR_GREEN)
            pyxel.text(90, 150, "Cancel", pyxel.COLOR_RED if overlay.selected_blessing is None else pyxel.COLOR_WHITE)
        # The tutorial overlay displays an instructional message to the player w.r.t. founding their first
        # settlement.
        if OverlayType.TUTORIAL in overlay.showing:
            pyxel.rectb(8, 140, 184, 25, pyxel.COLOR_WHITE)
            pyxel.rect(9, 141, 182, 23, pyxel.COLOR_BLACK)
            pyxel.text(60, 143, "Welcome to Microcosm!", pyxel.COLOR_WHITE)
            pyxel.text(12, 153, "Click a quad to found your first settlement.", pyxel.COLOR_WHITE)
        # The pause overlay displays the available pause options for the player to select.
        if OverlayType.PAUSE in overlay.showing:
            pyxel.rectb(52, 60, 96, 63, pyxel.COLOR_WHITE)
            pyxel.rect(53, 61, 94, 61, pyxel.COLOR_BLACK)
            pyxel.text(80, 68, "Game paused", pyxel.COLOR_WHITE)
            pyxel.text(88, 80, "Resume",
                       pyxel.COLOR_RED if overlay.pause_option is PauseOption.RESUME else pyxel.COLOR_WHITE)
            if overlay.has_saved:
                pyxel.text(88, 90, "Saved!", pyxel.COLOR_GREEN)
            else:
                pyxel.text(90, 90, "Save",
                           pyxel.COLOR_RED if overlay.pause_option is PauseOption.SAVE else pyxel.COLOR_WHITE)
            pyxel.text(84, 100, "Controls",
                       pyxel.COLOR_RED if overlay.pause_option is PauseOption.CONTROLS else pyxel.COLOR_WHITE)
            pyxel.text(90, 110, "Quit",
                       pyxel.COLOR_RED if overlay.pause_option is PauseOption.QUIT else pyxel.COLOR_WHITE)
        # The controls overlay displays the controls that are not permanent fixtures at the bottom of the screen.
        if OverlayType.CONTROLS in overlay.showing:
            pyxel.load("resources/sprites.pyxres")
            if not overlay.show_additional_controls:
                pyxel.rectb(10, 20, 180, 144, pyxel.COLOR_WHITE)
                pyxel.rect(11, 21, 178, 142, pyxel.COLOR_BLACK)
                pyxel.text(85, 30, "Controls", pyxel.COLOR_WHITE)
                pyxel.text(23, 45, "ARROWS", pyxel.COLOR_WHITE)
                pyxel.text(83, 45, "Navigate menus/pan map", pyxel.COLOR_WHITE)
                pyxel.text(23, 55, "CTRL + ARROWS", pyxel.COLOR_WHITE)
                pyxel.text(83, 55, "Quickly pan the map", pyxel.COLOR_WHITE)
                pyxel.text(23, 65, "R CLICK", pyxel.COLOR_WHITE)
                pyxel.text(83, 65, "Show quad yield", pyxel.COLOR_WHITE)
                pyxel.text(23, 75, "L CLICK", pyxel.COLOR_WHITE)
                pyxel.text(83, 75, "Move/select/attack units", pyxel.COLOR_WHITE)
                pyxel.text(23, 85, "C", pyxel.COLOR_WHITE)
                pyxel.text(83, 85, "Add/change construction", pyxel.COLOR_WHITE)
                pyxel.text(23, 95, "F", pyxel.COLOR_WHITE)
                pyxel.text(83, 95, "Add/change blessing", pyxel.COLOR_WHITE)
                pyxel.text(23, 105, "D", pyxel.COLOR_WHITE)
                pyxel.text(83, 105, "Deploy unit", pyxel.COLOR_WHITE)
                pyxel.text(23, 115, "N", pyxel.COLOR_WHITE)
                pyxel.text(83, 115, "Next song", pyxel.COLOR_WHITE)
                pyxel.text(23, 125, "B", pyxel.COLOR_WHITE)
                pyxel.text(83, 125, "Buyout construction", pyxel.COLOR_WHITE)
                pyxel.text(23, 135, "A", pyxel.COLOR_WHITE)
                pyxel.text(83, 135, "Auto-select construction", pyxel.COLOR_WHITE)

                # Down arrow
                pyxel.blt(180, 150, 0, 0, 76, 8, 8)

                pyxel.text(54, 150, "Press SPACE to go back.", pyxel.COLOR_WHITE)
            else:
                pyxel.rectb(10, 20, 180, 144, pyxel.COLOR_WHITE)
                pyxel.rect(11, 21, 178, 142, pyxel.COLOR_BLACK)
                pyxel.text(85, 30, "Controls", pyxel.COLOR_WHITE)
                pyxel.text(23, 45, "M", pyxel.COLOR_WHITE)
                pyxel.text(83, 45, "Go through movable units", pyxel.COLOR_WHITE)
                pyxel.text(23, 55, "J", pyxel.COLOR_WHITE)
                pyxel.text(83, 55, "Jump to idle settlement", pyxel.COLOR_WHITE)
                pyxel.text(23, 65, "X", pyxel.COLOR_WHITE)
                pyxel.text(83, 65, "Disband unit", pyxel.COLOR_WHITE)

                # Up arrow
                pyxel.blt(180, 150, 0, 8, 76, 8, 8)

                pyxel.text(54, 150, "Press SPACE to go back.", pyxel.COLOR_WHITE)
