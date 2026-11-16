"""Scene 1: S01 Something Is Still Missing
Faithfully following the National Champion Script (Assignment Plot S01):
1. Kitchen has cleared after closing. The chef stands alone before an almost flawless dish.
2. He tastes it (Eating.png), sets down his spoon, pulls the plate closer, adjusts the sauce.
3. Colleague peeks from the pantry doorway: "The customers already said it was delicious."
4. Chef: "I know." (Modern Chief.png)
5. He tastes it again: "But something's still missing..." (Chief Thinking.png behind the table & in dialogue!)
6. Colleague looks at the clock: "You said that yesterday." (Apprentice full body photo on the right!)
7. Chef does not answer (Chief Thinking.png).
8. Camera holds on his culinary notebook crowded with crossed-out ratios, ending with: "The Last Ingredient?"
"""
import math
import sys
from pathlib import Path

# Add project root to path for standalone execution
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import arcade
from arcade.types import Color
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD,
    SCENE_1_DIR, START_FULLSCREEN
)
from core.particles import Raindrop, GourmetSteamParticle
from core.dialogue import DialogueBox
from core.audio import AudioManager
from core.base_view import BaseGameView

# Scene 1 Story Phases
PHASE_S01_EXAMINE = 0   # Kitchen cleared, chef alone before the dish
PHASE_S01_EATING = 1    # Tasting, adjusting sauce
PHASE_S01_DIALOGUE = 2  # Conversation with colleague at the door
PHASE_S01_NOTEBOOK = 3  # Close-up camera focus on the recipe notebook
PHASE_S01_STEAK_CUT = 4 # First-person interactive steak slicing close-up


class SteakSizzleSpark:
    """Golden butter/jus sizzle sparks erupting from the carving knife edge."""
    def __init__(self, x: float, y: float):
        import random
        self.x = x + random.uniform(-6, 6)
        self.y = y + random.uniform(-6, 6)
        angle = random.uniform(0.0, 2 * math.pi)
        spd = random.uniform(35, 120)
        self.vx = math.cos(angle) * spd
        self.vy = math.sin(angle) * spd + 25.0
        self.r = random.uniform(1.8, 3.6)
        self.life = random.uniform(0.2, 0.45)
        self.max_life = self.life
        self.color = (
            random.randint(245, 255),
            random.randint(185, 235),
            random.randint(70, 130),
        )

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.r = max(0.6, self.r - dt * 2.2)

    def draw(self):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            arcade.draw_circle_filled(
                self.x, self.y, self.r,
                Color(self.color[0], self.color[1], self.color[2], alpha)
            )


class SauceRipple:
    """Expanding circular ripples in the gourmet jus when the slice separates and lands."""
    def __init__(self, x: float, y: float, delay: float = 0.0):
        import random
        self.x = x
        self.y = y
        self.delay = delay
        self.radius = 4.0
        self.growth_speed = random.uniform(40.0, 75.0)
        self.life = 0.85
        self.max_life = 0.85
        self.color = (210, 150, 75)

    def update(self, dt: float):
        if self.delay > 0:
            self.delay -= dt
            return
        self.radius += self.growth_speed * dt
        self.life -= dt

    def draw(self):
        if self.delay <= 0 and self.life > 0:
            alpha = int(180 * (self.life / self.max_life))
            arcade.draw_ellipse_outline(
                self.x, self.y, self.radius * 2.2, self.radius * 1.1,
                Color(self.color[0], self.color[1], self.color[2], alpha),
                border_width=2.0
            )


