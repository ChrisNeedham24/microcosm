import random
import typing

from models import Player, Improvement, ImprovementType, Effect, Blessing, Settlement, UnitPlan, Unit, Biome, Heathen

SETL_NAMES = {
    Biome.DESERT: [
        "Enfu", "Saknoten", "Despemar", "Khasolzum", "Nekpesir", "Akhtamar", "Absai", "Khanomhat", "Sharrisir", "Kisri"
    ],
    Biome.FOREST: [
        "Kalshara", "Mora Caelora", "Yam Ennore", "Uyla Themar", "Nelrenqua", "Caranlian", "Osaenamel", "Elhamel",
        "Allenrion", "Nilathaes"
    ],
    Biome.SEA: [
        "Natanas", "Tempetia", "Leviarey", "Atlalis", "Neptulean", "Oceacada", "Naurus", "Hylore", "Expathis", "Liquasa"
    ],
    Biome.MOUNTAIN: [
        "Nem Tarhir", "Dharnturm", "Hun Thurum", "Vil Tarum", "Khurn Kuldihr", "Hildarim", "Gog Daruhl", "Vogguruhm",
        "Dhighthiod", "Malwihr"
    ]
}


def get_settlement_name(biome: Biome) -> str:
    name = random.choice(SETL_NAMES[biome])
    SETL_NAMES[biome].remove(name)
    return name

# TODO FF Put descriptions of blessings and improvements in the wiki

BLESSINGS = {
    "beg_spl": Blessing("Beginner Spells", "Everyone has to start somewhere, right?", 50),
    "div_arc": Blessing("Divine Architecture", "As the holy ones intended.", 150),
    "rud_exp": Blessing("Rudimentary Explosives", "Nothing can go wrong with this.", 50),
    "rob_exp": Blessing("Robotic Experiments", "The artificial eye only stares back.", 150),
    "adv_trd": Blessing("Advanced Trading", "You could base a society on this.", 50),
    "sl_vau": Blessing("Self-locking Vaults", "Nothing's getting in or out.", 150),
    "prf_nec": Blessing("Profitable Necessities", "The irresistible temptation of a quick buck.", 50),
    "art_pht": Blessing("Hollow Photosynthesis", "Moonlight is just as good.", 150),
    "tor_tec": Blessing("Torture Techniques", "There's got to be something better.", 50),
    "apr_ref": Blessing("Aperture Refinement", "Picture perfect.", 150),
    "grt_goo": Blessing("The Greater Good", "The benefit of helping others.", 50),
    "ref_prc": Blessing("Reformist Principles", "Maybe another system could be better.", 150)
}

# TODO F Should be able to expand a settlement somehow probably

