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
    get_default_unit, get_improvement, get_blessing, HEATHEN_UNIT_PLAN, get_unit_plan, Namer
from menu import Menu, MenuOption, SetupOption
from models import Player, Settlement, Construction, OngoingBlessing, CompletedConstruction, Unit, HarvestStatus, \
    EconomicStatus, Heathen, AIPlaystyle, GameConfig, Biome, Victory, VictoryType
from movemaker import MoveMaker
from music_player import MusicPlayer
from overlay import SettlementAttackType, PauseOption
from save_encoder import SaveEncoder, ObjectConverter


class Game:
    """
    The main class for the game. Contains the majority of business logic, and none of the drawing.
    """
    def __init__(self):
        """
        Initialises the game.
        """
        pyxel.init(200, 200, title="Microcosm")

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
                else:
                    self.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press down.
                    self.map_pos = self.map_pos[0], clamp(self.map_pos[1] + 1, -1, 69)
        elif pyxel.btnp(pyxel.KEY_UP):
            if self.on_menu:
                self.menu.navigate(up=True)
            elif self.game_started:
                if self.board.overlay.is_constructing():
                    self.board.overlay.navigate_constructions(down=False)
                elif self.board.overlay.is_standard():
                    self.board.overlay.navigate_blessings(down=False)
                elif self.board.overlay.is_setl_click():
                    self.board.overlay.navigate_setl_click(up=True)
                elif self.board.overlay.is_pause():
                    self.board.overlay.navigate_pause(down=False)
                else:
                    self.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press up.
                    self.map_pos = self.map_pos[0], clamp(self.map_pos[1] - 1, -1, 69)
        elif pyxel.btnp(pyxel.KEY_LEFT):
            if self.on_menu:
                self.menu.navigate(left=True)
            if self.game_started and self.board.overlay.is_constructing() and \
                    len(self.board.overlay.available_constructions) > 0:
                self.board.overlay.constructing_improvement = True
                self.board.overlay.selected_construction = self.board.overlay.available_constructions[0]
            elif self.game_started:
                if self.board.overlay.is_setl_click():
                    self.board.overlay.navigate_setl_click(left=True)
                else:
                    self.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press left.
                    self.map_pos = clamp(self.map_pos[0] - 1, -1, 77), self.map_pos[1]
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            if self.on_menu:
                self.menu.navigate(right=True)
            if self.game_started and self.board.overlay.is_constructing():
                self.board.overlay.constructing_improvement = False
                self.board.overlay.selected_construction = self.board.overlay.available_unit_plans[0]
                self.board.overlay.unit_plan_boundaries = 0, 5
            elif self.game_started:
                if self.board.overlay.is_setl_click():
                    self.board.overlay.navigate_setl_click(right=True)
                else:
                    self.board.overlay.remove_warning_if_possible()
                    # If we're not on a menu, pan the map when you press right.
                    self.map_pos = clamp(self.map_pos[0] + 1, -1, 77), self.map_pos[1]
        elif pyxel.btnp(pyxel.KEY_RETURN):
            if self.on_menu:
                if self.menu.in_game_setup and self.menu.setup_option is SetupOption.START_GAME:
                    # If the player has pressed enter to start the game, generate the players, board, and AI players.
                    pyxel.mouse(visible=True)
                    self.game_started = True
                    self.turn = 1
                    self.on_menu = False
                    cfg: GameConfig = self.menu.get_game_config()
                    self.gen_players(cfg)
                    self.board = Board(cfg, self.namer)
                    self.move_maker.board_ref = self.board
                    self.board.overlay.toggle_tutorial()
                    self.initialise_ais()
                    self.music_player.stop_menu_music()
                    self.music_player.play_game_music()
                elif self.menu.loading_game:
                    if self.menu.save_idx == -1:
                        self.menu.loading_game = False
                    else:
                        self.load_game(self.menu.save_idx)
                elif self.menu.in_wiki:
                    if self.menu.wiki_option is None:
                        self.menu.in_wiki = False
                    else:
                        self.menu.wiki_showing = self.menu.wiki_option
                else:
                    if self.menu.menu_option is MenuOption.NEW_GAME:
                        self.menu.in_game_setup = True
                    elif self.menu.menu_option is MenuOption.LOAD_GAME:
                        self.menu.loading_game = True
                        self.get_saves()
                    elif self.menu.menu_option is MenuOption.WIKI:
                        self.menu.in_wiki = True
                    elif self.menu.menu_option is MenuOption.EXIT:
                        pyxel.quit()
            elif self.game_started and self.board.overlay.is_victory():
                # If the player has won the game, enter will take them back to the menu.
                self.game_started = False
                self.on_menu = True
                self.menu.loading_game = False
                self.menu.in_game_setup = False
                self.menu.menu_option = MenuOption.NEW_GAME
                self.music_player.stop_game_music()
                self.music_player.play_menu_music()
            # If the player is choosing a blessing or construction, enter will select it.
            elif self.game_started and self.board.overlay.is_constructing():
                if self.board.overlay.selected_construction is not None:
                    self.board.selected_settlement.current_work = Construction(self.board.overlay.selected_construction)
                self.board.overlay.toggle_construction([], [])
            elif self.game_started and self.board.overlay.is_blessing():
                if self.board.overlay.selected_blessing is not None:
                    self.players[0].ongoing_blessing = OngoingBlessing(self.board.overlay.selected_blessing)
                self.board.overlay.toggle_blessing([])
            elif self.game_started and self.board.overlay.is_setl_click():
                # If the player has chosen to attack a settlement, execute the attack.
                if self.board.overlay.setl_attack_opt is SettlementAttackType.ATTACK:
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
                        self.players[0].settlements.append(data.settlement)
                        for idx, p in enumerate(self.players):
                            if data.settlement in p.settlements and idx != 0:
                                p.settlements.remove(data.settlement)
                                break
                    self.board.overlay.toggle_setl_attack(data)
                    self.board.attack_time_bank = 0
                    self.board.overlay.toggle_setl_click(None, None)
                elif self.board.overlay.setl_attack_opt is SettlementAttackType.BESIEGE:
                    # Alternatively, begin a siege on the settlement.
                    self.board.selected_unit.sieging = True
                    self.board.overlay.attacked_settlement.under_siege_by = self.board.selected_unit
                    self.board.overlay.toggle_setl_click(None, None)
                else:
                    self.board.overlay.toggle_setl_click(None, None)
            elif self.game_started and self.board.overlay.is_pause():
                if self.board.overlay.pause_option is PauseOption.RESUME:
                    self.board.overlay.toggle_pause()
                elif self.board.overlay.pause_option is PauseOption.SAVE:
                    self.save_game()
                elif self.board.overlay.pause_option is PauseOption.CONTROLS:
                    self.board.overlay.toggle_controls()
                elif self.board.overlay.pause_option is PauseOption.QUIT:
                    self.game_started = False
                    self.on_menu = True
                    self.menu.loading_game = False
                    self.menu.in_game_setup = False
                    self.menu.menu_option = MenuOption.NEW_GAME
                    self.music_player.stop_game_music()
                    self.music_player.play_menu_music()
            elif self.game_started and not self.board.overlay.is_tutorial():
                # If we are not in any of the above situations, end the turn.
                self.board.overlay.update_turn(self.turn)
                if self.end_turn():
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
                                                       get_available_unit_plans(self.players[0],
                                                                                self.board.selected_settlement.level))
        elif pyxel.btnp(pyxel.KEY_F):
            if self.game_started and self.board.overlay.is_standard():
                # Pick a blessing.
                self.board.overlay.toggle_blessing(get_available_blessings(self.players[0]))
        elif pyxel.btnp(pyxel.KEY_D):
            if self.game_started and self.board.selected_settlement is not None and \
                    len(self.board.selected_settlement.garrison) > 0:
                self.board.deploying_army = True
                self.board.overlay.toggle_deployment()
            elif self.game_started and self.board.selected_unit is not None:
                # If a unit is selected rather than a settlement, pressing D disbands the army, destroying the unit and
                # adding to the player's wealth.
                self.players[0].wealth += self.board.selected_unit.plan.cost
                self.players[0].units.remove(self.board.selected_unit)
                self.board.selected_unit = None
                self.board.overlay.toggle_unit(None)
        elif pyxel.btnp(pyxel.KEY_TAB):
            # Pressing tab iterates through the player's settlements, centreing on each one.
            if self.game_started and self.board.overlay.can_iter_settlements_units():
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
            if self.game_started and self.board.overlay.is_bless_notif():
                self.board.overlay.toggle_blessing_notification(None)
            elif self.game_started and self.board.overlay.is_constr_notif():
                self.board.overlay.toggle_construction_notification(None)
            elif self.game_started and self.board.overlay.is_lvl_notif():
                self.board.overlay.toggle_level_up_notification(None)
            elif self.game_started and self.board.overlay.is_controls():
                self.board.overlay.toggle_controls()
            elif self.game_started and self.board.overlay.can_iter_settlements_units() and \
                    len(self.players[0].units) > 0:
                self.board.overlay.remove_warning_if_possible()
                if self.board.overlay.is_setl():
                    self.board.selected_settlement = None
                    self.board.overlay.toggle_settlement(None, self.players[0])
                if self.board.selected_unit is None:
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
            if self.game_started and self.board.selected_settlement is not None:
                # Pressing B will buyout the remaining cost of the settlement's current construction.
                current_work = self.board.selected_settlement.current_work
                remaining_work = current_work.construction.cost - current_work.zeal_consumed
                if self.players[0].wealth >= remaining_work:
                    self.board.overlay.toggle_construction_notification([
                        CompletedConstruction(self.board.selected_settlement.current_work.construction,
                                              self.board.selected_settlement)
                    ])
                    complete_construction(self.board.selected_settlement)
                    self.players[0].wealth -= remaining_work
        elif pyxel.btnp(pyxel.KEY_P):
            if self.game_started and not self.board.overlay.is_victory():
                self.board.overlay.toggle_pause()

    def draw(self):
        """
        Draws the game to the screen.
        """
        if self.on_menu:
            self.menu.draw()
        elif self.game_started:
            self.board.draw(self.players, self.map_pos, self.turn, self.heathens)

    def gen_players(self, cfg: GameConfig):
        """
        Generates the players for the game based on the supplied config.
        :param cfg: The game config.
        """
        self.players = [Player("The Chosen One", cfg.player_colour, 0, [], [], [], set())]
        colours = [pyxel.COLOR_NAVY, pyxel.COLOR_PURPLE, pyxel.COLOR_GREEN, pyxel.COLOR_BROWN, pyxel.COLOR_DARK_BLUE,
                   pyxel.COLOR_LIGHT_BLUE, pyxel.COLOR_RED, pyxel.COLOR_ORANGE, pyxel.COLOR_YELLOW, pyxel.COLOR_LIME,
                   pyxel.COLOR_CYAN, pyxel.COLOR_GRAY, pyxel.COLOR_PINK, pyxel.COLOR_PEACH]
        # Ensure that an AI player doesn't choose the same colour as the player.
        colours.remove(cfg.player_colour)
        for i in range(1, cfg.player_count):
            colour = random.choice(colours)
            colours.remove(colour)
            self.players.append(Player(f"NPC{i}", colour, 0, [], [], [], set(),
                                       ai_playstyle=random.choice(list(AIPlaystyle))))

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
                    setl.harvest_status = HarvestStatus.POOR
                    setl.economic_status = EconomicStatus.RECESSION
                elif setl.satisfaction < 40:
                    setl.harvest_status = HarvestStatus.POOR
                    setl.economic_status = EconomicStatus.STANDARD
                elif setl.satisfaction < 60:
                    setl.harvest_status = HarvestStatus.STANDARD
                    setl.economic_status = EconomicStatus.STANDARD
                elif setl.satisfaction >= 60:
                    setl.harvest_status = HarvestStatus.PLENTIFUL
                    setl.economic_status = EconomicStatus.STANDARD
                elif setl.satisfaction >= 80:
                    setl.harvest_status = HarvestStatus.PLENTIFUL
                    setl.economic_status = EconomicStatus.BOOM

                total_wealth, total_harvest, total_zeal, total_fortune = get_setl_totals(setl)
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
                            setl.strength -= setl.max_strength * 0.1
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
                    setl.satisfaction -= 0.5
                elif total_harvest >= setl.level * 8:
                    setl.satisfaction += 0.25
                setl.satisfaction = clamp(setl.satisfaction, 0, 100)

                setl.harvest_reserves += total_harvest
                # Settlement levels are increased if the settlement's harvest reserves exceed a certain level (specified
                # in models.py).
                if setl.harvest_reserves >= pow(setl.level, 2) * 25 and setl.level < 10:
                    setl.level += 1
                    levelled_up_settlements.append(setl)

                # Process the current construction, completing it if it has been finished.
                if setl.current_work is not None:
                    setl.current_work.zeal_consumed += total_zeal
                    if setl.current_work.zeal_consumed >= setl.current_work.construction.cost:
                        completed_constructions.append(CompletedConstruction(setl.current_work.construction, setl))
                        complete_construction(setl)
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
            self.heathens.append(get_heathen(heathen_loc))

        # Reset all heathens.
        for heathen in self.heathens:
            heathen.remaining_stamina = heathen.plan.total_stamina
            if heathen.health < heathen.plan.max_health:
                heathen.health = min(heathen.health + heathen.plan.max_health * 0.1, 100)

        self.board.overlay.remove_warning_if_possible()
        self.turn += 1

        possible_victory = self.check_for_victory()
        if possible_victory is not None:
            self.board.overlay.toggle_victory(possible_victory)
            return False
        return True

    def check_for_victory(self) -> typing.Optional[Victory]:
        """
        Check if any of the six victories have been achieved by any of the players.
        :return: A Victory, if one has been achieved.
        """
        players_with_setls = 0
        for p in self.players:
            if len(p.settlements) > 0:
                jubilated_setls = 0
                lvl_ten_setls = 0
                constructed_sanctum = False

                players_with_setls += 1
                for s in p.settlements:
                    if s.satisfaction == 100:
                        jubilated_setls += 1
                    if s.level == 10:
                        lvl_ten_setls += 1
                    if any(imp.name == "Holy Sanctum" for imp in s.improvements):
                        constructed_sanctum = True
                if jubilated_setls >= 5:
                    p.jubilation_ctr += 1
                else:
                    p.jubilation_ctr = 0
                # If the player has maintained 5 settlements at 100% satisfaction for 25 turns, they have achieved a
                # JUBILATION victory.
                if p.jubilation_ctr == 25:
                    return Victory(p, VictoryType.JUBILATION)
                # If the player has at least 10 settlements of level 10, they have achieved a GLUTTONY victory.
                if lvl_ten_setls >= 10:
                    return Victory(p, VictoryType.GLUTTONY)
                # If the player has constructed the Holy Sanctum, they have achieved a VIGOUR victory.
                if constructed_sanctum:
                    return Victory(p, VictoryType.VIGOUR)
            elif any(unit.plan.can_settle for unit in self.players[0].units):
                players_with_setls += 1
            # If the player has accumulated at least 100k wealth over the game, they have achieved an AFFLUENCE victory.
            if p.accumulated_wealth >= 100000:
                return Victory(p, VictoryType.AFFLUENCE)
            # If the player has undergone the blessings for all three pieces of ardour, they have achieved a
            # SERENDIPITY victory.
            if len([bls for bls in p.blessings if "Piece of" in bls.name]) == 3:
                return Victory(p, VictoryType.SERENDIPITY)

        if players_with_setls == 1:
            # If there is only one player with settlements, they have achieved an ELIMINATION victory.
            return Victory(next(player for player in self.players if len(player.settlements) > 0),
                           VictoryType.ELIMINATION)

        return None

    def process_heathens(self):
        """
        Process the turns for each of the heathens.
        """
        all_units = []
        for player in self.players:
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
                heathen.location = heathen.location[0] + x_movement, heathen.location[1] + y_movement
                heathen.remaining_stamina -= abs(x_movement) + abs(y_movement)

    def initialise_ais(self):
        """
        Initialise the AI players by adding their first settlement in a random location.
        """
        for player in self.players:
            if player.ai_playstyle is not None:
                setl_coords = random.randint(0, 89), random.randint(0, 99)
                quad_biome = self.board.quads[setl_coords[0]][setl_coords[1]].biome
                setl_name = self.namer.get_settlement_name(quad_biome)
                new_settl = Settlement(setl_name, setl_coords, [],
                                       [self.board.quads[setl_coords[0]][setl_coords[1]]],
                                       [get_default_unit(setl_coords)])
                player.settlements.append(new_settl)

    def process_ais(self):
        """
        Process the moves for each AI player.
        """
        for player in self.players:
            if player.ai_playstyle is not None:
                self.move_maker.make_move(player, self.players)

    def save_game(self):
        """
        Saves the current game with the current timestamp as the file name.
        """
        with open(f"saves/save-{datetime.datetime.now().isoformat(timespec='seconds')}.json", "w", encoding="utf-8") \
                as save_file:
            # We use chain.from_iterable() here because the quads array is 2D.
            save = {
                "quads": list(chain.from_iterable(self.board.quads)),
                "players": self.players,
                "heathens": self.heathens,
                "turn": self.turn,
                "cfg": self.board.game_config
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
        # Filter out the README, plus sort and reverse the list so that the most recent are first.
        saves = list(filter(lambda file: not file == "README.md", os.listdir("saves")))
        saves.sort()
        saves.reverse()
        with open(f"saves/{saves[save_idx]}", "r", encoding="utf-8") as save_file:
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
                    # We can do a direct conversion to a Unit object for units.
                    p.units[idx] = Unit(u.health, u.remaining_stamina, (u.location[0], u.location[1]), u.garrisoned,
                                        u.plan, u.has_attacked, u.sieging)
                for s in p.settlements:
                    # Make sure we remove the settlement's name so that we don't get duplicates.
                    self.namer.remove_settlement_name(s.name, s.quads[0].biome)
                    # Another tuple-array fix.
                    s.location = (s.location[0], s.location[1])
                    if s.current_work is not None:
                        # Get the actual Improvement or UnitPlan objects for the current work. We use hasattr() because
                        # improvements have a type and unit plans do not.
                        if hasattr(s.current_work.construction, "type"):
                            s.current_work.construction = get_improvement(s.current_work.construction.name)
                        else:
                            s.current_work.construction = get_unit_plan(s.current_work.construction.name)
                    for idx, imp in enumerate(s.improvements):
                        # Do another direct conversion for improvements.
                        s.improvements[idx] = get_improvement(imp.name)
                # We also do direct conversions to Blessing objects for the ongoing one, if there is one, as well as any
                # previously-completed ones.
                if p.ongoing_blessing:
                    p.ongoing_blessing.blessing = get_blessing(p.ongoing_blessing.blessing.name)
                for idx, bls in enumerate(p.blessings):
                    p.blessings[idx] = get_blessing(bls.name)
                if p.ai_playstyle is not None:
                    p.ai_playstyle = AIPlaystyle[p.ai_playstyle]
            # For the AI players, we can just make quads_seen an empty set, as it's not used.
            for i in range(1, len(self.players)):
                self.players[i].quads_seen = set()

            self.heathens = []
            for h in save.heathens:
                # Do another direct conversion for the heathens.
                self.heathens.append(Heathen(h.health, h.remaining_stamina, (h.location[0], h.location[1]),
                                             HEATHEN_UNIT_PLAN, h.has_attacked))

            self.turn = save.turn
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
        saves = list(filter(lambda file_name: not file_name == "README.md", os.listdir("saves")))
        # Default to the cancel option if there are no saves available.
        if len(saves) == 0:
            self.menu.save_idx = -1
        else:
            saves.sort()
            saves.reverse()
            for f in saves:
                # Just show the date and time.
                self.menu.saves.append(f[5:-5].replace("T", " "))
