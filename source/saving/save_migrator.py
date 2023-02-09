from source.foundation.catalogue import get_blessing
from source.foundation.models import UnitPlan

"""
The following migrations have occurred during Microcosm's development:

v1.1
- AI players had their playstyle expanded to not only include attacking, but also expansion.
  This is migrated by mapping directly to the attacking attribute, and setting the expansion attribute to neutral.
- Relics were added, adding the is_relic attribute to Quads. This is migrated by setting all quads without the attribute
  to False.
- Imminent victories were added for players, telling players when they or others are close to winning the game. This can
  be migrated by simpling setting them to an empty set if the attribute is not present, as it will be populated next
  turn.
- The eliminated attribute was added for players, which can be determined by checking the number of settlements the
  player has.

v1.2
- Climatic effects were added to the game as a part of its configuration. This can be mapped to False.

v2.0
- Factions were added for players. As it would be difficult for players to choose, their faction can be determined from
  the colour they chose.
- The player faction was also added to the game configuration, which can be determined in the same way as above.

v2.2
- Healing units were added. All existing unit plans can be mapped to False for the heals attribute.
- The has_attacked attribute was changed to has_acted for units, and this can be directly mapped across.
- The sieging attribute for units was changed to besieging, and this can also be mapped directly.
- The under_siege_by attribute keeping track of the optional unit besieging the settlement was changed to a simple
  boolean attribute called besieged. Migration can occur by mapping to True if the value is not None.
"""


def migrate_unit_plan(unit_plan) -> UnitPlan:
    plan_prereq = None if unit_plan.prereq is None else get_blessing(unit_plan.prereq.name)
    will_heal: bool = unit_plan.heals if hasattr(unit_plan, "heals") else False

    return UnitPlan(unit_plan.power, unit_plan.max_health, unit_plan.total_stamina,
                    unit_plan.name, plan_prereq, unit_plan.cost, unit_plan.can_settle,
                    will_heal)
