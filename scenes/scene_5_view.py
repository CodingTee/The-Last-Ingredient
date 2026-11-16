"""Scene 5 / S05: Outside His Old Home
Cinematic 2D Side-scroller following the National Champion Script (Assignment Plot S05):
1. A desolate stormy rain night; long side-scrolling street with multi-layer parallax.
2. Protagonist walks right through the rain, streetlamps, puddles, and city reflections.
3. Interactive traffic hazards: animated car with honk & screech warnings, water spray & splash physics.
4. Arrives at his former home: stranger's name on mailbox, front door locked, window latched.
5. Explores the side alley, discovers the old kitchen back door with the loose latch.
6. Jiggles the latch to unlock the door, whispers "I'll eat something... then I'll go", and slips inside.
7. Seamlessly transitions into Scene 6: Old Home Kitchen & Midnight Tarot Cards.
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
from arcade.types.rect import LRBT
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD, START_FULLSCREEN,
    ASSETS_DIR, SCENE_5_DIR
)
from core.player import Player
from core.dialogue import DialogueBox
from core.audio import AudioManager
from core.base_view import BaseGameView

# World Constants
WORLD_WIDTH = 4600.0
PLAYER_Y_MIN = 80.0    # Allows character to walk freely down onto the asphalt road
PLAYER_Y_MAX = 228.0   # Sidewalk near rear hedges

# Interactive Landmark Stages
STAGE_WALKING = 0
STAGE_AT_HOUSE = 1
STAGE_LATCH_UNLOCKED = 2
STAGE_ENTERING = 3


class Scene5View(BaseGameView):
    def __init__(self, from_scene_1=False):
        super().__init__()
        self.from_scene_1 = from_scene_1
        self.audio = AudioManager()
        self.t = 0.0

        # Cameras: World Camera (scrolls horizontally) + UI Camera (fixed HUD)
        self.world_cam = None
        self.ui_cam = None
        self.cam_x = SCREEN_WIDTH / 2
        self.cam_target_x = SCREEN_WIDTH / 2

        # Narrative Stage
        self.stage = STAGE_WALKING

        # Load Textures
        street_dir = SCENE_5_DIR
        self.tex_sky = arcade.load_texture(str(street_dir / "sky_skyline.png"))
        self.tex_mid = arcade.load_texture(str(street_dir / "street_midground.png"))
        self.tex_pave = arcade.load_texture(str(street_dir / "street_sidewalk_pave.png"))
        
        # Enhanced anime assets & Animated Rain Mansion (5 Frames)
        self.tex_house_frames = []
        self.tex_gate_frames = []
        for i in range(5):
            f_path = street_dir / f"anime_mansion_rain_{i}.png"
            if f_path.exists():
                self.tex_house_frames.append(arcade.load_texture(str(f_path)))
            g_path = street_dir / f"mansion_gate_fg_{i}.png"
            if g_path.exists():
                self.tex_gate_frames.append(arcade.load_texture(str(g_path)))
        house_asset = street_dir / "anime_house_exterior.png"
        self.tex_house = self.tex_house_frames[0] if self.tex_house_frames else arcade.load_texture(str(house_asset if house_asset.exists() else street_dir / "old_house_exterior.png"))
        if not self.tex_house_frames:
            self.tex_house_frames = [self.tex_house]
        self.house_anim_timer = 0.0
        self.house_frame_idx = 0
        self.house_frame_duration = 0.09  # ~11 FPS for crisp, fluid rain animation
        
        shelter_asset = street_dir / "anime_bus_shelter.png"
        self.tex_shelter = arcade.load_texture(str(shelter_asset if shelter_asset.exists() else street_dir / "bus_stop_shelter.png"))
        
        vending_asset = street_dir / "anime_vending_machine.png"
        if not vending_asset.exists():
            vending_asset = street_dir / "vending_machine.png"
        self.tex_vending = arcade.load_texture(str(vending_asset)) if vending_asset.exists() else None
        
        self.tex_lamp = arcade.load_texture(str(street_dir / "streetlight.png"))

        # Dialogue portraits
        scene1_dir = ASSETS_DIR / "Scene 1"
        self.portrait_chef = arcade.load_texture(str(scene1_dir / "Modern Chief.png"))
        self.portrait_thinking = arcade.load_texture(str(scene1_dir / "Chief Thinking.png"))

        # Streetlamps world coordinates (Lamp 1 at x=75 to the left of the bus shelter at x=330)
        self.lamp_positions = [75, 920, 1650, 2380, 3120, 3820, 4360]

        # Distinct, organic puddles along the street (None overlapping with the house at x=2800~4150)
        self.puddles = [
            # Puddle 1: Elongated curb runoff to the right of bus stop
            {"type": "curb_run", "x": 630, "y": 146, "w": 125, "h": 20, "tint": "cool"},
            # Puddle 2: Dual-lobed organic puddle moved under streetlamp #3 (x=1650) reflecting warm golden light!
            {"type": "dual_lobe", "x": 1710, "y": 172, "w": 110, "h": 26, "tint": "warm_lamp"},
            # Puddle 3: Broad shallow wet glaze across pavement slabs
            {"type": "shallow_spread", "x": 1380, "y": 168, "w": 140, "h": 26, "tint": "cool"},
            # Puddle 4: Three-splash irregular cluster along the sidewalk
            {"type": "cluster", "x": 2240, "y": 178, "w": 96, "h": 22, "tint": "cool"},
            # Puddle 5: Curb runoff at the far end of the street past the house
            {"type": "curb_run", "x": 4420, "y": 148, "w": 115, "h": 18, "tint": "cool"},
        ]
        self.puddle_ripples = []  # list of (x, y, radius, max_radius, alpha)

        # Rain particles in screen viewport space
        self.raindrops = []
        for _ in range(160):
            rx = random.uniform(-60, SCREEN_WIDTH + 60)
            ry = random.uniform(0, SCREEN_HEIGHT + 40)
            rspeed = random.uniform(700, 1000)
            rlen = random.uniform(16, 28)
            self.raindrops.append([rx, ry, rspeed, rlen])
        self.rain_splashes = []  # list of (x, y, radius, alpha)

        # Distant Thunder & Lightning system
        self.lightning_timer = random.uniform(8.0, 18.0)
        self.lightning_flash = 0.0
        self.thunder_delay = 0.0

        # Player character
        self.player = Player(x=220, y=208, char_id="modern")
        self.player.speed = 240.0
        self.dust_particles = []

        # Input keys
        self.key_left = False
        self.key_right = False
        self.key_up = False
        self.key_down = False
        self.key_shift = False

        # Investigation states
        self.inspected_mailbox = False
        self.inspected_front_door = False
        self.inspected_window = False
        self.inspected_side_gate = False
        self.latch_unlocked = False

        # Rapid-tap gate vaulting / scaling states
        self.is_climbing = False
        self.vault_power = 0.0          # 0.0 to 1.0 (accumulated by rapid tapping)
        self.vault_threshold = 1.0      # Must reach 1.0 to clear gate
        self.vault_last_tap_time = 0.0  # Time of last tap/click
        self.vault_phase = 0            # 0: tapping, 1: jumping based on power, 2: cleared gate & receding into backyard
        self.vault_stage = 1            # Stage 1: Build momentum to 100%, Stage 2: Final 5-tap sprint (TAP! TAP! TAP!)
        self.vault_sprint_taps = 0      # 0 to 5 consecutive taps in Stage 2
        self.vault_is_99_fail = False   # True if sprint was interrupted, triggering 99% near-miss jump
        self.vault_timer = 0.0
        self.vault_start_x = 0.0
        self.vault_start_y = 0.0
        self.vault_jump_t = 0.0
        self.vault_jump_height = 0.0
        self.vault_active = False       # True when player is at the gate actively tapping
        self.player_vault_disappeared = False  # True when player has vanished into backyard darkness

        # Transition to kitchen fade
        self.fade_alpha = 0.0
        self.is_transitioning = False

        # Cinematic Dialogue Box
        self.dialogue = DialogueBox()
        self.opening_dialogue_done = False

        # Screen Shake State
        self.shake_duration = 0.0
        self.shake_intensity = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0

        # Car Traffic System (Mr. Bean's 4-frame animated sprite)
        car_dir = SCENE_5_DIR / "car"
        self.car_textures = [
            arcade.load_texture(str(car_dir / f"car_{i}.png")) for i in range(1, 5)
        ]
        self.car_frame = 0
        self.car_frame_timer = 0.0
        self.car_x = 1800.0
        self.car_y = 96.0    # Center of the asphalt road lane (adjusted lower)
        self.car_w = 270.0
        self.car_h = 128.0
        self.car_speed = 480.0
        self.car_honked = False
        self.car_respawn_timer = 0.0

        # Car Special Effects Particles
        self.car_smoke = []          # [x, y, vx, vy, radius, max_radius, alpha]
        self.car_water_sprays = []   # [x, y, vx, vy, radius, alpha]

        # Player Death & Respawn System
        self.is_dead = False
        self.death_alpha = 0.0
        self.blood_splatters = []
        self.respawn_btn_hovered = False

        # Start opening dialogue
        self._trigger_intro_dialogue()

    def setup_camera(self):
        super().setup_camera()
        if not self.window:
            return
        if self.world_cam is None:
            self.world_cam = arcade.camera.Camera2D(window=self.window)
        if self.ui_cam is None:
            self.ui_cam = arcade.camera.Camera2D(window=self.window)
        self.update_camera()

    def update_camera(self):
        super().update_camera()
        if self.window and self.world_cam and self.ui_cam:
            # World Camera
            self.world_cam.viewport = LRBT(0, self.window.width, 0, self.window.height)
            self.world_cam.projection = LRBT(-SCREEN_WIDTH / 2, SCREEN_WIDTH / 2, -SCREEN_HEIGHT / 2, SCREEN_HEIGHT / 2)
            self.world_cam.position = (self.cam_x, SCREEN_HEIGHT / 2)

            # UI Camera (Fixed 1:1 screen viewport)
            self.ui_cam.viewport = LRBT(0, self.window.width, 0, self.window.height)
            self.ui_cam.projection = LRBT(-SCREEN_WIDTH / 2, SCREEN_WIDTH / 2, -SCREEN_HEIGHT / 2, SCREEN_HEIGHT / 2)
            self.ui_cam.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    def on_show_view(self):
        super().on_show_view()
        self.audio.play("rain_loop", volume_scale=0.55, loop=True)

    def on_hide_view(self):
        self.audio.stop_sound("rain_loop")

    def _trigger_intro_dialogue(self):
        if self.opening_dialogue_done:
            return
        self.opening_dialogue_done = True
        script = [
            ("Chef", "\"Another rejection... 'We are unable to offer you employment.'\"", (210, 175, 120), self.portrait_thinking),
            ("Chef", "\"My feet carried me back here... my old home.\"", (210, 175, 120), self.portrait_chef),
        ]
        self.dialogue.start_dialogue(script)

    def _trigger_car_hit_death(self):
        """Trigger violent car hit death sequence with camera jolt, visceral SFX, and blood splatter."""
        self.is_dead = True
        self.shake_duration = 0.85
        self.shake_intensity = 38.0
        # Impact triggers thunder crack and dying heartbeat thump
        self.audio.play("thunder", volume_scale=1.0)
        self.audio.play("choking_heartbeat", volume_scale=1.0)
        self.lightning_flash = 0.2
        self.thunder_delay = 0.0

        # Stop player movement
        self.player.is_moving = False
        self.key_left = self.key_right = self.key_up = self.key_down = False
        self.key_shift = False
        self.player_vault_disappeared = False

        # Generate randomized organic blood splatters
        self.blood_splatters = []
        for _ in range(24):
            sx = random.uniform(60, SCREEN_WIDTH - 60)
            sy = random.uniform(60, SCREEN_HEIGHT - 60)
            srad = random.uniform(14, 46)
            drops = [
                (random.uniform(-srad * 1.5, srad * 1.5), random.uniform(-srad * 1.5, srad * 1.5), random.uniform(2, 6))
                for _ in range(random.randint(4, 9))
            ]
            self.blood_splatters.append({
                "x": sx, "y": sy, "r": srad, "drops": drops,
                "color": (random.randint(120, 160), random.randint(10, 24), random.randint(15, 30))
            })

    def _respawn_player(self):
        """Respawn player safely at the starting sidewalk location without repeating intro dialogue."""
        self.player.x = 220
        self.player.y = 208
        self.player.facing = "down"
        self.player.is_moving = False
        self.key_left = self.key_right = self.key_up = self.key_down = False
        self.key_shift = False
        self.player_vault_disappeared = False

        self.is_dead = False
        self.death_alpha = 0.0
        self.blood_splatters = []

        # Stop any active dialogue so intro does NOT replay
        self.opening_dialogue_done = True
        self.dialogue.active = False

        # Reset car ahead
        self.car_x = self.player.x + 1100.0
        self.car_honked = False
        self.car_respawn_timer = 0.0

        self.audio.play("click", volume_scale=0.7)

    # ---------------------------------------------------------------- Update
    def on_update(self, dt):
        if self.is_paused:
            return

        self.t += dt
        self.dialogue.update(dt)

        # Screen Shake Update
        if self.shake_duration > 0:
            self.shake_duration -= dt
            decay = max(0.0, self.shake_duration / 0.85)
            self.shake_offset_x = random.uniform(-self.shake_intensity, self.shake_intensity) * decay
            self.shake_offset_y = random.uniform(-self.shake_intensity, self.shake_intensity) * decay
        else:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0

        # Death screen alpha fade
        if self.is_dead:
            self.death_alpha = min(240.0, self.death_alpha + dt * 320.0)

        # 0. Rapid Tap Vaulting & Scaling Update
        if self.vault_active:
            now = self.t

            # Phase 0: Player is standing at the gate, actively tapping/mashing
            if self.vault_phase == 0:
                self.player.place(self.vault_start_x, self.vault_start_y)
                # Keep strictly locked to clean back view
                self.player.facing = 'up'
                self.player.is_moving = False
                self.player._update_texture()

                # Stage 1: Build momentum up to 100%
                if self.vault_stage == 1:
                    # Continuous automatic decay in Stage 1
                    self.vault_power = max(0.0, self.vault_power - dt * 0.28)

                    # Reached 100% threshold -> Unlock Stage 2 Final Sprint!
                    if self.vault_power >= self.vault_threshold:
                        self.vault_power = 1.0
                        self.vault_stage = 2
                        self.vault_sprint_taps = 0
                        self.vault_last_tap_time = now
                        self.audio.play("click", volume_scale=0.9)
                        self.shake_duration = 0.15
                        self.shake_intensity = 3.0
                    # If stopped tapping for > 0.7s and has accumulated power (> 0.05), partial jump
                    elif (now - self.vault_last_tap_time) > 0.70 and self.vault_power > 0.05:
                        self.vault_phase = 1
                        self.vault_is_99_fail = False
                        self.vault_jump_t = 0.0
                        self.vault_jump_height = self.vault_power * 175.0
                        self.audio.play('Normal Walk', volume_scale=0.7)

                # Stage 2: Final Sprint - Must tap 5 consecutive times without interruption
                elif self.vault_stage == 2:
                    # In Stage 2, threshold is at 100%
                    self.vault_power = 1.0
                    # Interrupted check: pause > 0.7s without completing 5 taps -> 99% near-miss jump!
                    if (now - self.vault_last_tap_time) > 0.70:
                        self.vault_phase = 1
                        self.vault_is_99_fail = True
                        self.vault_jump_t = 0.0
                        # 99% jump height: jumps almost over the gate (top rail), but misses by a hair!
                        self.vault_jump_height = 0.99 * 195.0
                        self.vault_power = 0.99
                        self.audio.play('Normal Walk', volume_scale=0.85)

            # Phase 1: Insufficient power jump or interrupted 99% near-miss jump
            elif self.vault_phase == 1:
                self.vault_jump_t += dt
                jump_duration = 0.68 if self.vault_is_99_fail else 0.65
                p = self.vault_jump_t / jump_duration

                # Accelerated rapid decay during jump
                # Rapidly drains remaining momentum to 0 while airborne
                self.vault_power = max(0.0, self.vault_power - dt * 2.2)

                if p <= 1.0:
                    # Natural parabola: 4 * p * (1 - p) peaks at 1.0 when p = 0.5
                    current_lift = 4.0 * p * (1.0 - p) * self.vault_jump_height
                    # Use place() so the SPRITE actually moves upward into the air!
                    self.player.place(self.vault_start_x, self.vault_start_y + current_lift)
                    self.player.facing = 'up'
                    self.player.is_moving = False
                    self.player._update_texture()
                else:
                    # Landed back on ground!
                    self.player.place(self.vault_start_x, self.vault_start_y)
                    self.vault_phase = 0
                    self.vault_stage = 1           # Reset back to Stage 1!
                    self.vault_sprint_taps = 0
                    self.vault_power = 0.0         # Threshold bar cleared to 0!
                    self.vault_is_99_fail = False
                    self.vault_last_tap_time = self.t
                    self.audio.play('Normal Walk', volume_scale=0.75)

            # Phase 2: FULL VAULT SUCCESS (Cleared gate! Soars over, lands behind, and recedes/shrinks into backyard)
            elif self.vault_phase == 2:
                self.vault_timer += dt
                # Sub-phase A: Soar up towards the top of the iron railing (0.0 to 0.45s)
                # Before crossing over the railing: Protagonist layer > Iron Gate
                # X-axis is STRICTLY locked to self.vault_start_x (no left/right movement)
                if self.vault_timer < 0.45:
                    p = self.vault_timer / 0.45
                    # Higher soaring leap to comfortably clear the top of the fence railing (y=510)
                    lift = math.sin(p * math.pi * 0.5) * 285.0
                    dest_y = self.vault_start_y + lift
                    self.player.place(self.vault_start_x, dest_y)
                    self.player.character_scale = 0.22
                    self.player.facing = 'up'
                    self.player.is_moving = False
                    self.player._update_texture()
                # Sub-phase B: Leaping onto/over the railing, landing on the pathway, and receding into backyard
                # During this phase, Iron Gate layer > Protagonist (Iron Gate drawn OVER protagonist)
                else:
                    recede_t = self.vault_timer - 0.45
                    p_recede = min(1.0, recede_t / 1.25)
                    # First 0.22s: drop from high peak onto the cobblestone path
                    if recede_t <= 0.22:
                        p_land = recede_t / 0.22
                        # Smooth landing down onto path (center y=285, feet on cobblestones at y=217)
                        dest_y = (self.vault_start_y + 285.0) - p_land * (285.0 - 60.0)
                    else:
                        # Walking deeper along cobblestone path into the backyard shadows
                        p_walk = min(1.0, (recede_t - 0.22) / 1.03)
                        dest_y = 285.0 + p_walk * 42.0

                    self.player.place(self.vault_start_x, dest_y)
                    # Gradually shrink character_scale (0.18 -> 0.025) into the deep darkness
                    scale_val = max(0.025, 0.18 - p_recede * 0.155)
                    self.player.character_scale = scale_val
                    self.player.facing = 'up'
                    self.player.is_moving = True

                    # Seamless scene transition: start fading to black as character walks deep into shadows
                    if p_recede >= 0.35:
                        self.is_transitioning = True
                        self.stage = STAGE_ENTERING

                    # Completely vanished into the backyard darkness: mark vanished so he never pops back
                    if self.vault_timer >= 1.70:
                        self.player_vault_disappeared = True

        # 1. Player Movement & Boundaries (Supports Sprinting with SHIFT)
        if not self.dialogue.active and not self.is_transitioning and not self.is_dead and not self.vault_active:
            move_x = (1 if self.key_right else 0) - (1 if self.key_left else 0)
            move_y = (1 if self.key_up else 0) - (1 if self.key_down else 0)

            # Sprinting mechanic: Hold [Shift] to run faster down the avenue!
            is_sprinting = self.key_shift and (move_x != 0 or move_y != 0)
            if is_sprinting:
                self.player.speed = 440.0
                self.player.step_interval = 0.08
            else:
                self.player.speed = 240.0
                self.player.step_interval = 0.13

            # Check if player's FEET genuinely step inside any water puddle
            feet_x = self.player.x
            feet_y = self.player.y - 83.6  # Exact bottom of shoes
            in_puddle = False
            for p in self.puddles:
                px, py = p["x"], p["y"]
                pw, ph = p["w"], p["h"]
                dx = (feet_x - px) / max(1.0, pw * 0.5)
                dy = (feet_y - py) / max(1.0, ph * 0.5)
                if dx * dx + dy * dy <= 1.0:
                    in_puddle = True
                    break

            if in_puddle:
                self.player.footstep_sound = "Walk on puddle"
            else:
                self.player.footstep_sound = "Normal Walk"

            prev_frame = self.player.anim_frame_idx
            # Pass dust_particles=None to avoid spawning fake dust on rainy wet ground
            self.player.update(
                dt, move_x, move_y, None,
                bounds=(130, WORLD_WIDTH - 150, PLAYER_Y_MIN, PLAYER_Y_MAX)
            )

            # Spawn ripples and water splash droplets when feet hit the puddle
            if in_puddle and self.player.is_moving:
                if self.player.anim_frame_idx in (1, 3) and self.player.anim_frame_idx != prev_frame:
                    # Spawn ripple directly at feet location inside the puddle!
                    self.puddle_ripples.append([feet_x, feet_y, 4.0, random.uniform(20, 32), 200])
                    # Spawn real water splash droplets scattering outward (water splash FX)
                    for _ in range(4):
                        sp_x = feet_x + random.uniform(-16, 16)
                        sp_y = feet_y + random.uniform(0, 12)
                        self.rain_splashes.append([sp_x, sp_y, random.uniform(2.5, 4.5), 230])

        # 1b. Car Traffic Simulation & Special Effects
        if not self.is_dead:
            self.car_x -= self.car_speed * dt

            # 4-frame animation loop
            self.car_frame_timer += dt
            if self.car_frame_timer >= 0.09:
                self.car_frame_timer = 0.0
                self.car_frame = (self.car_frame + 1) % len(self.car_textures)

            # Tire water spray emission
            if random.random() < 0.80:
                for tx in [self.car_x - self.car_w * 0.28, self.car_x + self.car_w * 0.31]:
                    self.car_water_sprays.append([
                        tx + random.uniform(-6, 6),
                        self.car_y - self.car_h * 0.38 + random.uniform(-2, 4),
                        random.uniform(50, 150),
                        random.uniform(20, 65),
                        random.uniform(2.5, 4.5),
                        210.0
                    ])

            # Exhaust smoke particles emission from rear exhaust pipe
            if random.random() < 0.60:
                self.car_smoke.append([
                    self.car_x + self.car_w * 0.44 + random.uniform(-4, 4),
                    self.car_y - 38 + random.uniform(-3, 3),
                    random.uniform(35, 75),
                    random.uniform(12, 28),
                    random.uniform(6.0, 9.0),
                    random.uniform(24.0, 36.0),
                    120.0
                ])

            # Warning horn if player is on the road ahead
            if not self.car_honked and self.player.y <= 145:
                dist_to_player = self.car_x - self.player.x
                if 120 < dist_to_player < 420:
                    self.car_honked = True
                    self.audio.play("car_horn", volume_scale=0.9)

            # Car collision detection with player
            if self.player.y <= 145:
                dx = abs(self.player.x - self.car_x)
                dy = abs(self.player.y - self.car_y)
                if dx < (self.car_w * 0.38 + 22) and dy < (self.car_h * 0.38 + 26):
                    self._trigger_car_hit_death()

            # Recycle car once offscreen past camera left
            cam_left = self.cam_x - SCREEN_WIDTH / 2
            if self.car_x < max(-300, cam_left - 450):
                self.car_respawn_timer += dt
                if self.car_respawn_timer >= 3.5:
                    self.car_respawn_timer = 0.0
                    self.car_x = min(WORLD_WIDTH + 450, self.cam_x + SCREEN_WIDTH / 2 + random.uniform(350, 650))
                    self.car_honked = False

        # Update tire water spray particles
        for sp in self.car_water_sprays[:]:
            sp[0] += sp[2] * dt
            sp[1] += sp[3] * dt
            sp[3] -= 180.0 * dt
            sp[5] -= 420.0 * dt
            if sp[5] <= 0:
                self.car_water_sprays.remove(sp)

        # Update exhaust smoke particles
        for sm in self.car_smoke[:]:
            sm[0] += sm[2] * dt
            sm[1] += sm[3] * dt
            sm[4] = min(sm[5], sm[4] + dt * 18.0)
            sm[6] -= 85.0 * dt
            if sm[6] <= 0:
                self.car_smoke.remove(sm)

        # 2. Camera Tracking (Smooth Lerp + Screen Shake)
        half_screen = SCREEN_WIDTH / 2
        self.cam_target_x = max(half_screen, min(WORLD_WIDTH - half_screen, self.player.x))
        self.cam_x += (self.cam_target_x - self.cam_x) * min(1.0, dt * 8.0)
        if self.world_cam:
            self.world_cam.position = (self.cam_x + self.shake_offset_x, SCREEN_HEIGHT / 2 + self.shake_offset_y)

        # 3. Rain Particle Update
        for r in self.raindrops:
            r[0] += math.cos(math.radians(105)) * r[2] * dt
            r[1] -= math.sin(math.radians(105)) * r[2] * dt
            if r[1] <= 150:
                # Spawn splash on ground in world coordinates (UNDER the player)
                if random.random() < 0.40:
                    ground_wx = self.cam_x - SCREEN_WIDTH / 2 + r[0]
                    # Do not spawn ground splash inside bus shelter or under vending machine
                    if not (85 <= ground_wx <= 575) and not (850 <= ground_wx <= 990):
                        ground_wy = random.uniform(50, 185)
                        self.rain_splashes.append([ground_wx, ground_wy, 2.0, 150])
                r[0] = random.uniform(-60, SCREEN_WIDTH + 60)
                r[1] = SCREEN_HEIGHT + random.uniform(5, 35)

        # Update rain splashes
        for sp in self.rain_splashes[:]:
            sp[2] += 28.0 * dt
            sp[3] -= 450.0 * dt
            if sp[3] <= 0:
                self.rain_splashes.remove(sp)

        # Update puddle ripples
        for rip in self.puddle_ripples[:]:
            rip[2] += 38.0 * dt
            rip[4] -= 220.0 * dt
            if rip[4] <= 0 or rip[2] >= rip[3]:
                self.puddle_ripples.remove(rip)

        # Update dust / footstep particles
        for d in self.dust_particles[:]:
            d.update(dt)
            if d.life <= 0:
                self.dust_particles.remove(d)

        # 4. Thunder & Lightning Logic
        self.lightning_timer -= dt
        if self.lightning_timer <= 0:
            self.lightning_flash = 0.12
            self.thunder_delay = random.uniform(0.9, 1.4)
            self.lightning_timer = random.uniform(14.0, 26.0)

        if self.lightning_flash > 0:
            self.lightning_flash -= dt

        if self.thunder_delay > 0:
            self.thunder_delay -= dt
            if self.thunder_delay <= 0:
                self.audio.play("thunder", volume_scale=0.7)

        # 5. Animated Mansion Rain Frame Advance
        if self.tex_house_frames:
            self.house_anim_timer += dt
            if self.house_anim_timer >= self.house_frame_duration:
                self.house_anim_timer -= self.house_frame_duration
                self.house_frame_idx = (self.house_frame_idx + 1) % len(self.tex_house_frames)

        # 6. Scene Stage Progress
        if self.player.x > 2750 and self.stage == STAGE_WALKING:
            self.stage = STAGE_AT_HOUSE

        # 7. Fade-to-black on entering kitchen
        if self.is_transitioning:
            self.fade_alpha = min(255.0, self.fade_alpha + dt * 220.0)
            if self.fade_alpha >= 255.0:
                self._load_kitchen_scene()

    def _start_gate_vault(self):
        """Initiate rapid-tap gate vaulting interaction at the side gate."""
        self.vault_active = True
        self.vault_power = 0.0
        self.vault_phase = 0
        self.vault_stage = 1
        self.vault_sprint_taps = 0
        self.vault_is_99_fail = False
        self.player_vault_disappeared = False
        self.vault_timer = 0.0
        self.vault_jump_t = 0.0
        # Exactly center player at the gate opening (x=4037.08, y=225.0)
        self.vault_start_x = 4037.08
        self.vault_start_y = 225.0
        self.player.place(self.vault_start_x, self.vault_start_y)
        # Strictly show clean back view (facing up, idle back pose)
        self.player.facing = 'up'
        self.player.is_moving = False
        self.player.anim_frame_idx = 0
        self.player.anim_timer = 0.0
        self.player._update_texture()
        self.vault_last_tap_time = self.t
        self.audio.play("Normal Walk", volume_scale=0.6)

    def _register_vault_tap(self):
        """Called when user presses SPACE or clicks during gate vaulting."""
        if not self.vault_active or self.vault_phase != 0:
            return

        self.vault_last_tap_time = self.t

        # Stage 1: Build momentum to 100%
        if self.vault_stage == 1:
            self.vault_power = min(1.0, self.vault_power + 0.11)
            self.audio.play("Normal Walk", min_interval=0.06, volume_scale=0.65)
            # Check if reached 100% threshold
            if self.vault_power >= 1.0:
                self.vault_power = 1.0
                self.vault_stage = 2
                self.vault_sprint_taps = 0
                self.vault_last_tap_time = self.t
                self.audio.play("click", volume_scale=0.9)
                self.shake_duration = 0.15
                self.shake_intensity = 3.0

        # Stage 2: Final Sprint - 5 consecutive taps without pause!
        elif self.vault_stage == 2:
            self.vault_sprint_taps += 1
            self.audio.play("Normal Walk", min_interval=0.04, volume_scale=0.85)

            # 5 consecutive taps completed without interruption -> Jump over the gate!
            if self.vault_sprint_taps >= 5:
                self.vault_phase = 2
                self.vault_timer = 0.0
                self.audio.play('table_slam', volume_scale=0.55)
                self.shake_duration = 0.35
                self.shake_intensity = 7.0

    def _load_kitchen_scene(self):
        """Enter the S05 backyard before reaching the old kitchen door."""
        self.audio.stop_sound("rain_loop")
        from scenes.scene_5_backyard_view import BackyardView
        if not hasattr(self, "_backyard_view"):
            self._backyard_view = BackyardView(street_view=self)
        self.window.show_view(self._backyard_view)

    # ---------------------------------------------------------------- Draw
    def on_draw(self):
        self.clear(color=(12, 15, 24))

        # =========================================================================
        # 1. WORLD CAMERA: Parallax World Layers
        # =========================================================================
        if self.world_cam:
            self.world_cam.use()

        cam_l = self.cam_x - SCREEN_WIDTH / 2
        cam_r = self.cam_x + SCREEN_WIDTH / 2

        # Layer A: Far Parallax Sky & Skyline (Factor 0.20)
        sky_w = 2560
        sky_shift = (cam_l * 0.20) % sky_w
        first_sky_x = cam_l - sky_shift
        for i in range(3):
            sx = first_sky_x + i * sky_w
            arcade.draw_texture_rect(self.tex_sky, arcade.XYWH(sx + sky_w / 2, SCREEN_HEIGHT / 2, sky_w, SCREEN_HEIGHT))

        # Layer B: Midground Suburban Houses & Power Lines (Factor 0.50)
        mid_w = 2560
        mid_shift = (cam_l * 0.50) % mid_w
        first_mid_x = cam_l - mid_shift
        for i in range(3):
            mx = first_mid_x + i * mid_w
            arcade.draw_texture_rect(self.tex_mid, arcade.XYWH(mx + mid_w / 2, 485, mid_w, 500))

        # Layer C: Walking Surface (Street Sidewalk Pavement)
        pave_w = 1280
        num_tiles = int(math.ceil(WORLD_WIDTH / pave_w)) + 1
        for i in range(num_tiles):
            px = i * pave_w + pave_w / 2
            arcade.draw_texture_rect(self.tex_pave, arcade.XYWH(px, 140, pave_w, 280))

        # Layer D: Bus Stop Shelter at the Street Corner (x = 330, right next to lamp #1 at x=75)
        arcade.draw_texture_rect(self.tex_shelter, arcade.XYWH(330, 290, 480, 285))

        # Layer E: The Luxury Mansion Exterior (x = 3460) with Living Rain Effect
        # Positioned with stone mailbox pillar at x ~ 2810 to backyard gate at x ~ 4040
        house_cx = 3460
        current_tex = self.tex_house_frames[self.house_frame_idx] if self.tex_house_frames else self.tex_house
        # Tight transparent sprites share one canvas; preserve their native ratio.
        house_width = 1450
        house_height = house_width * current_tex.height / current_tex.width
        # Positioned forward close to the street for an immersive, prominent mansion facade
        house_cy = 468.0
        # Deeper cold midnight storm tint (darker slate-blue for authentic nocturnal shadow)
        mansion_night_tint = arcade.types.Color(115, 125, 145, 255)
        arcade.draw_texture_rect(
            current_tex,
            arcade.XYWH(house_cx, house_cy, house_width, house_height),
            color=mansion_night_tint
        )

        # Wrought-Iron Side Gate Ajar Indicator when unlatched
        if self.latch_unlocked:
            # Faint cool lantern light through the opened side gate leading to backyard
            gate_world_x = house_cx - 1450 / 2 + 1450 * 0.90
            gate_world_y = 175
            arcade.draw_ellipse_filled(gate_world_x, gate_world_y, 45, 115, (170, 210, 245, 50))
            arcade.draw_line(gate_world_x - 12, gate_world_y - 45, gate_world_x - 12, gate_world_y + 45, (190, 225, 255, 190), 2.5)

        # Layer F: Ground Puddles (Distinct organic shapes, zero house overlap)
        for p in self.puddles:
            ptype = p["type"]
            px, py = p["x"], p["y"]
            pw, ph = p["w"], p["h"]

            if ptype == "curb_run":
                # Type 1: Elongated narrow water runoff against the curb bevel
                arcade.draw_ellipse_filled(px, py, pw, ph, (10, 14, 20, 95))
                arcade.draw_ellipse_filled(px + 10, py + 1, pw * 0.72, ph * 0.8, (110, 145, 185, 30))
                # Delicate water edge meniscus highlight along the curb line
                arcade.draw_line(px - pw * 0.4, py - ph * 0.35, px + pw * 0.4, py - ph * 0.35, (160, 195, 230, 42), 1.5)

            elif ptype == "dual_lobe":
                # Type 2: Double-lobed merged pools
                arcade.draw_ellipse_filled(px - 14, py, pw * 0.68, ph * 1.1, (10, 14, 20, 90))
                arcade.draw_ellipse_filled(px + 22, py - 3, pw * 0.54, ph * 0.85, (10, 14, 20, 85))
                # Translucent sky sheens
                arcade.draw_ellipse_filled(px - 10, py, pw * 0.5, ph * 0.75, (110, 145, 185, 28))
                arcade.draw_ellipse_filled(px + 20, py - 3, pw * 0.38, ph * 0.6, (110, 145, 185, 24))
                # Warm streetlamp reflection glint
                if p.get("tint") == "warm_lamp":
                    flick = math.sin(self.t * 22.0) * 3.5
                    arcade.draw_ellipse_filled(px - 4, py + 1, 30 + flick, 10, (255, 215, 130, 36))
                    arcade.draw_ellipse_filled(px - 4, py + 1, 14 + flick * 0.5, 5, (255, 240, 190, 48))

            elif ptype == "shallow_spread":
                # Type 3: Wide shallow pavement depression across slab seams
                arcade.draw_ellipse_filled(px, py, pw, ph, (12, 16, 22, 75))
                arcade.draw_ellipse_filled(px - 8, py - 1, pw * 0.78, ph * 0.75, (115, 150, 190, 26))
                arcade.draw_ellipse_filled(px + 24, py + 1, pw * 0.42, ph * 0.6, (115, 150, 190, 20))
                # Subtle sky sheen center
                arcade.draw_ellipse_filled(px - 4, py - 1, pw * 0.4, ph * 0.45, (180, 215, 245, 22))

            elif ptype == "cluster":
                # Type 4: Three irregular splash droplets
                arcade.draw_ellipse_filled(px, py, pw * 0.65, ph * 0.9, (12, 15, 22, 85))
                arcade.draw_ellipse_filled(px - 30, py - 4, 26, 12, (12, 15, 22, 70))
                arcade.draw_ellipse_filled(px + 34, py + 3, 22, 10, (12, 15, 22, 65))
                # Sky sheens
                arcade.draw_ellipse_filled(px, py, pw * 0.45, ph * 0.6, (110, 145, 185, 28))
                arcade.draw_ellipse_filled(px - 30, py - 4, 18, 7, (110, 145, 185, 22))

        # Draw Puddle Ripples
        for rx, ry, rrad, max_rad, ralpha in self.puddle_ripples:
            col = (180, 215, 245, int(ralpha))
            arcade.draw_ellipse_outline(rx, ry, rrad * 2, rrad * 0.8, col, 1.5)

        # Layer G: Streetlamps along the street
        for lx in self.lamp_positions:
            arcade.draw_texture_rect(self.tex_lamp, arcade.XYWH(lx, 325, 140, 390))

            # Volumetric Streetlamp Light Cone
            cone_w_top = 35
            cone_w_bot = 260
            lamp_bulb_y = 475
            flicker = math.sin(self.t * 26.0 + lx) * 3.0
            pts = [
                (lx - cone_w_top / 2, lamp_bulb_y),
                (lx + cone_w_top / 2, lamp_bulb_y),
                (lx + cone_w_bot / 2 + flicker, 135),
                (lx - cone_w_bot / 2 - flicker, 135),
            ]
            arcade.draw_polygon_filled(pts, (255, 215, 130, 22))

            # Multi-layer soft feathered light pool on the ground
            for rw, rh, alpha in [(270, 52, 12), (200, 38, 20), (130, 24, 30), (60, 12, 42)]:
                arcade.draw_ellipse_filled(lx, 138, rw + flicker, rh, (255, 215, 125, alpha))

        # Layer G2: Glowing Anime Vending Machine (Centered EXACTLY under streetlamp #2 at x=920)
        if self.tex_vending:
            vx, vy = 920, 268
            # Draw subtle ambient ground reflection under the vending machine
            arcade.draw_ellipse_filled(vx, 148, 130, 20, (15, 65, 90, 16))
            arcade.draw_ellipse_filled(vx, 148, 70, 10, (30, 110, 145, 20))
            # Draw authentic anime vending machine sprite (Centered exactly with lamp post!)
            arcade.draw_texture_rect(self.tex_vending, arcade.XYWH(vx, vy, 134, 235))

        # Ground Rain Droplet Splashes (World Space, drawn on ground UNDER the character)
        for sx, sy, srad, salpha in self.rain_splashes:
            col = (185, 215, 245, int(salpha))
            arcade.draw_ellipse_outline(sx, sy, srad * 2, srad * 0.7, col, 1.2)

        # Layer H: Modern Chef Character & Traffic (Depth-Sorted)
        corr = self.aspect_ratio_correction
        if self.player_vault_disappeared:
            # Character has disappeared into the dark backyard; do NOT draw him so he never pops back!
            self._draw_car_traffic(corr)
        # When jumping on street side before crossing railing (vault_phase == 1, or vault_phase == 2 before 0.45s)
        elif self.vault_active and (self.vault_phase == 1 or (self.vault_phase == 2 and self.vault_timer < 0.45)):
            # Draw grounded shadow at feet position
            ground_shadow_y = self.vault_start_y - self.player.feet_offset + 4
            lift = max(0.0, self.player.y - self.vault_start_y)
            shadow_scale = max(0.12, 1.0 - lift / 260.0)
            shadow_w = 70 * corr * shadow_scale
            shadow_h = 16 * shadow_scale
            shadow_alpha = int(max(10, 85 * shadow_scale))
            arcade.draw_ellipse_filled(self.player.x, ground_shadow_y, shadow_w, shadow_h, (0, 0, 0, shadow_alpha))
            # Draw sprite
            self.player.sprite.scale_x = self.player.character_scale * corr
            self.player.sprite.scale_y = self.player.character_scale
            self.player.sprite_list.draw()
            self._draw_car_traffic(corr)
        elif self.vault_active and self.vault_phase == 2:
            # Sub-phase B: Character has leaped over railing onto path behind gate, shrinking
            path_shadow_y = self.player.y - self.player.feet_offset + 3
            scale_ratio = self.player.character_scale / 0.18
            shadow_w = 38 * corr * scale_ratio
            shadow_h = 10 * scale_ratio
            arcade.draw_ellipse_filled(self.player.x, path_shadow_y, shadow_w, shadow_h, (0, 0, 0, int(60 * scale_ratio)))
            self.player.sprite.scale_x = self.player.character_scale * corr
            self.player.sprite.scale_y = self.player.character_scale
            self.player.sprite_list.draw()
            self._draw_car_traffic(corr)
        else:
            if self.player.y > self.car_y:
                self.player.draw(corr)
                self._draw_car_traffic(corr)
            else:
                self._draw_car_traffic(corr)
                self.player.draw(corr)

        # Layer H2: Cutout Wrought-Iron Gate Foreground Layer (Draws OVER player ONLY after leaping onto/over railing & shrinking!)
        if self.tex_gate_frames and ((self.vault_active and self.vault_phase == 2 and self.vault_timer >= 0.45) or self.is_transitioning):
            gate_tex = self.tex_gate_frames[self.house_frame_idx % len(self.tex_gate_frames)]
            # Match Layer E (mansion background) 100% pixel-perfectly without subpixel offset
            crop_scale = house_width / current_tex.width
            gate_w = gate_tex.width * crop_scale
            gate_h = gate_tex.height * crop_scale
            gate_left = (house_cx - house_width / 2.0) + 1340.0 * crop_scale
            gate_top = (house_cy + house_height / 2.0) - 315.0 * crop_scale
            gate_cx = gate_left + gate_w / 2.0
            gate_cy = gate_top - gate_h / 2.0
            mansion_night_tint = arcade.types.Color(115, 125, 145, 255)
            arcade.draw_texture_rect(
                gate_tex,
                arcade.XYWH(gate_cx, gate_cy, gate_w, gate_h),
                color=mansion_night_tint
            )

        # Layer I: Dynamic World Street Ambient Fog / Rain Haze
        haze_alpha = int(28 + math.sin(self.t * 1.5) * 6)
        arcade.draw_rect_filled(
            arcade.XYWH(self.cam_x, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
            (10, 16, 28, haze_alpha)
        )

        # Layer J: Interactive Landmark Prompts (In World Space)
        if not self.dialogue.active and not self.is_transitioning:
            self._draw_interactive_prompts()

        # =========================================================================
        # 2. UI CAMERA: Overlays, Dialogue, Pause Menu
        # =========================================================================
        if self.ui_cam:
            self.ui_cam.use()

        # Foreground Rain Streaks (rendered in screen space for consistent density)
        # Exclude bus shelter (x: 85..575, y <= 440) and vending machine (x: 845..995, y <= 390)
        cam_left = self.cam_x - SCREEN_WIDTH / 2
        for r in self.raindrops:
            rx, ry = r[0], r[1]
            wx = cam_left + rx
            wy = ry

            # Don't draw rain streak over the bus shelter
            if 85 <= wx <= 575 and wy <= 440:
                continue

            # Don't draw rain streak over the vending machine
            if 845 <= wx <= 995 and wy <= 390:
                continue

            dx = math.cos(math.radians(105)) * r[3]
            dy = math.sin(math.radians(105)) * r[3]
            arcade.draw_line(rx, ry, rx + dx, ry - dy, (175, 205, 240, 145), 1.5)

        # Distant Lightning Flash Overlay
        if self.lightning_flash > 0:
            flash_alpha = min(210, int((self.lightning_flash / 0.12) * 200))
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (210, 235, 255, flash_alpha)
            )

        # Narrative Bar & Interactive Vault HUD Overlay
        self._draw_cinematic_hud()

        # Dialogue Box
        self.dialogue.draw(corr)

        # Scene Transition Fade-to-black
        if self.is_transitioning and self.fade_alpha > 0:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (8, 8, 12, int(self.fade_alpha))
            )
            if self.fade_alpha > 120:
                arcade.draw_text(
                    "[ Slipping inside the dark, familiar kitchen... ]",
                    SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                    (245, 230, 200), 20, anchor_x="center", bold=True
                )

        # Death & Respawn Screen Overlay
        if self.is_dead:
            self._draw_death_overlay(corr)

        # Global Pause & Exit Overlay
        self.draw_pause_overlay()

    def _draw_car_traffic(self, corr: float):
        """Draw 4-frame animated car with headlights, wet road reflections, smoke, and tire spray."""
        if not self.car_textures:
            return

        cx = self.car_x
        cy = self.car_y
        cw = self.car_w * corr
        ch = self.car_h

        # 1. Wet asphalt tire contact shadow
        arcade.draw_ellipse_filled(cx, cy - ch * 0.44, cw * 0.90, 16, (8, 10, 16, 175))

        # 2. Volumetric Headlight Beams (Facing left)
        hl_x = cx - cw * 0.44
        hl_y = cy - 6
        beam_len = 390 * corr
        top_y = hl_y + 18
        bot_y = hl_y - 56

        # Outer soft volumetric light cone
        pts_outer = [
            (hl_x, hl_y),
            (hl_x - beam_len, top_y),
            (hl_x - beam_len - 45 * corr, bot_y),
            (hl_x - 12, bot_y + 12),
        ]
        arcade.draw_polygon_filled(pts_outer, (255, 240, 160, 34))

        # Core intense beam
        pts_core = [
            (hl_x, hl_y),
            (hl_x - beam_len * 0.65, top_y - 6),
            (hl_x - beam_len * 0.70, bot_y + 10),
            (hl_x - 12, bot_y + 14),
        ]
        arcade.draw_polygon_filled(pts_core, (255, 250, 195, 52))

        # Headlight bulb corona & flare
        flicker = math.sin(self.t * 30.0) * 1.5
        arcade.draw_circle_filled(hl_x, hl_y, 14 + flicker, (255, 245, 180, 190))
        arcade.draw_circle_filled(hl_x, hl_y, 6, (255, 255, 245, 255))

        # Wet road specular reflection from headlights
        arcade.draw_ellipse_filled(hl_x - 160 * corr, cy - 42, 230 * corr, 24, (255, 225, 120, 36))
        arcade.draw_ellipse_filled(hl_x - 160 * corr, cy - 42, 130 * corr, 12, (255, 245, 180, 50))

        # 3. Draw animated car sprite (Frame 0-3 loop)
        car_tex = self.car_textures[self.car_frame]
        arcade.draw_texture_rect(car_tex, arcade.XYWH(cx, cy, cw, ch))

        # 4. Rear Taillight Red Glow
        tl_x = cx + cw * 0.45
        tl_y = cy - 12
        arcade.draw_circle_filled(tl_x, tl_y, 14, (255, 30, 20, 115))
        arcade.draw_circle_filled(tl_x, tl_y, 4, (255, 180, 160, 225))

        # 5. Tire water spray mist
        for sp in self.car_water_sprays:
            col = (185, 215, 245, int(sp[5]))
            arcade.draw_circle_filled(sp[0], sp[1], sp[4], col)

        # 6. Exhaust smoke puffs
        for sm in self.car_smoke:
            sm_col = (135, 145, 160, int(sm[6]))
            arcade.draw_circle_filled(sm[0], sm[1], sm[4], sm_col)

    def _draw_death_overlay(self, corr: float):
        """Draw dark bloody death screen with center Respawn button."""
        alpha = int(min(240, self.death_alpha))

        # 1. Dark crimson/black fullscreen veil
        arcade.draw_rect_filled(
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
            (16, 4, 6, alpha)
        )
        # Heavy outer vignette border
        arcade.draw_rect_outline(
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH - 24, SCREEN_HEIGHT - 24),
            (150, 20, 25, int(alpha * 0.75)), 3.5
        )

        # 2. Organic blood splatters radiating across screen
        for b in self.blood_splatters:
            bx, by, br, drops, col = b["x"], b["y"], b["r"], b["drops"], b["color"]
            b_alpha = int(alpha * 0.82)
            arcade.draw_ellipse_filled(bx, by, br * 1.6, br * 1.2, (col[0], col[1], col[2], b_alpha))
            for dx, dy, dr in drops:
                arcade.draw_circle_filled(bx + dx, by + dy, dr, (col[0], col[1], col[2], b_alpha))

        # 3. Header Text
        arcade.draw_text(
            "FATAL COLLISION",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 75,
            (255, 45, 40, int(alpha)), 32,
            anchor_x="center", bold=True
        )
        arcade.draw_text(
            "Struck down by oncoming traffic on the dark asphalt road.",
            SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 35,
            (250, 230, 230, int(alpha * 0.95)), 14,
            anchor_x="center"
        )

        # 4. Center Respawn Button
        btn_w = 320 * corr
        btn_h = 52
        btn_x = SCREEN_WIDTH / 2
        btn_y = SCREEN_HEIGHT / 2 - 45
        pulse = math.sin(self.t * 4.0) * 0.25 + 0.75

        bg_col = (45, 12, 16, int(245 * pulse)) if not self.respawn_btn_hovered else (85, 20, 28, 255)
        border_col = (255, 60, 50, int(255 * pulse)) if not self.respawn_btn_hovered else (255, 215, 80, 255)

        arcade.draw_rect_filled(arcade.XYWH(btn_x, btn_y, btn_w, btn_h), bg_col)
        arcade.draw_rect_outline(arcade.XYWH(btn_x, btn_y, btn_w, btn_h), border_col, 2.2)

        arcade.draw_text(
            "▶  RESPAWN",
            btn_x, btn_y - 7,
            (255, 240, 220, int(255 * pulse)), 15,
            anchor_x="center", bold=True
        )
        arcade.draw_text(
            "[ Press SPACE / ENTER or CLICK to Respawn ]",
            btn_x, btn_y - 46,
            (240, 225, 225, int(alpha * 0.9)), 12,
            anchor_x="center"
        )

    def _draw_interactive_prompts(self):
        """Draw proximity interaction pills above player's head when near landmarks."""
        px = self.player.x

        # Landmark 1: Mailbox (No. 27 on Stone Pillar, x = 2750 to 2890)
        if 2750 < px < 2890:
            self.player.draw_interact_prompt("[E] Read Mailbox & House Plate")

        # Landmark 2: Grand Front Porch & Double Doors (x = 3100 to 3290)
        elif 3100 < px < 3290:
            self.player.draw_interact_prompt("[E] Try Front Double Doors")

        # Landmark 3: Living Room Floor-to-Ceiling Windows (x = 3530 to 3720)
        elif 3530 < px < 3720:
            self.player.draw_interact_prompt("[E] Peer Through High Windows")

        # Landmark 4: Wrought-Iron Side Gate (x > 3960)
        elif px > 3960:
            if not self.vault_active and not self.is_transitioning:
                self.player.draw_interact_prompt("[E] Vault Over Gate into Backyard")
            elif self.vault_active and self.vault_phase == 0 and self.vault_stage == 2:
                # Stage 2: Flashing floating TAP! TAP! TAP! prompt above player
                flash_v = (math.sin(self.t * 16.0) + 1.0) / 2.0
                flash_c = (255, int(210 + 45 * flash_v), int(40 + 215 * flash_v))
                bounce = abs(math.sin(self.t * 14.0)) * 6.0
                arcade.draw_text("TAP! TAP! TAP!", self.player.x, self.player.y + 78 + bounce, flash_c, 13, bold=True, anchor_x="center")

    def _draw_cinematic_hud(self):
        """Draw top narrative bar with chapter title and current goal."""
        # Rapid-Tap Vaulting HUD overlay when scaling gate (Prominent center-screen gauge with Threshold Target Line)
        if self.vault_active and self.vault_phase in (0, 1):
            vh_cx = SCREEN_WIDTH / 2
            vh_cy = 145
            box_w = 580
            box_h = 108

            # Border styling
            if self.vault_phase == 1:
                bg_border = (245, 80, 80)
            elif self.vault_stage == 2:
                pulse_b = int(180 + 75 * ((math.sin(self.t * 12.0) + 1.0) / 2.0))
                bg_border = (255, pulse_b, 60)
            else:
                bg_border = COLOR_GOLD

            # Semi-transparent high-contrast backing
            arcade.draw_rect_filled(arcade.XYWH(vh_cx, vh_cy, box_w, box_h), (10, 14, 22, 235))
            arcade.draw_rect_outline(arcade.XYWH(vh_cx, vh_cy, box_w, box_h), bg_border, 2.0)

            # Top prompt line
            pct_int = int(min(1.0, self.vault_power) * 100)
            if self.vault_phase == 1:
                if self.vault_is_99_fail:
                    arcade.draw_text("⚡ MISSED BY A HAIR! (99% JUMP - SPRINT INTERRUPTED)",
                                     vh_cx, vh_cy + 24, (255, 95, 85), 13, bold=True, anchor_x="center")
                else:
                    arcade.draw_text("⚡ INSUFFICIENT MOMENTUM! MOMENTUM DRAINING RAPIDLY...",
                                     vh_cx, vh_cy + 24, (255, 95, 85), 13, bold=True, anchor_x="center")
            elif self.vault_stage == 2:
                # Stage 2: Flashing TAP! TAP! TAP! prompt
                flash_v = (math.sin(self.t * 16.0) + 1.0) / 2.0
                flash_col = (255, int(210 + 45 * flash_v), int(40 + 215 * flash_v))
                arcade.draw_text("⚡ TAP!  TAP!  TAP! ⚡",
                                 vh_cx, vh_cy + 24, flash_col, 16, bold=True, anchor_x="center")
            else:
                arcade.draw_text("⚡ RAPIDLY MASH [SPACE] OR CLICK MOUSE TO SCALE THE GATE!",
                                 vh_cx, vh_cy + 24, COLOR_GOLD, 13, bold=True, anchor_x="center")

            # Progress gauge bar (width 440, offset left by 24px so the 100% circle fits neatly on the right)
            bar_w = 440
            bar_h = 22
            bar_cx = vh_cx - 24
            bar_y = vh_cy - 8
            arcade.draw_rect_filled(arcade.XYWH(bar_cx, bar_y, bar_w, bar_h), (25, 30, 42))
            arcade.draw_rect_outline(arcade.XYWH(bar_cx, bar_y, bar_w, bar_h), (140, 165, 205), 1.5)

            # Fill bar
            fill_w = bar_w * min(1.0, self.vault_power)
            if fill_w > 0:
                if self.vault_phase == 1:
                    gauge_color = (245, 65, 55)  # Fast-collapsing crimson bar
                elif self.vault_stage == 2:
                    pulse_g = int(215 + 40 * math.sin(self.t * 10.0))
                    gauge_color = (50, pulse_g, 120)  # Stage 2 glowing full gauge
                else:
                    gauge_color = (90, 235, 140) if self.vault_power >= 0.90 else ((245, 195, 60) if self.vault_power >= 0.50 else (90, 175, 245))
                arcade.draw_rect_filled(arcade.XYWH(bar_cx - bar_w / 2 + fill_w / 2, bar_y, fill_w, bar_h - 4), gauge_color)

            # 100% Circle Badge on the right side of the threshold bar
            circle_cx = bar_cx + bar_w / 2 + 25
            circle_cy = bar_y
            circle_r = 17

            if self.vault_stage == 2:
                # Stage 2: Pulsing bright green / gold badge
                pulse_r = (math.sin(self.t * 12.0) + 1.0) / 2.0
                badge_bg = (35, int(155 + 50 * pulse_r), 75)
                badge_ring = (255, 240, 130)
                txt_col = (255, 255, 255)
                # Outer glow pulse ring
                arcade.draw_circle_outline(circle_cx, circle_cy, circle_r + 3.0 * pulse_r, (255, 230, 90, int(160 * (1.0 - pulse_r))), 1.8)
            elif self.vault_power >= 0.90:
                badge_bg = (50, 42, 22)
                badge_ring = (255, 215, 80)
                txt_col = (255, 235, 130)
            else:
                badge_bg = (20, 26, 38)
                badge_ring = (130, 155, 195)
                txt_col = (175, 195, 225)

            arcade.draw_circle_filled(circle_cx, circle_cy, circle_r, badge_bg)
            arcade.draw_circle_outline(circle_cx, circle_cy, circle_r, badge_ring, 2.2)
            arcade.draw_text("100%", circle_cx, circle_cy, txt_col, 9, bold=True, anchor_x="center", anchor_y="center")

            # Status line
            if self.vault_phase == 1:
                if self.vault_is_99_fail:
                    status_note = "MISSED BY A HAIR! (Stopped at 99% - Resetting to Stage 1...)"
                    status_col = (255, 110, 100)
                else:
                    status_note = f"MOMENTUM EXHAUSTED: {pct_int}%  (Draining to 0 - Land and tap without stopping!)"
                    status_col = (255, 120, 110)
            elif self.vault_stage == 2:
                dots = "● " * self.vault_sprint_taps + "○ " * (5 - self.vault_sprint_taps)
                status_note = f"CONSECUTIVE TAPS: [ {dots.strip()} ] ({self.vault_sprint_taps}/5)  -  TAP RAPIDLY WITHOUT PAUSE!"
                status_col = (255, 230, 110)
            else:
                status_note = f"MOMENTUM: {pct_int}%  (Decaying steadily! Reach 100% to enter Final Sprint)"
                status_col = (245, 215, 130) if self.vault_power >= 0.60 else (210, 225, 245)
            arcade.draw_text(status_note, vh_cx, vh_cy - 34, status_col, 11, bold=True, anchor_x="center")



    # ---------------------------------------------------------------- Controls
    def on_key_press(self, key, modifiers):
        if self.handle_pause_key(key):
            return

        if key == arcade.key.F11:
            self.toggle_fullscreen()
            return

        # Handle respawn when dead
        if self.is_dead:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.R):
                self._respawn_player()
            return

        if self.dialogue.active:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                self.dialogue.advance()
            return

        # Rapid tap vaulting with SPACE / ENTER / E / W / UP
        if self.vault_active and self.vault_phase == 0:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E, arcade.key.W, arcade.key.UP):
                self._register_vault_tap()
                return

        if key in (arcade.key.W, arcade.key.UP):
            self.key_up = True
        elif key in (arcade.key.S, arcade.key.DOWN):
            self.key_down = True
        elif key in (arcade.key.A, arcade.key.LEFT):
            self.key_left = True
        elif key in (arcade.key.D, arcade.key.RIGHT):
            self.key_right = True
        elif key in (arcade.key.LSHIFT, arcade.key.RSHIFT):
            self.key_shift = True
        elif key == arcade.key.E:
            self._handle_interaction()

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.W, arcade.key.UP):
            self.key_up = False
        elif key in (arcade.key.S, arcade.key.DOWN):
            self.key_down = False
        elif key in (arcade.key.A, arcade.key.LEFT):
            self.key_left = False
        elif key in (arcade.key.D, arcade.key.RIGHT):
            self.key_right = False
        elif key in (arcade.key.LSHIFT, arcade.key.RSHIFT):
            self.key_shift = False
        if not (self.key_up or self.key_down or self.key_left or self.key_right):
            self.player.stop_footstep()

    def on_mouse_motion(self, x, y, dx, dy):
        if self.handle_pause_mouse_motion(x, y):
            return

        if self.is_dead:
            vx, vy = self.to_virtual_coords(x, y)
            corr = self.aspect_ratio_correction
            btn_w = 320 * corr
            btn_h = 52
            btn_x = SCREEN_WIDTH / 2
            btn_y = SCREEN_HEIGHT / 2 - 45
            self.respawn_btn_hovered = (abs(vx - btn_x) <= btn_w / 2 and abs(vy - btn_y) <= btn_h / 2)
            return

    def on_mouse_press(self, x, y, button, modifiers):
        if self.handle_pause_mouse_press(x, y, button):
            return

        # Click to respawn when dead
        if self.is_dead:
            self._respawn_player()
            return

        if self.dialogue.active:
            self.dialogue.advance()
            return

        # Mouse click tap for gate vaulting
        if self.vault_active and self.vault_phase == 0:
            self._register_vault_tap()

    # ---------------------------------------------------------------- Interaction Logic
    def _handle_interaction(self):
        px = self.player.x

        # Landmark 1: Mailbox (No. 27 on Stone Pillar)
        if 2750 < px < 2890:
            self.inspected_mailbox = True
            self.audio.play("click")
            self.dialogue.start_dialogue([
                ("Mailbox", "He wipes rain off the bronze mailbox on the stone pillar.", (210, 175, 120)),
                ("Pillar Plaque", "Engraved in weathered brass: 'No. 27'. Stamped across it is a judicial foreclosure seal.", (235, 198, 110)),
                ("Chef", "A cold reminder of the ruinous court judgment. My career, my savings, and this estate... all confiscated.", (210, 175, 120), self.portrait_thinking),
            ])

        # Landmark 2: Grand Front Porch & Double Doors
        elif 3100 < px < 3290:
            self.inspected_front_door = True
            self.audio.play("click")
            self.dialogue.start_dialogue([
                ("Front Porch", "He steps onto the wide stone porch beneath the grand portico, sheltering from the downpour.", (210, 175, 120)),
                ("Front Doors", "He grips the bronze door handles. The heavy oak doors are padlocked shut with heavy steel chains.", (235, 100, 90)),
                ("Chef", "The bailiff took the main keys weeks ago. There is no way in through the front.", (210, 175, 120), self.portrait_chef),
            ])

        # Landmark 3: Two-Story Living Room Windows
        elif 3530 < px < 3720:
            self.inspected_window = True
            self.audio.play("click")
            self.dialogue.start_dialogue([
                ("Window", "He peers past the rain running down the tall floor-to-ceiling glass panes.", (210, 175, 120)),
                ("Inside", "Heavy curtains hang motionless. Inside the cavernous hall, designer furniture sits covered under white drop cloths.", (220, 180, 120)),
                ("Chef", "No warmth, no lights. An empty tomb of former glory.", (210, 175, 120), self.portrait_thinking),
            ])

        # Landmark 4: Wrought-Iron Side Gate - Rapid-Tap Vaulting Interaction
        elif px > 3960:
            if not self.vault_active and not self.is_transitioning:
                self.dialogue.start_dialogue([
                    ("Wrought-Iron Gate", "The side gate is padlocked shut. Through the iron bars, the wet cobblestone path winds into the backyard.", (210, 175, 120)),
                    ("Chef", "\"I used to vault over this gate when I forgot my keys as an apprentice. Let's see if I've still got the spring in my legs.\"", (235, 215, 170), self.portrait_chef),
                    ("Tutorial", "[ Repeatedly press [SPACE] or Click Mouse rapidly to build momentum and vault over the gate! ]", COLOR_GOLD),
                ], on_complete=self._start_gate_vault)


# Backward compatibility alias
RainyStreetView = Scene5View


if __name__ == "__main__":
    window = arcade.Window(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Scene 5: Outside His Old Home",
        resizable=False,
        fullscreen=START_FULLSCREEN,
    )
    if START_FULLSCREEN:
        window.set_fullscreen(True)
    view = Scene5View()
    window.show_view(view)
    arcade.run()
