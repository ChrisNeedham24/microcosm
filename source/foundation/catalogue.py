import random
from copy import deepcopy
from typing import Dict, List, Optional

import pyxel

from source.foundation import achievements
from source.foundation.models import FactionDetail, Player, Improvement, ImprovementType, Effect, Blessing, \
    Settlement, UnitPlan, Unit, Biome, Heathen, Faction, Project, ProjectType, VictoryType, DeployerUnitPlan, \
    Achievement, HarvestStatus, EconomicStatus, ResourceCollection
from source.util.calculator import player_has_resources_for_improvement, scale_unit_plan_attributes, \
    scale_blessing_attributes


# The list of multiplayer lobby names.
LOBBY_NAMES = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi",
    "Omicron", "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega"
]


# The list of player names for multiplayer games.
PLAYER_NAMES = [
    "Ace", "Buster", "Chief", "Dingo", "E.T.", "Fang", "Ghost", "Hawk", "Iris", "Judge", "Kanga", "Laser", "Meteor",
    "Neutron", "Ozone", "Pyro", "Quokka", "Reaper", "Snake", "Turbo", "Ultra", "Viper", "Wizard", "Xylo", "Yabby",
    "Zulu"
]


# The list of settlement names, for each biome.
SETL_NAMES = {
    Biome.DESERT: [
        "Enfu", "Saknoten", "Despemar", "Khasolzum", "Nekpesir", "Akhtamar", "Absai", "Khanomhat", "Sharrisir", "Kisri",
        "Kervapet", "Khefupet", "Djesy", "Quri", "Sakmusa", "Khasru", "Farvaru", "Kiteru", "Setmeris", "Qulno",
        "Kirinu", "Farpesiris", "Neripet", "Shafu", "Kiskhekhen", "Ennotjer", "Desnounis", "Avseta", "Ebsai", "Ektu"
    ],
    Biome.FOREST: [
        "Kalshara", "Mora Caelora", "Yam Ennore", "Uyla Themar", "Nelrenqua", "Caranlian", "Osaenamel", "Elhamel",
        "Allenrion", "Nilathaes", "Osna Thalas", "Mytebel", "Ifoqua", "Amsanas", "Effa Dorei", "Aff Tirion",
        "Wamalenor", "Thaihona", "Illmelion", "Naallume", "Ayh Taesi", "Naalbel", "Ohelean", "Esaqua", "Ulananore",
        "Ei Allanar", "Eririon", "Wan Thalor", "Maldell", "Mile Thalore"
    ],
    Biome.SEA: [
        "Natanas", "Tempetia", "Leviarey", "Atlalis", "Neptulean", "Oceacada", "Naurus", "Hylore", "Expathis",
        "Liquasa", "Navanoch", "Flulean", "Calaril", "Njomon", "Jutumari", "Atlalora", "Abystin", "Vapolina",
        "Watamari", "Pacirius", "Calaren", "Aegmon", "Puratia", "Nephren", "Glalis", "Tritemari", "Sireri", "Ocearis",
        "Navasa", "Merrius"
    ],
    Biome.MOUNTAIN: [
        "Nem Tarhir", "Dharnturm", "Hun Thurum", "Vil Tarum", "Kha Kuldihr", "Hildarim", "Gog Daruhl", "Vogguruhm",
        "Dhighthiod", "Malwihr", "Mil Boldar", "Hunfuhn", "Dunulur", "Kagria", "Meltorum", "Gol Darohm", "Beghrihm",
        "Heltorhm", "Kor Olihm", "Nilgron", "Garndor", "Khon Daruhm", "Bhalladuhr", "Kham Tarum", "Dugboldor",
        "Gor Faldir", "Vildarth", "Keraldur", "Vog Durahl", "Gumdim"
    ]
}


class Namer:
    """
    The class responsible for giving settlements names. Needs to be a class for cases in which the player quits their
    current game and loads another (or the same) immediately, without exiting the application. This is a problem due to
    the fact that, in that case, SETL_NAMES will not be reset, as it is on application start.
    """

    def __init__(self):
        self.names = deepcopy(SETL_NAMES)

    def get_settlement_name(self, biome: Biome) -> str:
        """
        Returns a settlement name for the given biome.
        :param biome: The biome of the settlement-to-be.
        :return: A settlement name.
        """
        name = random.choice(self.names[biome])
        # Note that we remove the settlement name to avoid duplicates.
        self.names[biome].remove(name)
        return name

    def remove_settlement_name(self, name: str, biome: Biome):
        """
        Removes a settlement name from the list. Used in loaded game and multiplayer cases.
        :param name: The settlement name to remove.
        :param biome: The biome of the settlement. Used to locate the name in the dictionary.
        """
        self.names[biome].remove(name)

    def reset(self):
        """
        Resets the available names.
        """
        self.names = deepcopy(SETL_NAMES)


