from typing import List, Optional, Set, Tuple

from source.foundation.catalogue import get_unit_plan, get_improvement, get_project, get_blessing, FACTION_COLOURS, \
    IMPROVEMENTS
from source.foundation.models import Quad, Biome, ResourceCollection, Player, Settlement, Unit, UnitPlan, Improvement, \
    Construction, HarvestStatus, EconomicStatus, Blessing, Faction, VictoryType, OngoingBlessing, AIPlaystyle, \
    AttackPlaystyle, ExpansionPlaystyle, Project, Heathen, DeployerUnit


def minify_resource_collection(rc: ResourceCollection) -> str:
    """
    Turn the given resource collection object into a minified string representation.
    :param rc: The resource collection object to minify.
    :return: A minified string representation of the resource collection.
    """
    return f"{rc.ore}+{rc.timber}+{rc.magma}+{rc.aurora}+{rc.bloodstone}+{rc.obsidian}+{rc.sunstone}+{rc.aquamarine}"


def minify_quad(quad: Quad) -> str:
    """
    Turn the given quad object into a minified string representation.
    :param quad: The quad object to minify.
    :return: A minified string representation of the quad.
    """
    # Just the first character of the biome is enough to identify it.
    quad_str: str = f"{quad.biome.value[0]}{quad.wealth}{quad.harvest}{quad.zeal}{quad.fortune}"
    if quad.resource:
        quad_str += minify_resource_collection(quad.resource)
    if quad.is_relic:
        quad_str += "ir"
    return quad_str


def minify_unit_plan(unit_plan: UnitPlan) -> str:
    """
    Turn the given unit plan object into a minified string representation.
    :param unit_plan: The unit plan object to minify.
    :return: A minified string representation of the unit plan.
    """
    return f"{unit_plan.power}/{unit_plan.max_health}/{unit_plan.total_stamina}/{unit_plan.cost}/{unit_plan.name}"


def minify_unit(unit: Unit) -> str:
    """
    Turn the given unit object into a minified string representation.
    :param unit: The unit object to minify.
    :return: A minified string representation of the unit.
    """
    unit_str: str = f"{unit.health}|{unit.remaining_stamina}|{unit.location[0]}-{unit.location[1]}|"
    unit_str += minify_unit_plan(unit.plan) + "|"
    unit_str += f"{unit.has_acted}|{unit.besieging}"
    if isinstance(unit, DeployerUnit):
        unit_str += "|"
        for passenger in unit.passengers:
            unit_str += minify_unit(passenger) + "^"
    return unit_str


def minify_improvement(improvement: Improvement) -> str:
    """
    Turn the given improvement object into a minified string representation.
    :param improvement: The improvement object to minify.
    :return: A minified string representation of the improvement.
    """
    # Just the first character of each word in the name of the improvement is enough to identify it.
    return "".join(word[0] for word in improvement.name.split(" "))


def minify_settlement(settlement: Settlement) -> str:
    """
    Turn the given settlement object into a minified string representation.
    :param settlement: The settlement object to minify.
    :return: A minified string representation of the settlement.
    """
    settlement_str: str = f"{settlement.name};{settlement.location[0]}-{settlement.location[1]};"
    settlement_str += "$".join(minify_improvement(imp) for imp in settlement.improvements) + ";"
    settlement_str += ",".join(f"{quad.location[0]}-{quad.location[1]}" for quad in settlement.quads) + ";"
    settlement_str += minify_resource_collection(settlement.resources) + ";"
    settlement_str += ",".join(minify_unit(unit) for unit in settlement.garrison) + ";"
    settlement_str += f"{settlement.strength};{settlement.max_strength};{settlement.satisfaction};"
    if cw := settlement.current_work:
        match cw.construction:
            case Improvement():
                settlement_str += "Improvement%"
            case Project():
                settlement_str += "Project%"
            case UnitPlan():
                settlement_str += "UnitPlan%"
        settlement_str += f"{cw.construction.name}%{cw.zeal_consumed}"
    settlement_str += ";"
    settlement_str += (f"{settlement.level};{settlement.harvest_reserves};"
                       f"{settlement.harvest_status.value};{settlement.economic_status.value};"
                       f"{settlement.produced_settler};{settlement.besieged}")
    return settlement_str


