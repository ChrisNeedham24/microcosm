import random
import typing

import pyxel

from source.display.board import Board
from source.util.calculator import clamp, complete_construction, attack_setl
from source.foundation.catalogue import get_available_improvements, get_available_blessings, get_available_unit_plans, \
    PROJECTS
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.display.menu import MainMenuOption, SetupOption, WikiOption
from source.foundation.models import Construction, OngoingBlessing, CompletedConstruction, Heathen, GameConfig, \
    OverlayType, Faction, ConstructionMenu, Project
from source.game_management.movemaker import set_player_construction
from source.display.overlay import SettlementAttackType, PauseOption
from source.saving.game_save_manager import load_game, get_saves, save_game


def on_key_arrow_down(game_controller: GameController, game_state: GameState, is_ctrl_key: bool):
    """
    Handles an Arrow Key down event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    :param is_ctrl_key: Whether the CTRL key has also been pressed.
    """
    if game_state.on_menu:
        game_controller.menu.navigate(down=True)
    elif game_state.game_started:
        if game_state.board.overlay.is_constructing():
            game_state.board.overlay.navigate_constructions(down=True)
        elif game_state.board.overlay.is_blessing():
            game_state.board.overlay.navigate_blessings(down=True)
        elif game_state.board.overlay.is_setl_click():
            game_state.board.overlay.navigate_setl_click(down=True)
        elif game_state.board.overlay.is_controls():
            game_state.board.overlay.show_additional_controls = True
        elif game_state.board.overlay.is_pause():
            game_state.board.overlay.navigate_pause(down=True)
        elif game_state.board.overlay.is_standard():
            game_state.board.overlay.navigate_standard(down=True)
        else:
            game_state.board.overlay.remove_warning_if_possible()
            # If we're not on a menu, pan the map when you press down.
            # Holding Ctrl will pan the map 5 spaces.
            if is_ctrl_key:
                game_state.map_pos = game_state.map_pos[0], clamp(game_state.map_pos[1] + 5, -1, 69)
            else:
                game_state.map_pos = game_state.map_pos[0], clamp(game_state.map_pos[1] + 1, -1, 69)


def on_key_arrow_up(game_controller: GameController, game_state: GameState, is_ctrl_key: bool):
    """
    Handles an Arrow Key up event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    :param is_ctrl_key: Whether the CTRL key has also been pressed.
    """
    if game_state.on_menu:
        game_controller.menu.navigate(up=True)
    elif game_state.game_started:
        if game_state.board.overlay.is_constructing():
            game_state.board.overlay.navigate_constructions(down=False)
        elif game_state.board.overlay.is_blessing():
            game_state.board.overlay.navigate_blessings(down=False)
        elif game_state.board.overlay.is_setl_click():
            game_state.board.overlay.navigate_setl_click(up=True)
        elif game_state.board.overlay.is_controls():
            game_state.board.overlay.show_additional_controls = False
        elif game_state.board.overlay.is_pause():
            game_state.board.overlay.navigate_pause(down=False)
        elif game_state.board.overlay.is_standard():
            game_state.board.overlay.navigate_standard(down=False)
        else:
            game_state.board.overlay.remove_warning_if_possible()
            # If we're not on a menu, pan the map when you press up.
            # Holding Ctrl will pan the map 5 spaces.
            if is_ctrl_key:
                game_state.map_pos = game_state.map_pos[0], clamp(game_state.map_pos[1] - 5, -1, 69)
            else:
                game_state.map_pos = game_state.map_pos[0], clamp(game_state.map_pos[1] - 1, -1, 69)


def on_key_arrow_left(game_controller: GameController, game_state: GameState, is_ctrl_key: bool):
    """
    Handles an Arrow Key left event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    :param is_ctrl_key: Whether the CTRL key has also been pressed.
    """
    if game_state.on_menu:
        game_controller.menu.navigate(left=True)
    if game_state.game_started and game_state.board.overlay.is_constructing():
        if game_state.board.overlay.current_construction_menu is ConstructionMenu.PROJECTS and \
                len(game_state.board.overlay.available_constructions) > 0:
            game_state.board.overlay.current_construction_menu = ConstructionMenu.IMPROVEMENTS
            game_state.board.overlay.selected_construction = game_state.board.overlay.available_constructions[0]
        elif game_state.board.overlay.current_construction_menu is ConstructionMenu.UNITS:
            game_state.board.overlay.current_construction_menu = ConstructionMenu.PROJECTS
            game_state.board.overlay.selected_construction = game_state.board.overlay.available_projects[0]
    elif game_state.game_started:
        if game_state.board.overlay.is_setl_click():
            game_state.board.overlay.navigate_setl_click(left=True)
        else:
            game_state.board.overlay.remove_warning_if_possible()
            # If we're not on a menu, pan the map when you press left.
            # Holding Ctrl will pan the map 5 spaces.
            if is_ctrl_key:
                game_state.map_pos = clamp(game_state.map_pos[0] - 5, -1, 77), game_state.map_pos[1]
            else:
                game_state.map_pos = clamp(game_state.map_pos[0] - 1, -1, 77), game_state.map_pos[1]