# The list of playable factions and their details.
FACTION_DETAILS = [
    FactionDetail(Faction.AGRICULTURISTS, """Using techniques passed down through the generations, the Agriculturists
                  are able to sustain their populace through famine and indeed through feast. Some of this land's
                  greatest delicacies are grown by these humble people, who insist that anyone could grow what they do,
                  winking at one another as they say it. Without the spectre of hunger on the horizon, the
                  Agriculturists lead the slow life, indulging in pleasures at their own pace.""",
                  "+ Immune to poor harvest", "- Generates 75% of usual zeal", VictoryType.GLUTTONY),
    FactionDetail(Faction.CAPITALISTS, """The sky-high towers and luxurious dwellings found throughout their cities
                  represent the Capitalists to the fullest. They value the clink of coins over anything else, and it
                  has served them well so far. However, if you take a look around the corner, things are clearly not
                  as the seem. And as the slums fill up, there better be enough food to go around, lest something...
                  dangerous happens.""", "+ Immune to recession", "- Double low harvest penalty",
                  VictoryType.AFFLUENCE),
    FactionDetail(Faction.SCRUTINEERS, """Due to a genetic trait, the Scrutineers have always had good eyesight and
                  they use it to full effect. Nothing gets past them, from the temples of the outlands to the streets
                  of their cities. But, as it goes, the devil is in the details, as the local clergy certainly aren't
                  exempt from the all-seeing eye, with blessings being stymied as much as is humanly possible.""",
                  "+ Investigations always succeed", "- Generates 75% of usual fortune", VictoryType.ELIMINATION),
    FactionDetail(Faction.GODLESS, """Many eons ago, a subsection of the population of these lands began to question
                  the effectiveness of their blessings after years of squalor and oppression. They shook free their
                  bonds and formed their own community based around the one thing that proved valuable to all people:
                  currency. However, despite shunning blessings at every opportunity, The Godless, as they became
                  known, are wont to dabble in blessings in moments of weakness, and what's left of their clergy makes
                  sure to sink the boot in.""", "+ Generates 125% of usual wealth", "- Blessings cost 125% of usual",
                  VictoryType.AFFLUENCE),
    FactionDetail(Faction.RAVENOUS, """Originating from a particular fertile part of these lands, The Ravenous have
                  enjoyed bountiful harvests for centuries. No matter the skill of the farmer, or the quality of the
                  seeds, a cultivation of significant size is always created after some months. But with such
                  consistency, comes complacency. Those that have resided in settlements occupied by The Ravenous,
                  over time, grow greedy. As populations increase, and more food is available, the existing residents
                  seek to keep it all for themselves, as newcomers are given the unbearable choice of starving or
                  leaving.""", "+ Generates 125% of usual harvest", "- Settlements capped at level 5",
                  VictoryType.JUBILATION),
    FactionDetail(Faction.FUNDAMENTALISTS, """There's nothing quite like the clang of iron striking iron to truly
                  ground a person in their surroundings. This is a fact that the Fundamentalists know well, as every
                  child of a certain age is required to serve as an apprentice in a local forge or refinery. With such
                  resources at their disposal, work is done quickly. And yet, suggestions that constructions should be
                  made quicker, and in some cases instantaneous, through the use of empire funds are met with utter
                  disgust by the people. For the Fundamentalists, everything must be done the right way.""",
                  "+ Generates 125% of usual zeal", "- Construction buyouts disabled", VictoryType.VIGOUR),
    FactionDetail(Faction.ORTHODOX, """Glory to the ancient ones, and glory to the passionate. The Orthodox look to
                  those that came before them for guidance, and they are justly rewarded that, with enlightenment and
                  discoveries occurring frequently. As the passionate tend to do, however, the clatter of coin in the
                  palm is met with a stern decline. Content they are with their existence, The Orthodox rely on seeing
                  what others cannot.""", "+ Generates 125% of usual fortune", "- Generates 75% of usual wealth",
                  VictoryType.SERENDIPITY),
    FactionDetail(Faction.CONCENTRATED, """For the unfamiliar, visiting the settlement of The Concentrated can be
                  overwhelming. The sheer mass of people everywhere one looks along with the cloud-breaching towers
                  can make one feel like they have been transported to some distant future. It is this intimidatory
                  factor, in combination with the colossal ramparts surrounding the megapolis that have kept The
                  Concentrated safe and sound for many years.""", "+ Stronger settlements that grow",
                  "- Limited to a single settlement", VictoryType.ELIMINATION),
    FactionDetail(Faction.FRONTIERSMEN, """Blink and you'll miss it; that's the story of the settlements of the
                  Frontier. The Frontiersmen have a near obsession with the thrill of the frontier and making
                  something of inhospitable terrain, in situations where others could not. Residing in a new
                  settlement is considered to be the pinnacle of Frontier achievement, but the shine wears off
                  quickly. After some time, the people become restless and seek to expand further. And thus the cycle
                  repeats.""", "+ Base satisfaction is 75", "- Settlers only at level 5", VictoryType.JUBILATION),
    FactionDetail(Faction.IMPERIALS, """The concept of raw power and strength has long been a core tenet of the
                  self-dubbed Empire, with compulsory military service a cultural feature. Drilled into the populace
                  for such an extensive period, the armed forces of the Imperials are a fearsome sight to behold.
                  Those opposite gaze at one another, gauging whether it might be preferred to retreat. But this
                  superiority leads to carelessness, as the Imperials assume that no one would dare attack one of
                  their settlements for fear of retribution, and thus leave them relatively undefended.""",
                  "+ Units have 50% more power", "- Settlements have 50% strength", VictoryType.ELIMINATION),
    FactionDetail(Faction.PERSISTENT, """Atop a mountain in the north of these lands, there is a people of a certain
                  philosophical nature. Instilled in all from birth to death is the ideal of determination, and
                  achieving one's goals no matter the cost, in time or in life. Aptly dubbed by others as The
                  Persistent, these militaristic people often elect to wear others down through sieges and defensive
                  manoeuvres. Of course, such strategies become ineffective against the well-prepared, but this does
                  not bother The Persistent; they simply continue on.""", "+ Units have 50% more health",
                  "- Units have 75% of usual power", VictoryType.ELIMINATION),
    FactionDetail(Faction.EXPLORERS, """Originating from an isolated part of the globe, the Explorers were first
                  introduced to the wider world when a lost trader stumbled across their crude and underdeveloped
                  settlement. Guiding the leaders of the settlement out to the nearest other settlement, and returning
                  to explain to the masses was significant. Once the Explorers got a taste, they have not been able to
                  stop. They look higher, run farther and dig deeper, at the expense of their energy levels.
                  Unfortunately for the Explorers, the required rest during the journey makes them easy targets for
                  Heathens.""", "+ Units have 50% more stamina", "- Units have 75% of usual health",
                  VictoryType.GLUTTONY),
    FactionDetail(Faction.INFIDELS, """Some say they were raised by Heathens, and some say that their DNA is actually
                  closer to Heathen than human. Regardless of their biological makeup, if you approach someone on the
                  street of any settlement and bring up the Infidels, you will be met with a look of disgust and the
                  question 'you're not one of them, are you?'. Seen as sub-human, other empires engage in combat on
                  sight with the Infidels, no matter the disguises they apply.""", "+ Special affinity with heathens",
                  "- Always attacked by AI players", VictoryType.ELIMINATION),
    FactionDetail(Faction.NOCTURNE, """Long have The Nocturne worshipped the holy moons of this world, and through
                  repeated attempts to modify their circadian rhythm, the strongest among them have developed genetic
                  abilities. These abilities go further than simply making them nocturnal, no, they see farther and
                  become stronger during the nighttime, and have perfected the art of predicting the sundown. As all
                  things are, however, there is a trade-off. When the sun is out, those of The Nocturne are weakened,
                  and largely huddle together waiting for their precious darkness to return.""",
                  "+ Thrive during the night", "- Units weakened during the day", VictoryType.ELIMINATION)
]

