import random
import time
import typing
from copy import deepcopy

import pyxel

from source.display.board import Board
from source.networking.client import dispatch_event, get_identifier
from source.networking.events import CreateEvent, EventType, QueryEvent, LeaveEvent, JoinEvent, InitEvent, \
    SetConstructionEvent, UpdateAction, SetBlessingEvent, BesiegeSettlementEvent, BuyoutConstructionEvent, \
    DisbandUnitEvent, AttackSettlementEvent, EndTurnEvent, UnreadyEvent, AutofillEvent, SaveEvent, QuerySavesEvent, \
    LoadEvent
from source.util.calculator import clamp, complete_construction, attack_setl, player_has_resources_for_improvement, \
    subtract_player_resources_for_improvement, update_player_quads_seen_around_point
from source.foundation.catalogue import get_available_improvements, get_available_blessings, get_available_unit_plans, \
    PROJECTS, FACTION_COLOURS
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.display.menu import MainMenuOption, SetupOption, WikiOption
from source.foundation.models import Construction, OngoingBlessing, CompletedConstruction, Heathen, GameConfig, \
    OverlayType, Faction, ConstructionMenu, Project, DeployerUnit, StandardOverlayView, Improvement, LobbyDetails, \
    PlayerDetails
from source.game_management.movemaker import set_player_construction
from source.display.overlay import SettlementAttackType, PauseOption
from source.saving.game_save_manager import load_game, get_saves, save_game, save_stats_achievements, get_stats


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
        elif game_state.board.overlay.is_unit() and game_state.board.overlay.show_unit_passengers:
            game_state.board.overlay.navigate_unit(down=True)
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
            game_state.board.overlay.navigate_standard(up=True)
        elif game_state.board.overlay.is_unit() and game_state.board.overlay.show_unit_passengers:
            game_state.board.overlay.navigate_unit(down=False)
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
        if game_controller.menu.loading_game:
            game_controller.menu.saves = get_saves()
    elif game_state.game_started:
        if game_state.board.overlay.is_constructing():
            if game_state.board.overlay.current_construction_menu is ConstructionMenu.PROJECTS and \
                    len(game_state.board.overlay.available_constructions) > 0:
                game_state.board.overlay.current_construction_menu = ConstructionMenu.IMPROVEMENTS
                game_state.board.overlay.selected_construction = game_state.board.overlay.available_constructions[0]
                game_state.board.overlay.construction_boundaries = 0, 5
            elif game_state.board.overlay.current_construction_menu is ConstructionMenu.UNITS:
                game_state.board.overlay.current_construction_menu = ConstructionMenu.PROJECTS
                game_state.board.overlay.selected_construction = game_state.board.overlay.available_projects[0]
        elif game_state.board.overlay.is_standard() and not game_state.board.overlay.is_blessing():
            game_state.board.overlay.navigate_standard(left=True)
        elif game_state.board.overlay.is_setl_click():
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
        if game_controller.menu.loading_game and game_controller.menu.upnp_enabled:
            qs_evt: QuerySavesEvent = QuerySavesEvent(EventType.QUERY_SAVES, get_identifier())
            dispatch_event(qs_evt)
    elif game_state.game_started:
        if game_state.board.overlay.is_constructing():
            if game_state.board.overlay.current_construction_menu is ConstructionMenu.IMPROVEMENTS:
                game_state.board.overlay.current_construction_menu = ConstructionMenu.PROJECTS
                game_state.board.overlay.selected_construction = game_state.board.overlay.available_projects[0]
            elif game_state.board.overlay.current_construction_menu is ConstructionMenu.PROJECTS:
                game_state.board.overlay.current_construction_menu = ConstructionMenu.UNITS
                game_state.board.overlay.selected_construction = game_state.board.overlay.available_unit_plans[0]
                game_state.board.overlay.unit_plan_boundaries = 0, 5
        elif game_state.board.overlay.is_standard() and not game_state.board.overlay.is_blessing():
            game_state.board.overlay.navigate_standard(right=True)
        elif game_state.board.overlay.is_setl_click():
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
        if (game_controller.menu.in_game_setup or game_controller.menu.multiplayer_lobby) and \
                game_controller.menu.setup_option is SetupOption.START_GAME:
            if game_controller.menu.multiplayer_enabled and not game_controller.menu.multiplayer_lobby:
                game_state.reset_state()
                lobby_create_event: CreateEvent = CreateEvent(EventType.CREATE, get_identifier(),
                                                              game_controller.menu.get_game_config())
                dispatch_event(lobby_create_event)
            else:
                if game_controller.menu.multiplayer_lobby:
                    if len(game_controller.menu.multiplayer_lobby.current_players) > 1:
                        game_init_event: InitEvent = InitEvent(EventType.INIT, get_identifier(),
                                                               game_controller.menu.multiplayer_lobby.name)
                        dispatch_event(game_init_event)
                else:
                    # If the player has pressed enter to start the game, generate the players, board, and AI players.
                    pyxel.mouse(visible=True)
                    game_controller.last_turn_time = time.time()
                    game_state.player_idx = 0
                    game_state.located_player_idx = True
                    game_state.game_started = True
                    game_state.turn = 1
                    # Reinitialise night variables.
                    random.seed()
                    game_state.until_night = random.randint(10, 20)
                    game_state.nighttime_left = 0
                    game_state.on_menu = False
                    cfg: GameConfig = game_controller.menu.get_game_config()
                    # Update stats to include the newly-selected faction.
                    save_stats_achievements(game_state, faction_to_add=cfg.player_faction)
                    game_state.gen_players(cfg)
                    game_state.board = Board(cfg, game_controller.namer)
                    game_controller.move_maker.board_ref = game_state.board
                    game_state.board.overlay.toggle_tutorial()
                    game_controller.namer.reset()
                    game_state.initialise_ais(game_controller.namer)
                    game_state.board.overlay.total_settlement_count = \
                        sum(len(p.settlements) for p in game_state.players) + 1
                    game_controller.music_player.stop_menu_music()
                    game_controller.music_player.play_game_music()
        elif game_controller.menu.loading_game:
            if game_controller.menu.loading_multiplayer_game:
                save_name: str = game_controller.menu.saves[game_controller.menu.save_idx]
                # We need to convert the save name back to the file name before we send it to the server.
                if save_name.endswith("(auto)"):
                    save_name = "autosave-" + save_name[:-7].replace(" ", "T") + ".json"
                else:
                    save_name = "save-" + save_name.replace(" ", "T") + ".json"
                l_evt: LoadEvent = LoadEvent(EventType.LOAD, get_identifier(), save_name)
                dispatch_event(l_evt)
            else:
                load_game(game_state, game_controller)
        elif game_controller.menu.joining_game and not game_controller.menu.showing_faction_details:
            menu = game_controller.menu
            lobby_join_event: JoinEvent = JoinEvent(EventType.JOIN, get_identifier(),
                                                    menu.multiplayer_lobbies[menu.lobby_index].name,
                                                    menu.available_multiplayer_factions[menu.faction_idx][0])
            dispatch_event(lobby_join_event)
            # Normally we would make changes to the game state or controller in the event listener, but because multiple
            # packets are sent back to the client when joining a game, we can't reset the namer in there, otherwise it
            # would be reset every time a new packet is received.
            game_controller.namer.reset()
        elif game_controller.menu.viewing_lobbies:
            current_lobby: LobbyDetails = game_controller.menu.multiplayer_lobbies[game_controller.menu.lobby_index]
            human_players: typing.List[PlayerDetails] = [p for p in current_lobby.current_players if p.id]
            if len(human_players) < current_lobby.cfg.player_count:
                # If the game is in progress, then the player can join as any faction that is currently played by an AI
                # player.
                if current_lobby.current_turn:
                    game_controller.menu.available_multiplayer_factions = \
                        [(Faction(p.faction), FACTION_COLOURS[p.faction])
                         for p in current_lobby.current_players if not p.id]
                # If the game hasn't started yet, however, the player can join as any faction that is not currently
                # chosen in the lobby.
                else:
                    available_factions = deepcopy(FACTION_COLOURS)
                    for player in current_lobby.current_players:
                        if player.id:
                            available_factions.pop(player.faction)
                    game_controller.menu.available_multiplayer_factions = list(available_factions.items())
                game_controller.menu.joining_game = True
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
                    game_controller.menu.saves = get_saves()
                case MainMenuOption.JOIN_GAME:
                    lobbies_query_event: QueryEvent = QueryEvent(EventType.QUERY, get_identifier())
                    dispatch_event(lobbies_query_event)
                case MainMenuOption.STATISTICS:
                    game_controller.menu.viewing_stats = True
                    game_controller.menu.player_stats = get_stats()
                case MainMenuOption.ACHIEVEMENTS:
                    game_controller.menu.viewing_achievements = True
                    game_controller.menu.player_stats = get_stats()
                case MainMenuOption.WIKI:
                    game_controller.menu.in_wiki = True
                case MainMenuOption.EXIT:
                    pyxel.quit()
    elif game_state.game_started and game_state.board.overlay.is_desync():
        menu = game_controller.menu
        # We don't need to check whether the current game is a multiplayer game since desync can only occur in
        # multiplayer games.
        lobby_join_event: JoinEvent = JoinEvent(EventType.JOIN, get_identifier(), menu.multiplayer_lobby.name,
                                                game_state.players[game_state.player_idx].faction)
        dispatch_event(lobby_join_event)
        # We only need to do limited resetting of game state since we'll be rejoining the game immediately.
        game_state.game_started = False
        game_state.on_menu = True
        game_state.reset_state()
        # Normally we would make changes to the game state or controller in the event listener, but because multiple
        # packets are sent back to the client when joining a game, we can't reset the namer in there, otherwise it
        # would be reset every time a new packet is received.
        game_controller.namer.reset()
        # Technically this does mean that the menu music only plays for a very short time while the player is rejoining,
        # but I found that it sounded better than just leaving the game music playing.
        game_controller.music_player.stop_game_music()
        game_controller.music_player.play_menu_music()
    elif game_state.game_started and not game_state.board.overlay.is_ach_notif() and \
            (game_state.board.overlay.is_victory() or
             game_state.board.overlay.is_elimination() and game_state.players[game_state.player_idx].eliminated):
        # If the game was a multiplayer one, then dispatch a leave event so that the server knows that this client is no
        # longer in the game. Once all players have returned to the main menu, the server will tear down all game state.
        if game_state.board.game_config.multiplayer:
            leave_lobby_event: LeaveEvent = LeaveEvent(EventType.LEAVE, get_identifier(),
                                                       game_controller.menu.multiplayer_lobby.name)
            dispatch_event(leave_lobby_event)
        # If the player has won the game, or they've just been eliminated themselves, enter will take them back
        # to the menu.
        game_state.game_started = False
        game_state.on_menu = True
        game_state.reset_state()
        game_controller.menu.loading_game = False
        game_controller.menu.loading_multiplayer_game = False
        game_controller.menu.in_game_setup = False
        game_controller.menu.multiplayer_lobby = None
        game_controller.menu.joining_game = False
        game_controller.menu.viewing_lobbies = False
        game_controller.menu.faction_idx = 0
        game_controller.menu.main_menu_option = MainMenuOption.NEW_GAME
        game_controller.music_player.stop_game_music()
        game_controller.music_player.play_menu_music()
    # If the player is choosing a blessing or construction, enter will select it.
    elif game_state.game_started and game_state.board.overlay.is_constructing():
        cons = game_state.board.overlay.selected_construction
        # If the selected construction is an improvement with required resources that the player does not have, pressing
        # the enter key will do nothing.
        if cons is not None and \
                not (isinstance(cons, Improvement) and
                     not player_has_resources_for_improvement(game_state.players[game_state.player_idx], cons)):
            if isinstance(cons, Improvement) and cons.req_resources:
                subtract_player_resources_for_improvement(game_state.players[game_state.player_idx], cons)
            game_state.board.selected_settlement.current_work = \
                Construction(game_state.board.overlay.selected_construction)
            # If we're in a multiplayer game, alert the server, which will alert other players.
            if game_state.board.game_config.multiplayer:
                sc_evt = SetConstructionEvent(EventType.UPDATE, get_identifier(),
                                              UpdateAction.SET_CONSTRUCTION, game_state.board.game_name,
                                              game_state.players[game_state.player_idx].faction,
                                              game_state.players[game_state.player_idx].resources,
                                              game_state.board.selected_settlement.name,
                                              game_state.board.selected_settlement.current_work)
                dispatch_event(sc_evt)
        if cons is None or game_state.board.selected_settlement.current_work is not None:
            game_state.board.overlay.toggle_construction([], [], [])
    elif game_state.game_started and game_state.board.overlay.is_blessing():
        if game_state.board.overlay.selected_blessing is not None:
            game_state.players[game_state.player_idx].ongoing_blessing = \
                OngoingBlessing(game_state.board.overlay.selected_blessing)
            # If we're in a multiplayer game, alert the server, which will alert other players.
            if game_state.board.game_config.multiplayer:
                sb_evt = SetBlessingEvent(EventType.UPDATE, get_identifier(), UpdateAction.SET_BLESSING,
                                          game_state.board.game_name, game_state.players[game_state.player_idx].faction,
                                          game_state.players[game_state.player_idx].ongoing_blessing)
                dispatch_event(sb_evt)
        game_state.board.overlay.toggle_blessing([])
    elif game_state.game_started and game_state.board.overlay.is_setl_click():
        match game_state.board.overlay.setl_attack_opt:
            # If the player has chosen to attack a settlement, execute the attack.
            case SettlementAttackType.ATTACK:
                game_state.board.overlay.toggle_setl_click(None, None)
                data = attack_setl(game_state.board.selected_unit, game_state.board.overlay.attacked_settlement,
                                   game_state.board.overlay.attacked_settlement_owner, False)
                # If we're in a multiplayer game, alert the server, which will alert other players.
                if game_state.board.game_config.multiplayer:
                    as_evt: AttackSettlementEvent = \
                        AttackSettlementEvent(EventType.UPDATE, get_identifier(), UpdateAction.ATTACK_SETTLEMENT,
                                              game_state.board.game_name,
                                              game_state.players[game_state.player_idx].faction,
                                              game_state.board.selected_unit.location,
                                              game_state.board.overlay.attacked_settlement.name)
                    dispatch_event(as_evt)
                if data.attacker_was_killed:
                    # If the player's unit died, destroy and deselect it.
                    game_state.players[game_state.player_idx].units.remove(game_state.board.selected_unit)
                    game_state.board.selected_unit = None
                    game_state.board.overlay.toggle_unit(None)
                elif data.setl_was_taken:
                    # If the settlement was taken, transfer it to the player, while also marking any units that
                    # were involved in the siege as no longer besieging.
                    data.settlement.besieged = False
                    for unit in game_state.players[game_state.player_idx].units:
                        for setl_quad in data.settlement.quads:
                            if abs(unit.location[0] - setl_quad.location[0]) <= 1 and \
                                    abs(unit.location[1] - setl_quad.location[1]) <= 1:
                                unit.besieging = False
                                break
                    # The Concentrated can only have a single settlement, so when they take others, the
                    # settlements simply disappear.
                    if game_state.players[game_state.player_idx].faction != Faction.CONCENTRATED:
                        game_state.players[game_state.player_idx].settlements.append(data.settlement)
                        update_player_quads_seen_around_point(game_state.players[game_state.player_idx],
                                                              data.settlement.location)
                    for idx, p in enumerate(game_state.players):
                        if data.settlement in p.settlements and idx != game_state.player_idx:
                            p.settlements.remove(data.settlement)
                            break
                game_state.board.overlay.toggle_setl_attack(data)
                game_state.board.attack_time_bank = 0
            case SettlementAttackType.BESIEGE:
                # Alternatively, begin a siege on the settlement.
                game_state.board.selected_unit.besieging = True
                game_state.board.overlay.attacked_settlement.besieged = True
                # If we're in a multiplayer game, alert the server, which will alert other players.
                if game_state.board.game_config.multiplayer:
                    bs_evt: BesiegeSettlementEvent = \
                        BesiegeSettlementEvent(EventType.UPDATE, get_identifier(), UpdateAction.BESIEGE_SETTLEMENT,
                                               game_state.board.game_name,
                                               game_state.players[game_state.player_idx].faction,
                                               game_state.board.selected_unit.location,
                                               game_state.board.overlay.attacked_settlement.name)
                    dispatch_event(bs_evt)
                game_state.board.overlay.toggle_setl_click(None, None)
            case _:
                game_state.board.overlay.toggle_setl_click(None, None)
    elif game_state.game_started and game_state.board.overlay.is_pause():
        match game_state.board.overlay.pause_option:
            case PauseOption.RESUME:
                game_state.board.overlay.toggle_pause()
            case PauseOption.SAVE:
                # Saving multiplayer games doesn't actually save a copy locally - rather it tells the server to save a
                # copy.
                if game_state.board.game_config.multiplayer:
                    s_evt: SaveEvent = SaveEvent(EventType.SAVE, get_identifier(), game_state.board.game_name)
                    dispatch_event(s_evt)
                else:
                    save_game(game_state)
                game_state.board.overlay.has_saved = True
            case PauseOption.CONTROLS:
                game_state.board.overlay.show_additional_controls = False
                game_state.board.overlay.toggle_controls()
            case PauseOption.QUIT:
                # If we're in a multiplayer game, alert the server, which will alert other players.
                if game_state.board.game_config.multiplayer:
                    leave_lobby_event: LeaveEvent = LeaveEvent(EventType.LEAVE, get_identifier(),
                                                               game_controller.menu.multiplayer_lobby.name)
                    dispatch_event(leave_lobby_event)
                game_state.game_started = False
                game_state.on_menu = True
                game_state.reset_state()
                game_controller.menu.loading_game = False
                game_controller.menu.loading_multiplayer_game = False
                game_controller.menu.in_game_setup = False
                game_controller.menu.multiplayer_lobby = None
                game_controller.menu.joining_game = False
                game_controller.menu.viewing_lobbies = False
                game_controller.menu.faction_idx = 0
                game_controller.menu.main_menu_option = MainMenuOption.NEW_GAME
                game_controller.music_player.stop_game_music()
                game_controller.music_player.play_menu_music()
    elif game_state.game_started and game_state.board.overlay.is_unit() and \
            game_state.board.overlay.show_unit_passengers:
        game_state.board.deploying_army_from_unit = True
        game_state.board.overlay.toggle_deployment()
    elif game_state.game_started and not (
            game_state.board.overlay.is_tutorial() or game_state.board.overlay.is_deployment() or
            game_state.board.overlay.is_bless_notif() or
            game_state.board.overlay.is_constr_notif() or game_state.board.overlay.is_lvl_notif() or
            game_state.board.overlay.is_close_to_vic() or
            game_state.board.overlay.is_investigation() or game_state.board.overlay.is_night() or
            game_state.board.overlay.is_ach_notif() or game_state.board.overlay.is_elimination()):
        # Multiplayer games don't just end the turn straight away, since we need to wait for all players to be ready.
        if game_state.board.game_config.multiplayer:
            # The player can't end a turn while the previous one is still being processed.
            if not game_state.processing_turn and not game_state.check_for_warnings():
                game_state.board.waiting_for_other_players = not game_state.board.waiting_for_other_players
                # Depending on whether the player has ended their turn, or they're retracting their readiness, send a
                # different event to the server.
                if game_state.board.waiting_for_other_players:
                    et_evt: EndTurnEvent = EndTurnEvent(EventType.END_TURN, get_identifier(),
                                                        game_state.board.game_name)
                    dispatch_event(et_evt)
                else:
                    u_evt: UnreadyEvent = UnreadyEvent(EventType.UNREADY, get_identifier(), game_state.board.game_name)
                    dispatch_event(u_evt)
        # If we are not in any of the above situations, end the turn.
        elif game_state.end_turn():
            # Autosave every turn, but only if the player is actually still in the game.
            if game_state.players[game_state.player_idx].settlements:
                save_game(game_state, auto=True)
            # Update the playtime statistic and check if any achievements have been obtained.
            time_elapsed = time.time() - game_controller.last_turn_time
            game_controller.last_turn_time = time.time()
            if new_achs := save_stats_achievements(game_state, time_elapsed):
                game_state.board.overlay.toggle_ach_notif(new_achs)

            game_state.board.overlay.total_settlement_count = sum(len(p.settlements) for p in game_state.players)
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
        game_state.board.overlay.toggle_standard()


