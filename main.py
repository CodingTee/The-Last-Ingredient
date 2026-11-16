"""Main entry point for The Last Ingredient.
Launches the full interactive 4-era narrative cooking experience.
"""
import sys
import os

# Ensure package root is in Python module search path
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import arcade
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, START_FULLSCREEN
from scenes.menu_view import MenuView
from core.base_view import setup_window_ime, configure_window_for_recording


def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=False, fullscreen=START_FULLSCREEN)
    setup_window_ime(window)
    configure_window_for_recording(window)
    if START_FULLSCREEN:
        window.set_fullscreen(True)
        configure_window_for_recording(window)
    menu_view = MenuView()
    window.show_view(menu_view)
    arcade.run()



if __name__ == "__main__":
    main()
