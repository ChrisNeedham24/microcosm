import random
import typing

from board import Board
from calculator import clamp, attack, get_setl_totals, complete_construction
from catalogue import get_heathen, \
    get_default_unit, FACTION_COLOURS, Namer
from models import Heathen
from models import Player, Settlement, CompletedConstruction, Unit, HarvestStatus, \
    EconomicStatus, AttackPlaystyle, GameConfig, Victory, VictoryType, AIPlaystyle, \
    ExpansionPlaystyle, Faction, Project
from movemaker import MoveMaker


class GameState:
    """
    The class that holds the logical Microcosm game state, tracking the state of the current game.
    """
    def __init__(self):
        """
        Creates the initial game state.
        """
        self.board: typing.Optional[Board] = None
        self.players: typing.List[Player] = []
        self.heathens: typing.List[Heathen] = []

        self.on_menu = True
        self.game_started = False

        # The map begins at a random position.
        self.map_pos: (int, int) = random.randint(0, 76), random.randint(0, 68)
        self.turn = 1

        random.seed()
        # There will always be a 10-20 turn break between nights.
        self.until_night: int = random.randint(10, 20)
        # Also keep track of how many turns of night are left. If this is 0, it is daytime.
        self.nighttime_left = 0

    def gen_players(self, cfg: GameConfig):
        """
        Generates the players for the game based on the supplied config.
        :param cfg: The game config.
        """
        self.players = [Player("The Chosen One", cfg.player_faction, FACTION_COLOURS[cfg.player_faction],
                                     0, [], [], [], set(), set())]
        factions = list(Faction)
        # Ensure that an AI player doesn't choose the same faction as the player.
        factions.remove(cfg.player_faction)
        for i in range(1, cfg.player_count):
            faction = random.choice(factions)
            factions.remove(faction)
            self.players.append(Player(f"NPC{i}", faction, FACTION_COLOURS[faction], 0, [], [], [], set(), set(),
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
                total_wealth -= unit.plan.cost / 10
        if self.players[0].faction is Faction.GODLESS:
            total_wealth *= 1.25
        elif self.players[0].faction is Faction.ORTHODOX:
            total_wealth *= 0.75
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
                    get_setl_totals(player, setl, self.nighttime_left > 0)
                overall_fortune += total_fortune
                overall_wealth += total_wealth
    
                # If the settlement is under siege, decrease its strength based on the number of besieging units.
                if setl.besieged:
                    besieging_units: typing.List[Unit] = []
                    for p in self.players:
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
                self.board.overlay.toggle_construction_notification(completed_constructions)
            if player.ai_playstyle is None and len(levelled_up_settlements) > 0:
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
            self.heathens.append(get_heathen(heathen_loc, self.turn))
    
        # Reset all heathens.
        for heathen in self.heathens:
            heathen.remaining_stamina = heathen.plan.total_stamina
            if heathen.health < heathen.plan.max_health:
                heathen.health = min(heathen.health + heathen.plan.max_health * 0.1, 100)
    
        self.board.overlay.remove_warning_if_possible()
        self.turn += 1
    
        # Make night-related calculations, but only if climatic effects are enabled.
        if self.board.game_config.climatic_effects:
            random.seed()
            if self.nighttime_left == 0:
                self.until_night -= 1
                if self.until_night == 0:
                    self.board.overlay.toggle_night(True)
                    # Nights last for between 5 and 20 turns.
                    self.nighttime_left = random.randint(5, 20)
                    for h in self.heathens:
                        h.plan.power = round(2 * h.plan.power)
                    if self.players[0].faction is Faction.NOCTURNE:
                        for u in self.players[0].units:
                            u.plan.power = round(2 * u.plan.power)
                        for setl in self.players[0].settlements:
                            for unit in setl.garrison:
                                unit.plan.power = round(2 * unit.plan.power)
            else:
                self.nighttime_left -= 1
                if self.nighttime_left == 0:
                    self.until_night = random.randint(10, 20)
                    self.board.overlay.toggle_night(False)
                    for h in self.heathens:
                        h.plan.power = round(h.plan.power / 2)
                    if self.players[0].faction is Faction.NOCTURNE:
                        for u in self.players[0].units:
                            u.plan.power = round(u.plan.power / 4)
                            u.health = round(u.health / 2)
                            u.plan.max_health = round(u.plan.max_health / 2)
                            u.plan.total_stamina = round(u.plan.total_stamina / 2)
                        for setl in self.players[0].settlements:
                            for unit in setl.garrison:
                                unit.plan.power = round(unit.plan.power / 4)
                                unit.health = round(unit.health / 2)
                                unit.plan.max_health = round(unit.plan.max_health / 2)
                                unit.plan.total_stamina = round(unit.plan.total_stamina / 2)
    
        possible_victory = self.check_for_victory()
        if possible_victory is not None:
            self.board.overlay.toggle_victory(possible_victory)
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
        for pl in self.players:
            all_setls.extend(pl.settlements)
    
        players_with_setls = 0
        for p in self.players:
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
            elif any(unit.plan.can_settle for unit in self.players[0].units):
                players_with_setls += 1
            elif not p.eliminated:
                p.eliminated = True
                self.board.overlay.toggle_elimination(p)
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
        all_units = []
        for player in self.players:
            # Heathens will not attack Infidel units.
            if player.faction is not Faction.INFIDELS:
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
                heathen.location = (clamp(heathen.location[0] + x_movement, 0, 99),
                                    clamp(heathen.location[1] + y_movement, 0, 89))
                heathen.remaining_stamina -= abs(x_movement) + abs(y_movement)
    
            # Players of the Infidels faction share vision with Heathen units.
            if self.players[0].faction is Faction.INFIDELS:
                for i in range(heathen.location[1] - 5, heathen.location[1] + 6):
                    for j in range(heathen.location[0] - 5, heathen.location[0] + 6):
                        self.players[0].quads_seen.add((j, i))
    
    def initialise_ais(self, namer: Namer):
        """
        Initialise the AI players by adding their first settlement in a random location.
        """
        for player in self.players:
            if player.ai_playstyle is not None:
                setl_coords = random.randint(0, 99), random.randint(0, 89)
                quad_biome = self.board.quads[setl_coords[1]][setl_coords[0]].biome
                setl_name = namer.get_settlement_name(quad_biome)
                new_settl = Settlement(setl_name, setl_coords, [],
                                       [self.board.quads[setl_coords[1]][setl_coords[0]]],
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
    
    def process_ais(self, move_maker: MoveMaker):
        """
        Process the moves for each AI player.
        """
        for player in self.players:
            if player.ai_playstyle is not None:
                move_maker.make_move(player, self.players, self.board.quads, self.board.game_config,
                                                     self.nighttime_left > 0)