def on_key_c(game_state: GameState):
    """
    Handles a C key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started and game_state.board.selected_settlement is not None:
        # Pick a construction.
        game_state.board.overlay.toggle_construction(
            get_available_improvements(game_state.players[game_state.player_idx],
                                       game_state.board.selected_settlement),
            PROJECTS,
            get_available_unit_plans(game_state.players[game_state.player_idx], game_state.board.selected_settlement))


def on_key_f(game_controller: GameController, game_state: GameState):
    """
    Handles an F key event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    """
    if game_state.on_menu and ((game_controller.menu.in_game_setup and
                                game_controller.menu.setup_option is SetupOption.PLAYER_FACTION)
                               or game_controller.menu.joining_game):
        game_controller.menu.showing_faction_details = not game_controller.menu.showing_faction_details
    elif game_state.game_started and game_state.board.overlay.is_standard() \
            and game_state.board.overlay.current_standard_overlay_view is StandardOverlayView.BLESSINGS:
        # Pick a blessing.
        game_state.board.overlay.toggle_blessing(get_available_blessings(game_state.players[game_state.player_idx]))


def on_key_d(game_state: GameState):
    """
    Handles a D key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started and game_state.board.selected_settlement is not None and \
            len(game_state.board.selected_settlement.garrison) > 0:
        game_state.board.deploying_army = not game_state.board.deploying_army
        game_state.board.overlay.toggle_deployment()
    elif game_state.game_started and game_state.board.selected_unit is not None and \
            game_state.board.selected_unit in game_state.players[game_state.player_idx].units and \
            isinstance(game_state.board.selected_unit, DeployerUnit) and \
            len(game_state.board.selected_unit.passengers) > 0:
        game_state.board.overlay.show_unit_passengers = not game_state.board.overlay.show_unit_passengers