def on_key_arrow_right(game_controller: GameController, game_state: GameState, is_ctrl_key: bool):
    """
    Handles an Arrow Key right event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    :param is_ctrl_key: Whether the CTRL key has also been pressed.
    """
    if game_state.on_menu:
        game_controller.menu.navigate(right=True)
    if game_state.game_started and game_state.board.overlay.is_constructing():
        if game_state.board.overlay.current_construction_menu is ConstructionMenu.IMPROVEMENTS:
            game_state.board.overlay.current_construction_menu = ConstructionMenu.PROJECTS
            game_state.board.overlay.selected_construction = game_state.board.overlay.available_projects[0]
        elif game_state.board.overlay.current_construction_menu is ConstructionMenu.PROJECTS:
            game_state.board.overlay.current_construction_menu = ConstructionMenu.UNITS
            game_state.board.overlay.selected_construction = game_state.board.overlay.available_unit_plans[0]
            game_state.board.overlay.unit_plan_boundaries = 0, 5
    elif game_state.game_started:
        if game_state.board.overlay.is_setl_click():
            game_state.board.overlay.navigate_setl_click(right=True)
        else:
            game_state.board.overlay.remove_warning_if_possible()
            # If we're not on a menu, pan the map when you press right.
            # Holding Ctrl will pan the map 5 spaces.
            if is_ctrl_key:
                game_state.map_pos = clamp(game_state.map_pos[0] + 5, -1, 77), game_state.map_pos[1]
            else:
                game_state.map_pos = clamp(game_state.map_pos[0] + 1, -1, 77), game_state.map_pos[1]