# The list of blessings that can be undergone.
BLESSINGS = {
    "beg_spl": Blessing("Beginner Spells", "Everyone has to start somewhere, right?", 100.0),
    "div_arc": Blessing("Divine Architecture", "As the holy ones intended.", 500.0),
    "inh_luc": Blessing("Inherent Luck", "Better lucky than good.", 2500.0),
    "rud_exp": Blessing("Rudimentary Explosives", "Nothing can go wrong with this.", 100.0),
    "rob_exp": Blessing("Robotic Experiments", "The artificial eye only stares back.", 500.0),
    "res_rep": Blessing("Resource Replenishment", "Never run out of what you need.", 2500.0),
    "adv_trd": Blessing("Advanced Trading", "You could base a society on this.", 100.0),
    "sl_vau": Blessing("Self-locking Vaults", "Nothing's getting in or out.", 500.0),
    "eco_mov": Blessing("Economic Movements", "Know the inevitable before it occurs.", 2500.0),
    "prf_nec": Blessing("Profitable Necessities", "The irresistible appeal of a quick buck.", 100.0),
    "art_pht": Blessing("Hollow Photosynthesis", "Moonlight is just as good.", 500.0),
    "met_alt": Blessing("Metabolic Alterations", "I feel full already!", 2500.0),
    "tor_tec": Blessing("Torture Techniques", "There's got to be something better.", 100.0),
    "apr_ref": Blessing("Aperture Refinement", "Picture perfect.", 500.0),
    "psy_sup": Blessing("Psychic Supervision", "I won't do what you tell me.", 2500.0),
    "grt_goo": Blessing("The Greater Good", "The benefit of helping others.", 100.0),
    "ref_prc": Blessing("Reformist Principles", "Maybe another system could be better.", 500.0),
    "brd_fan": Blessing("Broad Fanaticism", "Maybe I can do no wrong.", 2500.0),
    "anc_his": Blessing("Ancient History", "Guide us to the light.", 25000.0),
    "ard_one": Blessing("Piece of Strength", "The mighty will prevail.", 15000.0),
    "ard_two": Blessing("Piece of Passion", "Only the passionate will remain.", 15000.0),
    "ard_three": Blessing("Piece of Divinity", "Everything is revealed.", 15000.0)
}

