import datetime
import json
import os
import random
import socket
import socketserver
import time
import typing
import uuid
from itertools import chain

import pyxel
from miniupnpc import UPnP

from source.display.board import Board
from source.display.menu import SetupOption
from source.foundation.catalogue import FACTION_COLOURS, LOBBY_NAMES, PLAYER_NAMES, Namer, get_improvement, get_project, \
    get_unit_plan, get_blessing, get_heathen
from source.foundation.models import GameConfig, Player, PlayerDetails, LobbyDetails, Quad, Biome, ResourceCollection, \
    OngoingBlessing, InvestigationResult, Settlement, Unit, Heathen, Faction, AIPlaystyle, AttackPlaystyle, \
    ExpansionPlaystyle, LoadedMultiplayerState
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.game_management.movemaker import MoveMaker
from source.networking.client import dispatch_event
from source.networking.events import Event, EventType, CreateEvent, InitEvent, UpdateEvent, UpdateAction, \
    FoundSettlementEvent, QueryEvent, LeaveEvent, JoinEvent, RegisterEvent, SetBlessingEvent, SetConstructionEvent, \
    MoveUnitEvent, DeployUnitEvent, GarrisonUnitEvent, InvestigateEvent, BesiegeSettlementEvent, \
    BuyoutConstructionEvent, DisbandUnitEvent, AttackUnitEvent, AttackSettlementEvent, EndTurnEvent, UnreadyEvent, \
    HealUnitEvent, BoardDeployerEvent, DeployerDeployEvent, AutofillEvent
from source.saving.save_encoder import ObjectConverter, SaveEncoder
from source.saving.save_migrator import migrate_settlement, migrate_quad, migrate_unit, migrate_player
from source.util.calculator import split_list_into_chunks, complete_construction, attack, attack_setl, heal, clamp
from source.util.minifier import minify_quad, inflate_quad, minify_player, inflate_player, minify_heathens, \
    inflate_heathens, minify_quads_seen, inflate_quads_seen


