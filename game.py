import random
import random
import time
import typing

import pyxel

from board import Board
from calculator import clamp, attack, get_setl_totals, complete_construction, attack_setl
from catalogue import get_available_improvements, get_available_blessings, get_available_unit_plans, get_heathen, \
    get_default_unit, FACTION_COLOURS, PROJECTS
from game_controller import GameController
from game_state import GameState
from menu import MainMenuOption, SetupOption, WikiOption
from models import Player, Settlement, Construction, OngoingBlessing, CompletedConstruction, Unit, HarvestStatus, \
    EconomicStatus, Heathen, AttackPlaystyle, GameConfig, Victory, VictoryType, AIPlaystyle, \
    ExpansionPlaystyle, OverlayType, Faction, ConstructionMenu, Project
from movemaker import set_player_construction
from overlay import SettlementAttackType, PauseOption
from saving.game_save_manager import GameSaveManager


class Game:
    """
    The main class for the game. Contains the majority of business logic, and none of the drawing.
    """

    def __init__(self):
        """
        Initialises the game.
        """
        pyxel.init(200, 200, title="Microcosm", quit_key=pyxel.KEY_NONE)

        self.game_controller = GameController()
        self.game_state = GameState()

        pyxel.run(self.on_update, self.draw)

    def on_update(self):
        """
        On every update, calculate the elapsed time, manage music, and respond to key presses.
        """
        time_elapsed = time.time() - self.game_controller.last_time
        self.game_controller.last_time = time.time()

        if self.game_state.board is not None:
            self.game_state.board.update(time_elapsed)

        if self.game_state.on_menu:
            self.game_controller.music_player.restart_menu_if_necessary()
        elif not self.game_controller.music_player.is_playing():
            self.game_controller.music_player.next_song()

        all_units = []
        for player in self.game_state.players:
            for unit in player.units:
                all_units.append(unit)

