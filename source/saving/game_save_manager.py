from __future__ import annotations

import json
import os
import pathlib
import time
from datetime import datetime
from itertools import chain
from json import JSONDecodeError
from typing import TYPE_CHECKING, Optional, List, Dict, Tuple

import pyxel
from platformdirs import user_data_dir

from source.display.board import Board
from source.foundation.catalogue import get_blessing, get_project, get_unit_plan, get_improvement, ACHIEVEMENTS, Namer
from source.foundation.models import Heathen, UnitPlan, VictoryType, Faction, Statistics, Achievement, GameConfig, \
    Quad, HarvestStatus, EconomicStatus
from source.game_management.game_controller import GameController
if TYPE_CHECKING:
    from source.game_management.game_state import GameState
from source.saving.save_encoder import SaveEncoder, ObjectConverter
from source.saving.save_migrator import migrate_unit, migrate_player, migrate_climatic_effects, \
    migrate_quad, migrate_settlement, migrate_game_config, migrate_game_version
from source.util.calculator import clamp

# The prefix attached to save files created by the autosave feature.
AUTOSAVE_PREFIX = "auto"
# The directory where save files are created and loaded from. This is a different directory depending on the operating
# system the game is being run on. For example, on macOS, this will resolve to ~/Library/Application Support/microcosm.
# Similarly, on Linux, it will resolve to ~/.local/share/microcosm. For more details, refer to the platformdirs
# documentation.
SAVES_DIR = user_data_dir("microcosm", "microcosm")


def init_app_data():
    """
    Initialise the user application data directories for use.
    """
    # If the directory for saves and statistics does not exist, create it, as well as any required parent directories.
    if not os.path.exists(SAVES_DIR):
        pathlib.Path(SAVES_DIR).mkdir(parents=True, exist_ok=True)


def save_game(game_state: GameState, auto: bool = False):
    """
    Saves the current game with the current timestamp as the file name.
    :param game_state: The state of the game to save.
    :param auto: Whether the save is an autosave.
    """
    # Only maintain 3 autosaves at a time, delete the oldest if we already have 3 before saving the next.
    if auto and len(autosaves := list(filter(lambda fn: fn.startswith(AUTOSAVE_PREFIX), os.listdir(SAVES_DIR)))) == 3:
        autosaves.sort()
        os.remove(os.path.join(SAVES_DIR, autosaves[0]))
    # The ':' characters in the datestring must be replaced to conform with Windows files supported characters.
    sanitised_timestamp = datetime.now().isoformat(timespec='seconds').replace(':', '.')
    save_name = os.path.join(SAVES_DIR, f"{AUTOSAVE_PREFIX if auto else ''}save-{sanitised_timestamp}.json")
    with open(save_name, "w", encoding="utf-8") as save_file:
        # We use chain.from_iterable() here because the quads array is 2D.
        save = {
            "quads": list(chain.from_iterable(game_state.board.quads)),
            "players": game_state.players,
            "heathens": game_state.heathens,
            "turn": game_state.turn,
            "cfg": game_state.board.game_config,
            "night_status": {"until": game_state.until_night, "remaining": game_state.nighttime_left},
            "game_version": game_state.game_version
        }
        # Note that we use the SaveEncoder here for custom encoding for some classes.
        save_file.write(json.dumps(save, cls=SaveEncoder))
    save_file.close()


