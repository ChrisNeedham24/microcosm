from math import ceil
from typing import Optional

import pyxel

from source.display.display_utils import draw_paragraph
from source.foundation.models import Scene, TextLine


class Dialogue:
    def __init__(self):
        self.current_scene: Optional[Scene] = None
        self.waiting_time_bank = 0

    def draw(self):
        if self.current_scene:
            pyxel.cls(0)
            line: TextLine = self.current_scene.lines[self.current_scene.current_idx]
            if line.background_idx is not None:
                background_path: str = f"resources/introbg{ceil((line.background_idx + 1) / 3)}.pyxres"
                pyxel.load(background_path)
                pyxel.blt(0, 0, line.background_idx % 3, 0, 0, 200, 200)
            pyxel.rectb(20, 140, 160, 50, pyxel.COLOR_WHITE)
            pyxel.rect(21, 141, 158, 48, pyxel.COLOR_BLACK)
            draw_paragraph(25, 145, line.get_current_content(), 35)
            if line.speaker:
                pyxel.rectb(20, 125, 60, 16, pyxel.COLOR_WHITE)
                pyxel.rect(21, 126, 58, 12, pyxel.COLOR_BLACK)
                pyxel.text(25, 130, line.speaker.name, line.speaker.colour)
            if line.finished():
                pyxel.load("resources/sprites.pyxres")
                pyxel.blt(170 + 4 * (self.waiting_time_bank - 0.5), 176, 0, 0, 148, 5, 8)

    def update(self, elapsed_time: float):
        if self.current_scene:
            self.current_scene.update(elapsed_time)
            if self.current_scene.lines[self.current_scene.current_idx].finished():
                self.waiting_time_bank += elapsed_time
                if self.waiting_time_bank >= 1:
                    self.waiting_time_bank = 0

    def idle(self) -> bool:
        return self.current_scene.lines[self.current_scene.current_idx].finished()
