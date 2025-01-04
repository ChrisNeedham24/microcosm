import random
import typing
from collections import Counter
from enum import Enum

import pyxel

from source.networking.client import dispatch_event, get_identifier
from source.networking.events import FoundSettlementEvent, EventType, UpdateAction, MoveUnitEvent, DeployUnitEvent, \
    GarrisonUnitEvent, InvestigateEvent, AttackUnitEvent, HealUnitEvent, BoardDeployerEvent, DeployerDeployEvent
from source.util.calculator import calculate_yield_for_quad, attack, investigate_relic, heal, \
    get_resources_for_settlement, update_player_quads_seen_around_point
from source.foundation.catalogue import get_default_unit, Namer
from source.foundation.models import Player, Quad, Biome, Settlement, Unit, Heathen, GameConfig, InvestigationResult, \
    Faction, DeployerUnit, ResourceCollection
from source.display.overlay import Overlay
from source.display.overlay_display import display_overlay


class HelpOption(Enum):
    """
    Represents the help text options that are iterated through at the bottom of the screen.
    """
    SETTLEMENT = "TAB: Next settlement"
    UNIT = "SPACE: Next unit"
    OVERLAY = "SHIFT: Show status overlay"
    PAUSE = "ESC: Pause"
    END_TURN = "ENTER: End turn"


