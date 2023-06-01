"""
To house some of the more complicated validation functions for achievements.
"""
from __future__ import annotations

import typing

from source.foundation.models import Statistics, Settlement

if typing.TYPE_CHECKING:
    from source.game_management.game_state import GameState


def verify_the_golden_quad(game_state: GameState, _: Statistics) -> bool:
    for setl in game_state.players[0].settlements:
        setl_yield = 0
        for quad in setl.quads:
            setl_yield += quad.wealth
            setl_yield += quad.harvest
            setl_yield += quad.zeal
            setl_yield += quad.fortune
        if setl_yield >= 19:
            return True
    return False


def verify_full_house(game_state: GameState, _: Statistics) -> bool:
    setl_siege_counts: typing.Dict[str, int] = {}
    all_setls: typing.List[Settlement] = []
    for player in game_state.players:
        all_setls.extend(player.settlements)

    for unit in game_state.players[0].units:
        if unit.besieging:
            for setl in all_setls:
                for quad in setl.quads:
                    if abs(unit.location[0] - quad.location[0]) == 1 or abs(unit.location[1] - quad.location[1]) == 1:
                        setl_siege_counts[setl.name] = \
                            setl_siege_counts[setl.name] + 1 if setl.name in setl_siege_counts else 1

    return max(setl_siege_counts.values()) >= 8 if setl_siege_counts else False


def verify_its_worth_it(game_state: GameState, _: Statistics) -> bool:
    for setl in game_state.players[0].settlements:
        for imp in setl.improvements:
            if imp.effect.satisfaction < 0:
                return True
    return False
