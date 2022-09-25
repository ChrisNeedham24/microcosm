import random
import typing
from enum import Enum

import pyxel

from calculator import clamp
from catalogue import BLESSINGS, get_unlockable_improvements, IMPROVEMENTS, UNIT_PLANS, FACTION_COLOURS
from models import GameConfig, VictoryType, Faction


class MenuOption(Enum):
    """
    Represents the options the player can choose from the main menu.
    """
    NEW_GAME = "New Game"
    LOAD_GAME = "Load Game"
    WIKI = "Wiki"
    EXIT = "Exit"


class SetupOption(Enum):
    """
    Represents the options the player can choose from the game setup screen.
    """
    PLAYER_FACTION = "FACTION"
    PLAYER_COUNT = "COUNT"
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
    CLIMATE = "CLIM"
    BLESSINGS = "BLS"
    IMPROVEMENTS = "IMP"
    UNITS = "UNITS"


class Menu:
    """
    The class responsible for drawing and navigating the menu.
    """
    def __init__(self):
        """
        Initialise the menu with a random background image on the main menu.
        """
        self.menu_option = MenuOption.NEW_GAME
        random.seed()
        self.image = random.randint(0, 5)
        self.in_game_setup = False
        self.loading_game = False
        self.in_wiki = False
        self.wiki_option = WikiOption.VICTORIES
        self.wiki_showing = None
        self.victory_type = VictoryType.ELIMINATION
        self.blessing_boundaries = 0, 3
        self.improvement_boundaries = 0, 3
        self.unit_boundaries = 0, 9
        self.saves: typing.List[str] = []
        self.save_idx: typing.Optional[int] = 0
        self.setup_option = SetupOption.PLAYER_FACTION
        self.faction_idx = 0
        self.player_count = 2
        self.biome_clustering_enabled = True
        self.fog_of_war_enabled = True
        self.climatic_effects_enabled = True
        self.showing_night = False
        self.faction_colours: typing.List[typing.Tuple[Faction, int]] = list(FACTION_COLOURS.items())
        self.showing_faction_details = False
        self.faction_wiki_idx = 0

    def draw(self):
        """
        Draws the menu, based on where we are in it.
        """
        # Draw the background.
        if self.image < 3:
            pyxel.load("resources/background.pyxres")
            pyxel.blt(0, 0, self.image, 0, 0, 200, 200)
        else:
            pyxel.load("resources/background2.pyxres")
            pyxel.blt(0, 0, self.image - 3, 0, 0, 200, 200)
        if self.in_game_setup:
            pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
            pyxel.text(81, 25, "Game Setup", pyxel.COLOR_WHITE)
            pyxel.text(28, 40, "Player Faction",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.PLAYER_FACTION else pyxel.COLOR_WHITE)
            faction_offset = 50 - pow(len(self.faction_colours[self.faction_idx][0]), 1.4)
            if self.faction_idx == 0:
                pyxel.text(100 + faction_offset, 40, f"{self.faction_colours[self.faction_idx][0]} ->",
                           self.faction_colours[self.faction_idx][1])
            elif self.faction_idx == len(self.faction_colours) - 1:
                pyxel.text(95 + faction_offset, 40, f"<- {self.faction_colours[self.faction_idx][0]}",
                           self.faction_colours[self.faction_idx][1])
            else:
                pyxel.text(88 + faction_offset, 40, f"<- {self.faction_colours[self.faction_idx][0]} ->",
                           self.faction_colours[self.faction_idx][1])
            pyxel.text(26, 50, "(Press F to show more faction details)", pyxel.COLOR_WHITE)
            pyxel.text(28, 65, "Player Count",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.PLAYER_COUNT else pyxel.COLOR_WHITE)
            if self.player_count == 2:
                pyxel.text(140, 65, "2 ->", pyxel.COLOR_WHITE)
            elif 2 < self.player_count < 14:
                pyxel.text(130, 65, f"<- {self.player_count} ->", pyxel.COLOR_WHITE)
            else:
                pyxel.text(130, 65, "<- 14", pyxel.COLOR_WHITE)
            pyxel.text(28, 85, "Biome Clustering",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.BIOME_CLUSTERING else pyxel.COLOR_WHITE)
            if self.biome_clustering_enabled:
                pyxel.text(125, 85, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 85, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(28, 105, "Fog of War",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.FOG_OF_WAR else pyxel.COLOR_WHITE)
            if self.fog_of_war_enabled:
                pyxel.text(125, 105, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 105, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(28, 125, "Climatic Effects",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.CLIMATIC_EFFECTS else pyxel.COLOR_WHITE)
            if self.climatic_effects_enabled:
                pyxel.text(125, 125, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 125, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(81, 150, "Start Game",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.START_GAME else pyxel.COLOR_WHITE)

            if self.showing_faction_details:
                pyxel.load("resources/sprites.pyxres")
                pyxel.rectb(30, 30, 140, 124, pyxel.COLOR_WHITE)
                pyxel.rect(31, 31, 138, 122, pyxel.COLOR_BLACK)
                pyxel.text(70, 35, "Faction Details", pyxel.COLOR_WHITE)
                pyxel.text(35, 50, str(self.faction_colours[self.faction_idx][0].value),
                           self.faction_colours[self.faction_idx][1])
                pyxel.text(35, 110, "Recommended victory:", pyxel.COLOR_WHITE)

                if self.faction_idx == 0:
                    pyxel.text(35, 70, "+ Immune to poor harvest", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Generates 75% of usual zeal", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "GLUTTONY", pyxel.COLOR_GREEN)
                elif self.faction_idx == 1:
                    pyxel.text(35, 70, "+ Immune to recession", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Double low harvest penalty", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "AFFLUENCE", pyxel.COLOR_YELLOW)
                elif self.faction_idx == 2:
                    pyxel.text(35, 70, "+ Investigations always succeed", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Generates 75% of usual fortune", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)
                elif self.faction_idx == 3:
                    pyxel.text(35, 70, "+ Generates 125% of usual wealth", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Blessings cost 125% of usual", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "AFFLUENCE", pyxel.COLOR_YELLOW)
                elif self.faction_idx == 4:
                    pyxel.text(35, 70, "+ Generates 125% of usual harvest", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Settlements capped at level 5", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "JUBILATION", pyxel.COLOR_GREEN)
                elif self.faction_idx == 5:
                    pyxel.text(35, 70, "+ Generates 125% of usual zeal", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Construction buyouts disabled", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "VIGOUR", pyxel.COLOR_ORANGE)
                elif self.faction_idx == 6:
                    pyxel.text(35, 70, "+ Generates 125% of usual fortune", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Generates 75% of usual wealth", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "SERENDIPITY", pyxel.COLOR_PURPLE)
                elif self.faction_idx == 7:
                    pyxel.text(35, 70, "+ Settlements have 200% strength", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Limited to a single settlement", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)
                elif self.faction_idx == 8:
                    pyxel.text(35, 70, "+ Base satisfaction is 75", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Settlers only at level 5", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "JUBILATION", pyxel.COLOR_GREEN)
                elif self.faction_idx == 9:
                    pyxel.text(35, 70, "+ Units have 50% more power", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Settlements have 50% strength", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)
                elif self.faction_idx == 10:
                    pyxel.text(35, 70, "+ Units have 50% more health", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Units have 75% of usual power", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)
                elif self.faction_idx == 11:
                    pyxel.text(35, 70, "+ Units have 50% more stamina", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Units have 75% of usual health", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "GLUTTONY", pyxel.COLOR_GREEN)
                elif self.faction_idx == 12:
                    pyxel.text(35, 70, "+ Not attacked by heathens", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Always attacked by AI players", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)
                elif self.faction_idx == 13:
                    pyxel.text(35, 70, "+ Thrive during the night", pyxel.COLOR_GREEN)
                    pyxel.text(35, 90, "- Units weakened during the day", pyxel.COLOR_RED)
                    pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)

                pyxel.blt(150, 48, 0, self.faction_idx * 8, 92, 8, 8)
                if self.faction_idx != 0:
                    pyxel.text(35, 140, "<-", pyxel.COLOR_WHITE)
                    pyxel.blt(45, 138, 0, (self.faction_idx - 1) * 8, 92, 8, 8)
                pyxel.text(65, 140, "Press F to go back", pyxel.COLOR_WHITE)
                if self.faction_idx != len(self.faction_colours) - 1:
                    pyxel.blt(148, 138, 0, (self.faction_idx + 1) * 8, 92, 8, 8)
                    pyxel.text(158, 140, "->", pyxel.COLOR_WHITE)
        elif self.loading_game:
            pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
            pyxel.text(81, 25, "Load Game", pyxel.COLOR_WHITE)
            for idx, save in enumerate(self.saves):
                pyxel.text(25, 35 + idx * 10, save, pyxel.COLOR_WHITE)
                pyxel.text(150, 35 + idx * 10, "Load", pyxel.COLOR_RED if self.save_idx is idx else pyxel.COLOR_WHITE)
            pyxel.text(85, 150, "Cancel", pyxel.COLOR_RED if self.save_idx == -1 else pyxel.COLOR_WHITE)
        elif self.in_wiki:
            if self.wiki_showing is WikiOption.VICTORIES:
                pyxel.load("resources/sprites.pyxres")
                pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
                pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
                pyxel.text(82, 30, "Victories", pyxel.COLOR_WHITE)
                pyxel.text(56, 152, "Press SPACE to go back", pyxel.COLOR_WHITE)
                if self.victory_type is VictoryType.ELIMINATION:
                    pyxel.text(80, 40, "ELIMINATION", pyxel.COLOR_RED)
                    pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                    pyxel.text(30, 60, "Take control of all settlements", pyxel.COLOR_WHITE)
                    pyxel.line(24, 70, 175, 70, pyxel.COLOR_GRAY)
                    pyxel.text(25, 75, "Like any strong leader, you want the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 81, "best for your people. However,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 87, "constant attacks by filthy Heathens", pyxel.COLOR_WHITE)
                    pyxel.text(25, 93, "and enemy troops are enough to wear", pyxel.COLOR_WHITE)
                    pyxel.text(25, 99, "any great leader down. It is time to", pyxel.COLOR_WHITE)
                    pyxel.text(25, 105, "put an end to this, and become the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 111, "one true empire. Other empires will", pyxel.COLOR_WHITE)
                    pyxel.text(25, 117, "wither at your blade, and they will", pyxel.COLOR_WHITE)
                    pyxel.text(25, 123, "be all the more thankful for it.", pyxel.COLOR_WHITE)
                    pyxel.blt(158, 150, 0, 8, 28, 8, 8)
                    pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                elif self.victory_type is VictoryType.JUBILATION:
                    pyxel.text(80, 40, "JUBILATION", pyxel.COLOR_GREEN)
                    pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                    pyxel.text(30, 60, "Maintain 100% satisfaction in 5+", pyxel.COLOR_WHITE)
                    pyxel.text(30, 66, "settlements for 25 turns", pyxel.COLOR_WHITE)
                    pyxel.line(24, 76, 175, 76, pyxel.COLOR_GRAY)
                    pyxel.text(25, 81, "Your rule as leader is solid, your", pyxel.COLOR_WHITE)
                    pyxel.text(25, 87, "subjects faithful. But there is", pyxel.COLOR_WHITE)
                    pyxel.text(25, 93, "something missing. Your subjects,", pyxel. COLOR_WHITE)
                    pyxel.text(25, 99, "while not rebellious, do not have", pyxel.COLOR_WHITE)
                    pyxel.text(25, 105, "the love for you that you so", pyxel.COLOR_WHITE)
                    pyxel.text(25, 111, "desire. So be it. You will fill", pyxel.COLOR_WHITE)
                    pyxel.text(25, 117, "your empire with bread and", pyxel.COLOR_WHITE)
                    pyxel.text(25, 123, "circuses; your subjects will be the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 129, "envy of all! And quietly, your rule", pyxel.COLOR_WHITE)
                    pyxel.text(25, 135, "will be unquestioned.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                    pyxel.blt(35, 150, 0, 0, 36, 8, 8)
                    pyxel.blt(158, 150, 0, 8, 44, 8, 8)
                    pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                elif self.victory_type is VictoryType.GLUTTONY:
                    pyxel.text(84, 40, "GLUTTONY", pyxel.COLOR_GREEN)
                    pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                    pyxel.text(30, 60, "Reach level 10 in 10+ settlements", pyxel.COLOR_WHITE)
                    pyxel.line(24, 70, 175, 70, pyxel.COLOR_GRAY)
                    pyxel.text(25, 75, "There is nothing more satisfying as a", pyxel.COLOR_WHITE)
                    pyxel.text(25, 81, "leader than tucking into a generous", pyxel.COLOR_WHITE)
                    pyxel.text(25, 87, "meal prepared by your servants. But", pyxel.COLOR_WHITE)
                    pyxel.text(25, 93, "as a benevolent leader, you question", pyxel.COLOR_WHITE)
                    pyxel.text(25, 99, "why you alone can enjoy such luxuries.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 105, "You resolve to make it your mission to", pyxel.COLOR_WHITE)
                    pyxel.text(25, 111, "feed the masses, grow your empire and", pyxel.COLOR_WHITE)
                    pyxel.text(25, 117, "spread around the plains!", pyxel.COLOR_WHITE)
                    pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                    pyxel.blt(35, 150, 0, 8, 28, 8, 8)
                    pyxel.blt(158, 150, 0, 0, 44, 8, 8)
                    pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                elif self.victory_type is VictoryType.AFFLUENCE:
                    pyxel.text(82, 40, "AFFLUENCE", pyxel.COLOR_YELLOW)
                    pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                    pyxel.text(30, 60, "Accumulate 100,000 wealth over the", pyxel.COLOR_WHITE)
                    pyxel.text(30, 66, "course of the game", pyxel.COLOR_WHITE)
                    pyxel.line(24, 76, 175, 76, pyxel.COLOR_GRAY)
                    pyxel.text(25, 81, "Your empire has fallen on hard times.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 87, "Recent conflicts have not gone your", pyxel.COLOR_WHITE)
                    pyxel.text(25, 93, "way, your lands have been seized, and", pyxel.COLOR_WHITE)
                    pyxel.text(25, 99, "your treasuries are empty. This is no", pyxel.COLOR_WHITE)
                    pyxel.text(25, 105, "way for an empire to be. Your", pyxel.COLOR_WHITE)
                    pyxel.text(25, 111, "advisors tell you of untapped riches", pyxel.COLOR_WHITE)
                    pyxel.text(25, 117, "in the vast deserts. You make it your", pyxel.COLOR_WHITE)
                    pyxel.text(25, 123, "mission to squeeze every last copper", pyxel.COLOR_WHITE)
                    pyxel.text(25, 129, "out of those dunes, and out of the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 135, "whole world!", pyxel.COLOR_WHITE)
                    pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                    pyxel.blt(35, 150, 0, 8, 44, 8, 8)
                    pyxel.blt(158, 150, 0, 16, 44, 8, 8)
                    pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                elif self.victory_type is VictoryType.VIGOUR:
                    pyxel.text(88, 40, "VIGOUR", pyxel.COLOR_ORANGE)
                    pyxel.text(25, 45, "Objectives:", pyxel.COLOR_WHITE)
                    pyxel.text(30, 55, "Undergo the Ancient History blessing", pyxel.COLOR_WHITE)
                    pyxel.text(30, 65, "Construct the holy sanctum in a", pyxel.COLOR_WHITE)
                    pyxel.text(30, 71, "settlement", pyxel.COLOR_WHITE)
                    pyxel.line(24, 77, 175, 77, pyxel.COLOR_GRAY)
                    pyxel.text(25, 80, "You have always been fascinated with", pyxel.COLOR_WHITE)
                    pyxel.text(25, 86, "the bygone times of your empire and", pyxel.COLOR_WHITE)
                    pyxel.text(25, 92, "its rich history. There is never a", pyxel.COLOR_WHITE)
                    pyxel.text(25, 98, "better time than the present to devote", pyxel.COLOR_WHITE)
                    pyxel.text(25, 104, "some time to your studies. Your", pyxel.COLOR_WHITE)
                    pyxel.text(25, 110, "advisors tell you that the educated", pyxel.COLOR_WHITE)
                    pyxel.text(25, 116, "among your subjects have been doing", pyxel.COLOR_WHITE)
                    pyxel.text(25, 122, "some research recently, and have", pyxel.COLOR_WHITE)
                    pyxel.text(25, 128, "unearthed the plans for some form", pyxel.COLOR_WHITE)
                    pyxel.text(25, 134, "of Holy Sanctum. You make it your", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "mission to construct said sanctum.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                    pyxel.blt(35, 150, 0, 0, 44, 8, 8)
                    pyxel.blt(158, 151, 0, 24, 44, 8, 8)
                    pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                elif self.victory_type is VictoryType.SERENDIPITY:
                    pyxel.text(78, 40, "SERENDIPITY", pyxel.COLOR_PURPLE)
                    pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                    pyxel.text(30, 60, "Undergo the three blessings of", pyxel.COLOR_WHITE)
                    pyxel.text(30, 66, "ardour: the pieces of strength,", pyxel.COLOR_WHITE)
                    pyxel.text(30, 72, "passion, and divinity.", pyxel.COLOR_WHITE)
                    pyxel.line(24, 82, 175, 82, pyxel.COLOR_GRAY)
                    pyxel.text(25, 87, "Local folklore has always said that", pyxel.COLOR_WHITE)
                    pyxel.text(25, 93, "a man of the passions was a man", pyxel.COLOR_WHITE)
                    pyxel.text(25, 99, "unparalleled amongst his peers. You", pyxel.COLOR_WHITE)
                    pyxel.text(25, 105, "have long aspired to be such a man,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 111, "and such a leader. You consult your", pyxel.COLOR_WHITE)
                    pyxel.text(25, 117, "local sects and are informed that you", pyxel.COLOR_WHITE)
                    pyxel.text(25, 123, "are now ready to make the arduous", pyxel.COLOR_WHITE)
                    pyxel.text(25, 129, "journey of enlightenment and", pyxel.COLOR_WHITE)
                    pyxel.text(25, 135, "fulfillment. You grasp the opportunity", pyxel.COLOR_WHITE)
                    pyxel.text(25, 141, "with two hands, as a blessed man.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                    pyxel.blt(35, 150, 0, 16, 44, 8, 8)
            elif self.wiki_showing is WikiOption.FACTIONS:
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

                if self.faction_wiki_idx == 0:
                    pyxel.text(25, 40, "Using techniques passed down through ", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "the generations, the Agriculturists", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "are able to sustain their populace", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "through famine and indeed through", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "feast. Some of this land's greatest", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "delicacies are grown by these humble", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "people, who insist that anyone could", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "grow what they do, winking at one", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "another as they say it. Without the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "spectre of hunger on the horizon, the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "Agriculturists lead the slow life,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "indulging in pleasures at their own", pyxel.COLOR_WHITE)
                    pyxel.text(25, 112, "pace.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Immune to poor harvest", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Generates 75% of usual zeal", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "GLUTTONY", pyxel.COLOR_GREEN)
                elif self.faction_wiki_idx == 1:
                    pyxel.text(25, 40, "The sky-high towers and luxurious", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "dwellings found throughout their", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "cities represent the Capitalists to", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "the fullest. They value the clink of", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "coins over anything else, and it has", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "served them well so far. However, if", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "you take a look around the corner,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "things are clearly not as the seem.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "And as the slums fill up, there", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "better be enough food to go around,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "lest something... dangerous happens.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Immune to recession", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Double low harvest penalty", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "AFFLUENCE", pyxel.COLOR_YELLOW)
                elif self.faction_wiki_idx == 2:
                    pyxel.text(25, 40, "Due to a genetic trait, the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "Scrutineers have always had good", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "eyesight and they use it to full", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "effect. Nothing gets past them, from", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "the temples of the outlands to the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "streets of their cities. But, as it", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "goes, the devil is in the details, as", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "the local clergy certainly aren't", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "exempt from the all-seeing eye, with", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "blessings being stymied as much as is", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "humanly possible.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Investigations always succeed", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Generates 75% of usual fortune", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                elif self.faction_wiki_idx == 3:
                    pyxel.text(25, 40, "Many eons ago, a subsection of the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "population of these lands began to", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "question the effectiveness of their", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "blessings after years of squalor and", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "oppression. They shook free their", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "bonds and formed their own community", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "based around the one thing that", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "proved valuable to all people:", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "currency. However, despite shunning", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "blessings at every opportunity, The", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "Godless, as they became known, are", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "wont to dabble in blessings in", pyxel.COLOR_WHITE)
                    pyxel.text(25, 112, "moments of weakness, and what's left", pyxel.COLOR_WHITE)
                    pyxel.text(25, 118, "of their clergy makes sure to sink", pyxel.COLOR_WHITE)
                    pyxel.text(25, 124, "the boot in.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Generates 125% of usual wealth", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Blessings cost 125% of usual", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "AFFLUENCE", pyxel.COLOR_YELLOW)
                elif self.faction_wiki_idx == 4:
                    pyxel.text(25, 40, "Originating from a particular fertile", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "part of these lands, The Ravenous have", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "enjoyed bountiful harvests for", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "centuries. No matter the skill of the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "farmer, or the quality of the seeds, a", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "cultivation of significant size is", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "always created after some months. But", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "with such consistency, comes", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "complacency. Those that have resided", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "in settlements occupied by The", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "Ravenous, over time, grow greedy. As", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "populations increase, and more food", pyxel.COLOR_WHITE)
                    pyxel.text(25, 112, "is available, the existing residents", pyxel.COLOR_WHITE)
                    pyxel.text(25, 118, "seek to keep it all for themselves, as", pyxel.COLOR_WHITE)
                    pyxel.text(25, 124, "newcomers are given the unbearable", pyxel.COLOR_WHITE)
                    pyxel.text(25, 130, "choice of starving or leaving.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Generates 125% of usual harvest", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Settlements capped at level 5", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "JUBILATION", pyxel.COLOR_GREEN)
                elif self.faction_wiki_idx == 5:
                    pyxel.text(25, 40, "There's nothing quite like the clang", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "of iron striking iron to truly ground", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "a person in their surroundings. This", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "is a fact that the Fundamentalists", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "know well, as every child of a certain", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "age is required to serve as an", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "apprentice in a local forge or", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "refinery. With such resources at their", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "disposal, work is done quickly. And", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "yet, suggestions that constructions", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "should be made quicker, and in some", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "cases instantaneous, through the use", pyxel.COLOR_WHITE)
                    pyxel.text(25, 112, "of empire funds are met with utter", pyxel.COLOR_WHITE)
                    pyxel.text(25, 118, "disgust by the people. For the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 124, "Fundamentalists, everything must be", pyxel.COLOR_WHITE)
                    pyxel.text(25, 130, "done the right way.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Generates 125% of usual zeal", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Construction buyouts disabled", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "VIGOUR", pyxel.COLOR_ORANGE)
                elif self.faction_wiki_idx == 6:
                    pyxel.text(25, 40, "Glory to the ancient ones, and glory", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "to the passionate. The Orthodox look", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "to those that came before them for", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "guidance, and they are justly", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "rewarded that, with enlightenment", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "and discoveries occurring", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "frequently. As the passionate tend", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "to do, however, the clatter of coin", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "in the palm is met with a stern", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "decline. Content they are with their", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "existence, The Orthodox rely on", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "seeing what others cannot.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Generates 125% of usual fortune", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Generates 75% of usual wealth", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "SERENDIPITY", pyxel.COLOR_PURPLE)
                elif self.faction_wiki_idx == 7:
                    pyxel.text(25, 40, "For the unfamiliar, visiting the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "settlement of The Concentrated can", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "be overwhelming. The sheer mass of", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "people everywhere one looks along", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "with the cloud-breaching towers can", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "make one feel like they have been", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "transported to some distant future.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "It is this intimidatory factor, in", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "combination with the colossal", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "ramparts surrounding the megapolis", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "that have kept The Concentrated", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "safe and sound for many years.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Settlements have 200% strength", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Limited to a single settlement", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                elif self.faction_wiki_idx == 8:
                    pyxel.text(25, 40, "Blink and you'll miss it; that's the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "story of the settlements of the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "Frontier. The Frontiersmen have a", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "near obsession with the thrill of", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "the frontier and making something of", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "inhospitable terrain, in situations", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "where others could not. Residing in", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "a new settlement is considered to be", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "the pinnacle of Frontier achievement,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "but the shine wears off quickly.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "After some time, the people become", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "restless and seek to expand further.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 112, "And thus the cycle repeats.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Base satisfaction is 75", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Settlers only at level 5", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "JUBILATION", pyxel.COLOR_GREEN)
                elif self.faction_wiki_idx == 9:
                    pyxel.text(25, 40, "The concept of raw power and strength", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "has long been a core tenet of the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "self-dubbed Empire, with compulsory", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "military service a cultural feature.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "Drilled into the populace for such an", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "extensive period, the armed forces of", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "the Imperials are a fearsome sight to", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "behold. Those opposite gaze at one", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "another, gauging whether it might be", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "preferred to retreat. But this", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "superiority leads to carelessness, as", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "the Imperials assume that no one", pyxel.COLOR_WHITE)
                    pyxel.text(25, 112, "would dare attack one of their", pyxel.COLOR_WHITE)
                    pyxel.text(25, 118, "settlements for fear of retribution,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 124, "and thus leave them relatively", pyxel.COLOR_WHITE)
                    pyxel.text(25, 130, "undefended.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Units have 50% more power", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Settlements have 50% strength", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                elif self.faction_wiki_idx == 10:
                    pyxel.text(25, 40, "Atop a mountain in the north of these", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "lands, there is a people of a certain", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "philosophical nature. Instilled in all", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "from birth to death is the ideal of", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "determination, and achieving one's", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "goals no matter the cost, in time or", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "in life. Aptly dubbed by others as", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "The Persistent, these militaristic", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "people often elect to wear others down", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "through sieges and defensive", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "manoeuvres. Of course, such", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "strategies become ineffective against", pyxel.COLOR_WHITE)
                    pyxel.text(25, 112, "the well-prepared, but this does not", pyxel.COLOR_WHITE)
                    pyxel.text(25, 118, "bother The Persistent; they simply", pyxel.COLOR_WHITE)
                    pyxel.text(25, 124, "continue on.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Units have 50% more health", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Units have 75% of usual power", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                elif self.faction_wiki_idx == 11:
                    pyxel.text(25, 40, "Originating from an isolated part of", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "the globe, the Explorers were first", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "introduced to the wider world when a", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "lost trader stumbled across their", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "crude and underdeveloped settlement.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "Guiding the leaders of the settlement", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "out to the nearest other settlement,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "and returning to explain to the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "masses was significant. Once the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "Explorers got a taste, they have not", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "been able to stop. They look higher,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "run farther and dig deeper, at the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 112, "expense of their energy levels.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 118, "Unfortunately for the Explorers, the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 124, "required rest during the journey", pyxel.COLOR_WHITE)
                    pyxel.text(25, 130, "makes them easy targets for Heathens.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Units have 50% more stamina", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Units have 75% of usual health", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "GLUTTONY", pyxel.COLOR_GREEN)
                elif self.faction_wiki_idx == 12:
                    pyxel.text(25, 40, "Some say they were raised by Heathens,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "and some say that their DNA is", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "actually closer to Heathen than human.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "Regardless of their biological makeup,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "if you approach someone on the street", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "of any settlement and bring up the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "Infidels, you will be met with a look", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "of disgust and the question 'you're", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "not one of them, are you?'. Seen as", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "sub-human, other empires engage in", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "combat on sight with the Infidels,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "no matter the disguises they apply.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Not attacked by heathens", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Always attacked by AI players", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                elif self.faction_wiki_idx == 13:
                    pyxel.text(25, 40, "Long have The Nocturne worshipped the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 46, "holy moons of this world, and through", pyxel.COLOR_WHITE)
                    pyxel.text(25, 52, "repeated attempts to modify their", pyxel.COLOR_WHITE)
                    pyxel.text(25, 58, "circadian rhythm, the strongest among", pyxel.COLOR_WHITE)
                    pyxel.text(25, 64, "them have developed genetic abilities.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 70, "These abilities go further than simply", pyxel.COLOR_WHITE)
                    pyxel.text(25, 76, "making them nocturnal, no, they see", pyxel.COLOR_WHITE)
                    pyxel.text(25, 82, "farther and become stronger during the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 88, "nighttime, and have perfected the art", pyxel.COLOR_WHITE)
                    pyxel.text(25, 94, "of predicting the sundown. As all", pyxel.COLOR_WHITE)
                    pyxel.text(25, 100, "things are, however, there is a", pyxel.COLOR_WHITE)
                    pyxel.text(25, 106, "trade-off. When the sun is out, those", pyxel.COLOR_WHITE)
                    pyxel.text(25, 112, "of The Nocturne are weakened, and", pyxel.COLOR_WHITE)
                    pyxel.text(25, 118, "largely huddle together waiting for", pyxel.COLOR_WHITE)
                    pyxel.text(25, 124, "their precious darkness to return.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 140, "+ Thrive during the night", pyxel.COLOR_GREEN)
                    pyxel.text(25, 150, "- Units weakened during the day", pyxel.COLOR_RED)
                    pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
            elif self.wiki_showing is WikiOption.CLIMATE:
                pyxel.load("resources/sprites.pyxres")
                pyxel.rectb(20, 10, 160, 164, pyxel.COLOR_WHITE)
                pyxel.rect(21, 11, 158, 162, pyxel.COLOR_BLACK)
                pyxel.text(86, 15, "Climate", pyxel.COLOR_WHITE)
                pyxel.text(56, 162, "Press SPACE to go back", pyxel.COLOR_WHITE)
                if self.showing_night:
                    pyxel.blt(96, 25, 0, 8, 84, 8, 8)
                    pyxel.text(60, 35, "The Everlasting Night", pyxel.COLOR_DARK_BLUE)
                    pyxel.text(25, 45, "It's part of the life in this world.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 51, "It's the feeling running down your", pyxel.COLOR_WHITE)
                    pyxel.text(25, 57, "spine when you're walking the streets", pyxel.COLOR_WHITE)
                    pyxel.text(25, 63, "alone with only a torch to guide you.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 69, "It's the devastation when this month's", pyxel.COLOR_WHITE)
                    pyxel.text(25, 75, "cultivation is smaller than the last.", pyxel.COLOR_WHITE)
                    pyxel.text(25, 81, "It's the agony of looking out on a", pyxel.COLOR_WHITE)
                    pyxel.text(25, 87, "field of crops that won't grow. It's", pyxel.COLOR_WHITE)
                    pyxel.text(25, 93, "the fear of cursed heathens that could", pyxel.COLOR_WHITE)
                    pyxel.text(25, 99, "be lurking around every corner, ready", pyxel.COLOR_WHITE)
                    pyxel.text(25, 105, "to pounce. It's life during the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 111, "nighttime, and you pray to the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 117, "passions that the dawn soon comes.", pyxel.COLOR_WHITE)
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
                    pyxel.text(25, 45, "Each of those on this land can testify", pyxel.COLOR_WHITE)
                    pyxel.text(25, 51, "to the toll it takes on you. From the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 57, "heat of the sun when toiling in the", pyxel.COLOR_WHITE)
                    pyxel.text(25, 63, "fields, to the icy chill of the wind", pyxel.COLOR_WHITE)
                    pyxel.text(25, 69, "atop a mountain, it changes a man. But", pyxel.COLOR_WHITE)
                    pyxel.text(25, 75, "the climb is always worth the reward,", pyxel.COLOR_WHITE)
                    pyxel.text(25, 81, "and you truly feel one with the land", pyxel.COLOR_WHITE)
                    pyxel.text(25, 87, "as you gaze outward from the peak and", pyxel.COLOR_WHITE)
                    pyxel.text(25, 93, "fully absorb the graciousness of this", pyxel.COLOR_WHITE)
                    pyxel.text(25, 99, "world. This is home.", pyxel.COLOR_WHITE)
                    pyxel.line(24, 109, 175, 109, pyxel.COLOR_GRAY)
                    pyxel.text(25, 114, "Effects", pyxel.COLOR_WHITE)
                    pyxel.text(25, 124, "Persistent map and vision", pyxel.COLOR_GREEN)
                    pyxel.blt(158, 161, 0, 8, 84, 8, 8)
                    pyxel.text(168, 162, "->", pyxel.COLOR_WHITE)
            elif self.wiki_showing is WikiOption.BLESSINGS:
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
                        pyxel.text(160, 50 + adj_idx * 25, str(blessing.cost), pyxel.COLOR_WHITE)
                        pyxel.text(20, 57 + adj_idx * 25, str(blessing.description), pyxel.COLOR_WHITE)
                        imps = get_unlockable_improvements(blessing)
                        pyxel.text(20, 64 + adj_idx * 25, "U:", pyxel.COLOR_WHITE)
                        unlocked_names: typing.List[str] = []
                        if len(imps) > 0:
                            for imp in imps:
                                unlocked_names.append(imp.name)
                            if len(unlocked_names) > 0:
                                pyxel.text(28, 64 + adj_idx * 25, ", ".join(unlocked_names), pyxel.COLOR_WHITE)
                            else:
                                pyxel.text(28, 63 + adj_idx * 25, "victory", pyxel.COLOR_GREEN)
                        else:
                            pyxel.text(28, 63 + adj_idx * 25, "victory", pyxel.COLOR_GREEN)
                pyxel.text(56, 162, "Press SPACE to go back", pyxel.COLOR_WHITE)
                if self.blessing_boundaries[1] != len(BLESSINGS) - 1:
                    pyxel.text(152, 155, "More", pyxel.COLOR_WHITE)
                    pyxel.text(152, 161, "down!", pyxel.COLOR_WHITE)
                    pyxel.blt(172, 156, 0, 0, 76, 8, 8)
            elif self.wiki_showing is WikiOption.IMPROVEMENTS:
                pyxel.load("resources/sprites.pyxres")
                pyxel.rectb(10, 20, 180, 154, pyxel.COLOR_WHITE)
                pyxel.rect(11, 21, 178, 152, pyxel.COLOR_BLACK)
                pyxel.text(78, 30, "Improvements", pyxel.COLOR_ORANGE)
                pyxel.text(20, 40, "Name", pyxel.COLOR_WHITE)
                pyxel.text(155, 40, "Cost", pyxel.COLOR_WHITE)
                pyxel.blt(173, 39, 0, 16, 44, 8, 8)
                for idx, imp in enumerate(IMPROVEMENTS):
                    if self.improvement_boundaries[0] <= idx <= self.improvement_boundaries[1]:
                        adj_idx = idx - self.improvement_boundaries[0]
                        pyxel.text(20, 50 + adj_idx * 25, str(imp.name), pyxel.COLOR_WHITE)
                        pyxel.text(160, 50 + adj_idx * 25, str(imp.cost), pyxel.COLOR_WHITE)
                        pyxel.text(20, 57 + adj_idx * 25, str(imp.description), pyxel.COLOR_WHITE)
                        effects = 0
                        if imp.effect.wealth != 0:
                            sign = "+" if imp.effect.wealth > 0 else "-"
                            pyxel.text(20 + effects * 25, 64 + adj_idx * 25,
                                       f"{sign}{abs(imp.effect.wealth)}", pyxel.COLOR_YELLOW)
                            effects += 1
                        if imp.effect.harvest != 0:
                            sign = "+" if imp.effect.harvest > 0 else "-"
                            pyxel.text(20 + effects * 25, 64 + adj_idx * 25,
                                       f"{sign}{abs(imp.effect.harvest)}", pyxel.COLOR_GREEN)
                            effects += 1
                        if imp.effect.zeal != 0:
                            sign = "+" if imp.effect.zeal > 0 else "-"
                            pyxel.text(20 + effects * 25, 64 + adj_idx * 25,
                                       f"{sign}{abs(imp.effect.zeal)}", pyxel.COLOR_RED)
                            effects += 1
                        if imp.effect.fortune != 0:
                            sign = "+" if imp.effect.fortune > 0 else "-"
                            pyxel.text(20 + effects * 25, 64 + adj_idx * 25,
                                       f"{sign}{abs(imp.effect.fortune)}", pyxel.COLOR_PURPLE)
                            effects += 1
                        if imp.effect.strength != 0:
                            sign = "+" if imp.effect.strength > 0 else "-"
                            pyxel.blt(20 + effects * 25, 64 + adj_idx * 25, 0, 0, 28, 8, 8)
                            pyxel.text(30 + effects * 25, 64 + adj_idx * 25,
                                       f"{sign}{abs(imp.effect.strength)}", pyxel.COLOR_WHITE)
                            effects += 1
                        if imp.effect.satisfaction != 0:
                            sign = "+" if imp.effect.satisfaction > 0 else "-"
                            satisfaction_u = 8 if imp.effect.satisfaction >= 0 else 16
                            pyxel.blt(20 + effects * 25, 64 + adj_idx * 25, 0, satisfaction_u, 28, 8, 8)
                            pyxel.text(30 + effects * 25, 64 + adj_idx * 25,
                                       f"{sign}{abs(imp.effect.satisfaction)}", pyxel.COLOR_WHITE)
                pyxel.text(56, 162, "Press SPACE to go back", pyxel.COLOR_WHITE)
                if self.improvement_boundaries[1] != len(IMPROVEMENTS) - 1:
                    pyxel.text(152, 155, "More", pyxel.COLOR_WHITE)
                    pyxel.text(152, 161, "down!", pyxel.COLOR_WHITE)
                    pyxel.blt(172, 156, 0, 0, 76, 8, 8)
            elif self.wiki_showing is WikiOption.UNITS:
                pyxel.load("resources/sprites.pyxres")
                pyxel.rectb(10, 20, 180, 154, pyxel.COLOR_WHITE)
                pyxel.rect(11, 21, 178, 152, pyxel.COLOR_BLACK)
                pyxel.text(90, 30, "Units", pyxel.COLOR_WHITE)
                pyxel.text(20, 40, "Name", pyxel.COLOR_WHITE)
                pyxel.blt(90, 39, 0, 8, 36, 8, 8)
                pyxel.blt(110, 39, 0, 0, 36, 8, 8)
                pyxel.blt(130, 39, 0, 16, 36, 8, 8)
                pyxel.text(155, 40, "Cost", pyxel.COLOR_WHITE)
                pyxel.blt(173, 39, 0, 16, 44, 8, 8)
                for idx, unit in enumerate(UNIT_PLANS):
                    if self.unit_boundaries[0] <= idx <= self.unit_boundaries[1]:
                        adj_idx = idx - self.unit_boundaries[0]
                        pyxel.text(20, 50 + adj_idx * 10, str(unit.name), pyxel.COLOR_WHITE)
                        pyxel.text(160, 50 + adj_idx * 10, str(unit.cost), pyxel.COLOR_WHITE)
                        pyxel.text(88, 50 + adj_idx * 10, str(unit.max_health), pyxel.COLOR_WHITE)
                        pyxel.text(108, 50 + adj_idx * 10, str(unit.power), pyxel.COLOR_WHITE)
                        pyxel.text(132, 50 + adj_idx * 10, str(unit.total_stamina), pyxel.COLOR_WHITE)
                pyxel.text(56, 162, "Press SPACE to go back", pyxel.COLOR_WHITE)
                if self.unit_boundaries[1] != len(UNIT_PLANS) - 1:
                    pyxel.text(152, 155, "More", pyxel.COLOR_WHITE)
                    pyxel.text(152, 161, "down!", pyxel.COLOR_WHITE)
                    pyxel.blt(172, 156, 0, 0, 76, 8, 8)
            elif self.wiki_showing is None:
                pyxel.rectb(60, 55, 80, 100, pyxel.COLOR_WHITE)
                pyxel.rect(61, 56, 78, 98, pyxel.COLOR_BLACK)
                pyxel.text(92, 60, "Wiki", pyxel.COLOR_WHITE)
                pyxel.text(82, 75, "Victories",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.VICTORIES else pyxel.COLOR_WHITE)
                pyxel.text(85, 85, "Factions",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.FACTIONS else pyxel.COLOR_WHITE)
                pyxel.text(86, 95, "Climate",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.CLIMATE else pyxel.COLOR_WHITE)
                pyxel.text(82, 105, "Blessings",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.BLESSINGS else pyxel.COLOR_WHITE)
                pyxel.text(78, 115, "Improvements",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.IMPROVEMENTS else pyxel.COLOR_WHITE)
                pyxel.text(90, 125, "Units",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.UNITS else pyxel.COLOR_WHITE)
                pyxel.text(92, 145, "Back", pyxel.COLOR_RED if self.wiki_option is None else pyxel.COLOR_WHITE)
        else:
            pyxel.rectb(75, 120, 50, 60, pyxel.COLOR_WHITE)
            pyxel.rect(76, 121, 48, 58, pyxel.COLOR_BLACK)
            pyxel.text(82, 125, "MICROCOSM", pyxel.COLOR_WHITE)
            pyxel.text(85, 140, "New Game",
                       pyxel.COLOR_RED if self.menu_option is MenuOption.NEW_GAME else pyxel.COLOR_WHITE)
            pyxel.text(82, 150, "Load Game",
                       pyxel.COLOR_RED if self.menu_option is MenuOption.LOAD_GAME else pyxel.COLOR_WHITE)
            pyxel.text(92, 160, "Wiki",
                       pyxel.COLOR_RED if self.menu_option is MenuOption.WIKI else pyxel.COLOR_WHITE)
            pyxel.text(92, 170, "Exit",
                       pyxel.COLOR_RED if self.menu_option is MenuOption.EXIT else pyxel.COLOR_WHITE)

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
            if self.in_game_setup and not self.showing_faction_details:
                if self.setup_option is SetupOption.PLAYER_FACTION:
                    self.setup_option = SetupOption.PLAYER_COUNT
                elif self.setup_option is SetupOption.PLAYER_COUNT:
                    self.setup_option = SetupOption.BIOME_CLUSTERING
                elif self.setup_option is SetupOption.BIOME_CLUSTERING:
                    self.setup_option = SetupOption.FOG_OF_WAR
                elif self.setup_option is SetupOption.FOG_OF_WAR:
                    self.setup_option = SetupOption.CLIMATIC_EFFECTS
                elif self.setup_option is SetupOption.CLIMATIC_EFFECTS:
                    self.setup_option = SetupOption.START_GAME
            elif self.loading_game:
                if 0 <= self.save_idx < len(self.saves) - 1:
                    self.save_idx += 1
                elif self.save_idx == len(self.saves) - 1:
                    self.save_idx = -1
            elif self.in_wiki:
                if self.wiki_showing is WikiOption.BLESSINGS:
                    if self.blessing_boundaries[1] < len(BLESSINGS) - 1:
                        self.blessing_boundaries = self.blessing_boundaries[0] + 1, self.blessing_boundaries[1] + 1
                elif self.wiki_showing is WikiOption.IMPROVEMENTS:
                    if self.improvement_boundaries[1] < len(IMPROVEMENTS) - 1:
                        self.improvement_boundaries = \
                            self.improvement_boundaries[0] + 1, self.improvement_boundaries[1] + 1
                elif self.wiki_showing is WikiOption.UNITS:
                    if self.unit_boundaries[1] < len(UNIT_PLANS) - 1:
                        self.unit_boundaries = self.unit_boundaries[0] + 1, self.unit_boundaries[1] + 1
                else:
                    if self.wiki_option is WikiOption.VICTORIES:
                        self.wiki_option = WikiOption.FACTIONS
                    elif self.wiki_option is WikiOption.FACTIONS:
                        self.wiki_option = WikiOption.CLIMATE
                    elif self.wiki_option is WikiOption.CLIMATE:
                        self.wiki_option = WikiOption.BLESSINGS
                    elif self.wiki_option is WikiOption.BLESSINGS:
                        self.wiki_option = WikiOption.IMPROVEMENTS
                    elif self.wiki_option is WikiOption.IMPROVEMENTS:
                        self.wiki_option = WikiOption.UNITS
                    elif self.wiki_option is WikiOption.UNITS:
                        self.wiki_option = None
            else:
                if self.menu_option is MenuOption.NEW_GAME:
                    self.menu_option = MenuOption.LOAD_GAME
                elif self.menu_option is MenuOption.LOAD_GAME:
                    self.menu_option = MenuOption.WIKI
                elif self.menu_option is MenuOption.WIKI:
                    self.menu_option = MenuOption.EXIT
        if up:
            # Ensure that players cannot navigate the root menu while the faction details overlay is being shown.
            if self.in_game_setup and not self.showing_faction_details:
                if self.setup_option is SetupOption.PLAYER_COUNT:
                    self.setup_option = SetupOption.PLAYER_FACTION
                elif self.setup_option is SetupOption.BIOME_CLUSTERING:
                    self.setup_option = SetupOption.PLAYER_COUNT
                elif self.setup_option is SetupOption.FOG_OF_WAR:
                    self.setup_option = SetupOption.BIOME_CLUSTERING
                elif self.setup_option is SetupOption.CLIMATIC_EFFECTS:
                    self.setup_option = SetupOption.FOG_OF_WAR
                elif self.setup_option is SetupOption.START_GAME:
                    self.setup_option = SetupOption.CLIMATIC_EFFECTS
            elif self.loading_game:
                if self.save_idx == -1:
                    self.save_idx = len(self.saves) - 1
                elif self.save_idx > 0:
                    self.save_idx -= 1
            elif self.in_wiki:
                if self.wiki_showing is WikiOption.BLESSINGS:
                    if self.blessing_boundaries[0] > 0:
                        self.blessing_boundaries = self.blessing_boundaries[0] - 1, self.blessing_boundaries[1] - 1
                elif self.wiki_showing is WikiOption.IMPROVEMENTS:
                    if self.improvement_boundaries[0] > 0:
                        self.improvement_boundaries = \
                            self.improvement_boundaries[0] - 1, self.improvement_boundaries[1] - 1
                elif self.wiki_showing is WikiOption.UNITS:
                    if self.unit_boundaries[0] > 0:
                        self.unit_boundaries = self.unit_boundaries[0] - 1, self.unit_boundaries[1] - 1
                else:
                    if self.wiki_option is WikiOption.FACTIONS:
                        self.wiki_option = WikiOption.VICTORIES
                    elif self.wiki_option is WikiOption.CLIMATE:
                        self.wiki_option = WikiOption.FACTIONS
                    elif self.wiki_option is WikiOption.BLESSINGS:
                        self.wiki_option = WikiOption.CLIMATE
                    elif self.wiki_option is WikiOption.IMPROVEMENTS:
                        self.wiki_option = WikiOption.BLESSINGS
                    elif self.wiki_option is WikiOption.UNITS:
                        self.wiki_option = WikiOption.IMPROVEMENTS
                    elif self.wiki_option is None:
                        self.wiki_option = WikiOption.UNITS
            else:
                if self.menu_option is MenuOption.LOAD_GAME:
                    self.menu_option = MenuOption.NEW_GAME
                elif self.menu_option is MenuOption.WIKI:
                    self.menu_option = MenuOption.LOAD_GAME
                elif self.menu_option is MenuOption.EXIT:
                    self.menu_option = MenuOption.WIKI
        if left:
            if self.in_game_setup:
                if self.setup_option is SetupOption.PLAYER_FACTION:
                    self.faction_idx = clamp(self.faction_idx - 1, 0, len(self.faction_colours) - 1)
                elif self.setup_option is SetupOption.PLAYER_COUNT:
                    self.player_count = max(2, self.player_count - 1)
                elif self.setup_option is SetupOption.BIOME_CLUSTERING:
                    self.biome_clustering_enabled = False
                elif self.setup_option is SetupOption.FOG_OF_WAR:
                    self.fog_of_war_enabled = False
                elif self.setup_option is SetupOption.CLIMATIC_EFFECTS:
                    self.climatic_effects_enabled = False
            elif self.in_wiki and self.wiki_showing is WikiOption.VICTORIES:
                if self.victory_type is VictoryType.JUBILATION:
                    self.victory_type = VictoryType.ELIMINATION
                elif self.victory_type is VictoryType.GLUTTONY:
                    self.victory_type = VictoryType.JUBILATION
                elif self.victory_type is VictoryType.AFFLUENCE:
                    self.victory_type = VictoryType.GLUTTONY
                elif self.victory_type is VictoryType.VIGOUR:
                    self.victory_type = VictoryType.AFFLUENCE
                elif self.victory_type is VictoryType.SERENDIPITY:
                    self.victory_type = VictoryType.VIGOUR
            elif self.in_wiki and self.wiki_showing is WikiOption.FACTIONS and self.faction_wiki_idx != 0:
                self.faction_wiki_idx -= 1
            elif self.in_wiki and self.wiki_showing is WikiOption.CLIMATE:
                self.showing_night = False
        if right:
            if self.in_game_setup:
                if self.setup_option is SetupOption.PLAYER_FACTION:
                    self.faction_idx = clamp(self.faction_idx + 1, 0, len(self.faction_colours) - 1)
                elif self.setup_option is SetupOption.PLAYER_COUNT:
                    self.player_count = min(14, self.player_count + 1)
                elif self.setup_option is SetupOption.BIOME_CLUSTERING:
                    self.biome_clustering_enabled = True
                elif self.setup_option is SetupOption.FOG_OF_WAR:
                    self.fog_of_war_enabled = True
                elif self.setup_option is SetupOption.CLIMATIC_EFFECTS:
                    self.climatic_effects_enabled = True
            elif self.in_wiki and self.wiki_showing is WikiOption.VICTORIES:
                if self.victory_type is VictoryType.ELIMINATION:
                    self.victory_type = VictoryType.JUBILATION
                elif self.victory_type is VictoryType.JUBILATION:
                    self.victory_type = VictoryType.GLUTTONY
                elif self.victory_type is VictoryType.GLUTTONY:
                    self.victory_type = VictoryType.AFFLUENCE
                elif self.victory_type is VictoryType.AFFLUENCE:
                    self.victory_type = VictoryType.VIGOUR
                elif self.victory_type is VictoryType.VIGOUR:
                    self.victory_type = VictoryType.SERENDIPITY
            elif self.in_wiki and self.wiki_showing is WikiOption.FACTIONS and \
                    self.faction_wiki_idx != len(self.faction_colours) - 1:
                self.faction_wiki_idx += 1
            elif self.in_wiki and self.wiki_showing is WikiOption.CLIMATE:
                self.showing_night = True

    def get_game_config(self) -> GameConfig:
        """
        Returns the game config based on the setup screen selections.
        :return: The appropriate GameConfig object.
        """
        return GameConfig(self.player_count, self.faction_colours[self.faction_idx][0], self.biome_clustering_enabled,
                          self.fog_of_war_enabled, self.climatic_effects_enabled)
