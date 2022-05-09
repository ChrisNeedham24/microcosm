import time
import typing

import pyxel

from board import Board
from calculator import clamp
from catalogue import get_available_improvements, get_available_blessings, get_available_unit_plans
from menu import Menu, MenuOption
from models import Player, Settlement, Construction, OngoingBlessing, CompletedConstruction, Improvement, Unit, UnitPlan


# TODO F Music? Warduke Module 1/2/3 looks like a good shout
# TODO F Victory conditions - one for each resource type (harvest, wealth, etc.)
# TODO F Some sort of fog of war would be cool
# TODO F Pause screen for saving and exiting

class Game:
    def __init__(self):
        pyxel.init(200, 200, title="Microcosm")

        self.menu = Menu()
        self.board = Board()
        self.players: typing.List[Player] = [Player("Test", pyxel.COLOR_RED, 0, [], [], [])]

        self.on_menu = True
        self.game_started = False

        self.last_time = time.time()

        self.map_pos: (int, int) = 0, 0
        self.turn = 1

        pyxel.run(self.on_update, self.draw)

    def on_update(self):
        time_elapsed = time.time() - self.last_time
        self.last_time = time.time()

        self.board.update(time_elapsed)

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
                elif self.menu.menu_option is MenuOption.LOAD_GAME:
                    # TODO F Saving and loading
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
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_RIGHT):
            if self.game_started:
                self.board.overlay.remove_warning_if_possible()
                self.board.process_right_click(pyxel.mouse_x, pyxel.mouse_y, self.map_pos)
        elif pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.game_started:
                self.board.overlay.remove_warning_if_possible()
                self.board.process_left_click(pyxel.mouse_x, pyxel.mouse_y,
                                              len(self.players[0].settlements) > 0,
                                              self.players[0], self.map_pos)
        elif pyxel.btnp(pyxel.KEY_SHIFT):
            if self.game_started and not self.board.overlay.is_tutorial():
                self.board.overlay.remove_warning_if_possible()
                self.board.overlay.toggle_standard(self.turn)
        elif pyxel.btnp(pyxel.KEY_C):
            if self.game_started and self.board.selected_settlement is not None:
                self.board.overlay.toggle_construction(get_available_improvements(self.players[0],
                                                                                  self.board.selected_settlement),
                                                       get_available_unit_plans(self.players[0]))
        elif pyxel.btnp(pyxel.KEY_F):
            if self.game_started and self.board.overlay.is_standard():
                self.board.overlay.toggle_blessing(get_available_blessings(self.players[0]))
        elif pyxel.btnp(pyxel.KEY_D):
            if self.game_started and self.board.selected_settlement is not None and \
                    len(self.board.selected_settlement.garrison) > 0:
                self.board.deploying_army = True
                self.board.overlay.toggle_deployment()
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

    def draw(self):
        if self.on_menu:
            self.menu.draw()
        elif self.game_started:
            self.board.draw(self.players, self.map_pos, self.turn)

    def end_turn(self):
        # First make sure the player hasn't ended their turn without a construction or blessing.
        problematic_settlements = []
        for setl in self.players[0].settlements:
            if setl.current_work is None:
                problematic_settlements.append(setl)
        has_no_blessing = self.players[0].ongoing_blessing is None
        if not self.board.overlay.is_warning() and (len(problematic_settlements) > 0 or has_no_blessing):
            self.board.overlay.toggle_warning(problematic_settlements, has_no_blessing)
            return

        for player in self.players:
            total_fortune = 0
            total_wealth = 0
            completed_constructions: typing.List[CompletedConstruction] = []
            for setl in player.settlements:
                total_zeal = max(sum(quad.zeal for quad in setl.quads) +
                                 sum(imp.effect.zeal for imp in setl.improvements), 0.5)
                total_fortune += sum(quad.fortune for quad in setl.quads)
                total_fortune += sum(imp.effect.fortune for imp in setl.improvements)
                total_fortune = max(0.5, total_fortune)
                total_wealth += sum(quad.wealth for quad in setl.quads)
                total_wealth += sum(imp.effect.wealth for imp in setl.improvements)
                total_wealth = max(0.5, total_wealth)
                if setl.current_work is not None:
                    setl.current_work.zeal_consumed += total_zeal
                    if setl.current_work.zeal_consumed >= setl.current_work.construction.cost:
                        if isinstance(setl.current_work.construction, Improvement):
                            setl.improvements.append(setl.current_work.construction)
                            if setl.current_work.construction.effect.strength > 0:
                                setl.strength += setl.current_work.construction.effect.strength
                            if setl.current_work.construction.effect.satisfaction > 0:
                                setl.satisfaction += setl.current_work.construction.effect.satisfaction
                        else:
                            plan: UnitPlan = setl.current_work.construction
                            setl.garrison.append(Unit(plan.max_health, plan.total_stamina, setl.location, True, plan))
                        completed_constructions.append(CompletedConstruction(setl.current_work.construction, setl))
                        setl.current_work = None
            if len(completed_constructions) > 0:
                self.board.overlay.toggle_construction_notification(completed_constructions)
            for unit in player.units:
                unit.remaining_stamina = unit.plan.total_stamina
            if player.ongoing_blessing is not None:
                player.ongoing_blessing.fortune_consumed += total_fortune
                if player.ongoing_blessing.fortune_consumed >= player.ongoing_blessing.blessing.cost:
                    player.blessings.append(player.ongoing_blessing.blessing)
                    self.board.overlay.toggle_blessing_notification(player.ongoing_blessing.blessing)
                    player.ongoing_blessing = None
            player.wealth += total_wealth
        self.board.overlay.remove_warning_if_possible()
        self.turn += 1
