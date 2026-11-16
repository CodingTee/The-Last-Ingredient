"""S13: Return to the modern dining room, then follow the Crown."""
from pathlib import Path

import arcade
from PIL import Image, ImageFilter

from core.audio import AudioManager
from core.base_view import BaseGameView
from core.constants import SCREEN_HEIGHT, SCREEN_WIDTH
from core.dialogue import DialogueBox

ASSETS = Path(__file__).resolve().parent.parent / "assets"
CARD_DIR = ASSETS / "prehistoric" / "cooking_v2"
CX, CY = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
CARD_Y = 305
CARD_POSITIONS = {"beast": CX - 280, "crown": CX, "gear": CX + 280}
CARD_THOUGHTS = {
    "beast": "I can still hear the whistle hitting the ground.",
    "gear": "Maybe I should look at the Crown first.",
}
CARD_WIDTH, CARD_HEIGHT = 144, 216
ROOM_END = 3.0
CROWN_READY = 4.1
TRANSITION_END = 2.4


def smoothstep(value):
    progress = max(0.0, min(1.0, value))
    return progress * progress * (3 - 2 * progress)


class Scene13View(BaseGameView):
    clock_asset = "03_00"
    active_card = "crown"
    wake_line = "They didn't even get to sound the alarm."
    card_thoughts = CARD_THOUGHTS
    wake_sound = "choking_heartbeat"
    transition_color = (238, 185, 105)

    def next_view(self):
        from scenes.royal_view import RoyalKitchenView
        return RoyalKitchenView()

    def __init__(self):
        super().__init__()
        self.audio = AudioManager()
        self.elapsed = 0.0
        self.flip_elapsed = None
        self.hover = None
        self.dialogue = DialogueBox()
        self.time_warp_played = False

        room_dir = ASSETS / "Scene 6"
        with Image.open(room_dir / "Background Dark.png") as source:
            room = source.convert("RGBA")
        with Image.open(room_dir / "precision" / "clocks" / f"wall_clock_{self.clock_asset}_dark.png") as clock:
            clock = clock.convert("RGBA").resize((72, 72), Image.Resampling.LANCZOS)
            # Scene 8 places the clock at (834, 841) in the 1678 x 937 room.
            room.alpha_composite(clock, (834 - 36, 937 - 841 - 36))
        self.room = arcade.Texture(room)
        self.blurred_room = arcade.Texture(room.filter(ImageFilter.GaussianBlur(12)))

        self.table = arcade.load_texture(ASSETS / "Scene 8" / "tabletop.png")
        self.card_back = arcade.load_texture(ASSETS / "Scene 8" / "card_back.png")
        self.spent_faces = {
            card: arcade.load_texture(CARD_DIR / f"{card}_card.png")
            for card in CARD_POSITIONS
            if card != self.active_card and card != "gear"
        }
        self.face = arcade.load_texture(CARD_DIR / f"{self.active_card}_card.png")
        self.blurred_face = arcade.Texture(self.face.image.filter(ImageFilter.GaussianBlur(14)))
        self.line = arcade.Text(
            self.wake_line,
            CX, 67, (247, 230, 201), 19, anchor_x="center",
        )
        self.prompt = arcade.Text(
            f"Click the {self.active_card.title()} or press Enter",
            CX, 75, (246, 220, 167), 14, anchor_x="center",
        )

    def on_show_view(self):
        super().on_show_view()
        self.audio.play(self.wake_sound, volume_scale=0.55)

    def on_update(self, delta_time):
        if self.is_paused:
            return
        self.dialogue.update(delta_time)
        self.elapsed += delta_time
        if self.flip_elapsed is None:
            return
        self.flip_elapsed += delta_time
        if self.flip_elapsed >= 0.8 and not self.time_warp_played:
            self.time_warp_played = True
            self.audio.play("time_warp", volume_scale=0.7)
        if self.flip_elapsed >= TRANSITION_END:
            self.window.show_view(self.next_view())

    def on_draw(self):
        self.clear((0, 0, 0))
        self.use_game_camera()
        if self.elapsed < ROOM_END:
            self.draw_room()
        else:
            self.draw_table()
        if self.dialogue.active:
            self.dialogue.draw()
        self.draw_pause_overlay()

    def draw_room(self):
        room_rect = arcade.XYWH(CX, CY, SCREEN_WIDTH, SCREEN_WIDTH * 937 / 1678)
        arcade.draw_texture_rect(self.room, room_rect)
        blur = 1 - smoothstep((self.elapsed - 0.2) / 1.1)
        arcade.draw_texture_rect(self.blurred_room, room_rect, alpha=int(255 * blur))
        if 1.05 <= self.elapsed < 2.8:
            self.line.draw()
        fade = max(1 - smoothstep(self.elapsed / 0.9), smoothstep((self.elapsed - 2.65) / 0.35))
        self.shade((0, 0, 0), fade)

    def draw_table(self):
        width = max(SCREEN_WIDTH, SCREEN_HEIGHT * self.table.width / self.table.height)
        height = width * self.table.height / self.table.width
        arcade.draw_texture_rect(self.table, arcade.XYWH(CX, CY, width, height))
        for card in CARD_POSITIONS:
            if card == self.active_card:
                continue
            spent = self.spent_faces.get(card)
            arcade.draw_texture_rect(
                spent or self.card_back, self.card_rect(card), alpha=105 if spent else 255,
            )
        if self.flip_elapsed is not None:
            self.draw_card_transition()
            return

        rect = self.card_rect(self.active_card)
        arcade.draw_texture_rect(self.card_back, rect)
        light = smoothstep((self.elapsed - ROOM_END - 0.35) / 0.75)
        if light:
            arcade.draw_rect_outline(rect, (*self.transition_color, int(light * 210)), 2)
        if self.elapsed >= CROWN_READY and not self.dialogue.active:
            self.prompt.draw()
        self.shade((0, 0, 0), 1 - smoothstep((self.elapsed - ROOM_END) / 0.35))

    def draw_card_transition(self):
        time = self.flip_elapsed
        zoom = 1 + 1.35 * smoothstep(time / 1.25)
        width = max(4, CARD_WIDTH * zoom * abs(1 - 2 * min(1, time / 0.46)))
        height = CARD_HEIGHT * zoom
        y = CARD_Y + (CY - CARD_Y) * smoothstep(time / 0.7)
        x = CARD_POSITIONS[self.active_card]
        x += (CX - x) * smoothstep(time / 0.7)
        rect = arcade.XYWH(x, y, width, height)
        self.shade((14, 10, 6), 0.8 * smoothstep(time / 0.65))
        arcade.draw_texture_rect(self.card_back if time < 0.23 else self.face, rect)
        blur = smoothstep((time - 0.8) / 0.85)
        if blur:
            arcade.draw_texture_rect(self.blurred_face, rect, alpha=int(255 * blur))
        self.shade(self.transition_color, 0.72 * smoothstep((time - 1.1) / 0.65))
        self.shade((0, 0, 0), smoothstep((time - 1.78) / 0.57))

    def shade(self, color, amount):
        arcade.draw_rect_filled(
            arcade.XYWH(CX, CY, SCREEN_WIDTH, SCREEN_HEIGHT), (*color, int(255 * amount)),
        )

    def card_rect(self, card):
        lift = 8 if self.hover == card else 0
        return arcade.XYWH(CARD_POSITIONS[card], CARD_Y + lift, CARD_WIDTH, CARD_HEIGHT)

    def card_at(self, x, y):
        x, y = self.to_virtual_coords(x, y)
        for card in CARD_POSITIONS:
            rect = self.card_rect(card)
            if rect.left <= x <= rect.right and rect.bottom <= y <= rect.top:
                return card
        return None

    def activate_card(self):
        if self.elapsed >= CROWN_READY and self.flip_elapsed is None:
            self.flip_elapsed = 0.0
            self.audio.play("card_flip")

    def on_mouse_motion(self, x, y, dx, dy):
        if self.handle_pause_mouse_motion(x, y):
            return
        if self.elapsed >= ROOM_END and self.flip_elapsed is None and not self.dialogue.active:
            self.hover = self.card_at(x, y)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.handle_pause_mouse_press(x, y, button) or button != arcade.MOUSE_BUTTON_LEFT:
            return
        if self.flip_elapsed is not None or self.elapsed < ROOM_END:
            return
        if self.dialogue.active:
            self.dialogue.advance()
            return
        card = self.card_at(x, y)
        if card == self.active_card:
            self.activate_card()
        elif card in self.card_thoughts:
            self.hover = None
            self.dialogue.start_dialogue([("Chef", self.card_thoughts[card], (230, 210, 175))])

    def on_key_press(self, key, modifiers):
        if self.handle_pause_key(key):
            return
        if key == arcade.key.F11:
            self.toggle_fullscreen()
        elif key in (arcade.key.ENTER, arcade.key.SPACE, arcade.key.E):
            if self.dialogue.active:
                self.dialogue.advance()
            else:
                self.activate_card()
