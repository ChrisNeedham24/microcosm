import pyxel

from models import Settlement, Player


class Overlay:
    def draw(self, turn: int):
        pyxel.rectb(10, 10, 80, 72, pyxel.COLOR_WHITE)
        pyxel.rect(11, 11, 78, 70, pyxel.COLOR_BLACK)
        pyxel.text(15, 15, "Turn", pyxel.COLOR_WHITE)
        pyxel.text(75, 15, str(turn), pyxel.COLOR_GREEN)

    def draw_settlement(self, settlement: Settlement, player: Player):
        pyxel.rectb(6, 5, 88, 10, pyxel.COLOR_WHITE)
        pyxel.rect(7, 6, 86, 8, pyxel.COLOR_BLACK)
        pyxel.text(10, 7, settlement.name, player.colour)
        pyxel.text(66, 7, f"{round(sum(quad.wealth for quad in settlement.quads))}", pyxel.COLOR_YELLOW)
        pyxel.text(72, 7, f"{round(sum(quad.harvest for quad in settlement.quads))}", pyxel.COLOR_GREEN)
        pyxel.text(78, 7, f"{round(sum(quad.zeal for quad in settlement.quads))}", pyxel.COLOR_RED)
        pyxel.text(84, 7, f"{round(sum(quad.fortune for quad in settlement.quads))}", pyxel.COLOR_PURPLE)
