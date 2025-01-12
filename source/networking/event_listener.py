import datetime
import json
import platform
import random
import sched
import socket
import socketserver
import time
from itertools import chain
from site import getsitepackages
from threading import Thread
from typing import Dict, List, Optional, Set, Tuple, Callable

import pyxel
# For Windows clients we need to ensure that the miniupnpc DLL is loaded before attempting to import the module.
if platform.system() == "Windows":
    from ctypes import cdll, CDLL
    # Clients playing via the bundled EXE should already have the DLL loaded, since it's bundled into the EXE itself.
    try:
        CDLL("miniupnpc.dll")
    # However, clients playing from source or via a pip install will need to load the DLL manually.
    except FileNotFoundError:
        site_packages_path: str = next(path for path in getsitepackages() if path.endswith("site-packages"))
        cdll.LoadLibrary(f"{site_packages_path}/microcosm/source/resources/dll/miniupnpc.dll")
# We need to disable a lint rule for the miniupnpc import because it doesn't actually declare UPnP in its module. This
# isn't our fault, so we can just disable the rule.
# pylint: disable=no-name-in-module
from miniupnpc import UPnP

from source.display.board import Board
from source.display.menu import SetupOption
from source.foundation.catalogue import FACTION_COLOURS, LOBBY_NAMES, PLAYER_NAMES, Namer, get_improvement, \
    get_project, get_unit_plan, get_blessing, get_heathen
from source.foundation.models import GameConfig, Player, PlayerDetails, LobbyDetails, Quad, OngoingBlessing, \
    InvestigationResult, Settlement, Unit, Heathen, Faction, AIPlaystyle, AttackPlaystyle, ExpansionPlaystyle, \
    LoadedMultiplayerState, HarvestStatus, EconomicStatus
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.game_management.movemaker import MoveMaker
from source.networking.client import dispatch_event, get_identifier
from source.networking.events import Event, EventType, CreateEvent, InitEvent, UpdateEvent, UpdateAction, \
    FoundSettlementEvent, QueryEvent, LeaveEvent, JoinEvent, RegisterEvent, SetBlessingEvent, SetConstructionEvent, \
    MoveUnitEvent, DeployUnitEvent, GarrisonUnitEvent, InvestigateEvent, BesiegeSettlementEvent, \
    BuyoutConstructionEvent, DisbandUnitEvent, AttackUnitEvent, AttackSettlementEvent, EndTurnEvent, UnreadyEvent, \
    HealUnitEvent, BoardDeployerEvent, DeployerDeployEvent, AutofillEvent, SaveEvent, QuerySavesEvent, LoadEvent
from source.saving.game_save_manager import save_stats_achievements, save_game, get_saves, load_save_file
from source.saving.save_encoder import ObjectConverter, SaveEncoder
from source.saving.save_migrator import migrate_settlement, migrate_unit
from source.util.calculator import split_list_into_chunks, complete_construction, attack, attack_setl, heal, clamp, \
    update_player_quads_seen_around_point
from source.util.minifier import minify_quad, inflate_quad, minify_player, inflate_player, minify_heathens, \
    inflate_heathens, minify_quads_seen, inflate_quads_seen


class MicrocosmServer(socketserver.BaseServer):
    """
    A custom BaseServer implementation - used for typing purposes.
    """
    # Game name -> GameState.
    game_states_ref: Dict[str, GameState]
    # Game name -> Namer.
    namers_ref: Dict[str, Namer]
    # Game name -> MoveMaker.
    move_makers_ref: Dict[str, MoveMaker]
    # Whether this server is *the* game server.
    is_server: bool
    # An optional GameController - only used by clients to update displayed content, e.g. menus.
    game_controller_ref: Optional[GameController]
    # Game name -> a list of players in the game.
    game_clients_ref: Dict[str, List[PlayerDetails]]
    # Game name -> GameConfig.
    lobbies_ref: Dict[str, GameConfig]
    # Hash identifier -> (host, port).
    clients_ref: Dict[int, Tuple[str, int]]
    # Hash identifier -> number sent without response.
    keepalive_ctrs_ref: Dict[int, int]


