"""Scene 0: Main Menu and Prologue Hub for The Last Ingredient."""
from textwrap import wrap

import arcade
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD, START_FULLSCREEN, ASSETS_DIR
from core.particles import SteamParticle
from core.achievements import get_all_unlocked_achievements
from core.audio import AudioManager
from core.base_view import BaseGameView


class MenuView(BaseGameView):

    def __init__(self):
        super().__init__()
        self.audio = AudioManager()
        art = ASSETS_DIR / "menu"
        self.background = arcade.load_texture(art / "kitchen.jpg")
        self.props = {
            name: arcade.load_texture(art / f"{name}.png")
            for name in ("bowl", "ring", "beast", "crown", "gear")
        }
        self.steam_particles = [
            SteamParticle(928, 315, spread=20, base_radius=6.0)
            for _ in range(10)
        ]
        self.buttons = [
            ("start", "Start Journey", 270, 389, 362, 57),
            ("story", "Story Synopsis", 270, 321, 362, 48),
            ("achievements", "Achievements", 270, 262, 362, 48),
            ("exit", "Exit Game", 270, 203, 362, 48),
        ]
        self.hovered_btn = None
        self.show_story_modal = False
        self.show_achievements_modal = False
        self.unlocked_achievements = set()

    def on_update(self, dt):
        for particle in self.steam_particles:
            particle.update(dt)

    def _draw_prop(self, name, x, y, width, angle=0):
        texture = self.props[name]
        height = width * texture.height / texture.width
        arcade.draw_texture_rect(texture, arcade.XYWH(x, y, width, height), angle=angle)

    def on_draw(self):
        self.clear(color=(19, 17, 17))

        # Cover the physical viewport at the texture's native aspect ratio.
        self.window.default_camera.use()
        width, height = self.window.get_size()
        texture = self.background
        scale = max(width / texture.width, height / texture.height)
        arcade.draw_texture_rect(
            texture,
            arcade.XYWH(width / 2, height / 2, texture.width * scale, texture.height * scale),
        )

        # Use a centered, uniformly scaled design area for props and text.
        self.use_game_camera()
        arcade.draw_ellipse_filled(947, 181, 345, 60, (17, 10, 8, 155))
        self._draw_prop("bowl", 937, 267, 344)
        for particle in self.steam_particles:
            particle.draw()
        arcade.draw_ellipse_filled(1147, 181, 72, 15, (33, 16, 8, 115))
        self._draw_prop("ring", 1151, 211, 84, 8)
        self._draw_prop("beast", 661, 191, 73, 15)
        self._draw_prop("crown", 724, 180, 73, 2)
        self._draw_prop("gear", 790, 163, 73, -12)

        cream = (253, 235, 200)
        serif = ("Georgia", "Times New Roman")
        arcade.draw_text("THE LAST", 85, 620, cream, 39, font_name=serif)
        arcade.draw_text("INGREDIENT", 83, 535, cream, 62, font_name=serif)
        arcade.draw_text("One Chance to Begin Again", 89, 480, (235, 193, 131), 22,
                         font_name=serif, italic=True)
        arcade.draw_line(89, 453, 450, 453, (196, 146, 82, 180), 1)

        for btn_id, label, x, y, width, height in self.buttons:
            active = self.hovered_btn == btn_id
            primary = btn_id == "start"
            rect = arcade.XYWH(x, y, width, height)
            fill = (149, 69, 42) if primary else (27, 24, 23, 228)
            if active:
                fill = (177, 87, 50) if primary else (69, 49, 37, 248)
            arcade.draw_rect_filled(rect, fill)
            border = (241, 198, 130) if active or primary else (136, 108, 79)
            arcade.draw_rect_outline(rect, border, 1)
            arcade.draw_text(label, x - width / 2 + 20, y, cream, 17,
                             anchor_y="center", bold=primary)
            if primary or active:
                arcade.draw_text("›", x + width / 2 - 22, y, cream, 20,
                                 anchor_x="center", anchor_y="center")

        arcade.draw_text("WASD / Arrows   Move     ·     E   Interact     ·     Space / Click   Advance Dialogue",
                         89, 49, (232, 215, 194), 12)

        if self.show_story_modal:
            self._draw_story_modal()
        elif self.show_achievements_modal:
            self._draw_achievements_modal()

    def update_camera(self):
        if self.camera and self.window:
            width, height = self.window.get_size()
            scale = min(width / SCREEN_WIDTH, height / SCREEN_HEIGHT)
            half_width, half_height = width / (2 * scale), height / (2 * scale)
            self.camera.viewport = arcade.LRBT(0, width, 0, height)
            self.camera.projection = arcade.LRBT(-half_width, half_width, -half_height, half_height)
            self.camera.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    def to_virtual_coords(self, x, y):
        width, height = self.window.get_size()
        scale = min(width / SCREEN_WIDTH, height / SCREEN_HEIGHT)
        return ((x - width / 2) / scale + SCREEN_WIDTH / 2,
                (y - height / 2) / scale + SCREEN_HEIGHT / 2)

    def _button_at(self, x, y):
        for button_id, _, cx, cy, width, height in self.buttons:
            if abs(x - cx) <= width / 2 and abs(y - cy) <= height / 2:
                return button_id
        return None

    def _draw_story_modal(self):
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        arcade.draw_rect_filled(
            arcade.XYWH(cx, cy, SCREEN_WIDTH * 2, SCREEN_HEIGHT * 2), (0, 0, 0, 205)
        )
        panel = arcade.XYWH(cx, cy, 860, 526)
        arcade.draw_rect_filled(panel, (27, 24, 23, 252))
        arcade.draw_rect_outline(panel, (164, 121, 73), 1.5)

        left, right = cx - 370, cx + 370
        gold = (235, 193, 131)
        cream = (240, 225, 207)
        arcade.draw_text("Story Synopsis", left, 547, cream, 32,
                         font_name=("Georgia", "Times New Roman"))
        arcade.draw_line(left, 526, right, 526, (116, 85, 56), 1)

        if not hasattr(self, "_synopsis_text"):
            sections = (
                (
                    "Midnight Soup",
                    "After a food poisoning incident costs him his restaurant and home, a chef "
                    "returns on a rainy night to cook a bowl of egg noodles. At midnight, three "
                    "cards carry him into prehistory, a royal court, and the future.",
                ),
                (
                    "The Revelation",
                    "In a future laboratory, he learns that his attempts to change the past "
                    "caused the very tragedies he hoped to prevent.",
                ),
                (
                    "The Final Choice",
                    "Launching another jump repeats the cycle. If he lets the past rest, "
                    "he wakes to a quiet morning and shares two bowls of noodles with his wife.",
                ),
            )
            self._synopsis_text = []
            y = 502
            for heading, paragraph in sections:
                title = arcade.Text(heading, left, y, gold, 16, bold=True, anchor_y="top")
                self._synopsis_text.append(title)
                y -= 30
                for line in wrap(paragraph, width=82):
                    self._synopsis_text.append(
                        arcade.Text(line, left, y, cream, 15, anchor_y="top")
                    )
                    y -= 25
                y -= 18
        for label in self._synopsis_text:
            label.draw()

        arcade.draw_line(left, 158, right, 158, (116, 85, 56), 1)
        arcade.draw_text("Click anywhere or press Esc to close", cx, 126,
                         (195, 181, 168), 12, anchor_x="center")

    def _draw_achievements_modal(self):
        cx = SCREEN_WIDTH / 2
        cy = SCREEN_HEIGHT / 2
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, SCREEN_WIDTH * 2, SCREEN_HEIGHT * 2), (0, 0, 0, 205))
        panel = arcade.XYWH(cx, cy, 580, 320)
        arcade.draw_rect_filled(panel, (27, 24, 23, 250))
        arcade.draw_rect_outline(panel, COLOR_GOLD, 1.5)
        arcade.draw_text("Achievements", cx, cy + 112, COLOR_GOLD, 26,
                         font_name=("Georgia", "Times New Roman"), anchor_x="center")
        for name, y in (("A Fate of My Own Making", cy + 38), ("One More Tomorrow", cy - 26)):
            unlocked = name in self.unlocked_achievements
            arcade.draw_rect_filled(arcade.XYWH(cx, y, 500, 50), (48, 39, 32))
            arcade.draw_text(name, cx - 232, y, (253, 235, 200), 15, anchor_y="center")
            arcade.draw_text("Unlocked" if unlocked else "Locked", cx + 232, y,
                             COLOR_GOLD if unlocked else (195, 181, 168), 13,
                             anchor_x="right", anchor_y="center")
        arcade.draw_text("Click anywhere or press Esc to close", cx, cy - 113,
                         (195, 181, 168), 12, anchor_x="center")

    def on_mouse_motion(self, x, y, dx, dy):
        vx, vy = self.to_virtual_coords(x, y)
        if self.show_story_modal or self.show_achievements_modal:
            return
        self.hovered_btn = self._button_at(vx, vy)

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        vx, vy = self.to_virtual_coords(x, y)
        self.audio.play("click")
        if self.show_story_modal:
            self.show_story_modal = False
            return
        if self.show_achievements_modal:
            self.show_achievements_modal = False
            return

        selected = self._button_at(vx, vy)
        if selected == "start":
            from scenes.modern_view import ModernKitchenView
            self.window.show_view(ModernKitchenView())
        elif selected == "achievements":
            self.unlocked_achievements = get_all_unlocked_achievements()
            self.show_achievements_modal = True
        elif selected == "story":
            self.show_story_modal = True
        elif selected == "exit":
            self.window.close()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.F11:
            self.toggle_fullscreen()
        elif key == arcade.key.ESCAPE:
            if self.show_story_modal:
                self.show_story_modal = False
            elif self.show_achievements_modal:
                self.show_achievements_modal = False
            else:
                self.window.close()



if __name__ == "__main__":
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, "The Last Ingredient - Main Menu", resizable=False, fullscreen=START_FULLSCREEN)
    if START_FULLSCREEN:
        window.set_fullscreen(True)
    view = MenuView()
    window.show_view(view)
    arcade.run()

