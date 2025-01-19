import random
from enum import Enum
from typing import List, Optional, Tuple

import pyxel

from source.util.calculator import clamp
from source.foundation.catalogue import BLESSINGS, IMPROVEMENTS, UNIT_PLANS, FACTION_COLOURS, ACHIEVEMENTS
from source.foundation.models import GameConfig, VictoryType, Faction, Statistics, UnitPlan, DeployerUnitPlan, \
    LobbyDetails, LoadedMultiplayerState


class MainMenuOption(Enum):
    """
    Represents the options the player can choose from the main menu.
    """
    NEW_GAME = "New Game"
    LOAD_GAME = "Load Game"
    JOIN_GAME = "Join Game"
    STATISTICS = "Statistics"
    ACHIEVEMENTS = "Achievements"
    WIKI = "Wiki"
    EXIT = "Exit"


class SetupOption(Enum):
    """
    Represents the options the player can choose from the game setup screen.
    """
    PLAYER_FACTION = "FACTION"
    PLAYER_COUNT = "COUNT"
    MULTIPLAYER = "MULTI"
    BIOME_CLUSTERING = "BIOME"
    FOG_OF_WAR = "FOG"
    CLIMATIC_EFFECTS = "CLIMATE"
    START_GAME = "START"


class WikiOption(Enum):
    """
    Represents the options the player can choose from the wiki.
    """
    VICTORIES = "VIC"
    FACTIONS = "FAC"
    RESOURCES = "RES"
    CLIMATE = "CLIM"
    BLESSINGS = "BLS"
    IMPROVEMENTS = "IMP"
    PROJECTS = "PRJ"
    UNITS = "UNITS"
    BACK = "BACK"


class WikiUnitsOption(Enum):
    """
    Represents the different types of units displayed in the wiki.
    """
    ATTACKING = "ATT"
    HEALING = "HEAL"
    DEPLOYING = "DEP"


MenuOptions = SetupOption | WikiOption | MainMenuOption | VictoryType


