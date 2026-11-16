"""Happy Ending Scene View (H01 - H11).

Faithfully implements the official 45-scene script specification for The Last Ingredient:
- H01: This Time I Will Not Go Back (Hand on Abort, cancellation confirmed, coordinates dark)
- H02: What Never Happened (Montage: Prehistoric mother & juvenile safe, Royal girl sips soup & grows up)
- H03: The Quiet Left Behind (Darkened future lab, voluntary meal choice: water, noodles, egg)
- H04: For Someone Who Was Ready to Give Up (Childhood Egg Noodle Soup, Neuro-compound: Not Required)
- H05: No More Adjustments (Micro-cooking: water, boil, fry egg with uneven browned edge, reject perfection)
- H06: The Bowl Stays Here (Carrying bowl to return station, warning: physical items cannot be transferred,
       leaving the steaming bowl on future counter, stepping into return empty-handed)
- H07: Wake Up (White light fades to 07:30 AM warm sunlight, birds singing, wife's voice: "Wake up...")
- H08: The Same Dish (Table with two steaming bowls, wife made breakfast to let him rest)
- H09: She Really Did It (Wife's sleeve slips back, revealing the Sun-and-Vine Ring passed down generations)
- H10: Together (Eating together in peaceful warmth, no longer judging what is missing)
- H11: The Last Ingredient (Morning table view, achievement: 'One More Tomorrow', title & begin again)

APU CT029-3-2 Special Effects:
- Zero-stretching 16:9 / 16:10 background adaptation.
- Procedural warm morning light shafts, rising culinary steam, particle dispersion.
- Interactive choice buttons, mouse inspection, keyboard shortcuts (Space / Enter / Click).
- Strictly English player-facing narrative and interface.
"""
from __future__ import annotations
import math
from PIL import Image, ImageFilter, ImageSequence
import random
import time
from pathlib import Path
import arcade
from arcade.types import Color
from arcade.types.rect import LRBT

from core.base_view import BaseGameView
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ASSETS_DIR, SCENE_7_DIR, SOUNDS_DIR, COLOR_GOLD
from core.audio import AudioManager
from core.achievements import unlock_achievement, is_achievement_unlocked
from core.particles import SteamParticle


class WarmLightMote:
    """Atmospheric golden dust mote dancing in morning sunlight."""
    def __init__(self, x_min: float = 0, x_max: float = SCREEN_WIDTH):
        self.x = random.uniform(x_min, x_max)
        self.y = random.uniform(50, SCREEN_HEIGHT - 50)
        self.radius = random.uniform(1.5, 3.2)
        self.alpha = random.uniform(40, 160)
        self.speed_x = random.uniform(-12, 12)
        self.speed_y = random.uniform(6, 22)
        self.phase = random.uniform(0, math.tau)

    def update(self, dt: float):
        self.phase += dt * 1.5
        self.x += (self.speed_x + math.sin(self.phase) * 8.0) * dt
        self.y += self.speed_y * dt
        if self.y > SCREEN_HEIGHT + 10:
            self.y = -10
            self.x = random.uniform(0, SCREEN_WIDTH)

    def draw(self):
        a = int(self.alpha * (0.7 + 0.3 * math.sin(self.phase)))
        arcade.draw_circle_filled(self.x, self.y, self.radius, (255, 235, 175, a))


