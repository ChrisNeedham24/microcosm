import pyxel

from menu import Menu
from resource_loader import ResourceLoader


class Game:
    def __init__(self):
        pyxel.init(100, 100)

        self.menu = Menu()
        self.on_menu = True
        self.resource_loader = ResourceLoader()

        # pyxel.play(0, 0, loop=True)

        pyxel.run(self.on_update, self.draw)

    def on_update(self):
        if pyxel.btnp(pyxel.KEY_ESCAPE):
            pyxel.quit()
        elif pyxel.btnp(pyxel.KEY_DOWN):
            self.menu.navigate(True)
        elif pyxel.btnp(pyxel.KEY_UP):
            self.menu.navigate(False)

    def draw(self):
        self.menu.draw()
