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

from source.display.board import Board
from source.foundation.catalogue import FACTION_COLOURS, LOBBY_NAMES, PLAYER_NAMES, Namer, get_improvement, get_project, \
    get_unit_plan, get_blessing, get_heathen
from source.foundation.models import GameConfig, Player, PlayerDetails, LobbyDetails, Quad, Biome, ResourceCollection, \
    OngoingBlessing, InvestigationResult, Settlement, Unit, Heathen, Faction
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.networking.client import dispatch_event
from source.networking.events import Event, EventType, CreateEvent, InitEvent, UpdateEvent, UpdateAction, \
    FoundSettlementEvent, QueryEvent, LeaveEvent, JoinEvent, RegisterEvent, SetBlessingEvent, SetConstructionEvent, \
    MoveUnitEvent, DeployUnitEvent, GarrisonUnitEvent, InvestigateEvent, BesiegeSettlementEvent, \
    BuyoutConstructionEvent, DisbandUnitEvent, AttackUnitEvent, AttackSettlementEvent, EndTurnEvent, UnreadyEvent, \
    HealUnitEvent
from source.saving.save_encoder import ObjectConverter, SaveEncoder
from source.saving.save_migrator import migrate_settlement, migrate_quad
from source.util.calculator import split_list_into_chunks, complete_construction, attack, attack_setl, heal

HOST, SERVER_PORT, CLIENT_PORT = "localhost", 9999, 55555


