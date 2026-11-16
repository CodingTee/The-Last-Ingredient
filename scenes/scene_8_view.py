"""Scene 8: the chef leaves the kitchen and turns over a card on his way out."""
import math
import random
import sys
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw

# Add project root to path for standalone execution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import arcade
from arcade.types import LRBT
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD,
    ASSETS_DIR, START_FULLSCREEN, SCENE_7_DIR
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
MODE_TABLETOP_CARDS = 1

# Tabletop Tarot Card Configuration (Referencing Scene 13)
CX, CY = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
CARD_Y = 305
CARD_WIDTH, CARD_HEIGHT = 144, 216
TRANSITION_END = 2.4


def smoothstep(value: float) -> float:
    progress = max(0.0, min(1.0, value))
    return progress * progress * (3 - 2 * progress)


class Scene8View(BaseGameView):
    """Scene 8 View: S08 Three Cards at Midnight."""

    def __init__(self, meal_finished=True):
        super().__init__()
        self.audio = AudioManager()
        self.t = 0.0

        # Mode State
        self.mode = MODE_EXPLORE_HOUSE
        self.meal_finished_in_kitchen=meal_finished

        # Cameras (2D Smooth Tracking)
        self.world_cam = None
        self.ui_cam = None
        self.cam_x = 1260.0
        self.cam_y = 300.0

        # Dialogue System
        self.dialogue = DialogueBox()

        # Exploration Player: Modern Chef (Starts right beside the dining table)
        self.player = Player(x=1265.0, y=140.0, char_id="modern")
        self.player.footstep_sound = "scene_8_wood_step"
        if meal_finished:self.player.place(1490,300)
        self.player.speed = 220.0
        self.dust_particles = []

        # Sitting on sofa state
        self.is_sitting_on_sofa = False
        self.sitting_pos = (740.0, 343.0)
        char_sit_path = str(ASSETS_DIR / "characters" / "modern" / "char_sit.png")
        self.tex_char_sit = arcade.load_texture(char_sit_path)

        # Environment Textures (Background Dark & Background Light)
        scene6_dir = ASSETS_DIR / "Scene 6"
        self.tex_bg_dark = arcade.load_texture(str(scene6_dir / "Background Dark.png"))
        self.tex_bg_light = arcade.load_texture(str(scene6_dir / "Background Light.png"))

        # Dynamic Wall Clock States (Set to 12:00 Midnight for Scene 8)
        self.clock_time = "12:00"
        clocks_dir = scene6_dir / "precision" / "clocks"
        self.tex_clocks = {
            "11:00": arcade.load_texture(str(clocks_dir / "wall_clock_11_00_dark.png")),
            "00:00": arcade.load_texture(str(clocks_dir / "wall_clock_00_00_dark.png")),
            "12:00": arcade.load_texture(str(clocks_dir / "wall_clock_00_00_dark.png")),
            "03:00": arcade.load_texture(str(clocks_dir / "wall_clock_03_00_dark.png")),
            "06:00": arcade.load_texture(str(clocks_dir / "wall_clock_06_00_dark.png")),
        }

        # Interactive Light & Window States (Starts with dining lamp on to spotlight the meal)
        self.window_left_open = False
        self.window_right_open = False
        self.floor_lamp_on = False
        self.dining_lamp_on = True

        self.intensity_floor_lamp = 0.0
        self.intensity_dining_lamp = 1.0
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
            for _ in range(40)
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

        # Character Portraits
        scene1_dir = ASSETS_DIR / "Scene 1"
        self.portrait_chef = arcade.load_texture(str(scene1_dir / "Modern Chief.png"))
        self.portrait_thinking = arcade.load_texture(str(scene1_dir / "Chief Thinking.png"))

        # Steam particles rising from the soup bowl on the dining table
        self.table_steam = []
        self.meal_textures={n:arcade.load_texture(SCENE_7_DIR/'sprites'/(n+'.png')) for n in ('bowl_soup','chopsticks')}

        # ---------------------------------------------------------------------
        # S08 Tabletop Tarot Cards State
        # ---------------------------------------------------------------------
        self.tarot_cards = [
            {
                "id": "beast",
                "name": "THE BEAST",
                "era": "Prehistoric Era · Primeval Camp & Jungle",
                "roman": "I",
                "desc": "A dark beast turns toward a pale moon. Its eyes seem to catch the light as you tilt the card.",
                "color": (225, 115, 45),
                "cx": CX - 280,
                "cy": CARD_Y,
                "hover": False,
                "active": True
            },
            {
                "id": "crown",
                "name": "THE CROWN",
                "era": "Royal Court Era · Grand Kitchen c.1910",
                "roman": "II",
                "desc": "A gilded crown rests against a sunburst, framed by twisting vines.",
                "color": (225, 185, 65),
                "cx": CX,
                "cy": CARD_Y,
                "hover": False,
                "active": False  # Locked during shared timeline
            },
            {
                "id": "gear",
                "name": "THE GEAR",
                "era": "Future Era · Neural Synthesis Laboratory",
                "roman": "III",
                "desc": "Interlocking gears catch a cold blue light. Fine traces run between the teeth like circuits.",
                "color": (65, 190, 240),
                "cx": CX + 280,
                "cy": CARD_Y,
                "hover": False,
                "active": False  # Locked during shared timeline
            }
        ]

        card_dir = ASSETS_DIR / "prehistoric" / "cooking_v2"
        self.beast_card_texture = arcade.load_texture(card_dir / "beast_card.png")
        self.blurred_beast = arcade.Texture(
            self.beast_card_texture.image.filter(ImageFilter.GaussianBlur(14))
        )

        closeup_dir = ASSETS_DIR / "Scene 8"
        self.tabletop_texture = arcade.load_texture(closeup_dir / "tabletop.png")
        self.card_back_texture = arcade.load_texture(closeup_dir / "card_back.png")
        self.card_turn_time = 0.0
        self.tabletop_steam = []

        # Transition to Scene 9 (Vision blur and zoom to center, referencing Scene 13)
        self.transitioning_to_scene_9 = False
        self.time_warp_played = False
        self._trigger_intro_dialogue()

    def set_clock_time(self, time_str: str):
        """Update the time displayed on the fireplace wall clock ('11:00', '00:00', '12:00', '03:00', '06:00')."""
        if time_str in self.tex_clocks:
            self.clock_time = time_str

    def _trigger_intro_dialogue(self):
        self.dialogue.start_dialogue([
            ("Chef", "I should get out of here while I still can.", (230, 210, 175), self.portrait_thinking),
        ])

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
            self.world_cam.projection = LRBT(-SCREEN_HEIGHT*w/h/2, SCREEN_HEIGHT*w/h/2, -SCREEN_HEIGHT/2, SCREEN_HEIGHT/2)
        if self.ui_cam:
            self.ui_cam.viewport = LRBT(0, w, 0, h)
            self.ui_cam.projection = LRBT(-SCREEN_HEIGHT*w/h/2, SCREEN_HEIGHT*w/h/2, -SCREEN_HEIGHT/2, SCREEN_HEIGHT/2)
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

            self.player.speed = 360.0 if self.key_shift else 220.0
            self.player.step_interval = 0.09 if self.key_shift else 0.13

            if not self.is_sitting_on_sofa:
                self.player.update(
                    dt, move_x, move_y,
                    dust_particles=self.dust_particles,
                    bounds=(140.0, 1560.0, FLOOR_Y_MIN, FLOOR_Y_MAX),
                    obstacles=self.furniture_colliders
                )

            # Camera Smooth Tracking in X and Y
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

            # Dining Table Steam (World Coordinates at Dining Table x=1265, y=260)
            if not self.meal_finished_in_kitchen and len(self.table_steam) < 18 and random.random() < 0.4:
                self.table_steam.append({
                    "x": 1265.0 + random.uniform(-18, 18),
                    "y": 268.0,
                    "vx": random.uniform(-4, 4),
                    "vy": random.uniform(16, 28),
                    "size": random.uniform(5.0, 9.0),
                    "alpha": random.randint(70, 120)
                })

            for p in self.table_steam[:]:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["size"] += dt * 7.0
                p["alpha"] -= dt * 45.0
                if p["alpha"] <= 0:
                    self.table_steam.remove(p)

            # Smooth Light Interpolations
            target_fl = 1.0 if self.floor_lamp_on else 0.0
            self.intensity_floor_lamp += (target_fl - self.intensity_floor_lamp) * min(1.0, dt * 6.0)

            target_dl = 1.0 if self.dining_lamp_on else 0.0
            self.intensity_dining_lamp += (target_dl - self.intensity_dining_lamp) * min(1.0, dt * 6.0)

            target_wl = 1.0 if self.window_left_open else 0.0
            self.intensity_window_left += (target_wl - self.intensity_window_left) * min(1.0, dt * 6.0)

            target_wr = 1.0 if self.window_right_open else 0.0
            self.intensity_window_right += (target_wr - self.intensity_window_right) * min(1.0, dt * 6.0)

        # ---------------------------------------------------------------------
        # 2. Update Tabletop Cards Mode (S08)
        # ---------------------------------------------------------------------
        elif self.mode == MODE_TABLETOP_CARDS:
            # Tabletop rising steam puffs
            if not self.meal_finished_in_kitchen and len(self.tabletop_steam) < 22 and random.random() < 0.35:
                self.tabletop_steam.append({
                    "x": SCREEN_WIDTH / 2 - 120 + random.uniform(-25, 25),
                    "y": 140.0,
                    "vx": random.uniform(-5, 5),
                    "vy": random.uniform(22, 38),
                    "size": random.uniform(7.0, 12.0),
                    "alpha": random.randint(90, 140)
                })

            for p in self.tabletop_steam[:]:
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["size"] += dt * 9.0
                p["alpha"] -= dt * 50.0
                if p["alpha"] <= 0:
                    self.tabletop_steam.remove(p)

            # Vision blur transition for The Beast card (reference Scene 13)
            if self.transitioning_to_scene_9:
                self.card_turn_time += dt
                if self.card_turn_time >= 0.8 and not self.time_warp_played:
                    self.time_warp_played = True
                    self.audio.play("time_warp", volume_scale=0.7)
                if self.card_turn_time >= TRANSITION_END:
                    self._proceed_to_scene_9()

    def _proceed_to_scene_9(self):
        """Transition into Chapter Two: Prehistoric Era Primeval Forest (Scene 9)."""
        from scenes.scene_9_view import Scene9View
        self.transitioning_to_scene_9 = False
        self.window.show_view(Scene9View())

    # =========================================================================
    # DRAW LOGIC
    # =========================================================================
    def on_draw(self):
        self.clear(color=(12, 14, 20))

        if self.mode == MODE_EXPLORE_HOUSE:
            self._draw_house_exploration()
        elif self.mode == MODE_TABLETOP_CARDS:
            self._draw_tabletop_cards()

        # UI Overlay (Dialogue & Notifications)
        if self.ui_cam:
            self.ui_cam.use()

        # Draw Dialogue
        if self.dialogue.active:
            self.dialogue.draw()

        # Draw Pause Menu
        self.draw_pause_overlay()

    # -------------------------------------------------------------------------
    # 1. RENDER: House Exploration Mode
    # -------------------------------------------------------------------------
    def _draw_house_exploration(self):
        if self.world_cam:
            self.world_cam.position = (self.cam_x, self.cam_y)
            self.world_cam.use()

        # Base Environment (1678 x 937)
        arcade.draw_texture_rect(
            self.tex_bg_dark,
            arcade.XYWH(HOUSE_WORLD_WIDTH / 2, HOUSE_WORLD_HEIGHT / 2, HOUSE_WORLD_WIDTH, HOUSE_WORLD_HEIGHT)
        )

        # Dynamic Wall Clock on Chimney Wall (Position A: X=834, Y=841 in Arcade coords, 12:00 Midnight)
        if self.clock_time in self.tex_clocks:
            arcade.draw_texture_rect(
                self.tex_clocks[self.clock_time],
                arcade.XYWH(834.0, 841.0, 72.0, 72.0)
            )

        pulse = 0.5 + 0.5 * math.sin(self.t * 5.0)
        active_prompt = self.precision.draw()

        # Draw Bowl of Egg Noodles & Mysterious Box on Dining Table (World: 1265, 260)
        table_x = 1265.0
        table_y = 250.0

        if not self.meal_finished_in_kitchen:self._meal_sprite('bowl_soup',table_x-30,table_y+5,48,36)

        # Rising steam from table bowl
        for p in self.table_steam:
            arcade.draw_circle_filled(p["x"], p["y"], p["size"], (235, 240, 255, int(p["alpha"])))

        # Floating Dust Particles in Air
        for dm in self.dust_motes:
            arcade.draw_circle_filled(dm["x"], dm["y"], dm["r"], (210, 230, 255, dm["alpha"]))

        # Override prompt when near dining table for S08 clear table & box inspection
        px, py = self.player.x, self.player.y
        dist_table = math.hypot(px - 1265, py - 240)
        if dist_table < 130 and not self.dialogue.active:
            self._draw_world_prompt(1265, 340, "[Click or E] Examine Table", scale=1.0 + 0.05 * pulse, highlight=True)
        elif active_prompt:
            wx, wy, prompt_text, is_highlight = active_prompt
            self._draw_world_prompt(wx, wy, prompt_text, scale=1.0 + 0.05 * pulse, highlight=is_highlight)

    def _meal_sprite(self,name,x,y,w,h):
        texture=self.meal_textures[name]
        scale=min(w/texture.width,h/texture.height)
        arcade.draw_texture_rect(texture,arcade.XYWH(x,y,texture.width*scale,texture.height*scale))

    def _draw_world_prompt(self, wx, wy, text, scale=1.0, highlight=False):
        bw = 310 * scale
        bh = 40 * scale
        col_bg = (24, 28, 40, 225) if highlight else (15, 18, 24, 200)
        col_border = COLOR_GOLD if highlight else (140, 150, 175)
        arcade.draw_rect_filled(arcade.XYWH(wx, wy, bw, bh), col_bg)
        arcade.draw_rect_outline(arcade.XYWH(wx, wy, bw, bh), col_border, 1.6)
        arcade.draw_text(text, wx, wy - 5, (255, 250, 235), 11 * scale, anchor_x="center", bold=highlight)

    def shade(self, color, amount):
        arcade.draw_rect_filled(
            arcade.XYWH(CX, CY, SCREEN_WIDTH, SCREEN_HEIGHT),
            (*color, int(255 * max(0.0, min(1.0, amount)))),
        )

    def draw_beast_transition(self):
        time = self.card_turn_time
        zoom = 1.0 + 1.35 * smoothstep(time / 1.25)
        width = max(4.0, CARD_WIDTH * zoom * abs(1.0 - 2.0 * min(1.0, time / 0.46)))
        height = CARD_HEIGHT * zoom
        start_x = CX - 280
        x = start_x + (CX - start_x) * smoothstep(time / 0.7)
        y = CARD_Y + (CY - CARD_Y) * smoothstep(time / 0.7)
        rect = arcade.XYWH(x, y, width, height)

        # Ambient darkness shade (dims the table and other cards, reference Scene 13)
        self.shade((6, 16, 10), 0.8 * smoothstep(time / 0.65))

        # Base card (flips from card_back to beast)
        arcade.draw_texture_rect(
            self.card_back_texture if time < 0.23 else self.beast_card_texture,
            rect,
        )

        # Prehistoric emerald glow aura pulsing around the card as it turns face up
        if time >= 0.46:
            p_aura = min(1.0, (time - 0.46) / 0.8)
            aura_alpha = int(220 * math.sin(p_aura * math.pi))
            if aura_alpha > 0:
                arcade.draw_rect_outline(rect, (75, 235, 125, aura_alpha), 3.0)

        # Vision blur layer
        blur = smoothstep((time - 0.8) / 0.85)
        if blur > 0:
            arcade.draw_texture_rect(self.blurred_beast, rect, alpha=int(255 * blur))

        # Prehistoric green light flooding the player's vision (Green light of the prehistoric jungle)
        self.shade((55, 215, 110), 0.78 * smoothstep((time - 1.1) / 0.65))

        # Fade to pitch black
        self.shade((0, 0, 0), smoothstep((time - 1.78) / 0.57))

    # -------------------------------------------------------------------------
    # 2. RENDER: S08 Midnight Tabletop & Tarot Cards Close-up Mode
    # -------------------------------------------------------------------------
    def _draw_tabletop_cards(self):
        if self.ui_cam:
            self.ui_cam.use()

        texture = self.tabletop_texture
        viewport_width = SCREEN_HEIGHT * self.window.width / self.window.height
        scale = max(viewport_width / texture.width, SCREEN_HEIGHT / texture.height)
        w_tex = texture.width * scale
        h_tex = texture.height * scale

        # 1. Base Tabletop
        arcade.draw_texture_rect(
            texture,
            arcade.XYWH(CX, CY, w_tex, h_tex),
        )

        # 2. Tabletop steam (soft warm ambient puffs)
        for p in self.tabletop_steam:
            arcade.draw_circle_filled(p["x"], p["y"], p["size"], (235, 240, 255, int(p["alpha"])))

        # 3. Transition: draw other cards at rest, then draw moving & magnifying Beast card
        if self.transitioning_to_scene_9:
            for index in (1, 2):
                card = self.tarot_cards[index]
                rect = arcade.XYWH(card["cx"], card["cy"], CARD_WIDTH, CARD_HEIGHT)
                arcade.draw_texture_rect(self.card_back_texture, rect)
            self.draw_beast_transition()
            return

        # 4. Normal Mode: Tarot Cards
        for index, card in enumerate(self.tarot_cards):
            x = card["cx"]
            y = card["cy"] + (8 if card["hover"] else 0)
            rect = arcade.XYWH(x, y, CARD_WIDTH, CARD_HEIGHT)
            arcade.draw_texture_rect(self.card_back_texture, rect)
            if card["hover"]:
                outline_color = (80, 225, 125, 220) if index == 0 else (238, 186, 91, 210)
                arcade.draw_rect_outline(rect, outline_color, 2)

        if not self.dialogue.active:
            arcade.draw_text(
                "Click the first card or press Enter",
                CX, 75, (205, 245, 215), 14, anchor_x="center"
            )

    def on_key_press(self, key, modifiers):
        if self.transitioning_to_scene_9:
            return
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
            # Stand up from sofa
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

            # Interactive Trigger [E]
            if key == arcade.key.E:
                self._handle_exploration_interact()

        elif self.mode == MODE_TABLETOP_CARDS:
            if key == arcade.key.ESCAPE:
                self.mode = MODE_EXPLORE_HOUSE
            elif key in (arcade.key.ENTER, arcade.key.SPACE, arcade.key.E):
                self._activate_beast_card()

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
        if not (self.key_up or self.key_down or self.key_left or self.key_right):
            self.player.stop_footstep()

    def _handle_exploration_interact(self):
        """Handle player interaction with objects and landmarks in exploration mode."""
        px, py = self.player.x, self.player.y

        # 1. Dining Table Interaction -> Enter S08 Midnight Mode!
        dist_table = math.hypot(px - 1265, py - 240)
        if dist_table < 130:
            self._enter_tabletop_cards_mode()
            return

        target = self.precision.active()
        if not target:
            return

        # 2. Sofa Interaction
        if target == "sofa":
            if not self.is_sitting_on_sofa:
                self.is_sitting_on_sofa = True
                self.player.place(*self.sitting_pos)
                self.audio.play("click")
                self.dialogue.start_dialogue([
                    ("Old Sofa", "He sinks into the familiar dust-sheeted cushions.\nThe wall clock ticks softly in the silence, having passed midnight.", (210, 185, 140), self.portrait_thinking)
                ])
            else:
                self.is_sitting_on_sofa = False
                self.player.place(910.0, 310.0)
                self.audio.play("click")
            return

        # 3. Floor Lamp Switch
        if target == "floor_lamp":
            self.floor_lamp_on = not self.floor_lamp_on
            self.audio.play("click")
            status = "turns on the warm vintage standing lamp" if self.floor_lamp_on else "turns off the standing lamp"
            self.dialogue.start_dialogue([
                ("Floor Lamp", f"The brass floor switch clicks. He {status}.", (255, 230, 140))
            ])
            return

        # 4. Dining Table Remote (Chandelier)
        if target == "remote":
            self.dining_lamp_on = not self.dining_lamp_on
            self.audio.play("click")
            status = "illuminates the dining table and the steaming bowl of soup" if self.dining_lamp_on else "switches off the overhead chandelier"
            self.dialogue.start_dialogue([
                ("Table Remote Control", f"He picks up the small controller from the table.\nThe ceiling chandelier {status}.", (255, 220, 130))
            ])
            return

        # 5. Window Curtains
        if target == "window_left":
            self.window_left_open = not self.window_left_open
            self.audio.play("click")
            self.dialogue.start_dialogue([
                ("West Window", "Rainwater continues to run down the cold windowpane into the dark garden.", (180, 205, 235))
            ])
            return

        if target == "window_right":
            self.window_right_open = not self.window_right_open
            self.audio.play("click")
            self.dialogue.start_dialogue([
                ("East Window", "The stormy clouds outside part slightly, letting pale moonlight gleam across the floor.", (180, 205, 235))
            ])
            return

        # 6. Hearth, Trophy, Framed Photo & Wall Clock
        if target == "fireplace":
            self.audio.play("clue_match")
            clock_text = f"Higher on the chimney breast, the heavy brass wall clock has struck midnight: {self.clock_time}."
            self.dialogue.start_dialogue([
                ("Cold Hearth", "The stone fireplace has been dark and cold for weeks. Above it rests his Grand Prix trophy.", (220, 190, 150)),
                ("Grand Prix 2023", "Engraved in polished brass: 'For Uncompromising Mastery in Modern Culinary Arts.'", COLOR_GOLD),
                ("Framed Photo", "Beside the trophy rests the small framed photograph from the grand opening night of his restaurant.", (215, 200, 180)),
                ("Wall Clock", clock_text, (245, 215, 120)),
                ("Chef", "\"Twelve o'clock. The deadline has passed. Whatever comes tomorrow... tonight, there is only this silence.\"", (230, 205, 160), self.portrait_thinking)
            ])
            return

        # 7. Bookshelf
        if target == "bookshelf":
            self.dialogue.start_dialogue([
                ("Bookshelf", "Volumes on classical gastronomy, ancient medicinal herbs, and botanical compounds.", (200, 190, 170))
            ])
            return

        # 8. Vanity Dresser
        if target == "vanity":
            self.dialogue.start_dialogue([
                ("Vanity", "Bank repossession notices and sealed envelopes lie neatly stacked on the dresser.", (210, 170, 150))
            ])
            return

        # 9. Monstera Plant
        if target == "monstera":
            self.dialogue.start_dialogue([
                ("Monstera", "The broad waxy leaves are dry. Life has been paused here for a long time.", (160, 200, 160))
            ])
            return

    def _enter_tabletop_cards_mode(self):
        self.mode = MODE_TABLETOP_CARDS
        for card in self.tarot_cards:
            card["hover"] = False
        self.audio.play("clock_chime")

    def _card_contains(self, card, x, y):
        lift = 8 if card["hover"] else 0
        return abs(x - card["cx"]) <= CARD_WIDTH / 2 and abs(y - (card["cy"] + lift)) <= CARD_HEIGHT / 2

    def _activate_beast_card(self):
        if not self.transitioning_to_scene_9:
            self.transitioning_to_scene_9 = True
            self.card_turn_time = 0.0
            self.time_warp_played = False
            self.audio.play("card_flip")

    def on_mouse_motion(self, x, y, dx, dy):
        if self.handle_pause_mouse_motion(x, y):
            return
        if self.mode == MODE_TABLETOP_CARDS and not self.transitioning_to_scene_9:
            vx, vy = self._window_to_virtual_coords(x, y)
            for card in self.tarot_cards:
                card["hover"] = self._card_contains(card, vx, vy)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.transitioning_to_scene_9 or self.handle_pause_mouse_press(x, y, button):
            return
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        if self.dialogue.active:
            self.dialogue.advance()
            return

        vx, vy = self._window_to_virtual_coords(x, y)
        if self.mode == MODE_EXPLORE_HOUSE:
            near_table = math.hypot(self.player.x - 1265, self.player.y - 240) < 130
            wx = vx + self.cam_x - SCREEN_WIDTH / 2
            wy = vy + self.cam_y - SCREEN_HEIGHT / 2
            if near_table and abs(wx - 1265) <= 110 and 203 <= wy <= 365:
                self._enter_tabletop_cards_mode()
            return

        for index, card in enumerate(self.tarot_cards):
            if self._card_contains(card, vx, vy):
                if index == 0:
                    self._activate_beast_card()
                else:
                    self.dialogue.start_dialogue([
                        ("Chef", "Maybe I should start with the first card.", (230, 210, 175)),
                    ])
                return

    def _window_to_virtual_coords(self, wx, wy):
        """Map window viewport pixel coordinates back to virtual screen coordinates (1280 x 720)."""
        scale_x = SCREEN_WIDTH / max(1, self.window.width)
        scale_y = SCREEN_HEIGHT / max(1, self.window.height)
        vx=wx*scale_x
        ratio=(self.window.width/self.window.height)/(SCREEN_WIDTH/SCREEN_HEIGHT)
        return (vx-SCREEN_WIDTH/2)*ratio+SCREEN_WIDTH/2, wy*scale_y


if __name__ == "__main__":
    window = arcade.Window(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Scene 8: S08 Three Cards at Midnight",
        resizable=False,
        fullscreen=START_FULLSCREEN
    )
    if START_FULLSCREEN:
        window.set_fullscreen(True)
    view = Scene8View()
    window.show_view(view)
    arcade.run()
