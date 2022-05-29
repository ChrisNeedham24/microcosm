import random
import typing
from time import sleep

import vlc


class MusicPlayer:
    """
    The class responsible for playing the music in-game.
    """
    def __init__(self):
        """
        Load in the menu and background in-game music, shuffling them and setting their volumes.
        """
        self.menu_player: vlc.MediaPlayer = vlc.MediaPlayer("resources/audio/menu.aiff")
        self.menu_player.audio_set_volume(70)
        random.seed()
        self.game_players: typing.List[vlc.MediaPlayer] = \
            [vlc.MediaPlayer(f"resources/audio/background{i}.aiff") for i in range(1, 9)]
        random.shuffle(self.game_players)
        for gp in self.game_players:
            gp.audio_set_volume(70)
        self.current_idx = 0

    def play_menu_music(self):
        """
        Play the menu music, setting its volume first.
        """
        self.menu_player.audio_set_volume(70)
        self.menu_player.play()

    def stop_menu_music(self):
        """
        Stop the menu music, fading it out first.
        """
        for vol in range(70, 0, -10):
            sleep(0.08)
            self.menu_player.audio_set_volume(vol)
        self.menu_player.pause()  # Note that we pause, so the music will resume when the player returns to the menu.

    def play_game_music(self):
        """
        Play the current in-game music, setting its volume and restarting it first.
        """
        self.game_players[self.current_idx].audio_set_volume(70)
        self.game_players[self.current_idx].set_position(0)
        self.game_players[self.current_idx].play()

    def stop_game_music(self):
        """
        Stop the in-game music, fading it out first.
        """
        for vol in range(70, 0, -10):
            sleep(0.08)
            self.game_players[self.current_idx].audio_set_volume(vol)
        self.game_players[self.current_idx].pause()

    def next_song(self):
        """
        Skip to the next in-game song.
        """
        self.game_players[self.current_idx].pause()
        if self.current_idx < len(self.game_players) - 1:
            self.current_idx += 1
        else:
            self.current_idx = 0
        self.play_game_music()

    def is_playing(self) -> bool:
        """
        Returns whether any in-game song is playing. Used to skip to the next track if the current one has finished.
        :return: Whether an in-game song is playing.
        """
        return any(mp.is_playing() for mp in self.game_players)