# JJG FIXME Input handler
        if pyxel.btnp(pyxel.KEY_DOWN):
            if self.game_state.on_menu:
                self.game_controller.menu.navigate(down=True)
            elif self.game_state.game_started:
                if self.game_state.board.overlay.is_constructing():
                    self.game_state.board.overlay.navigate_constructions(down=True)
                elif self.game_state.board.overlay.is_blessing():
                    self.game_state.board.overlay.navigate_blessings(down=True)
                elif self.game_state.board.overlay.is_setl_click():
                    self.game_state.board.overlay.navigate_setl_click(down=True)
                elif self.game_state.board.overlay.is_controls():
                    self.game_state.board.overlay.show_additional_controls = True
                elif self.game_state.board.overlay.is_pause():
                    self.game_state.board.overlay.navigate_pause(down=True)
                elif self.game_state.board.overlay.is_standard():
                    self.game_state.board.overlay.navigate_standard(down=True)
                else:
                    self.game_state.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press down.
                    # Holding Ctrl will pan the map 5 spaces.
                    if pyxel.btn(pyxel.KEY_CTRL):
                        self.game_state.map_pos = self.game_state.map_pos[0], clamp(self.game_state.map_pos[1] + 5, -1, 69)
                    else:
                        self.game_state.map_pos = self.game_state.map_pos[0], clamp(self.game_state.map_pos[1] + 1, -1, 69)
        elif pyxel.btnp(pyxel.KEY_UP):
            if self.game_state.on_menu:
                self.game_controller.menu.navigate(up=True)
            elif self.game_state.game_started:
                if self.game_state.board.overlay.is_constructing():
                    self.game_state.board.overlay.navigate_constructions(down=False)
                elif self.game_state.board.overlay.is_blessing():
                    self.game_state.board.overlay.navigate_blessings(down=False)
                elif self.game_state.board.overlay.is_setl_click():
                    self.game_state.board.overlay.navigate_setl_click(up=True)
                elif self.game_state.board.overlay.is_controls():
                    self.game_state.board.overlay.show_additional_controls = False
                elif self.game_state.board.overlay.is_pause():
                    self.game_state.board.overlay.navigate_pause(down=False)
                elif self.game_state.board.overlay.is_standard():
                    self.game_state.board.overlay.navigate_standard(down=False)
                else:
                    self.game_state.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press up.
                    # Holding Ctrl will pan the map 5 spaces.
                    if pyxel.btn(pyxel.KEY_CTRL):
                        self.game_state.map_pos = self.game_state.map_pos[0], clamp(self.game_state.map_pos[1] - 5, -1, 69)
                    else:
                        self.game_state.map_pos = self.game_state.map_pos[0], clamp(self.game_state.map_pos[1] - 1, -1, 69)
        elif pyxel.btnp(pyxel.KEY_LEFT):
            if self.game_state.on_menu:
                self.game_controller.menu.navigate(left=True)
            if self.game_state.game_started and self.game_state.board.overlay.is_constructing():
                if self.game_state.board.overlay.current_construction_menu is ConstructionMenu.PROJECTS and \
                        len(self.game_state.board.overlay.available_constructions) > 0:
                    self.game_state.board.overlay.current_construction_menu = ConstructionMenu.IMPROVEMENTS
                    self.game_state.board.overlay.selected_construction = self.game_state.board.overlay.available_constructions[0]
                elif self.game_state.board.overlay.current_construction_menu is ConstructionMenu.UNITS:
                    self.game_state.board.overlay.current_construction_menu = ConstructionMenu.PROJECTS
                    self.game_state.board.overlay.selected_construction = self.game_state.board.overlay.available_projects[0]
            elif self.game_state.game_started:
                if self.game_state.board.overlay.is_setl_click():
                    self.game_state.board.overlay.navigate_setl_click(left=True)
                else:
                    self.game_state.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press left.
                    # Holding Ctrl will pan the map 5 spaces.
                    if pyxel.btn(pyxel.KEY_CTRL):
                        self.game_state.map_pos = clamp(self.game_state.map_pos[0] - 5, -1, 77), self.game_state.map_pos[1]
                    else:
                        self.game_state.map_pos = clamp(self.game_state.map_pos[0] - 1, -1, 77), self.game_state.map_pos[1]
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            if self.game_state.on_menu:
                self.game_controller.menu.navigate(right=True)
            if self.game_state.game_started and self.game_state.board.overlay.is_constructing():
                if self.game_state.board.overlay.current_construction_menu is ConstructionMenu.IMPROVEMENTS:
                    self.game_state.board.overlay.current_construction_menu = ConstructionMenu.PROJECTS
                    self.game_state.board.overlay.selected_construction = self.game_state.board.overlay.available_projects[0]
                elif self.game_state.board.overlay.current_construction_menu is ConstructionMenu.PROJECTS:
                    self.game_state.board.overlay.current_construction_menu = ConstructionMenu.UNITS
                    self.game_state.board.overlay.selected_construction = self.game_state.board.overlay.available_unit_plans[0]
                    self.game_state.board.overlay.unit_plan_boundaries = 0, 5
            elif self.game_state.game_started:
                if self.game_state.board.overlay.is_setl_click():
                    self.game_state.board.overlay.navigate_setl_click(right=True)
                else:
                    self.game_state.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press right.
                    # Holding Ctrl will pan the map 5 spaces.
                    if pyxel.btn(pyxel.KEY_CTRL):
                        self.game_state.map_pos = clamp(self.game_state.map_pos[0] + 5, -1, 77), self.game_state.map_pos[1]
                    else:
                        self.game_state.map_pos = clamp(self.game_state.map_pos[0] + 1, -1, 77), self.game_state.map_pos[1]
        elif pyxel.btnp(pyxel.KEY_RETURN):
            if self.game_state.on_menu:
                if self.game_controller.menu.in_game_setup and self.game_controller.menu.setup_option is SetupOption.START_GAME:
                    # If the player has pressed enter to start the game, generate the players, board, and AI players.
                    pyxel.mouse(visible=True)
                    self.game_state.game_started = True
                    self.game_state.turn = 1
                    # Reinitialise night variables.
                    random.seed()
                    self.game_state.until_night: int = random.randint(10, 20)
                    self.game_state.nighttime_left = 0
                    self.game_state.on_menu = False
                    cfg: GameConfig = self.game_controller.menu.get_game_config()
                    self.gen_players(cfg)
                    self.game_state.board = Board(cfg, self.game_controller.namer)
                    self.game_controller.move_maker.board_ref = self.game_state.board
                    self.game_state.board.overlay.toggle_tutorial()
                    self.game_controller.namer.reset()
                    self.initialise_ais()
                    self.game_controller.music_player.stop_menu_music()
                    self.game_controller.music_player.play_game_music()
                elif self.game_controller.menu.loading_game:
                    if self.game_controller.menu.save_idx == -1:
                        self.game_controller.menu.loading_game = False
                    else:
                        GameSaveManager.load_game(self.game_state, self.game_controller)
                elif self.game_controller.menu.in_wiki:
                    if self.game_controller.menu.wiki_option is WikiOption.BACK:
                        self.game_controller.menu.in_wiki = False
                    else:
                        self.game_controller.menu.wiki_showing = self.game_controller.menu.wiki_option
                else:
                    match self.game_controller.menu.main_menu_option:
                        case MainMenuOption.NEW_GAME:
                            self.game_controller.menu.in_game_setup = True
                        case MainMenuOption.LOAD_GAME:
                            self.game_controller.menu.loading_game = True
                            GameSaveManager.get_saves(self.game_controller)
                        case MainMenuOption.WIKI:
                            self.game_controller.menu.in_wiki = True
                        case MainMenuOption.EXIT:
                            pyxel.quit()
            elif self.game_state.game_started and (self.game_state.board.overlay.is_victory() or
                                        self.game_state.board.overlay.is_elimination() and self.game_state.players[0].eliminated):
                # If the player has won the game, or they've just been eliminated themselves, enter will take them back
                # to the menu.
                self.game_state.game_started = False
                self.game_state.on_menu = True
                self.game_controller.menu.loading_game = False
                self.game_controller.menu.in_game_setup = False
                self.game_controller.menu.main_menu_option = MainMenuOption.NEW_GAME
                self.game_controller.music_player.stop_game_music()
                self.game_controller.music_player.play_menu_music()
            # If the player is choosing a blessing or construction, enter will select it.
            elif self.game_state.game_started and self.game_state.board.overlay.is_constructing():
                if self.game_state.board.overlay.selected_construction is not None:
                    self.game_state.board.selected_settlement.current_work = Construction(self.game_state.board.overlay.selected_construction)
                self.game_state.board.overlay.toggle_construction([], [], [])
            elif self.game_state.game_started and self.game_state.board.overlay.is_blessing():
                if self.game_state.board.overlay.selected_blessing is not None:
                    self.game_state.players[0].ongoing_blessing = OngoingBlessing(self.game_state.board.overlay.selected_blessing)
                self.game_state.board.overlay.toggle_blessing([])
            elif self.game_state.game_started and self.game_state.board.overlay.is_setl_click():
                match self.game_state.board.overlay.setl_attack_opt:
                    # If the player has chosen to attack a settlement, execute the attack.
                    case SettlementAttackType.ATTACK:
                        self.game_state.board.overlay.toggle_setl_click(None, None)
                        data = attack_setl(self.game_state.board.selected_unit, self.game_state.board.overlay.attacked_settlement,
                                           self.game_state.board.overlay.attacked_settlement_owner, False)
                        if data.attacker_was_killed:
                            # If the player's unit died, destroy and deselect it.
                            self.game_state.players[0].units.remove(self.game_state.board.selected_unit)
                            self.game_state.board.selected_unit = None
                            self.game_state.board.overlay.toggle_unit(None)
                        elif data.setl_was_taken:
                            # If the settlement was taken, transfer it to the player, while also marking any units that
                            # were involved in the siege as no longer besieging.
                            data.settlement.besieged = False
                            for unit in self.game_state.players[0].units:
                                if abs(unit.location[0] - data.settlement.location[0]) <= 1 and \
                                        abs(unit.location[1] - data.settlement.location[1]) <= 1:
                                    unit.besieging = False
                            # The Concentrated can only have a single settlement, so when they take others, the
                            # settlements simply disappear.
                            if self.game_state.players[0].faction is not Faction.CONCENTRATED:
                                self.game_state.players[0].settlements.append(data.settlement)
                            for idx, p in enumerate(self.game_state.players):
                                if data.settlement in p.settlements and idx != 0:
                                    p.settlements.remove(data.settlement)
                                    break
                        self.game_state.board.overlay.toggle_setl_attack(data)
                        self.game_state.board.attack_time_bank = 0
                    case SettlementAttackType.BESIEGE:
                        # Alternatively, begin a siege on the settlement.
                        self.game_state.board.selected_unit.besieging = True
                        self.game_state.board.overlay.attacked_settlement.besieged = True
                        self.game_state.board.overlay.toggle_setl_click(None, None)
                    case _:
                        self.game_state.board.overlay.toggle_setl_click(None, None)
            elif self.game_state.game_started and self.game_state.board.overlay.is_pause():
                match self.game_state.board.overlay.pause_option:
                    case PauseOption.RESUME:
                        self.game_state.board.overlay.toggle_pause()
                    case PauseOption.SAVE:
                        GameSaveManager.save_game(self.game_state)
                        self.game_state.board.overlay.has_saved = True
                    case PauseOption.CONTROLS:
                        self.game_state.board.overlay.show_additional_controls = False
                        self.game_state.board.overlay.toggle_controls()
                    case PauseOption.QUIT:
                        self.game_state.game_started = False
                        self.game_state.on_menu = True
                        self.game_controller.menu.loading_game = False
                        self.game_controller.menu.in_game_setup = False
                        self.game_controller.menu.main_menu_option = MainMenuOption.NEW_GAME
                        self.game_controller.music_player.stop_game_music()
                        self.game_controller.music_player.play_menu_music()
            elif self.game_state.game_started and not (self.game_state.board.overlay.is_tutorial() or self.game_state.board.overlay.is_deployment() or
                                            self.game_state.board.overlay.is_bless_notif() or
                                            self.game_state.board.overlay.is_constr_notif() or self.game_state.board.overlay.is_lvl_notif() or
                                            self.game_state.board.overlay.is_close_to_vic() or
                                            self.game_state.board.overlay.is_investigation() or self.game_state.board.overlay.is_night()):
                # If we are not in any of the above situations, end the turn.
                if self.end_turn():
                    self.game_state.board.overlay.update_turn(self.game_state.turn)
                    self.process_heathens()
                    self.process_ais()
        # Mouse clicks are forwarded to the Board for processing.
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            if self.game_state.game_started:
                self.game_state.board.overlay.remove_warning_if_possible()
                self.game_state.board.process_right_click(pyxel.mouse_x, pyxel.mouse_y, self.game_state.map_pos)
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.game_state.game_started:
                other_setls = []
                for i in range(1, len(self.game_state.players)):
                    other_setls.extend(self.game_state.players[i].settlements)
                self.game_state.board.overlay.remove_warning_if_possible()
                self.game_state.board.process_left_click(pyxel.mouse_x, pyxel.mouse_y,
                                              len(self.game_state.players[0].settlements) > 0,
                                              self.game_state.players[0], self.game_state.map_pos, self.game_state.heathens, all_units,
                                              self.game_state.players, other_setls)
        elif pyxel.btnp(pyxel.KEY_SHIFT):
            if self.game_state.game_started:
                self.game_state.board.overlay.remove_warning_if_possible()
                # Display the standard overlay.
                self.game_state.board.overlay.toggle_standard(self.game_state.turn)
        elif pyxel.btnp(pyxel.KEY_C):
            if self.game_state.game_started and self.game_state.board.selected_settlement is not None:
                # Pick a construction.
                self.game_state.board.overlay.toggle_construction(get_available_improvements(self.game_state.players[0],
                                                                                  self.game_state.board.selected_settlement),
                                                       PROJECTS,
                                                       get_available_unit_plans(self.game_state.players[0],
                                                                                self.game_state.board.selected_settlement.level))
        elif pyxel.btnp(pyxel.KEY_F):
            if self.game_state.on_menu and self.game_controller.menu.in_game_setup and self.game_controller.menu.setup_option is SetupOption.PLAYER_FACTION:
                self.game_controller.menu.showing_faction_details = not self.game_controller.menu.showing_faction_details
            elif self.game_state.game_started and self.game_state.board.overlay.is_standard():
                # Pick a blessing.
                self.game_state.board.overlay.toggle_blessing(get_available_blessings(self.game_state.players[0]))
        elif pyxel.btnp(pyxel.KEY_D):
            if self.game_state.game_started and self.game_state.board.selected_settlement is not None and \
                    len(self.game_state.board.selected_settlement.garrison) > 0:
                self.game_state.board.deploying_army = True
                self.game_state.board.overlay.toggle_deployment()
            elif self.game_state.game_started and self.game_state.board.selected_unit is not None and \
                    self.game_state.board.selected_unit in self.game_state.players[0].units:
                # If a unit is selected rather than a settlement, pressing D disbands the army, destroying the unit and
                # adding to the player's wealth.
                self.game_state.players[0].wealth += self.game_state.board.selected_unit.plan.cost
                self.game_state.players[0].units.remove(self.game_state.board.selected_unit)
                self.game_state.board.selected_unit = None
                self.game_state.board.overlay.toggle_unit(None)
        elif pyxel.btnp(pyxel.KEY_TAB):
            # Pressing tab iterates through the player's settlements, centreing on each one.
            if self.game_state.game_started and self.game_state.board.overlay.can_iter_settlements_units() and \
                    len(self.game_state.players[0].settlements) > 0:
                self.game_state.board.overlay.remove_warning_if_possible()
                if self.game_state.board.overlay.is_unit():
                    self.game_state.board.selected_unit = None
                    self.game_state.board.overlay.toggle_unit(None)
                if self.game_state.board.selected_settlement is None:
                    self.game_state.board.selected_settlement = self.game_state.players[0].settlements[0]
                    self.game_state.board.overlay.toggle_settlement(self.game_state.players[0].settlements[0], self.game_state.players[0])
                elif len(self.game_state.players[0].settlements) > 1:
                    current_idx = self.game_state.players[0].settlements.index(self.game_state.board.selected_settlement)
                    new_idx = 0
                    if current_idx != len(self.game_state.players[0].settlements) - 1:
                        new_idx = current_idx + 1
                    self.game_state.board.selected_settlement = self.game_state.players[0].settlements[new_idx]
                    self.game_state.board.overlay.update_settlement(self.game_state.players[0].settlements[new_idx])
                self.game_state.map_pos = (clamp(self.game_state.board.selected_settlement.location[0] - 12, -1, 77),
                                clamp(self.game_state.board.selected_settlement.location[1] - 11, -1, 69))
        elif pyxel.btnp(pyxel.KEY_SPACE):
            # Pressing space either dismisses the current overlay or iterates through the player's units.
            if self.game_state.on_menu and self.game_controller.menu.in_wiki and self.game_controller.menu.wiki_showing is not None:
                self.game_controller.menu.wiki_showing = None
            if self.game_state.on_menu and self.game_controller.menu.in_game_setup:
                self.game_controller.menu.in_game_setup = False
            if self.game_state.on_menu and self.game_controller.menu.loading_game and self.game_controller.menu.load_failed:
                self.game_controller.menu.load_failed = False
            elif self.game_state.on_menu and self.game_controller.menu.loading_game:
                self.game_controller.menu.loading_game = False
            if self.game_state.game_started and self.game_state.board.overlay.is_elimination():
                self.game_state.board.overlay.toggle_elimination(None)
            elif self.game_state.game_started and self.game_state.board.overlay.is_night():
                self.game_state.board.overlay.toggle_night(None)
            elif self.game_state.game_started and self.game_state.board.overlay.is_close_to_vic():
                self.game_state.board.overlay.toggle_close_to_vic([])
            elif self.game_state.game_started and self.game_state.board.overlay.is_bless_notif():
                self.game_state.board.overlay.toggle_blessing_notification(None)
            elif self.game_state.game_started and self.game_state.board.overlay.is_constr_notif():
                self.game_state.board.overlay.toggle_construction_notification(None)
            elif self.game_state.game_started and self.game_state.board.overlay.is_lvl_notif():
                self.game_state.board.overlay.toggle_level_up_notification(None)
            elif self.game_state.game_started and self.game_state.board.overlay.is_controls():
                self.game_state.board.overlay.toggle_controls()
            elif self.game_state.game_started and self.game_state.board.overlay.is_investigation():
                self.game_state.board.overlay.toggle_investigation(None)
            elif self.game_state.game_started and self.game_state.board.overlay.can_iter_settlements_units() and \
                    len(self.game_state.players[0].units) > 0:
                self.game_state.board.overlay.remove_warning_if_possible()
                if self.game_state.board.overlay.is_setl():
                    self.game_state.board.selected_settlement = None
                    self.game_state.board.overlay.toggle_settlement(None, self.game_state.players[0])
                if self.game_state.board.selected_unit is None or isinstance(self.game_state.board.selected_unit, Heathen):
                    self.game_state.board.selected_unit = self.game_state.players[0].units[0]
                    self.game_state.board.overlay.toggle_unit(self.game_state.players[0].units[0])
                elif len(self.game_state.players[0].units) > 1:
                    current_idx = self.game_state.players[0].units.index(self.game_state.board.selected_unit)
                    new_idx = 0
                    if current_idx != len(self.game_state.players[0].units) - 1:
                        new_idx = current_idx + 1
                    self.game_state.board.selected_unit = self.game_state.players[0].units[new_idx]
                    self.game_state.board.overlay.update_unit(self.game_state.players[0].units[new_idx])
                self.game_state.map_pos = (clamp(self.game_state.board.selected_unit.location[0] - 12, -1, 77),
                                clamp(self.game_state.board.selected_unit.location[1] - 11, -1, 69))
        elif pyxel.btnp(pyxel.KEY_M):
            units = self.game_state.players[0].units
            filtered_units = [unit for unit in units if not unit.besieging and unit.remaining_stamina > 0]

            if self.game_state.game_started and self.game_state.board.overlay.can_iter_settlements_units() and \
                    len(filtered_units) > 0:
                self.game_state.board.overlay.remove_warning_if_possible()
                if self.game_state.board.overlay.is_setl():
                    self.game_state.board.selected_settlement = None
                    self.game_state.board.overlay.toggle_settlement(None, self.game_state.players[0])
                if self.game_state.board.selected_unit is None or isinstance(self.game_state.board.selected_unit, Heathen):
                    self.game_state.board.selected_unit = filtered_units[0]
                    self.game_state.board.overlay.toggle_unit(filtered_units[0])
                else:
                    current_selected_unit = self.game_state.board.selected_unit
                    new_idx = 0

                    if current_selected_unit in filtered_units and \
                            filtered_units.index(current_selected_unit) != len(filtered_units) - 1:
                        new_idx = filtered_units.index(current_selected_unit) + 1

                    self.game_state.board.selected_unit = filtered_units[new_idx]
                    self.game_state.board.overlay.update_unit(filtered_units[new_idx])

                self.game_state.map_pos = (clamp(self.game_state.board.selected_unit.location[0] - 12, -1, 77),
                                clamp(self.game_state.board.selected_unit.location[1] - 11, -1, 69))
        elif pyxel.btnp(pyxel.KEY_S):
            if self.game_state.game_started and self.game_state.board.selected_unit is not None and self.game_state.board.selected_unit.plan.can_settle:
                # Units that can settle can found new settlements when S is pressed.
                self.game_state.board.handle_new_settlement(self.game_state.players[0])
        elif pyxel.btnp(pyxel.KEY_N):
            if self.game_state.game_started:
                self.game_controller.music_player.next_song()
        elif pyxel.btnp(pyxel.KEY_B):
            if self.game_state.game_started and self.game_state.board.selected_settlement is not None and \
                    self.game_state.board.selected_settlement.current_work is not None and \
                    self.game_state.players[0].faction is not Faction.FUNDAMENTALISTS and \
                    not isinstance(self.game_state.board.selected_settlement.current_work.construction, Project):
                # Pressing B will buyout the remaining cost of the settlement's current construction. However, players
                # using the Fundamentalists faction are barred from this.
                current_work = self.game_state.board.selected_settlement.current_work
                remaining_work = current_work.construction.cost - current_work.zeal_consumed
                if self.game_state.players[0].wealth >= remaining_work:
                    self.game_state.board.overlay.toggle_construction_notification([
                        CompletedConstruction(self.game_state.board.selected_settlement.current_work.construction,
                                              self.game_state.board.selected_settlement)
                    ])
                    complete_construction(self.game_state.board.selected_settlement, self.game_state.players[0])
                    self.game_state.players[0].wealth -= remaining_work
        elif pyxel.btnp(pyxel.KEY_ESCAPE):
            if self.game_state.game_started and not self.game_state.board.overlay.is_victory() and not self.game_state.board.overlay.is_elimination():
                # Show the pause menu if there are no intrusive overlays being shown.
                if not self.game_state.board.overlay.showing or \
                        all(overlay in (OverlayType.ATTACK, OverlayType.SETL_ATTACK, OverlayType.SIEGE_NOTIF)
                            for overlay in self.game_state.board.overlay.showing):
                    self.game_state.board.overlay.toggle_pause()
                # Remove one overlay layer per ESCAPE press, assuming it is a layer that can be removed.
                elif not self.game_state.board.overlay.is_tutorial() and not self.game_state.board.overlay.is_deployment():
                    to_reset: typing.Optional[OverlayType] = self.game_state.board.overlay.remove_layer()
                    # Make sure we reset board selections if necessary.
                    if to_reset == OverlayType.UNIT:
                        self.game_state.board.selected_unit = None
                    elif to_reset == OverlayType.SETTLEMENT:
                        self.game_state.board.selected_settlement = None
        elif pyxel.btnp(pyxel.KEY_A):
            if self.game_state.game_started and self.game_state.board.overlay.is_setl() and \
                    self.game_state.board.selected_settlement.current_work is None:
                # Pressing the A key while a player settlement with no active construction is selected results in the
                # selection being made automatically (in much the same way that AI settlements have their constructions
                # selected).
                set_player_construction(self.game_state.players[0], self.game_state.board.selected_settlement, self.game_state.nighttime_left > 0)

    def draw(self):
        """
        Draws the game to the screen.
        """
        if self.game_state.on_menu:
            self.game_controller.menu.draw()
        elif self.game_state.game_started:
            self.game_state.board.draw(self.game_state.players, self.game_state.map_pos, self.game_state.turn, self.game_state.heathens, self.game_state.nighttime_left > 0,
                            self.game_state.until_night if self.game_state.until_night != 0 else self.game_state.nighttime_left)

    def gen_players(self, cfg: GameConfig):
        """
        Generates the players for the game based on the supplied config.
        :param cfg: The game config.
        """
        self.game_state.players = [Player("The Chosen One", cfg.player_faction, FACTION_COLOURS[cfg.player_faction],
                               0, [], [], [], set(), set())]
        factions = list(Faction)
        # Ensure that an AI player doesn't choose the same faction as the player.
        factions.remove(cfg.player_faction)
        for i in range(1, cfg.player_count):
            faction = random.choice(factions)
            factions.remove(faction)
            self.game_state.players.append(Player(f"NPC{i}", faction, FACTION_COLOURS[faction], 0, [], [], [], set(), set(),
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
        for setl in self.game_state.players[0].settlements:
            if setl.current_work is None:
                problematic_settlements.append(setl)
            total_wealth += sum(quad.wealth for quad in setl.quads)
            total_wealth += sum(imp.effect.wealth for imp in setl.improvements)
            total_wealth += (setl.level - 1) * 0.25 * total_wealth
            if setl.economic_status is EconomicStatus.RECESSION:
                total_wealth = 0
            elif setl.economic_status is EconomicStatus.BOOM:
                total_wealth *= 1.5
        for unit in self.game_state.players[0].units:
            if not unit.garrisoned:
                total_wealth -= unit.plan.cost / 10
        if self.game_state.players[0].faction is Faction.GODLESS:
            total_wealth *= 1.25
        elif self.game_state.players[0].faction is Faction.ORTHODOX:
            total_wealth *= 0.75
        has_no_blessing = self.game_state.players[0].ongoing_blessing is None
        will_have_negative_wealth = (self.game_state.players[0].wealth + total_wealth) < 0 and len(self.game_state.players[0].units) > 0
        if not self.game_state.board.overlay.is_warning() and \
                (len(problematic_settlements) > 0 or has_no_blessing or will_have_negative_wealth):
            self.game_state.board.overlay.toggle_warning(problematic_settlements, has_no_blessing, will_have_negative_wealth)
            return False

        for player in self.game_state.players:
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
                    get_setl_totals(player, setl, self.game_state.nighttime_left > 0)
                overall_fortune += total_fortune
                overall_wealth += total_wealth

                # If the settlement is under siege, decrease its strength based on the number of besieging units.
                if setl.besieged:
                    besieging_units: typing.List[Unit] = []
                    for p in self.game_state.players:
                        if p is not player:
                            for u in p.units:
                                if abs(u.location[0] - setl.location[0]) <= 1 and \
                                        abs(u.location[1] - setl.location[1]) <= 1:
                                    besieging_units.append(u)
                    if not besieging_units:
                        setl.besieged = False
                    else:
                        if all(u.health <= 0 for u in besieging_units):
                            setl.besieged = False
                        else:
                            setl.strength = max(0.0, setl.strength - 10 * len(besieging_units))
                else:
                    # Otherwise, increase the settlement's strength if it was recently under siege and is not at full
                    # strength.
                    if setl.strength < setl.max_strength:
                        setl.strength = min(setl.strength + setl.max_strength * 0.1, setl.max_strength)

                # Reset all units in the garrison in case any were garrisoned this turn.
                for g in setl.garrison:
                    g.has_acted = False
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
                self.game_state.board.overlay.toggle_construction_notification(completed_constructions)
            if player.ai_playstyle is None and len(levelled_up_settlements) > 0:
                self.game_state.board.overlay.toggle_level_up_notification(levelled_up_settlements)
            # Reset all units.
            for unit in player.units:
                unit.remaining_stamina = unit.plan.total_stamina
                # Heal the unit.
                if unit.health < unit.plan.max_health:
                    unit.health = min(unit.health + unit.plan.max_health * 0.1, unit.plan.max_health)
                unit.has_acted = False
                overall_wealth -= unit.plan.cost / 10
            # Process the current blessing, completing it if it was finished.
            if player.ongoing_blessing is not None:
                player.ongoing_blessing.fortune_consumed += overall_fortune
                if player.ongoing_blessing.fortune_consumed >= player.ongoing_blessing.blessing.cost:
                    player.blessings.append(player.ongoing_blessing.blessing)
                    # Show a notification if the player is non-AI.
                    if player.ai_playstyle is None:
                        self.game_state.board.overlay.toggle_blessing_notification(player.ongoing_blessing.blessing)
                    player.ongoing_blessing = None
            # If the player's wealth will go into the negative this turn, sell their units until it's above 0 again.
            while player.wealth + overall_wealth < 0:
                sold_unit = player.units.pop()
                if self.game_state.board.selected_unit is sold_unit:
                    self.game_state.board.selected_unit = None
                    self.game_state.board.overlay.toggle_unit(None)
                player.wealth += sold_unit.plan.cost
            # Update the player's wealth.
            player.wealth = max(player.wealth + overall_wealth, 0)
            player.accumulated_wealth += overall_wealth

        # Spawn a heathen every 5 turns.
        if self.game_state.turn % 5 == 0:
            heathen_loc = random.randint(0, 89), random.randint(0, 99)
            self.game_state.heathens.append(get_heathen(heathen_loc, self.game_state.turn))

        # Reset all heathens.
        for heathen in self.game_state.heathens:
            heathen.remaining_stamina = heathen.plan.total_stamina
            if heathen.health < heathen.plan.max_health:
                heathen.health = min(heathen.health + heathen.plan.max_health * 0.1, 100)

        self.game_state.board.overlay.remove_warning_if_possible()
        self.game_state.turn += 1

        # Make night-related calculations, but only if climatic effects are enabled.
        if self.game_state.board.game_config.climatic_effects:
            random.seed()
            if self.game_state.nighttime_left == 0:
                self.game_state.until_night -= 1
                if self.game_state.until_night == 0:
                    self.game_state.board.overlay.toggle_night(True)
                    # Nights last for between 5 and 20 turns.
                    self.game_state.nighttime_left = random.randint(5, 20)
                    for h in self.game_state.heathens:
                        h.plan.power = round(2 * h.plan.power)
                    if self.game_state.players[0].faction is Faction.NOCTURNE:
                        for u in self.game_state.players[0].units:
                            u.plan.power = round(2 * u.plan.power)
                        for setl in self.game_state.players[0].settlements:
                            for unit in setl.garrison:
                                unit.plan.power = round(2 * unit.plan.power)
            else:
                self.game_state.nighttime_left -= 1
                if self.game_state.nighttime_left == 0:
                    self.game_state.until_night = random.randint(10, 20)
                    self.game_state.board.overlay.toggle_night(False)
                    for h in self.game_state.heathens:
                        h.plan.power = round(h.plan.power / 2)
                    if self.game_state.players[0].faction is Faction.NOCTURNE:
                        for u in self.game_state.players[0].units:
                            u.plan.power = round(u.plan.power / 4)
                            u.health = round(u.health / 2)
                            u.plan.max_health = round(u.plan.max_health / 2)
                            u.plan.total_stamina = round(u.plan.total_stamina / 2)
                        for setl in self.game_state.players[0].settlements:
                            for unit in setl.garrison:
                                unit.plan.power = round(unit.plan.power / 4)
                                unit.health = round(unit.health / 2)
                                unit.plan.max_health = round(unit.plan.max_health / 2)
                                unit.plan.total_stamina = round(unit.plan.total_stamina / 2)

        # Autosave every 10 turns.
        if self.game_state.turn % 10 == 0:
            GameSaveManager.save_game(self.game_state, True)

        possible_victory = self.check_for_victory()
        if possible_victory is not None:
            self.game_state.board.overlay.toggle_victory(possible_victory)
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
        for pl in self.game_state.players:
            all_setls.extend(pl.settlements)

        players_with_setls = 0
        for p in self.game_state.players:
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
            elif any(unit.plan.can_settle for unit in self.game_state.players[0].units):
                players_with_setls += 1
            elif not p.eliminated:
                p.eliminated = True
                self.game_state.board.overlay.toggle_elimination(p)
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
            return Victory(next(player for player in self.game_state.players if len(player.settlements) > 0),
                           VictoryType.ELIMINATION)

        # If any players are newly-close to a victory, show that in the overlay.
        if len(close_to_vics) > 0:
            self.game_state.board.overlay.toggle_close_to_vic(close_to_vics)

        return None

    def process_heathens(self):
        """
        Process the turns for each of the heathens.
        """
        all_units = []
        for player in self.game_state.players:
            # Heathens will not attack Infidel units.
            if player.faction is not Faction.INFIDELS:
                for unit in player.units:
                    all_units.append(unit)
        for heathen in self.game_state.heathens:
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
                    for player in self.game_state.players:
                        if within_range in player.units:
                            player.units.remove(within_range)
                            break
                    if self.game_state.board.selected_unit is within_range:
                        self.game_state.board.selected_unit = None
                        self.game_state.board.overlay.toggle_unit(None)
                if heathen.health <= 0:
                    self.game_state.heathens.remove(heathen)
                # Only show the attack overlay if the unit attacked was the non-AI player's.
                if within_range in self.game_state.players[0].units:
                    self.game_state.board.overlay.toggle_attack(data)
            else:
                # If there are no units within range, just move randomly.
                x_movement = random.randint(-heathen.remaining_stamina, heathen.remaining_stamina)
                rem_movement = heathen.remaining_stamina - abs(x_movement)
                y_movement = random.choice([-rem_movement, rem_movement])
                heathen.location = (clamp(heathen.location[0] + x_movement, 0, 99),
                                    clamp(heathen.location[1] + y_movement, 0, 89))
                heathen.remaining_stamina -= abs(x_movement) + abs(y_movement)

            # Players of the Infidels faction share vision with Heathen units.
            if self.game_state.players[0].faction is Faction.INFIDELS:
                for i in range(heathen.location[1] - 5, heathen.location[1] + 6):
                    for j in range(heathen.location[0] - 5, heathen.location[0] + 6):
                        self.game_state.players[0].quads_seen.add((j, i))

    def initialise_ais(self):
        """
        Initialise the AI players by adding their first settlement in a random location.
        """
        for player in self.game_state.players:
            if player.ai_playstyle is not None:
                setl_coords = random.randint(0, 99), random.randint(0, 89)
                quad_biome = self.game_state.board.quads[setl_coords[1]][setl_coords[0]].biome
                setl_name = self.game_controller.namer.get_settlement_name(quad_biome)
                new_settl = Settlement(setl_name, setl_coords, [],
                                       [self.game_state.board.quads[setl_coords[1]][setl_coords[0]]],
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
        for player in self.game_state.players:
            if player.ai_playstyle is not None:
                self.game_controller.move_maker.make_move(player, self.game_state.players, self.game_state.board.quads, self.game_state.board.game_config,
                                          self.game_state.nighttime_left > 0)

