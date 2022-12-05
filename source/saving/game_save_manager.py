import json
import os
from datetime import datetime
from itertools import chain

import pyxel

from source.display.board import Board
from source.util.calculator import clamp
from source.foundation.catalogue import get_blessing, get_project, get_unit_plan, get_improvement
from source.game_management.game_controller import GameController
from source.game_management.game_state import GameState
from source.foundation.models import Biome, Heathen, UnitPlan, AttackPlaystyle, AIPlaystyle, Unit, ExpansionPlaystyle, \
    Faction
from source.saving.save_encoder import SaveEncoder, ObjectConverter

# The prefix attached to save files created by the autosave feature.
AUTOSAVE_PREFIX = "auto"
# The directory where save files are created and loaded from.
SAVES_DIR = "saves"


def save_game(game_state: GameState, auto: bool = False):
    """
    Saves the current game with the current timestamp as the file name.
    """
    # Only maintain 3 autosaves at a time, delete the oldest if we already have 3 before saving the next.
    if auto and len(
            autosaves := list(filter(lambda fn: fn.startswith(AUTOSAVE_PREFIX), os.listdir(SAVES_DIR)))) == 3:
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
            "night_status": {"until": game_state.until_night, "remaining": game_state.nighttime_left}
        }
        # Note that we use the SaveEncoder here for custom encoding for some classes.
        save_file.write(json.dumps(save, cls=SaveEncoder))
    save_file.close()


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
        filter(lambda file_name: not file_name == "README.md" and not file_name.startswith(AUTOSAVE_PREFIX),
               [f for f in os.listdir(SAVES_DIR) if not f.startswith('.')]))
    autosaves.sort()
    autosaves.reverse()
    saves.sort()
    saves.reverse()
    all_saves = autosaves + saves

    try:
        with open(os.path.join(SAVES_DIR, all_saves[game_controller.menu.save_idx]), "r",
                  encoding="utf-8") as save_file:
            # Use a custom object hook when loading the JSON so that the resulting objects have attribute access.
            save = json.loads(save_file.read(), object_hook=ObjectConverter)
            # Load in the quads.
            quads = [[None] * 100 for _ in range(90)]
            for i in range(90):
                for j in range(100):
                    quads[i][j] = save.quads[i * 100 + j]
                    # The biomes require special loading.
                    quads[i][j].biome = Biome[quads[i][j].biome]
            game_state.players = save.players
            # The list of tuples that is quads_seen needs special loading, as do a few other of the same type,
            # because tuples do not exist in JSON, so they are represented as arrays, which will clearly not work.
            for i in range(len(game_state.players[0].quads_seen)):
                game_state.players[0].quads_seen[i] = (
                    game_state.players[0].quads_seen[i][0], game_state.players[0].quads_seen[i][1])
            game_state.players[0].quads_seen = set(game_state.players[0].quads_seen)
            for p in game_state.players:
                for idx, u in enumerate(p.units):
                    # We can do a direct conversion to Unit and UnitPlan objects for units.
                    plan_prereq = None if u.plan.prereq is None else get_blessing(u.plan.prereq.name)
                    p.units[idx] = Unit(u.health, u.remaining_stamina, (u.location[0], u.location[1]), u.garrisoned,
                                        UnitPlan(u.plan.power, u.plan.max_health, u.plan.total_stamina,
                                                 u.plan.name, plan_prereq, u.plan.cost, u.plan.can_settle,
                                                 u.plan.heals),
                                        u.has_acted, u.besieging)
                for s in p.settlements:
                    # Make sure we remove the settlement's name so that we don't get duplicates.
                    game_controller.namer.remove_settlement_name(s.name, s.quads[0].biome)
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
                            s.current_work.construction = get_unit_plan(s.current_work.construction.name)
                    for idx, imp in enumerate(s.improvements):
                        # Do another direct conversion for improvements.
                        s.improvements[idx] = get_improvement(imp.name)
                    # Also convert all units in garrisons to Unit objects.
                    for idx, u in enumerate(s.garrison):
                        s.garrison[idx] = Unit(u.health, u.remaining_stamina, (u.location[0], u.location[1]),
                                               u.garrisoned, u.plan, u.has_acted, u.besieging)
                # We also do direct conversions to Blessing objects for the ongoing one, if there is one,
                # as well as any previously-completed ones.
                if p.ongoing_blessing:
                    p.ongoing_blessing.blessing = get_blessing(p.ongoing_blessing.blessing.name)
                for idx, bls in enumerate(p.blessings):
                    p.blessings[idx] = get_blessing(bls.name)
                if p.ai_playstyle is not None:
                    p.ai_playstyle = AIPlaystyle(AttackPlaystyle[p.ai_playstyle.attacking],
                                                 ExpansionPlaystyle[p.ai_playstyle.expansion])
                p.imminent_victories = set(p.imminent_victories)
                p.faction = Faction(p.faction)
            # For the AI players, we can just make quads_seen an empty set, as it's not used.
            for i in range(1, len(game_state.players)):
                game_state.players[i].quads_seen = set()

            game_state.heathens = []
            for h in save.heathens:
                # Do another direct conversion for the heathens.
                game_state.heathens.append(Heathen(h.health, h.remaining_stamina, (h.location[0], h.location[1]),
                                                   UnitPlan(h.plan.power, h.plan.max_health, 2, h.plan.name, None, 0),
                                                   h.has_attacked))

            game_state.turn = save.turn
            game_state.until_night = save.night_status.until
            game_state.nighttime_left = save.night_status.remaining
            game_cfg = save.cfg
        save_file.close()
        # Now do all the same logic we do when starting a game.
        pyxel.mouse(visible=True)
        game_state.game_started = True
        game_state.on_menu = False
        game_state.board = Board(game_cfg, game_controller.namer, quads)
        game_controller.move_maker.board_ref = game_state.board
        # Initialise the map position to the player's first settlement.
        game_state.map_pos = (clamp(game_state.players[0].settlements[0].location[0] - 12, -1, 77),
                              clamp(game_state.players[0].settlements[0].location[1] - 11, -1, 69))
        game_state.board.overlay.current_player = game_state.players[0]
        game_controller.music_player.stop_menu_music()
        game_controller.music_player.play_game_music()
    # pylint: disable=broad-except
    except Exception:
        game_controller.menu.load_failed = True


def get_saves(game_controller: GameController):
    """
    Get the prettified file names of each save file in the saves/ directory and pass them to the menu.
    """
    game_controller.menu.saves = []
    autosaves = list(filter(lambda file_name: file_name.startswith(AUTOSAVE_PREFIX), os.listdir(SAVES_DIR)))
    saves = list(
        filter(lambda file_name: not file_name == "README.md" and not file_name.startswith(AUTOSAVE_PREFIX),
               [f for f in os.listdir(SAVES_DIR) if not f.startswith('.')]))
    # Default to a fake option if there are no saves available.
    if len(autosaves) + len(saves) == 0:
        game_controller.menu.save_idx = -1
    else:
        autosaves.sort()
        autosaves.reverse()
        saves.sort()
        saves.reverse()
        for f in autosaves:
            game_controller.menu.saves.append(f[9:-5].replace("T", " ") + " (auto)")
        for f in saves:
            # Just show the date and time.
            game_controller.menu.saves.append(f[5:-5].replace("T", " "))
