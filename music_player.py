import random
import typing
from time import sleep

import vlc


class MusicPlayer:
    def __init__(self):
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
        self.menu_player.audio_set_volume(70)
        self.menu_player.play()

    def stop_menu_music(self):
        for vol in range(70, 0, -10):
            sleep(0.08)
            self.menu_player.audio_set_volume(vol)
        self.menu_player.pause()

    def play_game_music(self):
        self.game_players[self.current_idx].audio_set_volume(70)
        self.game_players[self.current_idx].set_position(0)
        self.game_players[self.current_idx].play()

    def stop_game_music(self):
        for vol in range(70, 0, -10):
            sleep(0.08)
            self.game_players[self.current_idx].audio_set_volume(vol)
        self.game_players[self.current_idx].pause()

    def next_song(self):
        self.game_players[self.current_idx].pause()
        if self.current_idx < len(self.game_players) - 1:
            self.current_idx += 1
        else:
            self.current_idx = 0
        self.play_game_music()

    def is_playing(self) -> bool:
        return any([mp.is_playing() for mp in self.game_players])
