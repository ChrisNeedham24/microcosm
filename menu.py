import random
import typing
from enum import Enum

import pyxel

from calculator import clamp
from catalogue import BLESSINGS, get_unlockable_improvements, IMPROVEMENTS, UNIT_PLANS
from models import GameConfig, VictoryType


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
    PLAYER_COLOUR = "COLOUR"
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
    CLIMATE = "CLIM"
    BLESSINGS = "BLS"
    IMPROVEMENTS = "IMP"
    UNITS = "UNITS"


# A convenient list of all available colours. Deliberately excludes black and white.
AVAILABLE_COLOURS = [
    ("Navy", pyxel.COLOR_NAVY),
    ("Purple", pyxel.COLOR_PURPLE),
    ("Green", pyxel.COLOR_GREEN),
    ("Brown", pyxel.COLOR_BROWN),
    ("Dark blue", pyxel.COLOR_DARK_BLUE),
    ("Light blue", pyxel.COLOR_LIGHT_BLUE),
    ("Red", pyxel.COLOR_RED),
    ("Orange", pyxel.COLOR_ORANGE),
    ("Yellow", pyxel.COLOR_YELLOW),
    ("Lime", pyxel.COLOR_LIME),
    ("Cyan", pyxel.COLOR_CYAN),
    ("Grey", pyxel.COLOR_GRAY),
    ("Pink", pyxel.COLOR_PINK),
    ("Peach", pyxel.COLOR_PEACH)
]


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
        self.setup_option = SetupOption.PLAYER_COLOUR
        self.colour_idx = 0
        self.player_count = 2
        self.biome_clustering_enabled = True
        self.fog_of_war_enabled = True
        self.climatic_effects_enabled = True
        self.showing_night = False

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
            pyxel.text(28, 40, "Player Colour",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.PLAYER_COLOUR else pyxel.COLOR_WHITE)
            colour_offset = 5 - len(AVAILABLE_COLOURS[self.colour_idx][0])
            if self.colour_idx == 0:
                pyxel.text(130 + colour_offset, 40, f"{AVAILABLE_COLOURS[self.colour_idx][0]} ->",
                           AVAILABLE_COLOURS[self.colour_idx][1])
            elif self.colour_idx == len(AVAILABLE_COLOURS) - 1:
                pyxel.text(130 + colour_offset, 40, f"<- {AVAILABLE_COLOURS[self.colour_idx][0]}",
                           AVAILABLE_COLOURS[self.colour_idx][1])
            else:
                pyxel.text(120 + colour_offset, 40, f"<- {AVAILABLE_COLOURS[self.colour_idx][0]} ->",
                           AVAILABLE_COLOURS[self.colour_idx][1])
            pyxel.text(28, 60, "Player Count",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.PLAYER_COUNT else pyxel.COLOR_WHITE)
            if self.player_count == 2:
                pyxel.text(140, 60, "2 ->", pyxel.COLOR_WHITE)
            elif 2 < self.player_count < 14:
                pyxel.text(130, 60, f"<- {self.player_count} ->", pyxel.COLOR_WHITE)
            else:
                pyxel.text(130, 60, "<- 14", pyxel.COLOR_WHITE)
            pyxel.text(28, 80, "Biome Clustering",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.BIOME_CLUSTERING else pyxel.COLOR_WHITE)
            if self.biome_clustering_enabled:
                pyxel.text(125, 80, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 80, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(28, 100, "Fog of War",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.FOG_OF_WAR else pyxel.COLOR_WHITE)
            if self.fog_of_war_enabled:
                pyxel.text(125, 100, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 100, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(28, 120, "Climatic Effects",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.CLIMATIC_EFFECTS else pyxel.COLOR_WHITE)
            if self.climatic_effects_enabled:
                pyxel.text(125, 120, "<- Enabled", pyxel.COLOR_GREEN)
            else:
                pyxel.text(125, 120, "Disabled ->", pyxel.COLOR_RED)
            pyxel.text(81, 150, "Start Game",
                       pyxel.COLOR_RED if self.setup_option is SetupOption.START_GAME else pyxel.COLOR_WHITE)
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
                pyxel.rectb(60, 55, 80, 90, pyxel.COLOR_WHITE)
                pyxel.rect(61, 56, 78, 88, pyxel.COLOR_BLACK)
                pyxel.text(92, 60, "Wiki", pyxel.COLOR_WHITE)
                pyxel.text(82, 75, "Victories",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.VICTORIES else pyxel.COLOR_WHITE)
                pyxel.text(86, 85, "Climate",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.CLIMATE else pyxel.COLOR_WHITE)
                pyxel.text(82, 95, "Blessings",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.BLESSINGS else pyxel.COLOR_WHITE)
                pyxel.text(78, 105, "Improvements",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.IMPROVEMENTS else pyxel.COLOR_WHITE)
                pyxel.text(90, 115, "Units",
                           pyxel.COLOR_RED if self.wiki_option is WikiOption.UNITS else pyxel.COLOR_WHITE)
                pyxel.text(92, 135, "Back", pyxel.COLOR_RED if self.wiki_option is None else pyxel.COLOR_WHITE)
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
            if self.in_game_setup:
                if self.setup_option is SetupOption.PLAYER_COLOUR:
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
            if self.in_game_setup:
                if self.setup_option is SetupOption.PLAYER_COUNT:
                    self.setup_option = SetupOption.PLAYER_COLOUR
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
                    if self.wiki_option is WikiOption.CLIMATE:
                        self.wiki_option = WikiOption.VICTORIES
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
                if self.setup_option is SetupOption.PLAYER_COLOUR:
                    self.colour_idx = clamp(self.colour_idx - 1, 0, len(AVAILABLE_COLOURS) - 1)
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
            elif self.in_wiki and self.wiki_showing is WikiOption.CLIMATE:
                self.showing_night = False
        if right:
            if self.in_game_setup:
                if self.setup_option is SetupOption.PLAYER_COLOUR:
                    self.colour_idx = clamp(self.colour_idx + 1, 0, len(AVAILABLE_COLOURS) - 1)
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
            elif self.in_wiki and self.wiki_showing is WikiOption.CLIMATE:
                self.showing_night = True

    def get_game_config(self) -> GameConfig:
        """
        Returns the game config based on the setup screen selections.
        :return: The appropriate GameConfig object.
        """
        return GameConfig(self.player_count, AVAILABLE_COLOURS[self.colour_idx][1], self.biome_clustering_enabled,
                          self.fog_of_war_enabled, self.climatic_effects_enabled)
