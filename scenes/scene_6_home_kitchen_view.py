"""Scene 6: S06 - S08 The Old Home Kitchen & Midnight Tarot Cards
Implements:
1. Exploration Mode: Spacious but dark house interior on a stormy night.
   - Parallax world with rain beating on windows, moonlight beams, dust-sheeted furniture.
   - Playable chef character with smooth walk controls (WASD / Arrow Keys).
   - Interactive memory landmarks and kitchen stove entrance.
2. Cooking Mama-Style Zoomed-In Cooking Counter:
   - Step 1: Fill water into pot via faucet.
   - Step 2: Ignite burner & heat control with blue flame particles and boiling water.
   - Step 3: Add noodles into bubbling broth, gentle stirring.
   - Step 4: Fry a sunny-side-up egg in the adjacent skillet with sizzling audio & popping particles.
   - Step 5: S07 Eggshell Memory: Click to scoop out the fallen shell, triggering the childhood relative memory.
   - Step 6: Assemble hot noodle soup with golden egg on top.
3. S08 Midnight Tarot Cards:
   - Three mysterious cards materialize on the table: The Beast, The Crown, The Gear.
   - Interactive hover, inspection modals, and card selection leading into Chapter Two.
"""
import math
import random
import sys
from pathlib import Path

# Add project root to path for standalone execution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import arcade
from arcade.types import LRBT, Color
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD,
    ASSETS_DIR, START_FULLSCREEN
)
from core.player import Player, FEET_OFFSET
from scenes.scene_6_precision import PrecisionEnvironment
from core.dialogue import DialogueBox
from core.audio import AudioManager
from core.base_view import BaseGameView

# World Dimensions for House Interior Exploration (Unified 3/4 Top-Down RPG Layout)
HOUSE_WORLD_WIDTH = 1678.0
HOUSE_WORLD_HEIGHT = 937.0
FLOOR_Y_MIN = 120.0
FLOOR_Y_MAX = 730.0

# Scene Modes
MODE_EXPLORE_HOUSE = 0
MODE_COOKING_MAMA = 1
MODE_TAROT_CARDS = 2

# Cooking Mama Steps
COOK_STEP_FILL_WATER = 0
COOK_STEP_IGNITE_STOVE = 1
COOK_STEP_ADD_NOODLES = 2
COOK_STEP_FRY_EGG = 3
COOK_STEP_EGGSHELL_MEMORY = 4
COOK_STEP_ASSEMBLE_DISH = 5
COOK_STEP_FINISHED = 6