IMPROVEMENTS = [
    Improvement(ImprovementType.MAGICAL, 30, "Melting Pot", "A starting pot to conduct concoctions.",
                Effect(fortune=5, satisfaction=2), None),
    Improvement(ImprovementType.MAGICAL, 100, "Haunted Forest", "The branches shake, yet there's no wind.",
                Effect(harvest=1, fortune=8, satisfaction=-5), BLESSINGS["beg_spl"]),
    Improvement(ImprovementType.MAGICAL, 100, "Occult Bartering", "Dealing with both dead and alive.",
                Effect(wealth=1, fortune=8, satisfaction=-1), BLESSINGS["adv_trd"]),
    Improvement(ImprovementType.MAGICAL, 250, "Ancient Shrine", "Some say it emanates an invigorating aura.",
                Effect(wealth=2, zeal=-2, fortune=20, satisfaction=10), BLESSINGS["div_arc"]),
    Improvement(ImprovementType.MAGICAL, 250, "Dimensional imagery", "See into another world.",
                Effect(fortune=25, satisfaction=2), BLESSINGS["apr_ref"]),
    Improvement(ImprovementType.INDUSTRIAL, 30, "Local Forge", "Just a mum-and-dad-type operation.",
                Effect(wealth=2, zeal=5), None),
    Improvement(ImprovementType.INDUSTRIAL, 100, "Weapons Factory", "Made to kill outsiders. Mostly.",
                Effect(wealth=2, zeal=5, strength=25, satisfaction=-2), BLESSINGS["rud_exp"]),
    Improvement(ImprovementType.INDUSTRIAL, 100, "Enslaved Workforce", "Gets the job done.",
                Effect(wealth=2, harvest=-1, zeal=6, fortune=-2, satisfaction=-5), BLESSINGS["tor_tec"]),
    Improvement(ImprovementType.INDUSTRIAL, 250, "Automated Production", "In and out, no fuss.",
                Effect(wealth=3, zeal=30, satisfaction=-10), BLESSINGS["rob_exp"]),
    Improvement(ImprovementType.INDUSTRIAL, 250, "Lab-grown Workers", "Human or not, they work the same.",
                Effect(wealth=3, harvest=-2, zeal=30, fortune=-5, strength=2, satisfaction=-10), BLESSINGS["art_pht"]),
    Improvement(ImprovementType.ECONOMICAL, 30, "City Market", "Pockets empty, but friend or foe?",
                Effect(wealth=5, harvest=2, zeal=2, fortune=-1, satisfaction=2), None),
    Improvement(ImprovementType.ECONOMICAL, 100, "State Bank", "You're not the first to try your luck.",
                Effect(wealth=8, fortune=-2, strength=5, satisfaction=2), BLESSINGS["adv_trd"]),
    Improvement(ImprovementType.ECONOMICAL, 100, "Harvest Levy", "Definitely only for times of need.",
                Effect(wealth=8, harvest=2, zeal=-1, fortune=-1, satisfaction=-2), BLESSINGS["prf_nec"]),
    Improvement(ImprovementType.ECONOMICAL, 250, "National Mint", "Gold as far as the eye can see.",
                Effect(wealth=30, fortune=-5, strength=10, satisfaction=5), BLESSINGS["sl_vau"]),
    Improvement(ImprovementType.ECONOMICAL, 250, "Federal Museum", "Cataloguing all that was left for us.",
                Effect(wealth=10, fortune=10, satisfaction=4), BLESSINGS["div_arc"]),
    Improvement(ImprovementType.BOUNTIFUL, 30, "Collectivised Farms", "Well, the shelves will be stocked.",
                Effect(wealth=2, harvest=10, zeal=-2, satisfaction=-2), None),
    Improvement(ImprovementType.BOUNTIFUL, 100, "Supermarket Chains", "On every street corner.",
                Effect(harvest=8, satisfaction=2), BLESSINGS["prf_nec"]),
    Improvement(ImprovementType.BOUNTIFUL, 100, "Distributed Rations", "Everyone gets their fair share.",
                Effect(harvest=8, zeal=-1, fortune=1, satisfaction=-1), BLESSINGS["grt_goo"]),
    Improvement(ImprovementType.BOUNTIFUL, 250, "Underground Greenhouses", "The glass is just for show.",
                Effect(harvest=25, zeal=-5, fortune=-2), BLESSINGS["art_pht"]),
    Improvement(ImprovementType.BOUNTIFUL, 250, "Impenetrable Stores", "Unprecedented control over stock.",
                Effect(wealth=-1, harvest=25, strength=5, satisfaction=-5), BLESSINGS["sl_vau"]),
    Improvement(ImprovementType.INTIMIDATORY, 30, "Insurmountable Walls", "Quite the view from up here.",
                Effect(strength=25, satisfaction=2), None),
    Improvement(ImprovementType.INTIMIDATORY, 100, "Intelligence Academy", "What's learnt in here, stays in here.",
                Effect(strength=30, satisfaction=-2), BLESSINGS["tor_tec"]),
    Improvement(ImprovementType.INTIMIDATORY, 100, "Minefields", "Cross if you dare.",
                Effect(harvest=-1, strength=30, satisfaction=-1), BLESSINGS["rud_exp"]),
    Improvement(ImprovementType.INTIMIDATORY, 250, "CCTV Cameras", "Big Brother's always watching.",
                Effect(zeal=5, fortune=-2, strength=50, satisfaction=-2), BLESSINGS["apr_ref"]),
    Improvement(ImprovementType.INTIMIDATORY, 250, "Cult of Personality", "The supreme leader can do no wrong.",
                Effect(wealth=2, harvest=2, zeal=2, fortune=2, strength=50, satisfaction=5), BLESSINGS["ref_prc"]),
    Improvement(ImprovementType.PANDERING, 30, "Aqueduct", "Water from there to here.",
                Effect(harvest=2, fortune=-1, satisfaction=5), None),
    Improvement(ImprovementType.PANDERING, 100, "Soup Kitchen", "No one's going hungry here.",
                Effect(wealth=-1, zeal=2, fortune=2, satisfaction=6), BLESSINGS["grt_goo"]),
    Improvement(ImprovementType.PANDERING, 100, "Puppet Shows", "Putting those spells to use.",
                Effect(wealth=1, zeal=-1, fortune=1, satisfaction=6), BLESSINGS["beg_spl"]),
    Improvement(ImprovementType.PANDERING, 250, "Universal Basic Income", "Utopian in more ways than one.",
                Effect(wealth=-5, harvest=2, zeal=2, fortune=2, strength=2, satisfaction=10), BLESSINGS["ref_prc"]),
    Improvement(ImprovementType.PANDERING, 250, "Infinite Entertainment", "Where the robots are the stars.",
                Effect(zeal=2, fortune=-1, satisfaction=12), BLESSINGS["rob_exp"])
]

