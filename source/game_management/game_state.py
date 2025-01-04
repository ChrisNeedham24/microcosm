import hashlib
import json
import random
from itertools import chain
from typing import Optional, List, Set, Tuple

from source.display.board import Board
from source.saving.game_save_manager import save_stats_achievements
from source.saving.save_encoder import SaveEncoder
from source.util.calculator import clamp, attack, get_setl_totals, complete_construction, \
    get_resources_for_settlement, update_player_quads_seen_around_point
from source.foundation.catalogue import get_heathen, get_default_unit, FACTION_COLOURS, Namer
from source.foundation.models import Heathen, Quad
from source.foundation.models import Player, Settlement, CompletedConstruction, Unit, HarvestStatus, EconomicStatus, \
    AttackPlaystyle, GameConfig, Victory, VictoryType, AIPlaystyle, ExpansionPlaystyle, Faction, Project
from source.game_management.movemaker import MoveMaker


class GameState:
    """
    The class that holds the logical Microcosm game state, tracking the state of the current game.
    """

    def __init__(self):
        """
        Creates the initial game state.
        """
        self.board: Optional[Board] = None
        self.players: List[Player] = []
        self.heathens: List[Heathen] = []

        self.on_menu = True
        self.game_started = False

        random.seed()
        # The map begins at a random position.
        self.map_pos: (int, int) = random.randint(0, 76), random.randint(0, 68)
        self.turn = 1

        # There will always be a 10-20 turn break between nights.
        self.until_night: int = random.randint(10, 20)
        # Also keep track of how many turns of night are left. If this is 0, it is daytime.
        self.nighttime_left = 0

        # We can hard-code the version here and update it when required. This was introduced so that saves with
        # resources can be distinguished from those without.
        self.game_version: float = 4.0

        # The index of the player in the overall list of players. Will always be zero for single-player games, but will
        # be variable for multiplayer ones.
        self.player_idx: int = 0
        # Whether the local player has determined their player index yet. This exists so that the server can
        # differentiate players that are yet to find their faction.
        self.located_player_idx: bool = False
        # The set of identifiers for players who have ended their turn and are ready for it to be processed.
        self.ready_players: Set[int] = set()
        # Whether the previous turn is being processed.
        self.processing_turn: bool = False

    def __hash__(self) -> int:
        """
        Generate a hash for the game state.

        This is currently only used to ensure that there is synchronisation between the game server and clients in
        multiplayer games.

        The components that make up the hash are those that make up a standard save file, and that also change during
        the course of a game. As such, the game config and version are not included, excluded along with other fields
        such as whether the user is on the menu, the set of ready players, etc.
        """
        # Each component of the hash needs to be bytes (or bytes-like) to be included in the hash. We use json.dumps()
        # because Player, Heathen, Quad, and the dataclasses that make them up, are unhashable by default. Rather than
        # implement a __hash__ function for each of them, it's easier to isolate that here.
        players_bytes: bytes = json.dumps(self.players, separators=(",", ":"), cls=SaveEncoder).encode()
        heathens_bytes: bytes = json.dumps(self.heathens, separators=(",", ":"), cls=SaveEncoder).encode()
        turn_bytes: bytes = str(self.turn).encode()
        until_night_bytes: bytes = str(self.until_night).encode()
        nighttime_left_bytes: bytes = str(self.nighttime_left).encode()
        # We use chain.from_iterable() here because the quads array is 2D.
        quads_bytes: bytes = json.dumps(list(chain.from_iterable(self.board.quads)),
                                        separators=(",", ":"), cls=SaveEncoder).encode()
        # We generate a SHA256 hash here rather than just using the built-in hash() function with a tuple of the above.
        # We do this because, since Python 3.3, the built-in function gives different results for the same data based on
        # a random hash seed. This is done to address a vulnerability, but since we need a stable hashing algorithm, we
        # use hashlib instead.
        sha256_hash = hashlib.sha256()
        sha256_hash.update(players_bytes)
        sha256_hash.update(heathens_bytes)
        sha256_hash.update(turn_bytes)
        sha256_hash.update(until_night_bytes)
        sha256_hash.update(nighttime_left_bytes)
        sha256_hash.update(quads_bytes)
        # We have to restrict the digest down to just its first eight digits to ensure that it fits in 64-bit
        # architectures. If we don't do this, Python will do further post-processing which can be platform and
        # architecture dependent - naturally we don't want anything like that.
        return int.from_bytes(sha256_hash.digest()[:8], byteorder="big", signed=True)

    def reset_state(self):
        """
        Resets the game state. Used when returning to the menu or creating a new multiplayer game.
        """
        self.board = None
        self.players = []
        self.heathens = []
        random.seed()
        self.map_pos = random.randint(0, 76), random.randint(0, 68)
        self.turn = 1
        self.until_night = random.randint(10, 20)
        self.nighttime_left = 0
        self.player_idx = 0
        self.located_player_idx = False
        self.ready_players = set()
        self.processing_turn = False

    def gen_players(self, cfg: GameConfig):
        """
        Generates the players for the game based on the supplied config.
        :param cfg: The game config.
        """
        self.players = [Player("The Chosen One", cfg.player_faction, FACTION_COLOURS[cfg.player_faction])]
        factions = list(Faction)
        # Ensure that an AI player doesn't choose the same faction as the player.
        factions.remove(cfg.player_faction)
        for i in range(1, cfg.player_count):
            faction = random.choice(factions)
            factions.remove(faction)
            self.players.append(Player(f"NPC{i}", faction, FACTION_COLOURS[faction],
                                       ai_playstyle=AIPlaystyle(random.choice(list(AttackPlaystyle)),
                                                                random.choice(list(ExpansionPlaystyle)))))

    def check_for_warnings(self) -> bool:
        """
        Check if the player has anything preventing them from ending their turn, e.g. idle settlements, no ongoing
        blessing, or negative wealth per turn.
        :return: Whether the player should be prevented from ending their turn.
        """
        problematic_settlements = []
        total_wealth = 0
        for setl in self.players[self.player_idx].settlements:
            if setl.current_work is None:
                problematic_settlements.append(setl)
            total_wealth += sum(quad.wealth for quad in setl.quads)
            total_wealth += sum(imp.effect.wealth for imp in setl.improvements)
            total_wealth += (setl.level - 1) * 0.25 * total_wealth
            if setl.economic_status is EconomicStatus.RECESSION:
                total_wealth = 0
            elif setl.economic_status is EconomicStatus.BOOM:
                total_wealth *= 1.5
        for unit in self.players[self.player_idx].units:
            if not unit.garrisoned:
                total_wealth -= unit.plan.cost / 10
        if self.players[self.player_idx].faction == Faction.GODLESS:
            total_wealth *= 1.25
        elif self.players[self.player_idx].faction == Faction.ORTHODOX:
            total_wealth *= 0.75
        has_no_blessing = self.players[self.player_idx].ongoing_blessing is None
        will_have_negative_wealth = \
            (self.players[self.player_idx].wealth + total_wealth) < 0 and len(self.players[self.player_idx].units) > 0
        if not self.board.overlay.is_warning() and \
                (len(problematic_settlements) > 0 or has_no_blessing or will_have_negative_wealth):
            self.board.overlay.toggle_warning(problematic_settlements, has_no_blessing, will_have_negative_wealth)
            return True
        return False

    def process_player(self, player: Player, is_current_player: bool):
        """
        Process a player when they are ending their turn. The following things are done in this method:

        - Update settlement harvest and economic statuses.
        - Update strength for besieged or recently besieged settlements.
        - Reset unit and garrison unit state.
        - Update settlement satisfaction.
        - Process settlement current work.
        - Update settlement level.
        - Show notifications for completed constructions or blessings.
        - Process ongoing blessing.
        - Update player wealth, auto-selling units if required.
        :param player: The player being processed.
        :param is_current_player: Whether the player being processed is the player on this machine.
        """
        overall_fortune = 0
        overall_wealth = 0
        completed_constructions: List[CompletedConstruction] = []
        levelled_up_settlements: List[Settlement] = []
        for setl in player.settlements:
            # Based on the settlement's satisfaction, place the settlement in a specific state of wealth and
            # harvest. More specifically, a satisfaction of less than 20 will yield 0 wealth and 0 harvest, a
            # satisfaction of [20, 40) will yield 0 harvest, a satisfaction of [60, 80) will yield 150% harvest,
            # and a satisfaction of 80 or more will yield 150% wealth and 150% harvest.
            if setl.satisfaction < 20:
                if player.faction != Faction.AGRICULTURISTS:
                    setl.harvest_status = HarvestStatus.POOR
                if player.faction != Faction.CAPITALISTS:
                    setl.economic_status = EconomicStatus.RECESSION
            elif setl.satisfaction < 40:
                if player.faction != Faction.AGRICULTURISTS:
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

            # If the settlement is under siege, decrease its strength based on the number of besieging units.
            if setl.besieged:
                besieging_units: List[Unit] = []
                for p in self.players:
                    if p is not player:
                        for u in p.units:
                            for setl_quad in setl.quads:
                                if abs(u.location[0] - setl_quad.location[0]) <= 1 and \
                                        abs(u.location[1] - setl_quad.location[1]) <= 1:
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
                setl.satisfaction -= (1 if player.faction == Faction.CAPITALISTS else 0.5)
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
            level_cap = 5 if player.faction == Faction.RAVENOUS else 10
            if setl.harvest_reserves >= pow(setl.level, 2) * 25 and setl.level < level_cap:
                setl.level += 1
                levelled_up_settlements.append(setl)
                # For players of The Concentrated faction, every time their one and only settlement levels up, it gains
                # an extra quad. The quad gained is determined by calculating which adjacent quad has the highest total
                # yield.
                if player.faction == Faction.CONCENTRATED:
                    best_quad_with_yield: Tuple[Quad, float] = None, 0
                    for setl_quad in setl.quads:
                        for i in range(setl_quad.location[0] - 1, setl_quad.location[0] + 2):
                            for j in range(setl_quad.location[1] - 1, setl_quad.location[1] + 2):
                                if 0 <= i <= 99 and 0 <= j <= 89:
                                    quad_to_test = self.board.quads[j][i]
                                    quad_yield = (quad_to_test.wealth + quad_to_test.harvest +
                                                  quad_to_test.zeal + quad_to_test.fortune)
                                    if quad_to_test not in setl.quads and quad_yield > best_quad_with_yield[1]:
                                        best_quad_with_yield = quad_to_test, quad_yield
                    setl.quads.append(best_quad_with_yield[0])
                    setl.resources = \
                        get_resources_for_settlement([quad.location for quad in setl.quads], self.board.quads)
                    update_player_quads_seen_around_point(player, best_quad_with_yield[0].location)

            if setl.resources:
                # Only core resources accumulate.
                player.resources.ore += setl.resources.ore
                player.resources.timber += setl.resources.timber
                player.resources.magma += setl.resources.magma

        # Just reset rare resources each turn - it's easier that way.
        player.resources.aurora = sum(1 for setl in player.settlements if setl.resources.aurora)
        player.resources.bloodstone = sum(1 for setl in player.settlements if setl.resources.bloodstone)
        player.resources.obsidian = sum(1 for setl in player.settlements if setl.resources.obsidian)
        player.resources.sunstone = sum(1 for setl in player.settlements if setl.resources.sunstone)
        player.resources.aquamarine = sum(1 for setl in player.settlements if setl.resources.aquamarine)

        # Show notifications if the player's constructions have completed or one of their settlements has levelled
        # up.
        if is_current_player and len(completed_constructions) > 0:
            self.board.overlay.toggle_construction_notification(completed_constructions)
        if is_current_player and len(levelled_up_settlements) > 0:
            self.board.overlay.toggle_level_up_notification(levelled_up_settlements)
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
                # Show a notification if the player is the one on this machine.
                if is_current_player:
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

    def process_climatic_effects(self, reseed_random: bool = True):
        """
        Updates current night tracking variables, and toggles nighttime if the correct turn arrives.
        :param reseed_random: Whether to reseed the random number generator. Will be False for multiplayer games as all
                              clients need to have the same random numbers generated so that they can stay in sync.
        """
        if reseed_random:
            random.seed()
        if self.nighttime_left == 0:
            self.until_night -= 1
            if self.until_night == 0:
                self.board.overlay.toggle_night(True)
                # Nights last for between 5 and 20 turns.
                self.nighttime_left = random.randint(5, 20)
                for h in self.heathens:
                    h.plan.power = round(2 * h.plan.power)
                for p in self.players:
                    if p.faction == Faction.NOCTURNE:
                        for u in p.units:
                            u.plan.power = round(2 * u.plan.power)
                        for setl in p.settlements:
                            for unit in setl.garrison:
                                unit.plan.power = round(2 * unit.plan.power)
        else:
            self.nighttime_left -= 1
            if self.nighttime_left == 0:
                self.until_night = random.randint(10, 20)
                self.board.overlay.toggle_night(False)
                for h in self.heathens:
                    h.plan.power = round(h.plan.power / 2)
                for p in self.players:
                    if p.faction == Faction.NOCTURNE:
                        for u in p.units:
                            u.plan.power = round(u.plan.power / 4)
                            u.health = round(u.health / 2)
                            u.plan.max_health = round(u.plan.max_health / 2)
                            u.plan.total_stamina = round(u.plan.total_stamina / 2)
                        for setl in p.settlements:
                            for unit in setl.garrison:
                                unit.plan.power = round(unit.plan.power / 4)
                                unit.health = round(unit.health / 2)
                                unit.plan.max_health = round(unit.plan.max_health / 2)
                                unit.plan.total_stamina = round(unit.plan.total_stamina / 2)

    def end_turn(self) -> bool:
        """
        Ends the current game turn, processing settlements, blessings, and units.
        :return: Whether the turn was successfully ended. Will be False in cases where a warning is generated, or the
        game ends.
        """
        # First make sure the player hasn't ended their turn without a construction or blessing.
        if self.check_for_warnings():
            return False

        for idx, player in enumerate(self.players):
            self.process_player(player, idx == self.player_idx)

        # Spawn a heathen every 5 turns.
        if self.turn % 5 == 0:
            heathen_loc = random.randint(0, 89), random.randint(0, 99)
            self.heathens.append(get_heathen(heathen_loc, self.turn))

        # Reset all heathens.
        for heathen in self.heathens:
            heathen.remaining_stamina = heathen.plan.total_stamina
            if heathen.health < heathen.plan.max_health:
                heathen.health = min(heathen.health + heathen.plan.max_health * 0.1, heathen.plan.max_health)

        self.board.overlay.remove_warning_if_possible()
        self.turn += 1

        # Make night-related calculations, but only if climatic effects are enabled.
        if self.board.game_config.climatic_effects:
            self.process_climatic_effects()

        possible_victory = self.check_for_victory()
        if possible_victory is not None:
            self.board.overlay.toggle_victory(possible_victory)
            # Update the victory/defeat statistics, depending on whether the player achieved a victory, or an AI player
            # did. Also check for any newly-obtained achievements.
            if possible_victory.player is self.players[self.player_idx]:
                if new_achs := save_stats_achievements(self, victory_to_add=possible_victory.type):
                    self.board.overlay.toggle_ach_notif(new_achs)
            # We need an extra eliminated check in here because if the player was eliminated at the same time that the
            # victory was achieved, e.g. in an elimination victory between two players, the defeat count would be
            # incremented twice - once here and once when they are marked as eliminated.
            elif not self.players[self.player_idx].eliminated:
                if new_achs := save_stats_achievements(self, increment_defeats=True):
                    self.board.overlay.toggle_ach_notif(new_achs)
            return False
        return True

    def check_for_victory(self) -> Optional[Victory]:
        """
        Check if any of the six victories have been achieved by any of the players. Also check if any players are close
        to a victory.
        :return: A Victory, if one has been achieved.
        """
        close_to_vics: List[Victory] = []
        all_setls = []
        for pl in self.players:
            all_setls.extend(pl.settlements)

        players_with_setls = 0
        for p in self.players:
            if len(p.settlements) > 0:
                jubilated_setls = 0
                lvl_ten_setls = 0
                constructing_sanctum = False
                constructed_sanctum = False

                # If a player controls all settlements bar one, they are close to an ELIMINATION victory.
                if len(p.settlements) + 1 == len(all_setls):
                    if VictoryType.ELIMINATION not in p.imminent_victories:
                        close_to_vics.append(Victory(p, VictoryType.ELIMINATION))
                        p.imminent_victories.add(VictoryType.ELIMINATION)
                # However, if a new settlement has been founded in the last turn, or the player has lost one of their
                # settlements, remove the imminent victory.
                elif VictoryType.ELIMINATION in p.imminent_victories:
                    p.imminent_victories.remove(VictoryType.ELIMINATION)

                players_with_setls += 1
                for s in p.settlements:
                    if s.satisfaction == 100:
                        jubilated_setls += 1
                    if s.level == 10:
                        lvl_ten_setls += 1
                    if any(imp.name == "Holy Sanctum" for imp in s.improvements):
                        constructed_sanctum = True
                    # If a player is currently constructing the Holy Sanctum, they are close to a VIGOUR victory.
                    elif s.current_work is not None and s.current_work.construction.name == "Holy Sanctum":
                        constructing_sanctum = True
                if constructing_sanctum:
                    if VictoryType.VIGOUR not in p.imminent_victories:
                        close_to_vics.append(Victory(p, VictoryType.VIGOUR))
                        p.imminent_victories.add(VictoryType.VIGOUR)
                # If the player is no longer constructing the Holy Sanctum in any of their settlements, remove the
                # imminent victory.
                elif VictoryType.VIGOUR in p.imminent_victories:
                    p.imminent_victories.remove(VictoryType.VIGOUR)
                if jubilated_setls >= 5:
                    p.jubilation_ctr += 1
                    # If a player has achieved 100% satisfaction in 5 settlements, they are close to (25 turns away)
                    # from a JUBILATION victory.
                    if VictoryType.JUBILATION not in p.imminent_victories:
                        close_to_vics.append(Victory(p, VictoryType.JUBILATION))
                        p.imminent_victories.add(VictoryType.JUBILATION)
                else:
                    p.jubilation_ctr = 0
                    if VictoryType.JUBILATION in p.imminent_victories:
                        p.imminent_victories.remove(VictoryType.JUBILATION)
                # If the player has maintained 5 settlements at 100% satisfaction for 25 turns, they have achieved a
                # JUBILATION victory.
                if p.jubilation_ctr == 25:
                    return Victory(p, VictoryType.JUBILATION)
                # If the player has at least 10 settlements of level 10, they have achieved a GLUTTONY victory.
                if lvl_ten_setls >= 10:
                    return Victory(p, VictoryType.GLUTTONY)
                # If a player has 8 level 10 settlements, they are close to a GLUTTONY victory.
                if lvl_ten_setls >= 8:
                    if VictoryType.GLUTTONY not in p.imminent_victories:
                        close_to_vics.append(Victory(p, VictoryType.GLUTTONY))
                        p.imminent_victories.add(VictoryType.GLUTTONY)
                # If a player has lost one of their level 10 settlements since last turn, remove the imminent victory.
                elif VictoryType.GLUTTONY in p.imminent_victories:
                    p.imminent_victories.remove(VictoryType.GLUTTONY)
                # If the player has constructed the Holy Sanctum, they have achieved a VIGOUR victory.
                if constructed_sanctum:
                    return Victory(p, VictoryType.VIGOUR)
            # Human players have a special advantage over the AIs - if they have a settler unit despite losing all of
            # their settlements, they are considered to still be in the game.
            elif not (not p.ai_playstyle and any(unit.plan.can_settle for unit in p.units)) and not p.eliminated:
                p.eliminated = True
                self.board.overlay.toggle_elimination(p)
                # Update the defeats stat if the eliminated player is the human player on this machine.
                if self.located_player_idx and p == self.players[self.player_idx]:
                    if new_achs := save_stats_achievements(self, increment_defeats=True):
                        self.board.overlay.toggle_ach_notif(new_achs)
            # If the player has accumulated at least 100k wealth over the game, they have achieved an AFFLUENCE victory.
            if p.accumulated_wealth >= 100000:
                return Victory(p, VictoryType.AFFLUENCE)
            # If a player has accumulated at least 75k wealth over the game, they are close to an AFFLUENCE victory.
            # Note that we don't need to worry about removing this victory type from the player's imminent victories due
            # to the fact that accumulated wealth is never subtracted from; it can never reach 75000 and then go below
            # it again.
            if p.accumulated_wealth >= 75000 and VictoryType.AFFLUENCE not in p.imminent_victories:
                close_to_vics.append(Victory(p, VictoryType.AFFLUENCE))
                p.imminent_victories.add(VictoryType.AFFLUENCE)
            # If the player has undergone the blessings for all three pieces of ardour, they have achieved a
            # SERENDIPITY victory.
            ardour_pieces = len([bls for bls in p.blessings if "Piece of" in bls.name])
            if ardour_pieces == 3:
                return Victory(p, VictoryType.SERENDIPITY)
            # If a player has undergone two of the required three blessings for the pieces of ardour, they are close to
            # a SERENDIPITY victory. Note that we don't need to worry about removing this victory type from the player's
            # imminent victories due to the fact that once a blessing is completed, it cannot be uncompleted.
            if ardour_pieces == 2 and VictoryType.SERENDIPITY not in p.imminent_victories:
                close_to_vics.append(Victory(p, VictoryType.SERENDIPITY))
                p.imminent_victories.add(VictoryType.SERENDIPITY)

        if players_with_setls == 1:
            other_human_player_with_settler: bool = False
            for p in self.players:
                has_settler: bool = any(unit.plan.can_settle for unit in p.units)
                if not p.ai_playstyle and has_settler and not p.settlements:
                    other_human_player_with_settler = True
                    break
            if not other_human_player_with_settler:
                # If there is only one player with settlements (and no other human players have a settler), they have
                # achieved an ELIMINATION victory.
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
        all_units: List[Unit] = []
        banned_quads: Set[Tuple[int, int]] = set()
        for player in self.players:
            for unit in player.units:
                # Heathens will not attack Infidel units.
                if player.faction != Faction.INFIDELS:
                    all_units.append(unit)
                # Ban heathens from all unit locations so that they don't occupy the same quad.
                else:
                    banned_quads.add(unit.location)
            # During nighttime, heathens cannot be within a certain number of quads of settlements with sunstone
            # resources. For example, heathens cannot be within 6 quads of a settlement with 1 sunstone resource, and
            # they cannot be within 9 quads of a settlement with 2 sunstone resources.
            for setl in player.settlements:
                for setl_quad in setl.quads:
                    if self.nighttime_left > 0 and setl.resources.sunstone:
                        exclusion_range = 3 * (1 + setl.resources.sunstone)
                        for i in range(setl_quad.location[0] - exclusion_range,
                                       setl_quad.location[0] + exclusion_range + 1):
                            for j in range(setl_quad.location[1] - exclusion_range,
                                           setl_quad.location[1] + exclusion_range + 1):
                                banned_quads.add((i, j))
                    # Ban heathens from all settlement locations so that they don't occupy the same quad.
                    else:
                        banned_quads.add(setl_quad.location)
        for heathen in self.heathens:
            within_range: Optional[Unit] = None
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
                # Only show the attack overlay if the unit attacked was the player's.
                if self.located_player_idx and within_range in self.players[self.player_idx].units:
                    self.board.overlay.toggle_attack(data)
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
            else:
                # If there are no units within range, just move randomly. Attempt this five times, and if a valid
                # location (i.e. one away from the influence of a settlement with one or more sunstones) is not found,
                # the heathen dies.
                found_valid_loc = False
                for _ in range(5):
                    x_movement = random.randint(-heathen.remaining_stamina, heathen.remaining_stamina)
                    rem_movement = heathen.remaining_stamina - abs(x_movement)
                    y_movement = random.choice([-rem_movement, rem_movement])
                    new_loc = (clamp(heathen.location[0] + x_movement, 0, 99),
                               clamp(heathen.location[1] + y_movement, 0, 89))
                    if new_loc not in banned_quads:
                        heathen.location = new_loc
                        heathen.remaining_stamina -= abs(x_movement) + abs(y_movement)
                        found_valid_loc = True
                        break
                if not found_valid_loc:
                    self.heathens.remove(heathen)

            # Players of the Infidels faction share vision with Heathen units.
            for player in self.players:
                if player.faction == Faction.INFIDELS:
                    update_player_quads_seen_around_point(player, heathen.location)
                    break

    def initialise_ais(self, namer: Namer):
        """
        Initialise the AI players by adding their first settlement in a random location.
        """
        for player in self.players:
            if player.ai_playstyle is not None:
                setl_coords = random.randint(0, 99), random.randint(0, 89)
                quad_biome = self.board.quads[setl_coords[1]][setl_coords[0]].biome
                setl_name = namer.get_settlement_name(quad_biome)
                setl_resources = get_resources_for_settlement([setl_coords], self.board.quads)
                new_settl = Settlement(setl_name, setl_coords, [],
                                       [self.board.quads[setl_coords[1]][setl_coords[0]]], setl_resources,
                                       [get_default_unit(setl_coords)])
                match player.faction:
                    case Faction.CONCENTRATED:
                        new_settl.strength *= 2
                        new_settl.max_strength *= 2
                    case Faction.FRONTIERSMEN:
                        new_settl.satisfaction = 75.0
                    case Faction.IMPERIALS:
                        new_settl.strength /= 2
                        new_settl.max_strength /= 2

                if new_settl.resources.obsidian:
                    new_settl.strength *= (1 + 0.5 * new_settl.resources.obsidian)
                    new_settl.max_strength *= (1 + 0.5 * new_settl.resources.obsidian)

                player.settlements.append(new_settl)
                update_player_quads_seen_around_point(player, new_settl.location)

    def process_ais(self, move_maker: MoveMaker):
        """
        Process the moves for each AI player.
        """
        for player in self.players:
            if player.ai_playstyle is not None:
                move_maker.make_move(player, self.players, self.board.quads, self.board.game_config,
                                     self.nighttime_left > 0, self.player_idx if self.located_player_idx else None)
