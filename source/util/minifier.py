from typing import List, Optional

from source.foundation.catalogue import get_unit_plan, get_improvement
from source.foundation.models import Quad, Biome, ResourceCollection, Player, Settlement, Unit, UnitPlan, Improvement


def minify_resource_collection(rc: ResourceCollection) -> str:
    # TODO this may increase the packet size too much
    return f"{rc.ore}-{rc.timber}-{rc.magma}-{rc.aurora}-{rc.bloodstone}-{rc.obsidian}-{rc.sunstone}-{rc.aquamarine}"


def minify_quad(quad: Quad) -> str:
    quad_str: str = f"{quad.biome.value[0]}{quad.wealth}{quad.harvest}{quad.zeal}{quad.fortune}"
    if quad.resource:
        quad_str += minify_resource_collection(quad.resource)
    if quad.is_relic:
        quad_str += "ir"
    return quad_str


def minify_unit_plan(unit_plan: UnitPlan) -> str:
    return f"{unit_plan.power}/{unit_plan.max_health}/{unit_plan.total_stamina}/{unit_plan.name}"


def minify_unit(unit: Unit) -> str:
    unit_str: str = f"{unit.health}/{unit.remaining_stamina}/{unit.location[0]}-{unit.location[1]}/"
    unit_str += minify_unit_plan(unit.plan) + "/"
    unit_str += f"{unit.has_acted}/{unit.besieging}"
    return f"{len(unit_str)}:{unit_str}"


def minify_settlement(settlement: Settlement) -> str:
    settlement_str: str = f"{settlement.name}/{settlement.location[0]}-{settlement.location[1]}/"
    for improvement in settlement.improvements:
        settlement_str += improvement.name + "-"
    settlement_str += "/"
    for quad in settlement.quads:
        settlement_str += f"{quad.location[0]}-{quad.location[1]},"
    settlement_str += "/"
    settlement_str += minify_resource_collection(settlement.resources) + "/"
    units_str: str = ""
    for unit in settlement.garrison:
        units_str += minify_unit(unit) + ","
    settlement_str += f"{len(units_str)}:{units_str}/"
    settlement_str += f"{settlement.strength}/{settlement.max_strength}/{settlement.satisfaction}/"
    if settlement.current_work:
        settlement_str += f"{settlement.current_work.construction.name}-{settlement.current_work.zeal_consumed}"
    settlement_str += "/"
    settlement_str += (f"{settlement.level}/{settlement.harvest_reserves}/"
                       f"{settlement.harvest_status}/{settlement.economic_status}/"
                       f"{settlement.produced_settler}/{settlement.besieged}")
    return settlement_str


def minify_player(player: Player) -> str:
    player_str: str = f"{player.name}/{player.faction}/{player.wealth}/"
    return player_str


def inflate_resource_collection(rc_str: str) -> ResourceCollection:
    return ResourceCollection(*[int(res) for res in rc_str.split("-")])


def inflate_quad(quad_str: str, location: (int, int)) -> Quad:
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


def inflate_unit_plan(up_str: str) -> UnitPlan:
    split_up: List[str] = up_str.split("/")
    unit_plan: UnitPlan = get_unit_plan(split_up[-1])
    unit_plan.power = split_up[0]
    unit_plan.max_health = split_up[1]
    unit_plan.total_stamina = split_up[2]
    return unit_plan


def inflate_unit(unit_str: str, garrisoned: bool) -> Unit:
    split_unit: List[str] = unit_str.split("/")
    unit_loc: (int, int) = tuple(split_unit[2].split("-"))
    unit_plan_str: str = "".join(split_unit[3:7])
    return Unit(float(split_unit[0]), int(split_unit[1]), unit_loc, garrisoned, inflate_unit_plan(unit_plan_str),
                bool(split_unit[7]), bool(split_unit[8]))


def inflate_settlement(setl_str: str, quads: List[List[Quad]]) -> Settlement:
    split_setl: List[str] = setl_str.split("/")
    cursor: int = 0
    name: str = split_setl[0]
    cursor += len(name)
    loc: (int, int) = tuple(split_setl[1].split("-"))
    cursor += len(split_setl[1])
    improvements: List[Improvement] = []
    for imp_name in split_setl[2].split("-")[:-1]:
        improvements.append(get_improvement(imp_name))
    cursor += len(split_setl[2])
    quads: List[Quad] = []
    for quad_loc in split_setl[3].split(",")[:-1]:
        quads.append(quads[int(quad_loc.split("-")[1])][int(quad_loc.split("-")[0])])
    cursor += len(split_setl[3])
    resources: ResourceCollection = inflate_resource_collection(split_setl[4])
    cursor += len(split_setl[4])
    garrison: List[Unit] = []
    units_length: int = int(split_setl[5][0])
    cursor += 2
    units_str: str = setl_str[cursor:cursor + units_length]
    for unit in units_str.split(",")[:-1]:
        garrison.append(inflate_unit(unit, garrisoned=True))
    cursor += units_length

    return Settlement()