def on_key_return(game_controller: GameController, game_state: GameState):
    """
    Handles an Enter key event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    """
    if game_state.on_menu:
        if game_controller.menu.in_game_setup and game_controller.menu.setup_option is SetupOption.START_GAME:
            # If the player has pressed enter to start the game, generate the players, board, and AI players.
            pyxel.mouse(visible=True)
            game_state.game_started = True
            game_state.turn = 1
            # Reinitialise night variables.
            random.seed()
            game_state.until_night = random.randint(10, 20)
            game_state.nighttime_left = 0
            game_state.on_menu = False
            cfg: GameConfig = game_controller.menu.get_game_config()
            game_state.gen_players(cfg)
            game_state.board = Board(cfg, game_controller.namer)
            game_controller.move_maker.board_ref = game_state.board
            game_state.board.overlay.toggle_tutorial()
            game_controller.namer.reset()
            game_state.initialise_ais(game_controller.namer)
            game_controller.music_player.stop_menu_music()
            game_controller.music_player.play_game_music()
        elif game_controller.menu.loading_game:
            if game_controller.menu.save_idx == -1:
                game_controller.menu.loading_game = False
            else:
                load_game(game_state, game_controller)
        elif game_controller.menu.in_wiki:
            if game_controller.menu.wiki_option is WikiOption.BACK:
                game_controller.menu.in_wiki = False
            else:
                game_controller.menu.wiki_showing = game_controller.menu.wiki_option
        else:
            match game_controller.menu.main_menu_option:
                case MainMenuOption.NEW_GAME:
                    game_controller.menu.in_game_setup = True
                case MainMenuOption.LOAD_GAME:
                    game_controller.menu.loading_game = True
                    get_saves(game_controller)
                case MainMenuOption.WIKI:
                    game_controller.menu.in_wiki = True
                case MainMenuOption.EXIT:
                    pyxel.quit()
    elif game_state.game_started and (game_state.board.overlay.is_victory() or
                                      game_state.board.overlay.is_elimination() and game_state.players[0].eliminated):
        # If the player has won the game, or they've just been eliminated themselves, enter will take them back
        # to the menu.
        game_state.game_started = False
        game_state.on_menu = True
        game_controller.menu.loading_game = False
        game_controller.menu.in_game_setup = False
        game_controller.menu.main_menu_option = MainMenuOption.NEW_GAME
        game_controller.music_player.stop_game_music()
        game_controller.music_player.play_menu_music()
        # If the player is choosing a blessing or construction, enter will select it.
    elif game_state.game_started and game_state.board.overlay.is_constructing():
        if game_state.board.overlay.selected_construction is not None:
            game_state.board.selected_settlement.current_work = Construction(
                game_state.board.overlay.selected_construction)
        game_state.board.overlay.toggle_construction([], [], [])
    elif game_state.game_started and game_state.board.overlay.is_blessing():
        if game_state.board.overlay.selected_blessing is not None:
            game_state.players[0].ongoing_blessing = OngoingBlessing(game_state.board.overlay.selected_blessing)
        game_state.board.overlay.toggle_blessing([])
    elif game_state.game_started and game_state.board.overlay.is_setl_click():
        match game_state.board.overlay.setl_attack_opt:
            # If the player has chosen to attack a settlement, execute the attack.
            case SettlementAttackType.ATTACK:
                game_state.board.overlay.toggle_setl_click(None, None)
                data = attack_setl(game_state.board.selected_unit, game_state.board.overlay.attacked_settlement,
                                   game_state.board.overlay.attacked_settlement_owner, False)
                if data.attacker_was_killed:
                    # If the player's unit died, destroy and deselect it.
                    game_state.players[0].units.remove(game_state.board.selected_unit)
                    game_state.board.selected_unit = None
                    game_state.board.overlay.toggle_unit(None)
                elif data.setl_was_taken:
                    # If the settlement was taken, transfer it to the player, while also marking any units that
                    # were involved in the siege as no longer besieging.
                    data.settlement.besieged = False
                    for unit in game_state.players[0].units:
                        if abs(unit.location[0] - data.settlement.location[0]) <= 1 and \
                                abs(unit.location[1] - data.settlement.location[1]) <= 1:
                            unit.besieging = False
                    # The Concentrated can only have a single settlement, so when they take others, the
                    # settlements simply disappear.
                    if game_state.players[0].faction is not Faction.CONCENTRATED:
                        game_state.players[0].settlements.append(data.settlement)
                    for idx, p in enumerate(game_state.players):
                        if data.settlement in p.settlements and idx != 0:
                            p.settlements.remove(data.settlement)
                            break
                game_state.board.overlay.toggle_setl_attack(data)
                game_state.board.attack_time_bank = 0
            case SettlementAttackType.BESIEGE:
                # Alternatively, begin a siege on the settlement.
                game_state.board.selected_unit.besieging = True
                game_state.board.overlay.attacked_settlement.besieged = True
                game_state.board.overlay.toggle_setl_click(None, None)
            case _:
                game_state.board.overlay.toggle_setl_click(None, None)
    elif game_state.game_started and game_state.board.overlay.is_pause():
        match game_state.board.overlay.pause_option:
            case PauseOption.RESUME:
                game_state.board.overlay.toggle_pause()
            case PauseOption.SAVE:
                save_game(game_state)
                game_state.board.overlay.has_saved = True
            case PauseOption.CONTROLS:
                game_state.board.overlay.show_additional_controls = False
                game_state.board.overlay.toggle_controls()
            case PauseOption.QUIT:
                game_state.game_started = False
                game_state.on_menu = True
                game_controller.menu.loading_game = False
                game_controller.menu.in_game_setup = False
                game_controller.menu.main_menu_option = MainMenuOption.NEW_GAME
                game_controller.music_player.stop_game_music()
                game_controller.music_player.play_menu_music()
    elif game_state.game_started and not (
            game_state.board.overlay.is_tutorial() or game_state.board.overlay.is_deployment() or
            game_state.board.overlay.is_bless_notif() or
            game_state.board.overlay.is_constr_notif() or game_state.board.overlay.is_lvl_notif() or
            game_state.board.overlay.is_close_to_vic() or
            game_state.board.overlay.is_investigation() or game_state.board.overlay.is_night()):
        # If we are not in any of the above situations, end the turn.
        if game_state.end_turn():
            # Autosave every 10 turns.
            if game_state.turn % 10 == 0:
                save_game(game_state, auto=True)

            game_state.board.overlay.update_turn(game_state.turn)
            game_state.process_heathens()
            game_state.process_ais(game_controller.move_maker)


