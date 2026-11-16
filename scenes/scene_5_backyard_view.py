# Upgraded BackyardView with Realistic 4-Pin Tumbler Lockpicking Minigame
# Features:
# 1. Stage 1: Door Lock Exterior - Clear painted brass keyhole; drag the boning knife into the keyhole.
# 2. Stage 2: 4-Pin Tumbler Alignment:
#    - 4 distinct heights across the 4 chambers.
#    - No auto-binding: player manually pushes pin up/down (Mouse drag / W/S / Up/Down).
#    - When reaching the correct sweet spot, a crisp click sound rings out!
#    - Player must explicitly press [SPACE] (or click BIND button) to fix/bind the pin.
#    - Bound pins STAY AT THEIR EXACT TARGET HEIGHT (no jumping to top!).
#    - Pressing SPACE at wrong position shakes the pin and pops up "INCORRECT POSITION!".
# 3. 100% English text across all UI, prompts, and dialogues.
import math
import random
import arcade
from arcade.types.rect import LRBT
from core.base_view import BaseGameView
from core.constants import ASSETS_DIR, SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD
from core.player import Player
from core.audio import AudioManager
from core.dialogue import DialogueBox
from scenes.backyard_layout import (can_walk, SPAWN, DOOR, CORRIDOR_EXIT,
                                    POND_RIPPLE_X, POND_RIPPLE_TOP_Y)