def minify_player(player: Player) -> str:
    """
    Turn the given player object into a minified string representation.
    :param player: The player object to minify.
    :return: A minified string representation of the player.
    """
    player_str: str = f"{player.name}~{player.faction.value}~{player.wealth}~"
    player_str += "!".join(minify_settlement(setl) for setl in player.settlements) + "~"
    player_str += "&".join(minify_unit(unit) for unit in player.units) + "~"
    player_str += ",".join(blessing.name for blessing in player.blessings) + "~"
    player_str += minify_resource_collection(player.resources) + "~"
    # We sort the player's imminent victories here specifically for testing purposes, so we can validate against the
    # whole minified string - this has no effect in actual use.
    player_str += ",".join([iv.value for iv in sorted(player.imminent_victories)]) + "~"
    if bls := player.ongoing_blessing:
        player_str += f"{bls.blessing.name}>{bls.fortune_consumed}"
    player_str += "~"
    if aip := player.ai_playstyle:
        player_str += f"{aip.attacking.value}-{aip.expansion.value}"
    player_str += "~"
    player_str += f"{player.jubilation_ctr}~{player.accumulated_wealth}~{player.eliminated}"
    return player_str


def minify_quads_seen(quads_seen: Set[Tuple[int, int]]) -> str:
    """
    Turn the given set of seen quads into a minified string representation.
    :param quads_seen: The set of seen quads to minify.
    :return: A minified string representation of the seen quads.
    """
    # We can just exclude seen quads with locations including negative values - they shouldn't exist anyway.
    return ",".join(f"{quad_loc[0]}-{quad_loc[1]}" for quad_loc in quads_seen if quad_loc[0] >= 0 and quad_loc[1] >= 0)


def minify_heathens(heathens: List[Heathen]) -> str:
    """
    Turn the given list of heathen objects into a minified string representation.
    :param heathens: The list of heathen objects to minify.
    :return: A minified string representation of the heathens.
    """
    heathens_str: str = ""
    for heathen in heathens:
        hp: UnitPlan = heathen.plan
        heathens_str += f"{heathen.health}*{heathen.remaining_stamina}*{heathen.location[0]}-{heathen.location[1]}*"
        heathens_str += f"{hp.power}*{hp.max_health}*{hp.total_stamina}*{hp.name}*{heathen.has_attacked},"
    return heathens_str


def inflate_resource_collection(rc_str: str) -> ResourceCollection:
    """
    Inflate the given minified resource collection string into a resource collection object.
    :param rc_str: The minified resource collection to inflate.
    :return: An inflated resource collection object.
    """
    # The below might look a bit complex at first glance, but we're just extracting out a list of integer values for
    # each resource in the collection and then using * to unpack them to be the arguments for the object constructor.
    return ResourceCollection(*[int(res) for res in rc_str.split("+")])


def inflate_quad(quad_str: str, location: (int, int)) -> Quad:
    """
    Inflate the given minified quad string into a quad object.
    :param quad_str: The minified quad to inflate.
    :param location: The location to use for the quad object - predetermined from the minified quad's index.
    :return: An inflated quad object.
    """
    quad_biome: Biome
    match quad_str[0]:
        case "D":
            quad_biome = Biome.DESERT
        case "F":
            quad_biome = Biome.FOREST
        case "S":
            quad_biome = Biome.SEA
        case "M":
            quad_biome = Biome.MOUNTAIN
    quad_resource: Optional[ResourceCollection] = None
    quad_is_relic: bool = False
    if len(quad_str) > 5:
        if len(quad_str) > 7:
            quad_resource = inflate_resource_collection(quad_str[5:20])
        quad_is_relic = quad_str.endswith("ir")
    inflated_quad: Quad = Quad(quad_biome, int(quad_str[1]), int(quad_str[2]), int(quad_str[3]), int(quad_str[4]),
                               location, resource=quad_resource, is_relic=quad_is_relic)
    return inflated_quad


def inflate_unit_plan(up_str: str, faction: Faction) -> UnitPlan:
    """
    Inflate the given minified unit plan string into a unit plan object.
    :param up_str: The minified unit plan to inflate.
    :param faction: The faction the inflated unit plan will belong to.
    :return: An inflated unit plan object.
    """
    split_up: List[str] = up_str.split("/")
    # Even though this unit plan could be in use by a unit currently being constructed by a settlement with bloodstone,
    # thus increasing its power and max health, we don't actually need the settlement to be supplied here. This is
    # because these two attributes are already minified anyway, and will be overwritten with the correct values below
    # regardless. Similarly, we mostly don't actually need the faction either, as the attributes that may be scaled
    # based on that are also covered below. The only reason we need the faction is that we may need to scale the cost of
    # the pre-requisite blessing for the unit plan, based on the player's faction.
    unit_plan: UnitPlan = get_unit_plan(split_up[-1], faction)
    unit_plan.power = float(split_up[0])
    unit_plan.max_health = float(split_up[1])
    unit_plan.total_stamina = int(split_up[2])
    unit_plan.cost = float(split_up[3])
    return unit_plan


