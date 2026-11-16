"""Menu compatibility shim: the chapter hub imports `PrehistoricCaveView`
from `scenes.prehistoric_view`, while the real implementation lives in
`scenes.prehistoric_explore_view` as `PrehistoricExploreView`. Re-export it
under the name the hub expects, with a safe placeholder fallback.
"""
try:
    from scenes.prehistoric_explore_view import PrehistoricExploreView as PrehistoricCaveView
except Exception:  # pragma: no cover - only if the real scene is unavailable
    import arcade
    from core.base_view import BaseGameView

    class PrehistoricCaveView(BaseGameView):
        def on_draw(self):
            self.clear((10, 10, 14))
            self.use_game_camera()
            arcade.draw_text("Prehistory — coming soon", 640, 360,
                             (220, 200, 170), 20, anchor_x="center", bold=True)

        def on_key_press(self, key, modifiers):
            if key in (arcade.key.ENTER, arcade.key.ESCAPE):
                from scenes.menu_view import MenuView
                self.window.show_view(MenuView())
