import pyxel


def on_update():
    if pyxel.btnp(pyxel.KEY_ESCAPE):
        pyxel.quit()


def draw():
    pyxel.cls(0)
    pyxel.rect(10, 10, 20, 20, 11)


class Game:
    def __init__(self):
        pyxel.init(600, 400)
        pyxel.run(on_update, draw)