def inflate_unit(unit_str: str, garrisoned: bool, faction: Faction) -> Unit:
    """
    Inflate the given minified unit string into a unit object.
    :param unit_str: The minified unit to inflate.
    :param garrisoned: Whether the minified unit is garrisoned.
    :param faction: The faction the inflated unit will belong to.
    :return: An inflated unit object.
    """
    split_unit: List[str] = unit_str.split("|")
    unit_health: float = float(split_unit[0])
    unit_rem_stamina: int = int(split_unit[1])
    # We need to do string comparisons against "True" here because if we just do 'is True' here instead, then everything
    # will evaluate to True. This is because any string that isn't empty is considered to be 'True'.
    unit_has_acted: bool = split_unit[4] == "True"
    unit_is_besieging: bool = split_unit[5] == "True"
    unit_loc: (int, int) = int(split_unit[2].split("-")[0]), int(split_unit[2].split("-")[1])
    # If the minified unit only has six parts, then it is a standard non-deployer unit.
    if len(split_unit) == 6:
        return Unit(unit_health, unit_rem_stamina, unit_loc, garrisoned, inflate_unit_plan(split_unit[3], faction),
                    unit_has_acted, unit_is_besieging)
    # Otherwise, it must be a deployer unit.
    passengers_str: str = "|".join(split_unit[6:])
    # Because we add a carat per passenger, there will be an extra one on the end. As such, we discard the last
    # split element.
    split_passengers: List[str] = passengers_str.split("^")[:-1]
    passengers: List[Unit] = [inflate_unit(sp, garrisoned=False, faction=faction) for sp in split_passengers]
    return DeployerUnit(unit_health, unit_rem_stamina, unit_loc, garrisoned, inflate_unit_plan(split_unit[3], faction),
                        unit_has_acted, unit_is_besieging, passengers)


def inflate_improvement(improvement_str: str) -> Improvement:
    """
    Inflate the given minified improvement string into an improvement object.
    :param improvement_str: The minified improvement to inflate.
    :return: An inflated improvement object.
    """
    # This is one of the more naive functions - we literally just test this string against all of the minified options.
    return next(imp for imp in IMPROVEMENTS if minify_improvement(imp) == improvement_str)


def inflate_settlement(setl_str: str, quads: List[List[Quad]], faction: Faction) -> Settlement:
    """
    Inflate the given minified settlement string into a settlement object.
    :param setl_str: The minified settlement to inflate.
    :param quads: The quads on the board.
    :param faction: The faction the inflated settlement will belong to.
    :return: An inflated settlement object.
    """
    split_setl: List[str] = setl_str.split(";")
    name: str = split_setl[0]
    loc: (int, int) = int(split_setl[1].split("-")[0]), int(split_setl[1].split("-")[1])
    improvements: List[Improvement] = []
    if split_setl[2]:
        for imp_name in split_setl[2].split("$"):
            improvements.append(inflate_improvement(imp_name))
    setl_quads: List[Quad] = []
    for quad_loc in split_setl[3].split(","):
        setl_quads.append(quads[int(quad_loc.split("-")[1])][int(quad_loc.split("-")[0])])
    resources: ResourceCollection = inflate_resource_collection(split_setl[4])
    garrison: List[Unit] = []
    if split_setl[5]:
        for unit in split_setl[5].split(","):
            garrison.append(inflate_unit(unit, garrisoned=True, faction=faction))
    strength: float = float(split_setl[6])
    max_strength: float = float(split_setl[7])
    satisfaction: float = float(split_setl[8])
    current_work: Optional[Construction] = None
    if split_setl[9]:
        work_details: List[str] = split_setl[9].split("%")
        match work_details[0]:
            case "Improvement":
                current_work = Construction(get_improvement(work_details[1]), float(work_details[2]))
            case "Project":
                current_work = Construction(get_project(work_details[1]), float(work_details[2]))
            case "UnitPlan":
                current_work = Construction(get_unit_plan(work_details[1], faction, resources), float(work_details[2]))
    level: int = int(split_setl[10])
    harvest_reserves: float = float(split_setl[11])
    harvest_status: HarvestStatus = HarvestStatus(split_setl[12])
    economic_status: EconomicStatus = EconomicStatus(split_setl[13])
    # We need to do string comparisons against "True" here because if we just do 'is True' here instead, then everything
    # will evaluate to True. This is because any string that isn't empty is considered to be 'True'.
    produced_settler: bool = split_setl[14] == "True"
    besieged: bool = split_setl[15] == "True"
    return Settlement(name, loc, improvements, setl_quads, resources, garrison, strength, max_strength, satisfaction,
                      current_work, level, harvest_reserves, harvest_status, economic_status, produced_settler,
                      besieged)