def on_key_tab(game_state: GameState):
    """
    Handles a Tab key event in the game loop.
    :param game_state: The current GameState object.
    """
    # Pressing tab iterates through the player's settlements, centring on each one.
    if game_state.game_started and game_state.board.overlay.can_iter_settlements_units() and \
            len(game_state.players[game_state.player_idx].settlements) > 0:
        game_state.board.overlay.remove_warning_if_possible()
        if game_state.board.overlay.is_unit():
            game_state.board.selected_unit = None
            game_state.board.overlay.toggle_unit(None)
        if game_state.board.selected_settlement is None:
            game_state.board.selected_settlement = game_state.players[game_state.player_idx].settlements[0]
            game_state.board.overlay.toggle_settlement(game_state.players[game_state.player_idx].settlements[0],
                                                       game_state.players[game_state.player_idx])
        elif len(game_state.players[game_state.player_idx].settlements) > 1:
            current_idx = \
                game_state.players[game_state.player_idx].settlements.index(game_state.board.selected_settlement)
            new_idx = 0
            if current_idx != len(game_state.players[game_state.player_idx].settlements) - 1:
                new_idx = current_idx + 1
            game_state.board.selected_settlement = game_state.players[game_state.player_idx].settlements[new_idx]
            game_state.board.overlay.update_settlement(game_state.players[game_state.player_idx].settlements[new_idx])
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
    # If we're in a multiplayer lobby, alert the server, which will alert other players.
    if game_state.on_menu and game_controller.menu.multiplayer_lobby:
        leave_lobby_event: LeaveEvent = LeaveEvent(EventType.LEAVE, get_identifier(),
                                                   game_controller.menu.multiplayer_lobby.name)
        dispatch_event(leave_lobby_event)
        game_controller.menu.multiplayer_lobby = None
        game_state.reset_state()
    elif game_state.on_menu and game_controller.menu.in_game_setup:
        game_controller.menu.in_game_setup = False
    if game_state.on_menu and game_controller.menu.loading_game and game_controller.menu.load_failed:
        game_controller.menu.load_failed = False
    elif game_state.on_menu and game_controller.menu.loading_game:
        game_controller.menu.loading_game = False
        game_controller.menu.loading_multiplayer_game = False
    elif game_state.on_menu and game_controller.menu.joining_game:
        game_controller.menu.joining_game = False
        if game_controller.menu.loading_multiplayer_game:
            game_controller.menu.loading_game = True
    elif game_state.on_menu and game_controller.menu.viewing_lobbies:
        game_controller.menu.viewing_lobbies = False
    elif game_state.on_menu and game_controller.menu.viewing_stats:
        game_controller.menu.viewing_stats = False
    elif game_state.on_menu and game_controller.menu.viewing_achievements:
        game_controller.menu.viewing_achievements = False
    # You should only be able to toggle the elimination overlay if you're actually still in the game.
    if game_state.game_started and \
            game_state.board.overlay.is_elimination() and \
            not game_state.players[game_state.player_idx].eliminated:
        game_state.board.overlay.toggle_elimination(None)
    elif game_state.game_started and game_state.board.overlay.is_ach_notif():
        game_state.board.overlay.toggle_ach_notif([])
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
            len(game_state.players[game_state.player_idx].units) > 0:
        game_state.board.overlay.remove_warning_if_possible()
        if game_state.board.overlay.is_setl():
            game_state.board.selected_settlement = None
            game_state.board.overlay.toggle_settlement(None, game_state.players[game_state.player_idx])
        if game_state.board.selected_unit is None or isinstance(game_state.board.selected_unit, Heathen):
            game_state.board.selected_unit = game_state.players[game_state.player_idx].units[0]
            game_state.board.overlay.toggle_unit(game_state.players[game_state.player_idx].units[0])
        elif len(game_state.players[game_state.player_idx].units) > 1:
            current_idx = game_state.players[game_state.player_idx].units.index(game_state.board.selected_unit)
            new_idx = 0
            if current_idx != len(game_state.players[game_state.player_idx].units) - 1:
                new_idx = current_idx + 1
            game_state.board.selected_unit = game_state.players[game_state.player_idx].units[new_idx]
            game_state.board.overlay.update_unit(game_state.players[game_state.player_idx].units[new_idx])
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
        game_state.board.handle_new_settlement(game_state.players[game_state.player_idx])


