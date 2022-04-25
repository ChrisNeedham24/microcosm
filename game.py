import pyxel

from menu import Menu


class Game:
    def __init__(self):
        pyxel.init(100, 100)

        self.menu = Menu()

        pyxel.run(self.on_update, self.draw)

    def on_update(self):
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()

    def draw(self):
        self.menu.draw()