# The list of improvements that can be built.
IMPROVEMENTS = [
    Improvement(ImprovementType.MAGICAL, 30.0, "Melting Pot", "A starting pot to conduct concoctions.",
                Effect(fortune=5.0, satisfaction=2.0), None, req_resources=ResourceCollection(magma=5)),
    Improvement(ImprovementType.MAGICAL, 180.0, "Haunted Forest", "The branches shake, yet there's no wind.",
                Effect(harvest=1.0, fortune=8.0, satisfaction=-5.0), BLESSINGS["beg_spl"]),
    Improvement(ImprovementType.MAGICAL, 180.0, "Occult Bartering", "Dealing with both dead and alive.",
                Effect(wealth=1.0, fortune=8.0, satisfaction=-1.0), BLESSINGS["adv_trd"]),
    Improvement(ImprovementType.MAGICAL, 1080.0, "Ancient Shrine", "Some say it emanates an invigorating aura.",
                Effect(wealth=2.0, zeal=-2.0, fortune=20.0, satisfaction=10.0), BLESSINGS["div_arc"],
                req_resources=ResourceCollection(timber=20)),
    Improvement(ImprovementType.MAGICAL, 1080.0, "Dimensional imagery", "See into another world.",
                Effect(fortune=25.0, satisfaction=2.0), BLESSINGS["apr_ref"]),
    Improvement(ImprovementType.MAGICAL, 1080.0, "Fortune Distillery", "Straight from the mouth.",
                Effect(zeal=-2.0, fortune=25.0, strength=-10.0, satisfaction=5.0), BLESSINGS["inh_luc"],
                req_resources=ResourceCollection(ore=20)),
    Improvement(ImprovementType.INDUSTRIAL, 30.0, "Local Forge", "Just a mum-and-dad-type operation.",
                Effect(wealth=2.0, zeal=5.0), None, req_resources=ResourceCollection(ore=5)),
    Improvement(ImprovementType.INDUSTRIAL, 180.0, "Weapons Factory", "Made to kill outsiders. Mostly.",
                Effect(wealth=2.0, zeal=5.0, strength=25.0, satisfaction=-2.0), BLESSINGS["rud_exp"],
                req_resources=ResourceCollection(ore=10)),
    Improvement(ImprovementType.INDUSTRIAL, 180.0, "Enslaved Workforce", "Gets the job done.",
                Effect(wealth=2.0, harvest=-1.0, zeal=6.0, fortune=-2.0, satisfaction=-5.0), BLESSINGS["tor_tec"]),
    Improvement(ImprovementType.INDUSTRIAL, 1080.0, "Automated Production", "In and out, no fuss.",
                Effect(wealth=3.0, zeal=30.0, satisfaction=-10.0), BLESSINGS["rob_exp"]),
    Improvement(ImprovementType.INDUSTRIAL, 1080.0, "Lab-grown Workers", "Human or not, they work the same.",
                Effect(wealth=3.0, harvest=-2.0, zeal=30.0, fortune=-5.0, strength=2.0, satisfaction=-10.0),
                BLESSINGS["art_pht"]),
    Improvement(ImprovementType.INDUSTRIAL, 1080.0, "Endless Mine", "Hang on, didn't I just remove that?",
                Effect(wealth=5.0, zeal=25.0, fortune=-2.0), BLESSINGS["res_rep"],
                req_resources=ResourceCollection(timber=20)),
    Improvement(ImprovementType.ECONOMICAL, 30.0, "City Market", "Pockets empty, but friend or foe?",
                Effect(wealth=5.0, harvest=2.0, zeal=2.0, fortune=-1.0, satisfaction=2.0), None),
    Improvement(ImprovementType.ECONOMICAL, 180.0, "State Bank", "You're not the first to try your luck.",
                Effect(wealth=8.0, fortune=-2.0, strength=5.0, satisfaction=2.0), BLESSINGS["adv_trd"]),
    Improvement(ImprovementType.ECONOMICAL, 180.0, "Harvest Levy", "Definitely only for times of need.",
                Effect(wealth=8.0, harvest=2.0, zeal=-1.0, fortune=-1.0, satisfaction=-2.0), BLESSINGS["prf_nec"]),
    Improvement(ImprovementType.ECONOMICAL, 1080.0, "National Mint", "Gold as far as the eye can see.",
                Effect(wealth=30.0, fortune=-5.0, strength=10.0, satisfaction=5.0), BLESSINGS["sl_vau"],
                req_resources=ResourceCollection(magma=20)),
    Improvement(ImprovementType.ECONOMICAL, 1080.0, "Federal Museum", "Cataloguing all that was left for us.",
                Effect(wealth=10.0, fortune=10.0, satisfaction=4.0), BLESSINGS["div_arc"]),
    Improvement(ImprovementType.ECONOMICAL, 1080.0, "Planned Economy", "Under the watchful eye.",
                Effect(wealth=20.0, harvest=5.0, zeal=5.0, satisfaction=-2.0), BLESSINGS["eco_mov"]),
    Improvement(ImprovementType.BOUNTIFUL, 30.0, "Collectivised Farms", "Well, the shelves will be stocked.",
                Effect(wealth=2.0, harvest=10.0, zeal=-2.0, satisfaction=-2.0), None),
    Improvement(ImprovementType.BOUNTIFUL, 180.0, "Supermarket Chains", "On every street corner.",
                Effect(harvest=8.0, satisfaction=2.0), BLESSINGS["prf_nec"],
                req_resources=ResourceCollection(timber=10)),
    Improvement(ImprovementType.BOUNTIFUL, 180.0, "Distributed Rations", "Everyone gets their fair share.",
                Effect(harvest=8.0, zeal=-1.0, fortune=1.0, satisfaction=-1.0), BLESSINGS["grt_goo"]),
    Improvement(ImprovementType.BOUNTIFUL, 1080.0, "Sunken Greenhouses", "The glass is just for show.",
                Effect(harvest=25.0, zeal=-5.0, fortune=-2.0), BLESSINGS["art_pht"],
                req_resources=ResourceCollection(magma=20)),
    Improvement(ImprovementType.BOUNTIFUL, 1080.0, "Impenetrable Stores", "Unprecedented control over stock.",
                Effect(wealth=-1.0, harvest=25.0, strength=5.0, satisfaction=-5.0), BLESSINGS["sl_vau"],
                req_resources=ResourceCollection(ore=20)),
    Improvement(ImprovementType.BOUNTIFUL, 1080.0, "Genetic Clinics", "Change me for the better.",
                Effect(harvest=15.0, zeal=15.0), BLESSINGS["met_alt"]),
    Improvement(ImprovementType.INTIMIDATORY, 30.0, "Insurmountable Walls", "Quite the view from up here.",
                Effect(strength=25.0, satisfaction=2.0), None),
    Improvement(ImprovementType.INTIMIDATORY, 180.0, "Intelligence Academy", "What's learnt in here, stays in here.",
                Effect(strength=30.0, satisfaction=-2.0), BLESSINGS["tor_tec"]),
    Improvement(ImprovementType.INTIMIDATORY, 180.0, "Minefields", "Cross if you dare.",
                Effect(harvest=-1.0, strength=30.0, satisfaction=-1.0), BLESSINGS["rud_exp"]),
    Improvement(ImprovementType.INTIMIDATORY, 1080.0, "CCTV Cameras", "Big Brother's always watching.",
                Effect(zeal=5.0, fortune=-2.0, strength=50.0, satisfaction=-2.0), BLESSINGS["apr_ref"]),
    Improvement(ImprovementType.INTIMIDATORY, 1080.0, "Cult of Personality", "The supreme leader can do no wrong.",
                Effect(wealth=2.0, harvest=2.0, zeal=2.0, fortune=2.0, strength=50.0, satisfaction=5.0),
                BLESSINGS["ref_prc"]),
    Improvement(ImprovementType.INTIMIDATORY, 1080.0, "Omniscient Police", "Not even jaywalking is allowed.",
                Effect(wealth=-2.0, zeal=-2.0, fortune=-5.0, strength=100.0, satisfaction=-10.0), BLESSINGS["psy_sup"]),
    Improvement(ImprovementType.PANDERING, 30.0, "Aqueduct", "Water from there to here.",
                Effect(harvest=2.0, fortune=-1.0, satisfaction=5.0), None),
    Improvement(ImprovementType.PANDERING, 180.0, "Soup Kitchen", "No one's going hungry here.",
                Effect(wealth=-1.0, zeal=2.0, fortune=2.0, satisfaction=6.0), BLESSINGS["grt_goo"],
                req_resources=ResourceCollection(magma=10)),
    Improvement(ImprovementType.PANDERING, 180.0, "Puppet Shows", "Putting those spells to use.",
                Effect(wealth=1.0, zeal=-1.0, fortune=1.0, satisfaction=6.0), BLESSINGS["beg_spl"],
                req_resources=ResourceCollection(timber=10)),
    Improvement(ImprovementType.PANDERING, 1080.0, "Common Chief Yield", "Utopian in more ways than one.",
                Effect(wealth=-5.0, harvest=2.0, zeal=2.0, fortune=2.0, strength=2.0, satisfaction=10.0),
                BLESSINGS["ref_prc"]),
    Improvement(ImprovementType.PANDERING, 1080.0, "Infinite Disport", "Where the robots are the stars.",
                Effect(zeal=2.0, fortune=-1.0, satisfaction=12.0), BLESSINGS["rob_exp"]),
    Improvement(ImprovementType.PANDERING, 1080.0, "Free Expression", "Say what we know you'll say.",
                Effect(satisfaction=15.0), BLESSINGS["brd_fan"]),
    Improvement(ImprovementType.INDUSTRIAL, 20000.0, "Holy Sanctum", "To converse with the holy ones.",
                Effect(), BLESSINGS["anc_his"])
]

