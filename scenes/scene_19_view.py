"""Fullscreen Royal aftermath with four player-paced shots."""
import math
from pathlib import Path

import arcade
from core.base_view import BaseGameView

ASSETS = Path(__file__).resolve().parents[1] / "assets"
ART_DIR = ASSETS / "s19"
SHOTS = (
    ("dining_room", "Get the physician! Help her first!", "The cook",
     ((0.04, "door_creak", 0.48), (0.18, "royal_leather_step", 0.7),
      (0.34, "royal_leather_step", 0.65), (0.49, "table_slam", 0.52)), 0.49, 13),
    ("chapel", "They buried her with her mother's ring.", "Narration",
     ((0.18, "clock_chime", 0.34),), 0.18, 2),
    ("record", "", "",
     ((0.12, "lock_click", 0.48), (0.58, "stamp_seal", 0.42)), 0.58, 5),
    ("execution", "", "", ((0.23, "montage_impact", 0.30),), 0.23, 6),
)
FADE_SECONDS = 0.65


class Scene19View(BaseGameView):
    def __init__(self):
        super().__init__()
        self.textures = {
            (shot, ratio): arcade.load_texture(
                ART_DIR / (f"{shot}_{ratio}.jpg" if shot == "execution" else f"{shot}_{ratio}.png")
            )
            for shot, *_ in SHOTS
            for ratio in ("16x10", "16x9")
        }
        self.sounds = {
            name: arcade.load_sound(ASSETS / "sounds" / f"{name}.wav")
            for _, _, _, cues, _, _ in SHOTS
            for _, name, _ in cues
        }
        self.players = []
        self.shot = 0
        self.elapsed = 0.0
        self.next_cue = 0
        self.speaker = arcade.Text("", 0, 0, (239, 195, 131), anchor_x="center")
        self.subtitle = arcade.Text("", 0, 0, (255, 245, 230), anchor_x="center")
        self.hint = arcade.Text("", 0, 0, (215, 203, 199), anchor_x="center")

    def on_hide_view(self):
        for player in self.players:
            arcade.stop_sound(player)
        self.players.clear()

    def on_update(self, delta_time):
        self.elapsed += delta_time
        cues = SHOTS[self.shot][3]
        while self.next_cue < len(cues):
            at, name, volume = cues[self.next_cue]
            if self.elapsed < at:
                break
            self.players.append(arcade.play_sound(self.sounds[name], volume=volume))
            self.next_cue += 1

    def on_draw(self):
        self.clear((10, 8, 10, 255))
        width, height = self.window.get_size()
        shot, line, speaker, _, impact_at, strength = SHOTS[self.shot]
        ratio = "16x9" if width / height >= (16 / 9 + 16 / 10) / 2 else "16x10"
        texture = self.textures[shot, ratio]
        since_impact = self.elapsed - impact_at
        shake = strength * max(0, 1 - since_impact / 0.4) if since_impact >= 0 else 0
        dx = shake * math.sin(since_impact * 83)
        dy = shake * math.cos(since_impact * 71)
        scale = max((width + 2 * abs(dx)) / texture.width,
                    (height + 2 * abs(dy)) / texture.height)
        scale *= 1 + min(self.elapsed, 5) * 0.003
        opacity = int(255 * min(1, self.elapsed / FADE_SECONDS))
        arcade.draw_texture_rect(
            texture,
            arcade.XYWH(width / 2 + dx, height / 2 + dy,
                        texture.width * scale, texture.height * scale),
            alpha=opacity,
        )
        if shake > 0:
            arcade.draw_lrbt_rectangle_filled(0, width, 0, height,
                                               (255, 211, 164, int(shake * 2)))
        footer = min(126, height * 0.21)
        if line:
            arcade.draw_lrbt_rectangle_filled(0, width, 0, footer, (11, 8, 12, 195))
        font_size = max(10, min(25, width / 44))
        action = "Continue to S20" if self.shot == len(SHOTS) - 1 else "Continue"
        for text, content, y, size in (
            (self.speaker, speaker.upper(), footer * 0.73, font_size * 0.65),
            (self.subtitle, line, footer * 0.39, font_size),
            (self.hint, f"Enter / Space / Click   {action}", footer * 0.10, font_size * 0.62),
        ):
            text.text = content
            text.x = width / 2
            text.y = y
            text.font_size = size
            text.draw()

    def advance(self):
        if self.elapsed < FADE_SECONDS:
            return
        if self.shot == len(SHOTS) - 1:
            from scenes.scene_20_view import Scene20View

            self.window.show_view(Scene20View())
            return
        self.shot += 1
        self.elapsed = 0.0
        self.next_cue = 0

    def on_key_press(self, symbol, modifiers):
        if symbol in (arcade.key.ENTER, arcade.key.SPACE):
            self.advance()
        elif symbol == arcade.key.F11:
            self.window.set_fullscreen(not self.window.fullscreen)
        elif symbol == arcade.key.ESCAPE:
            self.window.close()

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.advance()