class HomeKitchenView(BaseGameView):
    """Scene 6 View: Dark House Interior, Cooking Mama Kitchen Minigame & Midnight Cards."""

    def __init__(self):
        super().__init__()
        self.audio = AudioManager()
        self.t = 0.0

        # Mode State
        self.mode = MODE_EXPLORE_HOUSE
        self.cook_step = COOK_STEP_FILL_WATER

        # Cameras (2D Smooth Tracking in X and Y)
        self.world_cam = None
        self.ui_cam = None
        self.cam_x = SCREEN_WIDTH / 2
        self.cam_y = SCREEN_HEIGHT / 2

        # Dialogue System
        self.dialogue = DialogueBox()

        # Exploration Player: Modern Chef (Spacious 2D Movement - Starts in bottom-left corner)
        self.player = Player(x=200, y=215, char_id="modern")
        self.player.speed = 220.0
        self.dust_particles = []

        # Sitting on sofa state
        self.is_sitting_on_sofa = False
        self.sitting_pos = (740.0, 343.0)  # Thigh contact sits inside cushion; boots clear coffee-table edge
        char_sit_path = str(ASSETS_DIR / "characters" / "modern" / "char_sit.png")
        self.tex_char_sit = arcade.load_texture(char_sit_path)

        # Environment Textures (Background Dark & Background Light)
        scene6_dir = ASSETS_DIR / "Scene 6"
        self.tex_bg_dark = arcade.load_texture(str(scene6_dir / "Background Dark.png"))
        self.tex_bg_light = arcade.load_texture(str(scene6_dir / "Background Light.png"))

        # Dynamic Wall Clock States (11:00, 00:00 / 12:00, 03:00, 06:00)
        self.clock_time = "11:00"
        clocks_dir = scene6_dir / "precision" / "clocks"
        self.tex_clocks = {
            "11:00": arcade.load_texture(str(clocks_dir / "wall_clock_11_00_dark.png")),
            "00:00": arcade.load_texture(str(clocks_dir / "wall_clock_00_00_dark.png")),
            "12:00": arcade.load_texture(str(clocks_dir / "wall_clock_00_00_dark.png")),
            "03:00": arcade.load_texture(str(clocks_dir / "wall_clock_03_00_dark.png")),
            "06:00": arcade.load_texture(str(clocks_dir / "wall_clock_06_00_dark.png")),
        }

        # Registered cutouts and independent light passes load through PrecisionEnvironment.

        # Interactive Light & Window States
        self.window_left_open = False
        self.window_right_open = False
        self.floor_lamp_on = False
        self.dining_lamp_on = False

        # Continuous Smooth Light Intensities (0.0 to 1.0 for realistic bulb warm-up & curtain transitions)
        self.intensity_floor_lamp = 0.0
        self.intensity_dining_lamp = 0.0
        self.intensity_window_left = 0.0
        self.intensity_window_right = 0.0

        # Ambient Dust Motes in House
        self.dust_motes = [
            {
                "x": random.uniform(50, HOUSE_WORLD_WIDTH - 50),
                "y": random.uniform(100, 600),
                "vx": random.uniform(-6, 6),
                "vy": random.uniform(-4, 4),
                "r": random.uniform(1.5, 3.5),
                "alpha": random.randint(30, 80)
            }
            for _ in range(45)
        ]

        # Key Input States
        self.key_left = False
        self.key_right = False
        self.key_up = False
        self.key_down = False
        self.key_shift = False

        # Collision boxes come from precision/manifest.json via PrecisionEnvironment.
        self.furniture_colliders = []

        self.precision = PrecisionEnvironment(self, scene6_dir / "precision")

        # Exploration Interaction Flags
        self.examined_photo = False
        self.examined_window = False
        self.examined_table = False

        # Character Portrait
        scene1_dir = ASSETS_DIR / "Scene 1"
        self.portrait_chef = arcade.load_texture(str(scene1_dir / "Modern Chief.png"))
        self.portrait_thinking = arcade.load_texture(str(scene1_dir / "Chief Thinking.png"))

        # ---------------------------------------------------------------------
        # Cooking Mama Minigame State
        # ---------------------------------------------------------------------
        self.water_level = 0.0          # 0.0 to 1.0
        self.is_filling_water = False
        self.stove_ignited = False
        self.water_boiling = False
        self.boil_timer = 0.0
        self.noodles_added = False
        self.noodle_cook_progress = 0.0 # 0.0 to 1.0
        self.stir_count = 0

        self.oil_poured = False
        self.egg_cracked = False
        self.egg_cooked_progress = 0.0  # 0.0 to 1.0
        self.eggshell_present = False
        self.eggshell_removed = False
        self.dish_assembled = False

        # Particle Systems for Cooking
        self.boil_bubbles = []          # list of [x, y, r, vy, alpha]
        self.steam_puffs = []           # list of [x, y, vx, vy, size, alpha]
        self.flame_particles = []       # list of [x, y, vx, vy, r, col, alpha]
        self.sizzle_sparks = []         # list of [x, y, vx, vy, life]

        # ---------------------------------------------------------------------
        # Tarot Cards State (S08)
        # ---------------------------------------------------------------------
        self.tarot_cards = [
            {
                "id": "beast",
                "name": "THE BEAST",
                "era": "Prehistoric Era ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Primeval Jungle & Cave",
                "desc": "A carved primeval bone and amber crest. Whispers of a hunt that never should have occurred, and a warning whistle silenced in the dark.",
                "color": (210, 105, 55),
                "cx": SCREEN_WIDTH / 2 - 280,
                "cy": 330,
                "w": 180,
                "h": 280,
                "hover": False,
                "active": True
            },
            {
                "id": "crown",
                "name": "THE CROWN",
                "era": "Royal Court Era ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Medieval Palace & Dining",
                "desc": "A silver crest engraved with blooming sun and tangled vines. A young girl's bright laughter echoing down stone corridors before silence falls.",
                "color": (220, 180, 70),
                "cx": SCREEN_WIDTH / 2,
                "cy": 330,
                "w": 180,
                "h": 280,
                "hover": False,
                "active": False  # Unlocked after Beast
            },
            {
                "id": "gear",
                "name": "THE GEAR",
                "era": "Future Era ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· Quantum Synthesis Laboratory",
                "desc": "Interlocking neural telemetry rings glowing in cold cyan. The source of the unverified samples, and the paradoxical loop of fate.",
                "color": (70, 180, 230),
                "cx": SCREEN_WIDTH / 2 + 280,
                "cy": 330,
                "w": 180,
                "h": 280,
                "hover": False,
                "active": False  # Unlocked after Crown
            }
        ]
        self.selected_card = None
        self.inspecting_card = None
        self.transitioning_to_scene_7 = False
        self.fade_alpha = 0.0

        # Start opening narrative in exploration mode
        self._trigger_intro_dialogue()

    def _trigger_intro_dialogue(self):
        script = [
            (
                "Old Home",
                "He slips quietly through the unlocked kitchen back door.\nThe air inside is cold and still, carrying the scent of dry wood and vacated rooms.",
                (210, 175, 120)
            ),
            (
                "Chef",
                "\"The power is cut off, but the emergency gas line might still have pressure.\nJust a bowl of hot noodles... then I'll leave before morning.\"",
                (230, 210, 160),
                self.portrait_chef,
                "left"
            ),
            (
                "Tutorial",
                "[ Use W / A / S / D or Arrow Keys to walk. Hold [Shift] to sprint. Press [E] to investigate & enter kitchen. ]",
                COLOR_GOLD
            )
        ]
        self.dialogue.start_dialogue(script)

    def on_show_view(self):
        super().on_show_view()
        if self.world_cam is None and self.window:
            self.world_cam = arcade.camera.Camera2D(window=self.window)
            self.ui_cam = arcade.camera.Camera2D(window=self.window)
            self._update_all_cameras()

    def on_resize(self, width: int, height: int):
        super().on_resize(width, height)
        self._update_all_cameras()

    def _update_all_cameras(self):
        if not self.window:
            return
        w = self.window.width
        h = self.window.height
        if self.world_cam:
            self.world_cam.viewport = LRBT(0, w, 0, h)
            self.world_cam.projection = LRBT(-SCREEN_WIDTH / 2, SCREEN_WIDTH / 2, -SCREEN_HEIGHT / 2, SCREEN_HEIGHT / 2)
        if self.ui_cam:
            self.ui_cam.viewport = LRBT(0, w, 0, h)
            self.ui_cam.projection = LRBT(-SCREEN_WIDTH / 2, SCREEN_WIDTH / 2, -SCREEN_HEIGHT / 2, SCREEN_HEIGHT / 2)
            self.ui_cam.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    # =========================================================================
    # UPDATE LOGIC
    # =========================================================================
    def on_update(self, dt: float):
        if self.is_paused:
            return

        self.t += dt

        # Update Dialogue
        if self.dialogue.active:
            self.dialogue.update(dt)

        # ---------------------------------------------------------------------
        # 1. Update Exploration Mode
        # ---------------------------------------------------------------------
        if self.mode == MODE_EXPLORE_HOUSE:
            # Player Movement
            if not self.dialogue.active and not self.is_sitting_on_sofa:
                move_x = (1 if self.key_right else 0) - (1 if self.key_left else 0)
                move_y = (1 if self.key_up else 0) - (1 if self.key_down else 0)
            else:
                move_x = 0
                move_y = 0

            # Sprint Acceleration
            self.player.speed = 360.0 if self.key_shift else 220.0
            self.player.step_interval = 0.09 if self.key_shift else 0.13

            if not self.is_sitting_on_sofa:
                self.player.update(
                    dt, move_x, move_y,
                    dust_particles=self.dust_particles,
                    bounds=(140.0, 1560.0, FLOOR_Y_MIN, FLOOR_Y_MAX),
                    obstacles=self.furniture_colliders
                )

            # Camera Smooth Tracking in X and Y (like clearing_simulation.py)
            target_cam_x = max(SCREEN_WIDTH / 2, min(HOUSE_WORLD_WIDTH - SCREEN_WIDTH / 2, self.player.x))
            target_cam_y = max(SCREEN_HEIGHT / 2, min(HOUSE_WORLD_HEIGHT - SCREEN_HEIGHT / 2, self.player.y))
            self.cam_x += (target_cam_x - self.cam_x) * min(1.0, dt * 5.0)
            self.cam_y += (target_cam_y - self.cam_y) * min(1.0, dt * 5.0)

            # Update Dust Motes in House
            for dm in self.dust_motes:
                dm["x"] += dm["vx"] * dt
                dm["y"] += dm["vy"] * dt
                if dm["x"] < 50: dm["x"] = HOUSE_WORLD_WIDTH - 50
                elif dm["x"] > HOUSE_WORLD_WIDTH - 50: dm["x"] = 50
                if dm["y"] < 80: dm["y"] = HOUSE_WORLD_HEIGHT - 60
                elif dm["y"] > HOUSE_WORLD_HEIGHT - 60: dm["y"] = 80

            # Smooth Realistic Lighting Transitions (Warm filament ease & curtain reveal)
            target_fl = 1.0 if self.floor_lamp_on else 0.0
            self.intensity_floor_lamp += (target_fl - self.intensity_floor_lamp) * min(1.0, dt * 3.5)

            target_dl = 1.0 if self.dining_lamp_on else 0.0
            self.intensity_dining_lamp += (target_dl - self.intensity_dining_lamp) * min(1.0, dt * 4.0)

            target_wl = 1.0 if self.window_left_open else 0.0
            self.intensity_window_left += (target_wl - self.intensity_window_left) * min(1.0, dt * 3.0)

            target_wr = 1.0 if self.window_right_open else 0.0
            self.intensity_window_right += (target_wr - self.intensity_window_right) * min(1.0, dt * 3.0)

        # ---------------------------------------------------------------------
        # 2. Update Cooking Mama Mode
        # ---------------------------------------------------------------------
        elif self.mode == MODE_COOKING_MAMA:
            # Water Filling
            if self.is_filling_water and self.water_level < 1.0:
                self.water_level = min(1.0, self.water_level + dt * 0.45)
                if self.water_level >= 1.0:
                    self.is_filling_water = False
                    self.cook_step = COOK_STEP_IGNITE_STOVE
                    self.audio.play("click")
                    self.dialogue.start_dialogue([
                        ("Pot Filled", "The stainless steel pot is filled with fresh water.\nNow ignite the gas burner underneath.", (200, 220, 240))
                    ])

            # Stove Burning & Boiling Water
            if self.stove_ignited:
                # Add flame particles under pot
                for _ in range(3):
                    fx = random.uniform(320, 460)
                    fy = 220 + random.uniform(0, 8)
                    fvy = random.uniform(25, 55)
                    col = random.choice([(60, 160, 240), (80, 200, 255), (140, 220, 255)])
                    self.flame_particles.append([fx, fy, random.uniform(-4, 4), fvy, random.uniform(4, 9), col, 200])

                if not self.water_boiling:
                    self.boil_timer += dt
                    if self.boil_timer >= 2.5:
                        self.water_boiling = True
                        self.audio.play("boil")
                        if self.cook_step == COOK_STEP_IGNITE_STOVE:
                            self.cook_step = COOK_STEP_ADD_NOODLES

            # Boiling Bubbles & Steam
            if self.water_boiling:
                # Bubbles in pot
                if random.random() < 0.35:
                    self.boil_bubbles.append([
                        random.uniform(330, 450),
                        270 + random.uniform(0, 10),
                        random.uniform(3, 7),
                        random.uniform(35, 70),
                        200
                    ])
                # Steam puffs rising from pot
                if random.random() < 0.25:
                    self.steam_puffs.append([
                        random.uniform(340, 440),
                        350,
                        random.uniform(-10, 10),
                        random.uniform(40, 75),
                        random.uniform(12, 22),
                        140
                    ])

            # Noodles cooking progress
            if self.noodles_added and self.noodle_cook_progress < 1.0:
                self.noodle_cook_progress = min(1.0, self.noodle_cook_progress + dt * 0.25)

            # Egg frying
            if self.egg_cracked and self.egg_cooked_progress < 1.0:
                self.egg_cooked_progress = min(1.0, self.egg_cooked_progress + dt * 0.20)
                # Sizzling oil pops
                if random.random() < 0.4:
                    self.sizzle_sparks.append([
                        random.uniform(770, 890),
                        280 + random.uniform(-15, 15),
                        random.uniform(-15, 15),
                        random.uniform(20, 50),
                        0.35
                    ])

            # Update Flame Particles
            for fp in self.flame_particles[:]:
                fp[0] += fp[2] * dt
                fp[1] += fp[3] * dt
                fp[6] -= dt * 350
                fp[4] = max(1.0, fp[4] - dt * 4.0)
                if fp[6] <= 0:
                    self.flame_particles.remove(fp)

            # Update Boil Bubbles
            for bb in self.boil_bubbles[:]:
                bb[1] += bb[3] * dt
                bb[4] -= dt * 150
                if bb[1] > 340 or bb[4] <= 0:
                    self.boil_bubbles.remove(bb)

            # Update Steam Puffs
            for sp in self.steam_puffs[:]:
                sp[0] += sp[2] * dt
                sp[1] += sp[3] * dt
                sp[4] += dt * 16.0
                sp[5] -= dt * 90.0
                if sp[5] <= 0:
                    self.steam_puffs.remove(sp)

            # Update Sizzle Sparks
            for ss in self.sizzle_sparks[:]:
                ss[0] += ss[2] * dt
                ss[1] += ss[3] * dt
                ss[4] -= dt
                if ss[4] <= 0:
                    self.sizzle_sparks.remove(ss)

        # ---------------------------------------------------------------------
        # 3. Update Tarot Cards Mode (S08)
        # ---------------------------------------------------------------------
        elif self.mode == MODE_TAROT_CARDS:
            if self.transitioning_to_scene_7:
                self.fade_alpha = min(255.0, self.fade_alpha + dt * 180.0)
                if self.fade_alpha >= 255.0:
                    self._proceed_to_scene_7()

    def set_clock_time(self, time_str: str):
        """Update the time displayed on the fireplace wall clock ('11:00', '00:00', '03:00', '06:00')."""
        if time_str in self.tex_clocks:
            self.clock_time = time_str

    def _proceed_to_scene_7(self):
        """Transition into Scene 7: Prehistoric Era Primeval Cave."""
        from scenes.prehistoric_view import PrehistoricCaveView
        self.window.show_view(PrehistoricCaveView())

    # =========================================================================
    # DRAW LOGIC
    # =========================================================================
    def on_draw(self):
        self.clear(color=(12, 14, 20))

        if self.mode == MODE_EXPLORE_HOUSE:
            self._draw_house_exploration()
        elif self.mode == MODE_COOKING_MAMA:
            self._draw_cooking_mama()
        elif self.mode == MODE_TAROT_CARDS:
            self._draw_tarot_cards()

        # UI Overlay (Dialogue & Notifications)
        if self.ui_cam:
            self.ui_cam.use()

        # Draw Dialogue
        if self.dialogue.active:
            self.dialogue.draw()

        # Draw Pause Menu
        self.draw_pause_overlay()

    # -------------------------------------------------------------------------
    # 1. RENDER: House Exploration Mode (Photorealistic Anime Background & Dynamic FX)
    # -------------------------------------------------------------------------
    def _draw_house_exploration(self):
        if self.world_cam:
            self.world_cam.position = (self.cam_x, self.cam_y)
            self.world_cam.use()

        # =========================================================================
        # 1. BASE ENVIRONMENT: High-Resolution Background Dark (1678 x 937)
        # =========================================================================
        arcade.draw_texture_rect(
            self.tex_bg_dark,
            arcade.XYWH(HOUSE_WORLD_WIDTH / 2, HOUSE_WORLD_HEIGHT / 2, HOUSE_WORLD_WIDTH, HOUSE_WORLD_HEIGHT)
        )

        # Dynamic Wall Clock on Chimney Wall (Position A: X=834, Y=841 in Arcade coords)
        if self.clock_time in self.tex_clocks:
            arcade.draw_texture_rect(
                self.tex_clocks[self.clock_time],
                arcade.XYWH(834.0, 841.0, 72.0, 72.0)
            )

        pulse = 0.5 + 0.5 * math.sin(self.t * 5.0)
        active_prompt = self.precision.draw()

        # Floating Dust Particles in Air
        for dm in self.dust_motes:
            arcade.draw_circle_filled(dm["x"], dm["y"], dm["r"], (210, 230, 255, dm["alpha"]))

        # =========================================================================
        # 6. INTERACTIVE STORYTELLING PROMPT HUD
        # =========================================================================
        if active_prompt:
            wx, wy, prompt_text, is_highlight = active_prompt
            self._draw_world_prompt(wx, wy, prompt_text, scale=1.0 + 0.05 * pulse, highlight=is_highlight)

    def _draw_world_prompt(self, wx, wy, text, scale=1.0, highlight=False):
        bw = 260 * scale
        bh = 38 * scale
        bg_col = (180, 70, 50, 220) if highlight else (25, 30, 42, 210)
        border_col = COLOR_GOLD if highlight else (140, 170, 210)
        arcade.draw_rect_filled(arcade.XYWH(wx, wy, bw, bh), bg_col)
        arcade.draw_rect_outline(arcade.XYWH(wx, wy, bw, bh), border_col, 2.0 if highlight else 1.2)
        arcade.draw_text(text, wx, wy - 6 * scale, (255, 255, 255) if highlight else (230, 235, 245),
                         int(12 * scale), anchor_x="center", bold=True)

    # -------------------------------------------------------------------------
    # 2. RENDER: Cooking Mama Interactive Countertop Mode
    # -------------------------------------------------------------------------
    def _draw_cooking_mama(self):
        if self.ui_cam:
            self.ui_cam.use()

        # Dark Slate Countertop Background
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (20, 24, 32))
        # Stainless steel kitchen bench surface
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, 220, SCREEN_WIDTH, 440), (32, 38, 48))
        arcade.draw_line(0, 440, SCREEN_WIDTH, 440, (55, 65, 80), 3)

        # Ceramic tiles pattern on wall
        for tx in range(0, SCREEN_WIDTH, 80):
            arcade.draw_line(tx, 440, tx, SCREEN_HEIGHT, (28, 34, 44), 1)
        for ty in range(440, SCREEN_HEIGHT, 60):
            arcade.draw_line(0, ty, SCREEN_WIDTH, ty, (28, 34, 44), 1)

        # Cooking Mama Step Header Badge
        step_titles = [
            "STEP 1: FILL WATER INTO THE POT",
            "STEP 2: IGNITE STOVE BURNER & BOIL BROTH",
            "STEP 3: DROP NOODLES & STIR GENTLY",
            "STEP 4: FRY A SUNNY-SIDE-UP EGG IN SKILLET",
            "STEP 5: REMOVE THE FALLEN EGGSHELL",
            "STEP 6: ASSEMBLE & SERVE THE WARM NOODLES",
            "COMPLETE: A BOWL OF NOODLES"
        ]
        cur_title = step_titles[min(len(step_titles) - 1, self.cook_step)]
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, 675, 680, 48), (28, 35, 50, 240))
        arcade.draw_rect_outline(arcade.XYWH(SCREEN_WIDTH / 2, 675, 680, 48), COLOR_GOLD, 2)
        arcade.draw_text(cur_title, SCREEN_WIDTH / 2, 666, COLOR_GOLD, 16, anchor_x="center", bold=True)

        # ---------------------------------------------------------------------
        # LEFT APPARATUS: The Boiling Pot & Stove Burner
        # ---------------------------------------------------------------------
        pot_cx = 390
        pot_cy = 300

        # Burner Base & Blue Flames
        arcade.draw_ellipse_filled(pot_cx, 215, 180, 40, (18, 22, 28))
        arcade.draw_ellipse_outline(pot_cx, 215, 180, 40, (40, 50, 65), 3)
        for fp in self.flame_particles:
            arcade.draw_circle_filled(fp[0], fp[1], fp[4], (*fp[5], int(fp[6])))

        # Stove Control Knob (Clickable)
        knob_x = 390
        knob_y = 130
        knob_col = (180, 60, 45) if self.stove_ignited else (60, 70, 85)
        arcade.draw_circle_filled(knob_x, knob_y, 36, knob_col)
        arcade.draw_circle_outline(knob_x, knob_y, 36, COLOR_GOLD if self.stove_ignited else (120, 130, 150), 3)
        knob_angle = math.pi / 2 if self.stove_ignited else 0
        arcade.draw_line(
            knob_x, knob_y,
            knob_x + 28 * math.cos(knob_angle),
            knob_y + 28 * math.sin(knob_angle),
            (255, 255, 255), 4
        )
        knob_hint = "[ CLICK KNOB: FLAME ON ]" if not self.stove_ignited else "[ BURNER ACTIVE ]"
        arcade.draw_text(knob_hint, knob_x, knob_y - 55, COLOR_GOLD if self.stove_ignited else (170, 180, 200),
                         11, anchor_x="center", bold=True)

        # Stainless Steel Pot
        arcade.draw_rect_filled(arcade.XYWH(pot_cx, pot_cy, 170, 140), (95, 105, 120))
        arcade.draw_ellipse_filled(pot_cx, pot_cy - 70, 170, 36, (75, 85, 98))
        arcade.draw_ellipse_filled(pot_cx, pot_cy + 70, 170, 40, (110, 122, 138))
        # Pot handles
        arcade.draw_rect_filled(arcade.XYWH(pot_cx - 95, pot_cy + 30, 20, 14), (60, 65, 75))
        arcade.draw_rect_filled(arcade.XYWH(pot_cx + 95, pot_cy + 30, 20, 14), (60, 65, 75))

        # Water Level inside pot
        if self.water_level > 0:
            water_h = 100 * self.water_level
            water_col = (70, 140, 210, 190) if not self.water_boiling else (190, 170, 110, 210)
            arcade.draw_rect_filled(arcade.XYWH(pot_cx, pot_cy - 60 + water_h / 2, 160, water_h), water_col)
            arcade.draw_ellipse_filled(pot_cx, pot_cy - 60 + water_h, 160, 30, (water_col[0] + 20, water_col[1] + 20, water_col[2] + 20, 220))

        # Noodles inside boiling pot
        if self.noodles_added:
            noodle_col = (245, 230, 170)
            for i in range(12):
                nx = pot_cx - 60 + i * 11
                wave = math.sin(self.t * 5.0 + i) * 6.0
                arcade.draw_line(nx, pot_cy - 20, nx + wave, pot_cy + 25, noodle_col, 3)

        # Boil Bubbles & Steam
        for bb in self.boil_bubbles:
            arcade.draw_circle_filled(bb[0], bb[1], bb[2], (255, 255, 255, int(bb[4])))
        for sp in self.steam_puffs:
            arcade.draw_circle_filled(sp[0], sp[1], sp[4], (230, 240, 255, int(sp[5])))

        # Water Tap / Faucet above pot
        arcade.draw_rect_filled(arcade.XYWH(pot_cx, 510, 24, 70), (140, 150, 165))
        arcade.draw_rect_filled(arcade.XYWH(pot_cx - 40, 540, 90, 20), (140, 150, 165))
        # Tap valve handle (Clickable)
        valve_col = (60, 160, 240) if self.is_filling_water else (180, 190, 205)
        arcade.draw_circle_filled(pot_cx - 40, 565, 18, valve_col)
        arcade.draw_circle_outline(pot_cx - 40, 565, 18, (255, 255, 255), 2)
        if self.is_filling_water:
            # Water stream flowing down
            arcade.draw_rect_filled(arcade.XYWH(pot_cx - 40, 420, 12, 180), (100, 180, 255, 220))

        # ---------------------------------------------------------------------
        # RIGHT APPARATUS: The Skillet & Sunny-Side-Up Egg
        # ---------------------------------------------------------------------
        pan_cx = 840
        pan_cy = 280

        # Cast-Iron Skillet
        arcade.draw_circle_filled(pan_cx, pan_cy, 125, (28, 30, 36))
        arcade.draw_circle_outline(pan_cx, pan_cy, 125, (65, 70, 80), 7)
        # Pan Handle
        arcade.draw_rect_filled(arcade.XYWH(pan_cx + 160, pan_cy - 40, 95, 22), (25, 26, 30))

        # Fried Egg in Pan
        if self.egg_cracked:
            # Egg White spreading & sizzling
            white_alpha = min(245, int(80 + self.egg_cooked_progress * 165))
            arcade.draw_ellipse_filled(pan_cx, pan_cy, 150, 110, (245, 245, 240, white_alpha))
            arcade.draw_ellipse_filled(pan_cx - 15, pan_cy + 10, 130, 90, (255, 255, 250, white_alpha))

            # Golden Yolk with 3D specular highlight
            yolk_cx = pan_cx + 5
            yolk_cy = pan_cy - 2
            arcade.draw_circle_filled(yolk_cx, yolk_cy, 34, (245, 165, 30))
            arcade.draw_circle_filled(yolk_cx - 8, yolk_cy + 8, 10, (255, 220, 110, 230))
            arcade.draw_circle_filled(yolk_cx - 12, yolk_cy + 12, 4, (255, 255, 255, 240))

            # Sizzle sparks
            for ss in self.sizzle_sparks:
                arcade.draw_circle_filled(ss[0], ss[1], 2.5, (255, 220, 80, int(ss[4] * 600)))

            # S07 Fallen Eggshell Shard
            if self.eggshell_present and not self.eggshell_removed:
                es_x = pan_cx - 40
                es_y = pan_cy + 25
                arcade.draw_triangle_filled(es_x, es_y, es_x + 12, es_y - 8, es_x - 6, es_y - 12, (205, 175, 140))
                arcade.draw_triangle_outline(es_x, es_y, es_x + 12, es_y - 8, es_x - 6, es_y - 12, (120, 90, 60), 1.5)
                # Pulsing click hint on eggshell
                pulse = 1.0 + 0.12 * math.sin(self.t * 7.0)
                arcade.draw_circle_outline(es_x, es_y, 22 * pulse, (240, 75, 60), 2)
                arcade.draw_text("[ CLICK TO REMOVE SHELL ]", es_x, es_y + 24, (255, 110, 95), 11, anchor_x="center", bold=True)

        # ---------------------------------------------------------------------
        # INTERACTION CONTROL BUTTONS
        # ---------------------------------------------------------------------
        # Water Button / Faucet Hint
        if self.cook_step == COOK_STEP_FILL_WATER:
            self._draw_cook_button(pot_cx - 40, 615, 180, 40, "TURN ON FAUCET", (45, 120, 210))

        # Add Noodles Button
        elif self.cook_step == COOK_STEP_ADD_NOODLES:
            self._draw_cook_button(pot_cx, 440, 220, 42, "DROP IN NOODLES", (210, 140, 40))

        # Fry Egg Button
        elif self.cook_step == COOK_STEP_FRY_EGG:
            self._draw_cook_button(pan_cx, 440, 220, 42, "CRACK & FRY EGG", (220, 90, 50))

        # Assemble / Finish Dish Button
        elif self.cook_step in (COOK_STEP_ASSEMBLE_DISH, COOK_STEP_FINISHED):
            self._draw_cook_button(SCREEN_WIDTH / 2, 80, 320, 48, "SERVE EGG NOODLE SOUP", (185, 65, 50), highlight=True)

    def _draw_cook_button(self, bx, by, bw, bh, text, col, highlight=False):
        pulse = 1.0 + (0.05 * math.sin(self.t * 6.0) if highlight else 0.0)
        w = bw * pulse
        h = bh * pulse
        arcade.draw_rect_filled(arcade.XYWH(bx, by, w, h), col)
        arcade.draw_rect_outline(arcade.XYWH(bx, by, w, h), COLOR_GOLD if highlight else (255, 255, 255), 2)
        arcade.draw_text(text, bx, by - 6, (255, 255, 255), 13, anchor_x="center", bold=True)

    # -------------------------------------------------------------------------
    # 3. RENDER: S08 Midnight Tarot Cards Tabletop Mode
    # -------------------------------------------------------------------------
    def _draw_tarot_cards(self):
        if self.ui_cam:
            self.ui_cam.use()

        # Deep Midnight Dining Tabletop
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (16, 14, 20))

        # Warm spotlight on the bowl in the center
        arcade.draw_circle_filled(SCREEN_WIDTH / 2, 220, 160, (235, 195, 110, 35))

        # Hot Bowl of Egg Noodles on the Table
        bowl_cx = SCREEN_WIDTH / 2
        bowl_cy = 135
        arcade.draw_ellipse_filled(bowl_cx, bowl_cy, 190, 60, (230, 225, 215))
        arcade.draw_ellipse_outline(bowl_cx, bowl_cy, 190, 60, (140, 110, 75), 4)
        # Golden broth
        arcade.draw_ellipse_filled(bowl_cx, bowl_cy + 5, 170, 45, (200, 150, 70))
        # Egg noodles
        arcade.draw_ellipse_filled(bowl_cx, bowl_cy + 8, 140, 34, (245, 230, 165))
        # Sunny-side egg resting on top
        arcade.draw_circle_filled(bowl_cx - 15, bowl_cy + 10, 24, (255, 255, 245))
        arcade.draw_circle_filled(bowl_cx - 15, bowl_cy + 10, 14, (245, 165, 30))
        # Chopsticks resting across rim
        arcade.draw_line(bowl_cx - 90, bowl_cy + 25, bowl_cx + 80, bowl_cy + 35, (160, 90, 45), 4)

        # Header Title
        title_bob = math.sin(self.t * 2.0) * 3.0
        arcade.draw_text("CHAPTER ONE: THREE CARDS AT MIDNIGHT", SCREEN_WIDTH / 2, 660 + title_bob, COLOR_GOLD, 22, anchor_x="center", bold=True)
        arcade.draw_text("A memory stirs within the warm broth. Inspect the three destiny cards.", SCREEN_WIDTH / 2, 625 + title_bob, (210, 215, 230), 13, anchor_x="center")

        # Draw Tarot Cards
        for card in self.tarot_cards:
            is_hover = card["hover"]
            col = card["color"]
            cx = card["cx"]
            cy = card["cy"] + (12 if is_hover else 0)
            w = card["w"]
            h = card["h"]

            # Card Background
            bg_shade = (32, 28, 40) if card["active"] else (22, 20, 26)
            arcade.draw_rect_filled(arcade.XYWH(cx, cy, w, h), bg_shade)
            border_col = COLOR_GOLD if is_hover else col
            border_thick = 3.0 if is_hover else 1.8
            arcade.draw_rect_outline(arcade.XYWH(cx, cy, w, h), border_col, border_thick)

            # Card Emblem / Art
            arcade.draw_rect_filled(arcade.XYWH(cx, cy + 40, w - 30, 120), (col[0] // 3, col[1] // 3, col[2] // 3))
            arcade.draw_rect_outline(arcade.XYWH(cx, cy + 40, w - 30, 120), col, 1.2)

            # Emblem Symbol
            symbol = "I" if card["id"] == "beast" else ("II" if card["id"] == "crown" else "III")
            arcade.draw_text(symbol, cx, cy + 24, col, 36, anchor_x="center", bold=True)

            # Title
            arcade.draw_text(card["name"], cx, cy - 42, (255, 250, 235), 14, anchor_x="center", bold=True)
            status_txt = "[ CLICK TO ENTER ]" if card["active"] else "[ LOCKED ]"
            status_col = COLOR_GOLD if (card["active"] and is_hover) else ((180, 185, 195) if card["active"] else (100, 105, 115))
            arcade.draw_text(status_txt, cx, cy - 80, status_col, 11, anchor_x="center", bold=True)

        # Inspecting Card Modal
        if self.inspecting_card:
            self._draw_tarot_inspect_modal()

        # Fade-to-black on transition to Scene 7
        if self.transitioning_to_scene_7 and self.fade_alpha > 0:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (0, 0, 0, int(self.fade_alpha))
            )

    def _draw_tarot_inspect_modal(self):
        card = self.inspecting_card
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0, 210))
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 700, 440), (24, 22, 32))
        arcade.draw_rect_outline(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, 700, 440), COLOR_GOLD, 2)

        arcade.draw_text(card["name"], SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 155, card["color"], 22, anchor_x="center", bold=True)
        arcade.draw_text(card["era"], SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 120, (200, 210, 230), 13, anchor_x="center")
        arcade.draw_line(SCREEN_WIDTH / 2 - 280, SCREEN_HEIGHT / 2 + 105, SCREEN_WIDTH / 2 + 280, SCREEN_HEIGHT / 2 + 105, (80, 85, 100), 1)

        # Lore description
        arcade.draw_text(card["desc"], SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 40, (235, 230, 220), 14,
                         anchor_x="center", width=560, align="center")

        # Action Buttons
        if card["active"]:
            arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 130, 320, 46), (185, 65, 45))
            arcade.draw_rect_outline(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 130, 320, 46), COLOR_GOLD, 2)
            arcade.draw_text("SELECT THE BEAST & BEGIN JOURNEY", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 137, (255, 255, 255), 13, anchor_x="center", bold=True)
        else:
            arcade.draw_text("[ Destiny locked. You must experience the past in causal order. ]", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 130, (160, 160, 170), 12, anchor_x="center")

        arcade.draw_text("[ Click outside to close ]", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 190, (140, 140, 150), 11, anchor_x="center")

    # =========================================================================
    # INPUT CONTROLS
    # =========================================================================
    def on_key_press(self, key, modifiers):
        if self.handle_pause_key(key):
            return

        if key == arcade.key.F11:
            self.toggle_fullscreen()
            return

        # Advance dialogue on SPACE / ENTER / E
        if self.dialogue.active:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                self.dialogue.advance()
            return

        # Exploration Controls
        if self.mode == MODE_EXPLORE_HOUSE:
            # If sitting on sofa, any movement key automatically stands the player up
            if self.is_sitting_on_sofa and key in (
                arcade.key.A, arcade.key.LEFT, arcade.key.D, arcade.key.RIGHT,
                arcade.key.W, arcade.key.UP, arcade.key.S, arcade.key.DOWN
            ):
                self.is_sitting_on_sofa = False
                self.player.place(910.0, 310.0)
                self.audio.play("click")

            if key in (arcade.key.A, arcade.key.LEFT):
                self.key_left = True
            elif key in (arcade.key.D, arcade.key.RIGHT):
                self.key_right = True
            elif key in (arcade.key.W, arcade.key.UP):
                self.key_up = True
            elif key in (arcade.key.S, arcade.key.DOWN):
                self.key_down = True
            elif key in (arcade.key.LSHIFT, arcade.key.RSHIFT):
                self.key_shift = True

            # Interaction Key [E]
            elif key == arcade.key.E:
                self._handle_exploration_interact()

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.A, arcade.key.LEFT):
            self.key_left = False
        elif key in (arcade.key.D, arcade.key.RIGHT):
            self.key_right = False
        elif key in (arcade.key.W, arcade.key.UP):
            self.key_up = False
        elif key in (arcade.key.S, arcade.key.DOWN):
            self.key_down = False
        elif key in (arcade.key.LSHIFT, arcade.key.RSHIFT):
            self.key_shift = False

    def _handle_exploration_interact(self):
        px = self.player.x
        py = self.player.y - FEET_OFFSET + 8
        target = self.precision.active()

        # 1. Sofa Interaction (Sit Down / Stand Up)
        if target == "sofa":
            if self.is_sitting_on_sofa:
                # Stand up from sofa
                self.is_sitting_on_sofa = False
                self.player.x = 910.0
                self.player.y = 310.0  # Step down in front of the sofa
                self.player.sprite.center_x = 910.0
                self.player.sprite.center_y = 310.0
                self.audio.play("click")
            else:
                # Sit down on sofa
                self.is_sitting_on_sofa = True
                self.player.x = 737.5
                self.player.y = 330.0
                self.player.sprite.center_x = 737.5
                self.player.sprite.center_y = 330.0
                self.audio.play("click")
                self.dialogue.start_dialogue([
                    ("Emerald Velvet Sofa", "He sinks into the familiar green velvet cushions under the dust cloth.\nThe room feels still, filled with a heavy silence of years gone by.", (205, 215, 230)),
                    ("Chef", "\"Just five minutes of rest... before facing what comes tomorrow.\"", (220, 205, 175), self.portrait_thinking),
                    ("Instruction", "[ Press [E] or move W/A/S/D to stand back up. ]", COLOR_GOLD)
                ])
            return

        # 2. Floor Lamp Switch (Beside Sofa)
        if target == "floor_lamp":
            self.floor_lamp_on = not self.floor_lamp_on
            self.audio.play("click")
            status = "lights up with a warm amber glow" if self.floor_lamp_on else "clicks softly and dims away"
            self.dialogue.start_dialogue([
                ("Floor Lamp", f"The vintage brass lamp {status}.", (255, 220, 130))
            ])
            return

        # 3. Dining Table Remote Control (Toggles Overhead Chandelier)
        if target == "remote":
            self.dining_lamp_on = not self.dining_lamp_on
            self.audio.play("click")
            status = "ignites the overhead brass chandelier, casting a warm spotlight over the table" if self.dining_lamp_on else "switches off the overhead chandelier"
            self.dialogue.start_dialogue([
                ("Table Remote Control", f"He picks up the small controller from the table and clicks the switch.\nThe ceiling light {status}.", (255, 220, 130))
            ])
            return

        # 4. West (Left) Window Curtains
        if target == "window_left":
            self.window_left_open = not self.window_left_open
            self.audio.play("click")
            status = "He pulls aside the crimson velvet drapes. Cool moonlight and rain streak down the glass panes." if self.window_left_open else "He draws the heavy velvet curtains closed against the storm."
            self.dialogue.start_dialogue([
                ("West Window", status, (170, 210, 245))
            ])
            return

        # 5. East (Right) Window Curtains
        if target == "window_right":
            self.window_right_open = not self.window_right_open
            self.audio.play("click")
            status = "He parts the eastern drapes. Outside, the rain glistens against the night sky." if self.window_right_open else "He pulls the curtains shut, shutting out the dark outside world."
            self.dialogue.start_dialogue([
                ("East Window", status, (170, 210, 245))
            ])
            return

        # 6. Vanity Dresser / Foreclosure Letters
        if target == "vanity":
            self.audio.play("click")
            self.dialogue.start_dialogue([
                ("Entryway Vanity", "A stack of unopened mail covered in dust. On top rests a red-stamped foreclosure notice from the municipal court.", (220, 180, 140)),
                ("Court Notice", "\"Final Notice of Property Seizure: All assets and real estate forfeitures are non-negotiable.\"", (245, 95, 80)),
                ("Chef", "\"As if the empty rooms weren't enough of a reminder...\"", (215, 200, 175), self.portrait_thinking)
            ])
            return

        # 7. Fireplace, Trophy & Wall Clock
        if target == "fireplace":
            self.audio.play("clue_match")
            clock_text = f"Higher on the chimney breast, the heavy brass wall clock ticks quietly: {self.clock_time}."
            self.dialogue.start_dialogue([
                ("Cold Hearth", "The stone fireplace has been dark and cold for weeks. Above it rests his Grand Prix trophy.", (220, 190, 150)),
                ("Grand Prix 2023", "Engraved in polished brass: 'For Uncompromising Mastery in Modern Culinary Arts.'", COLOR_GOLD),
                ("Framed Photo", "Beside the trophy rests a small framed photograph from the grand opening night of his restaurant.", (215, 200, 180)),
                ("Wall Clock", clock_text, (245, 215, 120)),
                ("Chef", "\"I sacrificed every waking hour chasing that golden badge. And when the unverified salt was served... not a single judge remembered this trophy.\"", (230, 205, 160), self.portrait_thinking)
            ])
            return

        # 8. Bookshelf & Gastronomy Volumes
        if target == "bookshelf":
            self.audio.play("click")
            self.dialogue.start_dialogue([
                ("Bookshelf", "Gastronomy encyclopedias, culinary chemistry manuals, and French technique journals left behind on the carved oak shelves.", (200, 190, 170)),
                ("Cardboard Cartons", "Heavy brown boxes taped and labeled in thick black marker: 'RECIPES & JOURNALS', 'CHEF KNIVES'.", (210, 185, 140)),
                ("Chef", "\"Twelve years of kitchen experiments, reduced to four cardboard cartons on the floor.\"", (225, 210, 180), self.portrait_chef)
            ])
            return

        # 9. Monstera Houseplant
        if target == "monstera":
            self.audio.play("click")
            self.dialogue.start_dialogue([
                ("Monstera Plant", "A potted split-leaf monstera sits beside the sofa, its broad leaves drooping from weeks without water.", (160, 190, 170)),
                ("Chef", "\"Even the plants have dried out. Tomorrow the auctioneers will carry away the sofa.\"", (215, 200, 175), self.portrait_thinking)
            ])
            return

        # 10. East Kitchen Doorway
        if px >= 1480 and 180 <= py <= 460:
            self.audio.play("door_creak")
            from scenes.scene_7_kitchen_view import KitchenView
            self.window.show_view(KitchenView())
            return

    def on_mouse_motion(self, x, y, dx, dy):
        if self.handle_pause_mouse_motion(x, y):
            return

        vx, vy = self.to_virtual_coords(x, y)

        if self.mode == MODE_TAROT_CARDS:
            for card in self.tarot_cards:
                cx = card["cx"]
                cy = card["cy"]
                w = card["w"]
                h = card["h"]
                card["hover"] = (abs(vx - cx) <= w / 2 and abs(vy - cy) <= h / 2)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.handle_pause_mouse_press(x, y, button):
            return

        vx, vy = self.to_virtual_coords(x, y)

        if self.dialogue.active:
            self.dialogue.advance()
            return

        # ---------------------------------------------------------------------
        # Cooking Mama Clicks
        # ---------------------------------------------------------------------
        if self.mode == MODE_COOKING_MAMA:
            # Step 1: Turn On Faucet
            if self.cook_step == COOK_STEP_FILL_WATER:
                # Faucet valve button or valve area
                if abs(vx - (390 - 40)) <= 90 and 500 <= vy <= 640:
                    self.is_filling_water = True
                    self.audio.play("boil")
                    return

            # Step 2: Ignite Burner (Stove Knob)
            elif self.cook_step == COOK_STEP_IGNITE_STOVE:
                if math.hypot(vx - 390, vy - 130) <= 45:
                    self.stove_ignited = True
                    self.audio.play("click")
                    self.audio.play("sizzle")
                    self.dialogue.start_dialogue([
                        ("Burner Ignited", "The gas ignites with a quiet whoosh! Clear blue flames ring the burner.\nWait for the water to reach a rolling boil.", (120, 210, 255))
                    ])
                    return

            # Step 3: Add Noodles
            elif self.cook_step == COOK_STEP_ADD_NOODLES:
                if abs(vx - 390) <= 120 and 400 <= vy <= 480:
                    self.noodles_added = True
                    self.cook_step = COOK_STEP_FRY_EGG
                    self.audio.play("boil")
                    self.dialogue.start_dialogue([
                        ("Noodles Added", "Dry noodles slip into the boiling broth, instantly softening in the steam.\nNow crack and fry an egg in the side skillet.", (245, 220, 160))
                    ])
                    return

            # Step 4: Fry Egg
            elif self.cook_step == COOK_STEP_FRY_EGG:
                if abs(vx - 840) <= 120 and 400 <= vy <= 480:
                    self.egg_cracked = True
                    self.eggshell_present = True
                    self.cook_step = COOK_STEP_EGGSHELL_MEMORY
                    self.audio.play("chop")
                    self.audio.play("sizzle")
                    return

            # Step 5: Scoop Out Fallen Eggshell (S07 Key Clue!)
            elif self.cook_step == COOK_STEP_EGGSHELL_MEMORY:
                es_x = 840 - 40
                es_y = 280 + 25
                if math.hypot(vx - es_x, vy - es_y) <= 35:
                    self.eggshell_removed = True
                    self.cook_step = COOK_STEP_ASSEMBLE_DISH
                    self.audio.play("clue_match")
                    # S07 Narrative Flashback Memory
                    script = [
                        (
                            "Memory: The Eggshell",
                            "While cracking the egg, a small sharp fragment of shell falls into the pan.\nHe pauses, staring at it motionless.",
                            (210, 175, 120)
                        ),
                        (
                            "Family Member",
                            "\"Don't just stare at it. Use the other half of the eggshell to scoop it out gently.\"",
                            (245, 220, 160)
                        ),
                        (
                            "Family Member",
                            "\"Eat first, then face tomorrow.\nA full stomach gives you the courage to stand back up.\"",
                            (245, 220, 160)
                        ),
                        (
                            "Chef",
                            "\"...Eat first, then face tomorrow.\"",
                            (235, 210, 175),
                            self.portrait_thinking
                        ),
                        (
                            "Instruction",
                            "[ Press 'SERVE EGG NOODLE SOUP' to complete the dish. ]",
                            COLOR_GOLD
                        )
                    ]
                    self.dialogue.start_dialogue(script)
                    return

            # Step 6: Assemble & Finish Dish
            elif self.cook_step == COOK_STEP_ASSEMBLE_DISH:
                if abs(vx - SCREEN_WIDTH / 2) <= 160 and abs(vy - 80) <= 28:
                    self.cook_step = COOK_STEP_FINISHED
                    self.audio.play("achievement")
                    self.mode = MODE_TAROT_CARDS
                    self.dialogue.start_dialogue([
                        (
                            "A Bowl of Noodles",
                            "He sets down the hot bowl on the quiet wooden table.\nA comforting aroma of simple egg and broth rises through the dim room.",
                            (220, 205, 180)
                        ),
                        (
                            "Midnight Anomaly",
                            "As the steam rises, three ancient cards begin to shimmer upon the tabletop...",
                            COLOR_GOLD
                        )
                    ])
                    return

        # ---------------------------------------------------------------------
        # Tarot Cards Clicks (S08)
        # ---------------------------------------------------------------------
        elif self.mode == MODE_TAROT_CARDS:
            if self.inspecting_card:
                # Click 'Select Card' button
                if self.inspecting_card["active"]:
                    if abs(vx - SCREEN_WIDTH / 2) <= 160 and abs(vy - (SCREEN_HEIGHT / 2 - 130)) <= 25:
                        self.audio.play("card_flip")
                        self.audio.play("time_warp")
                        self.selected_card = self.inspecting_card["id"]
                        self.transitioning_to_scene_7 = True
                        self.inspecting_card = None
                        return
                # Close modal if clicked outside
                if abs(vx - SCREEN_WIDTH / 2) > 350 or abs(vy - SCREEN_HEIGHT / 2) > 220:
                    self.inspecting_card = None
                    self.audio.play("click")
                return

            # Inspect card click
            for card in self.tarot_cards:
                cx = card["cx"]
                cy = card["cy"]
                w = card["w"]
                h = card["h"]
                if abs(vx - cx) <= w / 2 and abs(vy - cy) <= h / 2:
                    self.inspecting_card = card
                    self.audio.play("card_flip")
                    return


# Standalone runner for direct testing
if __name__ == "__main__":
    window = arcade.Window(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Scene 6: Home Kitchen & Midnight Tarot Cards (S06 - S08)",
        resizable=False,
        fullscreen=START_FULLSCREEN
    )
    if START_FULLSCREEN:
        window.set_fullscreen(True)
    view = HomeKitchenView()
    window.show_view(view)
    arcade.run()