class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            evt: Event = json.loads(self.request[0], object_hook=ObjectConverter)
            sock: socket.socket = self.request[1]
            self.process_event(evt, sock)
        except UnicodeDecodeError:
            pass

    def process_event(self, evt: Event, sock: socket.socket):
        if evt.type == EventType.CREATE:
            self.process_create_event(evt, sock)
        elif evt.type == EventType.INIT:
            self.process_init_event(evt, sock)
        elif evt.type == EventType.UPDATE:
            self.process_update_event(evt, sock)
        elif evt.type == EventType.QUERY:
            self.process_query_event(evt, sock)
        elif evt.type == EventType.LEAVE:
            self.process_leave_event(evt, sock)
        elif evt.type == EventType.JOIN:
            self.process_join_event(evt, sock)
        elif evt.type == EventType.REGISTER:
            self.process_register_event(evt)
        elif evt.type == EventType.END_TURN:
            self.process_end_turn_event(evt, sock)
        elif evt.type == EventType.UNREADY:
            self.process_unready_event(evt)
        elif evt.type == EventType.AUTOFILL:
            self.process_autofill_event(evt, sock)

    def process_create_event(self, evt: CreateEvent, sock: socket.socket):
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        if self.server.is_server:
            lobby_name = random.choice(LOBBY_NAMES)
            while lobby_name in gsrs:
                lobby_name = random.choice(LOBBY_NAMES)
            player_name = random.choice(PLAYER_NAMES)
            gsrs[lobby_name] = GameState()
            gsrs[lobby_name].players.append(Player(player_name, evt.cfg.player_faction,
                                                   FACTION_COLOURS[evt.cfg.player_faction]))
            self.server.namers_ref[lobby_name] = Namer()
            self.server.move_makers_ref[lobby_name] = MoveMaker(self.server.namers_ref[lobby_name])
            self.server.game_clients_ref[lobby_name] = \
                [PlayerDetails(player_name, evt.cfg.player_faction, evt.identifier, self.client_address[0])]
            self.server.lobbies_ref[lobby_name] = evt.cfg
            resp_evt: CreateEvent = CreateEvent(evt.type, evt.timestamp, None, evt.cfg, lobby_name,
                                                self.server.game_clients_ref[lobby_name])
            sock.sendto(json.dumps(resp_evt, cls=SaveEncoder).encode(), self.server.clients_ref[evt.identifier])
        else:
            gsrs["local"].players.append(Player(evt.player_details[0].name, evt.cfg.player_faction,
                                                FACTION_COLOURS[evt.cfg.player_faction]))
            gsrs["local"].player_idx = 0
            gc: GameController = self.server.game_controller_ref
            gc.menu.multiplayer_lobby = LobbyDetails(evt.lobby_name, evt.player_details, evt.cfg, current_turn=None)
            gc.menu.in_multiplayer_lobby = True
            gc.namer.reset()

    def process_init_event(self, evt: InitEvent, sock: socket.socket):
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
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
            gsr.initialise_ais(namer)
            for player in gsr.players:
                if player.ai_playstyle:
                    for client in self.server.game_clients_ref[evt.game_name]:
                        ai_evt: FoundSettlementEvent = \
                            FoundSettlementEvent(EventType.UPDATE, datetime.datetime.now(), None,
                                                 UpdateAction.FOUND_SETTLEMENT, evt.game_name, player.faction,
                                                 player.settlements[0], from_settler=False)
                        sock.sendto(json.dumps(ai_evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                    self.server.clients_ref[client.id])
            quads_list: typing.List[Quad] = list(chain.from_iterable(gsr.board.quads))
            for idx, quads_chunk in enumerate(split_list_into_chunks(quads_list, 100)):
                minified_quads: str = ""
                for quad in quads_chunk:
                    quad_str: str = minify_quad(quad)
                    minified_quads += quad_str + ","
                for player in self.server.game_clients_ref[evt.game_name]:
                    resp_evt: InitEvent = InitEvent(evt.type, datetime.datetime.now(), None, evt.game_name,
                                                    gsr.until_night, self.server.lobbies_ref[evt.game_name],
                                                    minified_quads, idx)
                    sock.sendto(json.dumps(resp_evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[player.id])
        else:
            gc: GameController = self.server.game_controller_ref
            if not gsrs["local"].board:
                gsrs["local"].until_night = evt.until_night
                gsrs["local"].board = Board(evt.cfg, gc.namer, [[None] * 100 for _ in range(90)],
                                            player_idx=gsrs["local"].player_idx, game_name=evt.game_name)
                gc.move_maker.board_ref = gsrs["local"].board
            split_quads: typing.List[str] = evt.quad_chunk.split(",")[:-1]
            for j in range(100):
                inflated_quad: Quad = inflate_quad(split_quads[j], location=(j, evt.quad_chunk_idx))
                gsrs["local"].board.quads[evt.quad_chunk_idx][j] = inflated_quad
            quads_populated: bool = True
            for i in range(90):
                for j in range(100):
                    if not gsrs["local"].board or gsrs["local"].board.quads[i][j] is None:
                        quads_populated = False
                        break
                if not quads_populated:
                    break
            if quads_populated:
                pyxel.mouse(visible=True)
                gc.last_turn_time = time.time()
                gsrs["local"].game_started = True
                gsrs["local"].on_menu = False
                # TODO add stats/achs later
                gsrs["local"].board.overlay.toggle_tutorial()
                gsrs["local"].board.overlay.total_settlement_count = \
                    sum(len(p.settlements) for p in gsrs["local"].players) + 1
                gc.music_player.stop_menu_music()
                gc.music_player.play_game_music()

    def process_update_event(self, evt: UpdateEvent, sock: socket.socket):
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
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        game_name: str = evt.game_name if self.server.is_server else "local"
        evt.settlement.location = (evt.settlement.location[0], evt.settlement.location[1])
        migrate_settlement(evt.settlement)
        # We need this for the initial settlements.
        for idx, u in enumerate(evt.settlement.garrison):
            evt.settlement.garrison[idx] = migrate_unit(u)
        player = next(pl for pl in gsrs[game_name].players if pl.faction == evt.player_faction)
        player.settlements.append(evt.settlement)
        for i in range(evt.settlement.location[1] - 5, evt.settlement.location[1] + 6):
            for j in range(evt.settlement.location[0] - 5, evt.settlement.location[0] + 6):
                player.quads_seen.add((j, i))
        if evt.from_settler:
            settler_unit = next(u for u in player.units if u.location == evt.settlement.location)
            player.units.remove(settler_unit)
        if self.server.is_server:
            self.server.namers_ref[evt.game_name].remove_settlement_name(evt.settlement.name,
                                                                         evt.settlement.quads[0].biome)
            for player in self.server.game_clients_ref[evt.game_name]:
                if player.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[player.id])
        else:
            self.server.game_controller_ref.namer.remove_settlement_name(evt.settlement.name,
                                                                         evt.settlement.quads[0].biome)

    def process_set_blessing_event(self, evt: SetBlessingEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        player.ongoing_blessing = OngoingBlessing(get_blessing(evt.blessing.blessing.name))
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_set_construction_event(self, evt: SetConstructionEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        player.resources = evt.player_resources
        setl = next(setl for setl in player.settlements if setl.name == evt.settlement_name)
        setl.current_work = evt.construction
        if hasattr(evt.construction.construction, "effect"):
            setl.current_work.construction = get_improvement(evt.construction.construction.name)
        elif hasattr(evt.construction.construction, "type"):
            setl.current_work.construction = get_project(evt.construction.construction.name)
        else:
            setl.current_work.construction = get_unit_plan(evt.construction.construction.name)
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_move_unit_event(self, evt: MoveUnitEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.initial_loc[0], evt.initial_loc[1]))
        unit.location = (evt.new_loc[0], evt.new_loc[1])
        for i in range(unit.location[1] - 5, unit.location[1] + 6):
            for j in range(unit.location[0] - 5, unit.location[0] + 6):
                player.quads_seen.add((j, i))
        unit.remaining_stamina = evt.new_stamina
        unit.besieging = evt.besieging
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_deploy_unit_event(self, evt: DeployUnitEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        setl = next(setl for setl in player.settlements if setl.name == evt.settlement_name)
        deployed = setl.garrison.pop()
        deployed.garrisoned = False
        deployed.location = (evt.location[0], evt.location[1])
        for i in range(deployed.location[1] - 5, deployed.location[1] + 6):
            for j in range(deployed.location[0] - 5, deployed.location[0] + 6):
                player.quads_seen.add((j, i))
        player.units.append(deployed)
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_garrison_unit_event(self, evt: GarrisonUnitEvent, sock: socket.socket):
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
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_investigate_event(self, evt: InvestigateEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.unit_loc[0], evt.unit_loc[1]))
        # TODO Loading from saves
        match evt.result:
            case InvestigationResult.FORTUNE:
                player.ongoing_blessing.fortune_consumed += player.ongoing_blessing.cost / 5
            case InvestigationResult.WEALTH:
                player.wealth += 25
            case InvestigationResult.VISION:
                for i in range(evt.relic_loc[1] - 10, evt.relic_loc[1] + 11):
                    for j in range(evt.relic_loc[0] - 10, evt.relic_loc[0] + 11):
                        player.quads_seen.add((j, i))
            case InvestigationResult.HEALTH:
                unit.plan.max_health += 5
                unit.health += 5
            case InvestigationResult.POWER:
                unit.plan.power += 5
            case InvestigationResult.STAMINA:
                unit.plan.total_stamina += 1
                unit.remaining_stamina = unit.plan.total_stamina
            case InvestigationResult.UPKEEP:
                unit.plan.cost = 0
            case InvestigationResult.ORE:
                player.resources.ore += 10
            case InvestigationResult.TIMBER:
                player.resources.timber += 10
            case InvestigationResult.MAGMA:
                player.resources.magma += 10
        self.server.game_states_ref[game_name].board.quads[evt.relic_loc[1]][evt.relic_loc[0]].is_relic = False
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_besiege_settlement_event(self, evt: BesiegeSettlementEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.unit_loc[0], evt.unit_loc[1]))
        setl: Settlement
        for p in self.server.game_states_ref[game_name].players:
            for s in p.settlements:
                if s.name == evt.settlement_name:
                    setl = s
        unit.besieging = True
        setl.besieged = True
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_buyout_construction_event(self, evt: BuyoutConstructionEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        setl = next(s for s in player.settlements if s.name == evt.settlement_name)
        complete_construction(setl, player)
        player.wealth = evt.player_wealth
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_disband_unit_event(self, evt: DisbandUnitEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.location[0], evt.location[1]))
        player.wealth += unit.plan.cost
        player.units.remove(unit)
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_attack_unit_event(self, evt: AttackUnitEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        player = next(pl for pl in gsrs[game_name].players if pl.faction == evt.player_faction)
        attacker = next(u for u in player.units if u.location == (evt.attacker_loc[0], evt.attacker_loc[1]))
        defender: (Unit | Heathen, typing.Optional[Player])
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
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])
        else:
            if defender[1] is not None and \
                    defender[1].faction == gsrs["local"].players[gsrs["local"].player_idx].faction:
                data.player_attack = False
                sel_u = gsrs["local"].board.selected_unit
                if sel_u is not None and sel_u.location == (evt.defender_loc[0], evt.defender_loc[1]) and \
                        data.defender_was_killed:
                    gsrs["local"].board.selected_unit = None
                    gsrs["local"].board.overlay.toggle_unit(None)
                gsrs["local"].board.overlay.toggle_attack(data)
                gsrs["local"].board.attack_time_bank = 0

    def process_attack_settlement_event(self, evt: AttackSettlementEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        player = next(pl for pl in gsrs[game_name].players if pl.faction == evt.player_faction)
        attacker = next(u for u in player.units if u.location == (evt.attacker_loc[0], evt.attacker_loc[1]))
        setl: (Settlement, Player)
        for p in gsrs[game_name].players:
            for s in p.settlements:
                if s.name == evt.settlement_name:
                    setl = s, p
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
                for i in range(setl[0].location[1] - 5, setl[0].location[1] + 6):
                    for j in range(setl[0].location[0] - 5, setl[0].location[0] + 6):
                        player.quads_seen.add((j, i))
            setl[1].settlements.remove(setl[0])
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])
        else:
            if setl[1].faction == gsrs["local"].players[gsrs["local"].player_idx].faction:
                data.player_attack = False
                sel_s = gsrs["local"].board.selected_settlement
                if sel_s is not None and sel_s.name == evt.settlement_name and data.setl_was_taken:
                    gsrs["local"].board.selected_settlement = None
                    gsrs["local"].board.overlay.toggle_settlement(None, gsrs["local"].players[gsrs["local"].player_idx])
                gsrs["local"].board.overlay.toggle_setl_attack(data)
                gsrs["local"].board.attack_time_bank = 0

    def process_heal_unit_event(self, evt: HealUnitEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        player = next(pl for pl in gsrs[game_name].players if pl.faction == evt.player_faction)
        healer = next(u for u in player.units if u.location == (evt.healer_loc[0], evt.healer_loc[1]))
        healed = next(u for u in player.units if u.location == (evt.healed_loc[0], evt.healed_loc[1]))
        heal(healer, healed)
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_board_deployer_event(self, evt: BoardDeployerEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        unit = next(u for u in player.units if u.location == (evt.initial_loc[0], evt.initial_loc[1]))
        deployer = next(u for u in player.units if u.location == (evt.deployer_loc[0], evt.deployer_loc[1]))
        unit.remaining_stamina = evt.new_stamina
        deployer.passengers.append(unit)
        player.units.remove(unit)
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_deployer_deploy_event(self, evt: DeployerDeployEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        player = next(pl for pl in self.server.game_states_ref[game_name].players
                      if pl.faction == evt.player_faction)
        deployer = next(u for u in player.units if u.location == (evt.deployer_loc[0], evt.deployer_loc[1]))
        deployed = deployer.passengers[evt.passenger_idx]
        deployed.location = (evt.deployed_loc[0], evt.deployed_loc[1])
        deployer.passengers[evt.passenger_idx:evt.passenger_idx + 1] = []
        player.units.append(deployed)
        for i in range(deployed.location[1] - 5, deployed.location[1] + 6):
            for j in range(deployed.location[0] - 5, deployed.location[0] + 6):
                player.quads_seen.add((j, i))
        if self.server.is_server:
            for p in self.server.game_clients_ref[evt.game_name]:
                if p.faction != evt.player_faction:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])

    def process_query_event(self, evt: QueryEvent, sock: socket.socket):
        if self.server.is_server:
            lobbies: typing.List[LobbyDetails] = []
            for name, cfg in self.server.lobbies_ref.items():
                gs: GameState = self.server.game_states_ref[name]
                player_details: typing.List[PlayerDetails] = []
                player_details.extend(self.server.game_clients_ref[name])
                for player in [p for p in gs.players if p.ai_playstyle]:
                    player_details.append(PlayerDetails(player.name, player.faction, 0, "", is_ai=True))
                lobbies.append(LobbyDetails(name, player_details, cfg, None if not gs.game_started else gs.turn))
            resp_evt: QueryEvent = QueryEvent(EventType.QUERY, datetime.datetime.now(), None, lobbies)
            sock.sendto(json.dumps(resp_evt, cls=SaveEncoder).encode(), self.server.clients_ref[evt.identifier])
        else:
            gc: GameController = self.server.game_controller_ref
            gc.menu.multiplayer_lobbies = evt.lobbies
            gc.menu.viewing_lobbies = True

    def process_leave_event(self, evt: LeaveEvent, sock: socket.socket):
        if self.server.is_server:
            old_clients = self.server.game_clients_ref[evt.lobby_name]
            client_to_remove: PlayerDetails = next(client for client in old_clients if client.id == evt.identifier)
            new_clients = [client for client in old_clients if client.id != evt.identifier]
            self.server.game_clients_ref[evt.lobby_name] = new_clients
            if not new_clients:
                self.server.game_clients_ref.pop(evt.lobby_name)
                self.server.lobbies_ref.pop(evt.lobby_name)
                self.server.game_states_ref.pop(evt.lobby_name)
            else:
                player = next(p for p in self.server.game_states_ref[evt.lobby_name].players
                              if p.faction == client_to_remove.faction)
                if self.server.game_states_ref[evt.lobby_name].game_started:
                    player.ai_playstyle = AIPlaystyle(random.choice(list(AttackPlaystyle)),
                                                      random.choice(list(ExpansionPlaystyle)))
                    evt.player_ai_playstyle = player.ai_playstyle
                evt.leaving_player_faction = player.faction
                for p in self.server.game_clients_ref[evt.lobby_name]:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])
                # TODO Can ping off an end turn event if everyone else left is ready
        else:
            gs = self.server.game_states_ref["local"]
            player = next(p for p in gs.players if p.faction == evt.leaving_player_faction)
            if gs.game_started:
                player.ai_playstyle = evt.player_ai_playstyle
                gs.board.overlay.toggle_player_change(player, changed_player_is_leaving=True)
            else:
                gs.players.remove(player)
                current_players: typing.List[PlayerDetails] = \
                    [p for p in self.server.game_controller_ref.menu.multiplayer_lobby.current_players if p.faction != evt.leaving_player_faction]
                self.server.game_controller_ref.menu.multiplayer_lobby.current_players = current_players

    def process_join_event(self, evt: JoinEvent, sock: socket.socket):
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        gc: GameController = self.server.game_controller_ref
        gs: GameState = gsrs[evt.lobby_name if self.server.is_server else "local"]
        if self.server.is_server:
            player_name: str
            if gs.game_started:
                replaced_player: Player = next(p for p in gs.players if p.faction == evt.player_faction)
                replaced_player.ai_playstyle = None
                player_name = replaced_player.name
            else:
                player_name = random.choice(PLAYER_NAMES)
                while any(player.name == player_name for player in self.server.game_clients_ref[evt.lobby_name]):
                    player_name = random.choice(PLAYER_NAMES)
                gs.players.append(Player(player_name, evt.player_faction, FACTION_COLOURS[evt.player_faction]))
            self.server.game_clients_ref[evt.lobby_name].append(PlayerDetails(player_name, evt.player_faction,
                                                                              evt.identifier, self.client_address[0]))
            # We can't just combine the player details from game_clients_ref and manually make the AI players' ones
            # because order matters for this - the player joining needs to get their player index right.
            player_details: typing.List[PlayerDetails] = []
            for player in gs.players:
                if player.ai_playstyle:
                    player_details.append(PlayerDetails(player.name, player.faction, 0, "", is_ai=True))
                else:
                    player_details.append(next(pd for pd in self.server.game_clients_ref[evt.lobby_name]
                                               if pd.faction == player.faction))
            lobby_details: LobbyDetails = LobbyDetails(evt.lobby_name,
                                                       player_details,
                                                       self.server.lobbies_ref[evt.lobby_name],
                                                       current_turn=None if not gs.game_started else gs.turn)
            evt.lobby_details = lobby_details
            for player in [p for p in self.server.game_clients_ref[evt.lobby_name] if p.faction != evt.player_faction or not gs.game_started]:
                sock.sendto(json.dumps(evt, cls=SaveEncoder).encode(), self.server.clients_ref[player.id])
            if gs.game_started:
                quads_list: typing.List[Quad] = list(chain.from_iterable(gs.board.quads))
                for idx, quads_chunk in enumerate(split_list_into_chunks(quads_list, 100)):
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
                    for qs_chunk in split_list_into_chunks(list(player.quads_seen), 100):
                        evt.quads_seen_chunk = minify_quads_seen(set(qs_chunk))
                        sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                    self.server.clients_ref[evt.identifier])
                evt.player_chunk_idx = None
                evt.total_quads_seen = None
                evt.quads_seen_chunk = None
                evt.heathens_chunk = minify_heathens(gs.heathens)
                evt.total_heathens = len(gs.heathens)
                sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                            self.server.clients_ref[evt.identifier])
        else:
            gc.namer.reset()
            gc.menu.multiplayer_lobby = LobbyDetails(evt.lobby_name,
                                                     evt.lobby_details.current_players,
                                                     evt.lobby_details.cfg,
                                                     evt.lobby_details.current_turn)
            if evt.lobby_details.current_turn:
                if gs.game_started and not evt.quads_seen_chunk:
                    replaced_player: Player = next(p for p in gs.players if p.faction == evt.player_faction)
                    replaced_player.ai_playstyle = None
                    if gs.players[gs.player_idx].faction != evt.player_faction:
                        gs.board.overlay.toggle_player_change(replaced_player,
                                                              changed_player_is_leaving=False)
                else:
                    if gs.player_idx is None:
                        for idx, player in enumerate(evt.lobby_details.current_players):
                            if player.faction == evt.player_faction:
                                gs.player_idx = idx
                            gs.players.append(Player(player.name, player.faction,
                                                                FACTION_COLOURS[player.faction]))
                        gc.menu.multiplayer_game_being_loaded = LoadedMultiplayerState()
                    if not gs.board:
                        gs.until_night = evt.until_night
                        gs.nighttime_left = evt.nighttime_left
                        gs.board = Board(evt.cfg, gc.namer, [[None] * 100 for _ in range(90)],
                                                    player_idx=gs.player_idx, game_name=evt.lobby_name)
                        gc.move_maker.board_ref = gs.board
                    if evt.quad_chunk:
                        split_quads: typing.List[str] = evt.quad_chunk.split(",")[:-1]
                        for j in range(100):
                            inflated_quad: Quad = inflate_quad(split_quads[j], location=(j, evt.quad_chunk_idx))
                            gs.board.quads[evt.quad_chunk_idx][j] = inflated_quad
                        gc.menu.multiplayer_game_being_loaded.quad_chunks_loaded += 1
                    if evt.player_chunk:
                        gs.players[evt.player_chunk_idx] = \
                            inflate_player(evt.player_chunk, gs.board.quads)
                        gc.menu.multiplayer_game_being_loaded.players_loaded += 1
                    if evt.quads_seen_chunk:
                        gc.menu.multiplayer_game_being_loaded.total_quads_seen = evt.total_quads_seen
                        inflated_quads_seen: typing.Set[typing.Tuple[int, int]] = \
                            inflate_quads_seen(evt.quads_seen_chunk)
                        gs.players[evt.player_chunk_idx].quads_seen.update(inflated_quads_seen)
                        gc.menu.multiplayer_game_being_loaded.quads_seen_loaded += len(inflated_quads_seen)
                    if evt.heathens_chunk:
                        gc.menu.multiplayer_game_being_loaded.total_heathens = evt.total_heathens
                        gs.heathens = inflate_heathens(evt.heathens_chunk)
                        gc.menu.multiplayer_game_being_loaded.heathens_loaded = True
                    gs.turn = evt.lobby_details.current_turn
                    state_populated: bool = True
                    for i in range(90):
                        for j in range(100):
                            if not gs.board or gs.board.quads[i][j] is None:
                                state_populated = False
                                break
                        if not state_populated:
                            break
                    for p in gs.players:
                        if not p.quads_seen:
                            state_populated = False
                    if gs.turn > 5 and not gs.heathens:
                        state_populated = False
                    # TODO there may be something weird going on with joining games later on - not all players/quads
                    #  seen being sent/received?
                    if state_populated:
                        pyxel.mouse(visible=True)
                        gc.last_turn_time = time.time()
                        gs.game_started = True
                        gs.on_menu = False
                        # TODO add stats/achs later
                        # Initialise the map position to the player's first settlement.
                        gs.map_pos = (clamp(gs.players[gs.player_idx].settlements[0].location[0] - 12, -1, 77),
                                              clamp(gs.players[gs.player_idx].settlements[0].location[1] - 11, -1, 69))
                        gs.board.overlay.current_player = gs.players[gs.player_idx]
                        gs.board.overlay.total_settlement_count = \
                            sum(len(p.settlements) for p in gs.players) + 1
                        gc.music_player.stop_menu_music()
                        gc.music_player.play_game_music()
                        gc.menu.multiplayer_game_being_loaded = None
            else:
                if gs.player_idx is None:
                    for idx, player in enumerate(evt.lobby_details.current_players):
                        if player.faction == evt.player_faction:
                            gs.player_idx = idx
                        gs.players.append(Player(player.name, player.faction, FACTION_COLOURS[player.faction]))
                    gc.menu.joining_game = False
                    gc.menu.viewing_lobbies = False
                    gc.menu.in_multiplayer_lobby = True
                    gc.menu.setup_option = SetupOption.START_GAME
                else:
                    new_player: PlayerDetails = evt.lobby_details.current_players[-1]
                    gs.players.append(Player(new_player.name, new_player.faction,
                                                        FACTION_COLOURS[new_player.faction]))

    def process_register_event(self, evt: RegisterEvent):
        self.server.clients_ref[evt.identifier] = self.client_address[0], evt.port

    def process_end_turn_event(self, evt: EndTurnEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        gs: GameState = self.server.game_states_ref[game_name]
        random.seed(gs.turn)
        if self.server.is_server:
            gs.ready_players.add(evt.identifier)
            if len(gs.ready_players) == len(self.server.game_clients_ref[evt.game_name]):
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
                    gs.process_climatic_effects(reseed_random=False)
                # We need to check for victories on the server as well so each player's imminent victories are
                # populated - this affects how units will move.
                gs.check_for_victory()
                gs.process_heathens()
                # TODO Something weird going on with settlement names? Noticed a duplicate
                gs.process_ais(self.server.move_makers_ref[evt.game_name])
                for p in self.server.game_clients_ref[evt.game_name]:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])
                gs.ready_players.clear()
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
                gs.process_climatic_effects(reseed_random=False)
            possible_vic = gs.check_for_victory()
            if possible_vic is not None:
                gs.board.overlay.toggle_victory(possible_vic)
                # TODO handle victory/defeat stats/achs in here later
            # TODO handle playtime stats/achs
            gs.board.overlay.total_settlement_count = sum(len(p.settlements) for p in gs.players)
            gs.process_heathens()
            gs.process_ais(self.server.game_controller_ref.move_maker)
            gs.board.waiting_for_other_players = False
            gs.processing_turn = False

    def process_unready_event(self, evt: UnreadyEvent):
        self.server.game_states_ref[evt.game_name].ready_players.remove(evt.identifier)

    def process_autofill_event(self, evt: AutofillEvent, sock: socket.socket):
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        if self.server.is_server:
            max_players: int = self.server.lobbies_ref[evt.lobby_name].player_count
            current_players: int = len(self.server.game_clients_ref[evt.lobby_name])
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
            for player in self.server.game_clients_ref[evt.lobby_name]:
                update_evt: AutofillEvent = AutofillEvent(EventType.AUTOFILL, datetime.datetime.now(), None,
                                                          evt.lobby_name, gsrs[evt.lobby_name].players)
                sock.sendto(json.dumps(update_evt, cls=SaveEncoder).encode(), self.server.clients_ref[player.id])
        else:
            gc: GameController = self.server.game_controller_ref
            previous_player_count = len(gc.menu.multiplayer_lobby.current_players)
            for player in evt.players[previous_player_count:]:
                player.imminent_victories = set(player.imminent_victories)
                player.quads_seen = set(player.quads_seen)
                new_player_detail: PlayerDetails = PlayerDetails(player.name, player.faction, 0, "", is_ai=True)
                gc.menu.multiplayer_lobby.current_players.append(new_player_detail)
                gsrs["local"].players.append(player)