def on_key_n(game_controller: GameController, game_state: GameState):
    """
    Handles an N key event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    """
    if game_state.game_started:
        game_controller.music_player.next_song()


def on_key_a(game_controller: GameController, game_state: GameState):
    """
    Handles an A key event in the game loop.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    """
    if game_state.on_menu and (lob := game_controller.menu.multiplayer_lobby):
        # Pressing the A key while in a multiplayer lobby will fill the lobby with AI players, provided that the lobby
        # isn't already full.
        if len(lob.current_players) < lob.cfg.player_count:
            af_evt: AutofillEvent = AutofillEvent(EventType.AUTOFILL, get_identifier(), lob.name)
            dispatch_event(af_evt)
    elif game_state.game_started and game_state.board.overlay.is_setl() and \
            game_state.board.selected_settlement.current_work is None:
        # Pressing the A key while a player settlement with no active construction is selected results in the
        # selection being made automatically (in much the same way that AI settlements have their constructions
        # selected).
        set_player_construction(game_state.players[game_state.player_idx], game_state.board.selected_settlement,
                                game_state.nighttime_left > 0)
        # If we're in a multiplayer game, alert the server, which will alert other players.
        if game_state.board.game_config.multiplayer:
            sc_evt = SetConstructionEvent(EventType.UPDATE, get_identifier(), UpdateAction.SET_CONSTRUCTION,
                                          game_state.board.game_name, game_state.players[game_state.player_idx].faction,
                                          game_state.players[game_state.player_idx].resources,
                                          game_state.board.selected_settlement.name,
                                          game_state.board.selected_settlement.current_work)
            dispatch_event(sc_evt)


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
            game_state.players[game_state.player_idx].faction != Faction.FUNDAMENTALISTS and \
            not isinstance(game_state.board.selected_settlement.current_work.construction, Project):
        # Pressing B will buyout the remaining cost of the settlement's current construction. However, players
        # using the Fundamentalists faction are barred from this.
        current_work = game_state.board.selected_settlement.current_work
        remaining_work = current_work.construction.cost - current_work.zeal_consumed
        if game_state.players[game_state.player_idx].wealth >= remaining_work:
            game_state.board.overlay.toggle_construction_notification([
                CompletedConstruction(game_state.board.selected_settlement.current_work.construction,
                                      game_state.board.selected_settlement)
            ])
            complete_construction(game_state.board.selected_settlement, game_state.players[game_state.player_idx])
            game_state.players[game_state.player_idx].wealth -= remaining_work
            # If we're in a multiplayer game, alert the server, which will alert other players.
            if game_state.board.game_config.multiplayer:
                bc_evt: BuyoutConstructionEvent = \
                    BuyoutConstructionEvent(EventType.UPDATE, get_identifier(), UpdateAction.BUYOUT_CONSTRUCTION,
                                            game_state.board.game_name,
                                            game_state.players[game_state.player_idx].faction,
                                            game_state.board.selected_settlement.name,
                                            game_state.players[game_state.player_idx].wealth)
                dispatch_event(bc_evt)