class ModernKitchenView(BaseGameView):

    def __init__(self):
        super().__init__()
        self.audio = AudioManager()
        self.t = 0.0
        self.phase = PHASE_S01_EXAMINE

        # ---- Load Scene 1 High-Res Textures
        self.bg_kitchen = arcade.load_texture(str(SCENE_1_DIR / "scene_01_restaurant_kitchen_anime.png"))
        self.table_foreground = arcade.load_texture(str(SCENE_1_DIR / "Table_Foreground.png"))
        self.door_frame_overlay = arcade.load_texture(str(SCENE_1_DIR / "Door_Outer_Frame_Overlay.png"))

        # Protagonist poses (all 1024x1536, identical frame alignment)
        self.chef_normal = arcade.load_texture(str(SCENE_1_DIR / "Modern Chief.png"))
        self.chef_eating = arcade.load_texture(str(SCENE_1_DIR / "Eating.png"))
        self.chef_thinking = arcade.load_texture(str(SCENE_1_DIR / "Chief Thinking.png"))

        # Apprentice / Colleague textures
        self.apprentice_door_body_tex = arcade.load_texture(str(SCENE_1_DIR / "Apprentice_Door_Body.png"))
        self.apprentice_door_fingers_tex = arcade.load_texture(str(SCENE_1_DIR / "Apprentice_Door_Fingers.png"))
        self.apprentice_dialogue_tex = arcade.load_texture(str(SCENE_1_DIR / "Apprentice_Dialogue_Full.png"))
        self.apprentice_clock_tex = arcade.load_texture(str(SCENE_1_DIR / "apprentice_looking_at_clock.png"))
        self.apprentice_worry_tex = arcade.load_texture(str(SCENE_1_DIR / "Chief_Apprentice_Worry_Clean.png"))
        self.apprentice_moved_to_table = False
        self.apprentice_fingers_alpha = 0.0
        self.clock_cg_alpha = 0.0
        self.clock_sound_played = False

        # Gourmet Steak Plate & Steam (Uncut plate initially, eaten plate after protagonist tastes)
        self.steak_uncut_tex = arcade.load_texture(str(SCENE_1_DIR / "Steak_Cut_Frame_0.png"))
        self.steak_eaten_tex = arcade.load_texture(str(SCENE_1_DIR / "Steak_Cut_Eaten.png"))
        self.steak_tex = self.steak_uncut_tex
        self.steam_puff_tex = arcade.load_texture(str(SCENE_1_DIR / "soft_steam_puff.png"))

        # Interactive First-Person Steak Slicing Close-Up Textures (Frames 0..3 & Carving Knife)
        self.steak_cut_frames = [
            arcade.load_texture(str(SCENE_1_DIR / f"Steak_Cut_Frame_{i}.png"))
            for i in range(4)
        ]
        self.steak_knife_tex = arcade.load_texture(str(SCENE_1_DIR / "Steak_Cut_Knife.png"))

        # Steak Cut Interaction States
        self.steak_cut_completed = False
        self.steak_cut_progress = 0.0
        self.steak_cut_frame_idx = 0
        self.steak_cut_zoom = 0.0
        self.steak_cut_exit_anim = False
        self.steak_cut_dragging = False
        self.steak_cut_auto = False
        self.steak_cut_lift_timer = 0.0
        self.steak_cut_shake = 0.0
        self.steak_cut_sparks = []
        self.steak_cut_ripples = []
        self.steak_cut_chop_count = 0
        self.knife_hover_x = 1080.0
        self.knife_hover_y = 500.0

        # Cut trajectory line on 1280x720 canvas (30-degree angle with ground, shifted down)
        self.cut_x1 = 1000.0
        self.cut_y1 = 430.0
        self.cut_x2 = 740.0
        self.cut_y2 = 280.0

        # Culinary Recipe Notebook Assets & Nearscene CG
        self.recipes_book_tex = arcade.load_texture(str(SCENE_1_DIR / "Recipes Book.png"))
        self.notebook_nearscene_tex = arcade.load_texture(str(SCENE_1_DIR / "Recipes Book Nearscene.jpg"))
        self.notebook_cg_alpha = 0.0
        self.notebook_anim_timer = 0.0

        # Steak plate coordinate (centered on table surface)
        self.steak_x = 570.0
        self.steak_y = 310.0

        # Apprentice Full-Body Peek from Back Door (emerges from left behind door frame, final target x=980.0)
        self.apprentice_w = 94.0
        self.apprentice_h = 325.0
        self.apprentice_x = 880.0
        self.apprentice_target_x = 880.0
        self.apprentice_y = 385.0
        self.apprentice_speed = 220.0

        # Ambient rain effect for night window
        self.raindrops = [Raindrop(SCREEN_WIDTH, SCREEN_HEIGHT) for _ in range(70)]

        # Wispy gourmet steam rising from the seared steak
        self.steak_steam = [
            GourmetSteamParticle(570, 325, self.steam_puff_tex, spread=12.0, rise_speed=36.0, max_life=2.2)
            for _ in range(18)
        ]

        # Notebook screen button interaction
        self.hovered_nb_btn = None
        self.notebook_buttons = [
            ("next_scene", "▶  PROCEED TO S02 · UNVERIFIED SAMPLE", SCREEN_WIDTH / 2 - 190, 60, 340, 44),
            ("menu", "⌂  MAIN MENU", SCREEN_WIDTH / 2 + 190, 60, 320, 44),
        ]

        # Cinematic Dialogue Engine
        self.dialogue = DialogueBox()
        self._setup_scene_1_script()

    # ---------------------------------------------------------------- Script Choreography
    def _setup_scene_1_script(self):
        """Construct the exact Scene 1 narrative sequence."""
        script = [
            # 1. The kitchen after closing
            (
                "Kitchen",
                "Closing time. The chef stands alone before the prep counter.",
                (215, 195, 160)
            ),
            # 2. Tasting
            (
                "Chef",
                "He tastes the dish, adjusting the sauce.",
                (210, 175, 120),
                self.chef_eating,
                "left"
            ),
            # 3. Colleague
            (
                "Colleague",
                "\"The customers already said it was delicious.\"",
                (245, 175, 190),
                self.apprentice_dialogue_tex,
                "right"
            ),
            # 4. Chef
            (
                "Chef",
                "\"I know.\"",
                (210, 175, 120),
                self.chef_normal,
                "left"
            ),
            # 5. Missing
            (
                "Chef",
                "\"But something is still missing...\"",
                (225, 190, 110),
                self.chef_thinking,
                "left"
            ),
            # 6. Colleague
            (
                "Colleague",
                "\"You said that yesterday.\"",
                (245, 175, 190),
                None,
                "right"
            ),
            # 7. Contemplation
            (
                "Chef",
                "Lost in quiet thought...",
                (210, 175, 120),
                self.chef_thinking,
                "left"
            ),
        ]
        self.clock_cg_alpha = 0.0
        self.clock_sound_played = False
        self.apprentice_moved_to_table = False
        self.apprentice_x = 880.0
        self.apprentice_target_x = 880.0
        self.apprentice_fingers_alpha = 0.0
        self.notebook_cg_alpha = 0.0
        self.notebook_anim_timer = 0.0
        self.dialogue.start_dialogue(script, on_complete=self._show_notebook_closeup)

    def _show_notebook_closeup(self):
        """Camera holds on his culinary notebook: The Last Ingredient?"""
        self.phase = PHASE_S01_NOTEBOOK
        self.notebook_cg_alpha = 0.0
        self.notebook_anim_timer = 0.0
        self.audio.play("achievement", volume_scale=0.6)

    def _start_steak_cut_mode(self):
        """Transition into first-person close-up interactive steak slicing."""
        self.phase = PHASE_S01_STEAK_CUT
        self.steak_cut_progress = 0.0
        self.steak_cut_auto = False
        self.steak_cut_completed = False
        self.steak_cut_dragging = False
        self.steak_cut_zoom = 0.0
        self.steak_cut_exit_anim = False
        self.steak_cut_frame_idx = 0
        self.steak_cut_lift_timer = 0.0
        self.steak_cut_shake = 0.0
        self.steak_cut_sparks.clear()
        self.steak_cut_ripples.clear()
        self.steak_cut_chop_count = 0
        self.dialogue.active = False
        self.audio.play("sizzle", volume_scale=0.45)

    def _finish_steak_cut_mode(self):
        """Trigger exit zoom and return to tasting dialogue."""
        self.steak_cut_exit_anim = True

    def _handle_steak_drag(self, vx: float, vy: float):
        if self.steak_cut_completed:
            return
        dx = self.cut_x2 - self.cut_x1
        dy = self.cut_y2 - self.cut_y1
        line_len_sq = dx * dx + dy * dy
        t = ((vx - self.cut_x1) * dx + (vy - self.cut_y1) * dy) / line_len_sq
        t = max(0.0, min(1.0, t))
        if t > self.steak_cut_progress:
            self.steak_cut_progress = t
            bx = self.cut_x1 + t * dx
            by = self.cut_y1 + t * dy
            for _ in range(3):
                self.steak_cut_sparks.append(SteakSizzleSpark(bx, by))

    # ---------------------------------------------------------------- Update Loop
    def on_update(self, dt):
        if self.is_paused:
            return

        self.t += dt
        self.dialogue.update(dt)

        # Steak cut interactive mode updates
        if self.phase == PHASE_S01_STEAK_CUT or self.steak_cut_zoom > 0.001:
            if not self.steak_cut_exit_anim:
                self.steak_cut_zoom = min(1.0, self.steak_cut_zoom + dt * 3.5)
            else:
                self.steak_cut_zoom = max(0.0, self.steak_cut_zoom - dt * 4.0)
                if self.steak_cut_zoom <= 0.001:
                    self.phase = PHASE_S01_EXAMINE
                    self.steak_cut_exit_anim = False
                    self.steak_tex = self.steak_eaten_tex  # Counter plate updated to eaten plate (without small cut slice)
                    # Resume dialogue into Line 1 (tasting bite)
                    self.dialogue.current_idx = 1
                    self.dialogue.text_progress = 0
                    self.dialogue.type_timer = 0.0
                    self.dialogue.active = True

            # Auto-cutting mode if triggered by SPACE, Enter, or Click
            if self.steak_cut_auto and not self.steak_cut_completed:
                self.steak_cut_progress = min(1.0, self.steak_cut_progress + dt * 1.15)
                bx = self.cut_x1 + self.steak_cut_progress * (self.cut_x2 - self.cut_x1)
                by = self.cut_y1 + self.steak_cut_progress * (self.cut_y2 - self.cut_y1)
                for _ in range(2):
                    self.steak_cut_sparks.append(SteakSizzleSpark(bx, by))

            # Frame switching based on cutting progress
            p = self.steak_cut_progress
            if p < 0.25:
                self.steak_cut_frame_idx = 0
            elif p < 0.65:
                self.steak_cut_frame_idx = 1
                if self.steak_cut_chop_count < 1:
                    self.audio.play("chop", volume_scale=0.65)
                    self.steak_cut_chop_count = 1
            elif p < 0.95:
                self.steak_cut_frame_idx = 2
                if self.steak_cut_chop_count < 2:
                    self.audio.play("chop", volume_scale=0.7)
                    self.steak_cut_chop_count = 2
            else:
                self.steak_cut_frame_idx = 3
                if not self.steak_cut_completed:
                    self.steak_cut_completed = True
                    self.audio.play("chop", volume_scale=0.8)
                    self.audio.play("clue_match", volume_scale=0.65)
                    self.steak_cut_shake = 0.25
                    import random
                    for i in range(4):
                        self.steak_cut_ripples.append(
                            SauceRipple(885 + random.uniform(-15, 15), 235 + random.uniform(-10, 10), delay=i * 0.12)
                        )
                    for _ in range(16):
                        self.steak_cut_sparks.append(SteakSizzleSpark(895, 240))

            if self.steak_cut_completed:
                self.steak_cut_lift_timer += dt

            if self.steak_cut_shake > 0:
                self.steak_cut_shake = max(0.0, self.steak_cut_shake - dt * 2.0)

            for sp in self.steak_cut_sparks:
                sp.update(dt)
            self.steak_cut_sparks = [sp for sp in self.steak_cut_sparks if sp.life > 0]

            for rp in self.steak_cut_ripples:
                rp.update(dt)
            self.steak_cut_ripples = [rp for rp in self.steak_cut_ripples if rp.life > 0]

        # Trigger colleague peek animation when dialogue reaches her lines
        if self.dialogue.active:
            cur_line = self.dialogue.lines[self.dialogue.current_idx]
            speaker = cur_line[0]
            if "Colleague" in speaker or self.dialogue.current_idx >= 2:
                # Flush alignment with outer door frame edge (flush with door frame outer seam at x=944.0: center x=980.0)
                self.apprentice_target_x = 980.0
            else:
                self.apprentice_target_x = 880.0

        # Smooth apprentice position lerp
        if abs(self.apprentice_x - self.apprentice_target_x) > 0.5:
            direction = 1.0 if self.apprentice_target_x > self.apprentice_x else -1.0
            self.apprentice_x += direction * self.apprentice_speed * dt
            if direction > 0 and self.apprentice_x > self.apprentice_target_x:
                self.apprentice_x = self.apprentice_target_x
            elif direction < 0 and self.apprentice_x < self.apprentice_target_x:
                self.apprentice_x = self.apprentice_target_x

        # Fingers gripping animation: smoothly curl and grip door frame outer edge ONLY after body has emerged
        if self.apprentice_target_x == 980.0 and abs(self.apprentice_x - 980.0) <= 0.8:
            self.apprentice_fingers_alpha = min(1.0, self.apprentice_fingers_alpha + dt / 0.18)
        else:
            self.apprentice_fingers_alpha = 0.0

        # Clock cutscene event CG alpha transition
        is_clock_line = False
        if self.dialogue.active:
            cur_line = self.dialogue.lines[self.dialogue.current_idx]
            if "clock" in cur_line[1].lower():
                is_clock_line = True
                if not self.clock_sound_played:
                    self.audio.play("clock_chime", volume_scale=0.5)
                    self.clock_sound_played = True

        target_clock_alpha = 1.0 if is_clock_line else 0.0
        if abs(self.clock_cg_alpha - target_clock_alpha) > 0.005:
            self.clock_cg_alpha += (target_clock_alpha - self.clock_cg_alpha) * min(1.0, dt * 5.0)
        else:
            self.clock_cg_alpha = target_clock_alpha

        # Once the clock CG finishes (dialogue passes line 5), apprentice moves to table beside trash can
        if self.dialogue.active:
            if self.dialogue.current_idx > 5:
                self.apprentice_moved_to_table = True
        elif self.phase == PHASE_S01_NOTEBOOK:
            self.apprentice_moved_to_table = True

        # Update notebook nearscene CG animation
        if self.phase == PHASE_S01_NOTEBOOK:
            self.notebook_anim_timer += dt
            if self.notebook_cg_alpha < 1.0:
                self.notebook_cg_alpha = min(1.0, self.notebook_cg_alpha + dt * 2.5)

        # Update rain
        for r in self.raindrops:
            r.update(dt)

        # Update steak steam
        for s in self.steak_steam:
            s.update(dt)

    # ---------------------------------------------------------------- Draw Loop
    def on_draw(self):
        self.clear(color=(16, 14, 18))
        self.use_game_camera()

        # 1. High-Res Restaurant Kitchen Background
        arcade.draw_texture_rect(
            self.bg_kitchen,
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        )

        # 2. Window Rain FX (Upper Left)
        win_x = 340
        win_y = 610
        win_w = 380
        win_h = 220
        for r in self.raindrops:
            if win_x - win_w / 2 < r.x < win_x + win_w / 2 and win_y - win_h / 2 < r.y < win_y + win_h / 2:
                r.draw()

        corr = self.aspect_ratio_correction

        # 3. Colleague Peeking from Pantry Door Frame (Back Door - only before clock CG)
        if not self.apprentice_moved_to_table and self.dialogue.active and self.dialogue.current_idx >= 2:
            # 3.1 Body emerges from left behind door frame
            arcade.draw_texture_rect(
                self.apprentice_door_body_tex,
                arcade.XYWH(self.apprentice_x, self.apprentice_y, self.apprentice_w * corr, self.apprentice_h)
            )
            # 3.2 Door frame overlay occludes body while emerging (x < 980.0)
            if self.apprentice_x < 979.5:
                arcade.draw_texture_rect(
                    self.door_frame_overlay,
                    arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
                )
            # 3.3 Fingers grip onto the door frame outer edge after leaning out
            if self.apprentice_fingers_alpha > 0.01:
                arcade.draw_texture_rect(
                    self.apprentice_door_fingers_tex,
                    arcade.XYWH(self.apprentice_x, self.apprentice_y, self.apprentice_w * corr, self.apprentice_h),
                    color=Color(255, 255, 255, int(255 * self.apprentice_fingers_alpha))
                )

        # 5. Protagonist Chef Behind Prep Island Counter
        # Dynamic switching based on dialogue state:
        # Switch to thinking chef texture during contemplation
        current_chef_tex = self.chef_normal
        if self.dialogue.active:
            cur_line = self.dialogue.lines[self.dialogue.current_idx]
            port = cur_line[3] if len(cur_line) > 3 else None
            if port == self.chef_thinking or "missing" in cur_line[1].lower() or "contemplation" in cur_line[1].lower():
                current_chef_tex = self.chef_thinking
            elif port == self.chef_eating or "tastes a bite" in cur_line[1].lower():
                current_chef_tex = self.chef_eating
            elif port == self.chef_normal:
                current_chef_tex = self.chef_normal
        elif self.phase == PHASE_S01_NOTEBOOK:
            current_chef_tex = self.chef_thinking

        arcade.draw_texture_rect(
            current_chef_tex,
            arcade.XYWH(570, 400, 256 * corr, 385)
        )

        # 6. Colleague standing at original position beside table in aisle, behind table/trash layer (After clock CG: x=1130, y=330)
        if self.apprentice_moved_to_table:
            arcade.draw_texture_rect(
                self.apprentice_worry_tex,
                arcade.XYWH(1130, 330, 136 * corr, 445)
            )

        # 7. Stainless Island Prep Table Foreground (covers chef and apprentice lower body naturally)
        arcade.draw_texture_rect(
            self.table_foreground,
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        )

        # 7. Pure Gourmet Steak Plate Firmly on Table Plane (Refined 100x56)
        arcade.draw_texture_rect(
            self.steak_tex,
            arcade.XYWH(self.steak_x, self.steak_y, 100 * corr, 56)
        )

        # 7.2 Open Recipe Notebook to the right of steak on table (shifted slightly up: y=318)
        arcade.draw_texture_rect(
            self.recipes_book_tex,
            arcade.XYWH(695, 318, 114 * corr, 62)
        )

        # 8. Wispy Steam rising from the sizzling steak
        for s in self.steak_steam:
            s.draw()

        # 8.5 Fullscreen Event CG: Colleague looking at clock
        if self.clock_cg_alpha > 0.005:
            alpha = int(255 * max(0.0, min(1.0, self.clock_cg_alpha)))
            arcade.draw_texture_rect(
                self.apprentice_clock_tex,
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                color=Color(255, 255, 255, alpha)
            )

        # 9. Cinematic Dialogue Box (with right-side colleague avatar and left-side chef avatar)
        self.dialogue.draw(corr)

        # 10. Close-up Camera on Recipe Notebook: "The Last Ingredient?"
        if self.phase == PHASE_S01_NOTEBOOK:
            self._draw_notebook_closeup(corr)

        # 10.5 First-Person Interactive Steak Carving Close-Up View
        if self.phase == PHASE_S01_STEAK_CUT or self.steak_cut_zoom > 0.005:
            self._draw_steak_cut_view(corr)

        # 11. Global Pause & Exit Overlay (Pure English, sleek glassmorphism)
        self.draw_pause_overlay()

    # ---------------------------------------------------------------- Steak Carving Closeup
    def _draw_steak_cut_view(self, corr: float):
        """Draw the cinematic first-person close-up interactive steak slicing mode."""
        import random
        zoom_val = min(1.0, max(0.0, self.steak_cut_zoom))
        alpha = int(255 * zoom_val)
        if alpha <= 0:
            return

        # Camera haptic vibration
        shake_x = 0.0
        shake_y = 0.0
        if self.steak_cut_shake > 0:
            intensity = (self.steak_cut_shake / 0.25) * 4.5
            shake_x = random.uniform(-intensity, intensity)
            shake_y = random.uniform(-intensity, intensity)

        # 1. Dark vignette background dimming
        arcade.draw_rect_filled(
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
            Color(10, 8, 12, int(225 * zoom_val))
        )

        # 2. Main High-Res Steak Plate Frame (Smooth zoom-in scale: 0.88 -> 1.0)
        plate_scale = 0.88 + 0.12 * zoom_val
        arcade.draw_texture_rect(
            self.steak_cut_frames[self.steak_cut_frame_idx],
            arcade.XYWH(
                SCREEN_WIDTH / 2 + shake_x,
                SCREEN_HEIGHT / 2 + shake_y,
                SCREEN_WIDTH * plate_scale,
                SCREEN_HEIGHT * plate_scale
            ),
            color=Color(255, 255, 255, alpha)
        )

        # 3. Expanding Sauce Ripples under the severed slice
        for rp in self.steak_cut_ripples:
            rp.draw()

        # 4. Glistening Butter/Jus Sparks & Culinary Sizzle Particles
        for sp in self.steak_cut_sparks:
            sp.draw()

        # 5. Cutting Line Trajectory & Guide (if not completed)
        p = self.steak_cut_progress
        bx = self.cut_x1 + p * (self.cut_x2 - self.cut_x1)
        by = self.cut_y1 + p * (self.cut_y2 - self.cut_y1)

        if not self.steak_cut_completed:
            # Pulsing golden dashed guide line
            pulse = 0.5 + 0.5 * math.sin(self.t * 6.0)
            guide_alpha = int((140 + 100 * pulse) * zoom_val)
            guide_col = Color(255, 215, 110, guide_alpha)

            total_dx = self.cut_x2 - self.cut_x1
            total_dy = self.cut_y2 - self.cut_y1
            total_dist = math.sqrt(total_dx * total_dx + total_dy * total_dy)
            dash_len = 10.0
            gap_len = 6.0
            cur_dist = 0.0
            while cur_dist < total_dist:
                seg_start = cur_dist / total_dist
                seg_end = min(1.0, (cur_dist + dash_len) / total_dist)
                sx = self.cut_x1 + seg_start * total_dx
                sy = self.cut_y1 + seg_start * total_dy
                ex = self.cut_x1 + seg_end * total_dx
                ey = self.cut_y1 + seg_end * total_dy
                arcade.draw_line(sx, sy, ex, ey, guide_col, line_width=2.5)
                cur_dist += dash_len + gap_len

            # Gliding chevron prompt indicator
            glide_t = (self.t * 1.4) % 1.0
            gx = self.cut_x1 + glide_t * total_dx
            gy = self.cut_y1 + glide_t * total_dy
            arcade.draw_circle_filled(gx, gy, 4.5, Color(255, 245, 180, int(220 * zoom_val)))
            arcade.draw_circle_outline(gx, gy, 8.0, Color(255, 210, 90, int(180 * zoom_val)), border_width=1.5)

        # 6. Blade Slash Streak (from cut_x1 to current blade point)
        if p > 0.03:
            slash_alpha = int(220 * zoom_val)
            arcade.draw_line(
                self.cut_x1, self.cut_y1, bx, by,
                Color(255, 220, 130, int(slash_alpha * 0.7)), line_width=5.0
            )
            arcade.draw_line(
                self.cut_x1, self.cut_y1, bx, by,
                Color(255, 255, 255, slash_alpha), line_width=2.2
            )
            # Blade contact flare
            arcade.draw_circle_filled(bx, by, 6.0, Color(255, 255, 255, slash_alpha))
            arcade.draw_circle_outline(bx, by, 12.0, Color(255, 215, 100, int(slash_alpha * 0.8)), border_width=1.8)

        # 7. First-Person Carving Knife (Rotated right by another 10° to -4.0°)
        # Position knife blade cutting edge right at contact point (bx, by)
        knife_angle = -4.0  # Rotated right by another 10° from 6.0°
        if self.steak_cut_completed:
            lift = min(1.0, self.steak_cut_lift_timer / 0.5)
            # Smoothly lift up and away to reveal the freshly carved slice
            knife_x = bx - 75.0 - lift * 70.0
            knife_y = by + 5.0 + lift * 55.0
            knife_angle = -4.0 + lift * 8.0
            knife_alpha = int(255 * (1.0 - lift * 0.25) * zoom_val)
        else:
            if self.steak_cut_dragging or self.steak_cut_auto or p > 0.01:
                knife_x = bx - 75.0
                knife_y = by + 5.0
            else:
                target_kx = self.cut_x1 - 75.0
                target_ky = self.cut_y1 + 5.0
                knife_x = target_kx
                knife_y = target_ky + 12.0 * math.sin(self.t * 3.0)
            knife_alpha = alpha

        arcade.draw_texture_rect(
            self.steak_knife_tex,
            arcade.XYWH(knife_x + shake_x, knife_y + shake_y, 470, 220),
            angle=knife_angle,
            color=Color(255, 255, 255, knife_alpha)
        )

        # 8. Sleek Glassmorphic Prompt & Instruction Banners
        # Top Header Banner
        top_y = 660
        arcade.draw_rect_filled(
            arcade.XYWH(SCREEN_WIDTH / 2, top_y, 520, 52),
            Color(18, 16, 22, int(215 * zoom_val))
        )
        arcade.draw_rect_outline(
            arcade.XYWH(SCREEN_WIDTH / 2, top_y, 520, 52),
            Color(215, 175, 110, int(190 * zoom_val)),
            border_width=1.5
        )
        arcade.draw_text(
            "✦ FIRST-PERSON CARVING ✦",
            SCREEN_WIDTH / 2, top_y - 7,
            Color(255, 240, 210, alpha),
            14, anchor_x="center", bold=True
        )

        # Bottom Interaction / Completion Banner
        bot_y = 68
        if not self.steak_cut_completed:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, bot_y, 640, 56),
                Color(16, 18, 26, int(220 * zoom_val))
            )
            arcade.draw_rect_outline(
                arcade.XYWH(SCREEN_WIDTH / 2, bot_y, 640, 56),
                Color(120, 185, 245, int(180 * zoom_val)),
                border_width=1.5
            )
            arcade.draw_text(
                "✦ [ DRAG KNIFE ALONG LINE ] or [ PRESS SPACE TO SLICE ] ✦",
                SCREEN_WIDTH / 2, bot_y - 6,
                Color(220, 235, 255, alpha),
                13, anchor_x="center", bold=True
            )
        else:
            pulse_gold = 0.5 + 0.5 * math.sin(self.t * 5.0)
            border_c = Color(255, int(190 + 45 * pulse_gold), 90, alpha)
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, bot_y, 680, 60),
                Color(28, 22, 16, int(235 * zoom_val))
            )
            arcade.draw_rect_outline(
                arcade.XYWH(SCREEN_WIDTH / 2, bot_y, 680, 60),
                border_c,
                border_width=2.0
            )
            arcade.draw_text(
                "✨ PERFECT SEAR & TENDER SLICE ✨",
                SCREEN_WIDTH / 2, bot_y + 6,
                Color(255, 225, 140, alpha),
                13, anchor_x="center", bold=True
            )
            arcade.draw_text(
                "[ CLICK ANYWHERE OR PRESS SPACE TO TASTE ]",
                SCREEN_WIDTH / 2, bot_y - 14,
                Color(255, 255, 255, int(230 * zoom_val)),
                12, anchor_x="center"
            )

    # ---------------------------------------------------------------- Notebook Closeup
    def _draw_notebook_closeup(self, corr: float):
        """Draw the cinematic focus view on the chef's culinary recipe notebook (The Last Ingredient?)."""
        alpha_val = min(1.0, max(0.0, self.notebook_cg_alpha))
        alpha = int(255 * alpha_val)
        if alpha <= 0:
            return

        # Gentle cinematic slow-zoom over time (1.0 -> 1.025)
        zoom = 1.0 + 0.025 * min(1.0, self.notebook_anim_timer / 3.5)

        # Full-screen Event CG: Recipe Book Nearscene
        arcade.draw_texture_rect(
            self.notebook_nearscene_tex,
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH * zoom, SCREEN_HEIGHT * zoom),
            color=Color(255, 255, 255, alpha)
        )

        # Subtle dark gradient at bottom for button readability
        arcade.draw_rect_filled(
            arcade.XYWH(SCREEN_WIDTH / 2, 60, SCREEN_WIDTH, 120),
            Color(10, 8, 14, int(150 * alpha_val))
        )

        # Bottom Action Buttons
        for btn_id, label, bx, by, bw, bh in self.notebook_buttons:
            is_hover = (self.hovered_nb_btn == btn_id)
            if btn_id == "next_scene":
                bg_col = Color(42, 105, 68, int(235 * alpha_val)) if is_hover else Color(24, 46, 34, int(205 * alpha_val))
                border_col = Color(110, 245, 160, alpha) if is_hover else Color(75, 125, 95, int(180 * alpha_val))
            else:
                bg_col = Color(55, 65, 88, int(235 * alpha_val)) if is_hover else Color(30, 34, 46, int(205 * alpha_val))
                border_col = Color(140, 195, 255, alpha) if is_hover else Color(85, 105, 135, int(180 * alpha_val))

            arcade.draw_rect_filled(arcade.XYWH(bx, by, bw, bh), bg_col)
            arcade.draw_rect_outline(arcade.XYWH(bx, by, bw, bh), border_col, 2.0 if is_hover else 1.2)
            arcade.draw_text(label, bx, by - 6, Color(255, 255, 255, alpha), 13, anchor_x="center", bold=True)

    # ---------------------------------------------------------------- Controls & Interaction
    def on_key_press(self, key, modifiers):
        if self.handle_pause_key(key):
            return

        if key == arcade.key.F11:
            self.toggle_fullscreen()
            return

        if self.phase == PHASE_S01_STEAK_CUT:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                if self.steak_cut_completed:
                    self._finish_steak_cut_mode()
                else:
                    self.steak_cut_auto = True
            return

        if self.phase == PHASE_S01_NOTEBOOK:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                self._proceed_to_next_scene()
            return

        if self.dialogue.active:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                # If on line 0 (chef stands before dish), advance into steak cutting minigame
                if self.dialogue.current_idx == 0 and not self.steak_cut_completed:
                    if self.dialogue.text_progress < len(self.dialogue._wrapped_lines[0]):
                        self.dialogue.text_progress = len(self.dialogue._wrapped_lines[0])
                    else:
                        self._start_steak_cut_mode()
                    return
                self.dialogue.advance()
            return

    def on_mouse_motion(self, x, y, dx, dy):
        if self.handle_pause_mouse_motion(x, y):
            return

        vx, vy = self.to_virtual_coords(x, y)

        if self.phase == PHASE_S01_STEAK_CUT:
            self.knife_hover_x = vx
            self.knife_hover_y = vy
            return

        if self.phase == PHASE_S01_NOTEBOOK:
            self.hovered_nb_btn = None
            for btn_id, _, bx, by, bw, bh in self.notebook_buttons:
                if abs(vx - bx) <= bw / 2 and abs(vy - by) <= bh / 2:
                    self.hovered_nb_btn = btn_id
                    break

    def on_mouse_press(self, x, y, button, modifiers):
        if self.handle_pause_mouse_press(x, y, button):
            return

        vx, vy = self.to_virtual_coords(x, y)

        if self.phase == PHASE_S01_STEAK_CUT:
            if self.steak_cut_completed:
                self._finish_steak_cut_mode()
                return
            self.steak_cut_dragging = True
            self._handle_steak_drag(vx, vy)
            return

        if self.phase == PHASE_S01_NOTEBOOK:
            if self.hovered_nb_btn == "next_scene":
                self.audio.play("click")
                self._proceed_to_next_scene()
            elif self.hovered_nb_btn == "menu":
                self.audio.play("click")
                from scenes.menu_view import MenuView
                self.window.show_view(MenuView())
            else:
                self._proceed_to_next_scene()
            return

        if self.dialogue.active:
            # If clicked on the steak plate on the counter during line 0:
            if not self.steak_cut_completed and abs(vx - self.steak_x) <= 65 and abs(vy - self.steak_y) <= 45:
                self._start_steak_cut_mode()
                return
            # If advancing line 0 dialogue:
            if self.dialogue.current_idx == 0 and not self.steak_cut_completed:
                if self.dialogue.text_progress < len(self.dialogue._wrapped_lines[0]):
                    self.dialogue.text_progress = len(self.dialogue._wrapped_lines[0])
                else:
                    self._start_steak_cut_mode()
                return
            self.dialogue.advance()
            return

    def on_mouse_drag(self, x, y, dx, dy, _buttons, _modifiers):
        if self.phase == PHASE_S01_STEAK_CUT and not self.steak_cut_completed:
            vx, vy = self.to_virtual_coords(x, y)
            self._handle_steak_drag(vx, vy)

    def on_mouse_release(self, x, y, button, modifiers):
        if self.phase == PHASE_S01_STEAK_CUT:
            self.steak_cut_dragging = False

    def _proceed_to_next_scene(self):
        """Advance to S02 The Unverified Sample."""
        from scenes.scene_2_view import Scene2View
        self.window.show_view(Scene2View())


if __name__ == "__main__":
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, "The Last Ingredient - Scene 1", resizable=False, fullscreen=START_FULLSCREEN)
    if START_FULLSCREEN:
        window.set_fullscreen(True)
    view = ModernKitchenView()
    window.show_view(view)
    arcade.run()