class RequestHandler(socketserver.BaseRequestHandler):
    """
    The handler for any requests that come in to the listener.
    """

    def handle(self):
        """
        Handle the received request.
        """
        # A bit of typing magic here - without this, all our calls to self.server (e.g. self.server.is_server) would
        # generate warnings. This still generates a warning because self.server is actually a BaseServer, but it's a lot
        # less than the alternative.
        self.server: MicrocosmServer = self.server
        try:
            # self.request contains the packet bytes and a socket to use to respond (or send other packets out). We use
            # our ObjectConverter here so we have attribute access.
            evt: Event = json.loads(self.request[0], object_hook=ObjectConverter)
            sock: socket.socket = self.request[1]
            self.process_event(evt, sock)
        # Any packet that arrives at the listener that isn't syntactically valid can just be ignored.
        except UnicodeDecodeError:
            pass

    def _forward_packet(self, evt: Event, gc_key: str, sock: socket.socket,
                        gate: Callable[[PlayerDetails], bool] = lambda pd: True):
        """
        Forward the given event to the relevant clients.
        :param evt: The event to forward on.
        :param gc_key: The name of the relevant game.
        :param sock: The socket to use to send the packets out.
        :param gate: A lambda function to use to determine whether the given player should receive a packet with the
                     supplied event. Evaluates to True by default.
        """
        for player in self.server.game_clients_ref[gc_key]:
            if gate(player):
                sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                            self.server.clients_ref[player.id])

    def process_event(self, evt: Event, sock: socket.socket):
        """
        Process the given event.
        :param evt: The event to process.
        :param sock: The socket to use to respond, or send other packets out.
        """
        match evt.type:
            case EventType.CREATE:
                self.process_create_event(evt, sock)
            case EventType.INIT:
                self.process_init_event(evt, sock)
            case EventType.UPDATE:
                self.process_update_event(evt, sock)
            case EventType.QUERY:
                self.process_query_event(evt, sock)
            case EventType.LEAVE:
                self.process_leave_event(evt, sock)
            case EventType.JOIN:
                self.process_join_event(evt, sock)
            case EventType.REGISTER:
                self.process_register_event(evt)
            case EventType.END_TURN:
                self.process_end_turn_event(evt, sock)
            case EventType.UNREADY:
                self.process_unready_event(evt)
            case EventType.AUTOFILL:
                self.process_autofill_event(evt, sock)
            case EventType.SAVE:
                self.process_save_event(evt)
            case EventType.QUERY_SAVES:
                self.process_query_saves_event(evt, sock)
            case EventType.LOAD:
                self.process_load_event(evt, sock)
            case EventType.KEEPALIVE:
                self.process_keepalive_event(evt)

    def process_create_event(self, evt: CreateEvent, sock: socket.socket):
        """
        Process an event to create a multiplayer game.
        :param evt: The CreateEvent to process.
        :param sock: The socket to use to respond to the client that sent the create request.
        """
        gsrs: Dict[str, GameState] = self.server.game_states_ref
        # The game server picks a lobby name, creates game state, and sends the relevant details back to the client.
        if self.server.is_server:
            lobby_name = random.choice(LOBBY_NAMES)
            while lobby_name in gsrs:
                lobby_name = random.choice(LOBBY_NAMES)
            player_name = random.choice(PLAYER_NAMES)
            gsrs[lobby_name] = GameState()
            gsrs[lobby_name].players.append(Player(player_name, Faction(evt.cfg.player_faction),
                                                   FACTION_COLOURS[evt.cfg.player_faction]))
            self.server.namers_ref[lobby_name] = Namer()
            self.server.move_makers_ref[lobby_name] = MoveMaker(self.server.namers_ref[lobby_name])
            self.server.game_clients_ref[lobby_name] = \
                [PlayerDetails(player_name, evt.cfg.player_faction, evt.identifier)]
            self.server.lobbies_ref[lobby_name] = evt.cfg
            evt.lobby_name = lobby_name
            evt.player_details = self.server.game_clients_ref[lobby_name]
            sock.sendto(json.dumps(evt, cls=SaveEncoder).encode(), self.server.clients_ref[evt.identifier])
        # Upon receiving a response, the client can update their local game state and controller.
        else:
            gsrs["local"].players.append(Player(evt.player_details[0].name, Faction(evt.cfg.player_faction),
                                                FACTION_COLOURS[evt.cfg.player_faction]))
            gsrs["local"].player_idx = 0
            gsrs["local"].located_player_idx = True
            gc: GameController = self.server.game_controller_ref
            gc.menu.multiplayer_lobby = LobbyDetails(evt.lobby_name, evt.player_details, evt.cfg, current_turn=None)
            gc.namer.reset()

    def process_init_event(self, evt: InitEvent, sock: socket.socket):
        """
        Process an event to initialise a multiplayer game.
        :param evt: The InitEvent to process.
        :param sock: The socket to use to forward out settlement and quad data once the game is initialised.
        """
        gsrs: Dict[str, GameState] = self.server.game_states_ref
        # The game server initialises game state and AI players, and forwards out AI settlement and quad data to all
        # game clients.
        if self.server.is_server:
            gsr: GameState = gsrs[evt.game_name]
            gsr.game_started = True
            gsr.turn = 1
            random.seed()
            gsr.until_night = random.randint(10, 20)
            gsr.nighttime_left = 0
            gsr.on_menu = False
            namer: Namer = self.server.namers_ref[evt.game_name]
            gsr.board = Board(self.server.lobbies_ref[evt.game_name], namer)
            self.server.move_makers_ref[evt.game_name].board_ref = gsr.board
            # Rather than seeding the random number generator, we just let the AI settlements be placed randomly and
            # then forward on their details to each game client.
            gsr.initialise_ais(namer)
            for player in gsr.players:
                if player.ai_playstyle:
                    ai_evt: FoundSettlementEvent = \
                        FoundSettlementEvent(EventType.UPDATE, None, UpdateAction.FOUND_SETTLEMENT, evt.game_name,
                                             player.faction, player.settlements[0], from_settler=False)
                    self._forward_packet(ai_evt, evt.game_name, sock)
            quads_list: List[Quad] = list(chain.from_iterable(gsr.board.quads))
            # We split the quads into chunks of 100 in order to keep packet sizes suitably small.
            for idx, quads_chunk in enumerate(split_list_into_chunks(quads_list, 100)):
                minified_quads: str = ""
                for quad in quads_chunk:
                    quad_str: str = minify_quad(quad)
                    minified_quads += quad_str + ","
                resp_evt: InitEvent = InitEvent(evt.type, None, evt.game_name, gsr.until_night,
                                                self.server.lobbies_ref[evt.game_name], minified_quads, idx)
                # Since the quads are split up into multiple chunks, this means that each client will receive many
                # response InitEvent packets.
                self._forward_packet(resp_evt, evt.game_name, sock)
        # Each game client receives game state and quad data, and starts the game once every packet has been received.
        else:
            gc: GameController = self.server.game_controller_ref
            # The board will only be initialised once, when the first packet is received.
            if not gsrs["local"].board:
                gsrs["local"].until_night = evt.until_night
                gsrs["local"].board = Board(evt.cfg, gc.namer, [[None] * 100 for _ in range(90)],
                                            player_idx=gsrs["local"].player_idx, game_name=evt.game_name)
                gc.move_maker.board_ref = gsrs["local"].board
            split_quads: List[str] = evt.quad_chunk.split(",")[:-1]
            # Inflate each of the 100 quads received in this packet and assign them to the correct position on the
            # board, using the quad chunk index supplied in the event.
            for j in range(100):
                inflated_quad: Quad = inflate_quad(split_quads[j], location=(j, evt.quad_chunk_idx))
                gsrs["local"].board.quads[evt.quad_chunk_idx][j] = inflated_quad
            # Once every quad packet has been received, the game can start. We verify this by ensuring that the board
            # and every quad have non-None values.
            quads_populated: bool = True
            for i in range(90):
                for j in range(100):
                    if gsrs["local"].board.quads[i][j] is None:
                        quads_populated = False
                        break
                if not quads_populated:
                    break
            # Enter the game once all data has been received.
            if quads_populated:
                # Before we enter the game, we need to link the quad for each AI-generated settlement to the quads on
                # the actual board, so that changes to the quad on the board also affect the quad belonging to the
                # settlement. This does not occur normally because each settlement's quads will just be a deep copy by
                # default. This was noticed when desync was occurring because settlements were founded on top of
                # relics, which were then subsequently investigated and removed. But this would only affect the quads on
                # the board, and not the ones belonging to the settlements, due to the original deep copy
                # implementation. Also note that this cannot be done when processing FoundSettlementEvents because when
                # the AI settlements are generated, the quads for the board do not yet exist client-side.
                for p in gsrs["local"].players:
                    for s in p.settlements:
                        s.quads = [gsrs["local"].board.quads[s.location[1]][s.location[0]]]
                pyxel.mouse(visible=True)
                gc.last_turn_time = time.time()
                gsrs["local"].game_started = True
                gsrs["local"].on_menu = False
                # Update stats to include the newly-selected faction.
                save_stats_achievements(gsrs["local"],
                                        faction_to_add=gsrs["local"].players[gsrs["local"].player_idx].faction)
                gsrs["local"].board.overlay.toggle_tutorial()
                gsrs["local"].board.overlay.total_settlement_count = \
                    sum(len(p.settlements) for p in gsrs["local"].players) + 1
                gc.music_player.stop_menu_music()
                gc.music_player.play_game_music()

    def process_update_event(self, evt: UpdateEvent, sock: socket.socket):
        """
        Process the given update-related event.
        :param evt: The update-related event to process.
        :param sock: The socket to use to respond, or send other packets out.
        """
        match evt.action:
            case UpdateAction.FOUND_SETTLEMENT:
                self.process_found_settlement_event(evt, sock)
            case UpdateAction.SET_BLESSING:
                self.process_set_blessing_event(evt, sock)
            case UpdateAction.SET_CONSTRUCTION:
                self.process_set_construction_event(evt, sock)
            case UpdateAction.MOVE_UNIT:
                self.process_move_unit_event(evt, sock)
            case UpdateAction.DEPLOY_UNIT:
                self.process_deploy_unit_event(evt, sock)
            case UpdateAction.GARRISON_UNIT:
                self.process_garrison_unit_event(evt, sock)
            case UpdateAction.INVESTIGATE:
                self.process_investigate_event(evt, sock)
            case UpdateAction.BESIEGE_SETTLEMENT:
                self.process_besiege_settlement_event(evt, sock)
            case UpdateAction.BUYOUT_CONSTRUCTION:
                self.process_buyout_construction_event(evt, sock)
            case UpdateAction.DISBAND_UNIT:
                self.process_disband_unit_event(evt, sock)
            case UpdateAction.ATTACK_UNIT:
                self.process_attack_unit_event(evt, sock)
            case UpdateAction.ATTACK_SETTLEMENT:
                self.process_attack_settlement_event(evt, sock)
            case UpdateAction.HEAL_UNIT:
                self.process_heal_unit_event(evt, sock)
            case UpdateAction.BOARD_DEPLOYER:
                self.process_board_deployer_event(evt, sock)
            case UpdateAction.DEPLOYER_DEPLOY:
                self.process_deployer_deploy_event(evt, sock)

    def process_found_settlement_event(self, evt: FoundSettlementEvent, sock: socket.socket):
        """
        Process an event to found a settlement.
        :param evt: The FoundSettlementEvent to process.
        :param sock: The socket to use to forward out settlement data to other players.
        """
        gsrs: Dict[str, GameState] = self.server.game_states_ref
        game_name: str = evt.game_name if self.server.is_server else "local"
        # We need to unpack the JSON array into a tuple and convert the two statuses into Enums.
        evt.settlement.location = (evt.settlement.location[0], evt.settlement.location[1])
        evt.settlement.harvest_status = HarvestStatus(evt.settlement.harvest_status)
        evt.settlement.economic_status = EconomicStatus(evt.settlement.economic_status)
        migrate_settlement(evt.settlement)
        # We need this for the initial settlements, which contain a unit in the garrison.
        for idx, u in enumerate(evt.settlement.garrison):
            evt.settlement.garrison[idx] = migrate_unit(u, evt.player_faction)
        player = next(pl for pl in gsrs[game_name].players if pl.faction == evt.player_faction)
        player.settlements.append(evt.settlement)
        update_player_quads_seen_around_point(player, evt.settlement.location)
        if evt.from_settler:
            settler_unit = next(u for u in player.units if u.location == evt.settlement.location)
            player.units.remove(settler_unit)
        if self.server.is_server:
            # Remove the settlement name from the server's namer too, so that any AI settlements that are founded don't
            # end up having the same name.
            self.server.namers_ref[evt.game_name].remove_settlement_name(evt.settlement.name,
                                                                         evt.settlement.quads[0].biome)
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)
        else:
            self.server.game_controller_ref.namer.remove_settlement_name(evt.settlement.name,
                                                                         evt.settlement.quads[0].biome)

    def process_set_blessing_event(self, evt: SetBlessingEvent, sock: socket.socket):
        """
        Process an event to set a player's blessing.
        :param evt: The SetBlessingEvent to process.
        :param sock: The socket to use to forward out blessing data to other players.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        player.ongoing_blessing = OngoingBlessing(get_blessing(evt.blessing.blessing.name, player.faction))
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_set_construction_event(self, evt: SetConstructionEvent, sock: socket.socket):
        """
        Process an event to set a settlement's construction.
        :param evt: The SetConstructionEvent to process.
        :param sock: The socket to use to forward out construction data to other players.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        # Since some constructions cost resources, we need to update the player's resources for all other players too.
        player.resources = evt.player_resources
        setl = next(setl for setl in player.settlements if setl.name == evt.settlement_name)
        setl.current_work = evt.construction
        if hasattr(evt.construction.construction, "effect"):
            setl.current_work.construction = get_improvement(evt.construction.construction.name)
        elif hasattr(evt.construction.construction, "type"):
            setl.current_work.construction = get_project(evt.construction.construction.name)
        else:
            setl.current_work.construction = \
                get_unit_plan(evt.construction.construction.name, player.faction, setl.resources)
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_move_unit_event(self, evt: MoveUnitEvent, sock: socket.socket):
        """
        Process an event to move a unit.
        :param evt: The MoveUnitEvent to process.
        :param sock: The socket to use to forward out movement data to other players.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.initial_loc[0], evt.initial_loc[1]))
        # We need to unpack the JSON array into a tuple.
        unit.location = (evt.new_loc[0], evt.new_loc[1])
        update_player_quads_seen_around_point(player, unit.location)
        unit.remaining_stamina = evt.new_stamina
        unit.besieging = evt.besieging
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_deploy_unit_event(self, evt: DeployUnitEvent, sock: socket.socket):
        """
        Process an event to deploy a unit from a settlement.
        :param evt: The DeployUnitEvent to process.
        :param sock: The socket to use to forward out deployment data to other players.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        setl = next(setl for setl in player.settlements if setl.name == evt.settlement_name)
        deployed = setl.garrison.pop()
        deployed.garrisoned = False
        # We need to unpack the JSON array into a tuple.
        deployed.location = (evt.location[0], evt.location[1])
        update_player_quads_seen_around_point(player, deployed.location)
        player.units.append(deployed)
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_garrison_unit_event(self, evt: GarrisonUnitEvent, sock: socket.socket):
        """
        Process an event to garrison a unit in a settlement.
        :param evt: The GarrisonUnitEvent to process.
        :param sock: The socket to use to forward out unit data to other players.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.initial_loc[0], evt.initial_loc[1]))
        setl = next(setl for setl in player.settlements if setl.name == evt.settlement_name)
        unit.remaining_stamina = evt.new_stamina
        unit.garrisoned = True
        setl.garrison.append(unit)
        player.units.remove(unit)
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_investigate_event(self, evt: InvestigateEvent, sock: socket.socket):
        """
        Process an event to investigate a relic.
        :param evt: The InvestigateEvent to process.
        :param sock: The socket to use to forward out investigation data to other players.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.unit_loc[0], evt.unit_loc[1]))
        match evt.result:
            case InvestigationResult.FORTUNE:
                player.ongoing_blessing.fortune_consumed += player.ongoing_blessing.blessing.cost / 5
            case InvestigationResult.WEALTH:
                player.wealth += 25
            case InvestigationResult.VISION:
                update_player_quads_seen_around_point(player, evt.relic_loc, vision_range=10)
            case InvestigationResult.HEALTH:
                unit.plan.max_health += 5
                unit.health += 5
            case InvestigationResult.POWER:
                unit.plan.power += 5
            case InvestigationResult.STAMINA:
                unit.plan.total_stamina += 1
                unit.remaining_stamina = unit.plan.total_stamina
            case InvestigationResult.UPKEEP:
                unit.plan.cost = 0.0
            case InvestigationResult.ORE:
                player.resources.ore += 10
            case InvestigationResult.TIMBER:
                player.resources.timber += 10
            case InvestigationResult.MAGMA:
                player.resources.magma += 10
            case InvestigationResult.NONE:
                pass
        self.server.game_states_ref[game_name].board.quads[evt.relic_loc[1]][evt.relic_loc[0]].is_relic = False
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_besiege_settlement_event(self, evt: BesiegeSettlementEvent, sock: socket.socket):
        """
        Process an event to place a settlement under siege.
        :param evt: The BesiegeSettlementEvent to process.
        :param sock: The socket to use to forward out siege data to other players.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.unit_loc[0], evt.unit_loc[1]))
        # Technically by not initialising the settlement here, it could be undefined later when we attempt to set its
        # besieged attribute. In practice however, the server will always have a settlement with the name from the
        # event.
        setl: Settlement
        for p in self.server.game_states_ref[game_name].players:
            for s in p.settlements:
                if s.name == evt.settlement_name:
                    setl = s
        unit.besieging = True
        setl.besieged = True
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_buyout_construction_event(self, evt: BuyoutConstructionEvent, sock: socket.socket):
        """
        Process an event to buyout a settlement's construction.
        :param evt: The BuyoutConstructionEvent to process.
        :param sock: The socket to use to forward out construction data to other players.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        setl = next(s for s in player.settlements if s.name == evt.settlement_name)
        # Since we rely on the server having the same construction for the settlement as the client, and thus don't
        # include any data about the construction being bought out in the event, we have to lower the player's wealth
        # accordingly here too.
        complete_construction(setl, player)
        player.wealth = evt.player_wealth
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_disband_unit_event(self, evt: DisbandUnitEvent, sock: socket.socket):
        """
        Process an event to disband a unit.
        :param evt: The DisbandUnitEvent to process.
        :param sock: The socket to use to forward out unit data to other players.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.location[0], evt.location[1]))
        player.wealth += unit.plan.cost
        player.units.remove(unit)
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_attack_unit_event(self, evt: AttackUnitEvent, sock: socket.socket):
        """
        Process an event to attack a unit.
        :param evt: The AttackUnitEvent to process.
        :param sock: The socket to use to forward out unit data to other players.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        gsrs: Dict[str, GameState] = self.server.game_states_ref
        player = next(pl for pl in gsrs[game_name].players if pl.faction == evt.player_faction)
        attacker = next(u for u in player.units if u.location == (evt.attacker_loc[0], evt.attacker_loc[1]))
        # Technically by not initialising the defending unit here, it could be undefined later when the attack takes
        # place. In practice however, the server will always have a unit with the defending location from the event.
        # Additionally, the second part of this tuple refers to the player that owns the unit being attacked. Naturally,
        # this is optional because heathens don't belong to any player.
        defender: Tuple[Unit | Heathen, Optional[Player]]
        found_defender: bool = False
        for p in gsrs[game_name].players:
            for u in p.units:
                if u.location == (evt.defender_loc[0], evt.defender_loc[1]):
                    defender = u, p
        if not found_defender:
            for h in gsrs[game_name].heathens:
                if h.location == (evt.defender_loc[0], evt.defender_loc[1]):
                    defender = h, None
        data = attack(attacker, defender[0], ai=False)
        if attacker.health <= 0:
            player.units.remove(attacker)
        if defender[0].health <= 0:
            if defender[1] is None:
                gsrs[game_name].heathens.remove(defender[0])
            else:
                defender[1].units.remove(defender[0])
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)
        else:
            # When other players receive this attack event, we need to check if they were the player being attacked. If
            # so, show the attack overlay.
            if defender[1] is not None and \
                    defender[1].faction == gsrs["local"].players[gsrs["local"].player_idx].faction:
                data.player_attack = False
                gsrs["local"].board.overlay.toggle_attack(data)
                gsrs["local"].board.attack_time_bank = 0
            # Also, if the unit that was attacked was killed, and currently-selected, deselect it.
            sel_u = gsrs["local"].board.selected_unit
            if sel_u is not None and sel_u.location == (evt.defender_loc[0], evt.defender_loc[1]) and \
                    data.defender_was_killed:
                gsrs["local"].board.selected_unit = None
                gsrs["local"].board.overlay.toggle_unit(None)

    def process_attack_settlement_event(self, evt: AttackSettlementEvent, sock: socket.socket):
        """
        Process an event to attack a settlement.
        :param evt: The AttackSettlementEvent to process.
        :param sock: The socket to use to forward out settlement data.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        gsrs: Dict[str, GameState] = self.server.game_states_ref
        player = next(pl for pl in gsrs[game_name].players if pl.faction == evt.player_faction)
        attacker = next(u for u in player.units if u.location == (evt.attacker_loc[0], evt.attacker_loc[1]))
        # Technically by not initialising the settlement here, it could be undefined later when the attack takes place.
        # In practice however, the server will always have a settlement with the name from the event.
        setl: Tuple[Settlement, Player]
        for p in gsrs[game_name].players:
            for s in p.settlements:
                if s.name == evt.settlement_name:
                    setl = s, p
        # Expand the settlement tuple into the Settlement and Player objects when passing it through to the attack
        # function.
        data = attack_setl(attacker, *setl, ai=False)
        if data.attacker_was_killed:
            player.units.remove(attacker)
        if data.setl_was_taken:
            setl[0].besieged = False
            for unit in player.units:
                for setl_quad in setl[0].quads:
                    if abs(unit.location[0] - setl_quad.location[0]) <= 1 and \
                            abs(unit.location[1] - setl_quad.location[1]) <= 1:
                        unit.besieging = False
                        break
            if player.faction != Faction.CONCENTRATED:
                player.settlements.append(setl[0])
                update_player_quads_seen_around_point(player, setl[0].location)
            setl[1].settlements.remove(setl[0])
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)
        else:
            # When other players receive this attack event, we need to check if they own the settlement being attacked.
            # If so, show the settlement attack overlay. Also, if the settlement that was attacked was taken, deselect
            # it.
            if setl[1].faction == gsrs["local"].players[gsrs["local"].player_idx].faction:
                data.player_attack = False
                sel_s = gsrs["local"].board.selected_settlement
                if sel_s is not None and sel_s.name == evt.settlement_name and data.setl_was_taken:
                    gsrs["local"].board.selected_settlement = None
                    gsrs["local"].board.overlay.toggle_settlement(None, gsrs["local"].players[gsrs["local"].player_idx])
                gsrs["local"].board.overlay.toggle_setl_attack(data)
                gsrs["local"].board.attack_time_bank = 0

    def process_heal_unit_event(self, evt: HealUnitEvent, sock: socket.socket):
        """
        Process an event to heal a unit.
        :param evt: The HealUnitEvent to process.
        :param sock: The socket to use to forward out unit data.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        gsrs: Dict[str, GameState] = self.server.game_states_ref
        player = next(pl for pl in gsrs[game_name].players if pl.faction == evt.player_faction)
        healer = next(u for u in player.units if u.location == (evt.healer_loc[0], evt.healer_loc[1]))
        healed = next(u for u in player.units if u.location == (evt.healed_loc[0], evt.healed_loc[1]))
        heal(healer, healed)
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_board_deployer_event(self, evt: BoardDeployerEvent, sock: socket.socket):
        """
        Process an event to have a unit board a deployer unit.
        :param evt: The BoardDeployerEvent to process.
        :param sock: The socket to use to forward out unit data.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.initial_loc[0], evt.initial_loc[1]))
        deployer = next(u for u in player.units if u.location == (evt.deployer_loc[0], evt.deployer_loc[1]))
        unit.remaining_stamina = evt.new_stamina
        deployer.passengers.append(unit)
        player.units.remove(unit)
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_deployer_deploy_event(self, evt: DeployerDeployEvent, sock: socket.socket):
        """
        Process an event to have a deployer unit deploy a unit.
        :param evt: The DeployerDeployEvent to process.
        :param sock: The socket to use to forward out unit data.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        deployer = next(u for u in player.units if u.location == (evt.deployer_loc[0], evt.deployer_loc[1]))
        deployed = deployer.passengers[evt.passenger_idx]
        # We need to unpack the JSON array into a tuple.
        deployed.location = (evt.deployed_loc[0], evt.deployed_loc[1])
        deployer.passengers[evt.passenger_idx:evt.passenger_idx + 1] = []
        player.units.append(deployed)
        update_player_quads_seen_around_point(player, deployed.location)
        if self.server.is_server:
            self._forward_packet(evt, evt.game_name, sock, gate=lambda pd: pd.faction != evt.player_faction)

    def process_query_event(self, evt: QueryEvent, sock: socket.socket):
        """
        Process an event to query the ongoing multiplayer games on the server.
        :param evt: The QueryEvent to process.
        :param sock: The socket to use to respond to the client that sent the query.
        """
        if self.server.is_server:
            lobbies: List[LobbyDetails] = []
            for name, cfg in self.server.lobbies_ref.items():
                gs: GameState = self.server.game_states_ref[name]
                player_details: List[PlayerDetails] = []
                # We need to use extend here rather than just set player_details to be the game clients because if we do
                # that, then we end up adding AI players to our game clients in the loop below, which we don't want.
                player_details.extend(self.server.game_clients_ref[name])
                # Because AI players aren't stored as game clients, we need to add them separately from the game state
                # object. We can disregard eliminated players since nobody can join as them.
                for player in [p for p in gs.players if p.ai_playstyle and not p.eliminated]:
                    player_details.append(PlayerDetails(player.name, player.faction, id=None))
                lobbies.append(LobbyDetails(name, player_details, cfg, None if not gs.game_started else gs.turn))
            evt.lobbies = lobbies
            sock.sendto(json.dumps(evt, cls=SaveEncoder).encode(), self.server.clients_ref[evt.identifier])
        else:
            gc: GameController = self.server.game_controller_ref
            gc.menu.multiplayer_lobbies = evt.lobbies
            gc.menu.viewing_lobbies = True

    def process_leave_event(self, evt: LeaveEvent, sock: socket.socket):
        """
        Process an event to leave a multiplayer game.
        :param evt: The LeaveEvent to process.
        :param sock: The socket to use to forward out player data.
        """
        if self.server.is_server:
            old_clients = self.server.game_clients_ref[evt.lobby_name]
            client_to_remove: PlayerDetails = next(client for client in old_clients if client.id == evt.identifier)
            new_clients = [client for client in old_clients if client.id != evt.identifier]
            self.server.game_clients_ref[evt.lobby_name] = new_clients
            # If there aren't any clients in the game anymore, then the game is over, and we can remove all related
            # state.
            if not new_clients:
                self.server.game_clients_ref.pop(evt.lobby_name)
                self.server.lobbies_ref.pop(evt.lobby_name)
                self.server.game_states_ref.pop(evt.lobby_name)
            else:
                gs: GameState = self.server.game_states_ref[evt.lobby_name]
                player = next(p for p in gs.players if p.faction == client_to_remove.faction)
                # Since the player has left, we need to replace them with an AI.
                if gs.game_started:
                    player.ai_playstyle = AIPlaystyle(random.choice(list(AttackPlaystyle)),
                                                      random.choice(list(ExpansionPlaystyle)))
                    evt.player_ai_playstyle = player.ai_playstyle
                evt.leaving_player_faction = player.faction
                # We need this gate because multiple players may have left at the same time, meaning that they aren't
                # even in the game anymore to receive the packet.
                self._forward_packet(evt, evt.lobby_name, sock, gate=lambda pd: pd.id in self.server.clients_ref)
                # If every remaining player is ready for the turn to end, then end the turn.
                if len(gs.ready_players) == len(self.server.game_clients_ref[evt.lobby_name]):
                    self._server_end_turn(gs, EndTurnEvent(EventType.END_TURN, identifier=None,
                                                           game_name=evt.lobby_name), sock)
        else:
            gs = self.server.game_states_ref["local"]
            player = next(p for p in gs.players if p.faction == evt.leaving_player_faction)
            if gs.game_started:
                player.ai_playstyle = evt.player_ai_playstyle
                # If the player is in-game, then show the player change overlay.
                gs.board.overlay.toggle_player_change(player, changed_player_is_leaving=True)
            else:
                # Otherwise just remove the player from state and the lobby player list.
                gs.players.remove(player)
                current_players: List[PlayerDetails] = \
                    [p for p in self.server.game_controller_ref.menu.multiplayer_lobby.current_players
                     if p.faction != evt.leaving_player_faction]
                self.server.game_controller_ref.menu.multiplayer_lobby.current_players = current_players

    def process_join_event(self, evt: JoinEvent, sock: socket.socket):
        """
        Process an event to join a multiplayer game.
        :param evt: The JoinEvent to process.
        :param sock: The socket to use to forward out player data.
        """
        gsrs: Dict[str, GameState] = self.server.game_states_ref
        gc: GameController = self.server.game_controller_ref
        gs: GameState = gsrs[evt.lobby_name if self.server.is_server else "local"]
        if self.server.is_server:
            # Clients can rejoin ongoing games - in these cases, player details don't need to be changed as no AI
            # players are being replaced.
            client_is_rejoining: bool = \
                any(pd.id == evt.identifier for pd in self.server.game_clients_ref[evt.lobby_name])
            if not client_is_rejoining:
                player_name: str
                # If the player is joining an ongoing game, then they can just take the name of the AI player they're
                # replacing.
                if gs.game_started:
                    replaced_player: Player = next(p for p in gs.players if p.faction == evt.player_faction)
                    replaced_player.ai_playstyle = None
                    player_name = replaced_player.name
                # Otherwise, we just have to keep generating one for them until they get one that's not taken.
                else:
                    # If the player joining would take the player count above its max, then remove an AI player.
                    if len(gs.players) == self.server.lobbies_ref[evt.lobby_name].player_count:
                        gs.players.remove(next(p for p in gs.players if p.ai_playstyle))
                    player_name = random.choice(PLAYER_NAMES)
                    while any(player.name == player_name for player in self.server.game_clients_ref[evt.lobby_name]):
                        player_name = random.choice(PLAYER_NAMES)
                    gs.players.append(Player(player_name,
                                             Faction(evt.player_faction),
                                             FACTION_COLOURS[evt.player_faction]))
                self.server.game_clients_ref[evt.lobby_name].append(PlayerDetails(player_name, evt.player_faction,
                                                                                  evt.identifier))
            # We can't just combine the player details from game_clients_ref and manually make the AI players' ones
            # because order matters for this - the player joining needs to get their player index right.
            player_details: List[PlayerDetails] = []
            for player in gs.players:
                if player.ai_playstyle:
                    player_details.append(PlayerDetails(player.name, player.faction, id=None))
                else:
                    player_details.append(next(pd for pd in self.server.game_clients_ref[evt.lobby_name]
                                               if pd.faction == player.faction))
            evt.lobby_details = LobbyDetails(evt.lobby_name,
                                             player_details,
                                             self.server.lobbies_ref[evt.lobby_name],
                                             current_turn=None if not gs.game_started else gs.turn)
            # Alert the other players that a new player has joined, but only if they're not rejoining - other players
            # don't need to be alerted in these cases.
            if not client_is_rejoining:
                self._forward_packet(evt, evt.lobby_name, sock,
                                     gate=lambda pd: pd.faction != evt.player_faction or not gs.game_started)
            # If the player is joining an ongoing game, then we need to forward all the game state to them.
            if gs.game_started:
                quads_list: List[Quad] = list(chain.from_iterable(gs.board.quads))
                # We split the quads into chunks of 100 in order to keep packet sizes suitably small.
                for idx, quads_chunk in enumerate(split_list_into_chunks(quads_list, 100)):
                    # We sleep for 10ms between each chunk in order to account for slower connections. By doing this, we
                    # can stop these clients from being overwhelmed by packets.
                    time.sleep(0.01)
                    minified_quads: str = ""
                    for quad in quads_chunk:
                        quad_str: str = minify_quad(quad)
                        minified_quads += quad_str + ","
                    evt.until_night = gs.until_night
                    evt.nighttime_left = gs.nighttime_left
                    evt.cfg = self.server.lobbies_ref[evt.lobby_name]
                    evt.quad_chunk = minified_quads
                    evt.quad_chunk_idx = idx
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[evt.identifier])
                evt.total_quads_seen = sum(len(p.quads_seen) for p in gs.players)
                for idx, player in enumerate(gs.players):
                    # We sleep for 10ms between each player in order to account for slower connections. By doing this,
                    # we can stop these clients from being overwhelmed by packets.
                    time.sleep(0.01)
                    # Before we add the player to the event, we need to reset the data from the previous loop. We need
                    # to do this because the way we differentiate between the different types of JoinEvents client-side
                    # is by checking what attributes are populated. For example, if quad_chunk is not None, then we know
                    # to inflate the received quad data. Similarly, if player_chunk is not None, then we know to inflate
                    # the received player data. This principle applies to seen quads and heathens as well.
                    evt.until_night = None
                    evt.nighttime_left = None
                    evt.cfg = None
                    evt.quad_chunk = None
                    evt.quad_chunk_idx = None
                    evt.player_chunk = minify_player(player)
                    evt.player_chunk_idx = idx
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[evt.identifier])
                evt.player_chunk = None
                evt.player_chunk_idx = None
                for idx, player in enumerate(gs.players):
                    evt.player_chunk_idx = idx
                    evt.quads_seen_chunk = None
                    # We split the quad locations into chunks of 100 in order to keep packet sizes suitably small.
                    for qs_chunk in split_list_into_chunks(list(player.quads_seen), 100):
                        # We sleep for 10ms between each chunk in order to account for slower connections. By doing
                        # this, we can stop these clients from being overwhelmed by packets.
                        time.sleep(0.01)
                        evt.quads_seen_chunk = minify_quads_seen(set(qs_chunk))
                        sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                    self.server.clients_ref[evt.identifier])
                evt.player_chunk_idx = None
                evt.total_quads_seen = None
                evt.quads_seen_chunk = None
                # Since there are never that many heathens, we can just send them all together.
                evt.heathens_chunk = minify_heathens(gs.heathens)
                evt.total_heathens = len(gs.heathens)
                sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                            self.server.clients_ref[evt.identifier])
        else:
            gc.menu.multiplayer_lobby = LobbyDetails(evt.lobby_name,
                                                     evt.lobby_details.current_players,
                                                     evt.lobby_details.cfg,
                                                     evt.lobby_details.current_turn)
            if evt.lobby_details.current_turn:
                # Normally once all game state is loaded, we can remove the AI playstyle for the player and continue on
                # with the game. However, in some cases seen quad packets may be received by the player joining after
                # entering the game. This is because game state is considered to be populated as long as each player has
                # at least some seen quads. Additionally, for other players receiving this event after being forwarded
                # it, the player change overlay is displayed.
                if gs.game_started and not evt.quads_seen_chunk:
                    replaced_player: Player = next(p for p in gs.players if p.faction == evt.player_faction)
                    replaced_player.ai_playstyle = None
                    if gs.players[gs.player_idx].faction != evt.player_faction:
                        gs.board.overlay.toggle_player_change(replaced_player,
                                                              changed_player_is_leaving=False)
                # It is important to note that players already in the game being joined will never enter this else - it
                # is only for the player joining.
                else:
                    # If we are yet to determine which player the player joining is, do so.
                    if not gs.located_player_idx:
                        for idx, player in enumerate(evt.lobby_details.current_players):
                            if player.faction == evt.player_faction:
                                gs.player_idx = idx
                                gs.located_player_idx = True
                            gs.players.append(Player(player.name, Faction(player.faction),
                                                     FACTION_COLOURS[player.faction]))
                        gc.menu.multiplayer_game_being_loaded = LoadedMultiplayerState()
                    # Initialise the board with night data if it has not been done already.
                    if not gs.board:
                        gs.until_night = evt.until_night
                        gs.nighttime_left = evt.nighttime_left
                        gs.board = Board(evt.cfg, gc.namer, [[None] * 100 for _ in range(90)],
                                         player_idx=gs.player_idx, game_name=evt.lobby_name)
                        gc.move_maker.board_ref = gs.board
                    if evt.quad_chunk:
                        split_quads: List[str] = evt.quad_chunk.split(",")[:-1]
                        # Inflate each of the 100 quads received in this packet and assign them to the correct position
                        # on the board, using the quad chunk index supplied in the event.
                        for j in range(100):
                            inflated_quad: Quad = inflate_quad(split_quads[j], location=(j, evt.quad_chunk_idx))
                            gs.board.quads[evt.quad_chunk_idx][j] = inflated_quad
                        gc.menu.multiplayer_game_being_loaded.quad_chunks_loaded += 1
                    if evt.player_chunk:
                        # Inflate the player received in this packet.
                        gs.players[evt.player_chunk_idx] = inflate_player(evt.player_chunk, gs.board.quads)
                        # Remove the names of this player's settlements from the joining player's namer, in order to
                        # avoid name clashes.
                        for s in gs.players[evt.player_chunk_idx].settlements:
                            gc.namer.remove_settlement_name(s.name, s.quads[0].biome)
                        gc.menu.multiplayer_game_being_loaded.players_loaded += 1
                    if evt.quads_seen_chunk:
                        # Because these chunks could arrive after entering the game, we need to make sure the loading
                        # screen is still being shown before updating it.
                        if gc.menu.multiplayer_game_being_loaded:
                            gc.menu.multiplayer_game_being_loaded.total_quads_seen = evt.total_quads_seen
                        # Inflate each of the 100 quad locations received in this packet and assign them to the correct
                        # player, using the player chunk index supplied in the event.
                        inflated_quads_seen: Set[Tuple[int, int]] = inflate_quads_seen(evt.quads_seen_chunk)
                        gs.players[evt.player_chunk_idx].quads_seen.update(inflated_quads_seen)
                        if gc.menu.multiplayer_game_being_loaded:
                            gc.menu.multiplayer_game_being_loaded.quads_seen_loaded += len(inflated_quads_seen)
                    if evt.heathens_chunk:
                        gc.menu.multiplayer_game_being_loaded.total_heathens = evt.total_heathens
                        # Inflate the heathens received.
                        gs.heathens = inflate_heathens(evt.heathens_chunk)
                        gc.menu.multiplayer_game_being_loaded.heathens_loaded = True
                    gs.turn = evt.lobby_details.current_turn
                    # Once sufficient game state has been received, the game can start. We verify this by ensuring that
                    # the board, every quad, every player (and at least some of their seen quads), and the heathens have
                    # been loaded.
                    state_populated: bool = True
                    for i in range(90):
                        for j in range(100):
                            if gs.board.quads[i][j] is None:
                                state_populated = False
                                break
                        if not state_populated:
                            break
                    for p in gs.players:
                        if not p.quads_seen:
                            state_populated = False
                            break
                    # We don't care about the heathens before turn 5 because they wouldn't have spawned yet.
                    if gs.turn > 5 and not gs.heathens:
                        state_populated = False
                    # Enter the game once sufficient data has been received.
                    if state_populated:
                        pyxel.mouse(visible=True)
                        gc.last_turn_time = time.time()
                        gs.game_started = True
                        gs.on_menu = False
                        # Update stats to include the newly-selected faction.
                        save_stats_achievements(gsrs["local"], faction_to_add=evt.player_faction)
                        # Initialise the map position to the player's first settlement.
                        gs.map_pos = (clamp(gs.players[gs.player_idx].settlements[0].location[0] - 12, -1, 77),
                                      clamp(gs.players[gs.player_idx].settlements[0].location[1] - 11, -1, 69))
                        gs.board.overlay.current_player = gs.players[gs.player_idx]
                        gs.board.overlay.total_settlement_count = sum(len(p.settlements) for p in gs.players)
                        gc.music_player.stop_menu_music()
                        gc.music_player.play_game_music()
                        # We can reset the loading screen's statistics as well.
                        gc.menu.multiplayer_game_being_loaded = None
            # If the game hasn't started yet and we're still in the lobby.
            else:
                # If the client has not located their player index, then they must be the player that is joining, so we
                # need to determine their index.
                if not gs.located_player_idx:
                    for idx, player in enumerate(evt.lobby_details.current_players):
                        if player.faction == evt.player_faction:
                            gs.player_idx = idx
                            gs.located_player_idx = True
                        gs.players.append(Player(player.name, Faction(player.faction), FACTION_COLOURS[player.faction]))
                    gc.menu.joining_game = False
                    gc.menu.viewing_lobbies = False
                    gc.menu.setup_option = SetupOption.START_GAME
                # Otherwise, a new player has joined a lobby the client is already a part of.
                else:
                    new_player: PlayerDetails = evt.lobby_details.current_players[-1]
                    gs.players.append(Player(new_player.name, Faction(new_player.faction),
                                             FACTION_COLOURS[new_player.faction]))

    def process_register_event(self, evt: RegisterEvent):
        """
        Process an event to register a client with the server.
        :param evt: The RegisterEvent to process.
        """
        # Keep track of the client's IP address and port they're listening on, so we can send them packets.
        self.server.clients_ref[evt.identifier] = self.client_address[0], evt.port

    def _server_end_turn(self, gs: GameState, evt: EndTurnEvent, sock: socket.socket):
        """
        Process turn-ending logic for a multiplayer game on the game server.
        :param gs: The game state for the multiplayer game in which the turn is being ended.
        :param evt: The EndTurnEvent to forward to other players.
        :param sock: The socket to use to forward out turn data.
        """
        for idx, player in enumerate(gs.players):
            gs.process_player(player, idx == gs.player_idx)
        if gs.turn % 5 == 0:
            new_heathen_loc: (int, int) = random.randint(0, 89), random.randint(0, 99)
            gs.heathens.append(get_heathen(new_heathen_loc, gs.turn))
        for h in gs.heathens:
            h.remaining_stamina = h.plan.total_stamina
            if h.health < h.plan.max_health:
                h.health = min(h.health + h.plan.max_health * 0.1, h.plan.max_health)
        gs.turn += 1
        if gs.board.game_config.climatic_effects:
            # We don't reseed the random number generator here so that all clients have the same day-night cycle.
            gs.process_climatic_effects(reseed_random=False)
        # If no victory has been achieved, then save the game and process the turns for the heathens and AI players.
        if gs.check_for_victory() is None:
            save_game(gs, auto=True)
            gs.process_heathens()
            gs.process_ais(self.server.move_makers_ref[evt.game_name])
        # Pass the hash of the server's game state to clients so that they can validate that they're still in sync with
        # the server.
        evt.game_state_hash = hash(gs)
        # Alert all players that the turn has ended.
        self._forward_packet(evt, evt.game_name, sock)
        # Since we're in a new turn, there are no longer any players ready to end their turn.
        gs.ready_players.clear()

    def process_end_turn_event(self, evt: EndTurnEvent, sock: socket.socket):
        """
        Process an event to either signal that a player is ready to end the turn, or to actually end the game's current
        turn.
        :param evt: The EndTurnEvent to process.
        :param sock: The socket to use to forward out turn data.
        """
        game_name: str = evt.game_name if self.server.is_server else "local"
        gs: GameState = self.server.game_states_ref[game_name]
        gc: GameController = self.server.game_controller_ref
        # To keep the server and all clients in sync, we seed the random number generator with the game's turn before
        # ending each turn.
        random.seed(gs.turn)
        # If the server is receiving this event, then that means a player has signalled that they're ready for the turn
        # to end. As such, add them to the list, and end the turn if all players are ready.
        if self.server.is_server:
            gs.ready_players.add(evt.identifier)
            if len(gs.ready_players) == len(self.server.game_clients_ref[evt.game_name]):
                self._server_end_turn(gs, evt, sock)
        # If a client is receiving this event, however, then that means that all players are ready and the turn has
        # ended. Thus, process the turn.
        else:
            gs.processing_turn = True
            for idx, player in enumerate(gs.players):
                gs.process_player(player, idx == gs.player_idx)
            if gs.turn % 5 == 0:
                new_heathen_loc: (int, int) = random.randint(0, 89), random.randint(0, 99)
                gs.heathens.append(get_heathen(new_heathen_loc, gs.turn))
            for h in gs.heathens:
                h.remaining_stamina = h.plan.total_stamina
                if h.health < h.plan.max_health:
                    h.health = min(h.health + h.plan.max_health * 0.1, h.plan.max_health)
            gs.board.overlay.remove_warning_if_possible()
            gs.turn += 1
            if gs.board.game_config.climatic_effects:
                # We don't reseed the random number generator here so that all clients have the same day-night cycle.
                gs.process_climatic_effects(reseed_random=False)
            possible_vic = gs.check_for_victory()
            if possible_vic is not None:
                gs.board.overlay.toggle_victory(possible_vic)
                if possible_vic.player.faction == gs.players[gs.player_idx].faction:
                    if new_achs := save_stats_achievements(gs, victory_to_add=possible_vic.type):
                        gs.board.overlay.toggle_ach_notif(new_achs)
                # We need an extra eliminated check in here because if the player was eliminated at the same time that
                # the victory was achieved, e.g. in an elimination victory between two players, the defeat count would
                # be incremented twice - once here and once when they are marked as eliminated.
                elif not gs.players[gs.player_idx].eliminated:
                    if new_achs := save_stats_achievements(gs, increment_defeats=True):
                        gs.board.overlay.toggle_ach_notif(new_achs)
            # If no victory has been achieved, then process the turns for the heathens and AI players.
            else:
                time_elapsed = time.time() - gc.last_turn_time
                gc.last_turn_time = time.time()
                if new_achs := save_stats_achievements(gs, time_elapsed):
                    gs.board.overlay.toggle_ach_notif(new_achs)
                gs.board.overlay.total_settlement_count = sum(len(p.settlements) for p in gs.players)
                gs.process_heathens()
                gs.process_ais(gc.move_maker)
            gs.board.waiting_for_other_players = False
            # Ensure that the client is still in sync with the server - if it's not, display the desync overlay,
            # prompting the player to rejoin the game.
            gs.board.checking_game_sync = True
            if hash(gs) != evt.game_state_hash:
                gs.board.overlay.toggle_desync()
            gs.board.checking_game_sync = False
            gs.processing_turn = False

    def process_unready_event(self, evt: UnreadyEvent):
        """
        Process an event to mark a player has not being ready to end the current turn.
        :param evt: The UnreadyEvent to process.
        """
        # We use discard rather than remove here just in case a client attempts to unready between the time that the
        # turn has ended on the server and the time the turn has ended on the client's machine.
        self.server.game_states_ref[evt.game_name].ready_players.discard(evt.identifier)

    def process_autofill_event(self, evt: AutofillEvent, sock: socket.socket):
        """
        Process an event to autofill a multiplayer lobby.
        :param evt: The AutofillEvent to process.
        :param sock: The socket to use to forward out player data.
        """
        gsrs: Dict[str, GameState] = self.server.game_states_ref
        if self.server.is_server:
            max_players: int = self.server.lobbies_ref[evt.lobby_name].player_count
            current_players: int = len(self.server.game_clients_ref[evt.lobby_name])
            # Generate enough AI players to fill the lobby.
            for _ in range(max_players - current_players):
                ai_name = random.choice(PLAYER_NAMES)
                while any(player.name == ai_name for player in gsrs[evt.lobby_name].players):
                    ai_name = random.choice(PLAYER_NAMES)
                ai_faction = random.choice(list(Faction))
                while any(player.faction == ai_faction for player in gsrs[evt.lobby_name].players):
                    ai_faction = random.choice(list(Faction))
                ai_player = Player(ai_name, ai_faction, FACTION_COLOURS[ai_faction],
                                   ai_playstyle=AIPlaystyle(random.choice(list(AttackPlaystyle)),
                                                            random.choice(list(ExpansionPlaystyle))))
                gsrs[evt.lobby_name].players.append(ai_player)
            evt.players = gsrs[evt.lobby_name].players
            # Alert all players to the new AI players in the lobby.
            self._forward_packet(evt, evt.lobby_name, sock)
        else:
            gc: GameController = self.server.game_controller_ref
            previous_player_count = len(gc.menu.multiplayer_lobby.current_players)
            # Since AutofillEvents contain actual Player objects, we can just migrate them and update the lobby and game
            # state with them.
            for player in evt.players[previous_player_count:]:
                player.faction = Faction(player.faction)
                player.imminent_victories = set(player.imminent_victories)
                player.quads_seen = set(player.quads_seen)
                new_player_detail: PlayerDetails = PlayerDetails(player.name, player.faction, id=None)
                gc.menu.multiplayer_lobby.current_players.append(new_player_detail)
                gsrs["local"].players.append(player)

    def process_save_event(self, evt: SaveEvent):
        """
        Process an event to save the multiplayer game with the given name.
        :param evt: The SaveEvent to extract the game name from.
        """
        save_game(self.server.game_states_ref[evt.game_name])

    def process_query_saves_event(self, evt: QuerySavesEvent, sock: socket.socket):
        """
        Process an event to query the saved multiplayer games on the server.
        :param evt: The QuerySavesEvent to process.
        :param sock: The socket to use to respond to the client that sent the query.
        """
        if self.server.is_server:
            evt.saves = get_saves()
            sock.sendto(json.dumps(evt, cls=SaveEncoder).encode(), self.server.clients_ref[evt.identifier])
        else:
            self.server.game_controller_ref.menu.saves = evt.saves
            self.server.game_controller_ref.menu.loading_multiplayer_game = True

    def process_load_event(self, evt: LoadEvent, sock: socket.socket):
        """
        Process an event to load a multiplayer game.
        :param evt: The LoadEvent to process.
        :param sock: The socket to use to respond to the client that sent the load request.
        """
        if self.server.is_server:
            gsrs: Dict[str, GameState] = self.server.game_states_ref
            # Choose a new lobby name for the saved game.
            lobby_name = random.choice(LOBBY_NAMES)
            while lobby_name in gsrs:
                lobby_name = random.choice(LOBBY_NAMES)
            gsrs[lobby_name] = GameState()
            self.server.namers_ref[lobby_name] = Namer()
            # Load in all game state from the file.
            cfg, quads = load_save_file(gsrs[lobby_name], self.server.namers_ref[lobby_name], evt.save_name)
            # Make all players AIs so we can 'join' as any player.
            for p in gsrs[lobby_name].players:
                p.ai_playstyle = AIPlaystyle(AttackPlaystyle.NEUTRAL, ExpansionPlaystyle.NEUTRAL)
            self.server.game_clients_ref[lobby_name] = []
            self.server.move_makers_ref[lobby_name] = MoveMaker(self.server.namers_ref[lobby_name])
            self.server.lobbies_ref[lobby_name] = cfg
            gsrs[lobby_name].game_started = True
            gsrs[lobby_name].on_menu = False
            gsrs[lobby_name].board = Board(self.server.lobbies_ref[lobby_name], self.server.namers_ref[lobby_name],
                                           quads)
            self.server.move_makers_ref[lobby_name].board_ref = gsrs[lobby_name].board
            player_details: List[PlayerDetails] = []
            for player in [p for p in gsrs[lobby_name].players if not p.eliminated]:
                player_details.append(PlayerDetails(player.name, player.faction, id=None))
            # Respond with the lobby details so the client can pick a faction.
            evt.lobby = LobbyDetails(lobby_name, player_details, cfg, gsrs[lobby_name].turn)
            sock.sendto(json.dumps(evt, cls=SaveEncoder).encode(), self.server.clients_ref[evt.identifier])
        else:
            gc: GameController = self.server.game_controller_ref
            # Reset the client's namer so that it can be updated on join.
            gc.namer.reset()
            gc.menu.multiplayer_lobbies = [evt.lobby]
            gc.menu.available_multiplayer_factions = \
                [(Faction(p.faction), FACTION_COLOURS[p.faction]) for p in evt.lobby.current_players]
            gc.menu.loading_game = False
            gc.menu.joining_game = True

    def process_keepalive_event(self, evt: Event):
        """
        Process an event to determine whether the client is still playing (and their connection is stable).
        """
        # If the server is receiving this event, then the client responded to the initial keepalive, and we can reset
        # their counter.
        if self.server.is_server:
            self.server.keepalive_ctrs_ref[evt.identifier] = 0
        # If a client is receiving this event, however, they need to send one back to the server to signal that they're
        # still 'alive'.
        else:
            dispatch_event(Event(EventType.KEEPALIVE, get_identifier()))