# The list of projects that a settlement can be continuously working on.
PROJECTS = [
    Project(ProjectType.BOUNTIFUL, "Call of the Fields", "From hand to mouth."),
    Project(ProjectType.ECONOMICAL, "Inflation by Design", "More is more, right?"),
    Project(ProjectType.MAGICAL, "The Holy Epiphany", "Awaken the soul.")
]

# The list of unit plans that units can be recruited according to.
UNIT_PLANS = [
    UnitPlan(100.0, 100.0, 3, "Warrior", None, 25.0),
    UnitPlan(125.0, 50.0, 5, "Bowman", None, 25.0),
    UnitPlan(75.0, 125.0, 2, "Shielder", None, 25.0),
    UnitPlan(25.0, 25.0, 6, "Settler", None, 50.0, can_settle=True),
    UnitPlan(150.0, 75.0, 4, "Mage", BLESSINGS["beg_spl"], 50.0),
    UnitPlan(50.0, 50.0, 10, "Locksmith", BLESSINGS["sl_vau"], 75.0),
    UnitPlan(20.0, 50.0, 6, "Shaman", BLESSINGS["beg_spl"], 75.0, heals=True),
    UnitPlan(200.0, 40.0, 2, "Grenadier", BLESSINGS["rud_exp"], 100.0),
    UnitPlan(50.0, 200.0, 2, "Flagellant", BLESSINGS["tor_tec"], 200.0),
    DeployerUnitPlan(0.0, 80.0, 8, "Trojan Horse", BLESSINGS["sl_vau"], 300.0),
    UnitPlan(150.0, 125.0, 3, "Sniper", BLESSINGS["apr_ref"], 400.0),
    UnitPlan(50.0, 60.0, 8, "MediBot", BLESSINGS["rob_exp"], 500.0, heals=True),
    UnitPlan(150.0, 150.0, 5, "Drone", BLESSINGS["rob_exp"], 800.0),
    UnitPlan(100.0, 75.0, 10, "Narcotician", BLESSINGS["brd_fan"], 1000.0, heals=True),
    DeployerUnitPlan(0.0, 125.0, 12, "Golden Van", BLESSINGS["inh_luc"], 1100.0, max_capacity=5),
    UnitPlan(200.0, 200.0, 4, "Herculeum", BLESSINGS["met_alt"], 1200.0),
    UnitPlan(300.0, 50.0, 3, "Haruspex", BLESSINGS["psy_sup"], 1200.0),
    UnitPlan(40.0, 400.0, 2, "Fanatic", BLESSINGS["brd_fan"], 1200.0)
]

# A map of factions to their respective colours.
FACTION_COLOURS: Dict[Faction, int] = {
    Faction.AGRICULTURISTS: pyxel.COLOR_GREEN,
    Faction.CAPITALISTS: pyxel.COLOR_YELLOW,
    Faction.SCRUTINEERS: pyxel.COLOR_LIGHT_BLUE,
    Faction.GODLESS: pyxel.COLOR_CYAN,
    Faction.RAVENOUS: pyxel.COLOR_LIME,
    Faction.FUNDAMENTALISTS: pyxel.COLOR_ORANGE,
    Faction.ORTHODOX: pyxel.COLOR_PURPLE,
    Faction.CONCENTRATED: pyxel.COLOR_GRAY,
    Faction.FRONTIERSMEN: pyxel.COLOR_PEACH,
    Faction.IMPERIALS: pyxel.COLOR_DARK_BLUE,
    Faction.PERSISTENT: pyxel.COLOR_RED,
    Faction.EXPLORERS: pyxel.COLOR_PINK,
    Faction.INFIDELS: pyxel.COLOR_BROWN,
    Faction.NOCTURNE: pyxel.COLOR_NAVY
}

# A map of victory types to their respective colours.
VICTORY_TYPE_COLOURS: Dict[VictoryType, int] = {
    VictoryType.ELIMINATION: pyxel.COLOR_RED,
    VictoryType.JUBILATION: pyxel.COLOR_GREEN,
    VictoryType.GLUTTONY: pyxel.COLOR_GREEN,
    VictoryType.AFFLUENCE: pyxel.COLOR_YELLOW,
    VictoryType.VIGOUR: pyxel.COLOR_ORANGE,
    VictoryType.SERENDIPITY: pyxel.COLOR_PURPLE
}