def on_key_shift(game_state: GameState):
    """
    Handles a Shift key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started:
        game_state.board.overlay.remove_warning_if_possible()
        # Display the standard overlay.
        game_state.board.overlay.toggle_standard(game_state.turn)


def on_key_c(game_state: GameState):
    """
    Handles a C key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started and game_state.board.selected_settlement is not None:
        # Pick a construction.
        game_state.board.overlay.toggle_construction(
            get_available_improvements(game_state.players[0],
                                       game_state.board.selected_settlement),
            PROJECTS,
            get_available_unit_plans(game_state.players[0],
                                     game_state.board.selected_settlement.level))


def on_key_f(game_controller: GameController, game_state: GameState):
    """
    Handles an F key event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    """
    if game_state.on_menu and game_controller.menu.in_game_setup \
            and game_controller.menu.setup_option is SetupOption.PLAYER_FACTION:
        game_controller.menu.showing_faction_details = not game_controller.menu.showing_faction_details
    elif game_state.game_started and game_state.board.overlay.is_standard():
        # Pick a blessing.
        game_state.board.overlay.toggle_blessing(get_available_blessings(game_state.players[0]))


def on_key_d(game_state: GameState):
    """
    Handles a D key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started and game_state.board.selected_settlement is not None and \
            len(game_state.board.selected_settlement.garrison) > 0:
        game_state.board.deploying_army = True
        game_state.board.overlay.toggle_deployment()
    elif game_state.game_started and game_state.board.selected_unit is not None and \
            game_state.board.selected_unit in game_state.players[0].units:
        # If a unit is selected rather than a settlement, pressing D disbands the army, destroying the unit and
        # adding to the player's wealth.
        game_state.players[0].wealth += game_state.board.selected_unit.plan.cost
        game_state.players[0].units.remove(game_state.board.selected_unit)
        game_state.board.selected_unit = None
        game_state.board.overlay.toggle_unit(None)


def on_key_tab(game_state: GameState):
    """
    Handles a Tab key event in the game loop.
    :param game_state: The current GameState object.
    """
    # Pressing tab iterates through the player's settlements, centreing on each one.
    if game_state.game_started and game_state.board.overlay.can_iter_settlements_units() and \
            len(game_state.players[0].settlements) > 0:
        game_state.board.overlay.remove_warning_if_possible()
        if game_state.board.overlay.is_unit():
            game_state.board.selected_unit = None
            game_state.board.overlay.toggle_unit(None)
        if game_state.board.selected_settlement is None:
            game_state.board.selected_settlement = game_state.players[0].settlements[0]
            game_state.board.overlay.toggle_settlement(game_state.players[0].settlements[0], game_state.players[0])
        elif len(game_state.players[0].settlements) > 1:
            current_idx = game_state.players[0].settlements.index(game_state.board.selected_settlement)
            new_idx = 0
            if current_idx != len(game_state.players[0].settlements) - 1:
                new_idx = current_idx + 1
            game_state.board.selected_settlement = game_state.players[0].settlements[new_idx]
            game_state.board.overlay.update_settlement(game_state.players[0].settlements[new_idx])
        game_state.map_pos = (clamp(game_state.board.selected_settlement.location[0] - 12, -1, 77),
                              clamp(game_state.board.selected_settlement.location[1] - 11, -1, 69))


def on_key_space(game_controller: GameController, game_state: GameState):
    """
    Handles a Space key event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    """
    # Pressing space either dismisses the current overlay or iterates through the player's units.
    if game_state.on_menu and game_controller.menu.in_wiki and game_controller.menu.wiki_showing is not None:
        game_controller.menu.wiki_showing = None
    if game_state.on_menu and game_controller.menu.in_game_setup:
        game_controller.menu.in_game_setup = False
    if game_state.on_menu and game_controller.menu.loading_game and game_controller.menu.load_failed:
        game_controller.menu.load_failed = False
    elif game_state.on_menu and game_controller.menu.loading_game:
        game_controller.menu.loading_game = False
    if game_state.game_started and game_state.board.overlay.is_elimination():
        game_state.board.overlay.toggle_elimination(None)
    elif game_state.game_started and game_state.board.overlay.is_night():
        game_state.board.overlay.toggle_night(None)
    elif game_state.game_started and game_state.board.overlay.is_close_to_vic():
        game_state.board.overlay.toggle_close_to_vic([])
    elif game_state.game_started and game_state.board.overlay.is_bless_notif():
        game_state.board.overlay.toggle_blessing_notification(None)
    elif game_state.game_started and game_state.board.overlay.is_constr_notif():
        game_state.board.overlay.toggle_construction_notification(None)
    elif game_state.game_started and game_state.board.overlay.is_lvl_notif():
        game_state.board.overlay.toggle_level_up_notification(None)
    elif game_state.game_started and game_state.board.overlay.is_controls():
        game_state.board.overlay.toggle_controls()
    elif game_state.game_started and game_state.board.overlay.is_investigation():
        game_state.board.overlay.toggle_investigation(None)
    elif game_state.game_started and game_state.board.overlay.can_iter_settlements_units() and \
            len(game_state.players[0].units) > 0:
        game_state.board.overlay.remove_warning_if_possible()
        if game_state.board.overlay.is_setl():
            game_state.board.selected_settlement = None
            game_state.board.overlay.toggle_settlement(None, game_state.players[0])
        if game_state.board.selected_unit is None or isinstance(game_state.board.selected_unit, Heathen):
            game_state.board.selected_unit = game_state.players[0].units[0]
            game_state.board.overlay.toggle_unit(game_state.players[0].units[0])
        elif len(game_state.players[0].units) > 1:
            current_idx = game_state.players[0].units.index(game_state.board.selected_unit)
            new_idx = 0
            if current_idx != len(game_state.players[0].units) - 1:
                new_idx = current_idx + 1
            game_state.board.selected_unit = game_state.players[0].units[new_idx]
            game_state.board.overlay.update_unit(game_state.players[0].units[new_idx])
        game_state.map_pos = (clamp(game_state.board.selected_unit.location[0] - 12, -1, 77),
                              clamp(game_state.board.selected_unit.location[1] - 11, -1, 69))


def on_key_s(game_state: GameState):
    """
    Handles an S key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started and game_state.board.selected_unit is not None and \
            game_state.board.selected_unit.plan.can_settle:
        # Units that can settle can found new settlements when S is pressed.
        game_state.board.handle_new_settlement(game_state.players[0])