class Board:
    """
    The class responsible for drawing everything in-game (i.e. not on menu).
    """

    def __init__(self, cfg: GameConfig, namer: Namer, quads: typing.List[typing.List[Quad]] = None,
                 player_idx: int = 0, game_name: typing.Optional[str] = None):
        """
        Initialises the board with the given config and quads, if supplied.
        :param cfg: The game config.
        :param namer: The Namer instance to use for settlement names.
        :param quads: The quads loaded in, if we are loading a game.
        :param player_idx: The index of the player in the overall list of players. Will always be zero for single-player
                           games, but will be variable for multiplayer ones.
        :param game_name: The name of the current multiplayer game. Will be None for single-player games.
        """
        self.current_help = HelpOption.SETTLEMENT
        self.help_time_bank = 0
        self.attack_time_bank = 0
        self.siege_time_bank = 0
        self.construction_prompt_time_bank = 0
        self.heal_time_bank = 0
        self.player_change_time_bank = 0

        self.game_config: GameConfig = cfg
        self.namer: Namer = namer

        # We allow quads to be supplied here in load game cases.
        if quads is not None:
            self.quads = quads
        else:
            self.quads: typing.List[typing.List[typing.Optional[Quad]]] = [[None] * 100 for _ in range(90)]
            random.seed()
            self.generate_quads(cfg.biome_clustering, cfg.climatic_effects)

        self.quad_selected: typing.Optional[Quad] = None

        self.overlay = Overlay(self.game_config)
        self.selected_settlement: typing.Optional[Settlement] = None
        self.deploying_army = False
        self.deploying_army_from_unit = False
        self.selected_unit: typing.Optional[Unit | Heathen] = None

        self.player_idx: int = player_idx
        self.game_name: typing.Optional[str] = game_name
        self.waiting_for_other_players: bool = False
        self.checking_game_sync: bool = False

    def draw(self, players: typing.List[Player], map_pos: (int, int), turn: int, heathens: typing.List[Heathen],
             is_night: bool, turns_until_change: int):  # pragma: no cover
        """
        Draws the board and its objects to the screen.
        :param players: The players in the game.
        :param map_pos: The current map position.
        :param turn: The current turn.
        :param heathens: The list of Heathens to draw.
        :param is_night: Whether it is currently night.
        :param turns_until_change: The number of turns until a climatic change will occur (day -> night, or vice versa).
        """
        # Clear the screen to black.
        pyxel.cls(0)
        pyxel.rectb(0, 0, 200, 184, pyxel.COLOR_WHITE)

        pyxel.load("resources/quads.pyxres")
        selected_quad_coords: (int, int) = None
        quads_to_show: typing.Set[typing.Tuple[int, int]] = set()
        # At nighttime, the player can only see a few quads around their settlements and units. However, players of the
        # Nocturne faction have no vision impacts at nighttime. In addition to this, settlements with one or more
        # sunstone resources have extended vision proportionate to the number of sunstone resources they have.
        if is_night and players[self.player_idx].faction != Faction.NOCTURNE:
            for setl in players[self.player_idx].settlements:
                vision_range = 3 * (1 + setl.resources.sunstone)
                for setl_quad in setl.quads:
                    for i in range(setl_quad.location[0] - vision_range, setl_quad.location[0] + vision_range + 1):
                        for j in range(setl_quad.location[1] - vision_range, setl_quad.location[1] + vision_range + 1):
                            quads_to_show.add((i, j))
            for unit in players[self.player_idx].units:
                for i in range(unit.location[0] - 3, unit.location[0] + 4):
                    for j in range(unit.location[1] - 3, unit.location[1] + 4):
                        quads_to_show.add((i, j))
            # Players of the Infidels faction share vision with Heathen units.
            if players[self.player_idx].faction == Faction.INFIDELS:
                for heathen in heathens:
                    for i in range(heathen.location[0] - 5, heathen.location[0] + 6):
                        for j in range(heathen.location[1] - 5, heathen.location[1] + 6):
                            quads_to_show.add((i, j))
        else:
            quads_to_show = players[self.player_idx].quads_seen
        fog_of_war_impacts: bool = self.game_config.fog_of_war or \
            (is_night and players[self.player_idx].faction != Faction.NOCTURNE)
        # Draw the quads.
        for i in range(map_pos[0], map_pos[0] + 24):
            for j in range(map_pos[1], map_pos[1] + 22):
                if 0 <= i <= 99 and 0 <= j <= 89:
                    # Draw the quad if fog of war is off, or if the player has seen the quad, or we're in the tutorial.
                    # This same logic applies to all subsequent draws.
                    if (i, j) in quads_to_show or \
                            len(players[self.player_idx].settlements) == 0 or \
                            not fog_of_war_impacts:
                        quad = self.quads[j][i]
                        match quad.biome:
                            case Biome.DESERT:
                                quad_x = 0
                            case Biome.FOREST:
                                quad_x = 8
                            case Biome.SEA:
                                quad_x = 16
                            case _:
                                quad_x = 24
                        match quad.resource:
                            case ResourceCollection(ore=1):
                                quad_y = 28
                            case ResourceCollection(timber=1):
                                quad_y = 36
                            case ResourceCollection(magma=1):
                                quad_y = 44
                            case ResourceCollection(aurora=1):
                                quad_y = 52
                            case ResourceCollection(bloodstone=1):
                                quad_y = 60
                            case ResourceCollection(obsidian=1):
                                quad_y = 68
                            case ResourceCollection(sunstone=1):
                                quad_y = 76
                            case ResourceCollection(aquamarine=1):
                                quad_y = 84
                            case _:
                                quad_y = 4

                        if quad.is_relic:
                            quad_y = 20

                        if is_night:
                            quad_x += 32
                        pyxel.blt((i - map_pos[0]) * 8 + 4, (j - map_pos[1]) * 8 + 4, 0, quad_x, quad_y, 8, 8)
                        if quad.selected:
                            selected_quad_coords = i, j
                            pyxel.rectb((i - map_pos[0]) * 8 + 4, (j - map_pos[1]) * 8 + 4, 8, 8, pyxel.COLOR_RED)
                    elif not is_night:
                        pyxel.blt((i - map_pos[0]) * 8 + 4, (j - map_pos[1]) * 8 + 4, 0, 0, 12, 8, 8)

        pyxel.load("resources/sprites.pyxres")
        # Draw the heathens.
        for heathen in heathens:
            if (not fog_of_war_impacts or heathen.location in quads_to_show) and \
                    map_pos[0] <= heathen.location[0] < map_pos[0] + 24 and \
                    map_pos[1] <= heathen.location[1] < map_pos[1] + 22:
                quad: Quad = self.quads[heathen.location[1]][heathen.location[0]]
                match quad.biome:
                    case Biome.DESERT:
                        heathen_x = 0
                    case Biome.FOREST:
                        heathen_x = 8
                    case Biome.SEA:
                        heathen_x = 16
                    case _:
                        heathen_x = 24
                if is_night:
                    heathen_x += 32
                pyxel.blt((heathen.location[0] - map_pos[0]) * 8 + 4,
                          (heathen.location[1] - map_pos[1]) * 8 + 4, 0, heathen_x, 60, 8, 8)
                # Outline a heathen if the player can attack it.
                if self.selected_unit is not None and not isinstance(self.selected_unit, Heathen) and \
                        self.selected_unit in players[self.player_idx].units and \
                        not self.selected_unit.has_acted and \
                        abs(self.selected_unit.location[0] - heathen.location[0]) <= 1 and \
                        abs(self.selected_unit.location[1] - heathen.location[1]) <= 1:
                    pyxel.rectb((heathen.location[0] - map_pos[0]) * 8 + 4,
                                (heathen.location[1] - map_pos[1]) * 8 + 4, 8, 8, pyxel.COLOR_RED)
        for player in players:
            # Draw all player units.
            for unit in player.units:
                if (not fog_of_war_impacts or unit.location in quads_to_show) and \
                        map_pos[0] <= unit.location[0] < map_pos[0] + 24 and \
                        map_pos[1] <= unit.location[1] < map_pos[1] + 22:
                    quad: Quad = self.quads[unit.location[1]][unit.location[0]]
                    match quad.biome:
                        case Biome.DESERT:
                            unit_x = 0
                        case Biome.FOREST:
                            unit_x = 8
                        case Biome.SEA:
                            unit_x = 16
                        case _:
                            unit_x = 24
                    if is_night:
                        unit_x += 32
                    pyxel.blt((unit.location[0] - map_pos[0]) * 8 + 4,
                              (unit.location[1] - map_pos[1]) * 8 + 4, 0, unit_x, 16, 8, 8)
                    pyxel.rectb((unit.location[0] - map_pos[0]) * 8 + 4,
                                (unit.location[1] - map_pos[1]) * 8 + 4, 8, 8, player.colour)
                    # Highlight the player-selected unit, if there is one.
                    if self.selected_unit is unit and unit in players[self.player_idx].units:
                        movement = self.selected_unit.remaining_stamina
                        pyxel.rectb((self.selected_unit.location[0] - map_pos[0]) * 8 + 4 - (movement * 8),
                                    (self.selected_unit.location[1] - map_pos[1]) * 8 + 4 - (movement * 8),
                                    (2 * movement + 1) * 8, (2 * movement + 1) * 8, pyxel.COLOR_WHITE)
        for player in players:
            # Draw all player settlements.
            for settlement in player.settlements:
                if (not fog_of_war_impacts or settlement.location in quads_to_show) and \
                        map_pos[0] <= settlement.location[0] < map_pos[0] + 24 and \
                        map_pos[1] <= settlement.location[1] < map_pos[1] + 22:
                    for setl_quad in settlement.quads:
                        match setl_quad.biome:
                            case Biome.DESERT:
                                setl_x = 0
                            case Biome.FOREST:
                                setl_x = 8
                            case Biome.SEA:
                                setl_x = 16
                            case _:
                                setl_x = 24
                        if is_night and not settlement.besieged:
                            setl_x += 32
                        pyxel.blt((setl_quad.location[0] - map_pos[0]) * 8 + 4,
                                  (setl_quad.location[1] - map_pos[1]) * 8 + 4, 0, setl_x,
                                  68 if settlement.besieged else 4, 8, 8)

        # Only draw settlement additions if we're not deploying from a unit, as we want the board to be as clear as
        # possible in those situations.
        if not self.deploying_army_from_unit:
            for player in players:
                for settlement in player.settlements:
                    if settlement.location in quads_to_show or not fog_of_war_impacts:
                        # Draw name tags for non-selected settlements.
                        if self.selected_settlement is not settlement:
                            name_len = len(settlement.name)
                            x_offset = 11 - name_len
                            base_x_pos = (settlement.location[0] - map_pos[0]) * 8
                            base_y_pos = (settlement.location[1] - map_pos[1]) * 8
                            # Besieged settlements are displayed with a black background, along with their remaining
                            # strength.
                            if settlement.besieged:
                                pyxel.rect(base_x_pos - 17, base_y_pos - 8, 52, 10,
                                           pyxel.COLOR_WHITE if is_night else pyxel.COLOR_BLACK)
                                pyxel.text(base_x_pos - 10 + x_offset, base_y_pos - 6, settlement.name, player.colour)
                                # We need to base the size of the strength container on the length of the string, so
                                # that it is centred.
                                strength_as_str = str(round(settlement.strength))
                                match len(strength_as_str):
                                    case 3:
                                        pyxel.rect(base_x_pos, base_y_pos - 16, 16, 10,
                                                   pyxel.COLOR_WHITE if is_night else pyxel.COLOR_BLACK)
                                        pyxel.text(base_x_pos + 2, base_y_pos - 14, strength_as_str, pyxel.COLOR_RED)
                                    case 2:
                                        pyxel.rect(base_x_pos + 3, base_y_pos - 16, 11, 10,
                                                   pyxel.COLOR_WHITE if is_night else pyxel.COLOR_BLACK)
                                        pyxel.text(base_x_pos + 5, base_y_pos - 14, strength_as_str, pyxel.COLOR_RED)
                                    case 1:
                                        pyxel.rect(base_x_pos + 4, base_y_pos - 16, 8, 10,
                                                   pyxel.COLOR_WHITE if is_night else pyxel.COLOR_BLACK)
                                        pyxel.text(base_x_pos + 7, base_y_pos - 14, strength_as_str, pyxel.COLOR_RED)
                            else:
                                pyxel.rectb(base_x_pos - 17, base_y_pos - 8, 52, 10,
                                            pyxel.COLOR_WHITE if is_night else pyxel.COLOR_BLACK)
                                pyxel.rect(base_x_pos - 16, base_y_pos - 7, 50, 8, player.colour)
                                pyxel.text(base_x_pos - 10 + x_offset, base_y_pos - 6, settlement.name,
                                           pyxel.COLOR_WHITE)
                        else:
                            for setl_quad in settlement.quads:
                                pyxel.rectb((setl_quad.location[0] - map_pos[0]) * 8 + 4,
                                            (setl_quad.location[1] - map_pos[1]) * 8 + 4, 8, 8, pyxel.COLOR_RED)

        # For the selected quad, display its yield.
        if self.quad_selected is not None and selected_quad_coords is not None and \
                (selected_quad_coords in quads_to_show or len(players[self.player_idx].settlements) == 0 or
                 not fog_of_war_impacts):
            x_offset = 30 if selected_quad_coords[0] - map_pos[0] <= 8 else 0
            y_offset = -34 if selected_quad_coords[1] - map_pos[1] >= 36 else 0
            base_x_pos = (selected_quad_coords[0] - map_pos[0]) * 8 + x_offset
            base_y_pos = (selected_quad_coords[1] - map_pos[1]) * 8 + y_offset
            if self.quad_selected.resource:
                pyxel.rectb(base_x_pos - 22, base_y_pos + 8, 50, 22, pyxel.COLOR_WHITE)
                pyxel.rect(base_x_pos - 21, base_y_pos + 9, 48, 20, pyxel.COLOR_BLACK)
                pyxel.text(base_x_pos - 18, base_y_pos + 12, f"{round(self.quad_selected.wealth)}", pyxel.COLOR_YELLOW)
                pyxel.text(base_x_pos - 12, base_y_pos + 12, f"{round(self.quad_selected.harvest)}", pyxel.COLOR_GREEN)
                pyxel.text(base_x_pos - 6, base_y_pos + 12, f"{round(self.quad_selected.zeal)}", pyxel.COLOR_RED)
                pyxel.text(base_x_pos, base_y_pos + 12, f"{round(self.quad_selected.fortune)}", pyxel.COLOR_PURPLE)
                if self.quad_selected.resource.ore:
                    pyxel.text(base_x_pos - 18, base_y_pos + 20, "Ore", pyxel.COLOR_GRAY)
                elif self.quad_selected.resource.timber:
                    pyxel.text(base_x_pos - 18, base_y_pos + 20, "Timber", pyxel.COLOR_BROWN)
                elif self.quad_selected.resource.magma:
                    pyxel.text(base_x_pos - 18, base_y_pos + 20, "Magma", pyxel.COLOR_RED)
                elif self.quad_selected.resource.aurora:
                    pyxel.text(base_x_pos - 18, base_y_pos + 20, "Aurora", pyxel.COLOR_YELLOW)
                elif self.quad_selected.resource.bloodstone:
                    pyxel.text(base_x_pos - 18, base_y_pos + 20, "Bloodstone", pyxel.COLOR_RED)
                elif self.quad_selected.resource.obsidian:
                    pyxel.text(base_x_pos - 18, base_y_pos + 20, "Obsidian", pyxel.COLOR_GRAY)
                elif self.quad_selected.resource.sunstone:
                    pyxel.text(base_x_pos - 18, base_y_pos + 20, "Sunstone", pyxel.COLOR_ORANGE)
                elif self.quad_selected.resource.aquamarine:
                    pyxel.text(base_x_pos - 18, base_y_pos + 20, "Aquamarine", pyxel.COLOR_LIGHT_BLUE)
            else:
                pyxel.rectb(base_x_pos - 22, base_y_pos + 8, 30, 12, pyxel.COLOR_WHITE)
                pyxel.rect(base_x_pos - 21, base_y_pos + 9, 28, 10, pyxel.COLOR_BLACK)
                pyxel.text(base_x_pos - 18, base_y_pos + 12, f"{round(self.quad_selected.wealth)}", pyxel.COLOR_YELLOW)
                pyxel.text(base_x_pos - 12, base_y_pos + 12, f"{round(self.quad_selected.harvest)}", pyxel.COLOR_GREEN)
                pyxel.text(base_x_pos - 6, base_y_pos + 12, f"{round(self.quad_selected.zeal)}", pyxel.COLOR_RED)
                pyxel.text(base_x_pos, base_y_pos + 12, f"{round(self.quad_selected.fortune)}", pyxel.COLOR_PURPLE)

        if self.deploying_army:
            for setl_quad in self.selected_settlement.quads:
                for i in range(setl_quad.location[0] - 1, setl_quad.location[0] + 2):
                    for j in range(setl_quad.location[1] - 1, setl_quad.location[1] + 2):
                        if not any(s_q.location == (i, j) for s_q in self.selected_settlement.quads) and \
                                0 <= i <= 99 and 0 <= j <= 89:
                            pyxel.rectb((i - map_pos[0]) * 8 + 4, (j - map_pos[1]) * 8 + 4, 8, 8, pyxel.COLOR_WHITE)
        if self.deploying_army_from_unit:
            for i in range(self.selected_unit.location[0] - 1, self.selected_unit.location[0] + 2):
                for j in range(self.selected_unit.location[1] - 1, self.selected_unit.location[1] + 2):
                    if self.selected_unit.location != (i, j) and 0 <= i <= 99 and 0 <= j <= 89:
                        pyxel.rectb((i - map_pos[0]) * 8 + 4, (j - map_pos[1]) * 8 + 4, 8, 8, pyxel.COLOR_WHITE)

        # Also display the number of units the player can move at the bottom-right of the screen.
        movable_units = [unit for unit in players[self.player_idx].units
                         if unit.remaining_stamina > 0 and not unit.besieging]
        if len(movable_units) > 0:
            pluralisation = "s" if len(movable_units) > 1 else ""
            pyxel.rectb(150, 147, 40, 20, pyxel.COLOR_WHITE)
            pyxel.rect(151, 148, 38, 18, pyxel.COLOR_BLACK)
            pyxel.text(168, 150, str(len(movable_units)), pyxel.COLOR_WHITE)
            pyxel.text(156, 155, "movable", pyxel.COLOR_WHITE)
            pyxel.text(161, 160, f"unit{pluralisation}", pyxel.COLOR_WHITE)

        pyxel.rect(0, 184, 200, 16, pyxel.COLOR_BLACK)
        # There are a few situations in which we override the default help text:
        # - If the current game has multiplayer enabled, and the player is waiting for other players to finish their
        #   turn.
        # - If the current game has multiplayer enabled, and the player's local game state is being validated to ensure
        #   that it is in sync with the game server.
        # - If a unit is selected that can settle, alerting the player as to the settle button.
        # - If a unit is selected that can heal other units, alerting the player as to how to heal other units.
        if self.game_config.multiplayer and self.waiting_for_other_players:
            pyxel.text(2, 189, "Waiting for other players...", pyxel.COLOR_WHITE)
        elif self.game_config.multiplayer and self.checking_game_sync:
            pyxel.text(2, 189, "Checking game sync, please wait...", pyxel.COLOR_WHITE)
        elif self.selected_unit is not None and self.selected_unit.plan.can_settle:
            pyxel.text(2, 189, "S: Found new settlement", pyxel.COLOR_WHITE)
        elif self.selected_unit is not None and self.selected_unit.plan.heals and not self.selected_unit.has_acted:
            pyxel.text(2, 189, "L CLICK: Heal adjacent unit", pyxel.COLOR_WHITE)
        else:
            pyxel.text(2, 189, self.current_help.value, pyxel.COLOR_WHITE)

        exclamation_offset: int = 0
        if self.game_config.climatic_effects:
            exclamation_offset += 12
            if players[self.player_idx].faction == Faction.NOCTURNE:
                exclamation_offset += 17
                pyxel.text(135, 190, f"({turns_until_change})", pyxel.COLOR_WHITE)
            if is_night:
                pyxel.blt(153, 188, 0, 8, 84, 8, 8)
            else:
                pyxel.blt(153, 188, 0, 0, 84, 8, 8)
        # If the player isn't undergoing a blessing, or has one or more settlements without a construction, display
        # exclamation marks in the status bar.
        if any(setl.current_work is None for setl in players[self.player_idx].settlements):
            pyxel.blt(154 - exclamation_offset, 188, 0, 8, 124, 8, 8)
            exclamation_offset += 8
        if players[self.player_idx].ongoing_blessing is None:
            pyxel.blt(154 - exclamation_offset, 188, 0, 0, 124, 8, 8)

        pyxel.text(165, 189, f"Turn {turn}", pyxel.COLOR_WHITE)

        # Also display the overlay.
        display_overlay(self.overlay, is_night)

    def update(self, elapsed_time: float):
        """
        Update the time banks with the supplied elapsed time since the last update.
        :param elapsed_time: The time in seconds since the last update call.
        """
        self.help_time_bank += elapsed_time
        # Each help text is displayed for three seconds before changing.
        if self.help_time_bank > 3:
            match self.current_help:
                case HelpOption.SETTLEMENT:
                    self.current_help = HelpOption.UNIT
                case HelpOption.UNIT:
                    self.current_help = HelpOption.OVERLAY
                case HelpOption.OVERLAY:
                    self.current_help = HelpOption.PAUSE
                case HelpOption.PAUSE:
                    self.current_help = HelpOption.END_TURN
                case HelpOption.END_TURN:
                    self.current_help = HelpOption.SETTLEMENT
            self.help_time_bank = 0
        # If an attack has occurred, it is similarly displayed for three seconds before disappearing.
        if self.overlay.is_attack() or self.overlay.is_setl_attack():
            self.attack_time_bank += elapsed_time
            if self.attack_time_bank > 3:
                if self.overlay.is_attack():
                    self.overlay.toggle_attack(None)
                else:
                    self.overlay.toggle_setl_attack(None)
                self.attack_time_bank = 0
        # In the same way, if one of the player's settlements is under siege, display this for three seconds.
        if self.overlay.is_siege_notif():
            self.siege_time_bank += elapsed_time
            if self.siege_time_bank > 3:
                self.overlay.toggle_siege_notif(None, None)
                self.siege_time_bank = 0
        # If the player has selected a settlement with no active construction, rotate between the two prompts every
        # three seconds.
        if self.overlay.is_setl() and self.selected_settlement.current_work is None:
            self.construction_prompt_time_bank += elapsed_time
            if self.construction_prompt_time_bank > 3:
                self.overlay.show_auto_construction_prompt = not self.overlay.show_auto_construction_prompt
                self.construction_prompt_time_bank = 0
        # If the player has healed one of their units, display the result for three seconds before disappearing, like an
        # attack alert.
        if self.overlay.is_heal():
            self.heal_time_bank += elapsed_time
            if self.heal_time_bank > 3:
                self.overlay.toggle_heal(None)
                self.heal_time_bank = 0
        # If a player has left or joined the current multiplayer game, display who left/joined for three seconds before
        # disappearing, like the above alerts.
        if self.overlay.is_player_change():
            self.player_change_time_bank += elapsed_time
            if self.player_change_time_bank > 3:
                self.overlay.toggle_player_change(None, None)
                self.player_change_time_bank = 0

    def generate_quads(self, biome_clustering: bool, climatic_effects: bool):
        """
        Generate the quads to be used for this game.
        :param biome_clustering: Whether biome clustering is enabled or not.
        :param climatic_effects: Whether climatic effects are enabled or not.
        """
        for i in range(90):
            for j in range(100):
                if biome_clustering:
                    # The below block of code gets all directly adjacent quads to the one being currently generated.
                    surrounding_biomes = []
                    if i > 0:
                        if j > 0:
                            surrounding_biomes.append(self.quads[i - 1][j - 1].biome)
                        surrounding_biomes.append(self.quads[i - 1][j].biome)
                        if j < 99:
                            surrounding_biomes.append(self.quads[i - 1][j + 1].biome)
                    if j > 0:
                        surrounding_biomes.append(self.quads[i][j - 1].biome)
                    if len(surrounding_biomes) > 0:
                        # Work out which biome nearby is most prevalent, and 40% of the time, choose that biome. This
                        # 40% rate is adjustable. Note that 100% would result in the entire board having the same biome
                        # and 0% would result in random picks.
                        biome_ctr = Counter(surrounding_biomes)
                        max_rate: Biome = max(biome_ctr, key=biome_ctr.get)
                        biome: Biome
                        rand = random.random()
                        if rand < 0.4:
                            biome = max_rate
                        else:
                            biome = random.choice(list(Biome))
                    else:
                        biome = random.choice(list(Biome))
                else:
                    # If we're not using biome clustering, just randomly choose one.
                    biome = random.choice(list(Biome))
                quad_yield: typing.Tuple[int, int, int, int] = calculate_yield_for_quad(biome)

                resource: typing.Optional[ResourceCollection] = None
                # Each quad has a 1 in 20 chance of having a core resource, and a 1 in 100 chance of having a rare
                # resource. We combine these by saying that each quad has a 6% chance of having any resource at all.
                resource_chance = random.randint(0, 100)
                if resource_chance < 6:
                    if resource_chance < 1:
                        random_chance = random.randint(0, 100)
                        # If climatic effects are disabled, then sunstone would have no effect. As such, sunstone is not
                        # included in games with disabled climatic effects.
                        if climatic_effects:
                            if random_chance < 20:
                                resource = ResourceCollection(aurora=1)
                            elif random_chance < 40:
                                resource = ResourceCollection(bloodstone=1)
                            elif random_chance < 60:
                                resource = ResourceCollection(obsidian=1)
                            elif random_chance < 80:
                                resource = ResourceCollection(sunstone=1)
                            else:
                                resource = ResourceCollection(aquamarine=1)
                        else:
                            if random_chance < 25:
                                resource = ResourceCollection(aurora=1)
                            elif random_chance < 50:
                                resource = ResourceCollection(bloodstone=1)
                            elif random_chance < 75:
                                resource = ResourceCollection(obsidian=1)
                            else:
                                resource = ResourceCollection(aquamarine=1)
                    else:
                        random_chance = random.randint(0, 99)
                        if random_chance < 33:
                            resource = ResourceCollection(ore=1)
                        elif random_chance < 66:
                            resource = ResourceCollection(timber=1)
                        else:
                            resource = ResourceCollection(magma=1)

                is_relic = False
                relic_chance = random.randint(0, 100)
                if relic_chance < 1:
                    is_relic = True

                self.quads[i][j] = Quad(biome, *quad_yield, location=(j, i), is_relic=is_relic, resource=resource)

    def process_right_click(self, mouse_x: int, mouse_y: int, map_pos: (int, int)):
        """
        Process a right click by the player at given coordinates with the current map position.
        :param mouse_x: The X coordinate of the mouse click.
        :param mouse_y: The Y coordinate of the mouse click.
        :param map_pos: The current map position.
        """
        # Ensure that we only process right clicks in situations where it makes sense for the player to be able to click
        # the map. For example, if the player is choosing a construction for a settlement, they should not be able to
        # click around on the map.
        obscured_by_overlay = self.overlay.is_standard() or self.overlay.is_constructing() or \
            self.overlay.is_blessing() or self.overlay.is_deployment() or self.overlay.is_warning() or \
            self.overlay.is_bless_notif() or self.overlay.is_constr_notif() or self.overlay.is_lvl_notif() or \
            self.overlay.is_setl_click() or self.overlay.is_pause() or self.overlay.is_controls() or \
            self.overlay.is_victory() or self.overlay.is_elimination() or self.overlay.is_close_to_vic() or \
            self.overlay.is_investigation() or self.overlay.is_ach_notif()
        if not obscured_by_overlay and 4 <= mouse_x <= 196 and 4 <= mouse_y <= 180:
            # Work out which quad they've clicked, and select it.
            adj_x = int((mouse_x - 4) / 8) + map_pos[0]
            adj_y = int((mouse_y - 4) / 8) + map_pos[1]
            if self.quads[adj_y][adj_x].selected:
                self.quads[adj_y][adj_x].selected = False
                self.quad_selected = None
            else:
                self.quads[adj_y][adj_x].selected = True
                if self.quad_selected is not None:
                    self.quad_selected.selected = False
                self.quad_selected = self.quads[adj_y][adj_x]

    def process_left_click(self, mouse_x: int, mouse_y: int, settled: bool,
                           player: Player, map_pos: (int, int), heathens: typing.List[Heathen],
                           all_units: typing.List[Unit], all_players: typing.List[Player],
                           other_setls: typing.List[Settlement]):
        """
        Process a left click by the player at given coordinates.
        :param mouse_x: The X coordinate of the mouse click.
        :param mouse_y: The Y coordinate of the mouse click.
        :param settled: Whether the player has founded a settlement yet.
        :param player: The player making the click.
        :param map_pos: The current map position.
        :param heathens: The list of Heathens.
        :param all_units: The list of all Units in the game.
        :param all_players: The list of all Players in the game, AI or not.
        :param other_setls: The list of all AI Settlements.
        """
        # Ensure that we only process left clicks in situations where it makes sense for the player to be able to click
        # the map. For example, if the player is choosing a construction for a settlement, they should not be able to
        # click around on the map.
        obscured_by_overlay = self.overlay.is_standard() or self.overlay.is_constructing() or \
            self.overlay.is_blessing() or self.overlay.is_warning() or self.overlay.is_bless_notif() or \
            self.overlay.is_constr_notif() or self.overlay.is_lvl_notif() or self.overlay.is_setl_click() or \
            self.overlay.is_pause() or self.overlay.is_controls() or self.overlay.is_victory() or \
            self.overlay.is_elimination() or self.overlay.is_close_to_vic() or self.overlay.is_investigation() or \
            self.overlay.is_ach_notif()
        # Firstly, deselect the selected quad if there is one.
        if not obscured_by_overlay and self.quad_selected is not None:
            self.quad_selected.selected = False
            self.quad_selected = None
        if not obscured_by_overlay and 4 <= mouse_x <= 196 and 4 <= mouse_y <= 180:
            # Again, determine the quad.
            adj_x = int((mouse_x - 4) / 8) + map_pos[0]
            adj_y = int((mouse_y - 4) / 8) + map_pos[1]
            if 0 <= adj_x <= 99 and 0 <= adj_y <= 89:
                if not settled:
                    # If the player has not founded a settlement yet, then this first click denotes where their first
                    # settlement will be.
                    quad_biome = self.quads[adj_y][adj_x].biome
                    setl_name = self.namer.get_settlement_name(quad_biome)
                    setl_resources = get_resources_for_settlement([(adj_x, adj_y)], self.quads)
                    new_settl = Settlement(setl_name, (adj_x, adj_y), [], [self.quads[adj_y][adj_x]], setl_resources,
                                           [get_default_unit((adj_x, adj_y))])
                    match player.faction:
                        case Faction.CONCENTRATED:
                            new_settl.strength *= 2
                            new_settl.max_strength *= 2
                        case Faction.FRONTIERSMEN:
                            new_settl.satisfaction = 75.0
                        case Faction.IMPERIALS:
                            new_settl.strength /= 2
                            new_settl.max_strength /= 2
                    if new_settl.resources.obsidian:
                        new_settl.strength *= (1 + 0.5 * new_settl.resources.obsidian)
                        new_settl.max_strength *= (1 + 0.5 * new_settl.resources.obsidian)
                    player.settlements.append(new_settl)
                    # Automatically add 5 quads in either direction to the player's seen.
                    update_player_quads_seen_around_point(player, (adj_x, adj_y))
                    self.overlay.toggle_tutorial()
                    # Select the new settlement.
                    self.selected_settlement = new_settl
                    self.overlay.toggle_settlement(new_settl, player)
                    # If we're in a multiplayer game, alert the server, which will alert other players.
                    if self.game_config.multiplayer:
                        fs_evt: FoundSettlementEvent = FoundSettlementEvent(EventType.UPDATE, get_identifier(),
                                                                            UpdateAction.FOUND_SETTLEMENT,
                                                                            self.game_name, player.faction, new_settl,
                                                                            from_settler=False)
                        dispatch_event(fs_evt)
                else:
                    # If the player has selected a settlement, but has now clicked elsewhere, deselect the settlement.
                    if not self.deploying_army and \
                            self.selected_settlement is not None and \
                            all(quad.location != (adj_x, adj_y) for quad in self.selected_settlement.quads):
                        self.selected_settlement = None
                        self.overlay.toggle_settlement(None, player)
                    # If the player has selected neither unit nor settlement, and they have clicked on one of their
                    # settlements, select it.
                    elif self.selected_unit is None and self.selected_settlement is None and \
                            any((to_select := setl) and any(setl_quad.location == (adj_x, adj_y)
                                                            for setl_quad in setl.quads)
                                for setl in player.settlements):
                        self.selected_settlement = to_select
                        self.overlay.toggle_settlement(to_select, player)
                    # If the player has selected a unit, and they have clicked on one of their settlements, garrison the
                    # selected unit in the settlement, ensuring it is within range.
                    elif not self.deploying_army_from_unit and self.selected_unit is not None and \
                            self.selected_unit in player.units and self.selected_settlement is None and \
                            any((to_select := setl) and any(setl_quad.location == (adj_x, adj_y)
                                                            for setl_quad in setl.quads)
                                for setl in player.settlements) and \
                            self.selected_unit.location[0] - self.selected_unit.remaining_stamina <= adj_x <= \
                            self.selected_unit.location[0] + self.selected_unit.remaining_stamina and \
                            self.selected_unit.location[1] - self.selected_unit.remaining_stamina <= adj_y <= \
                            self.selected_unit.location[1] + self.selected_unit.remaining_stamina:
                        initial = self.selected_unit.location
                        distance_travelled = max(abs(initial[0] - adj_x), abs(initial[1] - adj_y))
                        self.selected_unit.remaining_stamina -= distance_travelled
                        self.selected_unit.garrisoned = True
                        to_select.garrison.append(self.selected_unit)
                        player.units.remove(self.selected_unit)
                        # If we're in a multiplayer game, alert the server, which will alert other players.
                        if self.game_config.multiplayer:
                            gu_evt: GarrisonUnitEvent = GarrisonUnitEvent(EventType.UPDATE, get_identifier(),
                                                                          UpdateAction.GARRISON_UNIT, self.game_name,
                                                                          player.faction, initial,
                                                                          self.selected_unit.remaining_stamina,
                                                                          to_select.name)
                            dispatch_event(gu_evt)
                        # Deselect the unit now.
                        self.selected_unit = None
                        self.overlay.toggle_unit(None)
                    # If the player has selected a unit, and they have clicked on one of their deployer units, add the
                    # selected unit as a passenger to the deployer unit, ensuring it is within range. Also make sure
                    # that the selected unit is not a deployer unit, and that the deployer unit clicked on has room for
                    # a new passenger.
                    elif not self.deploying_army_from_unit and self.selected_unit is not None and \
                            self.selected_unit in player.units and self.selected_settlement is None and \
                            any((to_select := unit).location == (adj_x, adj_y) and isinstance(unit, DeployerUnit)
                                for unit in player.units) and \
                            not isinstance(self.selected_unit, DeployerUnit) and \
                            len(to_select.passengers) < to_select.plan.max_capacity and \
                            self.selected_unit.location[0] - self.selected_unit.remaining_stamina <= adj_x <= \
                            self.selected_unit.location[0] + self.selected_unit.remaining_stamina and \
                            self.selected_unit.location[1] - self.selected_unit.remaining_stamina <= adj_y <= \
                            self.selected_unit.location[1] + self.selected_unit.remaining_stamina:
                        initial = self.selected_unit.location
                        distance_travelled = max(abs(initial[0] - adj_x), abs(initial[1] - adj_y))
                        self.selected_unit.remaining_stamina -= distance_travelled
                        to_select.passengers.append(self.selected_unit)
                        player.units.remove(self.selected_unit)
                        # If we're in a multiplayer game, alert the server, which will alert other players.
                        if self.game_config.multiplayer:
                            bd_evt: BoardDeployerEvent = BoardDeployerEvent(EventType.UPDATE, get_identifier(),
                                                                            UpdateAction.BOARD_DEPLOYER, self.game_name,
                                                                            player.faction, initial, to_select.location,
                                                                            self.selected_unit.remaining_stamina)
                            dispatch_event(bd_evt)
                        # Deselect the unit now.
                        self.selected_unit = None
                        self.overlay.toggle_unit(None)
                    # If the player is deploying a unit and they've clicked within one quad of the settlement the unit
                    # is being deployed from, place the unit there.
                    elif self.deploying_army and \
                            any(setl_quad.location[0] - 1 <= adj_x <= setl_quad.location[0] + 1 and
                                setl_quad.location[1] - 1 <= adj_y <= setl_quad.location[1] + 1
                                for setl_quad in self.selected_settlement.quads) and \
                            not any(s_q.location == (adj_x, adj_y) for s_q in self.selected_settlement.quads) and \
                            not any(heathen.location == (adj_x, adj_y) for heathen in heathens) and \
                            not any(unit.location == (adj_x, adj_y) for unit in all_units) and \
                            not any(any(setl_quad.location == (adj_x, adj_y) for setl_quad in setl.quads)
                                    for setl in other_setls):
                        deployed = self.selected_settlement.garrison.pop()
                        deployed.garrisoned = False
                        deployed.location = adj_x, adj_y
                        player.units.append(deployed)
                        # Add the surrounding quads to the player's seen.
                        update_player_quads_seen_around_point(player, (adj_x, adj_y))
                        # If we're in a multiplayer game, alert the server, which will alert other players.
                        if self.game_config.multiplayer:
                            du_evt: DeployUnitEvent = DeployUnitEvent(EventType.UPDATE, get_identifier(),
                                                                      UpdateAction.DEPLOY_UNIT, self.game_name,
                                                                      player.faction, self.selected_settlement.name,
                                                                      deployed.location)
                            dispatch_event(du_evt)
                        self.deploying_army = False
                        # Select the unit and deselect the settlement.
                        self.selected_unit = deployed
                        self.overlay.toggle_deployment()
                        self.selected_settlement = None
                        self.overlay.toggle_settlement(None, player)
                        self.overlay.toggle_unit(deployed)
                    # If the player is deploying a unit from a deployer unit, and they've clicked within one quad of the
                    # deployer unit being deployed from, place the unit there.
                    elif self.deploying_army_from_unit and \
                            self.selected_unit.location[0] - 1 <= adj_x <= self.selected_unit.location[0] + 1 and \
                            self.selected_unit.location[1] - 1 <= adj_y <= self.selected_unit.location[1] + 1 and \
                            not self.selected_unit.location == (adj_x, adj_y) and \
                            not any(heathen.location == (adj_x, adj_y) for heathen in heathens) and \
                            not any(unit.location == (adj_x, adj_y) for unit in all_units) and \
                            not any(any(setl_quad.location == (adj_x, adj_y) for setl_quad in setl.quads)
                                    for setl in other_setls):
                        unit_idx = self.overlay.unit_passengers_idx
                        deployed = self.selected_unit.passengers[unit_idx]
                        deployed.location = adj_x, adj_y
                        self.selected_unit.passengers[unit_idx:unit_idx + 1] = []
                        player.units.append(deployed)
                        # Add the surrounding quads to the player's seen.
                        update_player_quads_seen_around_point(player, (adj_x, adj_y))
                        # If we're in a multiplayer game, alert the server, which will alert other players.
                        if self.game_config.multiplayer:
                            dd_evt: DeployerDeployEvent = DeployerDeployEvent(EventType.UPDATE, get_identifier(),
                                                                              UpdateAction.DEPLOYER_DEPLOY,
                                                                              self.game_name, player.faction,
                                                                              self.selected_unit.location, unit_idx,
                                                                              deployed.location)
                            dispatch_event(dd_evt)
                        # Reset the relevant deployer unit state.
                        self.deploying_army_from_unit = False
                        self.overlay.unit_passengers_idx = 0
                        self.overlay.show_unit_passengers = False
                        # Select the unit as well.
                        self.selected_unit = deployed
                        self.overlay.toggle_deployment()
                        self.overlay.update_unit(deployed)
                    # If the player has not selected a unit and they've clicked on a visible heathen, select it.
                    elif self.selected_unit is None and \
                            ((adj_x, adj_y) in player.quads_seen or not self.game_config.fog_of_war) and \
                            any((to_select := heathen).location == (adj_x, adj_y) for heathen in heathens):
                        self.selected_unit = to_select
                        self.overlay.toggle_unit(to_select)
                    # If the player has selected one of their units and it hasn't attacked, and they've clicked on
                    # either an enemy unit or a heathen within range, attack it.
                    elif not self.deploying_army_from_unit and self.selected_unit is not None and \
                            not isinstance(self.selected_unit, Heathen) and \
                            self.selected_unit in player.units and not self.selected_unit.has_acted and \
                            (any((other_unit := heathen).location == (adj_x, adj_y) for heathen in heathens) or
                             any((other_unit := unit).location == (adj_x, adj_y) for unit in all_units)):
                        if self.selected_unit is not other_unit and other_unit not in player.units and \
                                abs(self.selected_unit.location[0] - other_unit.location[0]) <= 1 and \
                                abs(self.selected_unit.location[1] - other_unit.location[1]) <= 1:
                            data = attack(self.selected_unit, other_unit, ai=False)
                            # If we're in a multiplayer game, alert the server, which will alert other players.
                            if self.game_config.multiplayer:
                                au_evt: AttackUnitEvent = AttackUnitEvent(EventType.UPDATE, get_identifier(),
                                                                          UpdateAction.ATTACK_UNIT,
                                                                          self.game_name, player.faction,
                                                                          self.selected_unit.location,
                                                                          other_unit.location)
                                dispatch_event(au_evt)
                            # Destroy the player's unit if it died.
                            if self.selected_unit.health <= 0:
                                player.units.remove(self.selected_unit)
                                self.selected_unit = None
                                self.overlay.toggle_unit(None)
                            # Destroy the heathen/enemy unit if it died.
                            if other_unit.health <= 0:
                                if other_unit in heathens:
                                    heathens.remove(other_unit)
                                else:
                                    for p in all_players:
                                        if other_unit in p.units:
                                            p.units.remove(other_unit)
                                            break
                            # Show the attack results.
                            self.overlay.toggle_attack(data)
                            self.attack_time_bank = 0
                        # However, if the player clicked on another of their units, either heal or select it rather than
                        # attacking, depending on whether the currently-selected unit can heal others or not. Note that
                        # healer units cannot heal deployer units, since this would create weird behaviour where
                        # left-clicking on a friendly deployer unit is ambiguous in its purpose - healing or boarding.
                        elif other_unit in player.units:
                            if self.selected_unit is not other_unit and self.selected_unit.plan.heals and \
                                    not isinstance(other_unit, DeployerUnit) and \
                                    abs(self.selected_unit.location[0] - other_unit.location[0]) <= 1 and \
                                    abs(self.selected_unit.location[1] - other_unit.location[1]) <= 1:
                                data = heal(self.selected_unit, other_unit, ai=False)
                                # If we're in a multiplayer game, alert the server, which will alert other players.
                                if self.game_config.multiplayer:
                                    hu_evt: HealUnitEvent = HealUnitEvent(EventType.UPDATE, get_identifier(),
                                                                          UpdateAction.HEAL_UNIT, self.game_name,
                                                                          player.faction, self.selected_unit.location,
                                                                          other_unit.location)
                                    dispatch_event(hu_evt)
                                self.overlay.toggle_heal(data)
                                self.heal_time_bank = 0
                            else:
                                self.selected_unit = other_unit
                                self.overlay.update_unit(other_unit)
                    # If the player has selected one of their units and it hasn't attacked, and the player clicks on an
                    # enemy settlement within range, bring up the overlay to prompt the player on their action.
                    elif not self.deploying_army_from_unit and self.selected_unit is not None and \
                            not isinstance(self.selected_unit, Heathen) and \
                            self.selected_unit in player.units and not self.selected_unit.has_acted and \
                            any((to_attack := setl) and any((quad_to_attack := setl_quad).location == (adj_x, adj_y)
                                                            for setl_quad in setl.quads) for setl in other_setls):
                        if abs(self.selected_unit.location[0] - quad_to_attack.location[0]) <= 1 and \
                                abs(self.selected_unit.location[1] - quad_to_attack.location[1]) <= 1:
                            for p in all_players:
                                if to_attack in p.settlements:
                                    self.overlay.toggle_setl_click(to_attack, p)
                    # If the player has not selected a unit and they click on a visible one, select it.
                    elif self.selected_unit is None and \
                            ((adj_x, adj_y) in player.quads_seen or not self.game_config.fog_of_war) and \
                            any((to_select := unit).location == (adj_x, adj_y) for unit in all_units):
                        self.selected_unit = to_select
                        self.overlay.toggle_unit(to_select)
                    # If the player has selected one of their units and they've clicked an empty quad within range, move
                    # the unit there.
                    elif not self.deploying_army_from_unit and self.selected_unit is not None and \
                            not isinstance(self.selected_unit, Heathen) and \
                            not any(heathen.location == (adj_x, adj_y) for heathen in heathens) and \
                            self.selected_unit in player.units and \
                            not any(unit.location == (adj_x, adj_y) for unit in all_units) and \
                            not any(any(setl_quad.location == (adj_x, adj_y) for setl_quad in setl.quads)
                                    for setl in other_setls) and \
                            not self.quads[adj_y][adj_x].is_relic and \
                            self.selected_unit.location[0] - self.selected_unit.remaining_stamina <= adj_x <= \
                            self.selected_unit.location[0] + self.selected_unit.remaining_stamina and \
                            self.selected_unit.location[1] - self.selected_unit.remaining_stamina <= adj_y <= \
                            self.selected_unit.location[1] + self.selected_unit.remaining_stamina:
                        initial = self.selected_unit.location
                        distance_travelled = max(abs(initial[0] - adj_x), abs(initial[1] - adj_y))
                        self.selected_unit.remaining_stamina -= distance_travelled
                        self.selected_unit.location = adj_x, adj_y
                        # Any unit that moves more than 1 quad away while besieging ends their siege on the settlement.
                        found_besieged_setl = False
                        for setl in other_setls:
                            if setl.besieged and abs(self.selected_unit.location[0] - setl.location[0]) <= 1 and \
                                    abs(self.selected_unit.location[1] - setl.location[1]) <= 1:
                                found_besieged_setl = True
                        self.selected_unit.besieging = found_besieged_setl
                        # Update the player's seen quads.
                        update_player_quads_seen_around_point(player, (adj_x, adj_y))
                        # If we're in a multiplayer game, alert the server, which will alert other players.
                        if self.game_config.multiplayer:
                            mu_evt: MoveUnitEvent = MoveUnitEvent(EventType.UPDATE, get_identifier(),
                                                                  UpdateAction.MOVE_UNIT, self.game_name,
                                                                  player.faction, initial, self.selected_unit.location,
                                                                  self.selected_unit.remaining_stamina,
                                                                  self.selected_unit.besieging)
                            dispatch_event(mu_evt)
                    # If the player has selected one of their units and clicked on a relic, investigate it, providing
                    # that their unit is close enough.
                    elif not self.deploying_army_from_unit and self.selected_unit is not None and \
                            self.selected_unit in player.units and self.quads[adj_y][adj_x].is_relic:
                        if abs(self.selected_unit.location[0] - adj_x) <= 1 and \
                                abs(self.selected_unit.location[1] - adj_y) <= 1:
                            result: InvestigationResult = investigate_relic(player,
                                                                            self.selected_unit,
                                                                            (adj_x, adj_y),
                                                                            self.game_config)
                            # Relics cease to exist once investigated.
                            self.quads[adj_y][adj_x].is_relic = False
                            # If we're in a multiplayer game, alert the server, which will alert other players.
                            if self.game_config.multiplayer:
                                i_evt: InvestigateEvent = InvestigateEvent(EventType.UPDATE, get_identifier(),
                                                                           UpdateAction.INVESTIGATE, self.game_name,
                                                                           player.faction, self.selected_unit.location,
                                                                           (adj_x, adj_y), result)
                                dispatch_event(i_evt)
                            self.overlay.toggle_investigation(result)
                    # Lastly, if the player has selected a unit and they click elsewhere, deselect the unit.
                    elif not self.deploying_army_from_unit and self.selected_unit is not None and \
                            self.selected_unit.location != (adj_x, adj_y):
                        self.selected_unit = None
                        self.overlay.toggle_unit(None)

    def handle_new_settlement(self, player: Player):
        """
        Found a new settlement for the given player if permitted.
        :param player: The player founding the settlement.
        """
        can_settle = True
        for setl in player.settlements:
            # Of course, players cannot found settlements where they already have one. We also don't need to check every
            # single quad that the settlement has, because the only settlements that can have more than one quad are of
            # the very same faction that cannot recruit settlers.
            if setl.location == self.selected_unit.location:
                can_settle = False
                break
        if can_settle:
            quad_biome = self.quads[self.selected_unit.location[1]][self.selected_unit.location[0]].biome
            setl_name = self.namer.get_settlement_name(quad_biome)
            setl_resources = get_resources_for_settlement([self.selected_unit.location], self.quads)
            new_settl = Settlement(setl_name, self.selected_unit.location, [],
                                   [self.quads[self.selected_unit.location[1]][self.selected_unit.location[0]]],
                                   setl_resources, [])
            if player.faction == Faction.FRONTIERSMEN:
                new_settl.satisfaction = 75.0
            elif player.faction == Faction.IMPERIALS:
                new_settl.strength /= 2
                new_settl.max_strength /= 2
            if new_settl.resources.obsidian:
                new_settl.strength *= (1 + 0.5 * new_settl.resources.obsidian)
                new_settl.max_strength *= (1 + 0.5 * new_settl.resources.obsidian)
            player.settlements.append(new_settl)
            update_player_quads_seen_around_point(player, new_settl.location)
            # Destroy the settler unit and select the new settlement.
            player.units.remove(self.selected_unit)
            # If we're in a multiplayer game, alert the server, which will alert other players.
            if self.game_config.multiplayer:
                fs_evt: FoundSettlementEvent = FoundSettlementEvent(EventType.UPDATE, get_identifier(),
                                                                    UpdateAction.FOUND_SETTLEMENT,
                                                                    self.game_name, player.faction, new_settl)
                dispatch_event(fs_evt)
            self.selected_unit = None
            self.overlay.toggle_unit(None)
            self.selected_settlement = new_settl
            self.overlay.toggle_settlement(new_settl, player)
