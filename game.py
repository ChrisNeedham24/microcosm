import random
import time
import typing
from enum import Enum

import pyxel

from board import Board
from calculator import clamp, attack, get_player_totals, get_setl_totals, complete_construction
from catalogue import get_available_improvements, get_available_blessings, get_available_unit_plans, get_heathen, \
    get_settlement_name, get_default_unit, get_unlockable_units, get_unlockable_improvements
from menu import Menu, MenuOption
from models import Player, Settlement, Construction, OngoingBlessing, CompletedConstruction, Improvement, Unit, \
    UnitPlan, HarvestStatus, EconomicStatus, Heathen, AIPlaystyle, Blessing
from movemaker import MoveMaker
from music_player import MusicPlayer


# TODO FF Victory conditions - one for each resource type (harvest, wealth, etc.)
# TODO FF Some sort of fog of war would be cool
# TODO FF Pause screen for saving and exiting (also controls)
# TODO FF Add Wiki on main menu
# TODO FF Game setup screen with number of players and colours, also biome clustering on/off
# TODO F Add siegeing/attacking of settlements

class Game:
    def __init__(self):
        pyxel.init(200, 200, title="Microcosm")

        self.menu = Menu()
        self.board = Board()
        self.players: typing.List[Player] = [
            Player("Test", pyxel.COLOR_RED, 0, [], [], []),
            Player("NPC1", pyxel.COLOR_GREEN, 0, [], [], [], ai_playstyle=random.choice(list(AIPlaystyle))),
            Player("NPC2", pyxel.COLOR_PURPLE, 0, [], [], [], ai_playstyle=random.choice(list(AIPlaystyle))),
            Player("NPC3", pyxel.COLOR_CYAN, 0, [], [], [], ai_playstyle=random.choice(list(AIPlaystyle)))
        ]
        self.heathens: typing.List[Heathen] = []

        self.on_menu = True
        self.game_started = False

        self.last_time = time.time()

        self.map_pos: (int, int) = random.randint(0, 76), random.randint(0, 68)
        self.turn = 1

        self.music_player = MusicPlayer()
        self.music_player.play_menu_music()

        self.move_maker = MoveMaker(self.board)
        self.initialise_ais()

        pyxel.run(self.on_update, self.draw)

    def on_update(self):
        time_elapsed = time.time() - self.last_time
        self.last_time = time.time()

        self.board.update(time_elapsed)

        if not self.on_menu and not self.music_player.is_playing():
            self.music_player.next_song()

        all_units = []
        for player in self.players:
            for unit in player.units:
                all_units.append(unit)

        if pyxel.btnp(pyxel.KEY_DOWN):
            if self.on_menu:
                self.menu.navigate(True)
            elif self.game_started:
                if self.board.overlay.is_constructing():
                    self.board.overlay.navigate_constructions(down=True)
                elif self.board.overlay.is_blessing():
                    self.board.overlay.navigate_blessings(down=True)
                else:
                    self.board.overlay.remove_warning_if_possible()
                    self.map_pos = self.map_pos[0], clamp(self.map_pos[1] + 1, -1, 69)
        elif pyxel.btnp(pyxel.KEY_UP):
            if self.on_menu:
                self.menu.navigate(False)
            elif self.game_started:
                if self.board.overlay.is_constructing():
                    self.board.overlay.navigate_constructions(down=False)
                elif self.board.overlay.is_standard():
                    self.board.overlay.navigate_blessings(down=False)
                else:
                    self.board.overlay.remove_warning_if_possible()
                    self.map_pos = self.map_pos[0], clamp(self.map_pos[1] - 1, -1, 69)
        elif pyxel.btnp(pyxel.KEY_LEFT):
            if self.game_started and self.board.overlay.is_constructing():
                self.board.overlay.constructing_improvement = True
                self.board.overlay.selected_construction = self.board.overlay.available_constructions[0]
            elif self.game_started:
                self.board.overlay.remove_warning_if_possible()
                self.map_pos = clamp(self.map_pos[0] - 1, -1, 77), self.map_pos[1]
        elif pyxel.btnp(pyxel.KEY_RIGHT):
            if self.game_started and self.board.overlay.is_constructing():
                self.board.overlay.constructing_improvement = False
                self.board.overlay.selected_construction = self.board.overlay.available_unit_plans[0]
            elif self.game_started:
                self.board.overlay.remove_warning_if_possible()
                self.map_pos = clamp(self.map_pos[0] + 1, -1, 77), self.map_pos[1]
        elif pyxel.btnp(pyxel.KEY_RETURN):
            if self.on_menu:
                if self.menu.menu_option is MenuOption.NEW_GAME:
                    pyxel.mouse(visible=True)
                    self.game_started = True
                    self.on_menu = False
                    self.music_player.stop_menu_music()
                    self.music_player.play_game_music()
                elif self.menu.menu_option is MenuOption.LOAD_GAME:
                    # TODO FF Saving and loading
                    print("Unsupported for now.")
                elif self.menu.menu_option is MenuOption.EXIT:
                    pyxel.quit()
            elif self.game_started and self.board.overlay.is_constructing():
                if self.board.overlay.selected_construction is not None:
                    self.board.selected_settlement.current_work = Construction(self.board.overlay.selected_construction)
                self.board.overlay.toggle_construction([], [])
            elif self.game_started and self.board.overlay.is_blessing():
                if self.board.overlay.selected_blessing is not None:
                    self.players[0].ongoing_blessing = OngoingBlessing(self.board.overlay.selected_blessing)
                self.board.overlay.toggle_blessing([])
            elif self.game_started and not self.board.overlay.is_tutorial():
                self.board.overlay.update_turn(self.turn)
                self.end_turn()
                self.process_heathens()
                self.process_ais()
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            if self.game_started:
                self.board.overlay.remove_warning_if_possible()
                self.board.process_right_click(pyxel.mouse_x, pyxel.mouse_y, self.map_pos)
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.game_started:
                self.board.overlay.remove_warning_if_possible()
                self.board.process_left_click(pyxel.mouse_x, pyxel.mouse_y,
                                              len(self.players[0].settlements) > 0,
                                              self.players[0], self.map_pos, self.heathens, all_units,
                                              self.players)
        elif pyxel.btnp(pyxel.KEY_SHIFT):
            if self.game_started and not self.board.overlay.is_tutorial():
                self.board.overlay.remove_warning_if_possible()
                self.board.overlay.toggle_standard(self.turn)
        elif pyxel.btnp(pyxel.KEY_C):
            if self.game_started and self.board.selected_settlement is not None:
                self.board.overlay.toggle_construction(get_available_improvements(self.players[0],
                                                                                  self.board.selected_settlement),
                                                       get_available_unit_plans(self.players[0],
                                                                                self.board.selected_settlement.level))
        elif pyxel.btnp(pyxel.KEY_F):
            if self.game_started and self.board.overlay.is_standard():
                self.board.overlay.toggle_blessing(get_available_blessings(self.players[0]))
        elif pyxel.btnp(pyxel.KEY_D):
            if self.game_started and self.board.selected_settlement is not None and \
                    len(self.board.selected_settlement.garrison) > 0:
                self.board.deploying_army = True
                self.board.overlay.toggle_deployment()
            elif self.game_started and self.board.selected_unit is not None:
                self.players[0].wealth += self.board.selected_unit.plan.cost
                self.players[0].units.remove(self.board.selected_unit)
                self.board.selected_unit = None
                self.board.overlay.toggle_unit(None)
        elif pyxel.btnp(pyxel.KEY_TAB):
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
            if self.game_started and self.board.overlay.is_bless_notif():
                self.board.overlay.toggle_blessing_notification(None)
            elif self.game_started and self.board.overlay.is_constr_notif():
                self.board.overlay.toggle_construction_notification(None)
            elif self.game_started and self.board.overlay.is_lvl_notif():
                self.board.overlay.toggle_level_up_notification(None)
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
            if self.game_started and self.board.selected_unit.plan.can_settle:
                self.board.handle_new_settlement(self.players[0])
        elif pyxel.btnp(pyxel.KEY_N):
            if self.game_started:
                self.music_player.next_song()
        elif pyxel.btnp(pyxel.KEY_B):
            if self.game_started and self.board.selected_settlement is not None:
                current_work = self.board.selected_settlement.current_work
                remaining_work = current_work.construction.cost - current_work.zeal_consumed
                if self.players[0].wealth >= remaining_work:
                    self.board.overlay.toggle_construction_notification([
                        CompletedConstruction(self.board.selected_settlement.current_work.construction,
                                              self.board.selected_settlement)
                    ])
                    complete_construction(self.board.selected_settlement)
                    self.players[0].wealth -= remaining_work

    def draw(self):
        if self.on_menu:
            self.menu.draw()
        elif self.game_started:
            self.board.draw(self.players, self.map_pos, self.turn, self.heathens)

    def end_turn(self):
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
            return

        for player in self.players:
            total_fortune = 0
            total_wealth = 0
            completed_constructions: typing.List[CompletedConstruction] = []
            levelled_up_settlements: typing.List[Settlement] = []
            for setl in player.settlements:
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

                if total_harvest < setl.level * 3:
                    setl.satisfaction -= 0.5
                elif total_harvest >= setl.level * 6:
                    setl.satisfaction += 0.5

                setl.harvest_reserves += total_harvest
                if setl.harvest_reserves >= pow(setl.level, 2) * 25:
                    setl.level += 1
                    levelled_up_settlements.append(setl)

                if setl.current_work is not None:
                    setl.current_work.zeal_consumed += total_zeal
                    if setl.current_work.zeal_consumed >= setl.current_work.construction.cost:
                        completed_constructions.append(CompletedConstruction(setl.current_work.construction, setl))
                        complete_construction(setl)
            if player.ai_playstyle is None and len(completed_constructions) > 0:
                self.board.overlay.toggle_construction_notification(completed_constructions)
            if player.ai_playstyle is None and len(levelled_up_settlements) > 0:
                self.board.overlay.toggle_level_up_notification(levelled_up_settlements)
            for unit in player.units:
                unit.remaining_stamina = unit.plan.total_stamina
                if unit.health < unit.plan.max_health:
                    unit.health = min(unit.health + unit.plan.max_health * 0.1, 100)
                unit.has_attacked = False
                if not unit.garrisoned:
                    total_wealth -= unit.plan.cost / 25
            if player.ongoing_blessing is not None:
                player.ongoing_blessing.fortune_consumed += total_fortune
                if player.ongoing_blessing.fortune_consumed >= player.ongoing_blessing.blessing.cost:
                    player.blessings.append(player.ongoing_blessing.blessing)
                    if player.ai_playstyle is None:
                        self.board.overlay.toggle_blessing_notification(player.ongoing_blessing.blessing)
                    player.ongoing_blessing = None
            while player.wealth + total_wealth < 0:
                sold_unit = player.units.pop()
                player.wealth += sold_unit.plan.cost
            player.wealth = max(player.wealth + total_wealth, 0)

        if self.turn % 5 == 0:
            heathen_loc = random.randint(0, 89), random.randint(0, 99)
            self.heathens.append(get_heathen(heathen_loc))

        for heathen in self.heathens:
            heathen.remaining_stamina = heathen.plan.total_stamina
            if heathen.health < heathen.plan.max_health:
                heathen.health = min(heathen.health + heathen.plan.max_health * 0.1, 100)

        self.board.overlay.remove_warning_if_possible()
        self.turn += 1

    def process_heathens(self):
        all_units = []
        for player in self.players:
            for unit in player.units:
                all_units.append(unit)
        for heathen in self.heathens:
            within_range: typing.Optional[Unit] = None
            for unit in all_units:
                if max(abs(unit.location[0] - heathen.location[0]),
                       abs(unit.location[1] - heathen.location[1])) <= heathen.remaining_stamina and \
                        heathen.health >= unit.health / 2:
                    within_range = unit
                    break
            if within_range is not None:
                if within_range.location[0] - heathen.location[0] < 0:
                    heathen.location = within_range.location[0] + 1, within_range.location[1]
                else:
                    heathen.location = within_range.location[0] - 1, within_range.location[1]
                heathen.remaining_stamina = 0
                data = attack(heathen, within_range)
                if within_range.health < 0:
                    for player in self.players:
                        if within_range in player.units:
                            player.units.remove(within_range)
                            break
                    self.board.selected_unit = None
                    self.board.overlay.toggle_unit(None)
                if heathen.health < 0:
                    self.heathens.remove(heathen)
                if within_range in self.players[0].units:
                    self.board.overlay.toggle_attack(data)
            else:
                x_movement = random.randint(-heathen.remaining_stamina, heathen.remaining_stamina)
                rem_movement = heathen.remaining_stamina - abs(x_movement)
                y_movement = random.choice([-rem_movement, rem_movement])
                heathen.location = heathen.location[0] + x_movement, heathen.location[1] + y_movement
                heathen.remaining_stamina -= abs(x_movement) + abs(y_movement)

    def initialise_ais(self):
        for player in self.players:
            if player.ai_playstyle is not None:
                # Add their settlement.
                setl_coords = random.randint(0, 89), random.randint(0, 99)
                quad_biome = self.board.quads[setl_coords[0]][setl_coords[1]].biome
                setl_name = get_settlement_name(quad_biome)
                new_settl = Settlement(setl_name, [], 100, 50, setl_coords,
                                       [self.board.quads[setl_coords[0]][setl_coords[1]]],
                                       [get_default_unit(setl_coords)], None)
                player.settlements.append(new_settl)

    def process_ais(self):
        for player in self.players:
            if player.ai_playstyle is not None:
                # print(player)
                self.move_maker.make_move(player, self.players)

