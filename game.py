import datetime
import json
import os
import random
import time
import typing
from itertools import chain

import pyxel

from board import Board
from calculator import clamp, attack, get_setl_totals, complete_construction, attack_setl
from catalogue import get_available_improvements, get_available_blessings, get_available_unit_plans, get_heathen, \
    get_default_unit, get_improvement, get_blessing, get_unit_plan, Namer, FACTION_COLOURS, PROJECTS, get_project
from menu import Menu, MainMenuOption, SetupOption, WikiOption
from models import Player, Settlement, Construction, OngoingBlessing, CompletedConstruction, Unit, HarvestStatus, \
    EconomicStatus, Heathen, AttackPlaystyle, GameConfig, Biome, Victory, VictoryType, AIPlaystyle, \
    ExpansionPlaystyle, UnitPlan, OverlayType, Faction, ConstructionMenu, Project
from movemaker import MoveMaker, set_player_construction
from music_player import MusicPlayer
from overlay import SettlementAttackType, PauseOption
from save_encoder import SaveEncoder, ObjectConverter

# The prefix attached to save files created by the autosave feature.
AUTOSAVE_PREFIX = "auto"
# The directory where save files are created and loaded from.
SAVES_DIR = "saves"


class Game:
    """
    The main class for the game. Contains the majority of business logic, and none of the drawing.
    """

    def __init__(self):
        """
        Initialises the game.
        """
        pyxel.init(200, 200, title="Microcosm", quit_key=pyxel.KEY_NONE)

        self.menu = Menu()
        self.board: typing.Optional[Board] = None
        self.players: typing.List[Player] = []
        self.heathens: typing.List[Heathen] = []

        self.on_menu = True
        self.game_started = False

        self.last_time = time.time()

        # The map begins at a random position.
        self.map_pos: (int, int) = random.randint(0, 76), random.randint(0, 68)
        self.turn = 1

        self.music_player = MusicPlayer()
        self.music_player.play_menu_music()

        self.namer = Namer()
        self.move_maker = MoveMaker(self.namer)

        random.seed()
        # There will always be a 10-20 turn break between nights.
        self.until_night: int = random.randint(10, 20)
        # Also keep track of how many turns of night are left. If this is 0, it is daytime.
        self.nighttime_left = 0

        pyxel.run(self.on_update, self.draw)

    def on_update(self):
        """
        On every update, calculate the elapsed time, manage music, and respond to key presses.
        """
        time_elapsed = time.time() - self.last_time
        self.last_time = time.time()

        if self.board is not None:
            self.board.update(time_elapsed)

        if not self.on_menu and not self.music_player.is_playing():
            self.music_player.next_song()

        all_units = []
        for player in self.players:
            for unit in player.units:
                all_units.append(unit)

        if pyxel.btnp(pyxel.KEY_DOWN):
            if self.on_menu:
                self.menu.navigate(down=True)
            elif self.game_started:
                if self.board.overlay.is_constructing():
                    self.board.overlay.navigate_constructions(down=True)
                elif self.board.overlay.is_blessing():
                    self.board.overlay.navigate_blessings(down=True)
                elif self.board.overlay.is_setl_click():
                    self.board.overlay.navigate_setl_click(down=True)
                elif self.board.overlay.is_pause():
                    self.board.overlay.navigate_pause(down=True)
                elif self.board.overlay.is_standard():
                    self.board.overlay.navigate_standard(down=True)
                else:
                    self.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press down.
                    # Holding Ctrl will pan the map 5 spaces.
                    if pyxel.btn(pyxel.KEY_CTRL):
                        self.map_pos = self.map_pos[0], clamp(self.map_pos[1] + 5, -1, 69)
                    else:
                        self.map_pos = self.map_pos[0], clamp(self.map_pos[1] + 1, -1, 69)
        elif pyxel.btnp(pyxel.KEY_UP):
            if self.on_menu:
                self.menu.navigate(up=True)
            elif self.game_started:
                if self.board.overlay.is_constructing():
                    self.board.overlay.navigate_constructions(down=False)
                elif self.board.overlay.is_blessing():
                    self.board.overlay.navigate_blessings(down=False)
                elif self.board.overlay.is_setl_click():
                    self.board.overlay.navigate_setl_click(up=True)
                elif self.board.overlay.is_pause():
                    self.board.overlay.navigate_pause(down=False)
                elif self.board.overlay.is_standard():
                    self.board.overlay.navigate_standard(down=False)
                else:
                    self.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press up.
                    # Holding Ctrl will pan the map 5 spaces.
                    if pyxel.btn(pyxel.KEY_CTRL):
                        self.map_pos = self.map_pos[0], clamp(self.map_pos[1] - 5, -1, 69)
                    else:
                        self.map_pos = self.map_pos[0], clamp(self.map_pos[1] - 1, -1, 69)
        elif pyxel.btnp(pyxel.KEY_LEFT):
            if self.on_menu:
                self.menu.navigate(left=True)
            if self.game_started and self.board.overlay.is_constructing():
                if self.board.overlay.current_construction_menu is ConstructionMenu.PROJECTS and \
                        len(self.board.overlay.available_constructions) > 0:
                    self.board.overlay.current_construction_menu = ConstructionMenu.IMPROVEMENTS
                    self.board.overlay.selected_construction = self.board.overlay.available_constructions[0]
                elif self.board.overlay.current_construction_menu is ConstructionMenu.UNITS:
                    self.board.overlay.current_construction_menu = ConstructionMenu.PROJECTS
                    self.board.overlay.selected_construction = self.board.overlay.available_projects[0]
            elif self.game_started:
                if self.board.overlay.is_setl_click():
                    self.board.overlay.navigate_setl_click(left=True)
                else:
                    self.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press left.
                    # Holding Ctrl will pan the map 5 spaces.
                    if pyxel.btn(pyxel.KEY_CTRL):
                        self.map_pos = clamp(self.map_pos[0] - 5, -1, 77), self.map_pos[1]
                    else:
                        self.map_pos = clamp(self.map_pos[0] - 1, -1, 77), self.map_pos[1]
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            if self.on_menu:
                self.menu.navigate(right=True)
            if self.game_started and self.board.overlay.is_constructing():
                if self.board.overlay.current_construction_menu is ConstructionMenu.IMPROVEMENTS:
                    self.board.overlay.current_construction_menu = ConstructionMenu.PROJECTS
                    self.board.overlay.selected_construction = self.board.overlay.available_projects[0]
                elif self.board.overlay.current_construction_menu is ConstructionMenu.PROJECTS:
                    self.board.overlay.current_construction_menu = ConstructionMenu.UNITS
                    self.board.overlay.selected_construction = self.board.overlay.available_unit_plans[0]
                    self.board.overlay.unit_plan_boundaries = 0, 5
            elif self.game_started:
                if self.board.overlay.is_setl_click():
                    self.board.overlay.navigate_setl_click(right=True)
                else:
                    self.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press right.
                    # Holding Ctrl will pan the map 5 spaces.
                    if pyxel.btn(pyxel.KEY_CTRL):
                        self.map_pos = clamp(self.map_pos[0] + 5, -1, 77), self.map_pos[1]
                    else:
                        self.map_pos = clamp(self.map_pos[0] + 1, -1, 77), self.map_pos[1]
        elif pyxel.btnp(pyxel.KEY_RETURN):
            if self.on_menu:
                if self.menu.in_game_setup and self.menu.setup_option is SetupOption.START_GAME:
                    # If the player has pressed enter to start the game, generate the players, board, and AI players.
                    pyxel.mouse(visible=True)
                    self.game_started = True
                    self.turn = 1
                    # Reinitialise night variables.
                    random.seed()
                    self.until_night: int = random.randint(10, 20)
                    self.nighttime_left = 0
                    self.on_menu = False
                    cfg: GameConfig = self.menu.get_game_config()
                    self.gen_players(cfg)
                    self.board = Board(cfg, self.namer)
                    self.move_maker.board_ref = self.board
                    self.board.overlay.toggle_tutorial()
                    self.namer.reset()
                    self.initialise_ais()
                    self.music_player.stop_menu_music()
                    self.music_player.play_game_music()
                elif self.menu.loading_game:
                    if self.menu.save_idx == -1:
                        self.menu.loading_game = False
                    else:
                        self.load_game(self.menu.save_idx)
                elif self.menu.in_wiki:
                    if self.menu.wiki_option is WikiOption.BACK:
                        self.menu.in_wiki = False
                    else:
                        self.menu.wiki_showing = self.menu.wiki_option
                else:
                    match self.menu.main_menu_option:
                        case MainMenuOption.NEW_GAME:
                            self.menu.in_game_setup = True
                        case MainMenuOption.LOAD_GAME:
                            self.menu.loading_game = True
                            self.get_saves()
                        case MainMenuOption.WIKI:
                            self.menu.in_wiki = True
                        case MainMenuOption.EXIT:
                            pyxel.quit()
            elif self.game_started and (self.board.overlay.is_victory() or
                                        self.board.overlay.is_elimination() and self.players[0].eliminated):
                # If the player has won the game, or they've just been eliminated themselves, enter will take them back
                # to the menu.
                self.game_started = False
                self.on_menu = True
                self.menu.loading_game = False
                self.menu.in_game_setup = False
                self.menu.main_menu_option = MainMenuOption.NEW_GAME
                self.music_player.stop_game_music()
                self.music_player.play_menu_music()
            # If the player is choosing a blessing or construction, enter will select it.
            elif self.game_started and self.board.overlay.is_constructing():
                if self.board.overlay.selected_construction is not None:
                    self.board.selected_settlement.current_work = Construction(self.board.overlay.selected_construction)
                self.board.overlay.toggle_construction([], [], [])
            elif self.game_started and self.board.overlay.is_blessing():
                if self.board.overlay.selected_blessing is not None:
                    self.players[0].ongoing_blessing = OngoingBlessing(self.board.overlay.selected_blessing)
                self.board.overlay.toggle_blessing([])
            elif self.game_started and self.board.overlay.is_setl_click():
                match self.board.overlay.setl_attack_opt:
                    # If the player has chosen to attack a settlement, execute the attack.
                    case SettlementAttackType.ATTACK:
                        self.board.overlay.toggle_setl_click(None, None)
                        data = attack_setl(self.board.selected_unit, self.board.overlay.attacked_settlement,
                                           self.board.overlay.attacked_settlement_owner, False)
                        if data.attacker_was_killed:
                            # If the player's unit died, destroy and deselect it.
                            self.players[0].units.remove(self.board.selected_unit)
                            self.board.selected_unit = None
                            self.board.overlay.toggle_unit(None)
                        elif data.setl_was_taken:
                            # If the settlement was taken, transfer it to the player.
                            data.settlement.under_siege_by = None
                            # The Concentrated can only have a single settlement, so when they take others, the
                            # settlements simply disappear.
                            if self.players[0].faction is not Faction.CONCENTRATED:
                                self.players[0].settlements.append(data.settlement)
                            for idx, p in enumerate(self.players):
                                if data.settlement in p.settlements and idx != 0:
                                    p.settlements.remove(data.settlement)
                                    break
                        self.board.overlay.toggle_setl_attack(data)
                        self.board.attack_time_bank = 0
                    case SettlementAttackType.BESIEGE:
                        # Alternatively, begin a siege on the settlement.
                        self.board.selected_unit.sieging = True
                        self.board.overlay.attacked_settlement.under_siege_by = self.board.selected_unit
                        self.board.overlay.toggle_setl_click(None, None)
                    case _:
                        self.board.overlay.toggle_setl_click(None, None)
            elif self.game_started and self.board.overlay.is_pause():
                match self.board.overlay.pause_option:
                    case PauseOption.RESUME:
                        self.board.overlay.toggle_pause()
                    case PauseOption.SAVE:
                        self.save_game()
                        self.board.overlay.has_saved = True
                    case PauseOption.CONTROLS:
                        self.board.overlay.toggle_controls()
                    case PauseOption.QUIT:
                        self.game_started = False
                        self.on_menu = True
                        self.menu.loading_game = False
                        self.menu.in_game_setup = False
                        self.menu.main_menu_option = MainMenuOption.NEW_GAME
                        self.music_player.stop_game_music()
                        self.music_player.play_menu_music()
            elif self.game_started and not (self.board.overlay.is_tutorial() or self.board.overlay.is_deployment() or
                                            self.board.overlay.is_bless_notif() or
                                            self.board.overlay.is_constr_notif() or self.board.overlay.is_lvl_notif() or
                                            self.board.overlay.is_close_to_vic() or
                                            self.board.overlay.is_investigation() or self.board.overlay.is_night()):
                # If we are not in any of the above situations, end the turn.
                if self.end_turn():
                    self.board.overlay.update_turn(self.turn)
                    self.process_heathens()
                    self.process_ais()
        # Mouse clicks are forwarded to the Board for processing.
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            if self.game_started:
                self.board.overlay.remove_warning_if_possible()
                self.board.process_right_click(pyxel.mouse_x, pyxel.mouse_y, self.map_pos)
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.game_started:
                other_setls = []
                for i in range(1, len(self.players)):
                    other_setls.extend(self.players[i].settlements)
                self.board.overlay.remove_warning_if_possible()
                self.board.process_left_click(pyxel.mouse_x, pyxel.mouse_y,
                                              len(self.players[0].settlements) > 0,
                                              self.players[0], self.map_pos, self.heathens, all_units,
                                              self.players, other_setls)
        elif pyxel.btnp(pyxel.KEY_SHIFT):
            if self.game_started:
                self.board.overlay.remove_warning_if_possible()
                # Display the standard overlay.
                self.board.overlay.toggle_standard(self.turn)
        elif pyxel.btnp(pyxel.KEY_C):
            if self.game_started and self.board.selected_settlement is not None:
                # Pick a construction.
                self.board.overlay.toggle_construction(get_available_improvements(self.players[0],
                                                                                  self.board.selected_settlement),
                                                       PROJECTS,
                                                       get_available_unit_plans(self.players[0],
                                                                                self.board.selected_settlement.level))
        elif pyxel.btnp(pyxel.KEY_F):
            if self.on_menu and self.menu.in_game_setup and self.menu.setup_option is SetupOption.PLAYER_FACTION:
                self.menu.showing_faction_details = not self.menu.showing_faction_details
            elif self.game_started and self.board.overlay.is_standard():
                # Pick a blessing.
                self.board.overlay.toggle_blessing(get_available_blessings(self.players[0]))
        elif pyxel.btnp(pyxel.KEY_D):
            if self.game_started and self.board.selected_settlement is not None and \
                    len(self.board.selected_settlement.garrison) > 0:
                self.board.deploying_army = True
                self.board.overlay.toggle_deployment()
            elif self.game_started and self.board.selected_unit is not None and \
                    self.board.selected_unit in self.players[0].units:
                # If a unit is selected rather than a settlement, pressing D disbands the army, destroying the unit and
                # adding to the player's wealth.
                self.players[0].wealth += self.board.selected_unit.plan.cost
                self.players[0].units.remove(self.board.selected_unit)
                self.board.selected_unit = None
                self.board.overlay.toggle_unit(None)
        elif pyxel.btnp(pyxel.KEY_TAB):
            # Pressing tab iterates through the player's settlements, centreing on each one.
            if self.game_started and self.board.overlay.can_iter_settlements_units() and \
                    len(self.players[0].settlements) > 0:
                self.board.overlay.remove_warning_if_possible()
                if self.board.overlay.is_unit():
                    self.board.selected_unit = None
                    self.board.overlay.toggle_unit(None)
                if self.board.selected_settlement is None:
                    self.board.selected_settlement = self.players[0].settlements[0]
                    self.board.overlay.toggle_settlement(self.players[0].settlements[0], self.players[0])
                elif len(self.players[0].settlements) > 1:
                    current_idx = self.players[0].settlements.index(self.board.selected_settlement)
                    new_idx = 0
                    if current_idx != len(self.players[0].settlements) - 1:
                        new_idx = current_idx + 1
                    self.board.selected_settlement = self.players[0].settlements[new_idx]
                    self.board.overlay.update_settlement(self.players[0].settlements[new_idx])
                self.map_pos = (clamp(self.board.selected_settlement.location[0] - 12, -1, 77),
                                clamp(self.board.selected_settlement.location[1] - 11, -1, 69))
        elif pyxel.btnp(pyxel.KEY_SPACE):
            # Pressing space either dismisses the current overlay or iterates through the player's units.
            if self.on_menu and self.menu.in_wiki and self.menu.wiki_showing is not None:
                self.menu.wiki_showing = None
            if self.on_menu and self.menu.in_game_setup:
                self.menu.in_game_setup = False
            if self.on_menu and self.menu.loading_game:
                self.menu.loading_game = False
            if self.game_started and self.board.overlay.is_elimination():
                self.board.overlay.toggle_elimination(None)
            elif self.game_started and self.board.overlay.is_night():
                self.board.overlay.toggle_night(None)
            elif self.game_started and self.board.overlay.is_close_to_vic():
                self.board.overlay.toggle_close_to_vic([])
            elif self.game_started and self.board.overlay.is_bless_notif():
                self.board.overlay.toggle_blessing_notification(None)
            elif self.game_started and self.board.overlay.is_constr_notif():
                self.board.overlay.toggle_construction_notification(None)
            elif self.game_started and self.board.overlay.is_lvl_notif():
                self.board.overlay.toggle_level_up_notification(None)
            elif self.game_started and self.board.overlay.is_controls():
                self.board.overlay.toggle_controls()
            elif self.game_started and self.board.overlay.is_investigation():
                self.board.overlay.toggle_investigation(None)
            elif self.game_started and self.board.overlay.can_iter_settlements_units() and \
                    len(self.players[0].units) > 0:
                self.board.overlay.remove_warning_if_possible()
                if self.board.overlay.is_setl():
                    self.board.selected_settlement = None
                    self.board.overlay.toggle_settlement(None, self.players[0])
                if self.board.selected_unit is None or isinstance(self.board.selected_unit, Heathen):
                    self.board.selected_unit = self.players[0].units[0]
                    self.board.overlay.toggle_unit(self.players[0].units[0])
                elif len(self.players[0].units) > 1:
                    current_idx = self.players[0].units.index(self.board.selected_unit)
                    new_idx = 0
                    if current_idx != len(self.players[0].units) - 1:
                        new_idx = current_idx + 1
                    self.board.selected_unit = self.players[0].units[new_idx]
                    self.board.overlay.update_unit(self.players[0].units[new_idx])
                self.map_pos = (clamp(self.board.selected_unit.location[0] - 12, -1, 77),
                                clamp(self.board.selected_unit.location[1] - 11, -1, 69))
        elif pyxel.btnp(pyxel.KEY_S):
            if self.game_started and self.board.selected_unit is not None and self.board.selected_unit.plan.can_settle:
                # Units that can settle can found new settlements when S is pressed.
                self.board.handle_new_settlement(self.players[0])
        elif pyxel.btnp(pyxel.KEY_N):
            if self.game_started:
                self.music_player.next_song()
        elif pyxel.btnp(pyxel.KEY_B):
            if self.game_started and self.board.selected_settlement is not None and \
                    self.board.selected_settlement.current_work is not None and \
                    self.players[0].faction is not Faction.FUNDAMENTALISTS and \
                    not isinstance(self.board.selected_settlement.current_work.construction, Project):
                # Pressing B will buyout the remaining cost of the settlement's current construction. However, players
                # using the Fundamentalists faction are barred from this.
                current_work = self.board.selected_settlement.current_work
                remaining_work = current_work.construction.cost - current_work.zeal_consumed
                if self.players[0].wealth >= remaining_work:
                    self.board.overlay.toggle_construction_notification([
                        CompletedConstruction(self.board.selected_settlement.current_work.construction,
                                              self.board.selected_settlement)
                    ])
                    complete_construction(self.board.selected_settlement, self.players[0])
                    self.players[0].wealth -= remaining_work
        elif pyxel.btnp(pyxel.KEY_ESCAPE):
            if self.game_started and not self.board.overlay.is_victory() and not self.board.overlay.is_elimination():
                # Show the pause menu if there are no intrusive overlays being shown.
                if not self.board.overlay.showing or \
                        all(overlay in (OverlayType.ATTACK, OverlayType.SETL_ATTACK, OverlayType.SIEGE_NOTIF)
                            for overlay in self.board.overlay.showing):
                    self.board.overlay.toggle_pause()
                # Remove one overlay layer per ESCAPE press, assuming it is a layer that can be removed.
                elif not self.board.overlay.is_tutorial() and not self.board.overlay.is_deployment():
                    to_reset: typing.Optional[OverlayType] = self.board.overlay.remove_layer()
                    # Make sure we reset board selections if necessary.
                    if to_reset == OverlayType.UNIT:
                        self.board.selected_unit = None
                    elif to_reset == OverlayType.SETTLEMENT:
                        self.board.selected_settlement = None
        elif pyxel.btnp(pyxel.KEY_A):
            if self.game_started and self.board.overlay.is_setl() and \
                    self.board.selected_settlement.current_work is None:
                # Pressing the A key while a player settlement with no active construction is selected results in the
                # selection being made automatically (in much the same way that AI settlements have their constructions
                # selected).
                set_player_construction(self.players[0], self.board.selected_settlement, self.nighttime_left > 0)

    def draw(self):
        """
        Draws the game to the screen.
        """
        if self.on_menu:
            self.menu.draw()
        elif self.game_started:
            self.board.draw(self.players, self.map_pos, self.turn, self.heathens, self.nighttime_left > 0,
                            self.until_night if self.until_night != 0 else self.nighttime_left)

    def gen_players(self, cfg: GameConfig):
        """
        Generates the players for the game based on the supplied config.
        :param cfg: The game config.
        """
        self.players = [Player("The Chosen One", cfg.player_faction, FACTION_COLOURS[cfg.player_faction],
                               0, [], [], [], set(), set())]
        factions = list(Faction)
        # Ensure that an AI player doesn't choose the same faction as the player.
        factions.remove(cfg.player_faction)
        for i in range(1, cfg.player_count):
            faction = random.choice(factions)
            factions.remove(faction)
            self.players.append(Player(f"NPC{i}", faction, FACTION_COLOURS[faction], 0, [], [], [], set(), set(),
                                       ai_playstyle=AIPlaystyle(random.choice(list(AttackPlaystyle)),
                                                                random.choice(list(ExpansionPlaystyle)))))

    def end_turn(self) -> bool:
        """
        Ends the current game turn, processing settlements, blessings, and units.
        :return: Whether the turn was successfully ended. Will be False in cases where a warning is generated, or the
        game ends.
        """
        # First make sure the player hasn't ended their turn without a construction or blessing.
        problematic_settlements = []
        total_wealth = 0
        for setl in self.players[0].settlements:
            if setl.current_work is None:
                problematic_settlements.append(setl)
            total_wealth += sum(quad.wealth for quad in setl.quads)
            total_wealth += sum(imp.effect.wealth for imp in setl.improvements)
            total_wealth += (setl.level - 1) * 0.25 * total_wealth
            if setl.economic_status is EconomicStatus.RECESSION:
                total_wealth = 0
            elif setl.economic_status is EconomicStatus.BOOM:
                total_wealth *= 1.5
        for unit in self.players[0].units:
            if not unit.garrisoned:
                total_wealth -= unit.plan.cost / 25
        if self.players[0].faction is Faction.GODLESS:
            total_wealth *= 1.25
        elif self.players[0].faction is Faction.ORTHODOX:
            total_wealth *= 0.75
        has_no_blessing = self.players[0].ongoing_blessing is None
        will_have_negative_wealth = (self.players[0].wealth + total_wealth) < 0 and len(self.players[0].units) > 0
        if not self.board.overlay.is_warning() and \
                (len(problematic_settlements) > 0 or has_no_blessing or will_have_negative_wealth):
            self.board.overlay.toggle_warning(problematic_settlements, has_no_blessing, will_have_negative_wealth)
            return False

        for player in self.players:
            overall_fortune = 0
            overall_wealth = 0
            completed_constructions: typing.List[CompletedConstruction] = []
            levelled_up_settlements: typing.List[Settlement] = []
            for setl in player.settlements:
                # Based on the settlement's satisfaction, place the settlement in a specific state of wealth and
                # harvest. More specifically, a satisfaction of less than 20 will yield 0 wealth and 0 harvest, a
                # satisfaction of [20, 40) will yield 0 harvest, a satisfaction of [60, 80) will yield 150% harvest,
                # and a satisfaction of 80 or more will yield 150% wealth and 150% harvest.
                if setl.satisfaction < 20:
                    if player.faction is not Faction.AGRICULTURISTS:
                        setl.harvest_status = HarvestStatus.POOR
                    if player.faction is not Faction.CAPITALISTS:
                        setl.economic_status = EconomicStatus.RECESSION
                elif setl.satisfaction < 40:
                    if player.faction is not Faction.AGRICULTURISTS:
                        setl.harvest_status = HarvestStatus.POOR
                    setl.economic_status = EconomicStatus.STANDARD
                elif setl.satisfaction < 60:
                    setl.harvest_status = HarvestStatus.STANDARD
                    setl.economic_status = EconomicStatus.STANDARD
                elif setl.satisfaction < 80:
                    setl.harvest_status = HarvestStatus.PLENTIFUL
                    setl.economic_status = EconomicStatus.STANDARD
                else:
                    setl.harvest_status = HarvestStatus.PLENTIFUL
                    setl.economic_status = EconomicStatus.BOOM

                total_wealth, total_harvest, total_zeal, total_fortune = \
                    get_setl_totals(player, setl, self.nighttime_left > 0)
                overall_fortune += total_fortune
                overall_wealth += total_wealth

                # If the settlement is under siege, decrease its strength, ensuring that the sieging unit is still
                # alive.
                if setl.under_siege_by is not None:
                    found_unit = False
                    for p in self.players:
                        if setl.under_siege_by in p.units:
                            found_unit = True
                            break
                    if not found_unit:
                        setl.under_siege_by = None
                    else:
                        if setl.under_siege_by.health <= 0:
                            setl.under_siege_by = None
                        else:
                            setl.strength = max(0.0, setl.strength - setl.max_strength * 0.1)
                else:
                    # Otherwise, increase the settlement's strength if it was recently under siege and is not at full
                    # strength.
                    if setl.strength < setl.max_strength:
                        setl.strength = min(setl.strength + setl.max_strength * 0.1, setl.max_strength)

                # Reset all units in the garrison in case any were garrisoned this turn.
                for g in setl.garrison:
                    g.has_attacked = False
                    g.remaining_stamina = g.plan.total_stamina
                    if g.health < g.plan.max_health:
                        g.health = min(g.health + g.plan.max_health * 0.1, g.plan.max_health)

                # Settlement satisfaction is regulated by the amount of harvest generated against the level.
                if total_harvest < setl.level * 4:
                    setl.satisfaction -= (1 if player.faction is Faction.CAPITALISTS else 0.5)
                elif total_harvest >= setl.level * 8:
                    setl.satisfaction += 0.25
                setl.satisfaction = clamp(setl.satisfaction, 0, 100)

                # Process the current construction, completing it if it has been finished.
                if setl.current_work is not None and not isinstance(setl.current_work.construction, Project):
                    setl.current_work.zeal_consumed += total_zeal
                    if setl.current_work.zeal_consumed >= setl.current_work.construction.cost:
                        completed_constructions.append(CompletedConstruction(setl.current_work.construction, setl))
                        complete_construction(setl, player)

                setl.harvest_reserves += total_harvest
                # Settlement levels are increased if the settlement's harvest reserves exceed a certain level (specified
                # in models.py).
                level_cap = 5 if player.faction is Faction.RAVENOUS else 10
                if setl.harvest_reserves >= pow(setl.level, 2) * 25 and setl.level < level_cap:
                    setl.level += 1
                    levelled_up_settlements.append(setl)

            # Show notifications if the player's constructions have completed or one of their settlements has levelled
            # up.
            if player.ai_playstyle is None and len(completed_constructions) > 0:
                self.board.overlay.toggle_construction_notification(completed_constructions)
            if player.ai_playstyle is None and len(levelled_up_settlements) > 0:
                self.board.overlay.toggle_level_up_notification(levelled_up_settlements)
            # Reset all units.
            for unit in player.units:
                unit.remaining_stamina = unit.plan.total_stamina
                # Heal the unit.
                if unit.health < unit.plan.max_health:
                    unit.health = min(unit.health + unit.plan.max_health * 0.1, unit.plan.max_health)
                unit.has_attacked = False
                overall_wealth -= unit.plan.cost / 25
            # Process the current blessing, completing it if it was finished.
            if player.ongoing_blessing is not None:
                player.ongoing_blessing.fortune_consumed += overall_fortune
                if player.ongoing_blessing.fortune_consumed >= player.ongoing_blessing.blessing.cost:
                    player.blessings.append(player.ongoing_blessing.blessing)
                    # Show a notification if the player is non-AI.
                    if player.ai_playstyle is None:
                        self.board.overlay.toggle_blessing_notification(player.ongoing_blessing.blessing)
                    player.ongoing_blessing = None
            # If the player's wealth will go into the negative this turn, sell their units until it's above 0 again.
            while player.wealth + overall_wealth < 0:
                sold_unit = player.units.pop()
                if self.board.selected_unit is sold_unit:
                    self.board.selected_unit = None
                    self.board.overlay.toggle_unit(None)
                player.wealth += sold_unit.plan.cost
            # Update the player's wealth.
            player.wealth = max(player.wealth + overall_wealth, 0)
            player.accumulated_wealth += overall_wealth

        # Spawn a heathen every 5 turns.
        if self.turn % 5 == 0:
            heathen_loc = random.randint(0, 89), random.randint(0, 99)
            self.heathens.append(get_heathen(heathen_loc, self.turn))

        # Reset all heathens.
        for heathen in self.heathens:
            heathen.remaining_stamina = heathen.plan.total_stamina
            if heathen.health < heathen.plan.max_health:
                heathen.health = min(heathen.health + heathen.plan.max_health * 0.1, 100)

        self.board.overlay.remove_warning_if_possible()
        self.turn += 1

        # Make night-related calculations, but only if climatic effects are enabled.
        if self.board.game_config.climatic_effects:
            random.seed()
            if self.nighttime_left == 0:
                self.until_night -= 1
                if self.until_night == 0:
                    self.board.overlay.toggle_night(True)
                    # Nights last for between 5 and 20 turns.
                    self.nighttime_left = random.randint(5, 20)
                    for h in self.heathens:
                        h.plan.power = round(2 * h.plan.power)
                    if self.players[0].faction is Faction.NOCTURNE:
                        for u in self.players[0].units:
                            u.plan.power = round(2 * u.plan.power)
                        for setl in self.players[0].settlements:
                            for unit in setl.garrison:
                                unit.plan.power = round(2 * unit.plan.power)
            else:
                self.nighttime_left -= 1
                if self.nighttime_left == 0:
                    self.until_night = random.randint(10, 20)
                    self.board.overlay.toggle_night(False)
                    for h in self.heathens:
                        h.plan.power = round(h.plan.power / 2)
                    if self.players[0].faction is Faction.NOCTURNE:
                        for u in self.players[0].units:
                            u.plan.power = round(u.plan.power / 4)
                            u.health = round(u.health / 2)
                            u.plan.max_health = round(u.plan.max_health / 2)
                            u.plan.total_stamina = round(u.plan.total_stamina / 2)
                        for setl in self.players[0].settlements:
                            for unit in setl.garrison:
                                unit.plan.power = round(unit.plan.power / 4)
                                unit.health = round(unit.health / 2)
                                unit.plan.max_health = round(unit.plan.max_health / 2)
                                unit.plan.total_stamina = round(unit.plan.total_stamina / 2)

        # Autosave every 10 turns.
        if self.turn % 10 == 0:
            self.save_game(auto=True)

        possible_victory = self.check_for_victory()
        if possible_victory is not None:
            self.board.overlay.toggle_victory(possible_victory)
            return False
        return True

    def check_for_victory(self) -> typing.Optional[Victory]:
        """
        Check if any of the six victories have been achieved by any of the players. Also check if any players are close
        to a victory.
        :return: A Victory, if one has been achieved.
        """
        close_to_vics: typing.List[Victory] = []
        all_setls = []
        for pl in self.players:
            all_setls.extend(pl.settlements)

        players_with_setls = 0
        for p in self.players:
            if len(p.settlements) > 0:
                jubilated_setls = 0
                lvl_ten_setls = 0
                constructed_sanctum = False

                # If a player controls all settlements bar one, they are close to an ELIMINATION victory.
                if len(p.settlements) + 1 == len(all_setls) and VictoryType.ELIMINATION not in p.imminent_victories:
                    close_to_vics.append(Victory(p, VictoryType.ELIMINATION))
                    p.imminent_victories.add(VictoryType.ELIMINATION)

                players_with_setls += 1
                for s in p.settlements:
                    if s.satisfaction == 100:
                        jubilated_setls += 1
                    if s.level == 10:
                        lvl_ten_setls += 1
                    if any(imp.name == "Holy Sanctum" for imp in s.improvements):
                        constructed_sanctum = True
                    # If a player is currently constructing the Holy Sanctum, they are close to a VIGOUR victory.
                    elif s.current_work is not None and s.current_work.construction.name == "Holy Sanctum" and \
                            VictoryType.VIGOUR not in p.imminent_victories:
                        close_to_vics.append(Victory(p, VictoryType.VIGOUR))
                        p.imminent_victories.add(VictoryType.VIGOUR)
                if jubilated_setls >= 5:
                    p.jubilation_ctr += 1
                    # If a player has achieved 100% satisfaction in 5 settlements, they are close to (25 turns away)
                    # from a JUBILATION victory.
                    if VictoryType.JUBILATION not in p.imminent_victories:
                        close_to_vics.append(Victory(p, VictoryType.JUBILATION))
                        p.imminent_victories.add(VictoryType.JUBILATION)
                else:
                    p.jubilation_ctr = 0
                # If the player has maintained 5 settlements at 100% satisfaction for 25 turns, they have achieved a
                # JUBILATION victory.
                if p.jubilation_ctr == 25:
                    return Victory(p, VictoryType.JUBILATION)
                # If the player has at least 10 settlements of level 10, they have achieved a GLUTTONY victory.
                if lvl_ten_setls >= 10:
                    return Victory(p, VictoryType.GLUTTONY)
                # If a player has 8 level 10 settlements, they are close to a GLUTTONY victory.
                if lvl_ten_setls >= 8 and VictoryType.GLUTTONY not in p.imminent_victories:
                    close_to_vics.append(Victory(p, VictoryType.GLUTTONY))
                    p.imminent_victories.add(VictoryType.GLUTTONY)
                # If the player has constructed the Holy Sanctum, they have achieved a VIGOUR victory.
                if constructed_sanctum:
                    return Victory(p, VictoryType.VIGOUR)
            elif any(unit.plan.can_settle for unit in self.players[0].units):
                players_with_setls += 1
            elif not p.eliminated:
                p.eliminated = True
                self.board.overlay.toggle_elimination(p)
            # If the player has accumulated at least 100k wealth over the game, they have achieved an AFFLUENCE victory.
            if p.accumulated_wealth >= 100000:
                return Victory(p, VictoryType.AFFLUENCE)
            # If a player has accumulated at least 75k wealth over the game, they are close to an AFFLUENCE victory.
            if p.accumulated_wealth >= 75000 and VictoryType.AFFLUENCE not in p.imminent_victories:
                close_to_vics.append(Victory(p, VictoryType.AFFLUENCE))
                p.imminent_victories.add(VictoryType.AFFLUENCE)
            # If the player has undergone the blessings for all three pieces of ardour, they have achieved a
            # SERENDIPITY victory.
            ardour_pieces = len([bls for bls in p.blessings if "Piece of" in bls.name])
            if ardour_pieces == 3:
                return Victory(p, VictoryType.SERENDIPITY)
            # If a player has undergone two of the required three blessings for the pieces of ardour, they are close to
            # a SERENDIPITY victory.
            if ardour_pieces == 2 and VictoryType.SERENDIPITY not in p.imminent_victories:
                close_to_vics.append(Victory(p, VictoryType.SERENDIPITY))
                p.imminent_victories.add(VictoryType.SERENDIPITY)

        if players_with_setls == 1:
            # If there is only one player with settlements, they have achieved an ELIMINATION victory.
            return Victory(next(player for player in self.players if len(player.settlements) > 0),
                           VictoryType.ELIMINATION)

        # If any players are newly-close to a victory, show that in the overlay.
        if len(close_to_vics) > 0:
            self.board.overlay.toggle_close_to_vic(close_to_vics)

        return None

    def process_heathens(self):
        """
        Process the turns for each of the heathens.
        """
        all_units = []
        for player in self.players:
            # Heathens will not attack Infidel units.
            if player.faction is not Faction.INFIDELS:
                for unit in player.units:
                    all_units.append(unit)
        for heathen in self.heathens:
            within_range: typing.Optional[Unit] = None
            # Check if any player unit is within range of the heathen.
            for unit in all_units:
                if max(abs(unit.location[0] - heathen.location[0]),
                       abs(unit.location[1] - heathen.location[1])) <= heathen.remaining_stamina and \
                        heathen.health >= unit.health / 2:
                    within_range = unit
                    break
            # If there is a unit within range, move next to it and attack it.
            if within_range is not None:
                if within_range.location[0] - heathen.location[0] < 0:
                    heathen.location = within_range.location[0] + 1, within_range.location[1]
                else:
                    heathen.location = within_range.location[0] - 1, within_range.location[1]
                heathen.remaining_stamina = 0
                data = attack(heathen, within_range)
                if within_range.health <= 0:
                    for player in self.players:
                        if within_range in player.units:
                            player.units.remove(within_range)
                            break
                    if self.board.selected_unit is within_range:
                        self.board.selected_unit = None
                        self.board.overlay.toggle_unit(None)
                if heathen.health <= 0:
                    self.heathens.remove(heathen)
                # Only show the attack overlay if the unit attacked was the non-AI player's.
                if within_range in self.players[0].units:
                    self.board.overlay.toggle_attack(data)
            else:
                # If there are no units within range, just move randomly.
                x_movement = random.randint(-heathen.remaining_stamina, heathen.remaining_stamina)
                rem_movement = heathen.remaining_stamina - abs(x_movement)
                y_movement = random.choice([-rem_movement, rem_movement])
                heathen.location = (clamp(heathen.location[0] + x_movement, 0, 99),
                                    clamp(heathen.location[1] + y_movement, 0, 89))
                heathen.remaining_stamina -= abs(x_movement) + abs(y_movement)

            # Players of the Infidels faction share vision with Heathen units.
            if self.players[0].faction is Faction.INFIDELS:
                for i in range(heathen.location[1] - 5, heathen.location[1] + 6):
                    for j in range(heathen.location[0] - 5, heathen.location[0] + 6):
                        self.players[0].quads_seen.add((j, i))

    def initialise_ais(self):
        """
        Initialise the AI players by adding their first settlement in a random location.
        """
        for player in self.players:
            if player.ai_playstyle is not None:
                setl_coords = random.randint(0, 99), random.randint(0, 89)
                quad_biome = self.board.quads[setl_coords[1]][setl_coords[0]].biome
                setl_name = self.namer.get_settlement_name(quad_biome)
                new_settl = Settlement(setl_name, setl_coords, [],
                                       [self.board.quads[setl_coords[1]][setl_coords[0]]],
                                       [get_default_unit(setl_coords)])
                match player.faction:
                    case Faction.CONCENTRATED:
                        new_settl.strength *= 2
                    case Faction.FRONTIERSMEN:
                        new_settl.satisfaction = 75
                    case Faction.IMPERIALS:
                        new_settl.strength /= 2
                        new_settl.max_strength /= 2
                player.settlements.append(new_settl)

    def process_ais(self):
        """
        Process the moves for each AI player.
        """
        for player in self.players:
            if player.ai_playstyle is not None:
                self.move_maker.make_move(player, self.players, self.board.quads, self.board.game_config,
                                          self.nighttime_left > 0)

    def save_game(self, auto: bool = False):
        """
        Saves the current game with the current timestamp as the file name.
        """
        # Only maintain 3 autosaves at a time, delete the oldest if we already have 3 before saving the next.
        if auto and len(
                autosaves := list(filter(lambda fn: fn.startswith(AUTOSAVE_PREFIX), os.listdir(SAVES_DIR)))) == 3:
            autosaves.sort()
            os.remove(os.path.join(SAVES_DIR, autosaves[0]))
        # The ':' characters in the datestring must be replaced to conform with Windows files supported characters.
        sanitised_timestamp = datetime.datetime.now().isoformat(timespec='seconds').replace(':', '.')
        save_name = os.path.join(SAVES_DIR, f"{AUTOSAVE_PREFIX if auto else ''}save-{sanitised_timestamp}.json")
        with open(save_name, "w", encoding="utf-8") as save_file:
            # We use chain.from_iterable() here because the quads array is 2D.
            save = {
                "quads": list(chain.from_iterable(self.board.quads)),
                "players": self.players,
                "heathens": self.heathens,
                "turn": self.turn,
                "cfg": self.board.game_config,
                "night_status": {"until": self.until_night, "remaining": self.nighttime_left}
            }
            # Note that we use the SaveEncoder here for custom encoding for some classes.
            save_file.write(json.dumps(save, cls=SaveEncoder))
        save_file.close()

    def load_game(self, save_idx: int):
        """
        Loads the game with the given index from the saves/ directory.
        :param save_idx: The index of the save file to load. Determined from the list of saves chosen from on the menu.
        """
        # Reset the namer so that we have our original set of names again.
        self.namer.reset()
        # Sort and reverse both the autosaves and manual saves, remembering that the (up to) 3 autosaves will be
        # displayed first in the list.
        autosaves = list(filter(lambda file_name: file_name.startswith(AUTOSAVE_PREFIX), os.listdir(SAVES_DIR)))
        saves = list(
            filter(lambda file_name: not file_name == "README.md" and not file_name.startswith(AUTOSAVE_PREFIX),
                   os.listdir(SAVES_DIR)))
        autosaves.sort()
        autosaves.reverse()
        saves.sort()
        saves.reverse()
        all_saves = autosaves + saves
        with open(os.path.join(SAVES_DIR, all_saves[save_idx]), "r", encoding="utf-8") as save_file:
            # Use a custom object hook when loading the JSON so that the resulting objects have attribute access.
            save = json.loads(save_file.read(), object_hook=ObjectConverter)
            # Load in the quads.
            quads = [[None] * 100 for _ in range(90)]
            for i in range(90):
                for j in range(100):
                    quads[i][j] = save.quads[i * 100 + j]
                    # The biomes require special loading.
                    quads[i][j].biome = Biome[quads[i][j].biome]
            self.players = save.players
            # The list of tuples that is quads_seen needs special loading, as do a few other of the same type, because
            # tuples do not exist in JSON, so they are represented as arrays, which will clearly not work.
            for i in range(len(self.players[0].quads_seen)):
                self.players[0].quads_seen[i] = (self.players[0].quads_seen[i][0], self.players[0].quads_seen[i][1])
            self.players[0].quads_seen = set(self.players[0].quads_seen)
            for p in self.players:
                for idx, u in enumerate(p.units):
                    # We can do a direct conversion to Unit and UnitPlan objects for units.
                    plan_prereq = None if u.plan.prereq is None else get_blessing(u.plan.prereq.name)
                    p.units[idx] = Unit(u.health, u.remaining_stamina, (u.location[0], u.location[1]), u.garrisoned,
                                        UnitPlan(u.plan.power, u.plan.max_health, u.plan.total_stamina,
                                                 u.plan.name, plan_prereq, u.plan.cost, u.plan.can_settle),
                                        u.has_attacked, u.sieging)
                for s in p.settlements:
                    # Make sure we remove the settlement's name so that we don't get duplicates.
                    self.namer.remove_settlement_name(s.name, s.quads[0].biome)
                    # Another tuple-array fix.
                    s.location = (s.location[0], s.location[1])
                    if s.current_work is not None:
                        # Get the actual Improvement, Project, or UnitPlan objects for the current work. We use
                        # hasattr() because improvements have an effect where projects do not, and projects have a type
                        # where unit plans do not.
                        if hasattr(s.current_work.construction, "effect"):
                            s.current_work.construction = get_improvement(s.current_work.construction.name)
                        elif hasattr(s.current_work.construction, "type"):
                            s.current_work.construction = get_project(s.current_work.construction.name)
                        else:
                            s.current_work.construction = get_unit_plan(s.current_work.construction.name)
                    for idx, imp in enumerate(s.improvements):
                        # Do another direct conversion for improvements.
                        s.improvements[idx] = get_improvement(imp.name)
                    # Also convert all units in garrisons to Unit objects.
                    for idx, u in enumerate(s.garrison):
                        s.garrison[idx] = Unit(u.health, u.remaining_stamina, (u.location[0], u.location[1]),
                                               u.garrisoned, u.plan, u.has_attacked, u.sieging)
                    # Lastly ensure that if the settlement was under siege at the time of the save, we convert the
                    # sieging unit into proper objects too. This is necessary so that the siege is not improperly ended
                    # because the game thinks the sieging unit has died.
                    if s.under_siege_by is not None:
                        s_plan = s.under_siege_by.plan
                        plan_prereq = None if s_plan.prereq is None else get_blessing(s_plan.prereq.name)
                        s.under_siege_by = Unit(s.under_siege_by.health, s.under_siege_by.remaining_stamina,
                                                (s.under_siege_by.location[0], s.under_siege_by.location[1]),
                                                s.under_siege_by.garrisoned,
                                                UnitPlan(s_plan.power, s_plan.max_health, s_plan.total_stamina,
                                                         s_plan.name, plan_prereq, s_plan.cost, s_plan.can_settle),
                                                s.under_siege_by.has_attacked, s.under_siege_by.sieging)
                # We also do direct conversions to Blessing objects for the ongoing one, if there is one, as well as any
                # previously-completed ones.
                if p.ongoing_blessing:
                    p.ongoing_blessing.blessing = get_blessing(p.ongoing_blessing.blessing.name)
                for idx, bls in enumerate(p.blessings):
                    p.blessings[idx] = get_blessing(bls.name)
                if p.ai_playstyle is not None:
                    p.ai_playstyle = AIPlaystyle(AttackPlaystyle[p.ai_playstyle.attacking],
                                                 ExpansionPlaystyle[p.ai_playstyle.expansion])
                p.imminent_victories = set(p.imminent_victories)
                p.faction = Faction(p.faction)
            # For the AI players, we can just make quads_seen an empty set, as it's not used.
            for i in range(1, len(self.players)):
                self.players[i].quads_seen = set()

            self.heathens = []
            for h in save.heathens:
                # Do another direct conversion for the heathens.
                self.heathens.append(Heathen(h.health, h.remaining_stamina, (h.location[0], h.location[1]),
                                             UnitPlan(h.plan.power, h.plan.max_health, 2, h.plan.name, None, 0),
                                             h.has_attacked))

            self.turn = save.turn
            self.until_night = save.night_status.until
            self.nighttime_left = save.night_status.remaining
            game_cfg = save.cfg
        save_file.close()
        # Now do all the same logic we do when starting a game.
        pyxel.mouse(visible=True)
        self.game_started = True
        self.on_menu = False
        self.board = Board(game_cfg, self.namer, quads)
        self.move_maker.board_ref = self.board
        # Initialise the map position to the player's first settlement.
        self.map_pos = (clamp(self.players[0].settlements[0].location[0] - 12, -1, 77),
                        clamp(self.players[0].settlements[0].location[1] - 11, -1, 69))
        self.board.overlay.current_player = self.players[0]
        self.music_player.stop_menu_music()
        self.music_player.play_game_music()

    def get_saves(self):
        """
        Get the prettified file names of each save file in the saves/ directory and pass them to the menu.
        """
        self.menu.saves = []
        autosaves = list(filter(lambda file_name: file_name.startswith(AUTOSAVE_PREFIX), os.listdir(SAVES_DIR)))
        saves = list(
            filter(lambda file_name: not file_name == "README.md" and not file_name.startswith(AUTOSAVE_PREFIX),
                   os.listdir(SAVES_DIR)))
        # Default to a fake option if there are no saves available.
        if len(autosaves) + len(saves) == 0:
            self.menu.save_idx = -1
        else:
            autosaves.sort()
            autosaves.reverse()
            saves.sort()
            saves.reverse()
            for f in autosaves:
                self.menu.saves.append(f[9:-5].replace("T", " ") + " (auto)")
            for f in saves:
                # Just show the date and time.
                self.menu.saves.append(f[5:-5].replace("T", " "))
