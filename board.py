import random
import typing
from collections import Counter
from enum import Enum

import pyxel

from calculator import calculate_yield_for_quad, attack, investigate_relic
from catalogue import get_default_unit, Namer
from models import Player, Quad, Biome, Settlement, Unit, Heathen, GameConfig, InvestigationResult, Faction
from overlay import Overlay
from overlay_display import display_overlay


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

    def __init__(self, cfg: GameConfig, namer: Namer, quads: typing.List[typing.List[Quad]] = None):
        """
        Initialises the board with the given config and quads, if supplied.
        :param cfg: The game config.
        :param namer: The Namer instance to use for settlement names.
        :param quads: The quads loaded in, if we are loading a game.
        """
        self.current_help = HelpOption.SETTLEMENT
        self.help_time_bank = 0
        self.attack_time_bank = 0
        self.siege_time_bank = 0

        self.game_config: GameConfig = cfg
        self.namer: Namer = namer

        # We allow quads to be supplied here in load game cases.
        if quads is not None:
            self.quads = quads
        else:
            self.quads: typing.List[typing.List[typing.Optional[Quad]]] = [[None] * 100 for _ in range(90)]
            random.seed()
            self.generate_quads(cfg.biome_clustering)

        self.quad_selected: typing.Optional[Quad] = None

        self.overlay = Overlay()
        self.selected_settlement: typing.Optional[Settlement] = None
        self.deploying_army = False
        self.selected_unit: typing.Optional[Unit | Heathen] = None

    def draw(self, players: typing.List[Player], map_pos: (int, int), turn: int, heathens: typing.List[Heathen],
             is_night: bool, turns_until_change: int):
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
        # Nocturne faction have no vision impacts at nighttime.
        if is_night and players[0].faction is not Faction.NOCTURNE:
            for setl in players[0].settlements:
                for i in range(setl.location[0] - 3, setl.location[0] + 4):
                    for j in range(setl.location[1] - 3, setl.location[1] + 4):
                        quads_to_show.add((i, j))
            for unit in players[0].units:
                for i in range(unit.location[0] - 3, unit.location[0] + 4):
                    for j in range(unit.location[1] - 3, unit.location[1] + 4):
                        quads_to_show.add((i, j))
            # Players of the Infidels faction share vision with Heathen units.
            if players[0].faction is Faction.INFIDELS:
                for heathen in heathens:
                    for i in range(heathen.location[0] - 5, heathen.location[0] + 6):
                        for j in range(heathen.location[1] - 5, heathen.location[1] + 6):
                            quads_to_show.add((i, j))
        else:
            quads_to_show = players[0].quads_seen
        fog_of_war_impacts: bool = self.game_config.fog_of_war or \
            (is_night and players[0].faction is not Faction.NOCTURNE)
        # Draw the quads.
        for i in range(map_pos[0], map_pos[0] + 24):
            for j in range(map_pos[1], map_pos[1] + 22):
                if 0 <= i <= 99 and 0 <= j <= 89:
                    # Draw the quad if fog of war is off, or if the player has seen the quad, or we're in the tutorial.
                    # This same logic applies to all subsequent draws.
                    if (i, j) in quads_to_show or len(players[0].settlements) == 0 or not fog_of_war_impacts:
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
                        quad_y = 20 if quad.is_relic else 4
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
                if self.selected_unit is not None and self.selected_unit is not heathen and \
                        not self.selected_unit.has_attacked and \
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
                    if self.selected_unit is unit and unit in players[0].units:
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
                    quad: Quad = self.quads[settlement.location[1]][settlement.location[0]]
                    match quad.biome:
                        case Biome.DESERT:
                            setl_x = 0
                        case Biome.FOREST:
                            setl_x = 8
                        case Biome.SEA:
                            setl_x = 16
                        case _:
                            setl_x = 24
                    if is_night and settlement.under_siege_by is None:
                        setl_x += 32
                    pyxel.blt((settlement.location[0] - map_pos[0]) * 8 + 4,
                              (settlement.location[1] - map_pos[1]) * 8 + 4, 0, setl_x,
                              68 if settlement.under_siege_by is not None else 4, 8, 8)

        for player in players:
            for settlement in player.settlements:
                if settlement.location in quads_to_show or not fog_of_war_impacts:
                    # Draw name tags for non-selected settlements.
                    if self.selected_settlement is not settlement:
                        name_len = len(settlement.name)
                        x_offset = 11 - name_len
                        base_x_pos = (settlement.location[0] - map_pos[0]) * 8
                        base_y_pos = (settlement.location[1] - map_pos[1]) * 8
                        # Sieged settlements are displayed with a black background.
                        if settlement.under_siege_by is not None:
                            pyxel.rect(base_x_pos - 17, base_y_pos - 8, 52, 10,
                                       pyxel.COLOR_WHITE if is_night else pyxel.COLOR_BLACK)
                            pyxel.text(base_x_pos - 10 + x_offset, base_y_pos - 6, settlement.name, player.colour)
                        else:
                            pyxel.rectb(base_x_pos - 17, base_y_pos - 8, 52, 10,
                                        pyxel.COLOR_WHITE if is_night else pyxel.COLOR_BLACK)
                            pyxel.rect(base_x_pos - 16, base_y_pos - 7, 50, 8, player.colour)
                            pyxel.text(base_x_pos - 10 + x_offset, base_y_pos - 6, settlement.name, pyxel.COLOR_WHITE)
                    else:
                        pyxel.rectb((settlement.location[0] - map_pos[0]) * 8 + 4,
                                    (settlement.location[1] - map_pos[1]) * 8 + 4, 8, 8, pyxel.COLOR_RED)

        # For the selected quad, display its yield.
        if self.quad_selected is not None and selected_quad_coords is not None and \
                (selected_quad_coords in quads_to_show or len(players[0].settlements) == 0 or
                 not fog_of_war_impacts):
            x_offset = 30 if selected_quad_coords[0] - map_pos[0] <= 8 else 0
            y_offset = -34 if selected_quad_coords[1] - map_pos[1] >= 36 else 0
            base_x_pos = (selected_quad_coords[0] - map_pos[0]) * 8 + x_offset
            base_y_pos = (selected_quad_coords[1] - map_pos[1]) * 8 + y_offset
            pyxel.rectb(base_x_pos - 22, base_y_pos + 8, 30, 12, pyxel.COLOR_WHITE)
            pyxel.rect(base_x_pos - 21, base_y_pos + 9, 28, 10, pyxel.COLOR_BLACK)
            pyxel.text(base_x_pos - 18, base_y_pos + 12, f"{round(self.quad_selected.wealth)}", pyxel.COLOR_YELLOW)
            pyxel.text(base_x_pos - 12, base_y_pos + 12, f"{round(self.quad_selected.harvest)}", pyxel.COLOR_GREEN)
            pyxel.text(base_x_pos - 6, base_y_pos + 12, f"{round(self.quad_selected.zeal)}", pyxel.COLOR_RED)
            pyxel.text(base_x_pos, base_y_pos + 12, f"{round(self.quad_selected.fortune)}", pyxel.COLOR_PURPLE)

        if self.deploying_army:
            pyxel.rectb((self.selected_settlement.location[0] - map_pos[0]) * 8 - 4,
                        (self.selected_settlement.location[1] - map_pos[1]) * 8 - 4, 24, 24, pyxel.COLOR_WHITE)

        # Also display the number of units the player can move at the bottom-right of the screen.
        movable_units = [unit for unit in players[0].units if unit.remaining_stamina > 0 and not unit.sieging]
        if len(movable_units) > 0:
            pluralisation = "s" if len(movable_units) > 1 else ""
            pyxel.rectb(150, 147, 40, 20, pyxel.COLOR_WHITE)
            pyxel.rect(151, 148, 38, 18, pyxel.COLOR_BLACK)
            pyxel.text(168, 150, str(len(movable_units)), pyxel.COLOR_WHITE)
            pyxel.text(156, 155, "movable", pyxel.COLOR_WHITE)
            pyxel.text(161, 160, f"unit{pluralisation}", pyxel.COLOR_WHITE)

        pyxel.rect(0, 184, 200, 16, pyxel.COLOR_BLACK)
        # If a unit is selected that can settle, override all other help text and alert the player as to the settle
        # button.
        if self.selected_unit is not None and self.selected_unit.plan.can_settle:
            pyxel.text(2, 189, "S: Found new settlement", pyxel.COLOR_WHITE)
        else:
            pyxel.text(2, 189, self.current_help.value, pyxel.COLOR_WHITE)
        if self.game_config.climatic_effects:
            if players[0].faction is Faction.NOCTURNE:
                pyxel.text(135, 190, f"({turns_until_change})", pyxel.COLOR_WHITE)
            if is_night:
                pyxel.blt(153, 188, 0, 8, 84, 8, 8)
            else:
                pyxel.blt(153, 188, 0, 0, 84, 8, 8)
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

    def generate_quads(self, biome_clustering: bool):
        """
        Generate the quads to be used for this game.
        :param biome_clustering: Whether biome clustering is enabled or not.
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
                quad_yield: (float, float, float, float) = calculate_yield_for_quad(biome)

                is_relic = False
                relic_chance = random.randint(0, 100)
                if relic_chance < 1:
                    is_relic = True

                self.quads[i][j] = Quad(biome, *quad_yield, is_relic=is_relic)

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
            self.overlay.is_investigation()
        if not obscured_by_overlay and 4 <= mouse_x <= 196 and 4 <= mouse_y <= 180:
            # Work out which quad they've clicked, and select it.
            adj_x = int((mouse_x - 4) / 8) + map_pos[0]
            adj_y = int((mouse_y - 4) / 8) + map_pos[1]
            self.quads[adj_y][adj_x].selected = not self.quads[adj_y][adj_x].selected
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
        :param player: The non-AI player.
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
            self.overlay.is_elimination() or self.overlay.is_close_to_vic() or self.overlay.is_investigation()
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
                    new_settl = Settlement(setl_name, (adj_x, adj_y), [], [self.quads[adj_y][adj_x]],
                                           [get_default_unit((adj_x, adj_y))])
                    match player.faction:
                        case Faction.CONCENTRATED:
                            new_settl.strength *= 2
                        case Faction.FRONTIERSMEN:
                            new_settl.satisfaction = 75
                        case Faction.IMPERIALS:
                            new_settl.strength /= 2
                            new_settl.max_strength /= 2
                    player.settlements.append(new_settl)
                    # Automatically add 5 quads in either direction to the player's seen.
                    for i in range(adj_y - 5, adj_y + 6):
                        for j in range(adj_x - 5, adj_x + 6):
                            player.quads_seen.add((j, i))
                    self.overlay.toggle_tutorial()
                    # Select the new settlement.
                    self.selected_settlement = new_settl
                    self.overlay.toggle_settlement(new_settl, player)
                else:
                    # If the player has selected a settlement, but has now clicked elsewhere, deselect the settlement.
                    if not self.deploying_army and \
                            self.selected_settlement is not None and \
                            self.selected_settlement.location != (adj_x, adj_y):
                        self.selected_settlement = None
                        self.overlay.toggle_settlement(None, player)
                    # If the player has selected neither a unit or settlement, and they have clicked on one of their
                    # settlements, select it.
                    elif self.selected_unit is None and self.selected_settlement is None and \
                            any((to_select := setl).location == (adj_x, adj_y) for setl in player.settlements):
                        self.selected_settlement = to_select
                        self.overlay.toggle_settlement(to_select, player)
                    # If the player has selected a unit, and they have clicked on one of their settlements, garrison the
                    # selected unit in the settlement, ensuring it is within range.
                    elif self.selected_unit is not None and self.selected_unit in player.units and \
                            self.selected_settlement is None and \
                            any((to_select := setl).location == (adj_x, adj_y) for setl in player.settlements) and \
                            self.selected_unit.location[0] - self.selected_unit.remaining_stamina <= adj_x <= \
                            self.selected_unit.location[0] + self.selected_unit.remaining_stamina and \
                            self.selected_unit.location[1] - self.selected_unit.remaining_stamina <= adj_y <= \
                            self.selected_unit.location[1] + self.selected_unit.remaining_stamina:
                        self.selected_unit.garrisoned = True
                        to_select.garrison.append(self.selected_unit)
                        player.units.remove(self.selected_unit)
                        # Deselect the unit now.
                        self.selected_unit = None
                        self.overlay.toggle_unit(None)
                    # If the player is deploying a unit and they've clicked within one quad of the settlement the unit
                    # is being deployed from, place the unit there.
                    elif self.deploying_army and \
                            self.selected_settlement.location[0] - 1 <= adj_x <= \
                            self.selected_settlement.location[0] + 1 and \
                            self.selected_settlement.location[1] - 1 <= adj_y <= \
                            self.selected_settlement.location[1] + 1:
                        deployed = self.selected_settlement.garrison.pop()
                        deployed.garrisoned = False
                        deployed.location = adj_x, adj_y
                        player.units.append(deployed)
                        # Add the surrounding quads to the player's seen.
                        for i in range(adj_y - 5, adj_y + 6):
                            for j in range(adj_x - 5, adj_x + 6):
                                player.quads_seen.add((j, i))
                        self.deploying_army = False
                        # Select the unit and deselect the settlement.
                        self.selected_unit = deployed
                        self.overlay.toggle_deployment()
                        self.selected_settlement = None
                        self.overlay.toggle_settlement(None, player)
                        self.overlay.toggle_unit(deployed)
                    # If the player has not selected a unit and they've clicked on a heathen, select it.
                    elif self.selected_unit is None and \
                            any((to_select := heathen).location == (adj_x, adj_y) for heathen in heathens):
                        self.selected_unit = to_select
                        self.overlay.toggle_unit(to_select)
                    # If the player has selected one of their units and it hasn't attacked, and they've clicked on
                    # either an enemy unit or a heathen within range, attack it.
                    elif self.selected_unit is not None and not isinstance(self.selected_unit, Heathen) and \
                            self.selected_unit in player.units and not self.selected_unit.has_attacked and \
                            (any((to_attack := heathen).location == (adj_x, adj_y) for heathen in heathens) or
                             any((to_attack := unit).location == (adj_x, adj_y) for unit in all_units)):
                        if self.selected_unit is not to_attack and to_attack not in player.units and \
                                abs(self.selected_unit.location[0] - to_attack.location[0]) <= 1 and \
                                abs(self.selected_unit.location[1] - to_attack.location[1]) <= 1:
                            data = attack(self.selected_unit, to_attack, ai=False)
                            # Destroy the player's unit if it died.
                            if self.selected_unit.health <= 0:
                                player.units.remove(self.selected_unit)
                                self.selected_unit = None
                                self.overlay.toggle_unit(None)
                            # Destroy the heathen/enemy unit if it died.
                            if to_attack.health <= 0:
                                if to_attack in heathens:
                                    heathens.remove(to_attack)
                                else:
                                    for p in all_players:
                                        if to_attack in p.units:
                                            p.units.remove(to_attack)
                                            break
                            # Show the attack results.
                            self.overlay.toggle_attack(data)
                            self.attack_time_bank = 0
                        # However, if the player clicked on another of their units, select that rather than attacking.
                        elif to_attack in player.units:
                            self.selected_unit = to_attack
                            self.overlay.update_unit(to_attack)
                    # If the player has selected one of their units and it hasn't attacked, and the player clicks on an
                    # enemy settlement within range, bring up the overlay to prompt the player on their action.
                    elif self.selected_unit is not None and not isinstance(self.selected_unit, Heathen) and \
                            self.selected_unit in player.units and not self.selected_unit.has_attacked and \
                            any((to_attack := setl).location == (adj_x, adj_y) for setl in other_setls):
                        if abs(self.selected_unit.location[0] - to_attack.location[0]) <= 1 and \
                                abs(self.selected_unit.location[1] - to_attack.location[1]) <= 1:
                            for p in all_players:
                                if to_attack in p.settlements:
                                    self.overlay.toggle_setl_click(to_attack, p)
                    # If the player has not selected a unit and they click on one, select it.
                    elif self.selected_unit is None and \
                            any((to_select := unit).location == (adj_x, adj_y) for unit in all_units):
                        self.selected_unit = to_select
                        self.overlay.toggle_unit(to_select)
                    # If the player has selected one of their units and they've clicked an empty quad within range, move
                    # the unit there.
                    elif self.selected_unit is not None and not isinstance(self.selected_unit, Heathen) and \
                            not any(heathen.location == (adj_x, adj_y) for heathen in heathens) and \
                            self.selected_unit in player.units and \
                            not any(unit.location == (adj_x, adj_y) for unit in all_units) and \
                            not any(setl.location == (adj_x, adj_y) for setl in other_setls) and \
                            not self.quads[adj_y][adj_x].is_relic and \
                            self.selected_unit.location[0] - self.selected_unit.remaining_stamina <= adj_x <= \
                            self.selected_unit.location[0] + self.selected_unit.remaining_stamina and \
                            self.selected_unit.location[1] - self.selected_unit.remaining_stamina <= adj_y <= \
                            self.selected_unit.location[1] + self.selected_unit.remaining_stamina:
                        # Any unit that moves while sieging ends their siege on the settlement.
                        if self.selected_unit.sieging:
                            self.selected_unit.sieging = False
                            for setl in other_setls:
                                if setl.under_siege_by is self.selected_unit:
                                    setl.under_siege_by = None
                        initial = self.selected_unit.location
                        distance_travelled = max(abs(initial[0] - adj_x), abs(initial[1] - adj_y))
                        self.selected_unit.remaining_stamina -= distance_travelled
                        self.selected_unit.location = adj_x, adj_y
                        # Update the player's seen quads.
                        for i in range(adj_y - 5, adj_y + 6):
                            for j in range(adj_x - 5, adj_x + 6):
                                player.quads_seen.add((j, i))
                    # If the player has selected one of their units and clicked on a relic, investigate it, providing
                    # that their unit is close enough.
                    elif self.selected_unit is not None and self.selected_unit in player.units and \
                            self.quads[adj_y][adj_x].is_relic:
                        if abs(self.selected_unit.location[0] - adj_x) <= 1 and \
                                abs(self.selected_unit.location[1] - adj_y) <= 1:
                            result: InvestigationResult = investigate_relic(player,
                                                                            self.selected_unit,
                                                                            (adj_x, adj_y),
                                                                            self.game_config)
                            # Relics cease to exist once investigated.
                            self.quads[adj_y][adj_x].is_relic = False
                            self.overlay.toggle_investigation(result)
                    # Lastly, if the player has selected a unit and they click elsewhere, deselect the unit.
                    elif self.selected_unit is not None and self.selected_unit.location != (adj_x, adj_y):
                        self.selected_unit = None
                        self.overlay.toggle_unit(None)

    def handle_new_settlement(self, player: Player):
        """
        Found a new settlement for the given player if permitted.
        :param player: The player founding the settlement.
        """
        can_settle = True
        for setl in player.settlements:
            # Of course, players cannot found settlements where they already have one.
            if setl.location == self.selected_unit.location:
                can_settle = False
                break
        if can_settle:
            quad_biome = self.quads[self.selected_unit.location[1]][self.selected_unit.location[0]].biome
            setl_name = self.namer.get_settlement_name(quad_biome)
            new_settl = Settlement(setl_name, self.selected_unit.location, [],
                                   [self.quads[self.selected_unit.location[1]][self.selected_unit.location[0]]], [])
            if player.faction is Faction.FRONTIERSMEN:
                new_settl.satisfaction = 75
            elif player.faction is Faction.IMPERIALS:
                new_settl.strength /= 2
                new_settl.max_strength /= 2
            player.settlements.append(new_settl)
            # Destroy the settler unit and select the new settlement.
            player.units.remove(self.selected_unit)
            self.selected_unit = None
            self.overlay.toggle_unit(None)
            self.selected_settlement = new_settl
            self.overlay.toggle_settlement(new_settl, player)