def save_stats_achievements(game_state: GameState,
                            playtime: float = 0,
                            increment_turn: bool = True,
                            victory_to_add: Optional[VictoryType] = None,
                            increment_defeats: bool = False,
                            faction_to_add: Optional[Faction] = None) -> List[Achievement]:
    """
    Saves the supplied statistics to the statistics JSON file. Additionally, check if any achievements have been
    obtained. All parameters have default values so that they may be supplied at different times.
    :param game_state: The current game state object.
    :param playtime: The elapsed time since the last turn was ended.
    :param increment_turn: Whether a turn was just ended.
    :param victory_to_add: A victory to log, if one was achieved.
    :param increment_defeats: Whether the player just lost a game.
    :param faction_to_add: A chosen faction to log, if the player is starting a new game.
    :return: Any new achievements that have been obtained by the player.
    """
    playtime_to_write: float = playtime
    existing_turns: int = 0
    existing_victories: Dict[VictoryType, int] = {}
    existing_defeats: int = 0
    existing_factions: Dict[Faction, int] = {}
    existing_achievements: List[str] = []
    new_achievements: List[Achievement] = []

    stats_file_name = os.path.join(SAVES_DIR, "statistics.json")
    # If the player already has statistics and achievements, get those to add our new ones to.
    if os.path.isfile(stats_file_name):
        with open(stats_file_name, "r", encoding="utf-8") as stats_file:
            stats_json = json.loads(stats_file.read())
            playtime_to_write += stats_json["playtime"]
            existing_turns = stats_json["turns_played"]
            existing_victories = stats_json["victories"]
            existing_defeats = stats_json["defeats"]
            existing_factions = stats_json["factions"]
            # Achievements were introduced after the initial statistics, so we have to make sure they are present.
            existing_achievements = stats_json["achievements"] if "achievements" in stats_json else []

    turns_to_write = existing_turns + 1 if increment_turn else existing_turns
    defeats_to_write = existing_defeats + 1 if increment_defeats else existing_defeats
    achievements_to_write = existing_achievements

    victories_to_write = existing_victories
    if victory_to_add:
        # If the player has achieved this victory before, increment it, otherwise just set it to 1.
        if victory_to_add in existing_victories:
            existing_victories[victory_to_add] = existing_victories[victory_to_add] + 1
        else:
            existing_victories[victory_to_add] = 1

        # Check if any achievements have been obtained that can only be verified immediately after a player victory.
        # Note that we don't need to supply a real Statistics object for this, since all post-victory achievements only
        # require the game state to be verified.
        for ach in ACHIEVEMENTS:
            if ach.name not in achievements_to_write and ach.post_victory and \
                    ach.verification_fn(game_state, Statistics()):
                achievements_to_write.append(ach.name)
                new_achievements.append(ach)

    factions_to_write = existing_factions
    if faction_to_add:
        # If the player has used this faction before, increment it, otherwise just set it to 1.
        if faction_to_add in existing_factions:
            existing_factions[faction_to_add] = existing_factions[faction_to_add] + 1
        else:
            existing_factions[faction_to_add] = 1

    # All other achievements can be checked on every save, with the real Statistics. Note that we need to ensure that
    # the player objects for the game have been initialised. This is because player statistics are updated with faction
    # usage when starting a new game, and this occurs prior to the players being initialised.
    if game_state.players:
        for ach in ACHIEVEMENTS:
            if ach.name not in achievements_to_write and not ach.post_victory and \
                    ach.verification_fn(game_state, Statistics(playtime_to_write, turns_to_write, victories_to_write,
                                                               defeats_to_write, factions_to_write)):
                achievements_to_write.append(ach.name)
                new_achievements.append(ach)

    # Write the newly-updated statistics to the file.
    with open(stats_file_name, "w", encoding="utf-8") as stats_file:
        stats = {
            "playtime": playtime_to_write,
            "turns_played": turns_to_write,
            "victories": victories_to_write,
            "defeats": defeats_to_write,
            "factions": factions_to_write,
            "achievements": achievements_to_write
        }
        stats_file.write(json.dumps(stats))
    stats_file.close()

    return new_achievements


def get_stats() -> Statistics:
    """
    Retrieve the player's statistics from the statistics JSON file, if they have one.
    :return: An object containing the player's statistics.
    """
    stats_file_name = os.path.join(SAVES_DIR, "statistics.json")
    if os.path.isfile(stats_file_name):
        with open(stats_file_name, "r", encoding="utf-8") as stats_file:
            stats_json = json.loads(stats_file.read())
            return Statistics(**stats_json)
    else:
        return Statistics(0, 0, {}, 0, {}, set())