class HappyEndingView(BaseGameView):
    def __init__(self, start_stage: str = "H01"):
        super().__init__()
        self.stage = start_stage  # "H01" -> "H02" -> "H03" -> "H04" -> "H05" -> "H06" -> "H07" -> "H08" -> "H09" -> "H10" -> "H11"
        self.elapsed = 0.0
        self.audio = AudioManager()
        self._texts: dict[str, arcade.Text] = {}

        # Screen transition fade & visual effects
        self.fade_alpha = 255.0
        self.white_flash = 0.0
        self.sunlight_pulse = 0.0

        # Background textures
        self.tex_future = self._safe_load_tex(ASSETS_DIR / "future_lab" / "room_background.png")
        self.tex_future_counter = self._safe_load_tex(ASSETS_DIR / "future_lab" / "cooking" / "counter.png")
        self.tex_future_pan = self._safe_load_tex(ASSETS_DIR / "future_lab" / "cooking" / "pan.png")
        self.tex_prehistoric = self._safe_load_tex(ASSETS_DIR / "prehistoric" / "prehistoric_ground.png")
        self.tex_dino_normal = self._safe_load_tex(ASSETS_DIR / "Scene 9" / "Juvenile Dino.png")
        self.tex_royal_room = self._safe_load_tex(ASSETS_DIR / "royal" / "royal_kitchen_room.png")
        pov_dir = ASSETS_DIR / "endings" / "happy_ending"
        self.tex_wake_kitchen = arcade.load_texture(pov_dir / "h07_pov_kitchen.png")
        self.wake_blur_kitchen = arcade.Texture(
            self.tex_wake_kitchen.image.filter(ImageFilter.GaussianBlur(13))
        )
        self.wake_tilt_frames = []
        self.wake_tilt_end = 0.0
        with Image.open(pov_dir / "h07_head_tilt.gif") as animation:
            for frame in ImageSequence.Iterator(animation):
                self.wake_tilt_end += max(10, frame.info.get("duration", 40)) / 1000
                self.wake_tilt_frames.append(
                    (self.wake_tilt_end, arcade.Texture(frame.convert("RGBA")))
                )
        self.wake_blur_wife = arcade.Texture(
            self.wake_tilt_frames[0][1].image.filter(ImageFilter.GaussianBlur(7))
        )
        self.wake_focus_time = 1.85
        self.wake_tilt_time = 2.2
        self.wake_dialogue_time = self.wake_tilt_time + self.wake_tilt_end
        self.wake_started = 0.0
        self.tex_ending_kitchen = arcade.load_texture(SCENE_7_DIR / "backgrounds/kitchen_refined.png")
        self.tex_ending_wife = arcade.load_texture(pov_dir / "wife_kitchen_wide.png")
        self.tex_ending_table = arcade.load_texture(SCENE_7_DIR / "sprites/kitchen_table.png")
        self.tex_ending_bowl = arcade.load_texture(SCENE_7_DIR / "sprites/bowl_soup.png")

        # Particle effects
        self.motes = [WarmLightMote() for _ in range(35)]
        self.steam_particles = [SteamParticle(SCREEN_WIDTH / 2, 280, spread=22, base_radius=10.0) for _ in range(16)]

        # --- Sub-stage states ---
        # H01: Abort choice confirmed
        self.h01_confirmed = False
        self.he_cooking_scene = None
        self.he_bowl_left_in_future = False

        # H02: Timeline montage index (0: Prehistoric peaceful, 1: Royal girl sips soup, 2: Ring passing)
        self.h02_index = 0
        self.h02_timer = 0.0

        # H04/H05: Future Cooking micro-steps
        # 0: Recipe chosen, 1: Pouring water, 2: Adding noodles, 3: Frying egg, 4: Uneven edge prompt, 5: Plated
        self.cook_step = 0
        self.cook_progress = 0.0
        self.presentation_rejected = False

        # H06: Leaving the bowl
        self.h06_placed = False

        # H07 - H10: Dialogue sub-phases
        self.sub_step = 0
        self.tex_ring_closeup = arcade.load_texture(pov_dir / "h09_ring_closeup.png")

        # Achievement state
        self.is_new_achievement = False
        self.achievement_banner_y = -100.0

    def _safe_load_tex(self, path: Path):
        if path.exists():
            try:
                return arcade.load_texture(path)
            except Exception as e:
                print(f"Warning: Failed to load texture {path}: {e}")
        return None

    def on_show_view(self):
        super().on_show_view()
        self.fade_alpha = 255.0

    def trigger_white_flash(self):
        self.white_flash = 255.0
        self.audio.play("time_warp", volume_scale=0.7)

    # -------------------------------------------------------------------------
    # Update Loop
    # -------------------------------------------------------------------------
    def on_update(self, dt: float):
        if self.is_paused:
            return
        self.elapsed += dt

        # Smooth fades
        if self.fade_alpha > 0:
            self.fade_alpha = max(0.0, self.fade_alpha - dt * 260.0)
        if self.white_flash > 0:
            self.white_flash = max(0.0, self.white_flash - dt * 180.0)

        # Update motes & steam in appropriate stages
        if self.stage in ("H04", "H05", "H06", "H07", "H08", "H09", "H10", "H11"):
            for m in self.motes:
                m.update(dt)
            for s in self.steam_particles:
                s.update(dt)

        # H02 auto-progression timer
        if self.stage == "H02":
            self.h02_timer += dt

        # H05 Cooking progress
        if self.stage == "H05" and self.cook_step in (1, 2, 3):
            self.cook_progress += dt * 1.4
            if self.cook_progress >= 1.0:
                self.cook_progress = 0.0
                self.cook_step += 1
                if self.cook_step == 2:
                    self.audio.play("boil", volume_scale=0.7)
                elif self.cook_step == 3:
                    self.audio.play("sizzle", volume_scale=0.8)

        # H11 Achievement banner entrance animation
        if self.stage == "H11":
            target_y = SCREEN_HEIGHT - 65.0
            self.achievement_banner_y += (target_y - self.achievement_banner_y) * min(1.0, dt * 5.0)

    # -------------------------------------------------------------------------
    # Drawing
    # -------------------------------------------------------------------------
    def on_draw(self):
        self.clear()
        self.use_game_camera()

        # Render stage
        handler = getattr(self, f"_draw_{self.stage.lower()}", None)
        if handler:
            handler()

        # Ambient dust motes in peaceful stages
        if self.stage in ("H04", "H05", "H06", "H07", "H08", "H09", "H10", "H11"):
            for m in self.motes:
                m.draw()

        # Fade overlay
        if self.fade_alpha > 1.0:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (10, 12, 16, int(self.fade_alpha))
            )

        # White flash overlay
        if self.white_flash > 1.0:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (255, 255, 255, int(self.white_flash))
            )

        self.draw_pause_overlay()

    # =========================================================================
    # H01: This Time I Will Not Go Back
    # =========================================================================
    def _draw_h01(self):
        self._draw_bg_cover(self.tex_future, (14, 20, 28))

        # Dimmed panel overlay
        pw, ph = 780, 480
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, pw, ph), (10, 16, 24, 235))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, pw, ph), (60, 180, 220, 160), 2.0)

        # Stage Header
        self._text("title", "STAGE H01 — THIS TIME I WILL NOT GO BACK", 16, COLOR_GOLD, cx, cy + ph / 2 - 32, center=True, bold=True)
        self._text("sub", "The Final Neural Laboratory Decision", 12, (180, 205, 220), cx, cy + ph / 2 - 58, center=True)

        # Narrative Body
        lines = (
            "Before the jump capsule, coordinates pulse softly:\n"
            "   [ Ancient Tribe: -12,000 BP ]     [ Royal Kitchen: c. 1910 AD ]\n\n"
            "Chef (Internal): \"All along, I thought jumping back was the only way to save them.\n"
            "The poison was never in their food. It was in my desperate hands.\n\n"
            "This time... staying here is how I let them live.\""
        )
        self._text("body", lines, 13, (230, 238, 245), cx, cy + 18, center=True)

        # Decision button
        btn_y = cy - 160
        btn_w, btn_h = 420, 52
        pulse = 1.0 + 0.04 * math.sin(self.elapsed * 4.0)
        arcade.draw_rect_filled(arcade.XYWH(cx, btn_y, btn_w * pulse, btn_h), (25, 95, 135))
        arcade.draw_rect_outline(arcade.XYWH(cx, btn_y, btn_w * pulse, btn_h), (115, 225, 255), 2.0)
        self._text("btn_abort", "[ CLICK OR SPACE ]  ABORT TIME JUMP & STAND DOWN", 14, (255, 255, 255), cx, btn_y, center=True, bold=True)

    # =========================================================================
    # H02: What Never Happened
    # =========================================================================
    def _draw_h02(self):
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2

        if self.h02_index == 0:
            # Prehistory: Unharmed juvenile walks back into the trees
            self._draw_bg_cover(self.tex_prehistoric, (22, 28, 18))
            if self.tex_dino_normal:
                # Juvenile peacefully standing under canopy
                arcade.draw_texture_rect(self.tex_dino_normal, arcade.XYWH(cx, cy - 30, 360, 240))
            box_text = (
                "THE PRIMEVAL FOREST — WHAT NEVER HAPPENED\n\n"
                "The juvenile dinosaur lifts its head, senses the cool wind, and trots into the shade.\n"
                "Its mother waits among the ferns, turning peacefully back toward the valley.\n"
                "At the village hearth, the guards adjust their bone whistles in the evening breeze.\n"
                "No foreign weapon pierced the dusk. The whistle remained ready, but was not needed."
            )
        elif self.h02_index == 1:
            # Royal: Girl sips soup safely
            self._draw_bg_cover(self.tex_royal_room, (28, 22, 20))
            box_text = (
                "THE ROYAL DINING ROOM — WHAT NEVER HAPPENED\n\n"
                "The chef carries the bowl of barley and vegetable soup into the small dining room.\n"
                "The girl blows gently upon the surface, takes a warm spoonful, and smiles.\n\n"
                "Girl: \"Today's is lovely too.\"\n\n"
                "The sentence is not broken. The spoon does not clatter to the stones.\n"
                "The sun-and-vine ring catches the candlelight, resting safely upon her hand."
            )
        else:
            # Generations passing
            self._draw_bg_cover(self.tex_royal_room, (20, 16, 24))
            # Golden ring emblem glowing
            arcade.draw_circle_filled(cx, cy + 30, 75, (235, 195, 75, 45))
            arcade.draw_circle_outline(cx, cy + 30, 48, COLOR_GOLD, 4.0)
            arcade.draw_circle_filled(cx + 28, cy + 58, 12, (255, 245, 180))
            box_text = (
                "ACROSS THE GENERATIONS\n\n"
                "The ring remained upon her hand as decades passed.\n"
                "She grew up, laughed, grew old, and placed it onto her daughter's palm with a quiet blessing.\n"
                "\"When I grow up, I'll give it to my child.\"\n"
                "The promise made in a sunlit palace corridor was kept."
            )

        # Subtitle overlay box
        arcade.draw_rect_filled(arcade.XYWH(cx, 130, 840, 150), (12, 14, 18, 225))
        arcade.draw_rect_outline(arcade.XYWH(cx, 130, 840, 150), COLOR_GOLD, 1.8)
        self._text("h02_desc", box_text, 13, (245, 245, 245), cx, 130, center=True)
        self._text("h02_prompt", "[ CLICK OR SPACE TO ADVANCE MEMORY ]", 12, (215, 190, 130), cx, 38, center=True, bold=True)

    # =========================================================================
    # H03: The Quiet Left Behind
    # =========================================================================
    def _draw_h03(self):
        self._draw_bg_cover(self.tex_future, (14, 18, 24))
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2

        pw, ph = 760, 440
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, pw, ph), (10, 14, 20, 235))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, pw, ph), (80, 190, 230, 160), 2.0)

        self._text("h03_title", "STAGE H03 — THE QUIET LEFT BEHIND", 16, COLOR_GOLD, cx, cy + ph / 2 - 32, center=True, bold=True)

        lines = (
            "The control console is quiet. Consciousness Return is unlocked.\n\n"
            "Across the laboratory, the Food Synthesizer hums:\n"
            "   [ Fresh Spring Water ]       [ Hand-pulled Noodles ]       [ Farm Egg ]\n\n"
            "For the first time across all time, he cooks not to alter someone else's fate,\n"
            "but simply to make a warm meal with his own hands."
        )
        self._text("h03_body", lines, 13, (230, 238, 245), cx, cy + 10, center=True)

        btn_y = cy - 145
        arcade.draw_rect_filled(arcade.XYWH(cx, btn_y, 380, 48), (28, 90, 125))
        arcade.draw_rect_outline(arcade.XYWH(cx, btn_y, 380, 48), (110, 220, 255), 1.8)
        self._text("h03_btn", "[ CLICK OR SPACE ]  STEP UP TO THE COOKING STATION", 13, (255, 255, 255), cx, btn_y, center=True, bold=True)

    # =========================================================================
    # H04 & H05: Future Cooking & Rejecting Perfection
    # =========================================================================
    def _draw_h04(self):
        self._draw_cooking_station_shared()
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2

        # Recipe info card
        rw, rh = 640, 240
        arcade.draw_rect_filled(arcade.XYWH(cx, 550, rw, rh), (14, 20, 30, 235))
        arcade.draw_rect_outline(arcade.XYWH(cx, 550, rw, rh), (100, 210, 255), 2.0)

        self._text("h04_rec_title", "RECIPE: CHILDHOOD EGG NOODLE SOUP", 16, COLOR_GOLD, cx, 635, center=True, bold=True)
        self._text("h04_rec_status", "NEURAL COMPOUND: NOT REQUIRED (EXCLUDED)", 13, (120, 240, 180), cx, 605, center=True, bold=True)

        desc = (
            "Chef (Internal): \"That version of me from last night...\n"
            "Sitting in the dark, cold kitchen, staring at an empty table...\n"
            "If only I could place a warm bowl before him and tell him to breathe.\"\n\n"
            "He watches the clean water begin to warm."
        )
        self._text("h04_rec_body", desc, 13, (235, 240, 245), cx, 520, center=True)

        arcade.draw_rect_filled(arcade.XYWH(cx, 400, 320, 44), (35, 110, 155))
        arcade.draw_rect_outline(arcade.XYWH(cx, 400, 320, 44), (120, 230, 255), 1.8)
        self._text("h04_start_btn", "[ CLICK OR SPACE ]  BEGIN COOKING", 13, (255, 255, 255), cx, 400, center=True, bold=True)

    def _draw_h05(self):
        self._draw_cooking_station_shared()
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2

        # Step instruction box
        bw, bh = 700, 160
        arcade.draw_rect_filled(arcade.XYWH(cx, 560, bw, bh), (12, 18, 26, 235))
        arcade.draw_rect_outline(arcade.XYWH(cx, 560, bw, bh), COLOR_GOLD, 2.0)

        if self.cook_step == 0:
            step_txt = "STEP 1: ADD PURE WATER\n\nClick to pour pure water into the broth heating chamber."
            btn_txt = "[ CLICK OR SPACE ]  POUR WATER"
        elif self.cook_step == 1:
            step_txt = f"HEATING WATER...\n\nWater reaches a rolling simmer. Clean steam rises."
            btn_txt = "SIMMERING..."
        elif self.cook_step == 2:
            step_txt = "STEP 2: ADD HAND-PULLED NOODLES\n\nTransfer the noodles into the broth."
            btn_txt = "[ CLICK OR SPACE ]  DROP NOODLES"
        elif self.cook_step == 3:
            step_txt = "STEP 3: FRY SUNNY-SIDE-UP EGG\n\nFrying the egg. The white sizzles with a gently browned, uneven edge."
            btn_txt = "SIZZLING..."
        elif self.cook_step == 4:
            step_txt = (
                "MACHINE PROMPT: \"Egg white has an uneven edge. Adjust presentation to perfection?\"\n\n"
                "Chef: \"No. It's good just like this.\"\n"
                "He accepts the imperfection without hesitation."
            )
            btn_txt = "[ CLICK OR SPACE ]  \"NO. KEEP AS IT IS. SERVE BOWL.\""
        else:
            step_txt = "THE BOWL IS COMPLETED.\n\nA steaming, imperfect, warm bowl of egg noodle soup rests on the tray."
            btn_txt = "[ CLICK OR SPACE ]  LIFT THE BOWL"

        self._text("h05_step_txt", step_txt, 14, (240, 245, 250), cx, 570, center=True)

        if self.cook_step in (0, 2, 4, 5):
            arcade.draw_rect_filled(arcade.XYWH(cx, 440, 380, 44), (40, 120, 165))
            arcade.draw_rect_outline(arcade.XYWH(cx, 440, 380, 44), (130, 235, 255), 1.8)
            self._text("h05_action_btn", btn_txt, 13, (255, 255, 255), cx, 440, center=True, bold=True)

    def _draw_cooking_station_shared(self):
        self._draw_bg_cover(self.tex_future, (15, 20, 28))
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2

        # Counter & Pan in foreground
        if self.tex_future_counter:
            arcade.draw_texture_rect(self.tex_future_counter, arcade.XYWH(cx, 160, SCREEN_WIDTH, 320))
        if self.tex_future_pan:
            arcade.draw_texture_rect(self.tex_future_pan, arcade.XYWH(cx, 220, 280, 180))

        # Rising steam from hot broth
        for s in self.steam_particles:
            s.draw()

    # =========================================================================
    # H06: The Bowl Stays Here
    # =========================================================================
    def _draw_h06(self):
        self._draw_bg_cover(self.tex_future, (14, 18, 24))
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2

        # Drawing the steaming bowl left on the future table
        arcade.draw_ellipse_filled(cx, 320, 180, 90, (235, 230, 220))
        arcade.draw_ellipse_filled(cx, 335, 160, 60, (200, 150, 70))  # broth
        arcade.draw_circle_filled(cx - 15, 335, 18, (255, 175, 40))   # egg yolk
        arcade.draw_circle_filled(cx - 15, 335, 28, (255, 250, 240, 180))  # egg white
        for s in self.steam_particles:
            s.draw()

        pw, ph = 760, 250
        arcade.draw_rect_filled(arcade.XYWH(cx, 550, pw, ph), (10, 16, 26, 235))
        arcade.draw_rect_outline(arcade.XYWH(cx, 550, pw, ph), (255, 180, 80), 2.0)

        self._text("h06_warn", "SYSTEM NOTICE: PHYSICAL ITEMS CANNOT BE TRANSFERRED", 14, (255, 200, 90), cx, 630, center=True, bold=True)

        lines = (
            "He carries the bowl to Consciousness Return. The warning glows red.\n\n"
            "Chef: \"Can't take you with me, then...\"\n"
            "He gently sets the steaming bowl upon the clean work table.\n\n"
            "Chef: \"That's all right. Eat first. Face tomorrow when it comes.\""
        )
        self._text("h06_body", lines, 13, (235, 242, 248), cx, 535, center=True)

        btn_y = 120
        arcade.draw_rect_filled(arcade.XYWH(cx, btn_y, 420, 52), (30, 110, 150))
        arcade.draw_rect_outline(arcade.XYWH(cx, btn_y, 420, 52), (120, 230, 255), 2.0)
        self._text("h06_return_btn", "[ CLICK OR SPACE ]  ACTIVATE CONSCIOUSNESS RETURN", 14, (255, 255, 255), cx, btn_y, center=True, bold=True)

    # =========================================================================
    # H07 - H10: Revised Modern Morning, Wife & Heirloom Ring
    # =========================================================================
    ENDING_DIALOGUE = {
        "H07": (
            ("Wife", "Wake up... Your noodles are getting cold."),
            ("Chef", "You..."),
            ("Wife", "What's wrong? Bad dream?"),
        ),
        "H08": (
            ("Wife", "I made breakfast today. I thought I'd let you sleep in for once."),
            ("Chef", "You... made this?"),
            ("Wife", "Who else? Come on, eat while it's hot."),
        ),
        "H09": (
            ("Chef", "How did you get that ring?"),
            ("Wife", "Are you still half asleep? Mum gave it to me when I married you.\nIt's a family heirloom. If we ever have a daughter, I'll pass it on to her."),
        ),
        "H10": (
            ("Wife", "Does it look that bad? I broke the yolk a little when I flipped it."),
            ("Chef", "It's lovely. It's the most wonderful thing I've ever seen."),
            ("Wife", "Then stop staring. Let's eat together."),
        ),
    }

    def _draw_ending_dialogue(self):
        speaker, line = self.ENDING_DIALOGUE[self.stage][self.sub_step]
        left, bottom, width, height = 48, 24, 1184, 110
        panel = arcade.XYWH(left + width / 2, bottom + height / 2, width, height)
        arcade.draw_rect_filled(panel, (24, 19, 19, 244))
        arcade.draw_rect_outline(panel, (114, 87, 66), 1)
        self._text("ending_speaker", speaker, 16, COLOR_GOLD, left + 24, bottom + 85, bold=True)
        for i, row in enumerate(line.splitlines()):
            self._text(f"ending_line_{i}", row, 17, (245, 234, 222),
                       left + 24, bottom + 53 - i * 24)

    def _draw_h07(self):
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        time = max(0.0, self.elapsed - self.wake_started)
        blurred = time < self.wake_focus_time
        kitchen = self.wake_blur_kitchen if blurred else self.tex_wake_kitchen
        wife = self.wake_blur_wife if blurred else self.wake_tilt_frames[0][1]
        if time >= self.wake_tilt_time:
            playback = time - self.wake_tilt_time
            wife = next(
                (texture for end, texture in self.wake_tilt_frames if playback < end),
                self.wake_tilt_frames[-1][1],
            )
        self._draw_bg_cover(kitchen, (32, 28, 34))
        height = SCREEN_HEIGHT * 0.82
        arcade.draw_texture_rect(
            wife, arcade.XYWH(cx, height / 2, height * wife.width / wife.height, height),
        )

        if time < 1.65:
            opening = min(1.0, max(0.0, (time - 0.18) / 1.15))
        elif time < self.wake_focus_time:
            opening = (self.wake_focus_time - time) / 0.20
        else:
            opening = min(1.0, (time - self.wake_focus_time) / 0.22)
        opening = opening * opening * (3 - 2 * opening)
        if opening < 1.0:
            # Two curved eyelids start closed, then pull away from the center.
            xs = [SCREEN_WIDTH * i / 32 for i in range(33)]
            gap = cy * opening
            curve = [gap * (1 - 0.33 * (1 - opening) * (1 - math.sin(math.pi * i / 32))) for i in range(33)]
            for sign, edge in ((1, SCREEN_HEIGHT), (-1, 0)):
                arcade.draw_polygon_filled(
                    [(0, edge), (SCREEN_WIDTH, edge)]
                    + [(x, cy + sign * y) for x, y in reversed(list(zip(xs, curve)))],
                    (12, 9, 10),
                )
        if time < self.wake_dialogue_time:
            return

        self._draw_ending_dialogue()

    def _draw_h08(self):
        self._draw_master_ending_bg()
        self._draw_ending_dialogue()

    def _draw_h09(self):
        self._draw_bg_cover(self.tex_ring_closeup, (32, 28, 34))
        self._draw_ending_dialogue()

    def _draw_h10(self):
        self._draw_master_ending_bg()
        self._draw_ending_dialogue()

    # =========================================================================
    # H11: The Last Ingredient (Ending Climax & Achievement)
    # =========================================================================
    def _draw_h11(self):
        self._draw_master_ending_bg()
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2

        # Epilogue card
        pw, ph = 860, 310
        card_y = cy - 20
        arcade.draw_rect_filled(arcade.XYWH(cx, card_y, pw, ph), (14, 12, 18, 235))
        arcade.draw_rect_outline(arcade.XYWH(cx, card_y, pw, ph), COLOR_GOLD, 2.5)

        self._text("h11_main_title", "THE  LAST  INGREDIENT", 28, COLOR_GOLD, cx, card_y + 105, center=True, bold=True)
        self._text("h11_tagline", "One chance to begin again.", 16, (240, 230, 210), cx, card_y + 65, center=True, italic=True)

        self._text("h11_ending", "HAPPY ENDING · ONE MORE TOMORROW", 14,
                   COLOR_GOLD, cx, card_y - 4, center=True)

        # Action Buttons
        btn_y = card_y - 105
        btn_w, btn_h = 240, 44

        # Button 1: Future Retry
        arcade.draw_rect_filled(arcade.XYWH(cx - 150, btn_y, btn_w, btn_h), (35, 55, 80))
        arcade.draw_rect_outline(arcade.XYWH(cx - 150, btn_y, btn_w, btn_h), (90, 175, 235), 1.6)
        self._text("btn_retry", "[ FUTURE RETRY ]", 13, (230, 240, 255), cx - 150, btn_y, center=True, bold=True)

        # Button 2: Return to Menu
        arcade.draw_rect_filled(arcade.XYWH(cx + 150, btn_y, btn_w, btn_h), (75, 35, 30))
        arcade.draw_rect_outline(arcade.XYWH(cx + 150, btn_y, btn_w, btn_h), COLOR_GOLD, 1.6)
        self._text("btn_menu", "[ RETURN TO MENU ]", 13, (255, 240, 220), cx + 150, btn_y, center=True, bold=True)

        # Achievement Banner (Top Animation)
        self._draw_achievement_banner()

    def _draw_achievement_banner(self):
        cx = SCREEN_WIDTH / 2
        cy = self.achievement_banner_y
        bw, bh = 540, 58
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, bw, bh), (18, 22, 28, 245))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, bw, bh), COLOR_GOLD, 2.0)

        # Cup icon procedurally
        arcade.draw_circle_filled(cx - 220, cy, 14, COLOR_GOLD)
        arcade.draw_circle_filled(cx - 220, cy, 10, (25, 28, 35))

        self._text("ach_title", "ACHIEVEMENT UNLOCKED!", 12, COLOR_GOLD, cx - 190, cy + 9, bold=True)
        self._text("ach_name", "One More Tomorrow (Completed Happy Ending)", 13, (255, 255, 255), cx - 190, cy - 10)

    # -------------------------------------------------------------------------
    # Helper: Zero-Stretch Aspect Ratio Master Background
    # -------------------------------------------------------------------------
    def _draw_master_ending_bg(self):
        """Frame the Scene 7 kitchen and its dining table in morning light."""
        kitchen = self.tex_ending_kitchen
        table = self.tex_ending_table
        bowl = self.tex_ending_bowl
        world_width = 1678
        world_height = kitchen.height * world_width / kitchen.width
        scale = max(SCREEN_WIDTH / world_width, SCREEN_HEIGHT / world_height)
        left = (SCREEN_WIDTH - world_width * scale) / 2
        bottom = (SCREEN_HEIGHT - world_height * scale) / 2

        arcade.draw_rect_filled(
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
            (42, 34, 31),
        )
        arcade.draw_texture_rect(
            kitchen, arcade.XYWH(SCREEN_WIDTH / 2, bottom + world_height * scale / 2,
                                 world_width * scale, world_height * scale),
        )
        wife = self.tex_ending_wife
        wife_height = 235 * scale
        wife_x = left + 1110 * scale
        feet_y = bottom + 237 * scale
        arcade.draw_ellipse_filled(wife_x, feet_y + 2, 66 * scale, 16 * scale, (22, 14, 13, 82))
        arcade.draw_texture_rect(
            wife, arcade.XYWH(wife_x, feet_y + wife_height / 2,
                              wife_height * wife.width / wife.height, wife_height),
        )
        table_scale = min(360 / table.width, 330 / table.height) * scale
        arcade.draw_texture_rect(
            table, arcade.XYWH(left + 900 * scale, bottom + 270 * scale,
                               table.width * table_scale, table.height * table_scale),
        )
        bowl_scale = min(52 / bowl.width, 40 / bowl.height) * scale
        for x, y in ((870, 324), (938, 300)):
            arcade.draw_texture_rect(
                bowl, arcade.XYWH(left + x * scale, bottom + y * scale,
                                  bowl.width * bowl_scale, bowl.height * bowl_scale),
            )

    def _draw_bg_cover(self, tex, fallback_color: tuple):
        w, h = SCREEN_WIDTH, SCREEN_HEIGHT
        if tex is None:
            arcade.draw_rect_filled(arcade.XYWH(w / 2, h / 2, w, h), fallback_color)
            return

        tw, th = tex.width, tex.height
        scale = max(w / tw, h / th)
        dw, dh = tw * scale, th * scale
        arcade.draw_texture_rect(tex, arcade.XYWH(w / 2, h / 2, dw, dh))

    # -------------------------------------------------------------------------
    # Text Factory
    # -------------------------------------------------------------------------
    def _text(self, key: str, text: str, size: int, color: tuple, x: float, y: float,
              center: bool = False, bold: bool = False, italic: bool = False):
        anchor_x = "center" if center else "left"
        anchor_y = "center"
        if key not in self._texts:
            self._texts[key] = arcade.Text(
                text, x, y, color=color, font_size=size,
                font_name=("Segoe UI", "Calibri", "Arial"),
                bold=bold, italic=italic, anchor_x=anchor_x, anchor_y=anchor_y
            )
        else:
            t = self._texts[key]
            t.text = text
            t.x = x
            t.y = y
            t.color = color
            t.font_size = size
            t.bold = bold
            t.italic = italic
            t.anchor_x = anchor_x
            t.anchor_y = anchor_y
        self._texts[key].draw()

    # -------------------------------------------------------------------------
    # Input & Advancing
    # -------------------------------------------------------------------------
    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        if self.handle_pause_mouse_press(x, y, button):
            return
        vx, vy = self.to_virtual_coords(x, y)
        if self.stage == "H01":
            # Abort button clicked
            cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
            if abs(vx - cx) <= 220 and abs(vy - (cy - 160)) <= 30:
                self._advance_h01()
        elif self.stage == "H03":
            cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
            if abs(vx - cx) <= 200 and abs(vy - (cy - 145)) <= 28:
                self._open_he_cooking()
                self.audio.play("click", volume_scale=0.8)
        elif self.stage == "H04":
            cx = SCREEN_WIDTH / 2
            if abs(vx - cx) <= 170 and abs(vy - 400) <= 26:
                self.stage = "H05"
                self.cook_step = 0
                self.audio.play("click", volume_scale=0.8)
        elif self.stage == "H05":
            cx = SCREEN_WIDTH / 2
            if abs(vx - cx) <= 200 and abs(vy - 440) <= 26:
                self._advance_h05()
        elif self.stage == "H06":
            cx = SCREEN_WIDTH / 2
            if abs(vx - cx) <= 220 and abs(vy - 120) <= 30:
                self._advance_h06()
        elif self.stage == "H11":
            cx = SCREEN_WIDTH / 2
            card_y = SCREEN_HEIGHT / 2 - 20
            btn_y = card_y - 105
            # Future Retry button
            if abs(vx - (cx - 150)) <= 125 and abs(vy - btn_y) <= 26:
                from scenes.future_integrated_view import FutureLabView
                self.window.show_view(FutureLabView())
            # Return to Menu button
            elif abs(vx - (cx + 150)) <= 125 and abs(vy - btn_y) <= 26:
                from scenes.menu_view import MenuView
                self.window.show_view(MenuView())
        else:
            self._advance_general()

    def on_mouse_motion(self, x, y, dx, dy):
        self.handle_pause_mouse_motion(x, y)

    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.F11:
            self.toggle_fullscreen()
            return

        if self.handle_pause_key(key):
            return

        if key in (arcade.key.SPACE, arcade.key.ENTER):
            if self.stage == "H01":
                self._advance_h01()
            elif self.stage == "H03":
                self._open_he_cooking()
                self.audio.play("click", volume_scale=0.8)
            elif self.stage == "H04":
                self.stage = "H05"
                self.cook_step = 0
                self.audio.play("click", volume_scale=0.8)
            elif self.stage == "H05":
                self._advance_h05()
            elif self.stage == "H06":
                self._advance_h06()
            elif self.stage == "H11":
                from scenes.menu_view import MenuView
                self.window.show_view(MenuView())
            else:
                self._advance_general()

    def _open_he_cooking(self):
        if not self.h01_confirmed:
            return False
        from scenes.he_cooking_scene import HECookingScene
        if self.he_cooking_scene is None:
            self.he_cooking_scene = HECookingScene(self)
        self.window.show_view(self.he_cooking_scene)
        return True

    def _advance_h01(self):
        self.audio.play("clue_match", volume_scale=0.9)
        self.h01_confirmed = True
        self.stage = "H02"
        self.h02_index = 0
        self.fade_alpha = 200.0

    def _advance_h05(self):
        if self.cook_step == 0:
            self.cook_step = 1
            self.audio.play("boil", volume_scale=0.7)
        elif self.cook_step == 2:
            self.cook_step = 3
            self.audio.play("sizzle", volume_scale=0.8)
        elif self.cook_step == 4:
            self.cook_step = 5
            self.audio.play("chop", volume_scale=0.8)
        elif self.cook_step == 5:
            self.stage = "H06"
            self.audio.play("click", volume_scale=0.8)

    def _advance_h06(self):
        if self.he_bowl_left_in_future:
            self.trigger_white_flash()
            self.stage = "H07"
            self.wake_started = self.elapsed
        else:
            self._open_he_cooking()

    def _advance_general(self):
        self.audio.play("click", volume_scale=0.7)
        if self.stage == "H02":
            self.h02_index += 1
            if self.h02_index >= 3:
                self.stage = "H03"
                self.fade_alpha = 180.0
        elif self.stage in self.ENDING_DIALOGUE:
            if self.stage == "H07" and self.elapsed - self.wake_started < self.wake_dialogue_time:
                return
            self.sub_step += 1
            if self.sub_step < len(self.ENDING_DIALOGUE[self.stage]):
                return
            self.sub_step = 0
            self.stage = f"H{int(self.stage[1:]) + 1:02}"
            if self.stage == "H11":
                self.is_new_achievement = unlock_achievement("One More Tomorrow")
                self.audio.play("achievement", volume_scale=0.9)