class BackyardView(BaseGameView):
    def __init__(self, street_view=None):
        super().__init__()
        self.street_view = street_view
        self.texture = arcade.load_texture(str(ASSETS_DIR / 'Scene 5' / 'backyard_map.png'))
        self.w, self.h = self.texture.width, self.texture.height
        self.open_door_texture = arcade.load_texture(str(ASSETS_DIR / 'Scene 5' / 'backyard_door_open.png'))
        self.lock_backplate = arcade.load_texture(str(ASSETS_DIR / 'Scene 5' / 'wooden_door_lock_backplate.png'))
        self.lock_tool = arcade.load_texture(str(ASSETS_DIR / 'Scene 5' / 'lockpick_tool.png'))
        self.lock_tool_tip_fraction = .5
        self.world_cam = None
        self.keys = set()
        self.player = Player(0, 0, char_id='modern', scale=.18)
        self._place_feet(*SPAWN)
        self.player.facing = 'up'
        self.dialogue = DialogueBox()
        self.audio = AudioManager()
        self.door_unlatched = False
        self.fade = 0.0
        self.fade_in_alpha = 255.0
        self.entering = False
        self.door_open_hold = 0.0
        self.time = 0.0
        rng = random.Random(527)
        self.rain = [[rng.uniform(0, self.w), rng.uniform(0, self.h), rng.uniform(450, 650)] for _ in range(155)]
        self.ripples = []
        self.ripple_timer = 0.0
        self.rng = rng

        # Character portraits
        scene1_dir = ASSETS_DIR / "Scene 1"
        self.portrait_chef = arcade.load_texture(str(scene1_dir / "Modern Chief.png"))
        self.portrait_thinking = arcade.load_texture(str(scene1_dir / "Chief Thinking.png"))

        # Lockpicking State
        self.picking_lock = False
        self.lock_stage = "insert"        # "insert" (drag pick to keyhole) or "tumbler" (internal cutaway)

        # Stage 1: Tool Dragging
        self.tool_drag_x = SCREEN_WIDTH / 2 - 240.0
        self.tool_drag_y = SCREEN_HEIGHT / 2 - 110.0
        self.tool_drag_offset_x = 0.0
        self.tool_drag_offset_y = 0.0
        self.is_dragging_tool = False
        self.tool_inserted = False
        self.insert_anim_t = 0.0

        # Stage 2: 4-Pin Tumbler Mechanism
        self.selected_pin = 0
        self.tool_x = 470.0
        self.tool_target_x = 470.0
        self.pin_xs = [470.0, 580.0, 690.0, 800.0]
        # Realistic variable key-pin heights
        self.pin_heights = [44.0, 62.0, 34.0, 52.0]
        # 4 distinct target heights for the 4 pins (shallow to deep)
        self.target_lifts = [24.0, 68.0, 42.0, 56.0]
        self.pin_lifts = [0.0] * 4
        self.pin_locked = [False] * 4
        self.pin_wobble = [0.0] * 4
        self.pin_played_click = [False] * 4
        self.cylinder_turn = 0.0          # 0.0 to 90.0 degrees
        self.lock_shake = 0.0
        self.lock_solved = False
        self.lock_success_timer = 0.0
        self.pick_sound_cooldown = 0.0
        self.mouse_lifting = False
        self.mouse_drag_start_y = 0.0
        self.mouse_drag_initial_lift = 0.0
        self.sparks = []                  # Golden particle sparks [(x, y, vx, vy, life, color)]
        self.floating_popups = []         # Floating popups [{"x", "y", "vy", "text", "color", "timer", "max_time"}]

    def _place_feet(self, x, top_y):
        self.player.place(x, self.h - top_y + self.player.feet_offset - 8)

    def _feet(self):
        return self.player.x, self.h - (self.player.y - self.player.feet_offset + 8)

    def on_show_view(self):
        super().on_show_view()
        self.keys.clear()
        self.fade_in_alpha = 255.0
        self.world_cam = arcade.camera.Camera2D(window=self.window)
        self._fit_camera()
        self.audio.play('rain_loop', volume_scale=.4)

    def _fit_camera(self):
        if not self.world_cam or not self.window: return
        scale = min(self.window.width / self.w, self.window.height / self.h)
        vw, vh = round(self.w * scale), round(self.h * scale)
        left, bottom = (self.window.width - vw) // 2, (self.window.height - vh) // 2
        self.world_cam.viewport = LRBT(left, left + vw, bottom, bottom + vh)
        self.world_cam.projection = LRBT(-self.w / 2, self.w / 2, -self.h / 2, self.h / 2)
        self.world_cam.position = (self.w / 2, self.h / 2)

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self._fit_camera()

    def on_hide_view(self):
        self.keys.clear()

    def _near_door(self):
        x, y = self._feet()
        return math.hypot(x - DOOR[0], y - DOOR[1]) < 87

    def _near_corridor(self):
        x, y = self._feet()
        return math.hypot(x - CORRIDOR_EXIT[0], y - CORRIDOR_EXIT[1]) < 50

    def _start_lockpick_minigame(self):
        """Trigger door lock minigame: starts with Stage 1 (insert tool into keyway)."""
        self.picking_lock = True
        self.lock_stage = "insert"
        self.keys.clear()

        # Tool start position in Stage 1
        mid_x, mid_y = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 8
        self.tool_drag_x = mid_x - 240.0
        self.tool_drag_y = mid_y - 110.0
        self.tool_drag_offset_x = 0.0
        self.tool_drag_offset_y = 0.0
        self.is_dragging_tool = False
        self.tool_inserted = False
        self.insert_anim_t = 0.0

        # Stage 2 setup: 4 distinct randomized heights across chambers
        self.selected_pin = 0
        self.tool_x = self.pin_xs[0]
        self.tool_target_x = self.pin_xs[0]

        # Distinct heights: shallow (24), mid-shallow (40), mid-deep (56), deep (70)
        height_pool = [24.0, 40.0, 56.0, 70.0]
        random.shuffle(height_pool)
        self.target_lifts = [round(h + random.uniform(-2.0, 2.0), 1) for h in height_pool]

        self.pin_lifts = [0.0] * 4
        self.pin_locked = [False] * 4
        self.pin_wobble = [0.0] * 4
        self.pin_played_click = [False] * 4
        self.cylinder_turn = 0.0
        self.lock_shake = 0.0
        self.lock_solved = False
        self.lock_success_timer = 0.0
        self.mouse_lifting = False
        self.sparks.clear()
        self.floating_popups.clear()
        self.audio.play('click', volume_scale=0.6)

    def _attempt_bind_pin(self, pin_idx: int):
        """Called when user presses SPACE or clicks BIND button."""
        if not self.picking_lock or self.lock_stage != "tumbler" or self.lock_solved:
            return

        if self.pin_locked[pin_idx]:
            return

        target = self.target_lifts[pin_idx]
        diff = abs(self.pin_lifts[pin_idx] - target)
        px = self.pin_xs[pin_idx]

        # Check if inside Sweet Spot (diff <= 4.5 px)
        if diff <= 4.5:
            # SUCCESSFUL BIND: pin stays at this exact target height!
            self.pin_locked[pin_idx] = True
            self.pin_lifts[pin_idx] = target
            self.audio.play('lock_click', volume_scale=1.0)
            self.lock_shake = 0.45

            # Golden sparks burst
            for _ in range(22):
                self.sparks.append([
                    px, 340.0 + target * 0.5,
                    random.uniform(-65, 65), random.uniform(-20, 75),
                    0.45, (255, 220, 100)
                ])

            # Floating success pill in English
            self.floating_popups.append({
                "x": px,
                "y": 425.0,
                "vy": 40.0,
                "text": "PIN SET!",
                "color": (110, 245, 140),
                "timer": 0.0,
                "max_time": 1.2
            })

            # Recalculate cylinder turn
            locked_count = sum(self.pin_locked)
            self.cylinder_turn = (locked_count / 4.0) * 90.0

            # Check all 4 pins bound
            if locked_count >= 4:
                self.lock_solved = True
                self.door_unlatched = True
                self.audio.play('lock_unlock', volume_scale=0.95)
        else:
            # FAILED BIND: Jolt, shake pin, and pop up "INCORRECT POSITION!"
            self.pin_wobble[pin_idx] = 1.0
            self.lock_shake = 0.35
            self.audio.play('click', volume_scale=0.8)

            self.floating_popups.append({
                "x": px,
                "y": 425.0,
                "vy": 45.0,
                "text": "INCORRECT POSITION!",
                "color": (255, 90, 80),
                "timer": 0.0,
                "max_time": 1.1
            })

    def on_update(self, dt):
        if self.is_paused or not self.window or not getattr(self.window, '_active', True):
            self.keys.clear()
            return
        dt = min(dt, .1)
        self.time += dt
        self.dialogue.update(dt)

        if self.entering:
            # Give the player time to see the open doorway before fading out.
            hold_time = min(dt, self.door_open_hold)
            self.door_open_hold -= hold_time
            self.fade = min(255, self.fade + (dt - hold_time) * 240)
            if self.fade >= 255:
                from scenes.scene_6_home_kitchen_view import HomeKitchenView
                self.window.show_view(HomeKitchenView())
            return

        # =========================================================================
        # LOCKPICKING MINIGAME UPDATE
        # =========================================================================
        if self.picking_lock:
            # Stage 1: Insert tool animation update
            if self.lock_stage == "insert":
                if self.tool_inserted:
                    self.insert_anim_t += dt
                    if self.insert_anim_t >= 0.45:
                        self.lock_stage = "tumbler"
                        self.lock_shake = 0.3
                        self.audio.play('lock_click', volume_scale=0.85)
                return

            # Stage 2: 4-Pin Tumbler Mechanism
            for sp in self.sparks:
                sp[0] += sp[2] * dt
                sp[1] += sp[3] * dt
                sp[3] -= 160.0 * dt
                sp[4] -= dt
            self.sparks = [sp for sp in self.sparks if sp[4] > 0]

            # Update floating text popups
            for p in self.floating_popups:
                p["y"] += p["vy"] * dt
                p["timer"] += dt
            self.floating_popups = [p for p in self.floating_popups if p["timer"] < p["max_time"]]

            self.pick_sound_cooldown -= dt
            if self.lock_shake > 0:
                self.lock_shake = max(0.0, self.lock_shake - dt * 3.5)

            for i in range(4):
                if self.pin_wobble[i] > 0:
                    self.pin_wobble[i] = max(0.0, self.pin_wobble[i] - dt * 3.2)

            # Smooth tool horizontal sliding
            self.tool_target_x = self.pin_xs[self.selected_pin]
            self.tool_x += (self.tool_target_x - self.tool_x) * min(1.0, dt * 20.0)

            if not self.lock_solved:
                is_key_up = bool(self.keys & {arcade.key.W, arcade.key.UP})
                is_key_down = bool(self.keys & {arcade.key.S, arcade.key.DOWN})

                for i in range(4):
                    if self.pin_locked[i]:
                        # Locked pins stay strictly at their target heights
                        self.pin_lifts[i] = self.target_lifts[i]
                        continue

                    if i == self.selected_pin:
                        target_lift = self.target_lifts[i]

                        # Keyboard upward pushing
                        if is_key_up:
                            self.pin_lifts[i] = min(80.0, self.pin_lifts[i] + dt * 42.0)

                        # Keyboard downward lowering
                        elif is_key_down:
                            self.pin_lifts[i] = max(0.0, self.pin_lifts[i] - dt * 42.0)

                        # Distance to target height
                        diff = abs(self.pin_lifts[i] - target_lift)

                        # Entering Sweet Spot (diff <= 4.0 px) -> Play crisp click sound!
                        if diff <= 4.0:
                            if not self.pin_played_click[i]:
                                self.pin_played_click[i] = True
                                self.audio.play('lock_click', volume_scale=0.95)
                                self.lock_shake = 0.2
                                px = self.pin_xs[i]
                                for _ in range(4):
                                    self.sparks.append([px, 350.0 + target_lift * 0.4, random.uniform(-20, 20), random.uniform(10, 35), 0.26, (255, 235, 120)])
                        else:
                            if diff > 5.5:
                                self.pin_played_click[i] = False

                # Cylinder rotation tracks number of locked pins
                target_cyl = (sum(self.pin_locked) / 4.0) * 90.0
                self.cylinder_turn += (target_cyl - self.cylinder_turn) * min(1.0, dt * 10.0)
            else:
                # Victory sequence
                self.cylinder_turn = min(90.0, self.cylinder_turn + dt * 140.0)
                self.lock_success_timer += dt
                if self.lock_success_timer >= 1.3:
                    self.picking_lock = False
                    self.dialogue.start_dialogue([
                        ('Old Kitchen Door', 'The last tumbler clicks home with a heavy metallic *THUNK*! The rusted deadbolt unlatches.', COLOR_GOLD),
                        ('Chef', "\"Still remembers my touch after all these years... Now, just a bowl of noodles before morning.\"", (210, 175, 120), self.portrait_chef),
                        ('Tutorial', '[ Press [E] to slip into the dark kitchen. ]', COLOR_GOLD),
                    ])
            return

        # Smooth fade-in from street transition
        if self.fade_in_alpha > 0:
            self.fade_in_alpha = max(0.0, self.fade_in_alpha - dt * 260.0)

        # Player walking & sprinting logic
        mx = int(bool(self.keys & {arcade.key.D, arcade.key.RIGHT})) - int(bool(self.keys & {arcade.key.A, arcade.key.LEFT}))
        my = int(bool(self.keys & {arcade.key.W, arcade.key.UP})) - int(bool(self.keys & {arcade.key.S, arcade.key.DOWN}))
        if self.dialogue.active: mx = my = 0
        is_sprint = bool(self.keys & {arcade.key.LSHIFT, arcade.key.RSHIFT})
        self.player.speed = 340 if is_sprint else 190
        self.player.step_interval = 0.08 if is_sprint else 0.13
        steps = max(1, math.ceil(self.player.speed * dt / 5))
        for _ in range(steps):
            old_x, old_y = self.player.x, self.player.y
            self.player.update(dt / steps, mx, my, dust_particles=None, bounds=(0, self.w, 0, self.h))
            new_x, new_y = self.player.x, self.player.y
            fy = self.h - (old_y - self.player.feet_offset + 8)
            x = new_x if can_walk(new_x, fy) else old_x
            fy_new = self.h - (new_y - self.player.feet_offset + 8)
            y = new_y if can_walk(x, fy_new) else old_y
            self.player.place(x, y)

        for drop in self.rain:
            drop[0] += dt * 45
            drop[1] -= dt * drop[2]
            if drop[1] < 0: drop[0], drop[1] = self.rng.uniform(0, self.w), self.h + 20

        self.ripple_timer += dt
        if self.ripple_timer > .16:
            self.ripple_timer = 0
            self.ripples.append([self.rng.uniform(*POND_RIPPLE_X), self.h - self.rng.uniform(*POND_RIPPLE_TOP_Y), 0.0])
        for r in self.ripples: r[2] += dt
        self.ripples = [r for r in self.ripples if r[2] < .8]

    # =========================================================================
    # DRAW OVERLAYS
    # =========================================================================
    def _draw_lock_insert_stage(self):
        """Stage 1: Close-up of door lock hardware. Player manually drags pick to keyhole."""
        mid_x = SCREEN_WIDTH / 2
        mid_y = SCREEN_HEIGHT / 2 - 8

        # Dim background vignette
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (4, 7, 12, 235))

        # Close-up Door Backplate
        panel_w, panel_h = 780, 520
        arcade.draw_rect_filled(arcade.XYWH(mid_x + 7, mid_y - 7, panel_w + 6, panel_h + 6), (0, 0, 0, 130))
        arcade.draw_texture_rect(
            self.lock_backplate,
            arcade.XYWH(mid_x, mid_y, panel_w, panel_h),
            color=arcade.types.Color(165, 170, 180, 255)
        )

        # Escutcheon circular brass plate location (on the right below the handle)
        cx = mid_x + 184.4
        cy = mid_y - 44.6

        # Keyhole Slot (Dark vertical keyway aperture directly on the brass plate)
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, 4, 18), (6, 8, 12, 255))
        arcade.draw_circle_filled(cx, cy + 9, 3.5, (6, 8, 12, 255))
        arcade.draw_circle_filled(cx, cy - 9, 2.5, (6, 8, 12, 255))
        # Subtle metallic bevel highlight on the right slot edge
        arcade.draw_line(cx + 2.5, cy + 10, cx + 2.5, cy - 10, (140, 125, 85, 140), 1.0)

        # The Lockpick Tool (Steel boning knife / pick)
        tool_angle = 38.0
        tool_h = 230
        tool_w = tool_h * self.lock_tool.width / self.lock_tool.height
        rad = math.radians(tool_angle)
        offset_tip_x = 70.6
        offset_tip_y = 90.4

        if self.tool_inserted:
            # Slide into keyway animation
            progress = min(1.0, self.insert_anim_t / 0.45)
            # Center of knife when tip aligns with keyhole:
            knife_base_x = cx - offset_tip_x
            knife_base_y = cy - offset_tip_y
            slide_dist = progress * 24.0
            render_x = knife_base_x + math.sin(rad) * slide_dist
            render_y = knife_base_y + math.cos(rad) * slide_dist
            arcade.draw_texture_rect(self.lock_tool, arcade.XYWH(render_x, render_y, tool_w, tool_h), angle=tool_angle)
        else:
            # Draggable tool
            arcade.draw_texture_rect(self.lock_tool, arcade.XYWH(self.tool_drag_x, self.tool_drag_y, tool_w, tool_h), angle=tool_angle)

        # Header guidance HUD in pure English
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT - 44, SCREEN_WIDTH, 54), (10, 14, 22, 225))
        arcade.draw_line(0, SCREEN_HEIGHT - 71, SCREEN_WIDTH, SCREEN_HEIGHT - 71, (65, 75, 95, 180), 1.5)
        arcade.draw_text('OLD KITCHEN DOOR - CYLINDER PADLOCK', SCREEN_WIDTH / 2, SCREEN_HEIGHT - 34, COLOR_GOLD, 16, bold=True, anchor_x='center')
        arcade.draw_text('Drag the boning pick into the brass keyhole to pick the lock  [Click & Drag Mouse]', SCREEN_WIDTH / 2, SCREEN_HEIGHT - 58, (205, 220, 240), 12, anchor_x='center')

    def _draw_lock_tumbler_stage(self):
        """Stage 2: 4-Pin Tumbler Cutaway Mechanism with individual heights & manual SPACE binding."""
        mid_x = SCREEN_WIDTH / 2
        mid_y = SCREEN_HEIGHT / 2

        # Vignette
        arcade.draw_rect_filled(arcade.XYWH(mid_x, mid_y, SCREEN_WIDTH, SCREEN_HEIGHT), (4, 7, 12, 235))

        if self.lock_shake > 0:
            mid_x += (random.random() - 0.5) * self.lock_shake * 12.0
            mid_y += (random.random() - 0.5) * self.lock_shake * 12.0

        # Background door backplate shadow
        arcade.draw_texture_rect(
            self.lock_backplate,
            arcade.XYWH(mid_x, mid_y - 8, 820, 530),
            color=arcade.types.Color(110, 115, 125, 140)
        )

        # Cutaway Chassis
        box_w, box_h = 760, 440
        arcade.draw_rect_filled(arcade.XYWH(mid_x, mid_y, box_w, box_h), (30, 34, 42))
        arcade.draw_rect_outline(arcade.XYWH(mid_x, mid_y, box_w, box_h), (75, 85, 100), 4)

        # Corner Rivets
        for rx in [-box_w/2 + 20, box_w/2 - 20]:
            for ry in [-box_h/2 + 20, box_h/2 - 20]:
                arcade.draw_circle_filled(mid_x + rx, mid_y + ry, 6, (175, 150, 95))
                arcade.draw_circle_outline(mid_x + rx, mid_y + ry, 6, (40, 35, 25), 1.5)

        # Inner Cavity
        inner_w, inner_h = box_w - 32, box_h - 32
        arcade.draw_rect_filled(arcade.XYWH(mid_x, mid_y, inner_w, inner_h), (14, 17, 23))

        # Upper Static Cylinder Housing
        arcade.draw_rect_filled(arcade.XYWH(mid_x, mid_y + 115, inner_w, 150), (22, 26, 35))

        # Rotating Brass Plug
        plug_y = mid_y - 35
        plug_h = 90
        arcade.draw_rect_filled(arcade.XYWH(mid_x, plug_y, inner_w, plug_h), (52, 45, 32))
        for ly in range(int(plug_y - plug_h/2 + 4), int(plug_y + plug_h/2), 6):
            alpha_v = int(25 + 20 * math.sin((ly - plug_y) * 0.1))
            arcade.draw_line(mid_x - inner_w/2, ly, mid_x + inner_w/2, ly, (200, 175, 100, alpha_v), 1)

        # Keyway Channel
        keyway_y = mid_y - 125
        keyway_h = 75
        arcade.draw_rect_filled(arcade.XYWH(mid_x, keyway_y, inner_w, keyway_h), (8, 10, 15))
        arcade.draw_line(mid_x - inner_w/2, keyway_y + keyway_h/2, mid_x + inner_w/2, keyway_y + keyway_h/2, (40, 48, 60), 2)

        # 4 Pin Chambers
        driver_h = 50
        chamber_top = mid_y + 172

        for i, base_px in enumerate(self.pin_xs):
            # Wobble offset if space was pressed at wrong position
            wobble_x = 0.0
            if self.pin_wobble[i] > 0:
                wobble_x = math.sin(self.time * 42.0) * (self.pin_wobble[i] * 9.0)
            px = base_px + wobble_x

            k_h = self.pin_heights[i]
            is_locked = self.pin_locked[i]
            lift = self.pin_lifts[i]
            target_lift = self.target_lifts[i]
            diff = abs(lift - target_lift)
            is_sweet = (diff <= 4.5)

            # Chamber background
            arcade.draw_rect_filled(arcade.XYWH(px, mid_y + 25, 46, 280), (10, 12, 17))
            arcade.draw_rect_outline(arcade.XYWH(px, mid_y + 25, 46, 280), (45, 52, 65), 1.5)

            # Target shear shelf for this chamber
            target_seam = keyway_y + keyway_h/2 + k_h + target_lift - 20
            # Target notch markers at chamber sides
            notch_col = (110, 235, 140) if is_locked else ((255, 220, 80) if is_sweet else (80, 92, 110))
            arcade.draw_triangle_filled(px - 22, target_seam, px - 28, target_seam + 4, px - 28, target_seam - 4, notch_col)
            arcade.draw_triangle_filled(px + 22, target_seam, px + 28, target_seam + 4, px + 28, target_seam - 4, notch_col)

            # Pin vertical positions:
            # Bound pins stay at their exact target height (they do NOT jump to the top!)
            seam = keyway_y + keyway_h/2 + k_h + lift - 20
            key_top = seam
            key_bottom = key_top - k_h

            if is_locked:
                driver_bottom = seam + 2.0  # Caught on the shear ledge right at that height
            else:
                driver_bottom = seam
            driver_top = driver_bottom + driver_h

            # Spring
            sp_top = chamber_top
            sp_bottom = driver_top
            coils = 8
            h_sp = max(15, sp_top - sp_bottom)
            step = h_sp / (coils * 2)
            pts = [(px, sp_top)]
            for c in range(1, coils * 2):
                side = 1 if c % 2 == 1 else -1
                pts.append((px + side * 14, sp_top - c * step))
            pts.append((px, sp_bottom))
            for p_idx in range(len(pts) - 1):
                sp_col = (255, 215, 90) if is_sweet else ((185, 210, 235) if is_locked else (130, 140, 155))
                arcade.draw_line(pts[p_idx][0], pts[p_idx][1], pts[p_idx+1][0], pts[p_idx+1][1], sp_col, 2.5)

            # Driver Pin (Upper Pin)
            drv_col = (210, 195, 145) if is_locked else (155, 145, 125)
            drv_mid_y = (driver_top + driver_bottom) / 2
            arcade.draw_rect_filled(arcade.XYWH(px, drv_mid_y, 34, driver_h), drv_col)
            arcade.draw_rect_outline(arcade.XYWH(px, drv_mid_y, 34, driver_h), (55, 50, 40), 1.5)

            # Key Pin (Bottom Pin)
            key_col = (225, 195, 95) if is_locked else ((255, 220, 80) if is_sweet else (185, 150, 80))
            key_mid_y = (key_top + key_bottom) / 2
            arcade.draw_rect_filled(arcade.XYWH(px, key_mid_y, 34, k_h), key_col)
            arcade.draw_rect_outline(arcade.XYWH(px, key_mid_y, 34, k_h), (65, 50, 25), 1.5)

            # Conical tip
            tip_pts = [(px - 17, key_bottom), (px + 17, key_bottom), (px, key_bottom - 12)]
            arcade.draw_polygon_filled(tip_pts, key_col)
            arcade.draw_line(px - 17, key_bottom, px, key_bottom - 12, (65, 50, 25), 1.5)
            arcade.draw_line(px + 17, key_bottom, px, key_bottom - 12, (65, 50, 25), 1.5)

            # Sweet spot feedback glow right at this chamber's seam
            if is_sweet and not is_locked:
                pulse_s = (math.sin(self.time * 16.0) + 1.0) / 2.0
                arcade.draw_circle_filled(px, target_seam, 14 + pulse_s * 4, (255, 220, 100, int(130 + 90 * pulse_s)))

            # Roman Numeral & Status Tag in English
            numeral = ['I', 'II', 'III', 'IV'][i]
            arcade.draw_text(numeral, px, mid_y - 172, (215, 220, 230), 13, bold=True, anchor_x='center')

            if is_locked:
                status_text, status_col = '[ LOCKED ]', (110, 235, 140)
            elif is_sweet:
                status_text, status_col = '⚡ [ READY (SPACE) ]', (255, 230, 80)
            else:
                status_text, status_col = '[ UNLOCKED ]', (130, 140, 155)

            arcade.draw_text(status_text, px, mid_y - 192, status_col, 10, bold=True, anchor_x='center')

        # Selected Pin Cursor Indicator
        sel_px = self.pin_xs[self.selected_pin]
        arcade.draw_triangle_filled(sel_px, mid_y - 148, sel_px - 10, mid_y - 160, sel_px + 10, mid_y - 160, (255, 215, 75))

        # Boning Knife Tool inside the cutaway keyway
        active_lift = self.pin_lifts[self.selected_pin]
        blade_y = keyway_y + active_lift - 5
        arcade.draw_line(mid_x - inner_w/2, blade_y - 10, self.tool_x, blade_y - 10, (160, 168, 180), 9)
        arcade.draw_line(mid_x - inner_w/2, blade_y - 8, self.tool_x, blade_y - 8, (230, 238, 250), 3)
        tip_poly = [
            (self.tool_x - 4, blade_y - 14),
            (self.tool_x + 18, blade_y - 10),
            (self.tool_x + 8, blade_y),
            (self.tool_x - 8, blade_y - 5)
        ]
        arcade.draw_polygon_filled(tip_poly, (200, 208, 220))

        # Golden Sparks
        for sp in self.sparks:
            alpha = int(255 * (sp[4] / 0.45))
            arcade.draw_circle_filled(sp[0], sp[1], 2.8, (sp[5][0], sp[5][1], sp[5][2], alpha))

        # Floating Popups (Strictly English: "INCORRECT POSITION!" / "PIN SET!")
        for p in self.floating_popups:
            progress = p["timer"] / p["max_time"]
            alpha = max(0, min(255, int(255 * (1.0 - progress))))
            bg_alpha = max(0, min(255, int(225 * (1.0 - progress))))
            pill_w = len(p["text"]) * 10 + 26
            arcade.draw_rect_filled(arcade.XYWH(p["x"], p["y"], pill_w, 28), (18, 6, 8, bg_alpha))
            arcade.draw_rect_outline(arcade.XYWH(p["x"], p["y"], pill_w, 28), (p["color"][0], p["color"][1], p["color"][2], alpha), 1.8)
            arcade.draw_text(p["text"], p["x"], p["y"] - 5, (p["color"][0], p["color"][1], p["color"][2], alpha), 11, bold=True, anchor_x="center")

        # Header HUD in English
        arcade.draw_rect_filled(arcade.XYWH(mid_x, SCREEN_HEIGHT - 38, SCREEN_WIDTH, 48), (10, 14, 22, 220))
        arcade.draw_line(0, SCREEN_HEIGHT - 62, SCREEN_WIDTH, SCREEN_HEIGHT - 62, (65, 75, 95, 180), 1.5)
        arcade.draw_text('OLD KITCHEN DOOR - 4-PIN TUMBLER MECHANISM', mid_x, SCREEN_HEIGHT - 28, COLOR_GOLD, 15, bold=True, anchor_x='center')
        arcade.draw_text('4 Chambers have different depths! Push up/down -> listen for CLICK -> press [SPACE] to SET!', mid_x, SCREEN_HEIGHT - 49, (205, 220, 240), 11, anchor_x='center')

        # Interactive BIND Button (Spacebar Trigger) in English
        btn_w, btn_h = 280, 42
        btn_y = 66
        current_diff = abs(self.pin_lifts[self.selected_pin] - self.target_lifts[self.selected_pin])
        is_cur_sweet = (current_diff <= 4.5) and not self.pin_locked[self.selected_pin]

        if is_cur_sweet:
            pulse_b = (math.sin(self.time * 12.0) + 1.0) / 2.0
            btn_bg = (35, int(130 + 40 * pulse_b), 70, 245)
            btn_border = (255, 225, 80, 255)
            btn_txt = "⚡ [ SET PIN  (SPACE) ]"
            btn_txt_col = (255, 250, 220)
        else:
            btn_bg = (24, 28, 38, 235)
            btn_border = (75, 85, 105, 200)
            btn_txt = "[ SET PIN  (SPACE) ]"
            btn_txt_col = (180, 195, 215)

        arcade.draw_rect_filled(arcade.XYWH(mid_x, btn_y, btn_w, btn_h), btn_bg)
        arcade.draw_rect_outline(arcade.XYWH(mid_x, btn_y, btn_w, btn_h), btn_border, 2.0)
        arcade.draw_text(btn_txt, mid_x, btn_y - 6, btn_txt_col, 13, bold=True, anchor_x="center")

        # Cylinder Turn Bar (Left side of bottom HUD)
        cyl_pct = int((self.cylinder_turn / 90.0) * 100)
        arcade.draw_text(f"Cylinder: {self.cylinder_turn:.1f}° ({cyl_pct}%)", mid_x - 310, btn_y + 8, (255, 220, 120), 11, bold=True)
        arcade.draw_rect_filled(arcade.XYWH(mid_x - 240, btn_y - 12, 140, 10), (25, 30, 40))
        arcade.draw_rect_outline(arcade.XYWH(mid_x - 240, btn_y - 12, 140, 10), (90, 110, 140), 1.2)
        fill_turn = 140 * (self.cylinder_turn / 90.0)
        if fill_turn > 0:
            arcade.draw_rect_filled(arcade.XYWH(mid_x - 310 + fill_turn / 2, btn_y - 12, fill_turn, 8), (90, 220, 130))

        # Locked Progress Counter (Right side)
        locked_num = sum(self.pin_locked)
        arcade.draw_text(f"Pins Set: {locked_num} / 4", mid_x + 220, btn_y + 8, (120, 225, 150), 12, bold=True)
        dots = "● " * locked_num + "○ " * (4 - locked_num)
        arcade.draw_text(dots.strip(), mid_x + 220, btn_y - 12, (255, 220, 120), 13, bold=True)

        # Control instruction footer in English
        arcade.draw_text("Controls: [A/D] Select Pin   |   [Mouse Drag / W/S] Push Up/Down   |   [SPACE / Click Button] Set Pin   |   [ESC] Exit",
                         mid_x, 18, (175, 190, 210), 11, anchor_x="center")

    def _draw_lockpick_overlay(self):
        """Draw active lockpicking overlay based on current stage."""
        if self.lock_stage == "insert":
            self._draw_lock_insert_stage()
        else:
            self._draw_lock_tumbler_stage()

    def on_draw(self):
        self.clear(color=(8, 10, 16))
        if not self.world_cam: return
        self.world_cam.use()
        backyard_night_tint = arcade.types.Color(115, 125, 145, 255)
        arcade.draw_texture_rect(
            self.texture,
            arcade.XYWH(self.w / 2, self.h / 2, self.w, self.h),
            color=backyard_night_tint
        )
        if self.entering:
            # Patch origin is measured from the top-left of backyard_map.png.
            door_x, door_top = 408, 175
            door_w, door_h = self.open_door_texture.width, self.open_door_texture.height
            arcade.draw_texture_rect(
                self.open_door_texture,
                arcade.XYWH(door_x + door_w / 2, self.h - door_top - door_h / 2, door_w, door_h),
                color=backyard_night_tint,
            )
        self.player.draw()
        for x, y, t in self.ripples:
            arcade.draw_ellipse_outline(x, y, 4 + t * 32, 2 + t * 10, (170, 196, 214, int(65 * (1 - t / .8))), 1)
        for x, y, speed in self.rain:
            arcade.draw_line(x, y, x - 2, y + 14, (182, 204, 223, 60), 1)

        if not self.dialogue.active and not self.entering and not self.picking_lock:
            if self._near_door():
                self.player.draw_interact_prompt('[E] Slip into Kitchen' if self.door_unlatched else '[E] Pick Old Kitchen Lock', offset_y=90)
            elif self._near_corridor():
                self.player.draw_interact_prompt('[E] Return Along Side Corridor', offset_y=90)

        self.use_game_camera()
        if not self.dialogue.active and not self.entering and not self.picking_lock:
            arcade.draw_text('WASD / Arrows: Walk    Shift: Sprint    E: Interact    Esc: Pause', 18, SCREEN_HEIGHT - 26, (185, 199, 212), 12)

        # Draw lock-picking mini-game overlay
        if self.picking_lock:
            self._draw_lockpick_overlay()

        self.dialogue.draw(self.aspect_ratio_correction)
        if self.entering:
            arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0, int(self.fade)))
        if self.fade_in_alpha > 0:
            arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (8, 8, 12, int(self.fade_in_alpha)))
        self.draw_pause_overlay()

    def _interact(self):
        if self._near_door():
            if self.door_unlatched:
                self.keys.clear()
                self.door_open_hold = 0.4
                self.entering = True
                self.audio.play('door_creak', volume_scale=.5)
            else:
                self.keys.clear()
                self.dialogue.start_dialogue([
                    ('Old Kitchen Door', 'The rusted service door is padlocked shut with an old brass tumbler cylinder.', COLOR_GOLD),
                    ('Chef', "\"I still have my thin boning blade with me... let's see if my hands are still steady.\"", (210, 175, 120), self.portrait_chef),
                    ('Action', 'He inserts the slender blade into the keyway...', (90, 230, 140)),
                ], on_complete=self._start_lockpick_minigame)
        elif self._near_corridor() and self.street_view:
            street = self.street_view
            street.is_transitioning = False
            street.fade_alpha = 0
            street.stage = 2
            street.key_up = street.key_down = street.key_left = street.key_right = False
            self.window.show_view(street)

    def on_key_press(self, key, modifiers):
        if self.handle_pause_key(key):
            self.keys.clear()
            return
        if self.is_paused or self.entering: return
        if key == arcade.key.F11:
            self.toggle_fullscreen()
            self._fit_camera()
            return
        if self.dialogue.active:
            if key in (arcade.key.E, arcade.key.ENTER, arcade.key.SPACE): self.dialogue.advance()
            return
        if self.picking_lock:
            if key == arcade.key.ESCAPE:
                self.picking_lock = False
                return
            if self.lock_stage == "insert":
                if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                    self.tool_inserted = True
                    self.insert_anim_t = 0.0
                    self.audio.play('paper_slide', volume_scale=0.8)
                    return
            if self.lock_stage == "tumbler":
                # SPACE / ENTER / E triggers BIND attempt on selected pin!
                if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                    self._attempt_bind_pin(self.selected_pin)
                    return
                if key in (arcade.key.A, arcade.key.LEFT):
                    if self.selected_pin > 0:
                        self.selected_pin -= 1
                        self.audio.play('lock_pick', volume_scale=0.25)
                elif key in (arcade.key.D, arcade.key.RIGHT):
                    if self.selected_pin < 3:
                        self.selected_pin += 1
                        self.audio.play('lock_pick', volume_scale=0.25)
            self.keys.add(key)
            return

        if key == arcade.key.E:
            self._interact()
        else:
            self.keys.add(key)

    def on_key_release(self, key, modifiers):
        self.keys.discard(key)

    def on_mouse_press(self, x, y, button, modifiers):
        if self.handle_pause_mouse_press(x, y, button): return
        if not self.is_paused and self.dialogue.active:
            self.dialogue.advance()
            return

        if self.picking_lock:
            # Stage 1: Tool Dragging
            if self.lock_stage == "insert":
                if button == arcade.MOUSE_BUTTON_LEFT:
                    dist_to_center = math.hypot(x - self.tool_drag_x, y - self.tool_drag_y)
                    if dist_to_center < 140:
                        self.is_dragging_tool = True
                        self.tool_drag_offset_x = self.tool_drag_x - x
                        self.tool_drag_offset_y = self.tool_drag_y - y
                    else:
                        # Grab tool by handle if clicked elsewhere
                        self.is_dragging_tool = True
                        self.tool_drag_x = x + 70.0
                        self.tool_drag_y = y + 90.0
                        self.tool_drag_offset_x = 0.0
                        self.tool_drag_offset_y = 0.0
                        self._check_tool_insertion(x, y)
                return

            # Stage 2: 4-Pin Tumbler Drag / Button Click
            if self.lock_stage == "tumbler" and not self.lock_solved:
                if button == arcade.MOUSE_BUTTON_LEFT:
                    # Check if clicked on the BIND button (center: mid_x, 66, w: 280, h: 42)
                    mid_x = SCREEN_WIDTH / 2
                    if abs(x - mid_x) <= 140 and abs(y - 66) <= 21:
                        self._attempt_bind_pin(self.selected_pin)
                        return

                    self.mouse_lifting = True
                    self.mouse_drag_start_y = y
                    self.mouse_drag_initial_lift = self.pin_lifts[self.selected_pin]

    def on_mouse_release(self, x, y, button, modifiers):
        if self.picking_lock:
            if self.lock_stage == "insert":
                self.is_dragging_tool = False
                self._check_tool_insertion(x, y)
                return

            if self.lock_stage == "tumbler":
                if button == arcade.MOUSE_BUTTON_LEFT:
                    self.mouse_lifting = False

    def on_mouse_motion(self, x, y, dx, dy):
        self.handle_pause_mouse_motion(x, y)
        if self.picking_lock:
            if self.lock_stage == "insert":
                if self.is_dragging_tool and not self.tool_inserted:
                    self.tool_drag_x = x + self.tool_drag_offset_x
                    self.tool_drag_y = y + self.tool_drag_offset_y
                    self._check_tool_insertion(x, y)
                return

            if self.lock_stage == "tumbler" and not self.lock_solved:
                # Hover to select chamber (when not dragging)
                if not self.mouse_lifting:
                    for idx, px in enumerate(self.pin_xs):
                        if abs(x - px) < 46:
                            if self.selected_pin != idx:
                                self.selected_pin = idx
                                self.audio.play('lock_pick', volume_scale=0.22)
                            break
                else:
                    # Dragging to push up / down smoothly
                    sel = self.selected_pin
                    if not self.pin_locked[sel]:
                        delta_y = y - self.mouse_drag_start_y
                        target_val = max(0.0, min(80.0, self.mouse_drag_initial_lift + delta_y * 0.55))
                        self.pin_lifts[sel] = target_val

    def _check_tool_insertion(self, x, y):
        """Check if dragged tool tip is accurately aligned with the keyway hole."""
        if self.tool_inserted: return
        mid_x = SCREEN_WIDTH / 2
        mid_y = SCREEN_HEIGHT / 2 - 8
        cx = mid_x + 184.4
        cy = mid_y - 44.6

        # Exact tip position of the pick (with tool_angle = 38.0)
        tip_x = self.tool_drag_x + 70.6
        tip_y = self.tool_drag_y + 90.4

        # Only start the game when the pick's TIP / HEAD is truly aligned with the keyhole (< 24px)
        if math.hypot(tip_x - cx, tip_y - cy) < 24.0:
            self.tool_inserted = True
            self.insert_anim_t = 0.0
            self.audio.play('lock_pick', volume_scale=0.75)