def inflate_player(player_str: str, quads: List[List[Quad]]) -> Player:
    """
    Inflate the given minified player string into a player object.
    :param player_str: The minified player to inflate.
    :param quads: The quads on the board.
    :return: An inflated player object.
    """
    split_pl: List[str] = player_str.split("~")
    name: str = split_pl[0]
    faction: Faction = Faction(split_pl[1])
    wealth: float = float(split_pl[2])
    settlements: List[Settlement] = []
    if split_pl[3]:
        for mini_setl in split_pl[3].split("!"):
            settlements.append(inflate_settlement(mini_setl, quads, faction))
    units: List[Unit] = []
    if split_pl[4]:
        for mini_unit in split_pl[4].split("&"):
            units.append(inflate_unit(mini_unit, garrisoned=False, faction=faction))
    blessings: List[Blessing] = []
    if split_pl[5]:
        for bls in split_pl[5].split(","):
            blessings.append(get_blessing(bls, faction))
    resources: ResourceCollection = inflate_resource_collection(split_pl[6])
    imminent_victories: Set[VictoryType] = set()
    if split_pl[7]:
        for vic in split_pl[7].split(","):
            imminent_victories.add(VictoryType(vic))
    ongoing_blessing: Optional[OngoingBlessing] = None
    if split_pl[8]:
        ongoing_blessing = OngoingBlessing(get_blessing(split_pl[8].split(">")[0], faction),
                                           float(split_pl[8].split(">")[1]))
    ai_playstyle: Optional[AIPlaystyle] = None
    if split_pl[9]:
        ai_playstyle = AIPlaystyle(AttackPlaystyle(split_pl[9].split("-")[0]),
                                   ExpansionPlaystyle(split_pl[9].split("-")[1]))
    jubilation_ctr: int = int(split_pl[10])
    accumulated_wealth: float = float(split_pl[11])
    # We need to do a string comparison against "True" here because if we just do 'is True' here instead, then
    # everything will evaluate to True. This is because any string that isn't empty is considered to be 'True'.
    eliminated: bool = split_pl[12] == "True"
    return Player(name, faction, FACTION_COLOURS[faction], wealth, settlements, units, blessings, resources, set(),
                  imminent_victories, ongoing_blessing, ai_playstyle, jubilation_ctr, accumulated_wealth, eliminated)


def inflate_quads_seen(qs_str: str) -> Set[Tuple[int, int]]:
    """
    Inflate the given minified seen quads string into a set of tuples representing the locations of each seen quad.
    :param qs_str: The minified set of seen quads to inflate.
    :return: An inflated set of seen quad location tuples.
    """
    quads_seen: Set[Tuple[int, int]] = set()
    for quad_loc in qs_str.split(","):
        quads_seen.add((int(quad_loc.split("-")[0]), int(quad_loc.split("-")[1])))
    return quads_seen


def inflate_heathens(heathens_str: str) -> List[Heathen]:
    """
    Inflate the given minified heathens string into a list of heathen objects.
    :param heathens_str: The minified heathens to inflate.
    :return: An inflated list of heathen objects.
    """
    heathens: List[Heathen] = []
    mini_heathens: List[str] = heathens_str.split(",")[:-1]
    for heathen in mini_heathens:
        split_heathen: List[str] = heathen.split("*")
        health: float = float(split_heathen[0])
        remaining_stamina: int = int(split_heathen[1])
        location: (int, int) = int(split_heathen[2].split("-")[0]), int(split_heathen[2].split("-")[1])
        # We don't use inflate_unit_plan() here because that will attempt to retrieve the non-heathen plan for this
        # unit, which of course does not exist.
        unit_plan: UnitPlan = UnitPlan(float(split_heathen[3]), float(split_heathen[4]), int(split_heathen[5]),
                                       split_heathen[6], None, 0.0)
        # We need to do a string comparison against "True" here because if we just do 'is True' here instead, then
        # everything will evaluate to True. This is because any string that isn't empty is considered to be 'True'.
        has_attacked: bool = split_heathen[7] == "True"
        heathens.append(Heathen(health, remaining_stamina, location, unit_plan, has_attacked))
    return heathens
