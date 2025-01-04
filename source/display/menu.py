import random
from math import ceil
from enum import Enum
from typing import List, Optional, Tuple

import pyxel

from source.display.display_utils import draw_paragraph
from source.networking.client import get_identifier
from source.util.calculator import clamp
from source.foundation.catalogue import BLESSINGS, FACTION_DETAILS, VICTORY_TYPE_COLOURS, get_unlockable_improvements, \
    IMPROVEMENTS, UNIT_PLANS, FACTION_COLOURS, PROJECTS, ACHIEVEMENTS
from source.foundation.models import GameConfig, VictoryType, Faction, ProjectType, Statistics, UnitPlan, \
    DeployerUnitPlan, PlayerDetails, LobbyDetails, LoadedMultiplayerState


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
    The class responsible for drawing and navigating the menu.
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

    def draw(self):
        """
        Draws the menu, based on where we are in it.
        """
        # Draw the background. Based on the image bank number, we determine which resource file should be used.
        background_path = f"resources/background{ceil((self.image_bank + 1) / 3)}.pyxres"
        pyxel.load(background_path)
        pyxel.blt(0, 0, self.image_bank % 3, 0, 0, 200, 200)

        if self.upnp_enabled is None:
            pyxel.rectb(32, 80, 146, 26, pyxel.COLOR_WHITE)
            pyxel.rect(33, 81, 144, 24, pyxel.COLOR_BLACK)
            pyxel.text(60, 90, "Connecting to server...", pyxel.COLOR_WHITE)
        elif game := self.multiplayer_game_being_loaded:
            pyxel.rectb(30, 30, 140, 100, pyxel.COLOR_WHITE)
            pyxel.rect(31, 31, 138, 98, pyxel.COLOR_BLACK)
            pyxel.text(72, 35, f"Loading {self.multiplayer_lobby.name}...", pyxel.COLOR_WHITE)
            pyxel.text(35, 50, "Quads", pyxel.COLOR_WHITE)
            pyxel.text(140, 50, f"{int(game.quad_chunks_loaded / 90.0 * 100)}%",
                       pyxel.COLOR_GREEN if game.quad_chunks_loaded == 90 else pyxel.COLOR_WHITE)
            pyxel.text(35, 60, "Players", pyxel.COLOR_WHITE)
            pyxel.text(140, 60, f"{int(game.players_loaded / self.multiplayer_lobby.cfg.player_count * 100)}%",
                       pyxel.COLOR_GREEN if game.players_loaded == self.multiplayer_lobby.cfg.player_count
                       else pyxel.COLOR_WHITE)
            pyxel.text(35, 70, "Quads seen", pyxel.COLOR_WHITE)
            if game.total_quads_seen:
                pyxel.text(140, 70, f"{int(game.quads_seen_loaded / game.total_quads_seen * 100)}%",
                           pyxel.COLOR_GREEN if game.quads_seen_loaded == game.total_quads_seen else pyxel.COLOR_WHITE)
            pyxel.text(35, 80, "Heathens", pyxel.COLOR_WHITE)
            pyxel.text(140, 80, "100%" if game.heathens_loaded else "0%",
                       pyxel.COLOR_GREEN if game.heathens_loaded else pyxel.COLOR_WHITE)
        elif lob := self.multiplayer_lobby:
            pyxel.rectb(20, 20, 160, 154, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 152, pyxel.COLOR_BLACK)
            pyxel.text(70, 25, "Multiplayer Lobby", pyxel.COLOR_WHITE)

            pyxel.text(28, 40, "Lobby Name", pyxel.COLOR_WHITE)
            lobby_offset = 50 - pow(len(lob.name), 1.4)
            pyxel.text(100 + lobby_offset, 40, lob.name, pyxel.COLOR_GREEN)
            pyxel.text(80, 50, f"{len(lob.current_players)}/{lob.cfg.player_count} players", pyxel.COLOR_WHITE)

            pyxel.line(24, 58, 175, 58, pyxel.COLOR_GRAY)

            players_on_screen = lob.current_players[self.lobby_player_boundaries[0]:self.lobby_player_boundaries[1]]
            for idx, pl in enumerate(players_on_screen):
                player_is_client: bool = get_identifier() == pl.id
                name = pl.name
                if player_is_client:
                    name += " (you)"
                elif not pl.id:
                    name += " (AI)"
                pyxel.text(28, 66 + idx * 10, name, pyxel.COLOR_GREEN if player_is_client else pyxel.COLOR_WHITE)
                faction_offset = 50 - pow(len(pl.faction), 1.4)
                pyxel.text(100 + faction_offset, 66 + idx * 10, pl.faction, FACTION_COLOURS[pl.faction])

            pyxel.load("resources/sprites.pyxres")
            if (len(self.multiplayer_lobby.current_players) - self.lobby_player_boundaries[1]) > 1:
                pyxel.blt(165, 130, 0, 0, 76, 8, 8)
            if self.lobby_player_boundaries[0] != 0:
                pyxel.blt(165, 60, 0, 8, 76, 8, 8)

            if len(lob.current_players) < lob.cfg.player_count:
                pyxel.text(46, 140, "Waiting for other players...", pyxel.COLOR_GRAY)
                pyxel.text(38, 150, "(Press A to generate AI players)", pyxel.COLOR_GRAY)
            else:
                pyxel.text(81, 150, "Start Game", self.get_option_colour(SetupOption.START_GAME))
            pyxel.text(58, 160, "(Press SPACE to leave)", pyxel.COLOR_WHITE)
        elif self.in_game_setup:
            pyxel.rectb(20, 20, 160, 154, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 152, pyxel.COLOR_BLACK)
            pyxel.text(81, 25, "Game Setup", pyxel.COLOR_WHITE)
            pyxel.text(28, 40, "Player Faction", self.get_option_colour(SetupOption.PLAYER_FACTION))
            faction_offset = 50 - pow(len(self.faction_colours[self.faction_idx][0]), 1.4)
            if self.faction_idx == 0:
                pyxel.text(100 + faction_offset, 40, f"{self.faction_colours[self.faction_idx][0].value} ->",
                           self.faction_colours[self.faction_idx][1])
            elif self.faction_idx == len(self.faction_colours) - 1:
                pyxel.text(95 + faction_offset, 40, f"<- {self.faction_colours[self.faction_idx][0].value}",
                           self.faction_colours[self.faction_idx][1])
            else:
                pyxel.text(88 + faction_offset, 40, f"<- {self.faction_colours[self.faction_idx][0].value} ->",
                           self.faction_colours[self.faction_idx][1])
            pyxel.text(26, 50, "(Press F to show more faction details)", pyxel.COLOR_WHITE)
            pyxel.text(28, 65, "Player Count", self.get_option_colour(SetupOption.PLAYER_COUNT))
            match self.player_count:
                case 2:
                    pyxel.text(140, 65, "2 ->", pyxel.COLOR_WHITE)
                case 14:
                    pyxel.text(130, 65, "<- 14", pyxel.COLOR_WHITE)
                case _:
                    pyxel.text(130, 65, f"<- {self.player_count} ->", pyxel.COLOR_WHITE)

            if self.upnp_enabled:
                pyxel.text(28, 80, "Multiplayer", self.get_option_colour(SetupOption.MULTIPLAYER))
                if self.multiplayer_enabled:
                    pyxel.text(125, 80, "<- Enabled", pyxel.COLOR_GREEN)
                else:
                    pyxel.text(125, 80, "Disabled ->", pyxel.COLOR_RED)
            else:
                pyxel.text(28, 80, "Multiplayer", pyxel.COLOR_GRAY)
                pyxel.text(130, 80, "Disabled", pyxel.COLOR_GRAY)
            pyxel.text(28, 95, "Biome Clustering", self.get_option_colour(SetupOption.BIOME_CLUSTERING))
            if self.biome_clustering_enabled:
                pyxel.text(125, 95, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 95, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(28, 110, "Fog of War", self.get_option_colour(SetupOption.FOG_OF_WAR))
            if self.fog_of_war_enabled:
                pyxel.text(125, 110, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 110, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(28, 125, "Climatic Effects", self.get_option_colour(SetupOption.CLIMATIC_EFFECTS))
            if self.climatic_effects_enabled:
                pyxel.text(125, 125, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 125, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(81, 150, "Start Game", self.get_option_colour(SetupOption.START_GAME))
            pyxel.text(52, 160, "(Press SPACE to go back)", pyxel.COLOR_WHITE)

            if self.showing_faction_details:
                pyxel.load("resources/sprites.pyxres")
                pyxel.rectb(30, 30, 140, 124, pyxel.COLOR_WHITE)
                pyxel.rect(31, 31, 138, 122, pyxel.COLOR_BLACK)
                pyxel.text(70, 35, "Faction Details", pyxel.COLOR_WHITE)
                pyxel.text(35, 50, str(self.faction_colours[self.faction_idx][0].value),
                           self.faction_colours[self.faction_idx][1])
                pyxel.text(35, 110, "Recommended victory:", pyxel.COLOR_WHITE)

                # Draw the buff and debuff text for the currently selected faction.
                faction_detail = FACTION_DETAILS[self.faction_idx]
                pyxel.text(35, 70, faction_detail.buff, pyxel.COLOR_GREEN)
                pyxel.text(35, 90, faction_detail.debuff, pyxel.COLOR_RED)
                pyxel.text(35, 120, faction_detail.rec_victory_type,
                           VICTORY_TYPE_COLOURS[faction_detail.rec_victory_type])
                pyxel.blt(150, 48, 0, self.faction_idx * 8, 92, 8, 8)
                if self.faction_idx != 0:
                    pyxel.text(35, 140, "<-", pyxel.COLOR_WHITE)
                    pyxel.blt(45, 138, 0, (self.faction_idx - 1) * 8, 92, 8, 8)
                pyxel.text(65, 140, "Press F to go back", pyxel.COLOR_WHITE)
                if self.faction_idx != len(self.faction_colours) - 1:
                    pyxel.blt(148, 138, 0, (self.faction_idx + 1) * 8, 92, 8, 8)
                    pyxel.text(158, 140, "->", pyxel.COLOR_WHITE)
        elif self.loading_game:
            pyxel.load("resources/sprites.pyxres")

            if self.load_failed:
                pyxel.rectb(24, 75, 152, 60, pyxel.COLOR_WHITE)
                pyxel.rect(25, 76, 150, 58, pyxel.COLOR_BLACK)
                pyxel.text(85, 81, "Oh no!", pyxel.COLOR_RED)
                pyxel.text(35, 92, "Error: This game save is invalid.", pyxel.COLOR_RED)
                pyxel.text(53, 100, "It's probably corrupted.", pyxel.COLOR_RED)

                pyxel.text(56, 120, "Press SPACE to go back", pyxel.COLOR_WHITE)
            else:
                pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
                pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
                if self.loading_multiplayer_game:
                    pyxel.text(60, 25, "Load Multiplayer Game", pyxel.COLOR_WHITE)
                else:
                    pyxel.text(81, 25, "Load Game", pyxel.COLOR_WHITE)
                for idx, save in enumerate(self.saves):
                    if self.load_game_boundaries[0] <= idx <= self.load_game_boundaries[1]:
                        pyxel.text(25, 35 + (idx - self.load_game_boundaries[0]) * 10, save, pyxel.COLOR_WHITE)
                        pyxel.text(150, 35 + (idx - self.load_game_boundaries[0]) * 10, "Load",
                                   pyxel.COLOR_RED if self.save_idx is idx else pyxel.COLOR_WHITE)
                if self.load_game_boundaries[1] < len(self.saves) - 1:
                    draw_paragraph(147, 135, "More down!", 5)
                    pyxel.blt(167, 136, 0, 0, 76, 8, 8)
                pyxel.text(56, 152, "Press SPACE to go back", pyxel.COLOR_WHITE)
                if self.loading_multiplayer_game:
                    pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                    pyxel.blt(35, 150, 0, 0, 140, 8, 8)
                elif self.upnp_enabled:
                    pyxel.blt(158, 150, 0, 8, 140, 8, 8)
                    pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
        elif self.in_wiki:
            match self.wiki_showing:
                case WikiOption.VICTORIES:
                    pyxel.load("resources/sprites.pyxres")
                    pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
                    pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
                    pyxel.text(82, 30, "Victories", pyxel.COLOR_WHITE)
                    pyxel.text(56, 152, "Press SPACE to go back", pyxel.COLOR_WHITE)
                    match self.victory_type:
                        case VictoryType.ELIMINATION:
                            pyxel.text(80, 40, "ELIMINATION", pyxel.COLOR_RED)
                            pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                            draw_paragraph(30, 60, "Take control of all settlements", 36)
                            pyxel.line(24, 70, 175, 70, pyxel.COLOR_GRAY)
                            draw_paragraph(25, 75, """Like any strong leader, you want the best for your people.
                                                However, constant attacks by filthy Heathens and enemy troops are
                                                enough to wear any great leader down. It is time to put an end to this,
                                                and become the one true empire. Other empires will wither at your
                                                blade, and they will be all the more thankful for it.""", 38)
                            pyxel.blt(158, 150, 0, 8, 28, 8, 8)
                            pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                        case VictoryType.JUBILATION:
                            pyxel.text(80, 40, "JUBILATION", pyxel.COLOR_GREEN)
                            pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                            draw_paragraph(30, 60, "Maintain 100% satisfaction in 5+ settlements for 25 turns", 36)
                            pyxel.line(24, 76, 175, 76, pyxel.COLOR_GRAY)
                            draw_paragraph(25, 81, """Your rule as leader is solid, your subjects faithful. But
                                                there is something missing. Your subjects, while not rebellious, do not
                                                have the love for you that you so desire. So be it. You will fill your
                                                empire with bread and circuses; your subjects will be the envy of all!
                                                And quietly, your rule will be unquestioned.""", 38)
                            pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(35, 150, 0, 0, 36, 8, 8)
                            pyxel.blt(158, 150, 0, 8, 44, 8, 8)
                            pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                        case VictoryType.GLUTTONY:
                            pyxel.text(84, 40, "GLUTTONY", pyxel.COLOR_GREEN)
                            pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                            draw_paragraph(30, 60, "Reach level 10 in 10+ settlements", 36)
                            pyxel.line(24, 70, 175, 70, pyxel.COLOR_GRAY)
                            draw_paragraph(25, 75, """There is nothing more satisfying as a leader than tucking
                                                into a generous meal prepared by your servants. But as a benevolent
                                                leader, you question why you alone can enjoy such luxuries. You resolve
                                                to make it your mission to feed the masses, grow your empire and spread
                                                around the plains!""", 38)
                            pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(35, 150, 0, 8, 28, 8, 8)
                            pyxel.blt(158, 150, 0, 0, 44, 8, 8)
                            pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                        case VictoryType.AFFLUENCE:
                            pyxel.text(82, 40, "AFFLUENCE", pyxel.COLOR_YELLOW)
                            pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                            draw_paragraph(30, 60, "Accumulate 100,000 wealth over the course of the game", 36)
                            pyxel.line(24, 76, 175, 76, pyxel.COLOR_GRAY)
                            draw_paragraph(25, 81, """Your empire has fallen on hard times. Recent conflicts have
                                                not gone your way, your lands have been seized, and your treasuries are
                                                empty. This is no way for an empire to be. Your advisors tell you of
                                                untapped riches in the vast deserts. You make it your mission to
                                                squeeze every last copper out of those dunes, and out of the whole
                                                world!""", 38)
                            pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(35, 150, 0, 8, 44, 8, 8)
                            pyxel.blt(158, 150, 0, 16, 44, 8, 8)
                            pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                        case VictoryType.VIGOUR:
                            pyxel.text(88, 40, "VIGOUR", pyxel.COLOR_ORANGE)
                            pyxel.text(25, 45, "Objectives:", pyxel.COLOR_WHITE)
                            draw_paragraph(30, 55, "Undergo the Ancient History blessing", 36)
                            draw_paragraph(30, 65, "Construct the holy sanctum in a settlement", 36)
                            pyxel.line(24, 77, 175, 77, pyxel.COLOR_GRAY)
                            draw_paragraph(25, 80, """You have always been fascinated with the bygone times of
                                                your empire and its rich history. There is never a better time than
                                                the present to devote some time to your studies. Your advisors tell
                                                you that the educated among your subjects have been doing some
                                                research recently, and have unearthed the plans for some form of Holy
                                                Sanctum. You make it your mission to construct said sanctum.""", 38)
                            pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(35, 150, 0, 0, 44, 8, 8)
                            pyxel.blt(158, 151, 0, 24, 44, 8, 8)
                            pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                        case VictoryType.SERENDIPITY:
                            pyxel.text(78, 40, "SERENDIPITY", pyxel.COLOR_PURPLE)
                            pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                            draw_paragraph(30, 60, """Undergo the three blessings of ardour: the pieces of
                                                strength, passion, and divinity.""", 36)
                            pyxel.line(24, 82, 175, 82, pyxel.COLOR_GRAY)
                            draw_paragraph(25, 87, """Local folklore has always said that a man of the passions
                                                was a man unparalleled amongst his peers. You have long aspired to be
                                                such a man, and such a leader. You consult your local sects and are
                                                informed that you are now ready to make the arduous journey of
                                                enlightenment and fulfillment. You grasp the opportunity with two
                                                hands, as a blessed man.""", 38)
                            pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(35, 150, 0, 16, 44, 8, 8)
                case WikiOption.FACTIONS:
                    pyxel.load("resources/sprites.pyxres")
                    pyxel.rectb(20, 10, 160, 184, pyxel.COLOR_WHITE)
                    pyxel.rect(21, 11, 158, 182, pyxel.COLOR_BLACK)
                    pyxel.text(85, 15, "Factions", pyxel.COLOR_WHITE)
                    pyxel.text(25, 30, str(self.faction_colours[self.faction_wiki_idx][0].value),
                               self.faction_colours[self.faction_wiki_idx][1])
                    pyxel.blt(160, 28, 0, self.faction_wiki_idx * 8, 92, 8, 8)
                    pyxel.line(24, 137, 175, 137, pyxel.COLOR_GRAY)
                    pyxel.text(25, 160, "Recommended victory:", pyxel.COLOR_WHITE)
                    if self.faction_wiki_idx != 0:
                        pyxel.text(25, 180, "<-", pyxel.COLOR_WHITE)
                        pyxel.blt(35, 178, 0, (self.faction_wiki_idx - 1) * 8, 92, 8, 8)
                    if self.faction_wiki_idx != len(self.faction_colours) - 1:
                        pyxel.blt(158, 178, 0, (self.faction_wiki_idx + 1) * 8, 92, 8, 8)
                        pyxel.text(168, 180, "->", pyxel.COLOR_WHITE)
                    pyxel.text(56, 180, "Press SPACE to go back", pyxel.COLOR_WHITE)

                    # Draw the faction details for the currently selected faction.
                    faction_detail = FACTION_DETAILS[self.faction_wiki_idx]
                    draw_paragraph(25, 40, faction_detail.lore, 38)
                    pyxel.text(25, 140, faction_detail.buff, pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, faction_detail.debuff, pyxel.COLOR_RED)
                    pyxel.text(25, 170, faction_detail.rec_victory_type,
                               VICTORY_TYPE_COLOURS[faction_detail.rec_victory_type])
                case WikiOption.RESOURCES:
                    pyxel.load("resources/quads.pyxres")
                    pyxel.rectb(20, 10, 160, 184, pyxel.COLOR_WHITE)
                    pyxel.rect(21, 11, 158, 182, pyxel.COLOR_BLACK)
                    pyxel.text(83, 15, "Resources", pyxel.COLOR_WHITE)

                    if not self.showing_rare_resources:
                        draw_paragraph(28, 25,
                                       "Core resources are used to construct select improvements requiring resources.",
                                       36)
                        pyxel.line(24, 45, 175, 45, pyxel.COLOR_GRAY)
                        pyxel.text(28, 55, "Ore", pyxel.COLOR_GRAY)
                        draw_paragraph(28, 65, "Ore is used to construct improvements of size and strength.", 25)
                        for i in range(8):
                            pyxel.blt(135 + i * 9 - (i // 4) * 36, 65 + (i // 4) * 9, 0, i * 8, 28, 8, 8)
                        pyxel.text(28, 90, "Timber", pyxel.COLOR_BROWN)
                        draw_paragraph(28, 100, "Timber is used to construct improvements requiring lumber.", 25)
                        for i in range(8):
                            pyxel.blt(135 + i * 9 - (i // 4) * 36, 100 + (i // 4) * 9, 0, i * 8, 36, 8, 8)
                        pyxel.text(28, 125, "Magma", pyxel.COLOR_RED)
                        draw_paragraph(28, 135,
                                       "Magma is used to construct improvements requiring melting or heating.", 25)
                        for i in range(8):
                            pyxel.blt(135 + i * 9 - (i // 4) * 36, 135 + (i // 4) * 9, 0, i * 8, 44, 8, 8)
                        pyxel.text(150, 180, "Rare ->", pyxel.COLOR_YELLOW)
                    else:
                        draw_paragraph(28, 25,
                                       "Rare resources apply special effects to settlements within one quad.",
                                       36)
                        pyxel.line(24, 40, 175, 40, pyxel.COLOR_GRAY)
                        pyxel.text(28, 45, "Aurora", pyxel.COLOR_YELLOW)
                        draw_paragraph(28, 51, "Adds a wealth bonus of 50% per exploitation.", 25)
                        for i in range(8):
                            pyxel.blt(135 + i * 9 - (i // 4) * 36, 46 + (i // 4) * 9, 0, i * 8, 52, 8, 8)
                        pyxel.text(28, 65, "Bloodstone", pyxel.COLOR_RED)
                        draw_paragraph(28, 71, "Produced units gain 50% health/power per exploitation.", 25)
                        for i in range(8):
                            pyxel.blt(135 + i * 9 - (i // 4) * 36, 70 + (i // 4) * 9, 0, i * 8, 60, 8, 8)
                        pyxel.text(28, 91, "Obsidian", pyxel.COLOR_GRAY)
                        draw_paragraph(28, 97, "Adds a strength bonus of 50% per exploitation.", 25)
                        for i in range(8):
                            pyxel.blt(135 + i * 9 - (i // 4) * 36, 93 + (i // 4) * 9, 0, i * 8, 68, 8, 8)
                        pyxel.text(28, 111, "Sunstone", pyxel.COLOR_ORANGE)
                        draw_paragraph(28, 117, """At nighttime, adds a vision bonus per exploitation, removes harvest
                        effect, and protects from heathens.""", 25)
                        for i in range(8):
                            pyxel.blt(135 + i * 9 - (i // 4) * 36, 120 + (i // 4) * 9, 0, i * 8, 76, 8, 8)
                        pyxel.text(28, 149, "Aquamarine", pyxel.COLOR_LIGHT_BLUE)
                        draw_paragraph(28, 155, "Adds a fortune bonus of 50% per exploitation.", 25)
                        for i in range(8):
                            pyxel.blt(135 + i * 9 - (i // 4) * 36, 150 + (i // 4) * 9, 0, i * 8, 84, 8, 8)
                        pyxel.text(25, 180, "<- Core", pyxel.COLOR_GRAY)

                    pyxel.text(58, 180, "Press SPACE to go back", pyxel.COLOR_WHITE)
                case WikiOption.CLIMATE:
                    pyxel.load("resources/sprites.pyxres")
                    pyxel.rectb(20, 10, 160, 164, pyxel.COLOR_WHITE)
                    pyxel.rect(21, 11, 158, 162, pyxel.COLOR_BLACK)
                    pyxel.text(86, 15, "Climate", pyxel.COLOR_WHITE)
                    pyxel.text(56, 162, "Press SPACE to go back", pyxel.COLOR_WHITE)
                    if self.showing_night:
                        pyxel.blt(96, 25, 0, 8, 84, 8, 8)
                        pyxel.text(60, 35, "The Everlasting Night", pyxel.COLOR_DARK_BLUE)
                        draw_paragraph(25, 45, """It's part of the life in this world. It's the feeling running
                                            down your spine when you're walking the streets alone with only a torch to
                                            guide you. It's the devastation when this month's cultivation is smaller
                                            than the last. It's the agony of looking out on a field of crops that won't
                                            grow. It's the fear of cursed heathens that could be lurking around every
                                            corner, ready to pounce. It's life during the nighttime, and you pray to
                                            the passions that the dawn soon comes.""", 38)
                        pyxel.line(24, 127, 175, 127, pyxel.COLOR_GRAY)
                        pyxel.text(25, 130, "Effects", pyxel.COLOR_WHITE)
                        pyxel.text(25, 138, "Reduced vision/harvest", pyxel.COLOR_RED)
                        pyxel.text(25, 144, "Strengthened heathens", pyxel.COLOR_RED)
                        pyxel.text(25, 150, "Increased fortune", pyxel.COLOR_GREEN)
                        pyxel.text(25, 162, "<-", pyxel.COLOR_WHITE)
                        pyxel.blt(35, 161, 0, 0, 84, 8, 8)
                    else:
                        pyxel.blt(96, 25, 0, 0, 84, 8, 8)
                        pyxel.text(62, 35, "The Heat of the Sun", pyxel.COLOR_YELLOW)
                        draw_paragraph(25, 45, """Each of those on this land can testify to the toll it takes on
                                            you. From the heat of the sun when toiling in the fields, to the icy chill
                                            of the wind atop a mountain, it changes a man. But the climb is always
                                            worth the reward, and you truly feel one with the land as you gaze outward
                                            from the peak and fully absorb the graciousness of this world. This is
                                            home.""", 38)
                        pyxel.line(24, 109, 175, 109, pyxel.COLOR_GRAY)
                        pyxel.text(25, 114, "Effects", pyxel.COLOR_WHITE)
                        pyxel.text(25, 124, "Persistent map and vision", pyxel.COLOR_GREEN)
                        pyxel.blt(158, 161, 0, 8, 84, 8, 8)
                        pyxel.text(168, 162, "->", pyxel.COLOR_WHITE)
                case WikiOption.BLESSINGS:
                    pyxel.load("resources/sprites.pyxres")
                    pyxel.rectb(10, 20, 180, 154, pyxel.COLOR_WHITE)
                    pyxel.rect(11, 21, 178, 152, pyxel.COLOR_BLACK)
                    pyxel.text(82, 30, "Blessings", pyxel.COLOR_PURPLE)
                    pyxel.text(20, 40, "Name", pyxel.COLOR_WHITE)
                    pyxel.text(155, 40, "Cost", pyxel.COLOR_WHITE)
                    pyxel.blt(173, 39, 0, 24, 44, 8, 8)
                    for idx, blessing in enumerate(BLESSINGS.values()):
                        if self.blessing_boundaries[0] <= idx <= self.blessing_boundaries[1]:
                            adj_idx = idx - self.blessing_boundaries[0]
                            pyxel.text(20, 50 + adj_idx * 25, str(blessing.name), pyxel.COLOR_WHITE)
                            pyxel.text(160, 50 + adj_idx * 25, str(round(blessing.cost)), pyxel.COLOR_WHITE)
                            pyxel.text(20, 57 + adj_idx * 25, str(blessing.description), pyxel.COLOR_WHITE)
                            imps = get_unlockable_improvements(blessing)
                            pyxel.blt(20, 64 + adj_idx * 25, 0, 32, 44, 8, 8)
                            unlocked_names: List[str] = []
                            if len(imps) > 0:
                                for imp in imps:
                                    unlocked_names.append(imp.name)
                                if len(unlocked_names) > 0:
                                    pyxel.text(30, 64 + adj_idx * 25, ", ".join(unlocked_names), pyxel.COLOR_WHITE)
                                else:
                                    pyxel.text(30, 63 + adj_idx * 25, "victory", pyxel.COLOR_GREEN)
                            else:
                                pyxel.text(30, 63 + adj_idx * 25, "victory", pyxel.COLOR_GREEN)
                    pyxel.text(56, 162, "Press SPACE to go back", pyxel.COLOR_WHITE)
                    if self.blessing_boundaries[1] < len(BLESSINGS) - 1:
                        draw_paragraph(152, 155, "More down!", 5)
                        pyxel.blt(172, 156, 0, 0, 76, 8, 8)
                case WikiOption.IMPROVEMENTS:
                    pyxel.load("resources/sprites.pyxres")
                    pyxel.rectb(10, 20, 180, 154, pyxel.COLOR_WHITE)
                    pyxel.rect(11, 21, 178, 152, pyxel.COLOR_BLACK)
                    pyxel.text(78, 30, "Improvements", pyxel.COLOR_ORANGE)
                    pyxel.text(20, 40, "Name", pyxel.COLOR_WHITE)
                    pyxel.text(125, 40, "Cost", pyxel.COLOR_WHITE)
                    pyxel.blt(143, 39, 0, 16, 44, 8, 8)
                    pyxel.blt(152, 39, 0, 0, 132, 8, 8)
                    for idx, imp in enumerate(IMPROVEMENTS):
                        if self.improvement_boundaries[0] <= idx <= self.improvement_boundaries[1]:
                            adj_offset = (idx - self.improvement_boundaries[0]) * 25
                            pyxel.text(20, 50 + adj_offset, str(imp.name), pyxel.COLOR_WHITE)
                            cost_str: str = str(round(imp.cost))
                            if res := imp.req_resources:
                                if res.ore:
                                    cost_str += f", {res.ore} ore"
                                if res.timber:
                                    cost_str += f", {res.timber} timber"
                                if res.magma:
                                    cost_str += f", {res.magma} magma"
                            pyxel.text(125, 50 + adj_offset, cost_str, pyxel.COLOR_WHITE)
                            pyxel.text(20, 57 + adj_offset, str(imp.description), pyxel.COLOR_WHITE)
                            effects = 0
                            if (wealth := round(imp.effect.wealth)) != 0:
                                pyxel.text(20 + effects * 25, 64 + adj_offset, f"{wealth:+}", pyxel.COLOR_YELLOW)
                                effects += 1
                            if (harvest := round(imp.effect.harvest)) != 0:
                                pyxel.text(20 + effects * 25, 64 + adj_offset, f"{harvest:+}", pyxel.COLOR_GREEN)
                                effects += 1
                            if (zeal := round(imp.effect.zeal)) != 0:
                                pyxel.text(20 + effects * 25, 64 + adj_offset, f"{zeal:+}", pyxel.COLOR_RED)
                                effects += 1
                            if (fortune := round(imp.effect.fortune)) != 0:
                                pyxel.text(20 + effects * 25, 64 + adj_offset, f"{fortune:+}", pyxel.COLOR_PURPLE)
                                effects += 1
                            if (strength := round(imp.effect.strength)) != 0:
                                pyxel.blt(20 + effects * 25, 64 + adj_offset, 0, 0, 28, 8, 8)
                                pyxel.text(30 + effects * 25, 64 + adj_offset, f"{strength:+}", pyxel.COLOR_WHITE)
                                effects += 1
                            if (satisfaction := round(imp.effect.satisfaction)) != 0:
                                satisfaction_u = 8 if satisfaction >= 0 else 16
                                pyxel.blt(20 + effects * 25, 64 + adj_offset, 0, satisfaction_u, 28, 8, 8)
                                pyxel.text(30 + effects * 25, 64 + adj_offset, f"{satisfaction:+}", pyxel.COLOR_WHITE)
                    pyxel.text(56, 162, "Press SPACE to go back", pyxel.COLOR_WHITE)
                    if self.improvement_boundaries[1] < len(IMPROVEMENTS) - 1:
                        draw_paragraph(152, 155, "More down!", 5)
                        pyxel.blt(172, 156, 0, 0, 76, 8, 8)
                case WikiOption.PROJECTS:
                    pyxel.load("resources/sprites.pyxres")
                    pyxel.rectb(10, 20, 180, 154, pyxel.COLOR_WHITE)
                    pyxel.rect(11, 21, 178, 152, pyxel.COLOR_BLACK)
                    pyxel.text(86, 30, "Projects", pyxel.COLOR_WHITE)
                    for idx, project in enumerate(PROJECTS):
                        pyxel.text(20, 42 + idx * 30, project.name, pyxel.COLOR_WHITE)
                        pyxel.text(20, 50 + idx * 30, project.description, pyxel.COLOR_WHITE)
                        match project.type:
                            case ProjectType.BOUNTIFUL:
                                pyxel.text(20, 58 + idx * 30, "Converts 25% of zeal to harvest.", pyxel.COLOR_GREEN)
                                pyxel.blt(166, 50 + idx * 30, 0, 8, 44, 8, 8)
                            case ProjectType.ECONOMICAL:
                                pyxel.text(20, 58 + idx * 30, "Converts 25% of zeal to wealth.", pyxel.COLOR_YELLOW)
                                pyxel.blt(166, 50 + idx * 30, 0, 0, 44, 8, 8)
                            case ProjectType.MAGICAL:
                                pyxel.text(20, 58 + idx * 30, "Converts 25% of zeal to fortune.", pyxel.COLOR_PURPLE)
                                pyxel.blt(166, 50 + idx * 30, 0, 24, 44, 8, 8)
                    pyxel.text(56, 162, "Press SPACE to go back", pyxel.COLOR_WHITE)
                case WikiOption.UNITS:
                    pyxel.load("resources/sprites.pyxres")
                    pyxel.rectb(10, 20, 180, 154, pyxel.COLOR_WHITE)
                    pyxel.rect(11, 21, 178, 152, pyxel.COLOR_BLACK)
                    pyxel.text(20, 40, "Name", pyxel.COLOR_WHITE)
                    pyxel.blt(90, 39, 0, 8, 36, 8, 8)
                    pyxel.blt(130, 39, 0, 16, 36, 8, 8)
                    pyxel.text(155, 40, "Cost", pyxel.COLOR_WHITE)
                    pyxel.blt(173, 39, 0, 16, 44, 8, 8)
                    pyxel.text(56, 162, "Press SPACE to go back", pyxel.COLOR_WHITE)
                    if self.unit_boundaries[1] < len(self.unit_plans_to_render) - 1:
                        draw_paragraph(152, 140, "More down!", 5)
                        pyxel.blt(172, 141, 0, 0, 76, 8, 8)
                    match self.wiki_units_option:
                        case WikiUnitsOption.ATTACKING:
                            pyxel.text(75, 30, "Attacking units", pyxel.COLOR_WHITE)
                            pyxel.blt(110, 39, 0, 0, 36, 8, 8)
                            pyxel.blt(165, 161, 0, 40, 36, 8, 8)
                            pyxel.text(175, 162, "->", pyxel.COLOR_WHITE)
                        case WikiUnitsOption.HEALING:
                            pyxel.text(75, 30, "Healing units", pyxel.COLOR_WHITE)
                            pyxel.blt(110, 39, 0, 40, 36, 8, 8)
                            pyxel.text(18, 162, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(28, 161, 0, 0, 36, 8, 8)
                            pyxel.blt(165, 161, 0, 48, 36, 8, 8)
                            pyxel.text(175, 162, "->", pyxel.COLOR_WHITE)
                        case _:
                            pyxel.text(75, 30, "Deploying units", pyxel.COLOR_WHITE)
                            pyxel.blt(107, 39, 0, 48, 36, 8, 8)
                            pyxel.text(18, 162, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(28, 161, 0, 40, 36, 8, 8)
                    for idx, unit in enumerate(self.unit_plans_to_render):
                        if self.unit_boundaries[0] <= idx <= self.unit_boundaries[1]:
                            adj_idx = idx - self.unit_boundaries[0]
                            pyxel.text(20, 50 + adj_idx * 10, str(unit.name), pyxel.COLOR_WHITE)
                            pyxel.text(160, 50 + adj_idx * 10, str(round(unit.cost)), pyxel.COLOR_WHITE)
                            pyxel.text(88, 50 + adj_idx * 10, str(round(unit.max_health)), pyxel.COLOR_WHITE)
                            pyxel.text(108, 50 + adj_idx * 10,
                                       str(unit.max_capacity if isinstance(unit, DeployerUnitPlan)
                                           else round(unit.power)),
                                       pyxel.COLOR_WHITE)
                            pyxel.text(132, 50 + adj_idx * 10, str(unit.total_stamina), pyxel.COLOR_WHITE)
                case _:
                    pyxel.rectb(60, 40, 80, 120, pyxel.COLOR_WHITE)
                    pyxel.rect(61, 41, 78, 118, pyxel.COLOR_BLACK)
                    pyxel.text(92, 45, "Wiki", pyxel.COLOR_WHITE)
                    pyxel.text(82, 60, "Victories", self.get_option_colour(WikiOption.VICTORIES))
                    pyxel.text(85, 70, "Factions", self.get_option_colour(WikiOption.FACTIONS))
                    pyxel.text(83, 80, "Resources", self.get_option_colour(WikiOption.RESOURCES))
                    pyxel.text(86, 90, "Climate", self.get_option_colour(WikiOption.CLIMATE))
                    pyxel.text(82, 100, "Blessings", self.get_option_colour(WikiOption.BLESSINGS))
                    pyxel.text(78, 110, "Improvements", self.get_option_colour(WikiOption.IMPROVEMENTS))
                    pyxel.text(84, 120, "Projects", self.get_option_colour(WikiOption.PROJECTS))
                    pyxel.text(90, 130, "Units", self.get_option_colour(WikiOption.UNITS))
                    pyxel.text(92, 150, "Back", self.get_option_colour(WikiOption.BACK))
        elif self.viewing_stats:
            pyxel.rectb(20, 20, 160, 154, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 152, pyxel.COLOR_BLACK)
            pyxel.text(81, 25, "Statistics", pyxel.COLOR_WHITE)

            pyxel.text(28, 40, "Playtime", pyxel.COLOR_WHITE)
            playtime = self.player_stats.playtime
            playtime_hrs = int(playtime // 3600)
            playtime_mins = int(playtime // 60 - playtime_hrs * 60)
            pyxel.text(145, 40, f"{playtime_hrs}:{playtime_mins:02d}", pyxel.COLOR_WHITE)

            pyxel.text(28, 60, "Turns played", pyxel.COLOR_WHITE)
            pyxel.text(144, 60, str(self.player_stats.turns_played), pyxel.COLOR_WHITE)

            pyxel.text(28, 80, "Victory count", pyxel.COLOR_WHITE)
            pyxel.text(150, 80, str(sum(self.player_stats.victories.values())), pyxel.COLOR_GREEN)

            pyxel.text(28, 100, "Defeat count", pyxel.COLOR_WHITE)
            pyxel.text(150, 100, str(self.player_stats.defeats), pyxel.COLOR_RED)

            pyxel.text(28, 120, "Favourite victory", pyxel.COLOR_WHITE)
            fav_vic: VictoryType | str
            vic_colour: int
            if self.player_stats.victories:
                fav_vic = max(self.player_stats.victories, key=self.player_stats.victories.get)
                vic_colour = VICTORY_TYPE_COLOURS[fav_vic]
            else:
                fav_vic = "None"
                vic_colour = pyxel.COLOR_GRAY
            victory_offset = 50 - pow(len(fav_vic), 1.4)
            pyxel.text(105 + victory_offset, 120, fav_vic, vic_colour)

            pyxel.text(28, 140, "Favourite faction", pyxel.COLOR_WHITE)
            fav_faction: Faction | str
            faction_colour: int
            if self.player_stats.factions:
                fav_faction = max(self.player_stats.factions, key=self.player_stats.factions.get)
                faction_colour = FACTION_COLOURS[fav_faction]
            else:
                fav_faction = "None"
                faction_colour = pyxel.COLOR_GRAY
            faction_offset = 50 - pow(len(fav_faction), 1.4)
            pyxel.text(105 + faction_offset, 140, str(fav_faction), faction_colour)

            pyxel.text(58, 160, "Press SPACE to go back", pyxel.COLOR_WHITE)
        elif self.viewing_achievements:
            pyxel.load("resources/achievements.pyxres")
            pyxel.rectb(20, 20, 160, 154, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 152, pyxel.COLOR_BLACK)
            pyxel.text(77, 25, "Achievements", pyxel.COLOR_WHITE)
            pyxel.text(155, 25, f"{len(self.player_stats.achievements)}/{len(ACHIEVEMENTS)}", pyxel.COLOR_WHITE)

            for idx, ach in enumerate(ACHIEVEMENTS):
                if self.achievements_boundaries[0] <= idx <= self.achievements_boundaries[1]:
                    adj_idx = idx - self.achievements_boundaries[0]
                    x_coord = (idx // 32) * 16
                    if ach.name not in self.player_stats.achievements:
                        x_coord += 8
                    pyxel.blt(35, 40 + 30 * adj_idx, 0, x_coord, idx * 8 - (idx // 32) * 256, 8, 8)
                    pyxel.text(50, 38 + 30 * adj_idx, ach.name, pyxel.COLOR_WHITE)
                    draw_paragraph(50, 46 + 30 * adj_idx, ach.description, 30,
                                   pyxel.COLOR_WHITE if ach.name in self.player_stats.achievements
                                   else pyxel.COLOR_GRAY)

            if self.achievements_boundaries[1] < len(ACHIEVEMENTS) - 1:
                pyxel.load("resources/sprites.pyxres")
                draw_paragraph(150, 150, "More down!", 5)
                pyxel.blt(170, 151, 0, 0, 76, 8, 8)

            pyxel.text(58, 160, "Press SPACE to go back", pyxel.COLOR_WHITE)
        elif self.joining_game:
            pyxel.rectb(30, 30, 140, 100, pyxel.COLOR_WHITE)
            pyxel.rect(31, 31, 138, 98, pyxel.COLOR_BLACK)
            pyxel.text(72, 35, f"Joining {self.multiplayer_lobbies[self.lobby_index].name}", pyxel.COLOR_WHITE)
            current_faction: (Faction, int) = self.available_multiplayer_factions[self.faction_idx]
            faction_offset = 50 - pow(len(current_faction[0]), 1.4)
            if len(self.available_multiplayer_factions) == 1:
                pyxel.text(55, 60, "You will be joining as", pyxel.COLOR_WHITE)
                pyxel.text(58 + faction_offset, 70, f"{current_faction[0].value}", current_faction[1])
            else:
                pyxel.text(62, 60, "Choose your faction", pyxel.COLOR_GREEN)
                if self.faction_idx == 0:
                    pyxel.text(60 + faction_offset, 70, f"{current_faction[0].value} ->", current_faction[1])
                elif self.faction_idx == len(self.available_multiplayer_factions) - 1:
                    pyxel.text(55 + faction_offset, 70, f"<- {current_faction[0].value}", current_faction[1])
                else:
                    pyxel.text(48 + faction_offset, 70, f"<- {current_faction[0].value} ->", current_faction[1])
            pyxel.text(40, 80, "(Press F to show more details)", pyxel.COLOR_WHITE)
            pyxel.text(58, 105, "Press ENTER to continue", pyxel.COLOR_WHITE)
            pyxel.text(60, 115, "Press SPACE to go back", pyxel.COLOR_WHITE)

            if self.showing_faction_details:
                pyxel.load("resources/sprites.pyxres")
                pyxel.rectb(30, 30, 140, 124, pyxel.COLOR_WHITE)
                pyxel.rect(31, 31, 138, 122, pyxel.COLOR_BLACK)
                pyxel.text(70, 35, "Faction Details", pyxel.COLOR_WHITE)
                pyxel.text(35, 50, str(current_faction[0].value), current_faction[1])
                pyxel.text(35, 110, "Recommended victory:", pyxel.COLOR_WHITE)

                # Draw the buff and debuff text for the currently selected faction.
                faction_detail = next(detail for detail in FACTION_DETAILS
                                      if detail.faction == current_faction[0].value)
                total_faction_idx = FACTION_DETAILS.index(faction_detail)
                pyxel.text(35, 70, faction_detail.buff, pyxel.COLOR_GREEN)
                pyxel.text(35, 90, faction_detail.debuff, pyxel.COLOR_RED)
                pyxel.text(35, 120, faction_detail.rec_victory_type,
                           VICTORY_TYPE_COLOURS[faction_detail.rec_victory_type])
                pyxel.blt(150, 48, 0, total_faction_idx * 8, 92, 8, 8)
                if self.faction_idx != 0:
                    pyxel.text(35, 140, "<-", pyxel.COLOR_WHITE)
                    prev_total_faction_idx = \
                        self.faction_colours.index(self.available_multiplayer_factions[self.faction_idx - 1])
                    pyxel.blt(45, 138, 0, prev_total_faction_idx * 8, 92, 8, 8)
                pyxel.text(65, 140, "Press F to go back", pyxel.COLOR_WHITE)
                if self.faction_idx != len(self.available_multiplayer_factions) - 1:
                    next_total_faction_idx = \
                        self.faction_colours.index(self.available_multiplayer_factions[self.faction_idx + 1])
                    pyxel.blt(148, 138, 0, next_total_faction_idx * 8, 92, 8, 8)
                    pyxel.text(158, 140, "->", pyxel.COLOR_WHITE)
        elif self.viewing_lobbies:
            pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
            pyxel.text(81, 25, "Join Game", pyxel.COLOR_WHITE)
            for idx, lobby in enumerate(self.multiplayer_lobbies):
                human_players: List[PlayerDetails] = [p for p in lobby.current_players if p.id]
                lobby_is_full: bool = len(human_players) == lobby.cfg.player_count
                lobby_count_str: str = f"{len(human_players)}/{lobby.cfg.player_count}"
                lobby_turn_str: str = "in lobby" if lobby.current_turn is None else f"turn {lobby.current_turn}"
                pyxel.text(25, 35 + idx * 10,
                           f"{lobby.name} - {lobby_count_str} - {lobby_turn_str}",
                           pyxel.COLOR_RED if lobby_is_full else pyxel.COLOR_WHITE)
                if lobby_is_full:
                    pyxel.text(150, 35 + idx * 10, "Full",
                               pyxel.COLOR_RED if self.lobby_index is idx else pyxel.COLOR_GRAY)
                else:
                    pyxel.text(150, 35 + idx * 10, "Join",
                               pyxel.COLOR_RED if self.lobby_index is idx else pyxel.COLOR_WHITE)
            pyxel.text(56, 152, "Press SPACE to go back", pyxel.COLOR_WHITE)
        else:
            pyxel.rectb(72, 95, 56, 90, pyxel.COLOR_WHITE)
            pyxel.rect(73, 96, 54, 88, pyxel.COLOR_BLACK)
            pyxel.text(82, 100, "MICROCOSM", pyxel.COLOR_WHITE)
            pyxel.text(85, 115, "New Game", self.get_option_colour(MainMenuOption.NEW_GAME))
            pyxel.text(82, 125, "Load Game", self.get_option_colour(MainMenuOption.LOAD_GAME))
            pyxel.text(82, 135, "Join Game",
                       pyxel.COLOR_GRAY if not self.upnp_enabled else self.get_option_colour(MainMenuOption.JOIN_GAME))
            pyxel.text(80, 145, "Statistics", self.get_option_colour(MainMenuOption.STATISTICS))
            pyxel.text(76, 155, "Achievements", self.get_option_colour(MainMenuOption.ACHIEVEMENTS))
            pyxel.text(92, 165, "Wiki", self.get_option_colour(MainMenuOption.WIKI))
            pyxel.text(92, 175, "Exit", self.get_option_colour(MainMenuOption.EXIT))

            if not self.upnp_enabled:
                pyxel.rectb(12, 10, 176, 26, pyxel.COLOR_WHITE)
                pyxel.rect(13, 11, 174, 24, pyxel.COLOR_BLACK)
                pyxel.text(65, 15, "UPnP not available!", pyxel.COLOR_RED)
                pyxel.text(48, 25, "Multiplayer will be disabled.", pyxel.COLOR_WHITE)

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
