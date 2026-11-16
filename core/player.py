"""Player entity module with 4-frame walk cycle [idle, walk1, idle, walk2]
Supports seamless character switching across the 4 eras: modern, savage, chef, astronaut.
"""
import os
import math
import arcade
from core.constants import CHARACTERS_DIR, CHARACTERS
from core.particles import FootstepDust
from core.audio import AudioManager

CHARACTER_SCALE = 0.22
CANVAS_W = 640
CANVAS_H = 860
BASELINE_Y = 810
FEET_OFFSET = (BASELINE_Y - CANVAS_H / 2.0) * CHARACTER_SCALE  # ~83.6 px


class Player:
    def __init__(self, x, y, char_id="modern", sprites_dir=None, scale=None):
        self.x = x
        self.y = y
        self.char_id = char_id
        # Scenes drawn in the pixel style load their pre-pixelised copies.
        self.sprites_dir = sprites_dir or CHARACTERS_DIR
        # The pixel scenes pre-scale the character texture to its final world
        # size, so they pass scale=1.0. Other scenes keep CHARACTER_SCALE.
        self.character_scale = scale if scale is not None else CHARACTER_SCALE
        self.facing = "down"   # "down", "up", "left", "right"
        self.is_moving = False
        self.speed = 220.0     # Pixels per second

        # 4-stage walk cycle: [idle (parallel), walk1 (left), idle (parallel), walk2 (right)]
        self.anim_timer = 0.0
        self.anim_frame_idx = 0
        self.step_interval = 0.13

        # Gentle idle breathing bob
        self.idle_timer = 0.0

        # Load textures for all 4 eras
        self.textures = {}
        self._load_character_textures(char_id, self.sprites_dir)

        # Feet sit BASELINE_Y down a CANVAS_H-tall canvas. The sprite is always
        # centred on (x, y); feet_offset is only the world distance from that
        # centre down to the feet, used for the contact shadow and depth sort.
        # Derive it from the actual texture height and the baseline fraction so
        # it is correct for every character regardless of canvas width (savage
        # is 520 wide, tribe_* are 640) and for both pre-scaled and full-canvas
        # textures, instead of assuming a 640-wide canvas.
        base_frac = BASELINE_Y / CANVAS_H - 0.5
        self.feet_offset = base_frac * self.textures["down"]["idle"].height * self.character_scale

        # Setup active sprite
        self.sprite = arcade.Sprite(self.textures[self.facing]["idle"], scale=self.character_scale)
        self.sprite.center_x = self.x
        self.sprite.center_y = self.y
        self.sprite_list = arcade.SpriteList()
        self.sprite_list.append(self.sprite)

        self.audio = AudioManager()

    def _load_character_textures(self, char_id, sprites_dir=None):
        cdir = (sprites_dir or CHARACTERS_DIR) / char_id
        dirs = ["down", "up", "left", "right"]
        self.textures = {}
        for d in dirs:
            self.textures[d] = {
                "idle": arcade.load_texture(str(cdir / f"char_{d}_idle.png")),
                "walk1": arcade.load_texture(str(cdir / f"char_{d}_walk1.png")),
                "walk2": arcade.load_texture(str(cdir / f"char_{d}_walk2.png")),
            }

    def set_character(self, char_id):
        if char_id in CHARACTERS and char_id != self.char_id:
            self.char_id = char_id
            self._load_character_textures(char_id, self.sprites_dir)
            self._update_texture()

    def place(self, x, y):
        """Teleport and sync the sprite immediately (no walk cycle)."""
        self.x = x
        self.y = y
        self.sprite.center_x = x
        self.sprite.center_y = y

    def update(self, dt, move_x, move_y, dust_particles=None, bounds=(50, 1230, 80, 520), obstacles=None):
        if move_x != 0 or move_y != 0:
            length = math.hypot(move_x, move_y)
            norm_x = (move_x / length) * self.speed
            norm_y = (move_y / length) * self.speed
            self.is_moving = True

            # Determine dominant facing direction
            if abs(move_x) >= abs(move_y):
                self.facing = "right" if move_x > 0 else "left"
            else:
                self.facing = "up" if move_y > 0 else "down"

            # Apply movement with bounds clamping and axis-separated obstacle sliding
            min_x, max_x, min_y, max_y = bounds
            next_x = max(min_x, min(max_x, self.x + norm_x * dt))
            next_y = max(min_y, min(max_y, self.y + norm_y * dt))

            if obstacles:
                feet_y_next = next_y - self.feet_offset + 8
                feet_y_cur = self.y - self.feet_offset + 8
                feet_r = 16.0

                # 1. Try sliding along X
                collided_x = False
                for ox1, ox2, oy1, oy2 in obstacles:
                    if (ox1 - feet_r < next_x < ox2 + feet_r) and (oy1 < feet_y_cur < oy2):
                        collided_x = True
                        break
                if not collided_x:
                    self.x = next_x

                # 2. Try sliding along Y
                collided_y = False
                for ox1, ox2, oy1, oy2 in obstacles:
                    if (ox1 - feet_r < self.x < ox2 + feet_r) and (oy1 < feet_y_next < oy2):
                        collided_y = True
                        break
                if not collided_y:
                    self.y = next_y
            else:
                self.x = next_x
                self.y = next_y

            # Cycle: [idle (parallel), walk1 (left), idle (parallel), walk2 (right)]
            self.anim_timer += dt
            if self.anim_timer >= self.step_interval:
                self.anim_timer = 0.0
                self.anim_frame_idx = (self.anim_frame_idx + 1) % 4

                # Footfall on step 1 (left) or 3 (right)
                if self.anim_frame_idx in (1, 3):
                    if dust_particles is not None:
                        offset_x = -10 if self.anim_frame_idx == 1 else 10
                        dust_particles.append(FootstepDust(self.x + offset_x, self.y - self.feet_offset))
                    self.audio.play("footstep", min_interval=0.22, volume_scale=0.35)
        else:
            self.is_moving = False
            self.anim_timer = 0.0
            self.anim_frame_idx = 0
            self.idle_timer += dt

        self._update_texture()
        self.sprite.center_x = self.x
        self.sprite.center_y = self.y

    def _update_texture(self):
        dir_tex = self.textures[self.facing]
        if self.is_moving:
            # Strictly follows: [parallel, left foot, parallel, right foot]
            cycle = [dir_tex["idle"], dir_tex["walk1"], dir_tex["idle"], dir_tex["walk2"]]
            self.sprite.texture = cycle[self.anim_frame_idx]
        else:
            self.sprite.texture = dir_tex["idle"]

    def draw(self, aspect_correction: float = 1.0):
        # Soft character shadow on the floor
        shadow_w = 70 * aspect_correction
        shadow_h = 16
        shadow_y = self.y - self.feet_offset + 4
        arcade.draw_ellipse_filled(self.x, shadow_y, shadow_w, shadow_h, (0, 0, 0, 85))

        # Maintain natural 1:1 character proportions without widescreen stretch
        self.sprite.scale_x = self.character_scale * aspect_correction
        self.sprite.scale_y = self.character_scale

        # Draw character sprite
        self.sprite_list.draw()

    def draw_interact_prompt(self, text="[E] Interact", offset_y=115):
        """Draw an atmospheric floating interactive pill above character's head."""
        bob = math.sin(self.idle_timer * 4.0) * 3.0
        prompt_y = self.y + offset_y + bob

        # Pill background
        box_w = max(110, len(text) * 8 + 32)
        box_h = 28
        arcade.draw_rect_filled(arcade.XYWH(self.x, prompt_y, box_w, box_h), (25, 25, 30, 220))
        arcade.draw_rect_outline(arcade.XYWH(self.x, prompt_y, box_w, box_h), (235, 198, 110, 220), 1.5)
        arcade.draw_text(text, self.x, prompt_y - 6, (255, 250, 230), 12,
                         anchor_x="center", bold=True)
