import random
import typing
from copy import deepcopy

import pyxel

from models import Player, Improvement, ImprovementType, Effect, Blessing, Settlement, UnitPlan, Unit, Biome, Heathen, \
    Faction, Project, ProjectType

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
        Removes a settlement name from the list. Used in loaded game cases.
        :param name: The settlement name to remove.
        :param biome: The biome of the settlement. Used to locate the name in the dictionary.
        """
        self.names[biome].remove(name)

    def reset(self):
        """
        Resets the available names.
        """
        self.names = deepcopy(SETL_NAMES)


# The list of blessings that can be undergone.
BLESSINGS = {
    "beg_spl": Blessing("Beginner Spells", "Everyone has to start somewhere, right?", 100),
    "div_arc": Blessing("Divine Architecture", "As the holy ones intended.", 500),
    "inh_luc": Blessing("Inherent Luck", "Better lucky than good.", 2500),
    "rud_exp": Blessing("Rudimentary Explosives", "Nothing can go wrong with this.", 100),
    "rob_exp": Blessing("Robotic Experiments", "The artificial eye only stares back.", 500),
    "res_rep": Blessing("Resource Replenishment", "Never run out of what you need.", 2500),
    "adv_trd": Blessing("Advanced Trading", "You could base a society on this.", 100),
    "sl_vau": Blessing("Self-locking Vaults", "Nothing's getting in or out.", 500),
    "eco_mov": Blessing("Economic Movements", "Know the inevitable before it occurs.", 2500),
    "prf_nec": Blessing("Profitable Necessities", "The irresistible appeal of a quick buck.", 100),
    "art_pht": Blessing("Hollow Photosynthesis", "Moonlight is just as good.", 500),
    "met_alt": Blessing("Metabolic Alterations", "I feel full already!", 2500),
    "tor_tec": Blessing("Torture Techniques", "There's got to be something better.", 100),
    "apr_ref": Blessing("Aperture Refinement", "Picture perfect.", 500),
    "psy_sup": Blessing("Psychic Supervision", "I won't do what you tell me.", 2500),
    "grt_goo": Blessing("The Greater Good", "The benefit of helping others.", 100),
    "ref_prc": Blessing("Reformist Principles", "Maybe another system could be better.", 500),
    "brd_fan": Blessing("Broad Fanaticism", "Maybe I can do no wrong.", 2500),
    "anc_his": Blessing("Ancient History", "Guide us to the light.", 25000),
    "ard_one": Blessing("Piece of Strength", "The mighty will prevail.", 15000),
    "ard_two": Blessing("Piece of Passion", "Only the passionate will remain.", 15000),
    "ard_three": Blessing("Piece of Divinity", "Everything is revealed.", 15000)
}

# The list of improvements that can be built.
IMPROVEMENTS = [
    Improvement(ImprovementType.MAGICAL, 30, "Melting Pot", "A starting pot to conduct concoctions.",
                Effect(fortune=5, satisfaction=2), None),
    Improvement(ImprovementType.MAGICAL, 180, "Haunted Forest", "The branches shake, yet there's no wind.",
                Effect(harvest=1, fortune=8, satisfaction=-5), BLESSINGS["beg_spl"]),
    Improvement(ImprovementType.MAGICAL, 180, "Occult Bartering", "Dealing with both dead and alive.",
                Effect(wealth=1, fortune=8, satisfaction=-1), BLESSINGS["adv_trd"]),
    Improvement(ImprovementType.MAGICAL, 1080, "Ancient Shrine", "Some say it emanates an invigorating aura.",
                Effect(wealth=2, zeal=-2, fortune=20, satisfaction=10), BLESSINGS["div_arc"]),
    Improvement(ImprovementType.MAGICAL, 1080, "Dimensional imagery", "See into another world.",
                Effect(fortune=25, satisfaction=2), BLESSINGS["apr_ref"]),
    Improvement(ImprovementType.MAGICAL, 1080, "Fortune Distillery", "Straight from the mouth.",
                Effect(zeal=-2, fortune=25, strength=-10, satisfaction=5), BLESSINGS["inh_luc"]),
    Improvement(ImprovementType.INDUSTRIAL, 30, "Local Forge", "Just a mum-and-dad-type operation.",
                Effect(wealth=2, zeal=5), None),
    Improvement(ImprovementType.INDUSTRIAL, 180, "Weapons Factory", "Made to kill outsiders. Mostly.",
                Effect(wealth=2, zeal=5, strength=25, satisfaction=-2), BLESSINGS["rud_exp"]),
    Improvement(ImprovementType.INDUSTRIAL, 180, "Enslaved Workforce", "Gets the job done.",
                Effect(wealth=2, harvest=-1, zeal=6, fortune=-2, satisfaction=-5), BLESSINGS["tor_tec"]),
    Improvement(ImprovementType.INDUSTRIAL, 1080, "Automated Production", "In and out, no fuss.",
                Effect(wealth=3, zeal=30, satisfaction=-10), BLESSINGS["rob_exp"]),
    Improvement(ImprovementType.INDUSTRIAL, 1080, "Lab-grown Workers", "Human or not, they work the same.",
                Effect(wealth=3, harvest=-2, zeal=30, fortune=-5, strength=2, satisfaction=-10), BLESSINGS["art_pht"]),
    Improvement(ImprovementType.INDUSTRIAL, 1080, "Endless Mine", "Hang on, didn't I just remove that?",
                Effect(wealth=5, zeal=25, fortune=-2), BLESSINGS["res_rep"]),
    Improvement(ImprovementType.ECONOMICAL, 30, "City Market", "Pockets empty, but friend or foe?",
                Effect(wealth=5, harvest=2, zeal=2, fortune=-1, satisfaction=2), None),
    Improvement(ImprovementType.ECONOMICAL, 180, "State Bank", "You're not the first to try your luck.",
                Effect(wealth=8, fortune=-2, strength=5, satisfaction=2), BLESSINGS["adv_trd"]),
    Improvement(ImprovementType.ECONOMICAL, 180, "Harvest Levy", "Definitely only for times of need.",
                Effect(wealth=8, harvest=2, zeal=-1, fortune=-1, satisfaction=-2), BLESSINGS["prf_nec"]),
    Improvement(ImprovementType.ECONOMICAL, 1080, "National Mint", "Gold as far as the eye can see.",
                Effect(wealth=30, fortune=-5, strength=10, satisfaction=5), BLESSINGS["sl_vau"]),
    Improvement(ImprovementType.ECONOMICAL, 1080, "Federal Museum", "Cataloguing all that was left for us.",
                Effect(wealth=10, fortune=10, satisfaction=4), BLESSINGS["div_arc"]),
    Improvement(ImprovementType.ECONOMICAL, 1080, "Planned Economy", "Under the watchful eye.",
                Effect(wealth=20, harvest=5, zeal=5, satisfaction=-2), BLESSINGS["eco_mov"]),
    Improvement(ImprovementType.BOUNTIFUL, 30, "Collectivised Farms", "Well, the shelves will be stocked.",
                Effect(wealth=2, harvest=10, zeal=-2, satisfaction=-2), None),
    Improvement(ImprovementType.BOUNTIFUL, 180, "Supermarket Chains", "On every street corner.",
                Effect(harvest=8, satisfaction=2), BLESSINGS["prf_nec"]),
    Improvement(ImprovementType.BOUNTIFUL, 180, "Distributed Rations", "Everyone gets their fair share.",
                Effect(harvest=8, zeal=-1, fortune=1, satisfaction=-1), BLESSINGS["grt_goo"]),
    Improvement(ImprovementType.BOUNTIFUL, 1080, "Sunken Greenhouses", "The glass is just for show.",
                Effect(harvest=25, zeal=-5, fortune=-2), BLESSINGS["art_pht"]),
    Improvement(ImprovementType.BOUNTIFUL, 1080, "Impenetrable Stores", "Unprecedented control over stock.",
                Effect(wealth=-1, harvest=25, strength=5, satisfaction=-5), BLESSINGS["sl_vau"]),
    Improvement(ImprovementType.BOUNTIFUL, 1080, "Genetic Clinics", "Change me for the better.",
                Effect(harvest=15, zeal=15), BLESSINGS["met_alt"]),
    Improvement(ImprovementType.INTIMIDATORY, 30, "Insurmountable Walls", "Quite the view from up here.",
                Effect(strength=25, satisfaction=2), None),
    Improvement(ImprovementType.INTIMIDATORY, 180, "Intelligence Academy", "What's learnt in here, stays in here.",
                Effect(strength=30, satisfaction=-2), BLESSINGS["tor_tec"]),
    Improvement(ImprovementType.INTIMIDATORY, 180, "Minefields", "Cross if you dare.",
                Effect(harvest=-1, strength=30, satisfaction=-1), BLESSINGS["rud_exp"]),
    Improvement(ImprovementType.INTIMIDATORY, 1080, "CCTV Cameras", "Big Brother's always watching.",
                Effect(zeal=5, fortune=-2, strength=50, satisfaction=-2), BLESSINGS["apr_ref"]),
    Improvement(ImprovementType.INTIMIDATORY, 1080, "Cult of Personality", "The supreme leader can do no wrong.",
                Effect(wealth=2, harvest=2, zeal=2, fortune=2, strength=50, satisfaction=5), BLESSINGS["ref_prc"]),
    Improvement(ImprovementType.INTIMIDATORY, 1080, "Omniscient Police", "Not even jaywalking is allowed.",
                Effect(wealth=-2, zeal=-2, fortune=-5, strength=100, satisfaction=-10), BLESSINGS["psy_sup"]),
    Improvement(ImprovementType.PANDERING, 30, "Aqueduct", "Water from there to here.",
                Effect(harvest=2, fortune=-1, satisfaction=5), None),
    Improvement(ImprovementType.PANDERING, 180, "Soup Kitchen", "No one's going hungry here.",
                Effect(wealth=-1, zeal=2, fortune=2, satisfaction=6), BLESSINGS["grt_goo"]),
    Improvement(ImprovementType.PANDERING, 180, "Puppet Shows", "Putting those spells to use.",
                Effect(wealth=1, zeal=-1, fortune=1, satisfaction=6), BLESSINGS["beg_spl"]),
    Improvement(ImprovementType.PANDERING, 1080, "Common Chief Yield", "Utopian in more ways than one.",
                Effect(wealth=-5, harvest=2, zeal=2, fortune=2, strength=2, satisfaction=10), BLESSINGS["ref_prc"]),
    Improvement(ImprovementType.PANDERING, 1080, "Infinite Disport", "Where the robots are the stars.",
                Effect(zeal=2, fortune=-1, satisfaction=12), BLESSINGS["rob_exp"]),
    Improvement(ImprovementType.PANDERING, 1080, "Free Expression", "Say what we know you'll say.",
                Effect(satisfaction=15), BLESSINGS["brd_fan"]),
    Improvement(ImprovementType.INDUSTRIAL, 20000, "Holy Sanctum", "To converse with the holy ones.",
                Effect(), BLESSINGS["anc_his"])
]

PROJECTS = [
    Project(ProjectType.BOUNTIFUL, "Call of the Fields", "From hand to mouth."),
    Project(ProjectType.ECONOMICAL, "Inflation by Design", "More is more, right?"),
    Project(ProjectType.MAGICAL, "The Holy Epiphany", "Awaken the soul.")
]

# The list of unit plans that units can be recruited according to.
UNIT_PLANS = [
    UnitPlan(100, 100, 3, "Warrior", None, 25),
    UnitPlan(125, 50, 5, "Bowman", None, 25),
    UnitPlan(75, 125, 2, "Shielder", None, 25),
    UnitPlan(25, 25, 6, "Settler", None, 50, can_settle=True),
    UnitPlan(150, 75, 4, "Mage", BLESSINGS["beg_spl"], 50),
    UnitPlan(50, 50, 10, "Locksmith", BLESSINGS["sl_vau"], 75),
    UnitPlan(200, 40, 2, "Grenadier", BLESSINGS["rud_exp"], 100),
    UnitPlan(50, 200, 2, "Flagellant", BLESSINGS["tor_tec"], 200),
    UnitPlan(150, 125, 3, "Sniper", BLESSINGS["apr_ref"], 400),
    UnitPlan(150, 150, 5, "Drone", BLESSINGS["rob_exp"], 800),
    UnitPlan(200, 200, 4, "Herculeum", BLESSINGS["met_alt"], 1200),
    UnitPlan(300, 50, 3, "Haruspex", BLESSINGS["psy_sup"], 1200),
    UnitPlan(40, 400, 2, "Fanatic", BLESSINGS["brd_fan"], 1200)
]


FACTION_COLOURS: typing.Dict[Faction, int] = {
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


def get_heathen_plan(turn: int) -> UnitPlan:
    """
    Returns the turn-adjusted UnitPlan for the Heathen units. Heathens have their power and health increased by 10 every
    40 turns.
    :param turn: The game's current turn.
    :return: The UnitPlan to use for the created Heathen.
    """
    return UnitPlan(80 + 10 * (turn // 40), 80 + 10 * (turn // 40), 2, "Heathen" + "+" * (turn // 40), None, 0)


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


def get_available_improvements(player: Player, settlement: Settlement) -> typing.List[Improvement]:
    """
    Retrieves the available improvements for the given player's settlement.
    :param player: The owner of the given settlement.
    :param settlement: The settlement to retrieve improvements for.
    :return: A list of available improvements.
    """
    # Once frontier settlements reach level 5, they can only construct settler units, and no improvements.
    if player.faction is Faction.FRONTIERSMEN and settlement.level >= 5:
        return []
    completed_blessing_names = list(map(lambda blessing: blessing.name, player.blessings))
    # An improvement is available if the improvement has not been built in this settlement yet and either the player has
    # satisfied the improvement's pre-requisite or the improvement does not have one.
    imps = [imp for imp in IMPROVEMENTS if (imp.prereq is None or imp.prereq.name in completed_blessing_names)
            and imp not in settlement.improvements]

    # Sort improvements by cost.
    imps.sort(key=lambda i: i.cost)
    return imps


def get_available_unit_plans(player: Player, setl_lvl: int) -> typing.List[UnitPlan]:
    """
    Retrieves the available unit plans for the given player and settlement level.
    :param player: The player viewing the available units.
    :param setl_lvl: The level of the settlement the player is viewing units in.
    :return: A list of available units.
    """
    unit_plans = []
    completed_blessing_names = list(map(lambda blessing: blessing.name, player.blessings))
    for unit_plan in deepcopy(UNIT_PLANS):
        # A unit plan is available if the unit plan's pre-requisite has been satisfied, or it is non-existent.
        if unit_plan.prereq is None or unit_plan.prereq.name in completed_blessing_names:
            # Note that settlers can only be recruited in settlements of at least level 2. Additionally, users of The
            # Concentrated cannot construct settlers at all.
            if unit_plan.can_settle and setl_lvl > 1 and player.faction is not Faction.CONCENTRATED:
                unit_plans.append(unit_plan)
            # Once frontier settlements reach level 5, they can only construct settler units, and no improvements.
            elif not unit_plan.can_settle and not (player.faction is Faction.FRONTIERSMEN and setl_lvl >= 5):
                unit_plans.append(unit_plan)

    if player.faction is Faction.IMPERIALS:
        for unit_plan in unit_plans:
            unit_plan.power *= 1.5
    elif player.faction is Faction.PERSISTENT:
        for unit_plan in unit_plans:
            unit_plan.max_health *= 1.5
            unit_plan.power *= 0.75
    elif player.faction is Faction.EXPLORERS:
        for unit_plan in unit_plans:
            unit_plan.total_stamina = round(1.5 * unit_plan.total_stamina)
            unit_plan.max_health *= 0.75

    # Sort unit plans by cost.
    unit_plans.sort(key=lambda up: up.cost)
    return unit_plans


def get_available_blessings(player: Player) -> typing.List[Blessing]:
    """
    Retrieves the available blessings for the given player.
    :param player: The player viewing the available blessings.
    :return: A list of available blessings.
    """
    completed_blessing_names = list(map(lambda blessing: blessing.name, player.blessings))
    blessings = [bls for bls in deepcopy(BLESSINGS).values() if bls.name not in completed_blessing_names]

    if player.faction is Faction.GODLESS:
        for bls in blessings:
            bls.cost *= 1.5

    # Sort blessings by cost.
    blessings.sort(key=lambda b: b.cost)
    return blessings


def get_all_unlockable(blessing: Blessing) -> typing.List[typing.Union[Improvement, UnitPlan]]:
    """
    Retrieves all unlockable improvements and unit plans for the given blessing.
    :param blessing: The blessing to search pre-requisites for.
    :return: A list of unlockable improvements and unit plans.
    """
    unlockable = [imp for imp in IMPROVEMENTS if (imp.prereq is not None) and (imp.prereq.name == blessing.name)]
    unlockable.extend([up for up in UNIT_PLANS if (up.prereq is not None) and (up.prereq.name == blessing.name)])
    return unlockable


def get_unlockable_improvements(blessing: Blessing) -> typing.List[Improvement]:
    """
    Retrieves all unlockable improvements for the given blessing.
    :param blessing: The blessing to search pre-requisites for.
    :return: A list of unlockable improvements.
    """
    return [imp for imp in IMPROVEMENTS if (imp.prereq is not None) and (imp.prereq.name == blessing.name)]


def get_unlockable_units(blessing: Blessing) -> typing.List[UnitPlan]:
    """
    Retrieves all unlockable unit plans for the given blessing.
    :param blessing: The blessing to search pre-requisites for.
    :return: A list of unlockable unit plans.
    """
    return [up for up in UNIT_PLANS if (up.prereq is not None) and (up.prereq.name == blessing.name)]


def get_improvement(name: str) -> Improvement:
    """
    Get the improvement with the given name. Used when loading games.
    :param name: The name of the improvement.
    :return: The Improvement with the given name.
    """
    return next(imp for imp in IMPROVEMENTS if imp.name == name)


def get_blessing(name: str) -> Blessing:
    """
    Get the blessing with the given name. Used when loading games.
    :param name: The name of the blessing.
    :return: The Blessing with the given name.
    """
    return next(bls for bls in BLESSINGS.values() if bls.name == name)


def get_unit_plan(name: str) -> UnitPlan:
    """
    Get the unit plan with the given name. Used when loading games.
    :param name: The name of the unit plan.
    :return: The UnitPlan with the given name.
    """
    return next(up for up in UNIT_PLANS if up.name == name)