def on_key_n(game_controller: GameController, game_state: GameState):
    """
    Handles an N key event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    """
    if game_state.game_started:
        game_controller.music_player.next_song()


def on_key_a(game_state: GameState):
    """
    Handles an A key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started and game_state.board.overlay.is_setl() and \
            game_state.board.selected_settlement.current_work is None:
        # Pressing the A key while a player settlement with no active construction is selected results in the
        # selection being made automatically (in much the same way that AI settlements have their constructions
        # selected).
        set_player_construction(game_state.players[0], game_state.board.selected_settlement,
                                game_state.nighttime_left > 0)


def on_key_escape(game_state: GameState):
    """
    Handles an ESC key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started and not game_state.board.overlay.is_victory() \
            and not game_state.board.overlay.is_elimination():
        # Show the pause menu if there are no intrusive overlays being shown.
        if not game_state.board.overlay.showing or all(overlay in (OverlayType.ATTACK,
                                                                   OverlayType.SETL_ATTACK,
                                                                   OverlayType.SIEGE_NOTIF,
                                                                   OverlayType.HEAL)
                                                       for overlay in game_state.board.overlay.showing):
            game_state.board.overlay.toggle_pause()
        # Remove one overlay layer per ESCAPE press, assuming it is a layer that can be removed.
        elif not game_state.board.overlay.is_tutorial() and not game_state.board.overlay.is_deployment():
            to_reset: typing.Optional[OverlayType] = game_state.board.overlay.remove_layer()
            # Make sure we reset board selections if necessary.
            if to_reset == OverlayType.UNIT:
                game_state.board.selected_unit = None
            elif to_reset == OverlayType.SETTLEMENT:
                game_state.board.selected_settlement = None


