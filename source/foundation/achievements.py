"""
To house some of the more complicated validation functions for achievements.
"""
from __future__ import annotations

import typing

from source.foundation.models import Statistics, Settlement

if typing.TYPE_CHECKING:
    from source.game_management.game_state import GameState


def verify_full_house(game_state: GameState, _: Statistics) -> bool:
    """
    The verification method for the 'Full House' achievement.
    :param game_state: The current game state object.
    :param _: The current statistics, which are unused.
    :return: Whether the achievement's criteria have been met.
    """
    # Store which settlements in the game are under siege, and by how many units.
    setl_siege_counts: typing.Dict[str, int] = {}
    all_setls: typing.List[Settlement] = []
    for player in game_state.players:
        all_setls.extend(player.settlements)

    for unit in game_state.players[game_state.player_idx].units:
        if unit.besieging:
            for setl in all_setls:
                for quad in setl.quads:
                    # Associate the current besieging unit with a settlement under siege based on location.
                    if abs(unit.location[0] - quad.location[0]) <= 1 and abs(unit.location[1] - quad.location[1]) <= 1:
                        setl_siege_counts[setl.name] = \
                            setl_siege_counts[setl.name] + 1 if setl.name in setl_siege_counts else 1

    # If the player has eight or more units besieging another settlement, they have met the criterion for this
    # achievement.
    return max(setl_siege_counts.values()) >= 8 if setl_siege_counts else False


def verify_its_worth_it(game_state: GameState, _: Statistics) -> bool:
    """
    The verification method for the 'It's Worth It' achievement.
    :param game_state: The current game state object.
    :param _: The current statistics, which are unused.
    :return: Whether the achievement's criteria have been met.
    """
    # If the player has constructed an improvement in any of their settlements that reduces satisfaction, they have met
    # the criterion for this achievement.
    for setl in game_state.players[game_state.player_idx].settlements:
        for imp in setl.improvements:
            if imp.effect.satisfaction < 0:
                return True
    return False


def verify_the_third_x(game_state: GameState, _: Statistics) -> bool:
    """
    The verification method for the 'The Third X' achievement.
    :param game_state: The current game state object.
    :param _: The current statistics, which are unused.
    :return: Whether the achievement's criteria have been met.
    """
    # If the player has a settlement with at least four resources of any kind, they have met the criterion for this
    # achievement.
    for setl in game_state.players[game_state.player_idx].settlements:
        rs = setl.resources
        if rs.ore + rs.timber + rs.magma + rs.aurora + rs.bloodstone + rs.obsidian + rs.sunstone + rs.aquamarine >= 4:
            return True
    return False