class Menu:
    """
    The class responsible for the state management and visual navigation of the menu.
    """

    def __init__(self):
        """
        Initialise the menu with a random background image on the main menu.
        """
        self.main_menu_option = MainMenuOption.NEW_GAME
        random.seed()
        self.image_bank = random.randint(0, 5)
        self.in_game_setup = False
        self.loading_game = False
        self.in_wiki = False
        self.wiki_option = WikiOption.VICTORIES
        self.wiki_showing = None
        self.victory_type = VictoryType.ELIMINATION
        self.blessing_boundaries = 0, 3
        self.improvement_boundaries = 0, 3
        self.unit_boundaries = 0, 8
        self.saves: List[str] = []
        self.save_idx: Optional[int] = 0
        self.setup_option = SetupOption.PLAYER_FACTION
        self.faction_idx = 0
        self.player_count = 2
        self.multiplayer_enabled = False
        self.biome_clustering_enabled = True
        self.fog_of_war_enabled = True
        self.climatic_effects_enabled = True
        self.showing_night = False
        self.faction_colours: List[Tuple[Faction, int]] = list(FACTION_COLOURS.items())
        self.showing_faction_details = False
        self.faction_wiki_idx = 0
        self.load_game_boundaries = 0, 9
        self.load_failed = False
        self.viewing_stats = False
        self.player_stats: Optional[Statistics] = None
        self.wiki_units_option: WikiUnitsOption = WikiUnitsOption.ATTACKING
        self.unit_plans_to_render: List[UnitPlan] = \
            [up for up in UNIT_PLANS if not up.heals and not isinstance(up, DeployerUnitPlan)]
        self.viewing_achievements = False
        self.achievements_boundaries = 0, 3
        self.showing_rare_resources = False
        self.multiplayer_lobby: Optional[LobbyDetails] = None
        self.viewing_lobbies = False
        self.multiplayer_lobbies: List[LobbyDetails] = []
        self.lobby_index = 0
        self.joining_game = False
        self.available_multiplayer_factions: List[Tuple[Faction, int]] = []
        self.lobby_player_boundaries = 0, 7
        self.multiplayer_game_being_loaded: Optional[LoadedMultiplayerState] = None
        self.loading_multiplayer_game = False
        self.upnp_enabled: Optional[bool] = None  # None before a connection has been attempted.

    def navigate(self, up: bool = False, down: bool = False, left: bool = False, right: bool = False):
        """
        Navigate the menu based on the given arrow key pressed.
        :param up: Whether the up arrow key was pressed.
        :param down: Whether the down arrow key was pressed.
        :param left: Whether the left arrow key was pressed.
        :param right: Whether the right arrow key was pressed.
        """
        if down:
            # Ensure that players cannot navigate the root menu while the faction details overlay is being shown.
            # Similarly ensure that they cannot navigate the menu while in a multiplayer lobby.
            if self.in_game_setup and not self.showing_faction_details and not self.multiplayer_lobby:
                self.next_menu_option(self.setup_option, wrap_around=True,
                                      # If UPnP isn't enabled, then we want to skip over the Multiplayer option.
                                      skip=self.setup_option == SetupOption.PLAYER_COUNT and not self.upnp_enabled)
            elif self.loading_game:
                if self.save_idx == self.load_game_boundaries[1] and self.save_idx < len(self.saves) - 1:
                    self.load_game_boundaries = self.load_game_boundaries[0] + 1, self.load_game_boundaries[1] + 1
                if 0 <= self.save_idx < len(self.saves) - 1:
                    self.save_idx += 1
            elif self.multiplayer_lobby and \
                    self.lobby_player_boundaries[1] < len(self.multiplayer_lobby.current_players) - 1:
                self.lobby_player_boundaries = self.lobby_player_boundaries[0] + 1, self.lobby_player_boundaries[1] + 1
            elif self.viewing_lobbies and self.lobby_index < len(self.multiplayer_lobbies) - 1:
                self.lobby_index += 1
            elif self.viewing_achievements:
                if self.achievements_boundaries[1] < len(ACHIEVEMENTS) - 1:
                    self.achievements_boundaries = \
                        self.achievements_boundaries[0] + 1, self.achievements_boundaries[1] + 1
            elif self.in_wiki:
                match self.wiki_showing:
                    case WikiOption.BLESSINGS:
                        if self.blessing_boundaries[1] < len(BLESSINGS) - 1:
                            self.blessing_boundaries = self.blessing_boundaries[0] + 1, self.blessing_boundaries[1] + 1
                    case WikiOption.IMPROVEMENTS:
                        if self.improvement_boundaries[1] < len(IMPROVEMENTS) - 1:
                            self.improvement_boundaries = \
                                self.improvement_boundaries[0] + 1, self.improvement_boundaries[1] + 1
                    case WikiOption.UNITS:
                        if self.unit_boundaries[1] < len(self.unit_plans_to_render) - 1:
                            self.unit_boundaries = self.unit_boundaries[0] + 1, self.unit_boundaries[1] + 1
                    case _:
                        self.next_menu_option(self.wiki_option, wrap_around=True)
            else:
                self.next_menu_option(self.main_menu_option, wrap_around=True,
                                      # If UPnP isn't enabled, then we want to skip over the Join Game option.
                                      skip=self.main_menu_option == MainMenuOption.LOAD_GAME and not self.upnp_enabled)
        if up:
            # Ensure that players cannot navigate the root menu while the faction details overlay is being shown.
            # Similarly ensure that they cannot navigate the menu while in a multiplayer lobby.
            if self.in_game_setup and not self.showing_faction_details and not self.multiplayer_lobby:
                self.previous_menu_option(self.setup_option, wrap_around=True,
                                          # If UPnP isn't enabled, then we want to skip over the Multiplayer option.
                                          skip=(self.setup_option == SetupOption.BIOME_CLUSTERING and
                                                not self.upnp_enabled))
            elif self.loading_game:
                if self.save_idx > 0 and self.save_idx == self.load_game_boundaries[0]:
                    self.load_game_boundaries = self.load_game_boundaries[0] - 1, self.load_game_boundaries[1] - 1
                if self.save_idx > 0:
                    self.save_idx -= 1
            elif self.multiplayer_lobby and self.lobby_player_boundaries[0] > 0:
                self.lobby_player_boundaries = self.lobby_player_boundaries[0] - 1, self.lobby_player_boundaries[1] - 1
            elif self.viewing_lobbies and self.lobby_index > 0:
                self.lobby_index -= 1
            elif self.viewing_achievements:
                if self.achievements_boundaries[0] > 0:
                    self.achievements_boundaries = \
                        self.achievements_boundaries[0] - 1, self.achievements_boundaries[1] - 1
            elif self.in_wiki:
                match self.wiki_showing:
                    case WikiOption.BLESSINGS:
                        if self.blessing_boundaries[0] > 0:
                            self.blessing_boundaries = self.blessing_boundaries[0] - 1, self.blessing_boundaries[1] - 1
                    case WikiOption.IMPROVEMENTS:
                        if self.improvement_boundaries[0] > 0:
                            self.improvement_boundaries = \
                                self.improvement_boundaries[0] - 1, self.improvement_boundaries[1] - 1
                    case WikiOption.UNITS:
                        if self.unit_boundaries[0] > 0:
                            self.unit_boundaries = self.unit_boundaries[0] - 1, self.unit_boundaries[1] - 1
                    case _:
                        self.previous_menu_option(self.wiki_option, wrap_around=True)
            else:
                self.previous_menu_option(self.main_menu_option, wrap_around=True,
                                          # If UPnP isn't enabled, then we want to skip over the Join Game option.
                                          skip=(self.main_menu_option == MainMenuOption.STATISTICS and
                                                not self.upnp_enabled))
        if left:
            if self.in_game_setup:
                match self.setup_option:
                    case SetupOption.PLAYER_FACTION:
                        self.faction_idx = clamp(self.faction_idx - 1, 0, len(self.faction_colours) - 1)
                    case SetupOption.PLAYER_COUNT:
                        self.player_count = max(2, self.player_count - 1)
                    case SetupOption.MULTIPLAYER:
                        self.multiplayer_enabled = False
                    case SetupOption.BIOME_CLUSTERING:
                        self.biome_clustering_enabled = False
                    case SetupOption.FOG_OF_WAR:
                        self.fog_of_war_enabled = False
                    case SetupOption.CLIMATIC_EFFECTS:
                        self.climatic_effects_enabled = False
            elif self.loading_game:
                self.loading_multiplayer_game = False
            elif self.joining_game:
                self.faction_idx = clamp(self.faction_idx - 1, 0, len(self.available_multiplayer_factions) - 1)
            elif self.in_wiki and self.wiki_showing is WikiOption.VICTORIES:
                self.previous_menu_option(self.victory_type)
            elif self.in_wiki and self.wiki_showing is WikiOption.FACTIONS and self.faction_wiki_idx != 0:
                self.faction_wiki_idx -= 1
            elif self.in_wiki and self.wiki_showing is WikiOption.RESOURCES:
                self.showing_rare_resources = False
            elif self.in_wiki and self.wiki_showing is WikiOption.CLIMATE:
                self.showing_night = False
            elif self.in_wiki and self.wiki_showing is WikiOption.UNITS:
                if self.wiki_units_option is WikiUnitsOption.HEALING:
                    self.wiki_units_option = WikiUnitsOption.ATTACKING
                    self.unit_plans_to_render = \
                        [up for up in UNIT_PLANS if not up.heals and not isinstance(up, DeployerUnitPlan)]
                    self.unit_boundaries = 0, 8
                elif self.wiki_units_option is WikiUnitsOption.DEPLOYING:
                    self.wiki_units_option = WikiUnitsOption.HEALING
                    self.unit_plans_to_render = [up for up in UNIT_PLANS if up.heals]
                    self.unit_boundaries = 0, 8
        if right:
            if self.in_game_setup:
                match self.setup_option:
                    case SetupOption.PLAYER_FACTION:
                        self.faction_idx = clamp(self.faction_idx + 1, 0, len(self.faction_colours) - 1)
                    case SetupOption.PLAYER_COUNT:
                        self.player_count = min(14, self.player_count + 1)
                    case SetupOption.MULTIPLAYER:
                        self.multiplayer_enabled = True
                    case SetupOption.BIOME_CLUSTERING:
                        self.biome_clustering_enabled = True
                    case SetupOption.FOG_OF_WAR:
                        self.fog_of_war_enabled = True
                    case SetupOption.CLIMATIC_EFFECTS:
                        self.climatic_effects_enabled = True
            elif self.joining_game:
                self.faction_idx = clamp(self.faction_idx + 1, 0, len(self.available_multiplayer_factions) - 1)
            elif self.in_wiki and self.wiki_showing is WikiOption.VICTORIES:
                self.next_menu_option(self.victory_type)
            elif self.in_wiki and self.wiki_showing is WikiOption.FACTIONS and \
                    self.faction_wiki_idx != len(self.faction_colours) - 1:
                self.faction_wiki_idx += 1
            elif self.in_wiki and self.wiki_showing is WikiOption.RESOURCES:
                self.showing_rare_resources = True
            elif self.in_wiki and self.wiki_showing is WikiOption.CLIMATE:
                self.showing_night = True
            elif self.in_wiki and self.wiki_showing is WikiOption.UNITS:
                if self.wiki_units_option is WikiUnitsOption.ATTACKING:
                    self.wiki_units_option = WikiUnitsOption.HEALING
                    self.unit_plans_to_render = [up for up in UNIT_PLANS if up.heals]
                    self.unit_boundaries = 0, 8
                elif self.wiki_units_option is WikiUnitsOption.HEALING:
                    self.wiki_units_option = WikiUnitsOption.DEPLOYING
                    self.unit_plans_to_render = [up for up in UNIT_PLANS if isinstance(up, DeployerUnitPlan)]
                    self.unit_boundaries = 0, 8

    def get_game_config(self) -> GameConfig:
        """
        Returns the game config based on the setup screen selections.
        :return: The appropriate GameConfig object.
        """
        return GameConfig(self.player_count, self.faction_colours[self.faction_idx][0], self.biome_clustering_enabled,
                          self.fog_of_war_enabled, self.climatic_effects_enabled, self.multiplayer_enabled)

    def next_menu_option(self, current_option: MenuOptions, wrap_around: bool = False, skip: bool = False) -> None:
        """
        Given a menu option, go to the next item within the list of the option's enums.
        :param current_option: The currently selected option.
        :param wrap_around: If true, then choosing to go the next option when at the end of the list will wrap around
                            to the start of the list.
        :param skip: If true, then skip the next option and go to the one after.
        """
        current_option_idx = list(options_enum := type(current_option)).index(current_option)

        # Determine the index of the next option value.
        target_option_idx = (current_option_idx + (2 if skip else 1)) % len(list(options_enum))
        # If the currently selected option is the last option in the list and wrap-around is disabled, revert the index
        # to its original value. In other words, we're staying at the bottom of the list and not going back up.
        if (current_option_idx + (2 if skip else 1)) >= len(options_enum) and not wrap_around:
            target_option_idx = current_option_idx

        target_option = list(options_enum)[target_option_idx]
        self.change_menu_option(target_option)

    def previous_menu_option(self, current_option: MenuOptions, wrap_around: bool = False, skip: bool = False) -> None:
        """
        Given a menu option, go to the previous item within the list of the option's enums.
        :param current_option: The currently selected option.
        :param wrap_around: If true, then choosing to go the previous option when at the start of the list will wrap
                            around to the end of the list.
        :param skip: If true, then skip the previous option and go to the one before.
        """
        current_option_idx = list(options_enum := type(current_option)).index(current_option)

        # Determine the index of the previous option value.
        target_option_idx = (current_option_idx - (2 if skip else 1)) % len(list(options_enum))
        # If the currently selected option is the first option in the list and wrap-around is disabled, revert the
        # index to its original value. In other words, we're staying at the top of the list and not going back down.
        if (current_option_idx - (2 if skip else 1)) < 0 and not wrap_around:
            target_option_idx = current_option_idx

        target_option = list(options_enum)[target_option_idx]
        self.change_menu_option(target_option)

    def change_menu_option(self, target_option: MenuOptions) -> None:
        """
        Select the given menu option.
        :param target_option: The target option to be selected.
        """
        # Based on the enum type of the target option, figure out which corresponding field we need to change.
        match target_option:
            case SetupOption():
                self.setup_option = target_option
            case WikiOption():
                self.wiki_option = target_option
            case MainMenuOption():
                self.main_menu_option = target_option
            case VictoryType():
                self.victory_type = target_option

    def get_option_colour(self, option: MenuOptions) -> int:
        """
        Determine which colour to use for drawing menu options. RED if the option is currently selected by the user,
        and WHITE otherwise.
        :param option: the menu option to pick the colour for.
        :return: The appropriate colour.
        """
        match option:
            case SetupOption():
                field_to_check = self.setup_option
            case WikiOption():
                field_to_check = self.wiki_option
            case _:
                field_to_check = self.main_menu_option

        return pyxel.COLOR_RED if field_to_check is option else pyxel.COLOR_WHITE