def on_key_b(game_state: GameState):
    """
    Handles a B key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started and game_state.board.selected_settlement is not None and \
            game_state.board.selected_settlement.current_work is not None and \
            game_state.players[0].faction is not Faction.FUNDAMENTALISTS and \
            not isinstance(game_state.board.selected_settlement.current_work.construction, Project):
        # Pressing B will buyout the remaining cost of the settlement's current construction. However, players
        # using the Fundamentalists faction are barred from this.
        current_work = game_state.board.selected_settlement.current_work
        remaining_work = current_work.construction.cost - current_work.zeal_consumed
        if game_state.players[0].wealth >= remaining_work:
            game_state.board.overlay.toggle_construction_notification([
                CompletedConstruction(game_state.board.selected_settlement.current_work.construction,
                                      game_state.board.selected_settlement)
            ])
            complete_construction(game_state.board.selected_settlement, game_state.players[0])
            game_state.players[0].wealth -= remaining_work


def on_key_m(game_state: GameState):
    """
    Handles an M key event in the game loop.
    :param game_state: The current GameState object.
    """
    units = game_state.players[0].units
    filtered_units = [unit for unit in units if not unit.besieging and unit.remaining_stamina > 0]

    if game_state.game_started and game_state.board.overlay.can_iter_settlements_units() and \
            len(filtered_units) > 0:
        game_state.board.overlay.remove_warning_if_possible()
        if game_state.board.overlay.is_setl():
            game_state.board.selected_settlement = None
            game_state.board.overlay.toggle_settlement(None, game_state.players[0])
        if game_state.board.selected_unit is None or isinstance(game_state.board.selected_unit, Heathen):
            game_state.board.selected_unit = filtered_units[0]
            game_state.board.overlay.toggle_unit(filtered_units[0])
        else:
            current_selected_unit = game_state.board.selected_unit
            new_idx = 0

            if current_selected_unit in filtered_units and \
                    filtered_units.index(current_selected_unit) != len(filtered_units) - 1:
                new_idx = filtered_units.index(current_selected_unit) + 1

            game_state.board.selected_unit = filtered_units[new_idx]
            game_state.board.overlay.update_unit(filtered_units[new_idx])

        game_state.map_pos = (clamp(game_state.board.selected_unit.location[0] - 12, -1, 77),
                              clamp(game_state.board.selected_unit.location[1] - 11, -1, 69))


def on_key_j(game_state: GameState):
    """
    Handles a J key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started and game_state.board.overlay.can_jump_to_setl():
        # Pressing the J key will jump to an idle settlement, if such a settlement exists.
        idle_settlements = [setl for setl in game_state.players[0].settlements if setl.current_work is None]
        if idle_settlements:
            if game_state.board.selected_settlement is None:
                game_state.board.selected_settlement = idle_settlements[0]
                game_state.board.overlay.toggle_settlement(game_state.board.selected_settlement, game_state.players[0])
            elif game_state.board.selected_settlement not in idle_settlements:
                # If the player has currently selected another non-idle settlement, when they press the J key,
                # bring them back to the first idle settlement.
                game_state.board.selected_settlement = idle_settlements[0]
                game_state.board.overlay.update_settlement(game_state.board.selected_settlement)
            elif len(idle_settlements) > 1:
                current_idx = idle_settlements.index(game_state.board.selected_settlement)
                new_idx = 0
                if current_idx != len(idle_settlements) - 1:
                    new_idx = current_idx + 1
                game_state.board.selected_settlement = idle_settlements[new_idx]
                game_state.board.overlay.update_settlement(idle_settlements[new_idx])
            game_state.map_pos = (clamp(game_state.board.selected_settlement.location[0] - 12, -1, 77),
                                  clamp(game_state.board.selected_settlement.location[1] - 11, -1, 69))


def on_mouse_button_right(game_state: GameState):
    """
    Handles a right mouse button click event in the game loop.
    Mouse clicks are forwarded to the Board for processing.
    :param game_state: The current GameState object.
    """
    if game_state.game_started:
        game_state.board.overlay.remove_warning_if_possible()
        game_state.board.process_right_click(pyxel.mouse_x, pyxel.mouse_y, game_state.map_pos)


def on_mouse_button_left(game_state: GameState):
    """
    Handles a left mouse button click event in the game loop.
    Mouse clicks are forwarded to the Board for processing.
    :param game_state: The current GameState object.
    """
    if game_state.game_started:
        all_units = []
        for player in game_state.players:
            for unit in player.units:
                all_units.append(unit)

        other_setls = []
        for i in range(1, len(game_state.players)):
            other_setls.extend(game_state.players[i].settlements)
        game_state.board.overlay.remove_warning_if_possible()
        game_state.board.process_left_click(pyxel.mouse_x, pyxel.mouse_y,
                                            len(game_state.players[0].settlements) > 0,
                                            game_state.players[0], game_state.map_pos, game_state.heathens,
                                            all_units,
                                            game_state.players, other_setls)