def on_key_m(game_state: GameState):
    """
    Handles an M key event in the game loop.
    :param game_state: The current GameState object.
    """
    units = game_state.players[game_state.player_idx].units
    filtered_units = [unit for unit in units if not unit.besieging and unit.remaining_stamina > 0]

    if game_state.game_started and game_state.board.overlay.can_iter_settlements_units() and \
            len(filtered_units) > 0:
        game_state.board.overlay.remove_warning_if_possible()
        if game_state.board.overlay.is_setl():
            game_state.board.selected_settlement = None
            game_state.board.overlay.toggle_settlement(None, game_state.players[game_state.player_idx])
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
        game_state.board.overlay.remove_warning_if_possible()
        # Pressing the J key will jump to an idle settlement, if such a settlement exists.
        idle_settlements = [setl for setl in game_state.players[game_state.player_idx].settlements
                            if setl.current_work is None]
        if idle_settlements:
            if game_state.board.overlay.is_unit():
                game_state.board.selected_unit = None
                game_state.board.overlay.toggle_unit(None)
            if game_state.board.selected_settlement is None:
                game_state.board.selected_settlement = idle_settlements[0]
                game_state.board.overlay.toggle_settlement(game_state.board.selected_settlement,
                                                           game_state.players[game_state.player_idx])
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
        for i in range(len(game_state.players)):
            if i != game_state.player_idx:
                other_setls.extend(game_state.players[i].settlements)
        game_state.board.overlay.remove_warning_if_possible()
        game_state.board.process_left_click(pyxel.mouse_x, pyxel.mouse_y,
                                            # The player hasn't 'settled' until they have a settlement. Alternatively,
                                            # if we're later in the game, even if they've just lost their last
                                            # settlement, they're still 'settled' if they're still in the game. This is
                                            # to avoid players with only settler units left being able to click anywhere
                                            # to get a new settlement for free.
                                            (len(game_state.players[game_state.player_idx].settlements) > 0 or
                                             game_state.turn != 1),
                                            game_state.players[game_state.player_idx], game_state.map_pos,
                                            game_state.heathens, all_units, game_state.players, other_setls)


def on_key_x(game_state: GameState):
    """
    Handles an X key event in the game loop.
    :param game_state: The current GameState object.
    """
    if game_state.game_started and game_state.board.selected_unit is not None and \
            game_state.board.selected_unit in game_state.players[game_state.player_idx].units:
        # If a unit is selected, pressing X disbands the army, destroying the unit and adding to the player's wealth.
        game_state.players[game_state.player_idx].wealth += game_state.board.selected_unit.plan.cost
        game_state.players[game_state.player_idx].units.remove(game_state.board.selected_unit)
        # If we're in a multiplayer game, alert the server, which will alert other players.
        if game_state.board.game_config.multiplayer:
            du_evt: DisbandUnitEvent = DisbandUnitEvent(EventType.UPDATE, get_identifier(), UpdateAction.DISBAND_UNIT,
                                                        game_state.board.game_name,
                                                        game_state.players[game_state.player_idx].faction,
                                                        game_state.board.selected_unit.location)
            dispatch_event(du_evt)
        game_state.board.selected_unit = None
        game_state.board.overlay.toggle_unit(None)