UNIT_PLANS = [
    UnitPlan(100, 100, 3, "Warrior", None, 25),
    UnitPlan(125, 50, 5, "Archer", None, 25),
    UnitPlan(25, 25, 6, "Settler", None, 50, can_settle=True),
    UnitPlan(150, 75, 4, "Mage", BLESSINGS["beg_spl"], 50),
    UnitPlan(200, 40, 2, "Grenadier", BLESSINGS["rud_exp"], 75),
    UnitPlan(150, 150, 5, "Drone", BLESSINGS["rob_exp"], 125),
    UnitPlan(50, 200, 2, "Flagellant", BLESSINGS["tor_tec"], 80),
    UnitPlan(150, 125, 3, "Sniper", BLESSINGS["apr_ref"], 100),
]


HEATHEN_UNIT_PLAN = UnitPlan(80, 80, 2, "Heathen", None, 0)


def get_heathen(location: (int, int)) -> Heathen:
    return Heathen(HEATHEN_UNIT_PLAN.max_health, HEATHEN_UNIT_PLAN.total_stamina, location, HEATHEN_UNIT_PLAN)


def get_default_unit(location: (int, int)) -> Unit:
    return Unit(UNIT_PLANS[0].max_health, UNIT_PLANS[0].total_stamina, location, True, UNIT_PLANS[0])


def get_available_improvements(player: Player, settlement: Settlement) -> typing.List[Improvement]:
    imps = [imp for imp in IMPROVEMENTS if (imp.prereq in player.blessings or imp.prereq is None)
            and imp not in settlement.improvements]

    def get_cost(imp: Improvement) -> float:
        return imp.cost

    imps.sort(key=get_cost)
    return imps


def get_available_unit_plans(player: Player, setl_lvl: int) -> typing.List[UnitPlan]:
    unit_plans = []
    for unit_plan in UNIT_PLANS:
        if unit_plan.prereq is None or unit_plan.prereq in player.blessings:
            if unit_plan.can_settle and setl_lvl > 1:
                unit_plans.append(unit_plan)
            elif not unit_plan.can_settle:
                unit_plans.append(unit_plan)

    def get_cost(up: UnitPlan) -> float:
        return up.cost

    unit_plans.sort(key=get_cost)
    return unit_plans


def get_available_blessings(player: Player) -> typing.List[Blessing]:
    blessings = [bls for bls in BLESSINGS.values() if bls not in player.blessings]

    def get_cost(blessing: Blessing) -> float:
        return blessing.cost

    blessings.sort(key=get_cost)
    return blessings


def get_unlockable_improvements(blessing: Blessing) -> typing.List[Improvement]:
    return [imp for imp in IMPROVEMENTS if imp.prereq is blessing]
