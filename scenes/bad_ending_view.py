"""Bad Ending Scene View (B01 - B07).
Follows the official 45-scene script specification for The Last Ingredient:
- B01: I Can Still Get It Right (Launch decision, dialogue branches based on truth understanding)
- B02: The Future Nutrient Block (Micro-interaction: synthesis, consumption, vial inspection)
- B03: The Wrong Target (Micro-interaction: crosshair aiming and firing at distant creature; discovery)
- B04: One Last Rescue (Lab return, anchor exhausted, emergency royal launch)
- B05: The Person in the Empty Kitchen (Royal kitchen, collision with counter, salt jar contaminated)
- B06: The Loop Closes (Montage replay of royal, prehistoric, and modern tragedy; realization)
- B07: Morning (Consciousness return, modern house, police arrival, achievement)

All player-facing text is strictly English.
"""
from __future__ import annotations
import math
import random
import time
from pathlib import Path
import arcade
from arcade.types import Color
from arcade.types.rect import LRBT

from core.base_view import BaseGameView
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ASSETS_DIR, SOUNDS_DIR, SCENE_7_DIR
from core.audio import AudioManager
from core.achievements import unlock_achievement


class BadEndingView(BaseGameView):
    def __init__(self, truth_understood: bool = False, start_stage: str = "B01"):
        super().__init__()
        self.truth_understood = truth_understood
        self.stage = start_stage  # "B01" -> "B02" -> "B03" -> "B04" -> "B05" -> "B06" -> "B07"
        self.elapsed = 0.0
        self.audio = AudioManager()
        self._texts: dict = {}

        # Screen transition fade & flash
        self.fade_alpha = 255.0  # Start with fade-in
        self.white_flash = 0.0
        self.screen_shake = 0.0

        # Background textures
        self.tex_future = self._safe_load_tex(ASSETS_DIR / "future_lab" / "room_background.png")
        self.tex_future_counter = self._safe_load_tex(ASSETS_DIR / "future_lab" / "cooking" / "counter.png")
        self.tex_future_pan = self._safe_load_tex(ASSETS_DIR / "future_lab" / "cooking" / "pan.png")
        self.tex_prehistoric = self._safe_load_tex(ASSETS_DIR / "prehistoric" / "prehistoric_ground.png")
        self.tex_dino_normal = self._safe_load_tex(ASSETS_DIR / "Scene 9" / "Juvenile Dino.png")
        self.tex_dino_hurt = self._safe_load_tex(ASSETS_DIR / "Scene 9" / "Juvenile Dino Hurt.png")
        self.tex_royal_kitchen = self._safe_load_tex(ASSETS_DIR / "royal" / "royal_kitchen_room.png")
        self.ending_kitchen = None

        # --- B02: Nutrient block states ---
        self.b02_step = 0  # 0: Ready to synthesize, 1: Synthesizing, 2: Synthesized, 3: Consumed, 4: Vial secured, 5: Countdown
        self.b02_progress = 0.0
        self.b02_countdown = 3.0

        # --- B03: Crosshair aiming states ---
        self.mouse_x = SCREEN_WIDTH / 2
        self.mouse_y = SCREEN_HEIGHT / 2
        self.b03_target_x = 350.0
        self.b03_target_y = 480.0
        self.b03_target_dir = 1.0
        self.b03_fired = False
        self.b03_fire_timer = 0.0
        self.b03_phase = 0  # 0: Aiming, 1: Fired & Hit, 2: Close-up discovery

        # --- B05: Royal kitchen interaction states ---
        self.b05_phase = 0  # 0: Approaching pot, 1: Footsteps heard, 2: Collision & spill, 3: Recall

        # --- B06: Montage slideshow states ---
        self.b06_card_index = 0
        self.b06_card_timer = 0.0

        # --- B07: Modern awakening states ---
        self.b07_textures = None
        self.b07_phase = 0  # Zero-based storyboard index
        self.b07_stills = None
        self.achievement_banner_y = -100.0
        self.is_new_achievement = False

        # Adapter fields for NutrientPrepView
        self.nutrient_consumed = False
        self.cooking_complete = False
        self.transit_committed = True
        self.keys = set()

    def _safe_load_tex(self, path: Path):
        if path.exists():
            try:
                return arcade.load_texture(path)
            except Exception as e:
                print(f"Warning: Failed to load texture {path}: {e}")
        return None

    def on_show_view(self):
        super().on_show_view()
        if self.stage == "B05":
            self._enter_b05()
            return
        if self.stage == "B06":
            from scenes.future_nutrient_view import TransitDepartureView
            TransitDepartureView.open_modern_return(self.window, self.truth_understood)
            return
        if getattr(self, "nutrient_consumed", False) and self.stage == "B02" and self.b02_step < 3:
            self.b02_step = 3
        self.fade_alpha = 255.0

    def _open_nutrient_prep(self):
        from scenes.future_nutrient_view import NutrientPrepView
        self.window.show_view(NutrientPrepView(self))

    def trigger_white_flash(self, duration: float = 1.0):
        self.white_flash = 255.0
        self.audio.play("time_warp", volume_scale=0.9)

    def trigger_shake(self, amount: float = 14.0):
        self.screen_shake = amount

    # -------------------------------------------------------------------------
    # Update logic
    # -------------------------------------------------------------------------
    def on_update(self, dt: float):
        if self.is_paused:
            return
        dt = min(dt, 0.05)
        self.elapsed += dt

        # Fade in smoothing
        if self.fade_alpha > 0:
            self.fade_alpha = max(0.0, self.fade_alpha - dt * 320.0)

        # White flash fade
        if self.white_flash > 0:
            self.white_flash = max(0.0, self.white_flash - dt * 280.0)

        # Screen shake dampening
        if self.screen_shake > 0:
            self.screen_shake = max(0.0, self.screen_shake - dt * 28.0)

        # Stage specific updates
        if self.stage == "B02":
            if self.b02_step == 1:
                self.b02_progress += dt * 0.75
                if self.b02_progress >= 1.0:
                    self.b02_progress = 1.0
                    self.b02_step = 2
                    self.audio.play("click", volume_scale=0.8)
            elif self.b02_step == 5:
                self.b02_countdown -= dt
                if self.b02_countdown <= 0.0:
                    self.stage = "B03"
                    self.trigger_white_flash()

        elif self.stage == "B03":
            if self.b03_phase == 0:
                # Creature moves slowly on high ground
                self.b03_target_x += self.b03_target_dir * dt * 32.0
                if self.b03_target_x > 880:
                    self.b03_target_dir = -1.0
                elif self.b03_target_x < 360:
                    self.b03_target_dir = 1.0
            elif self.b03_phase == 1:
                self.b03_fire_timer += dt
                if self.b03_fire_timer >= 1.6:
                    self.b03_phase = 2  # Close up
                    self.trigger_white_flash(0.8)
            elif self.b03_phase == 2:
                self.b03_fire_timer += dt

        elif self.stage == "B05":
            if self.b05_phase == 2:
                # Spill countdown to recall
                self.screen_shake = max(self.screen_shake, 3.0)

        elif self.stage == "B06":
            self.b06_card_timer += dt

        elif self.stage == "B07":
            if self.b07_phase == 6 and self.is_new_achievement:
                target_y = SCREEN_HEIGHT - 65.0
                self.achievement_banner_y += (target_y - self.achievement_banner_y) * min(1.0, dt * 5.0)

    # -------------------------------------------------------------------------
    # Drawing helpers
    # -------------------------------------------------------------------------
    def _draw_fitted_bg(self, texture, tint=(255, 255, 255, 255)):
        if not texture:
            arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (15, 18, 25))
            return
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        tw, th = texture.width, texture.height
        scale = max(w / tw, h / th)
        dw, dh = tw * scale, th * scale
        c = Color.from_iterable(tint) if not isinstance(tint, Color) else tint
        arcade.draw_texture_rect(texture, arcade.XYWH(w / 2, h / 2, dw, dh), color=c)

    def _draw_card_box(self, cx: float, cy: float, w: float, h: float, bg_color=(12, 18, 28, 240), border_color=(66, 185, 225)):
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, w, h), bg_color)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, w, h), border_color, 2)

    def _draw_button(self, label: str, cx: float, cy: float, w: float = 320, h: float = 46, hovered: bool = False, hotkey: str = ""):
        bg = (24, 60, 85, 245) if hovered else (14, 32, 48, 230)
        border = (120, 240, 255) if hovered else (70, 160, 200)
        text_col = (255, 255, 255) if hovered else (210, 235, 248)
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, w, h), bg)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, w, h), border, 2)
        txt = f"{label}  [{hotkey}]" if hotkey else label
        arcade.draw_text(txt, cx, cy - 6, text_col, 14, anchor_x="center", bold=hovered)

    # -------------------------------------------------------------------------
    # Render stages
    # -------------------------------------------------------------------------
    def on_draw(self):
        self.clear((8, 12, 20))

        # Camera with screen shake
        ox = random.uniform(-self.screen_shake, self.screen_shake) if self.screen_shake > 0 else 0
        oy = random.uniform(-self.screen_shake, self.screen_shake) if self.screen_shake > 0 else 0

        self.window.default_camera.use()

        if self.stage == "B01":
            self._draw_b01()
        elif self.stage == "B02":
            self._draw_b02()
        elif self.stage == "B03":
            self._draw_b03()
        elif self.stage == "B04":
            self._draw_b04()
        elif self.stage == "B05":
            self._draw_b05()
        elif self.stage == "B06":
            self._draw_b06()
        elif self.stage == "B07":
            self._draw_b07()

        # White flash overlay
        if self.white_flash > 0:
            arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                                    (255, 255, 255, int(min(255, self.white_flash))))

        # Screen fade overlay
        if self.fade_alpha > 0:
            arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                                    (0, 0, 0, int(min(255, self.fade_alpha))))

        # Global HUD Header
        arcade.draw_text(f"BAD ENDING · {self.stage}", 28, SCREEN_HEIGHT - 32, (100, 210, 240, 180), 12, bold=True)

        self.draw_pause_overlay()

    # -------------------------------------------------------------------------
    # B01: I Can Still Get It Right
    # -------------------------------------------------------------------------
    def _draw_b01(self):
        self._draw_fitted_bg(self.tex_future, tint=(210, 230, 255, 255))

        # Dim background slightly for dialogue card
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (6, 14, 24, 150))

        # Physical Jump Capsule HUD
        self._draw_card_box(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50, 820, 360)
        arcade.draw_text("SCENE B01 | I CAN STILL GET IT RIGHT", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 195, (90, 230, 255), 18, anchor_x="center", bold=True)
        arcade.draw_text("TEMPORAL DISPLACEMENT CHAMBER · PHYSICAL JUMP CAPSULE", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 168, (150, 190, 215), 11, anchor_x="center")

        status_text = "STATUS: [ TRUTH UNDERSTOOD ]" if self.truth_understood else "STATUS: [ UNVERIFIED ANOMALIES ]"
        status_color = (110, 245, 160) if self.truth_understood else (255, 180, 80)
        arcade.draw_text(status_text, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 135, status_color, 12, anchor_x="center", bold=True)

        # Monologue
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 35, 740, 110), (10, 22, 36, 200))
        arcade.draw_text("CHEF", SCREEN_WIDTH / 2 - 350, SCREEN_HEIGHT / 2 + 65, (245, 210, 110), 14, bold=True)

        if not self.truth_understood:
            line = '"If I get there before it happens, there\'s still a chance.\nI can stop the beast. I can stop the poisoning."'
        else:
            line = '"Now I know what goes wrong. I just have to avoid it this time.\nI have the technology. I can change the outcome."'
        arcade.draw_text(line, SCREEN_WIDTH / 2 - 350, SCREEN_HEIGHT / 2 + 12, (230, 245, 255), 15, width=700, multiline=True)

        # System Warning
        arcade.draw_text("SYSTEM NOTICE: Physical jump transports biological body and field equipment into the past.\nWarning: Synthesizing standard field nutrient block recommended before departure.",
                         SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50, (170, 205, 225), 12, anchor_x="center", align="center")

        # Action Buttons
        is_hover_launch = (SCREEN_WIDTH / 2 - 180 <= self.mouse_x <= SCREEN_WIDTH / 2 + 180 and
                           SCREEN_HEIGHT / 2 - 145 <= self.mouse_y <= SCREEN_HEIGHT / 2 - 100)
        self._draw_button("CONFIRM LAUNCH TIME JUMP", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 120, 360, 46, hovered=is_hover_launch, hotkey="SPACE / ENTER")

        arcade.draw_text("[T] Toggle Truth Understood Branch (Test Mode)    [ESC] Pause Menu", SCREEN_WIDTH / 2, 28, (120, 160, 185), 12, anchor_x="center")

    # -------------------------------------------------------------------------
    # B02: The Future Nutrient Block
    # -------------------------------------------------------------------------
    def _draw_b02(self):
        self._draw_fitted_bg(self.tex_future, tint=(140, 160, 190, 255))

        # Counter Overlay
        if self.tex_future_counter:
            arcade.draw_texture_rect(self.tex_future_counter, arcade.XYWH(SCREEN_WIDTH / 2, 220, SCREEN_WIDTH, 440))
        if self.tex_future_pan:
            arcade.draw_texture_rect(self.tex_future_pan, arcade.XYWH(SCREEN_WIDTH / 2 - 120, 260, 380, 190))

        # Top Station HUD
        self._draw_card_box(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 130, 860, 150)
        arcade.draw_text("SCENE B02 | THE FUTURE NUTRIENT BLOCK", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 85, (90, 230, 255), 17, anchor_x="center", bold=True)
        arcade.draw_text("FOOD SYNTHESIZER · ACTIVE PROTOCOL: FIELD NUTRIENT BLOCK", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 112, (160, 205, 230), 12, anchor_x="center")
        arcade.draw_text("Formula: Neuro-Compound Formulation (Safe for Adapted Researcher Body)", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 136, (120, 245, 175), 12, anchor_x="center", bold=True)

        # Interactive Step Cards
        cx = SCREEN_WIDTH / 2 + 230
        cy = 310
        self._draw_card_box(cx, cy, 380, 280)

        # Step 1: Synthesize
        btn1_hover = (cx - 160 <= self.mouse_x <= cx + 160 and cy + 70 <= self.mouse_y <= cy + 115)
        if self.b02_step == 0:
            self._draw_button("1. SYNTHESIZE NUTRIENT BLOCK", cx, cy + 90, 320, 42, hovered=btn1_hover, hotkey="SPACE")
        elif self.b02_step == 1:
            arcade.draw_rect_filled(arcade.XYWH(cx, cy + 90, 320, 42), (18, 42, 60))
            arcade.draw_rect_outline(arcade.XYWH(cx, cy + 90, 320, 42), (80, 210, 245), 2)
            arcade.draw_rect_filled(arcade.XYWH(cx - 158 + 158 * self.b02_progress, cy + 90, 316 * self.b02_progress, 38), (50, 180, 230, 180))
            arcade.draw_text(f"SYNTHESIZING... {int(self.b02_progress * 100)}%", cx, cy + 83, (255, 255, 255), 13, anchor_x="center", bold=True)
        else:
            self._draw_button("✓ NUTRIENT BLOCK SYNTHESIZED", cx, cy + 90, 320, 42, hovered=False)

        # Step 2: Consume
        btn2_hover = (cx - 160 <= self.mouse_x <= cx + 160 and cy + 10 <= self.mouse_y <= cy + 55)
        if self.b02_step < 2:
            arcade.draw_rect_filled(arcade.XYWH(cx, cy + 30, 320, 42), (18, 26, 36, 160))
            arcade.draw_rect_outline(arcade.XYWH(cx, cy + 30, 320, 42), (60, 80, 95), 1)
            arcade.draw_text("2. CONSUME MEAL (LOCKED)", cx, cy + 24, (120, 140, 155), 12, anchor_x="center")
        elif self.b02_step == 2:
            self._draw_button("2. CONSUME NUTRIENT BLOCK", cx, cy + 30, 320, 42, hovered=btn2_hover)
        else:
            self._draw_button("✓ MEAL CONSUMED (ENERGY 100%)", cx, cy + 30, 320, 42, hovered=False)

        # Step 3: Fasten Neuro-Agent Vial
        btn3_hover = (cx - 160 <= self.mouse_x <= cx + 160 and cy - 50 <= self.mouse_y <= cy - 5)
        if self.b02_step < 3:
            arcade.draw_rect_filled(arcade.XYWH(cx, cy - 30, 320, 42), (18, 26, 36, 160))
            arcade.draw_rect_outline(arcade.XYWH(cx, cy - 30, 320, 42), (60, 80, 95), 1)
            arcade.draw_text("3. SECURE NEURO-AGENT VIAL", cx, cy - 36, (120, 140, 155), 12, anchor_x="center")
        elif self.b02_step == 3:
            self._draw_button("3. SECURE NEURO-AGENT VIAL", cx, cy - 30, 320, 42, hovered=btn3_hover)
        else:
            self._draw_button("✓ VIAL FASTENED TO BELT", cx, cy - 30, 320, 42, hovered=False)

        # Step 4: Enter Jump Capsule
        btn4_hover = (cx - 160 <= self.mouse_x <= cx + 160 and cy - 110 <= self.mouse_y <= cy - 65)
        if self.b02_step == 4:
            self._draw_button("ENTER JUMP CAPSULE", cx, cy - 90, 320, 42, hovered=btn4_hover, hotkey="SPACE")
        elif self.b02_step == 5:
            arcade.draw_rect_filled(arcade.XYWH(cx, cy - 90, 320, 42), (180, 40, 40, 240))
            arcade.draw_text(f"LAUNCHING IN {math.ceil(self.b02_countdown)}...", cx, cy - 96, (255, 255, 255), 14, anchor_x="center", bold=True)

        # Bottom Commentary
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2 - 160, 68, 560, 64), (10, 20, 32, 220))
        if self.b02_step == 0:
            cmt = "Synthesizing nutrient block for physical jump travel..."
        elif self.b02_step == 2:
            cmt = "Nutrient block synthesized safely. Consume before departure."
        elif self.b02_step == 3:
            cmt = "Chef: 'Energy restored. No toxicity... the future body tolerates it perfectly.'"
        elif self.b02_step == 4:
            cmt = "Chef: 'Vial secured on belt. Come on... there is still time!'"
        else:
            cmt = "Temporal displacement field active. Departure countdown underway."
        arcade.draw_text(cmt, SCREEN_WIDTH / 2 - 160, 62, (220, 240, 255), 13, anchor_x="center")

    # -------------------------------------------------------------------------
    # B03: The Wrong Target
    # -------------------------------------------------------------------------
    def _draw_b03(self):
        # Forest background
        self._draw_fitted_bg(self.tex_prehistoric, tint=(130, 160, 130, 255))

        # Mist & foliage dark vignette
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (12, 32, 24, 110))

        if self.b03_phase == 0 or self.b03_phase == 1:
            # Distant ridge / foliage obstruction
            arcade.draw_text("SCENE B03 | THE WRONG TARGET", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 48, (120, 240, 180), 18, anchor_x="center", bold=True)
            arcade.draw_text("PREHISTORIC FOREST — HIGH GROUND OVERLOOKING THE CAMP", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 74, (180, 215, 195), 12, anchor_x="center")

            # Creature on distant ridge
            tx, ty = self.b03_target_x, self.b03_target_y
            if self.b03_phase == 0:
                # Distant green silhouette through trees
                scale = 0.45
                if self.tex_dino_normal:
                    flip_x = self.b03_target_dir < 0
                    arcade.draw_texture_rect(self.tex_dino_normal, arcade.XYWH(tx, ty, 160 * scale, 120 * scale), color=Color(70, 150, 90, 210))
                else:
                    arcade.draw_ellipse_filled(tx, ty, 50, 30, (50, 120, 60, 200))
            else:
                # Collapsed
                scale = 0.45
                if self.tex_dino_hurt:
                    arcade.draw_texture_rect(self.tex_dino_hurt, arcade.XYWH(tx, ty - 10, 160 * scale, 100 * scale), color=Color(180, 120, 100, 240))
                else:
                    arcade.draw_ellipse_filled(tx, ty - 10, 50, 20, (80, 60, 50, 230))

            # Foreground leaves & tree branches (framing the sniper view)
            arcade.draw_circle_filled(100, SCREEN_HEIGHT - 80, 220, (10, 26, 16, 220))
            arcade.draw_circle_filled(SCREEN_WIDTH - 80, SCREEN_HEIGHT - 100, 260, (10, 26, 16, 220))
            arcade.draw_circle_filled(SCREEN_WIDTH / 2, SCREEN_HEIGHT + 30, 200, (10, 26, 16, 200))

            # Crosshairs overlay
            mx, my = self.mouse_x, self.mouse_y
            # Slight natural breathing sway
            sway_x = math.sin(self.elapsed * 2.2) * 8.0
            sway_y = math.cos(self.elapsed * 1.8) * 6.0
            cx, cy = mx + sway_x, my + sway_y

            # Check if hovered on creature
            is_on_target = math.hypot(cx - tx, cy - ty) < 65.0
            reticle_color = (255, 60, 60, 230) if is_on_target else (90, 230, 255, 200)

            if self.b03_phase == 0:
                # Draw aiming reticle
                arcade.draw_circle_outline(cx, cy, 38, reticle_color, 2)
                arcade.draw_circle_outline(cx, cy, 4, reticle_color, 2)
                arcade.draw_line(cx - 55, cy, cx - 12, cy, reticle_color, 2)
                arcade.draw_line(cx + 12, cy, cx + 55, cy, reticle_color, 2)
                arcade.draw_line(cx, cy - 55, cx, cy - 12, reticle_color, 2)
                arcade.draw_line(cx, cy + 12, cx, cy + 55, reticle_color, 2)

                hint_text = "LOCKED ON TARGET — [ LEFT CLICK TO FIRE ]" if is_on_target else "AIM CROSSHAIR AT DISTANT MOVING SILHOUETTE"
                arcade.draw_text(hint_text, SCREEN_WIDTH / 2, 70, reticle_color, 14, anchor_x="center", bold=True)
            else:
                arcade.draw_text("TARGET STRUCK! ADVANCING DOWN SLOPE...", SCREEN_WIDTH / 2, 70, (255, 210, 100), 15, anchor_x="center", bold=True)

            # Monologue prompt
            arcade.draw_text('Chef: "I remember the giant beast silhouette at the cave... I can\'t let it get to the camp!"',
                             SCREEN_WIDTH / 2, 110, (240, 245, 255), 14, anchor_x="center")

        elif self.b03_phase == 2:
            # Dramatic Close-up Reveal
            self._draw_fitted_bg(self.tex_prehistoric, tint=(80, 100, 80, 255))
            arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (8, 20, 14, 180))

            # Dino Hurt Close-up
            if self.tex_dino_hurt:
                arcade.draw_texture_rect(self.tex_dino_hurt, arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50, 480, 320))

            # Triangle dart glow on neck
            pulse = math.sin(self.elapsed * 6.0) * 0.5 + 0.5
            arcade.draw_circle_filled(SCREEN_WIDTH / 2 - 35, SCREEN_HEIGHT / 2 + 42, 14 + pulse * 6, (80, 180, 255, int(160 + pulse * 80)))
            arcade.draw_triangle_filled(SCREEN_WIDTH / 2 - 42, SCREEN_HEIGHT / 2 + 36,
                                       SCREEN_WIDTH / 2 - 28, SCREEN_HEIGHT / 2 + 36,
                                       SCREEN_WIDTH / 2 - 35, SCREEN_HEIGHT / 2 + 52,
                                       (220, 240, 255))

            # Dialogue Card
            self._draw_card_box(SCREEN_WIDTH / 2, 130, 920, 190)
            arcade.draw_text("CHEF", SCREEN_WIDTH / 2 - 420, 188, (245, 210, 110), 14, bold=True)
            arcade.draw_text('"No... No, no, no! It\'s just a juvenile dinosaur!\nThe triangular dart... the blue neural payload diffusing into its neck... IT WAS ME!"',
                             SCREEN_WIDTH / 2 - 420, 140, (255, 240, 240), 14, width=840, multiline=True)

            arcade.draw_text('Distant Tribesperson: "Over here! I\'ve found something in the brush!"',
                             SCREEN_WIDTH / 2 - 420, 112, (200, 225, 210), 12, italic=True)

            arcade.draw_text("SYSTEM ALARM: Temporal displacement window expired. Emergency recall engaged!",
                             SCREEN_WIDTH / 2, 54, (255, 100, 100), 13, anchor_x="center", bold=True)

            # Advance button
            is_hover_adv = (SCREEN_WIDTH / 2 - 140 <= self.mouse_x <= SCREEN_WIDTH / 2 + 140 and 16 <= self.mouse_y <= 48)
            self._draw_button("CONTINUE EMERGENCY RECALL", SCREEN_WIDTH / 2, 32, 280, 34, hovered=is_hover_adv, hotkey="SPACE")

    # -------------------------------------------------------------------------
    # B04: One Last Rescue
    # -------------------------------------------------------------------------
    def _draw_b04(self):
        self._draw_fitted_bg(self.tex_future, tint=(220, 160, 160, 255))
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (20, 8, 12, 180))

        self._draw_card_box(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 30, 860, 420, bg_color=(20, 12, 18, 245), border_color=(220, 90, 90))
        arcade.draw_text("SCENE B04 | ONE LAST RESCUE", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 205, (255, 110, 110), 18, anchor_x="center", bold=True)
        arcade.draw_text("FUTURE LABORATORY · EMERGENCY RECALL TERMINAL", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 178, (220, 170, 170), 11, anchor_x="center")

        # Terminal Status
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 95, 780, 90), (10, 12, 18, 220))
        arcade.draw_text("PREHISTORIC JUMP ANCHOR: [ EXHAUSTED / PERMANENTLY DEPLETED ]", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 115, (220, 70, 70), 13, anchor_x="center", bold=True)
        arcade.draw_text("ROYAL HOUSEHOLD ANCHOR (CIRCA 1910): [ CHARGED / DESTINATION READY ]", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 82, (100, 230, 150), 13, anchor_x="center", bold=True)

        # Monologue
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 25, 780, 110), (18, 12, 16, 220))
        arcade.draw_text("CHEF", SCREEN_WIDTH / 2 - 360, SCREEN_HEIGHT / 2 + 8, (245, 210, 110), 14, bold=True)
        arcade.draw_text('"It\'s too late for them... The juvenile, the guards, the whistle that never sounded... it happened because of my dart!\n'
                         'No... but I can still save her! The girl in the royal kitchen... I can remove the soup before anyone ever tastes it!"',
                         SCREEN_WIDTH / 2 - 360, SCREEN_HEIGHT / 2 - 45, (255, 235, 240), 14, width=720, multiline=True)

        # Launch Royal Jump Button
        is_hover_jump = (SCREEN_WIDTH / 2 - 200 <= self.mouse_x <= SCREEN_WIDTH / 2 + 200 and
                         SCREEN_HEIGHT / 2 - 145 <= self.mouse_y <= SCREEN_HEIGHT / 2 - 95)
        self._draw_button("LAUNCH SECOND JUMP: ROYAL HOUSEHOLD", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 120, 400, 48, hovered=is_hover_jump, hotkey="SPACE / ENTER")

    # -------------------------------------------------------------------------
    # B05: The Person in the Empty Kitchen
    # -------------------------------------------------------------------------
    def _draw_b05(self):
        self._draw_fitted_bg(self.tex_royal_kitchen, tint=(210, 210, 210, 255))
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (15, 12, 10, 140))

        self._draw_card_box(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 80, 920, 80)
        arcade.draw_text("SCENE B05 | THE PERSON IN THE EMPTY KITCHEN", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 65, (255, 215, 120), 18, anchor_x="center", bold=True)
        arcade.draw_text("ROYAL HOUSEHOLD KITCHEN — 1910 · THE COOK IS WASHING HANDS IN THE CORRIDOR", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 92, (220, 200, 170), 11, anchor_x="center")

        # Dialogue / narrative stage card
        self._draw_card_box(SCREEN_WIDTH / 2, 150, 920, 220)
        arcade.draw_text("CHEF", SCREEN_WIDTH / 2 - 420, 222, (245, 210, 110), 14, bold=True)

        if self.b05_phase == 0:
            narration = ('"The kitchen is completely empty. The vegetable soup is simmering on the cast-iron stove.\n'
                         'The girl is waiting down the hallway in the dining room.\n'
                         'If I take the pot off the stove right now, she will never drink it!"')
            btn_text = "APPROACH STOVE TO REMOVE SOUP POT"
            hotkey = "SPACE / CLICK"
        elif self.b05_phase == 1:
            narration = ('*Footsteps echo from the stone hallway outside! The past cook is returning!*\n'
                         '"Someone\'s coming—! If we meet face to face, the temporal paradox will collapse!"')
            btn_text = "TURN AWAY HURRIEDLY TO EVADE DETECTION"
            hotkey = "SPACE / CLICK"
        else:
            narration = ('*CLACK! Your field kit strikes the sharp edge of the counter!*\n'
                         '*The glass vial shatters. Blue chemical liquid splashes across the wood, streaming into the OPEN SALT JAR on the shelf!*\n'
                         '"Wait— NO! NOT THE SALT—!"\n'
                         '*SYSTEM ALARM: Critical proximity. Protective recall engaged!*')
            btn_text = "AUTOMATED RECALL ENGAGED"
            hotkey = "SPACE / CLICK"

        arcade.draw_text(narration, SCREEN_WIDTH / 2 - 420, 148, (250, 245, 240), 14, width=840, multiline=True)

        # Action Button
        is_hover_btn = (SCREEN_WIDTH / 2 - 200 <= self.mouse_x <= SCREEN_WIDTH / 2 + 200 and 55 <= self.mouse_y <= 100)
        self._draw_button(btn_text, SCREEN_WIDTH / 2, 78, 400, 44, hovered=is_hover_btn, hotkey=hotkey)

    # -------------------------------------------------------------------------
    # B06: The Loop Closes
    # -------------------------------------------------------------------------
    def _draw_ending_kitchen(self, overlay_alpha):
        if self.ending_kitchen is None:
            from scenes.scene_7_dining import KitchenDining

            sprites = SCENE_7_DIR / "sprites"
            self.ending_kitchen = (
                arcade.load_texture(SCENE_7_DIR / "backgrounds/kitchen_refined.png"),
                arcade.load_texture(sprites / "kitchen_table.png"),
                arcade.load_texture(sprites / "bowl_soup.png"),
                KitchenDining.center,
            )

        kitchen, table, bowl, table_center = self.ending_kitchen
        width, height = SCREEN_WIDTH, SCREEN_HEIGHT
        self._draw_fitted_bg(kitchen)

        # Register the furniture to the same 1678 x 937 world used in Scene 7.
        scale = max(width / kitchen.width, height / kitchen.height) * kitchen.width / 1678
        left = width / 2 - 839 * scale
        bottom = height / 2 - 468.5 * scale
        table_scale = min(360 / table.width, 330 / table.height) * scale
        arcade.draw_texture_rect(table, arcade.XYWH(
            left + table_center[0] * scale, bottom + table_center[1] * scale,
            table.width * table_scale, table.height * table_scale,
        ), color=Color(222, 208, 187, 255))
        bowl_scale = min(52 / bowl.width, 40 / bowl.height) * scale
        arcade.draw_texture_rect(bowl, arcade.XYWH(
            left + 900 * scale, bottom + 324 * scale,
            bowl.width * bowl_scale, bowl.height * bowl_scale,
        ))
        arcade.draw_rect_filled(arcade.XYWH(width / 2, height / 2, width, height),
                                (8, 10, 16, overlay_alpha))

    def _draw_b06(self):
        self._draw_ending_kitchen(155)

        arcade.draw_text("SCENE B06 | THE LOOP CLOSES", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 60, (235, 195, 110), 20, anchor_x="center", bold=True)
        arcade.draw_text("THE CAUSAL REVELATION · THE TRAGIC TIME LOOP", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 90, (160, 190, 210), 12, anchor_x="center")

        # 4 Montage Replay Slides
        cards = [
            ("I. THE ROYAL SOUP (1910)",
             "The past cook stirred a pinch from the contaminated salt jar into the soup.\n"
             "In the dining room, the girl took a single spoonful. The silver spoon fell.\n"
             "The sun-and-vine ring slipped from her lifeless finger."),

            ("II. THE PREHISTORIC POISONING (ANCIENT ERA)",
             "Hunters retrieved the beast killed by your neural dart.\n"
             "The tribe roasted the meat. The guards collapsed in agonizing silence.\n"
             "The bone whistle slipped into the ashes without sounding an alarm."),

            ("III. THE MODERN RESTAURANT (PRESENT DAY)",
             "Centuries later, the ancient toxin was unearthed and synthesized in a modern lab.\n"
             "A mislabelled sample reached your restaurant kitchen line...\n"
             "Starting the tragedy that drove you into the past."),

            ("IV. THE CAUSAL LOOP (FUTURE LABORATORY)",
             "The loop closes. The chef stares at his trembling hands.\n\n"
             'Chef: "It was me all along...\n'
             'I was never going back to save them. I was the one who brought the poison into their lives."')
        ]

        title, desc = cards[min(self.b06_card_index, len(cards) - 1)]

        self._draw_card_box(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 880, 320)
        arcade.draw_text(title, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 115, (255, 215, 110), 16, anchor_x="center", bold=True)
        arcade.draw_text(desc, SCREEN_WIDTH / 2 - 390, SCREEN_HEIGHT / 2 - 40, (235, 245, 255), 14, width=780, multiline=True)

        # Slide progression indicators
        for i in range(len(cards)):
            ix = SCREEN_WIDTH / 2 - 60 + i * 40
            col = (255, 215, 110) if i == self.b06_card_index else (60, 90, 120)
            arcade.draw_circle_filled(ix, SCREEN_HEIGHT / 2 - 110, 6, col)

        # Advance button
        btn_label = "NEXT REVELATION" if self.b06_card_index < len(cards) - 1 else "RETURN TO THE PRESENT"
        is_hover_next = (SCREEN_WIDTH / 2 - 180 <= self.mouse_x <= SCREEN_WIDTH / 2 + 180 and 85 <= self.mouse_y <= 130)
        self._draw_button(btn_label, SCREEN_WIDTH / 2, 108, 360, 44, hovered=is_hover_next, hotkey="SPACE / ENTER")

    # -------------------------------------------------------------------------
    # B07: Noon
    # -------------------------------------------------------------------------
    def _draw_b07_room(self):
        if self.b07_textures is None:
            asset_dir = ASSETS_DIR / "endings" / "b07"
            self.b07_textures = tuple(
                self._safe_load_tex(asset_dir / filename)
                for filename in ("morning.png", "vanity.png", "maid_uniform.png", "protagonist.png")
            )

        background, vanity, uniform, protagonist = self.b07_textures
        if background is None:
            self._draw_fitted_bg(None)
            return

        room = self._b07_cover(background)
        room_width, room_height = room.width, room.height
        center_x, center_y = room.center_x, room.center_y
        arcade.draw_texture_rect(background, room)
        layers = [(vanity, 0.069, 0.65, 0.28), (uniform, 0.109, 0.60, 0.18)]
        if self.b07_phase == 0:
            layers.append((protagonist, 0.79, 0.87, 0.145))
        for texture, x, y, size in layers:
            if texture is not None:
                height = room_height * size
                width = room_width * size * (texture.width / texture.height) * (background.height / background.width)
                left = center_x + (x - 0.5) * room_width
                bottom = center_y + (0.5 - y) * room_height
                arcade.draw_texture_rect(texture, arcade.XYWH(left, bottom, width, height))

    def _b07_cover(self, background):
        # Cover the viewport while keeping the same physical scale on both axes.
        window_width, window_height = self.window.get_framebuffer_size()
        scale = max(window_width / background.width, window_height / background.height)
        room_width = background.width * scale * SCREEN_WIDTH / window_width
        room_height = background.height * scale * SCREEN_HEIGHT / window_height
        center_x, center_y = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        return arcade.XYWH(center_x, center_y, room_width, room_height)

    def _draw_b07(self):
        self.camera.use()
        if self.b07_phase == 0:
            self._draw_b07_room()
        else:
            if self.b07_stills is None:
                asset_dir = ASSETS_DIR / "endings" / "b07"
                self.b07_stills = [
                    arcade.load_texture(asset_dir / f"shot_{shot}.png")
                    for shot in range(2, 7)
                ]
            background = self.b07_stills[min(self.b07_phase - 1, 4)]
            arcade.draw_texture_rect(background, self._b07_cover(background))

        if self.b07_phase == 6:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (18, 10, 4, 205),
            )
            arcade.draw_text("A Fate of My Own Making", 640, 356, (220, 176, 99), 44, anchor_x="center")
            for label, center in (("Return to Menu", 462), ("Retry Future Scene", 818)):
                hovered = abs(self.mouse_x - center) <= 150 and abs(self.mouse_y - 255) <= 28
                self._draw_button(label, center, 255, 300, 56, hovered=hovered)
            if self.is_new_achievement:
                self._draw_b07_achievement_banner()
            return

        captions = (
            "7:30 AM",
            "",
            "Homeowner: Who are you? How did you get in?",
            "Chef: I'm sorry.",
            "",
            "I kept looking for the moment it all went wrong. In the end, I was the one who couldn't stop.",
        )
        caption = captions[self.b07_phase]
        if caption:
            arcade.draw_rect_filled(arcade.XYWH(640, 120, 1040, 40), (18, 12, 8, 205))
            arcade.draw_text(caption, 640, 120, (255, 239, 213), 16, anchor_x="center", anchor_y="center")
        self._draw_button("CONTINUE", 640, 55, 320, 44, hotkey="SPACE / ENTER")

    def _draw_b07_achievement_banner(self):
        cx = SCREEN_WIDTH / 2
        cy = self.achievement_banner_y
        gold = (235, 195, 110)
        banner = arcade.XYWH(cx, cy, 540, 58)
        arcade.draw_rect_filled(banner, (18, 22, 28, 245))
        arcade.draw_rect_outline(banner, gold, 2.0)
        arcade.draw_circle_filled(cx - 220, cy, 14, gold)
        arcade.draw_circle_filled(cx - 220, cy, 10, (25, 28, 35))
        arcade.draw_text("ACHIEVEMENT UNLOCKED!", cx - 190, cy + 9, gold, 12, bold=True)
        arcade.draw_text(
            "A Fate of My Own Making (Completed Bad Ending)",
            cx - 190, cy - 10, (255, 255, 255), 13,
        )

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        self.mouse_x = x
        self.mouse_y = y
        self.handle_pause_mouse_motion(x, y)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        if self.handle_pause_mouse_press(x, y, button):
            return

        if self.stage == "B01":
            # Launch jump button
            if (SCREEN_WIDTH / 2 - 180 <= x <= SCREEN_WIDTH / 2 + 180 and
                    SCREEN_HEIGHT / 2 - 145 <= y <= SCREEN_HEIGHT / 2 - 100):
                self._advance_b01()

        elif self.stage == "B02":
            cx = SCREEN_WIDTH / 2 + 230
            cy = 310
            # Step 1: Synthesize
            if self.b02_step == 0 and (cx - 160 <= x <= cx + 160 and cy + 70 <= y <= cy + 115):
                self._open_nutrient_prep()
            # Step 2: Consume
            elif self.b02_step == 2 and (cx - 160 <= x <= cx + 160 and cy + 10 <= y <= cy + 55):
                self.b02_step = 3
                self.audio.play("click", volume_scale=0.8)
            # Step 3: Secure vial
            elif self.b02_step == 3 and (cx - 160 <= x <= cx + 160 and cy - 50 <= y <= cy - 5):
                self.b02_step = 4
                self.audio.play("click", volume_scale=0.8)
            # Step 4: Enter Jump Capsule
            elif self.b02_step == 4 and (cx - 160 <= x <= cx + 160 and cy - 110 <= y <= cy - 65):
                self.b02_step = 5
                self.audio.play("time_warp", volume_scale=0.8)

        elif self.stage == "B03":
            if self.b03_phase == 0:
                # Firing dart
                self.b03_phase = 1
                self.audio.play("camera_evidence", volume_scale=0.9)
                self.trigger_shake(6.0)
            elif self.b03_phase == 2:
                # Continue recall
                if SCREEN_WIDTH / 2 - 140 <= x <= SCREEN_WIDTH / 2 + 140 and 16 <= y <= 48:
                    self.stage = "B04"
                    self.trigger_white_flash()

        elif self.stage == "B04":
            if (SCREEN_WIDTH / 2 - 200 <= x <= SCREEN_WIDTH / 2 + 200 and
                    SCREEN_HEIGHT / 2 - 145 <= y <= SCREEN_HEIGHT / 2 - 95):
                self._enter_b05()

        elif self.stage == "B05":
            if SCREEN_WIDTH / 2 - 200 <= x <= SCREEN_WIDTH / 2 + 200 and 55 <= y <= 100:
                self._advance_b05()

        elif self.stage == "B06":
            if SCREEN_WIDTH / 2 - 180 <= x <= SCREEN_WIDTH / 2 + 180 and 85 <= y <= 130:
                self._advance_b06()

        elif self.stage == "B07":
            if self.b07_phase < 6:
                if abs(x - 640) <= 160 and abs(y - 55) <= 22:
                    self._advance_b07()
            elif abs(y - 255) <= 28:
                if abs(x - 462) <= 150:
                    from scenes.menu_view import MenuView
                    self.window.show_view(MenuView())
                elif abs(x - 818) <= 150:
                    from scenes.future_integrated_view import FutureLabView
                    self.window.show_view(FutureLabView())

    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.F11:
            self.toggle_fullscreen()
            return

        if self.handle_pause_key(key):
            return

        # Toggle test mode for truth understood
        if key == arcade.key.T and self.stage == "B01":
            self.truth_understood = not self.truth_understood
            self.audio.play("click", volume_scale=0.7)
            return

        # Space / Enter shortcuts for advancing
        if key in (arcade.key.SPACE, arcade.key.ENTER):
            if self.stage == "B01":
                self._advance_b01()
            elif self.stage == "B02":
                if self.b02_step == 0:
                    self._open_nutrient_prep()
                elif self.b02_step == 2:
                    self.b02_step = 3
                    self.audio.play("click", volume_scale=0.8)
                elif self.b02_step == 3:
                    self.b02_step = 4
                    self.audio.play("click", volume_scale=0.8)
                elif self.b02_step == 4:
                    self.b02_step = 5
                    self.audio.play("time_warp", volume_scale=0.8)
            elif self.stage == "B03":
                if self.b03_phase == 0:
                    self.b03_phase = 1
                    self.audio.play("camera_evidence", volume_scale=0.9)
                    self.trigger_shake(6.0)
                elif self.b03_phase == 2:
                    self.stage = "B04"
                    self.trigger_white_flash()
            elif self.stage == "B04":
                self._enter_b05()
            elif self.stage == "B05":
                self._advance_b05()
            elif self.stage == "B06":
                self._advance_b06()
            elif self.stage == "B07":
                if self.b07_phase < 6:
                    self._advance_b07()

    def _advance_b01(self):
        from scenes.future_integrated_view import FutureLabView
        from core.player import FEET_OFFSET
        laboratory = FutureLabView()
        laboratory.truth_understood = self.truth_understood
        laboratory.transit_committed = True
        laboratory.player.place(480, 294 + FEET_OFFSET)
        self.window.show_view(laboratory)

    def _enter_b05(self):
        """Launch the integrated Royal-kitchen encounter with route state."""
        from scenes.scene_b05 import SceneB05View
        self.window.show_view(SceneB05View(
            truth_understood=self.truth_understood, story_mode=True))

    def _advance_b05(self):
        if self.b05_phase == 0:
            self.b05_phase = 1
            self.audio.play("Normal Walk", volume_scale=0.9)
        elif self.b05_phase == 1:
            self.b05_phase = 2
            self.audio.play("table_slam", volume_scale=1.0)
            self.trigger_shake(16.0)
        else:
            from scenes.future_nutrient_view import TransitDepartureView
            TransitDepartureView.open_modern_return(self.window, self.truth_understood)

    def _advance_b06(self):
        self.b06_card_index += 1
        if self.b06_card_index >= 4:
            self.stage = "B07"
            self.trigger_white_flash()
            self.audio.play("clock_chime", volume_scale=0.8)
        else:
            self.audio.play("montage_impact", volume_scale=0.8)

    def _advance_b07(self):
        self.b07_phase += 1
        if self.b07_phase == 2:
            self.audio.play("door_creak", volume_scale=0.8)
        elif self.b07_phase == 6:
            self.is_new_achievement = unlock_achievement("A Fate of My Own Making")
            if self.is_new_achievement:
                self.audio.play("achievement", volume_scale=0.9)