# The list of achievements that the player can obtain.
ACHIEVEMENTS: List[Achievement] = [
    Achievement("Chicken Dinner", "Win a game.",
                lambda _, stats: len(stats.victories) > 0),
    Achievement("Fully Improved", "Build every non-victory improvement in one game.",
                lambda gs, _: (sum(len(s.improvements)
                                   for s in gs.players[gs.player_idx].settlements) >= len(IMPROVEMENTS) - 1)),
    Achievement("Harvest Galore", "Have at least 5 settlements with plentiful harvests.",
                lambda gs, _: len([s for s in gs.players[gs.player_idx].settlements
                                   if s.harvest_status == HarvestStatus.PLENTIFUL]) >= 5),
    Achievement("Mansa Musa", "Have at least 5 settlements with boom economies.",
                lambda gs, _: len([s for s in gs.players[gs.player_idx].settlements
                                   if s.economic_status == EconomicStatus.BOOM]) >= 5),
    Achievement("Last One Standing", "Achieve an elimination victory.",
                lambda _, stats: VictoryType.ELIMINATION in stats.victories),
    Achievement("They Love Me!", "Achieve a jubilation victory.",
                lambda _, stats: VictoryType.JUBILATION in stats.victories),
    Achievement("Megalopoleis", "Achieve a gluttony victory.",
                lambda _, stats: VictoryType.GLUTTONY in stats.victories),
    Achievement("Wealth Upon Wealth", "Achieve an affluence victory.",
                lambda _, stats: VictoryType.AFFLUENCE in stats.victories),
    Achievement("Sanctum Sanctorum", "Achieve a vigour victory.",
                lambda _, stats: VictoryType.VIGOUR in stats.victories),
    Achievement("Arduously Blessed", "Achieve a serendipity victory.",
                lambda _, stats: VictoryType.SERENDIPITY in stats.victories),
    Achievement("Grow And Grow", "Win with the Agriculturists.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.AGRICULTURISTS, post_victory=True),
    Achievement("Money Talks", "Win with the Capitalists.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.CAPITALISTS, post_victory=True),
    Achievement("Telescopic", "Win with the Scrutineers.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.SCRUTINEERS, post_victory=True),
    Achievement("Suitably Skeptical", "Win with The Godless.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.GODLESS, post_victory=True),
    Achievement("Gallivanting Greed", "Win with The Ravenous.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.RAVENOUS, post_victory=True),
    Achievement("The Clang Of Iron", "Win with the Fundamentalists.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.FUNDAMENTALISTS, post_victory=True),
    Achievement("The Passionate Eye", "Win with The Orthodox.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.ORTHODOX, post_victory=True),
    Achievement("Cloudscrapers", "Win with The Concentrated.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.CONCENTRATED, post_victory=True),
    Achievement("Never Rest", "Win with the Frontiersmen.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.FRONTIERSMEN, post_victory=True),
    Achievement("Empirical Evidence", "Win with the Imperials.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.IMPERIALS, post_victory=True),
    Achievement("The Singular Purpose", "Win with The Persistent.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.PERSISTENT, post_victory=True),
    Achievement("Cartographic Courage", "Win with the Explorers.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.EXPLORERS, post_victory=True),
    Achievement("Sub-Human, Super-Success", "Win with the Infidels.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.INFIDELS, post_victory=True),
    Achievement("Shine In The Dark", "Win with The Nocturne.",
                lambda gs, _: gs.players[gs.player_idx].faction == Faction.NOCTURNE, post_victory=True),
    Achievement("The Golden Quad", "Found a settlement on a quad with at least 19 total yield.",
                lambda gs, _: any((setl.quads[0].wealth + setl.quads[0].harvest +
                                   setl.quads[0].zeal + setl.quads[0].fortune) >= 19
                                  for setl in gs.players[gs.player_idx].settlements)),
    Achievement("Wholly Blessed", "Undergo all non-victory blessings.",
                lambda gs, _: len(gs.players[gs.player_idx].blessings) >= len(BLESSINGS) - 4),
    Achievement("Unstoppable Force", "Have 20 deployed units.",
                lambda gs, _: len(gs.players[gs.player_idx].units) >= 20),
    Achievement("Full House", "Besiege a settlement with 8 units at once.",
                achievements.verify_full_house),
    Achievement("Sprawling Skyscrapers", "Fully expand a Concentrated settlement.",
                lambda gs, _: (gs.players[gs.player_idx].faction == Faction.CONCENTRATED and
                               any(setl.level == 10 for setl in gs.players[gs.player_idx].settlements))),
    Achievement("Ready Reservists", "Accumulate 10 units in a garrison.",
                lambda gs, _: any(len(setl.garrison) >= 10 for setl in gs.players[gs.player_idx].settlements)),
    Achievement("The Big Wall", "Have a settlement reach 300 strength.",
                lambda gs, _: any(setl.strength >= 300 for setl in gs.players[gs.player_idx].settlements)),
    Achievement("Utopia", "Reach 100 satisfaction in a settlement.",
                lambda gs, _: any(setl.satisfaction == 100 for setl in gs.players[gs.player_idx].settlements)),
    Achievement("All Grown Up", "Reach level 10 in a settlement.",
                lambda gs, _: any(setl.level == 10 for setl in gs.players[gs.player_idx].settlements)),
    Achievement("Terra Nullius", "Found 10 settlements.",
                lambda gs, _: len(gs.players[gs.player_idx].settlements) >= 10),
    Achievement("All Is Revealed", "See all quads in a fog of war game.",
                lambda gs, _: len(gs.players[gs.player_idx].quads_seen) == 9000),
    Achievement("Player's Choice", "Have at least 3 imminent victories in one game.",
                lambda gs, _: len(gs.players[gs.player_idx].imminent_victories) >= 3),
    # The below will need to be changed if extra factions are ever introduced.
    Achievement("Free For All", "Win a game with 14 players.",
                lambda gs, _: len(gs.players) == 14, post_victory=True),
    Achievement("Sleepwalker", "Have 5 units deployed at nighttime.",
                lambda gs, _: gs.nighttime_left > 0 and len(gs.players[gs.player_idx].units) >= 5),
    Achievement("Just Before Bed", "Play for 1 hour total.",
                lambda _, stats: int(stats.playtime // 3600) >= 1),
    Achievement("All Nighter", "Play for 5 hours total.",
                lambda _, stats: int(stats.playtime // 3600) >= 5),
    Achievement("Keep Coming Back", "Play for 20 hours total.",
                lambda _, stats: int(stats.playtime // 3600) >= 20),
    Achievement("One More Turn", "Play 250 turns.",
                lambda _, stats: stats.turns_played >= 250),
    Achievement("What Time Is It?", "Play 1000 turns.",
                lambda _, stats: stats.turns_played >= 1000),
    Achievement("The Collector", "Achieve every type of victory.",
                lambda _, stats: len(stats.victories) == 6),
    Achievement("Globalist", "Use every faction.",
                # The below will need to be changed if extra factions are ever introduced.
                lambda _, stats: len(stats.factions) == 14),
    Achievement("Midnight Feast", "Achieve plentiful harvest in a settlement at nighttime.",
                lambda gs, _: gs.nighttime_left > 0 and any(setl.harvest_status == HarvestStatus.PLENTIFUL
                                                            for setl in gs.players[gs.player_idx].settlements)),
    Achievement("It's Worth It", "Build an improvement that decreases satisfaction.",
                achievements.verify_its_worth_it),
    Achievement("On The Brink", "Found a settlement on the edge of the map.",
                lambda gs, _: any(setl.location[0] == 0 or setl.location[0] == 99 or
                                  setl.location[1] == 0 or setl.location[1] == 89
                                  for setl in gs.players[gs.player_idx].settlements)),
    Achievement("Speed Run", "Win a 2 player game in 25 turns or less.",
                lambda gs, _: len(gs.players) == 2 and gs.turn <= 25, post_victory=True),
    Achievement("Mighty Miner", "Have 100 ore.",
                lambda gs, _: gs.players[gs.player_idx].resources.ore >= 100),
    Achievement("Lofty Lumberjack", "Have 100 timber.",
                lambda gs, _: gs.players[gs.player_idx].resources.timber >= 100),
    Achievement("Molten Multitude", "Have 100 magma.",
                lambda gs, _: gs.players[gs.player_idx].resources.magma >= 100),
    Achievement("The Third X", "Have a settlement with 4 or more resources.",
                achievements.verify_the_third_x),
    Achievement("Luxuries Abound", "Have one of each rare resource.",
                lambda gs, _: ((res := gs.players[gs.player_idx].resources).aurora and
                               res.bloodstone and res.obsidian and res.sunstone and res.aquamarine)),
    Achievement("Going Online", "Win a multiplayer game.",
                lambda gs, _: gs.board.game_config.multiplayer, post_victory=True),
    Achievement("Big Game Hunter", "Win a 14 player multiplayer game.",
                lambda gs, _: gs.board.game_config.multiplayer and len(gs.players) == 14, post_victory=True),
    Achievement("Focus Victim", "Be eliminated first in a multiplayer game.",
                lambda gs, _: (gs.board.game_config.multiplayer and
                               gs.players[gs.player_idx].eliminated and
                               len([p for p in gs.players if p.eliminated]) == 1 and
                               len(gs.players) > 2)),
    Achievement("Greetings Fellow Robots", "Win a multiplayer game as the only human.",
                lambda gs, _: (gs.board.game_config.multiplayer and
                               len([p for p in gs.players if not p.ai_playstyle]) == 1), post_victory=True),
    Achievement("50 Hours Later", "Play 200 turns in a single multiplayer game.",
                lambda gs, _: gs.board.game_config.multiplayer and gs.turn >= 200)
]


def get_heathen_plan(turn: int) -> UnitPlan:
    """
    Returns the turn-adjusted UnitPlan for the Heathen units. Heathens have their power and health increased by 10 every
    40 turns.
    :param turn: The game's current turn.
    :return: The UnitPlan to use for the created Heathen.
    """
    return UnitPlan(80.0 + 10 * (turn // 40), 80.0 + 10 * (turn // 40), 2, "Heathen" + "+" * (turn // 40), None, 0.0)


def get_heathen(location: (int, int), turn: int) -> Heathen:
    """
    Creates a heathen at the given location.
    :param location: The location for the heathen-to-be.
    :param turn: The game's current turn.
    :return: The created Heathen object.
    """
    plan = get_heathen_plan(turn)
    return Heathen(plan.max_health, plan.total_stamina, location, plan)


def get_default_unit(location: (int, int)) -> Unit:
    """
    Creates the default unit for each player in their first settlement, which is a Warrior.
    :param location: The location for the unit. Largely irrelevant due to the fact that it is garrisoned.
    :return: The created Unit object.
    """
    return Unit(UNIT_PLANS[0].max_health, UNIT_PLANS[0].total_stamina, location, True, deepcopy(UNIT_PLANS[0]))


def get_available_improvements(player: Player,
                               settlement: Settlement,
                               strict: bool = False) -> List[Improvement]:
    """
    Retrieves the available improvements for the given player's settlement.
    :param player: The owner of the given settlement.
    :param settlement: The settlement to retrieve improvements for.
    :param strict: Whether to only include improvements that the player has the required resources for.
    :return: A list of available improvements.
    """
    # Once frontier settlements reach level 5, they can only construct settler units, and no improvements.
    if player.faction == Faction.FRONTIERSMEN and settlement.level >= 5:
        return []
    completed_blessing_names = list(map(lambda blessing: blessing.name, player.blessings))
    # An improvement is available if the improvement has not been built in this settlement yet, either the player has
    # satisfied the improvement's pre-requisite or the improvement does not have one, and either we don't care about
    # resources for this call or the player has the required resources (if any) for the improvement.
    imps = [imp for imp in IMPROVEMENTS if (imp.prereq is None or imp.prereq.name in completed_blessing_names)
            and imp not in settlement.improvements
            and (not strict or (not imp.req_resources or player_has_resources_for_improvement(player, imp)))]

    # Sort improvements by cost.
    imps.sort(key=lambda i: i.cost)
    return imps


def get_available_unit_plans(player: Player, setl: Settlement) -> List[UnitPlan]:
    """
    Retrieves the available unit plans for the given player and settlement level.
    :param player: The player viewing the available units.
    :param setl: The settlement the player is viewing units in.
    :return: A list of available units.
    """
    unit_plans = []
    completed_blessing_names = list(map(lambda blessing: blessing.name, player.blessings))
    for unit_plan in deepcopy(UNIT_PLANS):
        # A unit plan is available if the unit plan's pre-requisite has been satisfied, or it is non-existent.
        if unit_plan.prereq is None or unit_plan.prereq.name in completed_blessing_names:
            # Note that settlers can only be recruited in settlements of at least level 2. Additionally, users of The
            # Concentrated cannot construct settlers at all.
            if unit_plan.can_settle and setl.level > 1 and player.faction != Faction.CONCENTRATED:
                unit_plans.append(unit_plan)
            # Once frontier settlements reach level 5, they can only construct settler units, and no improvements.
            elif not unit_plan.can_settle and not (player.faction == Faction.FRONTIERSMEN and setl.level >= 5):
                unit_plans.append(unit_plan)
        scale_unit_plan_attributes(unit_plan, player.faction, setl.resources)

    # Sort unit plans by cost.
    unit_plans.sort(key=lambda up: up.cost)
    return unit_plans


def get_available_blessings(player: Player) -> List[Blessing]:
    """
    Retrieves the available blessings for the given player.
    :param player: The player viewing the available blessings.
    :return: A list of available blessings.
    """
    completed_blessing_names = list(map(lambda blessing: blessing.name, player.blessings))
    blessings = [scale_blessing_attributes(bls, player.faction) for bls in deepcopy(BLESSINGS).values()
                 if bls.name not in completed_blessing_names]

    # Sort blessings by cost.
    blessings.sort(key=lambda b: b.cost)
    return blessings


def get_all_unlockable(blessing: Blessing) -> List[Improvement | UnitPlan]:
    """
    Retrieves all unlockable improvements and unit plans for the given blessing.
    :param blessing: The blessing to search pre-requisites for.
    :return: A list of unlockable improvements and unit plans.
    """
    unlockable: List[Improvement | UnitPlan] = get_unlockable_improvements(blessing)
    unlockable.extend(get_unlockable_units(blessing))
    return unlockable


def get_unlockable_improvements(blessing: Blessing) -> List[Improvement]:
    """
    Retrieves all unlockable improvements for the given blessing.
    :param blessing: The blessing to search pre-requisites for.
    :return: A list of unlockable improvements.
    """
    return [imp for imp in IMPROVEMENTS if (imp.prereq is not None) and (imp.prereq.name == blessing.name)]


def get_unlockable_units(blessing: Blessing) -> List[UnitPlan]:
    """
    Retrieves all unlockable unit plans for the given blessing.
    :param blessing: The blessing to search pre-requisites for.
    :return: A list of unlockable unit plans.
    """
    return [up for up in UNIT_PLANS if (up.prereq is not None) and (up.prereq.name == blessing.name)]


def get_improvement(name: str) -> Improvement:
    """
    Get the improvement with the given name. Used when loading games and in multiplayer games.
    :param name: The name of the improvement.
    :return: The Improvement with the given name.
    """
    return next(imp for imp in IMPROVEMENTS if imp.name == name)


def get_project(name: str) -> Project:
    """
    Get the project with the given name. Used when loading games and in multiplayer games.
    :param name: The name of the project.
    :return: The Project with the given name.
    """
    return next(prj for prj in PROJECTS if prj.name == name)


def get_blessing(name: str, faction: Faction) -> Blessing:
    """
    Get the blessing with the given name. Used when loading games and in multiplayer games.
    :param name: The name of the blessing.
    :param faction: The faction of the player retrieving the blessing.
    :return: The Blessing with the given name, with scaled attributes if necessary.
    """
    # We need to deepcopy so that changes to one Blessing don't affect all the others as well.
    blessing: Blessing = deepcopy(next(bls for bls in BLESSINGS.values() if bls.name == name))
    scale_blessing_attributes(blessing, faction)
    return blessing


def get_unit_plan(name: str, faction: Faction, setl_resources: Optional[ResourceCollection] = None) -> UnitPlan:
    """
    Get the unit plan with the given name. Used when loading games and in multiplayer games.
    :param name: The name of the unit plan.
    :param faction: The faction of the player retrieving the unit plan.
    :param setl_resources: The optionally-supplied resource collection of the settlement that this unit plan will be
                           constructed in. Naturally unsupplied if the unit plan is not under construction.
    :return: The UnitPlan with the given name, with scaled attributes if necessary.
    """
    # We need to deepcopy so that changes to one UnitPlan don't affect all the others as well.
    unit_plan: UnitPlan = deepcopy(next(up for up in UNIT_PLANS if up.name == name))
    scale_unit_plan_attributes(unit_plan, faction, setl_resources)
    if unit_plan.prereq is not None:
        scale_blessing_attributes(unit_plan.prereq, faction)
    return unit_plan