def load_save_file(game_state: GameState,
                   namer: Namer,
                   save_name: str) -> Tuple[GameConfig, List[List[Quad]]]:
    """
    Load the save file with the given name into the supplied game state and namer objects.
    :param game_state: The game state to load the save data into.
    :param namer: The namer to update with settlement details from the saved game.
    :param save_name: The name of the save file to load.
    :return: A tuple containing the game configuration and the quads on the board.
    """
    game_cfg: GameConfig
    quads: List[List[Quad]]
    with open(os.path.join(SAVES_DIR, save_name), "r", encoding="utf-8") as save_file:
        # Use a custom object hook when loading the JSON so that the resulting objects have attribute access.
        save = json.loads(save_file.read(), object_hook=ObjectConverter)
        # Load in the quads.
        quads = [[None] * 100 for _ in range(90)]
        for i in range(90):
            for j in range(100):
                quads[i][j] = migrate_quad(save.quads[i * 100 + j], (j, i))
        migrate_game_version(game_state, save)
        game_state.players = save.players
        for p in game_state.players:
            # The list of tuples that is quads_seen needs special loading, as do a few other of the same type,
            # because tuples do not exist in JSON, so they are represented as arrays, which will clearly not work.
            for i in range(len(p.quads_seen)):
                p.quads_seen[i] = (p.quads_seen[i][0], p.quads_seen[i][1])
            p.quads_seen = set(p.quads_seen)
            for idx, u in enumerate(p.units):
                # We can do a direct conversion to Unit and UnitPlan objects for units.
                p.units[idx] = migrate_unit(u, p.faction)
            for s in p.settlements:
                # Make sure we remove the settlement's name so that we don't get duplicates.
                namer.remove_settlement_name(s.name, s.quads[0].biome)
                # Another tuple-array fix.
                s.location = (s.location[0], s.location[1])
                if s.current_work is not None:
                    # Get the actual Improvement, Project, or UnitPlan objects for the current work. We use
                    # hasattr() because improvements have an effect where projects do not, and projects have
                    # a type where unit plans do not.
                    if hasattr(s.current_work.construction, "effect"):
                        s.current_work.construction = get_improvement(s.current_work.construction.name)
                    elif hasattr(s.current_work.construction, "type"):
                        s.current_work.construction = get_project(s.current_work.construction.name)
                    else:
                        s.current_work.construction = \
                            get_unit_plan(s.current_work.construction.name, p.faction, s.resources)
                for idx, imp in enumerate(s.improvements):
                    # Do another direct conversion for improvements.
                    s.improvements[idx] = get_improvement(imp.name)
                # Also convert all units in garrisons to Unit objects.
                for idx, u in enumerate(s.garrison):
                    s.garrison[idx] = migrate_unit(u, p.faction)
                s.harvest_status = HarvestStatus(s.harvest_status)
                s.economic_status = EconomicStatus(s.economic_status)
                # We also need to link the quads for each settlement to the quads on the actual board so that changes
                # made to the quad on the board, e.g. investigating a relic that occupies the same quad as a settlement,
                # are reflected in the settlement's quad as well.
                for idx, q in enumerate(s.quads):
                    s.quads[idx] = quads[q.location[1]][q.location[0]]
                migrate_settlement(s)
            # We also do direct conversions to Blessing objects for the ongoing one, if there is one,
            # as well as any previously-completed ones.
            if p.ongoing_blessing:
                p.ongoing_blessing.blessing = get_blessing(p.ongoing_blessing.blessing.name, p.faction)
            for idx, bls in enumerate(p.blessings):
                p.blessings[idx] = get_blessing(bls.name, p.faction)
            imminent_victories: List[VictoryType] = []
            for iv in p.imminent_victories:
                imminent_victories.append(VictoryType(iv))
            p.imminent_victories = set(imminent_victories)
            migrate_player(p)

        game_state.heathens = []
        for h in save.heathens:
            # Do another direct conversion for the heathens.
            game_state.heathens.append(Heathen(float(h.health), h.remaining_stamina, (h.location[0], h.location[1]),
                                               UnitPlan(float(h.plan.power), float(h.plan.max_health),
                                                        h.plan.total_stamina, h.plan.name, None, 0.0),
                                               h.has_attacked))

        game_state.turn = save.turn
        migrate_climatic_effects(game_state, save)
        game_cfg = migrate_game_config(save.cfg)
    save_file.close()
    return game_cfg, quads


def load_game(game_state: GameState, game_controller: GameController):
    """
    Loads the game with the given index from the saves/ directory.
    :param game_controller: The current GameController object.
    :param game_state: The current GameState object.
    """
    # Reset the namer so that we have our original set of names again.
    game_controller.namer.reset()
    # Sort and reverse both the autosaves and manual saves, remembering that the (up to) 3 autosaves will be
    # displayed first in the list.
    autosaves = list(filter(lambda file_name: file_name.startswith(AUTOSAVE_PREFIX), os.listdir(SAVES_DIR)))
    saves = list(
        filter(lambda file_name: file_name.startswith("save-"),
               [f for f in os.listdir(SAVES_DIR) if not f.startswith('.')]))
    autosaves.sort(reverse=True)
    saves.sort(reverse=True)
    all_saves = autosaves + saves

    try:
        game_cfg, quads = load_save_file(game_state, game_controller.namer, all_saves[game_controller.menu.save_idx])
        # Now do all the same logic we do when starting a game.
        pyxel.mouse(visible=True)
        game_controller.last_turn_time = time.time()
        # Because we only load single-player games using this function, we know that the player will be the first player
        # in the players list in game state.
        game_state.player_idx = 0
        game_state.located_player_idx = True
        game_state.game_started = True
        game_state.on_menu = False
        game_state.board = Board(game_cfg, game_controller.namer, quads)
        game_controller.move_maker.board_ref = game_state.board
        # Initialise the map position to the player's first settlement.
        game_state.map_pos = (clamp(game_state.players[0].settlements[0].location[0] - 12, -1, 77),
                              clamp(game_state.players[0].settlements[0].location[1] - 11, -1, 69))
        game_state.board.overlay.current_player = game_state.players[0]
        game_state.board.overlay.total_settlement_count = sum(len(p.settlements) for p in game_state.players)
        game_controller.music_player.stop_menu_music()
        game_controller.music_player.play_game_music()
    except (JSONDecodeError, AttributeError, KeyError, StopIteration, ValueError):
        game_controller.menu.load_failed = True


def get_saves() -> List[str]:
    """
    Get the prettified file names of each save file in the saves/ directory.
    :return: The prettified file names of the available save files.
    """
    save_names: List[str] = []
    autosaves = list(filter(lambda file_name: file_name.startswith(AUTOSAVE_PREFIX), os.listdir(SAVES_DIR)))
    saves = list(filter(lambda file_name: file_name.startswith("save-"),
                        [f for f in os.listdir(SAVES_DIR) if not f.startswith('.')]))
    autosaves.sort(reverse=True)
    saves.sort(reverse=True)
    for f in autosaves:
        save_names.append(f[9:-5].replace("T", " ") + " (auto)")
    for f in saves:
        # Just show the date and time.
        save_names.append(f[5:-5].replace("T", " "))
    return save_names
