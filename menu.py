import random
import typing
from enum import Enum

import pyxel

from calculator import clamp
from catalogue import BLESSINGS, get_unlockable_improvements, IMPROVEMENTS, UNIT_PLANS, FACTION_COLOURS, PROJECTS
from models import GameConfig, VictoryType, Faction, ProjectType


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
    PROJECTS = "PRJ"
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
        self.load_game_boundaries = 0, 9

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
            pyxel.rectb(20, 20, 160, 154, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 152, pyxel.COLOR_BLACK)
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
            match self.player_count:
                case 2:
                    pyxel.text(140, 65, "2 ->", pyxel.COLOR_WHITE)
                case 14:
                    pyxel.text(130, 65, "<- 14", pyxel.COLOR_WHITE)
                case _:
                    pyxel.text(130, 65, f"<- {self.player_count} ->", pyxel.COLOR_WHITE)

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
            pyxel.text(52, 160, "(Press SPACE to go back)", pyxel.COLOR_WHITE)

            if self.showing_faction_details:
                pyxel.load("resources/sprites.pyxres")
                pyxel.rectb(30, 30, 140, 124, pyxel.COLOR_WHITE)
                pyxel.rect(31, 31, 138, 122, pyxel.COLOR_BLACK)
                pyxel.text(70, 35, "Faction Details", pyxel.COLOR_WHITE)
                pyxel.text(35, 50, str(self.faction_colours[self.faction_idx][0].value),
                           self.faction_colours[self.faction_idx][1])
                pyxel.text(35, 110, "Recommended victory:", pyxel.COLOR_WHITE)

                match self.faction_idx:
                    case 0:
                        pyxel.text(35, 70, "+ Immune to poor harvest", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Generates 75% of usual zeal", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "GLUTTONY", pyxel.COLOR_GREEN)
                    case 1:
                        pyxel.text(35, 70, "+ Immune to recession", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Double low harvest penalty", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "AFFLUENCE", pyxel.COLOR_YELLOW)
                    case 2:
                        pyxel.text(35, 70, "+ Investigations always succeed", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Generates 75% of usual fortune", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)
                    case 3:
                        pyxel.text(35, 70, "+ Generates 125% of usual wealth", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Blessings cost 125% of usual", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "AFFLUENCE", pyxel.COLOR_YELLOW)
                    case 4:
                        pyxel.text(35, 70, "+ Generates 125% of usual harvest", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Settlements capped at level 5", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "JUBILATION", pyxel.COLOR_GREEN)
                    case 5:
                        pyxel.text(35, 70, "+ Generates 125% of usual zeal", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Construction buyouts disabled", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "VIGOUR", pyxel.COLOR_ORANGE)
                    case 6:
                        pyxel.text(35, 70, "+ Generates 125% of usual fortune", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Generates 75% of usual wealth", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "SERENDIPITY", pyxel.COLOR_PURPLE)
                    case 7:
                        pyxel.text(35, 70, "+ Settlements have 200% strength", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Limited to a single settlement", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)
                    case 8:
                        pyxel.text(35, 70, "+ Base satisfaction is 75", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Settlers only at level 5", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "JUBILATION", pyxel.COLOR_GREEN)
                    case 9:
                        pyxel.text(35, 70, "+ Units have 50% more power", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Settlements have 50% strength", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)
                    case 10:
                        pyxel.text(35, 70, "+ Units have 50% more health", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Units have 75% of usual power", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)
                    case 11:
                        pyxel.text(35, 70, "+ Units have 50% more stamina", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Units have 75% of usual health", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "GLUTTONY", pyxel.COLOR_GREEN)
                    case 12:
                        pyxel.text(35, 70, "+ Special affinity with heathens", pyxel.COLOR_GREEN)
                        pyxel.text(35, 90, "- Always attacked by AI players", pyxel.COLOR_RED)
                        pyxel.text(35, 120, "ELIMINATION", pyxel.COLOR_RED)
                    case 13:
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
            pyxel.load("resources/sprites.pyxres")
            pyxel.rectb(20, 20, 160, 144, pyxel.COLOR_WHITE)
            pyxel.rect(21, 21, 158, 142, pyxel.COLOR_BLACK)
            pyxel.text(81, 25, "Load Game", pyxel.COLOR_WHITE)
            for idx, save in enumerate(self.saves):
                if self.load_game_boundaries[0] <= idx <= self.load_game_boundaries[1]:
                    pyxel.text(25, 35 + (idx - self.load_game_boundaries[0]) * 10, save, pyxel.COLOR_WHITE)
                    pyxel.text(150, 35 + (idx - self.load_game_boundaries[0]) * 10, "Load",
                               pyxel.COLOR_RED if self.save_idx is idx else pyxel.COLOR_WHITE)
            if self.load_game_boundaries[1] != len(self.saves) - 1:
                pyxel.text(147, 135, "More", pyxel.COLOR_WHITE)
                pyxel.text(147, 141, "down!", pyxel.COLOR_WHITE)
                pyxel.blt(167, 136, 0, 0, 76, 8, 8)
            pyxel.text(56, 152, "Press SPACE to go back", pyxel.COLOR_WHITE)
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
                            pyxel.text(30, 60, "Take control of all settlements", pyxel.COLOR_WHITE)
                            pyxel.line(24, 70, 175, 70, pyxel.COLOR_GRAY)
                            self.draw_paragraph(25, 75, """Like any strong leader, you want the best for your people. However,
                                                constant attacks by filthy Heathens and enemy troops are enough to wear any 
                                                great leader down. It is time to put an end to this, and become the one true 
                                                empire. Other empires will wither at your blade, and they will be all the more 
                                                thankful for it.""", 38)
                            pyxel.blt(158, 150, 0, 8, 28, 8, 8)
                            pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                        case VictoryType.JUBILATION:
                            pyxel.text(80, 40, "JUBILATION", pyxel.COLOR_GREEN)
                            pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                            pyxel.text(30, 60, "Maintain 100% satisfaction in 5+", pyxel.COLOR_WHITE)
                            pyxel.text(30, 66, "settlements for 25 turns", pyxel.COLOR_WHITE)
                            pyxel.line(24, 76, 175, 76, pyxel.COLOR_GRAY)
                            self.draw_paragraph(25, 81, """Your rule as leader is solid, your subjects faithful. But there is
                                                something missing. Your subjects, while not rebellious, do not have the love 
                                                for you that you so desire. So be it. You will fill your empire with bread and 
                                                circuses; your subjects will be the envy of all! And quietly, your rule will be 
                                                unquestioned.""", 38)
                            pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(35, 150, 0, 0, 36, 8, 8)
                            pyxel.blt(158, 150, 0, 8, 44, 8, 8)
                            pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                        case VictoryType.GLUTTONY:
                            pyxel.text(84, 40, "GLUTTONY", pyxel.COLOR_GREEN)
                            pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                            pyxel.text(30, 60, "Reach level 10 in 10+ settlements", pyxel.COLOR_WHITE)
                            pyxel.line(24, 70, 175, 70, pyxel.COLOR_GRAY)
                            self.draw_paragraph(25, 75, """There is nothing more satisfying as a leader than tucking into a
                                                generous meal prepared by your servants. But as a benevolent leader, you 
                                                question why you alone can enjoy such luxuries. You resolve to make it your 
                                                mission to feed the masses, grow your empire and spread around the plains!""",
                                                38)
                            pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(35, 150, 0, 8, 28, 8, 8)
                            pyxel.blt(158, 150, 0, 0, 44, 8, 8)
                            pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                        case VictoryType.AFFLUENCE:
                            pyxel.text(82, 40, "AFFLUENCE", pyxel.COLOR_YELLOW)
                            pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                            pyxel.text(30, 60, "Accumulate 100,000 wealth over the", pyxel.COLOR_WHITE)
                            pyxel.text(30, 66, "course of the game", pyxel.COLOR_WHITE)
                            pyxel.line(24, 76, 175, 76, pyxel.COLOR_GRAY)
                            self.draw_paragraph(25, 81, """Your empire has fallen on hard times. Recent conflicts have not gone
                                                your way, your lands have been seized, and your treasuries are empty. This is 
                                                no way for an empire to be. Your advisors tell you of untapped riches in the 
                                                vast deserts. You make it your mission to squeeze every last copper out of 
                                                those dunes, and out of the whole world!""", 38)
                            pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(35, 150, 0, 8, 44, 8, 8)
                            pyxel.blt(158, 150, 0, 16, 44, 8, 8)
                            pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                        case VictoryType.VIGOUR:
                            pyxel.text(88, 40, "VIGOUR", pyxel.COLOR_ORANGE)
                            pyxel.text(25, 45, "Objectives:", pyxel.COLOR_WHITE)
                            pyxel.text(30, 55, "Undergo the Ancient History blessing", pyxel.COLOR_WHITE)
                            pyxel.text(30, 65, "Construct the holy sanctum in a", pyxel.COLOR_WHITE)
                            pyxel.text(30, 71, "settlement", pyxel.COLOR_WHITE)
                            pyxel.line(24, 77, 175, 77, pyxel.COLOR_GRAY)
                            self.draw_paragraph(25, 80, """You have always been fascinated with the bygone times of your empire
                                                and its rich history. There is never a better time than the present to devote 
                                                some time to your studies. Your advisors tell you that the educated among your 
                                                subjects have been doing some research recently, and have unearthed the plans 
                                                for some form of Holy Sanctum. You make it your mission to construct said 
                                                sanctum.""", 38)
                            pyxel.text(25, 152, "<-", pyxel.COLOR_WHITE)
                            pyxel.blt(35, 150, 0, 0, 44, 8, 8)
                            pyxel.blt(158, 151, 0, 24, 44, 8, 8)
                            pyxel.text(168, 152, "->", pyxel.COLOR_WHITE)
                        case VictoryType.SERENDIPITY:
                            pyxel.text(78, 40, "SERENDIPITY", pyxel.COLOR_PURPLE)
                            pyxel.text(25, 50, "Objective:", pyxel.COLOR_WHITE)
                            pyxel.text(30, 60, "Undergo the three blessings of", pyxel.COLOR_WHITE)
                            pyxel.text(30, 66, "ardour: the pieces of strength,", pyxel.COLOR_WHITE)
                            pyxel.text(30, 72, "passion, and divinity.", pyxel.COLOR_WHITE)
                            pyxel.line(24, 82, 175, 82, pyxel.COLOR_GRAY)
                            self.draw_paragraph(25, 87, """Local folklore has always said that a man of the passions was a man
                                                unparalleled amongst his peers. You have long aspired to be such a man, and 
                                                such a leader. You consult your local sects and are informed that you are now 
                                                ready to make the arduous journey of enlightenment and fulfillment. You grasp 
                                                the opportunity with two hands, as a blessed man.""", 38)
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

                    match self.faction_wiki_idx:
                        case 0:
                            self.draw_paragraph(25, 40, """Using techniques passed down through the generations, the
                                                Agriculturists are able to sustain their populace through famine and indeed 
                                                through feast. Some of this land's greatest delicacies are grown by these 
                                                humble people, who insist that anyone could grow what they do, winking at one 
                                                another as they say it. Without the spectre of hunger on the horizon, the 
                                                Agriculturists lead the slow life, indulging in pleasures at their own pace.
                                                """, 38)
                            pyxel.text(25, 140, "+ Immune to poor harvest", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Generates 75% of usual zeal", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "GLUTTONY", pyxel.COLOR_GREEN)
                        case 1:
                            self.draw_paragraph(25, 40, """The sky-high towers and luxurious dwellings found throughout their
                                                cities represent the Capitalists to the fullest. They value the clink of coins 
                                                over anything else, and it has served them well so far. However, if you take a 
                                                look around the corner, things are clearly not as the seem. And as the slums 
                                                fill up, there better be enough food to go around, lest something... dangerous 
                                                happens.""", 38)
                            pyxel.text(25, 140, "+ Immune to recession", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Double low harvest penalty", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "AFFLUENCE", pyxel.COLOR_YELLOW)
                        case 2:
                            self.draw_paragraph(25, 40, """Due to a genetic trait, the Scrutineers have always had good
                                                eyesight and they use it to full effect. Nothing gets past them, from the 
                                                temples of the outlands to the streets of their cities. But, as it goes, the 
                                                devil is in the details, as the local clergy certainly aren't exempt from the 
                                                all-seeing eye, with blessings being stymied as much as is humanly possible.
                                                """, 38)
                            pyxel.text(25, 140, "+ Investigations always succeed", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Generates 75% of usual fortune", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                        case 3:
                            self.draw_paragraph(25, 40, """Many eons ago, a subsection of the population of these lands began
                                                to question the effectiveness of their blessings after years of squalor and 
                                                oppression. They shook free their bonds and formed their own community based 
                                                around the one thing that proved valuable to all people: currency. However, 
                                                despite shunning blessings at every opportunity, The Godless, as they became 
                                                known, are wont to dabble in blessings in moments of weakness, and what's left 
                                                of their clergy makes sure to sink the boot in.""", 38)
                            pyxel.text(25, 140, "+ Generates 125% of usual wealth", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Blessings cost 125% of usual", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "AFFLUENCE", pyxel.COLOR_YELLOW)
                        case 4:
                            self.draw_paragraph(25, 40, """Originating from a particular fertile part of these lands, The
                                                Ravenous have enjoyed bountiful harvests for centuries. No matter the skill of 
                                                the farmer, or the quality of the seeds, a cultivation of significant size is 
                                                always created after some months. But with such consistency, comes complacency.
                                                Those that have resided in settlements occupied by The Ravenous, over time, 
                                                grow greedy. As populations increase, and more food is available, the existing 
                                                residents seek to keep it all for themselves, as newcomers are given the 
                                                unbearable choice of starving or leaving.""", 38)
                            pyxel.text(25, 140, "+ Generates 125% of usual harvest", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Settlements capped at level 5", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "JUBILATION", pyxel.COLOR_GREEN)
                        case 5:
                            self.draw_paragraph(25, 40, """There's nothing quite like the clang of iron striking iron to truly
                                                ground a person in their surroundings. This is a fact that the Fundamentalists 
                                                know well, as every child of a certain age is required to serve as an 
                                                apprentice in a local forge or refinery. With such resources at their disposal, 
                                                work is done quickly. And yet, suggestions that constructions should be made 
                                                quicker, and in some cases instantaneous, through the use of empire funds are 
                                                met with utter disgust by the people. For the Fundamentalists, everything must 
                                                be done the right way.""", 38)
                            pyxel.text(25, 140, "+ Generates 125% of usual zeal", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Construction buyouts disabled", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "VIGOUR", pyxel.COLOR_ORANGE)
                        case 6:
                            self.draw_paragraph(25, 40, """Glory to the ancient ones, and glory to the passionate. The Orthodox
                                                look to those that came before them for guidance, and they are justly rewarded 
                                                that, with enlightenment and discoveries occurring frequently. As the 
                                                passionate tend to do, however, the clatter of coin in the palm is met with a 
                                                stern decline. Content they are with their existence, The Orthodox rely on 
                                                seeing what others cannot.""", 38)
                            pyxel.text(25, 140, "+ Generates 125% of usual fortune", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Generates 75% of usual wealth", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "SERENDIPITY", pyxel.COLOR_PURPLE)
                        case 7:
                            self.draw_paragraph(25, 40, """For the unfamiliar, visiting the settlement of The Concentrated can
                                                be overwhelming. The sheer mass of people everywhere one looks along with the 
                                                cloud-breaching towers can make one feel like they have been transported to 
                                                some distant future. It is this intimidatory factor, in combination with the 
                                                colossal ramparts surrounding the megapolis that have kept The Concentrated 
                                                safe and sound for many years.""", 38)
                            pyxel.text(25, 140, "+ Settlements have 200% strength", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Limited to a single settlement", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                        case 8:
                            self.draw_paragraph(25, 40, """Blink and you'll miss it; that's the story of the settlements of the
                                                Frontier. The Frontiersmen have a near obsession with the thrill of the 
                                                frontier and making something of inhospitable terrain, in situations where 
                                                others could not. Residing in a new settlement is considered to be the pinnacle 
                                                of Frontier achievement, but the shine wears off quickly. After some time, the 
                                                people become restless and seek to expand further. And thus the cycle repeats.
                                                """, 38)
                            pyxel.text(25, 140, "+ Base satisfaction is 75", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Settlers only at level 5", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "JUBILATION", pyxel.COLOR_GREEN)
                        case 9:
                            self.draw_paragraph(25, 40, """The concept of raw power and strength has long been a core tenet of
                                                the self-dubbed Empire, with compulsory military service a cultural feature. 
                                                Drilled into the populace for such an extensive period, the armed forces of the 
                                                Imperials are a fearsome sight to behold. Those opposite gaze at one another, 
                                                gauging whether it might be preferred to retreat. But this superiority leads to 
                                                carelessness, as the Imperials assume that no one would dare attack one of 
                                                their settlements for fear of retribution, and thus leave them relatively 
                                                undefended.""", 38)
                            pyxel.text(25, 140, "+ Units have 50% more power", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Settlements have 50% strength", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                        case 10:
                            self.draw_paragraph(25, 40, """Atop a mountain in the north of these lands, there is a people of a
                                                certain philosophical nature. Instilled in all from birth to death is the ideal 
                                                of determination, and achieving one's goals no matter the cost, in time or in 
                                                life. Aptly dubbed by others as The Persistent, these militaristic people often 
                                                elect to wear others down through sieges and defensive manoeuvres. Of course, 
                                                such strategies become ineffective against the well-prepared, but this does not 
                                                bother The Persistent; they simply continue on.""", 38)
                            pyxel.text(25, 140, "+ Units have 50% more health", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Units have 75% of usual power", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                        case 11:
                            self.draw_paragraph(25, 40, """Originating from an isolated part of the globe, the Explorers were
                                                first introduced to the wider world when a lost trader stumbled across their 
                                                crude and underdeveloped settlement. Guiding the leaders of the settlement out 
                                                to the nearest other settlement, and returning to explain to the masses was 
                                                significant. Once the Explorers got a taste, they have not been able to stop. 
                                                They look higher, run farther and dig deeper, at the expense of their energy 
                                                levels. Unfortunately for the Explorers, the required rest during the journey 
                                                makes them easy targets for Heathens.""", 38)
                            pyxel.text(25, 140, "+ Units have 50% more stamina", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Units have 75% of usual health", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "GLUTTONY", pyxel.COLOR_GREEN)
                        case 12:
                            self.draw_paragraph(25, 40, """Some say they were raised by Heathens, and some say that their DNA
                                                is actually closer to Heathen than human. Regardless of their biological 
                                                makeup, if you approach someone on the street of any settlement and bring up 
                                                the Infidels, you will be met with a look of disgust and the question 'you're 
                                                not one of them, are you?'. Seen as sub-human, other empires engage in combat 
                                                on sight with the Infidels, no matter the disguises they apply.""", 38)
                            pyxel.text(25, 140, "+ Not attacked by heathens", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Always attacked by AI players", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                        case 13:
                            self.draw_paragraph(25, 40, """Long have The Nocturne worshipped the holy moons of this world, and
                                                through repeated attempts to modify their circadian rhythm, the strongest among 
                                                them have developed genetic abilities. These abilities go further than simply 
                                                making them nocturnal, no, they see farther and become stronger during the 
                                                nighttime, and have perfected the art of predicting the sundown. As all things 
                                                are, however, there is a trade-off. When the sun is out, those of The Nocturne 
                                                are weakened, and largely huddle together waiting for their precious darkness 
                                                to return.""", 38)
                            pyxel.text(25, 140, "+ Thrive during the night", pyxel.COLOR_GREEN)
                            pyxel.text(25, 150, "- Units weakened during the day", pyxel.COLOR_RED)
                            pyxel.text(25, 170, "ELIMINATION", pyxel.COLOR_RED)
                case WikiOption.CLIMATE:
                    pyxel.load("resources/sprites.pyxres")
                    pyxel.rectb(20, 10, 160, 164, pyxel.COLOR_WHITE)
                    pyxel.rect(21, 11, 158, 162, pyxel.COLOR_BLACK)
                    pyxel.text(86, 15, "Climate", pyxel.COLOR_WHITE)
                    pyxel.text(56, 162, "Press SPACE to go back", pyxel.COLOR_WHITE)
                    if self.showing_night:
                        pyxel.blt(96, 25, 0, 8, 84, 8, 8)
                        pyxel.text(60, 35, "The Everlasting Night", pyxel.COLOR_DARK_BLUE)
                        self.draw_paragraph(25, 45, """It's part of the life in this world. It's the feeling running down
                                            your spine when you're walking the streets alone with only a torch to guide 
                                            you. It's the devastation when this month's cultivation is smaller than the 
                                            last. It's the agony of looking out on a field of crops that won't grow. It's 
                                            the fear of cursed heathens that could be lurking around every corner, ready to 
                                            pounce. It's life during the nighttime, and you pray to the passions that the 
                                            dawn soon comes.""", 38)
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
                        self.draw_paragraph(25, 45, """Each of those on this land can testify to the toll it takes on you.
                                            From the heat of the sun when toiling in the fields, to the icy chill of the 
                                            wind atop a mountain, it changes a man. But the climb is always worth the 
                                            reward, and you truly feel one with the land as you gaze outward from the peak 
                                            and fully absorb the graciousness of this world. This is home.""", 38)
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
                case WikiOption.IMPROVEMENTS:
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
                case _:
                    pyxel.rectb(60, 45, 80, 110, pyxel.COLOR_WHITE)
                    pyxel.rect(61, 46, 78, 108, pyxel.COLOR_BLACK)
                    pyxel.text(92, 50, "Wiki", pyxel.COLOR_WHITE)
                    pyxel.text(82, 65, "Victories",
                               pyxel.COLOR_RED if self.wiki_option is WikiOption.VICTORIES else pyxel.COLOR_WHITE)
                    pyxel.text(85, 75, "Factions",
                               pyxel.COLOR_RED if self.wiki_option is WikiOption.FACTIONS else pyxel.COLOR_WHITE)
                    pyxel.text(86, 85, "Climate",
                               pyxel.COLOR_RED if self.wiki_option is WikiOption.CLIMATE else pyxel.COLOR_WHITE)
                    pyxel.text(82, 95, "Blessings",
                               pyxel.COLOR_RED if self.wiki_option is WikiOption.BLESSINGS else pyxel.COLOR_WHITE)
                    pyxel.text(78, 105, "Improvements",
                               pyxel.COLOR_RED if self.wiki_option is WikiOption.IMPROVEMENTS else pyxel.COLOR_WHITE)
                    pyxel.text(84, 115, "Projects",
                               pyxel.COLOR_RED if self.wiki_option is WikiOption.PROJECTS else pyxel.COLOR_WHITE)
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
                match self.setup_option:
                    case SetupOption.PLAYER_FACTION:
                        self.setup_option = SetupOption.PLAYER_COUNT
                    case SetupOption.PLAYER_COUNT:
                        self.setup_option = SetupOption.BIOME_CLUSTERING
                    case SetupOption.BIOME_CLUSTERING:
                        self.setup_option = SetupOption.FOG_OF_WAR
                    case SetupOption.FOG_OF_WAR:
                        self.setup_option = SetupOption.CLIMATIC_EFFECTS
                    case SetupOption.CLIMATIC_EFFECTS:
                        self.setup_option = SetupOption.START_GAME
                    case SetupOption.START_GAME:
                        self.setup_option = SetupOption.PLAYER_FACTION
            elif self.loading_game:
                if self.save_idx == self.load_game_boundaries[1] and self.save_idx < len(self.saves) - 1:
                    self.load_game_boundaries = self.load_game_boundaries[0] + 1, self.load_game_boundaries[1] + 1
                if 0 <= self.save_idx < len(self.saves) - 1:
                    self.save_idx += 1
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
                        if self.unit_boundaries[1] < len(UNIT_PLANS) - 1:
                            self.unit_boundaries = self.unit_boundaries[0] + 1, self.unit_boundaries[1] + 1
                    case _:
                        match self.wiki_option:
                            case WikiOption.VICTORIES:
                                self.wiki_option = WikiOption.FACTIONS
                            case WikiOption.FACTIONS:
                                self.wiki_option = WikiOption.CLIMATE
                            case WikiOption.CLIMATE:
                                self.wiki_option = WikiOption.BLESSINGS
                            case WikiOption.BLESSINGS:
                                self.wiki_option = WikiOption.IMPROVEMENTS
                            case WikiOption.IMPROVEMENTS:
                                self.wiki_option = WikiOption.PROJECTS
                            case WikiOption.PROJECTS:
                                self.wiki_option = WikiOption.UNITS
                            case WikiOption.UNITS:
                                self.wiki_option = None
                            case None:
                                self.wiki_option = WikiOption.VICTORIES
            else:
                match self.menu_option:
                    case MenuOption.NEW_GAME:
                        self.menu_option = MenuOption.LOAD_GAME
                    case MenuOption.LOAD_GAME:
                        self.menu_option = MenuOption.WIKI
                    case MenuOption.WIKI:
                        self.menu_option = MenuOption.EXIT
                    case MenuOption.EXIT:
                        self.menu_option = MenuOption.NEW_GAME
        if up:
            # Ensure that players cannot navigate the root menu while the faction details overlay is being shown.
            if self.in_game_setup and not self.showing_faction_details:
                match self.setup_option:
                    case SetupOption.PLAYER_COUNT:
                        self.setup_option = SetupOption.PLAYER_FACTION
                    case SetupOption.BIOME_CLUSTERING:
                        self.setup_option = SetupOption.PLAYER_COUNT
                    case SetupOption.FOG_OF_WAR:
                        self.setup_option = SetupOption.BIOME_CLUSTERING
                    case SetupOption.CLIMATIC_EFFECTS:
                        self.setup_option = SetupOption.FOG_OF_WAR
                    case SetupOption.START_GAME:
                        self.setup_option = SetupOption.CLIMATIC_EFFECTS
                    case SetupOption.PLAYER_FACTION:
                        self.setup_option = SetupOption.START_GAME
            elif self.loading_game:
                if self.save_idx > 0 and self.save_idx == self.load_game_boundaries[0]:
                    self.load_game_boundaries = self.load_game_boundaries[0] - 1, self.load_game_boundaries[1] - 1
                if self.save_idx > 0:
                    self.save_idx -= 1
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
                        match self.wiki_option:
                            case WikiOption.FACTIONS:
                                self.wiki_option = WikiOption.VICTORIES
                            case WikiOption.CLIMATE:
                                self.wiki_option = WikiOption.FACTIONS
                            case WikiOption.BLESSINGS:
                                self.wiki_option = WikiOption.CLIMATE
                            case WikiOption.IMPROVEMENTS:
                                self.wiki_option = WikiOption.BLESSINGS
                            case WikiOption.PROJECTS:
                                self.wiki_option = WikiOption.IMPROVEMENTS
                            case WikiOption.UNITS:
                                self.wiki_option = WikiOption.PROJECTS
                            case WikiOption.VICTORIES:
                                self.wiki_option = None
                            case _:
                                self.wiki_option = WikiOption.UNITS
            else:
                match self.menu_option:
                    case MenuOption.LOAD_GAME:
                        self.menu_option = MenuOption.NEW_GAME
                    case MenuOption.WIKI:
                        self.menu_option = MenuOption.LOAD_GAME
                    case MenuOption.EXIT:
                        self.menu_option = MenuOption.WIKI
                    case MenuOption.NEW_GAME:
                        self.menu_option = MenuOption.EXIT
        if left:
            if self.in_game_setup:
                match self.setup_option:
                    case SetupOption.PLAYER_FACTION:
                        self.faction_idx = clamp(self.faction_idx - 1, 0, len(self.faction_colours) - 1)
                    case SetupOption.PLAYER_COUNT:
                        self.player_count = max(2, self.player_count - 1)
                    case SetupOption.BIOME_CLUSTERING:
                        self.biome_clustering_enabled = False
                    case SetupOption.FOG_OF_WAR:
                        self.fog_of_war_enabled = False
                    case SetupOption.CLIMATIC_EFFECTS:
                        self.climatic_effects_enabled = False
            elif self.in_wiki and self.wiki_showing is WikiOption.VICTORIES:
                match self.victory_type:
                    case VictoryType.JUBILATION:
                        self.victory_type = VictoryType.ELIMINATION
                    case VictoryType.GLUTTONY:
                        self.victory_type = VictoryType.JUBILATION
                    case VictoryType.AFFLUENCE:
                        self.victory_type = VictoryType.GLUTTONY
                    case VictoryType.VIGOUR:
                        self.victory_type = VictoryType.AFFLUENCE
                    case VictoryType.SERENDIPITY:
                        self.victory_type = VictoryType.VIGOUR
            elif self.in_wiki and self.wiki_showing is WikiOption.FACTIONS and self.faction_wiki_idx != 0:
                self.faction_wiki_idx -= 1
            elif self.in_wiki and self.wiki_showing is WikiOption.CLIMATE:
                self.showing_night = False
        if right:
            if self.in_game_setup:
                match self.setup_option:
                    case SetupOption.PLAYER_FACTION:
                        self.faction_idx = clamp(self.faction_idx + 1, 0, len(self.faction_colours) - 1)
                    case SetupOption.PLAYER_COUNT:
                        self.player_count = min(14, self.player_count + 1)
                    case SetupOption.BIOME_CLUSTERING:
                        self.biome_clustering_enabled = True
                    case SetupOption.FOG_OF_WAR:
                        self.fog_of_war_enabled = True
                    case SetupOption.CLIMATIC_EFFECTS:
                        self.climatic_effects_enabled = True
            elif self.in_wiki and self.wiki_showing is WikiOption.VICTORIES:
                match self.victory_type:
                    case VictoryType.ELIMINATION:
                        self.victory_type = VictoryType.JUBILATION
                    case VictoryType.JUBILATION:
                        self.victory_type = VictoryType.GLUTTONY
                    case VictoryType.GLUTTONY:
                        self.victory_type = VictoryType.AFFLUENCE
                    case VictoryType.AFFLUENCE:
                        self.victory_type = VictoryType.VIGOUR
                    case VictoryType.VIGOUR:
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

    @staticmethod
    def draw_paragraph(x_start: int, y_start: int, text: str, line_length: int) -> None:
        """
        Render text to the screen while automatically accounting for line breaks.
        :param x_start: x of the text's starting position.
        :param y_start: y of the text's starting position.
        :param text: The full text to draw.
        :param line_length: The maximum character length of each line.
        """
        text_to_draw = ""
        text_y = y_start

        for word in text.split():
            # Iterate through each word and check if there's enough space on the current line to add it. Otherwise,
            # draw what we have so far and go to the next line.
            if len(text_to_draw) + len(word) <= line_length:
                text_to_draw += word
            else:
                pyxel.text(x_start, text_y, text_to_draw, pyxel.COLOR_WHITE)
                text_to_draw = word
                # Increment the y position of the text at the end of each line.
                text_y += 6

            # Add a space after each word (so that the reader doesn't run out of breath).
            text_to_draw += " "

        # Draw any remaining text to the final line.
        pyxel.text(x_start, text_y, text_to_draw, pyxel.COLOR_WHITE)

    def get_next_menu_option(self, options_enum: Enum, current_selection: typing.Type[Enum]) -> None:
        """
        PYDOC IS OVERRATED
        KITFOX SUCK EGG
        """
        if current_selection not in options_enum:
            return

        current_option_idx = list(options_enum).index(current_selection)
        next_option_idx = (current_option_idx + 1) % len(options_enum)
        next_option = list(options_enum)[next_option_idx]

        if options_enum is SetupOption:
            self.setup_option = next_option
        elif options_enum is WikiOption:
            self.wiki_option = next_option
        elif options_enum is MenuOption:
            self.menu_option = next_option