class EventListener:
    def __init__(self, is_server: bool = False):
        self.game_states: typing.Dict[str, GameState] = {}
        self.namers: typing.Dict[str, Namer] = {}
        self.move_makers: typing.Dict[str, MoveMaker] = {}
        # self.events: typing.Dict[str, typing.List[Event]] = {}
        self.is_server: bool = is_server
        self.game_controller: typing.Optional[GameController] = None
        self.game_clients: typing.Dict[str, typing.List[PlayerDetails]] = {}
        self.lobbies: typing.Dict[str, GameConfig] = {}
        self.clients: typing.Dict[int, typing.Tuple[str, int]] = {}  # Hash identifier to (host, port).

    def run(self):
        # TODO eventually just have a static port for clients too - probably 20k range - do this last once all local
        #  testing is done (delete the upnp mappings for other ports when this is done)
        with socketserver.UDPServer(("0.0.0.0", 9999 if self.is_server else 0), RequestHandler) as server:
            if not self.is_server:
                dispatch_event(RegisterEvent(EventType.REGISTER, datetime.datetime.now(),
                                             hash((uuid.getnode(), os.getpid())), server.server_address[1]))
                upnp = UPnP()
                upnp.discover()
                upnp.selectigd()
                ip_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                ip_sock.connect(("8.8.8.8", 80))
                private_ip: str = ip_sock.getsockname()[0]
                upnp.addportmapping(server.server_address[1], "UDP", private_ip, server.server_address[1], "Microcosm", "")
            server.game_states_ref = self.game_states
            server.namers_ref = self.namers
            server.move_makers_ref = self.move_makers
            # server.events_ref = self.events
            server.is_server = self.is_server
            server.game_controller_ref = self.game_controller
            server.game_clients_ref = self.game_clients
            server.lobbies_ref = self.lobbies
            server.clients_ref = self.clients
            server.serve_forever()


"""
Things to be initialised after the lobby is created:
- Turn
- Until night
- Nighttime left
- Players
- Board
- AIs (if any)
"""