class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        evt: Event = json.loads(self.request[0], object_hook=ObjectConverter)
        sock: socket.socket = self.request[1]
        self.process_event(evt, sock)

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
            self.process_leave_event(evt)
        elif evt.type == EventType.JOIN:
            self.process_join_event(evt, sock)
        elif evt.type == EventType.REGISTER:
            self.process_register_event(evt)
        elif evt.type == EventType.END_TURN:
            self.process_end_turn_event(evt, sock)
        elif evt.type == EventType.UNREADY:
            self.process_unready_event(evt)

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
            gc.menu.multiplayer_lobby_name = evt.lobby_name
            gc.menu.multiplayer_player_details = evt.player_details

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
            gsr.board = Board(self.server.lobbies_ref[evt.game_name], Namer())
            quads_list: typing.List[Quad] = list(chain.from_iterable(gsr.board.quads))
            for idx, quads_chunk in enumerate(split_list_into_chunks(quads_list, 100)):
                minified_quads: str = ""
                for quad in quads_chunk:
                    quad_str = f"{quad.biome.value[0]}{quad.wealth}{quad.harvest}{quad.zeal}{quad.fortune}"
                    if res := quad.resource:
                        if res.ore:
                            quad_str += "or"
                        elif res.timber:
                            quad_str += "t"
                        elif res.magma:
                            quad_str += "m"
                        elif res.aurora:
                            quad_str += "au"
                        elif res.bloodstone:
                            quad_str += "b"
                        elif res.obsidian:
                            quad_str += "ob"
                        elif res.sunstone:
                            quad_str += "s"
                        elif res.aquamarine:
                            quad_str += "aq"
                    if quad.is_relic:
                        quad_str += "ir"
                    quad_str += ","
                    minified_quads += quad_str
                for player in self.server.game_clients_ref[evt.game_name]:
                    resp_evt: InitEvent = InitEvent(evt.type, datetime.datetime.now(), None, evt.game_name,
                                                    gsr.until_night, self.server.lobbies_ref[evt.game_name],
                                                    minified_quads, idx)
                    sock.sendto(json.dumps(resp_evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[player.id])
        else:
            if not gsrs["local"].board:
                gsrs["local"].until_night = evt.until_night
                gsrs["local"].board = Board(evt.cfg, Namer(), [[None] * 100 for _ in range(90)],
                                            player_idx=gsrs["local"].player_idx, game_name=evt.game_name)
            split_quads: typing.List[str] = evt.quad_chunk.split(",")[:-1]
            for j in range(100):
                mini: str = split_quads[j]
                quad_biome: Biome
                match mini[0]:
                    case "D":
                        quad_biome = Biome.DESERT
                    case "F":
                        quad_biome = Biome.FOREST
                    case "S":
                        quad_biome = Biome.SEA
                    case "M":
                        quad_biome = Biome.MOUNTAIN
                quad_resource: typing.Optional[ResourceCollection] = None
                quad_is_relic: bool = False
                if len(mini) > 5:
                    if "or" in mini:
                        quad_resource = ResourceCollection(ore=1)
                    elif "t" in mini:
                        quad_resource = ResourceCollection(timber=1)
                    elif "m" in mini:
                        quad_resource = ResourceCollection(magma=1)
                    elif "au" in mini:
                        quad_resource = ResourceCollection(aurora=1)
                    elif "b" in mini:
                        quad_resource = ResourceCollection(bloodstone=1)
                    elif "ob" in mini:
                        quad_resource = ResourceCollection(obsidian=1)
                    elif "s" in mini:
                        quad_resource = ResourceCollection(sunstone=1)
                    elif "aq" in mini:
                        quad_resource = ResourceCollection(aquamarine=1)
                    quad_is_relic = mini.endswith("ir")
                expanded_quad: Quad = Quad(quad_biome, int(mini[1]), int(mini[2]), int(mini[3]), int(mini[4]),
                                           (j, evt.quad_chunk_idx), resource=quad_resource, is_relic=quad_is_relic)
                gsrs["local"].board.quads[evt.quad_chunk_idx][j] = expanded_quad
            quads_populated: bool = True
            for i in range(90):
                for j in range(100):
                    if not gsrs["local"].board or gsrs["local"].board.quads[i][j] is None:
                        quads_populated = False
                        break
                if not quads_populated:
                    break
            if quads_populated:
                gc: GameController = self.server.game_controller_ref
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

    def process_found_settlement_event(self, evt: FoundSettlementEvent, sock: socket.socket):
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        game_name: str = evt.game_name if self.server.is_server else "local"
        evt.settlement.location = (evt.settlement.location[0], evt.settlement.location[1])
        for i in range(len(evt.settlement.quads)):
            evt.settlement.quads[i] = migrate_quad(evt.settlement.quads[i],
                                                   (evt.settlement.location[0], evt.settlement.location[1]))
        player = next(pl for pl in gsrs[game_name].players if pl.faction == evt.player_faction)
        player.settlements.append(evt.settlement)
        if evt.from_settler:
            settler_unit = next(u for u in player.units if u.location == evt.settlement.location)
            player.units.remove(settler_unit)
        if self.server.is_server:
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
        # TODO Loading from saves is eventually going to be a problem because we're ignoring quads_seen
        match evt.result:
            case InvestigationResult.FORTUNE:
                player.ongoing_blessing.fortune_consumed += player.ongoing_blessing.cost / 5
            case InvestigationResult.WEALTH:
                player.wealth += 25
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
            if player.faction is not Faction.CONCENTRATED:
                player.settlements.append(setl)
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

    def process_query_event(self, evt: QueryEvent, sock: socket.socket):
        if self.server.is_server:
            lobbies: typing.List[LobbyDetails] = []
            for name, cfg in self.server.lobbies_ref.items():
                lobbies.append(LobbyDetails(name, self.server.game_clients_ref[name], cfg))
            resp_evt: QueryEvent = QueryEvent(EventType.QUERY, datetime.datetime.now(), None, lobbies)
            sock.sendto(json.dumps(resp_evt, cls=SaveEncoder).encode(), self.server.clients_ref[evt.identifier])
        else:
            gc: GameController = self.server.game_controller_ref
            gc.menu.multiplayer_lobbies = evt.lobbies

    def process_leave_event(self, evt: LeaveEvent):
        old_clients = self.server.game_clients_ref[evt.lobby_name]
        new_clients = [client for client in old_clients if client.id != evt.identifier]
        self.server.game_clients_ref[evt.lobby_name] = new_clients
        if not new_clients:
            self.server.game_clients_ref.pop(evt.lobby_name)
            self.server.lobbies_ref.pop(evt.lobby_name)
            self.server.game_states_ref.pop(evt.lobby_name)

    def process_join_event(self, evt: JoinEvent, sock: socket.socket):
        gsrs: typing.Dict[str, GameState] = self.server.game_states_ref
        if self.server.is_server:
            player_name = random.choice(PLAYER_NAMES)
            while any(player.name == player_name for player in self.server.game_clients_ref[evt.lobby_name]):
                player_name = random.choice(PLAYER_NAMES)
            gsrs[evt.lobby_name].players.append(Player(player_name, evt.player_faction,
                                                       FACTION_COLOURS[evt.player_faction]))
            self.server.game_clients_ref[evt.lobby_name].append(PlayerDetails(player_name, evt.player_faction,
                                                                              evt.identifier, self.client_address[0]))
            for player in self.server.game_clients_ref[evt.lobby_name]:
                update_evt: JoinEvent = JoinEvent(EventType.JOIN, datetime.datetime.now(), None, evt.lobby_name,
                                                  evt.player_faction, self.server.game_clients_ref[evt.lobby_name])
                sock.sendto(json.dumps(update_evt, cls=SaveEncoder).encode(),
                            self.server.clients_ref[player.id])
        else:
            if gsrs["local"].player_idx is None:
                for idx, player in enumerate(evt.player_details):
                    if player.faction == evt.player_faction:
                        gsrs["local"].player_idx = idx
                    gsrs["local"].players.append(Player(player.name, player.faction, FACTION_COLOURS[player.faction]))
            else:
                new_player: PlayerDetails = evt.player_details[-1]
                gsrs["local"].players.append(Player(new_player.name, new_player.faction,
                                                    FACTION_COLOURS[new_player.faction]))
            gc: GameController = self.server.game_controller_ref
            gc.menu.multiplayer_lobby_name = evt.lobby_name
            gc.menu.multiplayer_player_details = evt.player_details

    def process_register_event(self, evt: RegisterEvent):
        self.server.clients_ref[evt.identifier] = self.client_address[0], evt.port

    def process_end_turn_event(self, evt: EndTurnEvent, sock: socket.socket):
        game_name: str = evt.game_name if self.server.is_server else "local"
        gs: GameState = self.server.game_states_ref[game_name]
        if self.server.is_server:
            gs.ready_players.add(evt.identifier)
            if len(gs.ready_players) == len(gs.players):
                for idx, player in enumerate(gs.players):
                    gs.process_player(player, idx == gs.player_idx)
                if gs.turn % 5 == 0:
                    new_heathen_loc: (int, int) = random.randint(0, 89), random.randint(0, 99)
                    gs.heathens.append(get_heathen(new_heathen_loc, gs.turn))
                    evt.new_heathen_loc = new_heathen_loc
                for h in gs.heathens:
                    h.remaining_stamina = h.plan.total_stamina
                    if h.health < h.plan.max_health:
                        h.health = min(h.health + h.plan.max_health * 0.1, h.plan.max_health)
                gs.turn += 1
                # TODO process climatic effects in here, then send out update
                for p in self.server.game_clients_ref[evt.game_name]:
                    sock.sendto(json.dumps(evt, separators=(",", ":"), cls=SaveEncoder).encode(),
                                self.server.clients_ref[p.id])
                gs.ready_players.clear()
                # TODO handle heathen movements
        else:
            for idx, player in enumerate(gs.players):
                gs.process_player(player, idx == gs.player_idx)
            if evt.new_heathen_loc:
                gs.heathens.append(get_heathen((evt.new_heathen_loc[0], evt.new_heathen_loc[1]), gs.turn))
            for h in gs.heathens:
                h.remaining_stamina = h.plan.total_stamina
                if h.health < h.plan.max_health:
                    h.health = min(h.health + h.plan.max_health * 0.1, h.plan.max_health)
            gs.board.overlay.remove_warning_if_possible()
            gs.turn += 1
            possible_vic = gs.check_for_victory()
            if possible_vic is not None:
                gs.board.overlay.toggle_victory(possible_vic)
                # TODO handle victory/defeat stats/achs in here later
            gs.board.waiting_for_other_players = False
            # TODO handle playtime stats/achs
            gs.board.overlay.total_settlement_count = sum(len(p.settlements) for p in gs.players)

    def process_unready_event(self, evt: UnreadyEvent):
        self.server.game_states_ref[evt.game_name].ready_players.remove(evt.identifier)


class EventListener:
    def __init__(self, is_server: bool = False):
        self.game_states: typing.Dict[str, GameState] = {}
        # self.events: typing.Dict[str, typing.List[Event]] = {}
        self.is_server: bool = is_server
        self.game_controller: typing.Optional[GameController] = None
        self.game_clients: typing.Dict[str, typing.List[PlayerDetails]] = {}
        self.lobbies: typing.Dict[str, GameConfig] = {}
        self.clients: typing.Dict[int, typing.Tuple[str, int]] = {}  # Hash identifier to (host, port).

    def run(self):
        with socketserver.UDPServer((HOST, SERVER_PORT if self.is_server else 0), RequestHandler) as server:
            if not self.is_server:
                dispatch_event(RegisterEvent(EventType.REGISTER, datetime.datetime.now(),
                                             hash((uuid.getnode(), os.getpid())), server.server_address[1]))
            server.game_states_ref = self.game_states
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