class EventListener:
    """
    Listens for multiplayer-related events on a UPnP-exposed port.
    """
    def __init__(self,
                 is_server: bool = False,
                 game_states: Optional[Dict[str, GameState]] = None,
                 game_controller: Optional[GameController] = None):
        """
        Construct the listener.
        :param is_server: Whether the listener is *the* game server.
        :param game_states: An optional dictionary of game states - used by clients to pre-supply local state.
        :param game_controller: An optional game controller - used by clients to pre-supply local state.
        """
        # Game name -> GameState.
        self.game_states: Dict[str, GameState] = game_states if game_states is not None else {}
        # Game name -> Namer.
        self.namers: Dict[str, Namer] = {}
        # Game name -> MoveMaker.
        self.move_makers: Dict[str, MoveMaker] = {}
        # Whether this server is *the* game server.
        self.is_server: bool = is_server
        # An optional GameController - only used by clients to update displayed content, e.g. menus.
        self.game_controller: Optional[GameController] = game_controller
        # Game name -> a list of players in the game.
        self.game_clients: Dict[str, List[PlayerDetails]] = {}
        # Game name -> GameConfig.
        self.lobbies: Dict[str, GameConfig] = {}
        # Hash identifier -> (host, port).
        self.clients: Dict[int, Tuple[str, int]] = {}
        # Hash identifier -> number sent without response.
        self.keepalive_ctrs: Dict[int, int] = {}

        # The game server needs to send out regular keepalives in another thread, since we're going to be listening for
        # events on the main one.
        if self.is_server:
            self.keepalive_scheduler: sched.scheduler = sched.scheduler(time.time, time.sleep)
            keepalive_thread: Thread = Thread(target=self.run_keepalive_scheduler, daemon=True)
            keepalive_thread.start()

    def run_keepalive_scheduler(self):
        """
        Run the keepalive scheduler, which runs the keepalive every 5 seconds.
        """
        self.keepalive_scheduler.enter(5, 1, self.run_keepalive, (self.keepalive_scheduler,))
        self.keepalive_scheduler.run()

    def run_keepalive(self, scheduler: sched.scheduler):
        """
        Runs the keepalive, ensuring all clients are still playing the game (and their connection is stable).
        :param scheduler: The scheduler to use to run the keepalive.
        """
        # Run the keepalive again in 5 seconds.
        scheduler.enter(5, 1, self.run_keepalive, (scheduler,))
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        evt = Event(EventType.KEEPALIVE, None)
        clients_to_remove: List[int] = []
        # Send the keepalive event to each client.
        for identifier, client in self.clients.items():
            sock.sendto(json.dumps(evt, cls=SaveEncoder).encode(), client)
            if identifier in self.keepalive_ctrs:
                self.keepalive_ctrs[identifier] += 1
                # If a client has not responded to a keepalive event in the last 30 seconds, then they can be considered
                # to be no longer playing.
                if self.keepalive_ctrs[identifier] == 6:
                    clients_to_remove.append(identifier)
            else:
                self.keepalive_ctrs[identifier] = 1
        # Clients that are being removed are removed from their current game and then removed from the clients
        # dictionary.
        for identifier in clients_to_remove:
            for lobby_name, details in self.game_clients.items():
                for player_detail in details:
                    if player_detail.id == identifier:
                        # Rather than copy all the same logic as leave events, we simply send a leave event from the
                        # server to itself with the client's details.
                        l_evt: LeaveEvent = LeaveEvent(EventType.LEAVE, identifier, lobby_name)
                        sock.sendto(json.dumps(l_evt, cls=SaveEncoder).encode(), ("localhost", 9999))
            self.clients.pop(identifier)

    def run(self):
        """
        Run the event listener, listening forever.
        """
        # Bind the listener to all IP addresses on the machine. The game server listens on port 9999, while clients can
        # listen on whichever dynamic port they get assigned - since the server remembers what port each client is on,
        # it doesn't matter that it is different for each client.
        with socketserver.UDPServer(("0.0.0.0", 9999 if self.is_server else 0), RequestHandler) as server:
            # Clients need to open up their networking and contact the server before they can start listening for
            # events.
            if not self.is_server:
                try:
                    # Initialise UPnP, discovering and then selecting a valid UPnP IGD device on the connected network,
                    # where IGD refers to the protocol used for UPnP.
                    upnp = UPnP()
                    upnp.discover()
                    upnp.selectigd()
                    # Fundamentally, UPnP works by opening up a port into your connected network, and then forwards all
                    # public traffic directed at that port to a configured private IP within the network. Because of
                    # this, we need to determine what the private IP is for this machine. We do this by connecting to
                    # the Google DNS server, which allows us to see the private IP for this machine.
                    ip_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    ip_sock.connect(("8.8.8.8", 80))
                    private_ip: str = ip_sock.getsockname()[0]
                    mapping_idx: int = 0
                    todays_date: datetime.date = datetime.date.today()
                    # For security reasons, we don't really want to leave these UPnP ports open permanently (even though
                    # nothing is listening). As such, we check all existing port mappings on the network, and delete any
                    # mappings that were created on previous days. Additionally, if a previous mapping was for this
                    # machine, we delete the old one and make a new one.
                    while (port_mapping := upnp.getgenericportmapping(mapping_idx)) is not None:
                        mapping_name: str = port_mapping[3]
                        if mapping_name.startswith("Microcosm"):
                            # Because ISO dates can be sorted alphabetically to sort them chronologically, we can just
                            # extract the date from the mapping and compare the strings.
                            mapping_is_old: bool = mapping_name[10:] < str(todays_date)
                            mapping_is_for_this_machine: bool = port_mapping[2][0] == private_ip
                            if mapping_is_old or mapping_is_for_this_machine:
                                upnp.deleteportmapping(port_mapping[0], "UDP")
                        mapping_idx += 1
                    # Now create a new port mapping for this machine's private IP and dynamic listener port, complete
                    # with the creation date, so it can be deleted later.
                    upnp.addportmapping(server.server_address[1], "UDP", private_ip, server.server_address[1],
                                        f"Microcosm {todays_date}", "")
                    # Now with a port listening for external traffic, we can signal to the server that we're listening.
                    dispatch_event(RegisterEvent(EventType.REGISTER, get_identifier(), server.server_address[1]))
                    self.game_controller.menu.upnp_enabled = True
                # This would be a more specific Exception, but the UPnP library that is used actually raises the base
                # Exception. Thus, we also have to disable the lint rule for catching base Exceptions.
                # pylint: disable=broad-exception-caught
                except Exception:
                    self.game_controller.menu.upnp_enabled = False
                    # We can just return early since there's no way a client without UPnP will be able to receive
                    # packets from the game server, so there's no reason to serve the server at all.
                    return
            # So that the request handler can access the listener's state, we set some attributes on the handler itself.
            server.game_states_ref = self.game_states
            server.namers_ref = self.namers
            server.move_makers_ref = self.move_makers
            server.is_server = self.is_server
            server.game_controller_ref = self.game_controller
            server.game_clients_ref = self.game_clients
            server.lobbies_ref = self.lobbies
            server.clients_ref = self.clients
            server.keepalive_ctrs_ref = self.keepalive_ctrs
            # Listen for events until the process is killed.
            server.serve_forever()
