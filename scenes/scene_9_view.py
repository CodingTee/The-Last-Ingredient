"""Scene 9: S09 Someone Else's Body
Chapter Two - The Whistle That Never Sounded (Prehistoric Era)

Flow (rebuilt on the open explore map):
1. Enter the scene directly on the open prehistoric map: fade in, the camera
   rests on the tribespeople gathered around a baby dinosaur. The body cannot
   be controlled (possession): movement keys trigger the "moves on its own" flash.
2. First-person muddy hands close-up (assets/Scene 9/First Scene.png).
3. The camera turns to the top-right corner: the possessed body walks out on
   its own and crosses the map toward the tribe.
4. Encounter: scripted dialogue (tribespeople / hunter), Chef internal
   monologue in a distinct italic cold style, closing narrator line.
5. Interactive free roam: the player can walk around briefly (WASD/arrows),
   with the baby dinosaur framed on screen. Clicking the dinosaur begins the carry.
6. Rope handoff: the group carries the baby dinosaur toward camp, fade out,
   end card teasing S10. The village itself lives in scenes/scene_10_view.py
   (run_scene_10.py); the handoff into it is not wired yet (2026-10-25).

Game-facing strings stay ENGLISH per project directive.
"""
import math
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import arcade
from arcade.types.rect import LRBT

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD, SOUNDS_DIR
from core.dialogue import DialogueBox
from core.audio import AudioManager
from core.player import Player, FEET_OFFSET

from scenes.prehistoric_explore_view import (
    PrehistoricExploreView,
    WORLD_WIDTH, WORLD_HEIGHT, CAMP_X, CAMP_Y,
)

# ---- Story Phases (state machine) -------------------------------------------
PHASE_MAP = 0        # open map, uncontrollable, narration captions
PHASE_HANDS = 1      # first-person muddy-hands close-up
PHASE_APPROACH = 2   # body walks out of the top-right corner, on its own
PHASE_ENCOUNTER = 3  # dialogue segment A around the baby dinosaur
PHASE_MONOLOGUE = 4  # Chef internal monologue (italic cold style)
PHASE_CLOSING = 5    # closing narrator line (segment B)
PHASE_CARRY = 6      # rope handoff, carry the dino toward camp
PHASE_END = 7        # end card -> S10 placeholder (S10 not built)
PHASE_FREE = 8       # interactive: brief player-controlled roam, click dino to carry

# ---- Cast theme colors ------------------------------------------------------
COLOR_SAVAGE = (230, 140, 80)
COLOR_TRIBE = (205, 175, 135)
COLOR_CHEF_INTERNAL = (180, 205, 240)
COLOR_NARRATOR = (210, 215, 225)

# ---- World layout (world coords, 2600x1600 map) -----------------------------
DINO_X = WORLD_WIDTH * 0.26
DINO_Y = WORLD_HEIGHT * 0.30
TRIBE_SPOTS = [(-190, 128), (-150, -60), (140, 70)]
TRIBE_IDS = ["tribe_a", "tribe_b", "tribe_c"]
HUNTER_START = (WORLD_WIDTH - 240.0, WORLD_HEIGHT - 220.0)
# Arrive due south of the dino, well clear of the standing-stone ring
# (which sits ~360px from camp centre) and inside the dino's 320px clear
# zone, so the scripted walk can actually reach it.
APPROACH_TARGET = (DINO_X, DINO_Y + 200.0)

# Switch: S10+ must check this so the fixed-memory message never re-pops.
SHOW_MEMORY_MESSAGE_ONCE = True

# First-person awakening close-up art (rough muddy hands).
HANDS_IMAGE = ROOT_DIR / "assets" / "Scene 9" / "First Scene.png"
# Same juvenile art as Scene 11 so S09-S11 show one continuous creature.
DINO_IMAGE = ROOT_DIR / "assets" / "Scene 9" / "Juvenile Dino.png"
# The 1536x1024 art carries empty canvas below the body (rows 825..1024).
DINO_EMPTY_BOTTOM_FRAC = (1024 - 825) / 1024.0
# Carry fade is driven by remaining distance, so the group still walks at black.
CARRY_FADE_START_DIST = 560.0
CARRY_FADE_END_DIST = 120.0


class Scene9View(PrehistoricExploreView):
    """Scene 9: possession awakening staged on the open prehistoric map."""

    def __init__(self):
        super().__init__()
        self.audio = AudioManager()
        self.phase = PHASE_MAP
        self.phase_timer = 0.0
        self.fade_alpha = 255

        # The possessed hunter starts at the map's top-right corner.
        # place() syncs the sprite immediately so it does not linger at the
        # explore spawn (which sits right on the dino scene the camera opens on).
        self.player.place(*HUNTER_START)

        # Tribespeople NPCs around the baby dinosaur.
        self.tribespeople = []
        for (dx, dy), cid in zip(TRIBE_SPOTS, TRIBE_IDS):
            self.tribespeople.append(Player(DINO_X + dx, DINO_Y + dy, char_id=cid))

        # Baby dinosaur position (lying on the ground).
        self.dino_x, self.dino_y = DINO_X, DINO_Y
        self._dino_tex = None

        # Possession: movement keys are ignored.
        self.ignored_flash = 0.0

        # One-time fixed-memory player message.
        self.player_msg_alpha = 0
        self.player_msg_shown = False
        self.player_msg_timer = 0.0

        # Internal monologue state.
        self.mono_alpha = 0
        self.mono_timer = 0.0

        # Dialogue + script.
        self.dialogue = DialogueBox()
        self._setup_script()

        # Lazy text objects.
        self._text = {}

        # Dedicated UI camera (virtual 1280x720) so overlays never disturb
        # the world-follow camera position.
        self.ui_camera = None

        # Carry state (defensive init; also set in _enter_carry).
        self._carry_attached = False

        # Ambience handle.
        self._amb_player = None

        # Opening narration captions: (start_time, text)
        self.map_captions = [
            (0.9, "He opens his eyes. Green light. A jungle that is not his time."),
            (3.5, "This is not his body. It does not answer to him."),
        ]

    def _setup_script(self):
        # Segment A: narrator / tribesperson / narrator / hunter / tribesperson
        self.script_a = [
            (
                "Tribesperson",
                "\"Come and help! We won't be going home empty-handed today.\"",
                COLOR_TRIBE,
            ),
            (
                "Hunter",
                "\"Is it still breathing?\"",
                COLOR_SAVAGE,
            ),
            (
                "Tribesperson",
                "\"No.\"",
                COLOR_TRIBE,
            ),
        ]
        # Beat 6: Chef internal monologue (distinct overlay, not the dialogue box)
        self.monologue_text = "\"That isn't my voice...\""
        # Segment B: closing narrator
        self.script_b = [
            (
                "",
                "The hunter's body continues moving forward.",
                COLOR_NARRATOR,
            ),
        ]

    # ===================================================================
    # VIEW LIFECYCLE
    # ===================================================================
    def on_show_view(self):
        super().on_show_view()
        path = SOUNDS_DIR / "forest_ambience.wav"
        if path.exists():
            try:
                snd = arcade.load_sound(str(path))
                self._amb_player = snd.play(loop=True, volume=0.5)
            except Exception:
                self._amb_player = None

    # ===================================================================
    # PHASE TRANSITIONS
    # ===================================================================
    def _enter_hands(self):
        self.phase = PHASE_HANDS
        self.phase_timer = 0.0
        self.fade_alpha = 255  # hands fade in from black

    def _enter_approach(self):
        self.phase = PHASE_APPROACH
        self.phase_timer = 0.0
        self.fade_alpha = 255  # fade back into the map

    def _enter_encounter(self):
        self.phase = PHASE_ENCOUNTER
        self.phase_timer = 0.0
        self.dialogue.start_dialogue(self.script_a, on_complete=self._on_script_a_done)
        if SHOW_MEMORY_MESSAGE_ONCE and not self.player_msg_shown:
            self.player_msg_alpha = 255
            self.player_msg_shown = True
            self.player_msg_timer = 3.5

    def _on_script_a_done(self):
        self.phase = PHASE_MONOLOGUE
        self.phase_timer = 0.0
        self.mono_alpha = 255
        self.mono_timer = 3.4

    def _enter_closing(self):
        self.phase = PHASE_CLOSING
        self.phase_timer = 0.0
        self.dialogue.start_dialogue(self.script_b, on_complete=self._enter_free)

    def _enter_free(self):
        self.phase = PHASE_FREE
        self.phase_timer = 0.0
        self.held_keys.clear()

    def _enter_carry(self):
        self.phase = PHASE_CARRY
        self.phase_timer = 0.0
        self._carry_attached = False
        self.fade_alpha = 0.0

    def _enter_end(self):
        self.phase = PHASE_END
        self.phase_timer = 0.0

    # ===================================================================
    # CAMERA (narrative focus instead of free follow)
    # ===================================================================
    def _camera_focus(self):
        if self.phase in (PHASE_MAP, PHASE_HANDS):
            # Rest on the tribe group with a slow breathing drift.
            return (DINO_X - 60 + math.sin(self.t * 0.3) * 30,
                    DINO_Y - 30 + math.cos(self.t * 0.22) * 20)
        if self.phase == PHASE_APPROACH:
            return (self.player.x, self.player.y)
        if self.phase == PHASE_FREE:
            # Free roam: the camera follows the player so they can wander
            # anywhere on the map. The dino is guided by the edge arrow.
            return (self.player.x, self.player.y)
        if self.phase in (PHASE_ENCOUNTER, PHASE_MONOLOGUE, PHASE_CLOSING):
            mx = (self.player.x + self.dino_x) / 2
            my = (self.player.y + self.dino_y) / 2
            return (mx, my)
        return (self.player.x, self.player.y)  # carry / end

    def _follow_camera(self, dt=0.05):
        if not self.camera:
            return
        fx, fy = self._camera_focus()
        half_w, half_h = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        tx = max(half_w, min(WORLD_WIDTH - half_w, fx))
        ty = max(half_h, min(WORLD_HEIGHT - half_h, fy))
        cx, cy = self.camera.position
        k = min(1.0, dt * 2.6)
        self.camera.position = (cx + (tx - cx) * k, cy + (ty - cy) * k)

    # ===================================================================
    # UPDATE
    # ===================================================================
    def on_update(self, dt):
        if self.is_paused:
            return
        self.t += dt
        self.phase_timer += dt
        if self.ignored_flash > 0:
            self.ignored_flash -= dt

        # One-time memory message fade: runs in EVERY phase so a phase
        # transition can never freeze it at partial alpha.
        if self.player_msg_timer > 0:
            self.player_msg_timer -= dt
        elif self.player_msg_alpha > 0:
            self.player_msg_alpha = max(0, self.player_msg_alpha - dt * 180)

        for d in self.dust[:]:
            d.update(dt)
            if d.life <= 0:
                self.dust.remove(d)
        for e in self.embers:
            e.update(dt)
        for s in self.smoke:
            s.update(dt)
        for m in self.motes:
            m.update(dt, self.t)

        self._follow_camera(dt)

        if self.phase == PHASE_MAP:
            self.fade_alpha = max(0, self.fade_alpha - dt * 210)
            if self.phase_timer >= 6.0:
                self._enter_hands()

        elif self.phase == PHASE_HANDS:
            self.fade_alpha = max(0, self.fade_alpha - dt * 420)
            if self.phase_timer >= 3.4:
                self._enter_approach()

        elif self.phase == PHASE_APPROACH:
            self.fade_alpha = max(0, self.fade_alpha - dt * 320)
            dx = APPROACH_TARGET[0] - self.player.x
            dy = APPROACH_TARGET[1] - self.player.y
            dist = math.hypot(dx, dy)
            if dist > 10:
                self.player.update(dt, dx / dist, dy / dist,
                                   dust_particles=self.dust,
                                   bounds=(160, WORLD_WIDTH - 160, 200, WORLD_HEIGHT - 200))
            else:
                self.player.update(dt, 0, 0, dust_particles=self.dust,
                                   bounds=(160, WORLD_WIDTH - 160, 200, WORLD_HEIGHT - 200))
                self._enter_encounter()
                return
            # Keep the body out of prop / standing-stone bases even on the
            # scripted walk, so it slides around (never through) the ring.
            self._resolve_collisions()

        elif self.phase == PHASE_ENCOUNTER:
            self._idle_cast(dt)
            self.dialogue.update(dt)

        elif self.phase == PHASE_MONOLOGUE:
            self._idle_cast(dt)
            if self.mono_timer > 0:
                self.mono_timer -= dt
            elif self.mono_alpha > 0:
                self.mono_alpha = max(0, self.mono_alpha - dt * 200)
            if self.mono_alpha <= 0 and self.mono_timer <= 0:
                self._enter_closing()

        elif self.phase == PHASE_CLOSING:
            self._idle_cast(dt)
            self.dialogue.update(dt)

        elif self.phase == PHASE_FREE:
            self._free_roam(dt)

        elif self.phase == PHASE_CARRY:
            self._carry(dt)

        elif self.phase == PHASE_END:
            # End card only: the S10 village scene is split out as its own
            # scene (scenes/scene_10_view.py, run_scene_10.py) and is NOT
            # wired into this ending yet (user call, 2026-10-25). SPACE /
            # ENTER on the card still returns to the menu.
            self.fade_alpha = min(255, self.fade_alpha + dt * 160)

    def _idle_cast(self, dt):
        """Everyone stands still (idle frame) during dialogue beats."""
        bounds = (160, WORLD_WIDTH - 160, 200, WORLD_HEIGHT - 200)
        self.player.update(dt, 0, 0, dust_particles=self.dust, bounds=bounds)
        for tp in self.tribespeople:
            tp.update(dt, 0, 0, bounds=bounds)

    def _free_roam(self, dt):
        """Brief player-controlled exploration before the carry begins."""
        bounds = (160, WORLD_WIDTH - 160, 200, WORLD_HEIGHT - 200)
        hk = self.held_keys
        move_x, move_y = 0.0, 0.0
        if arcade.key.W in hk or arcade.key.UP in hk:
            move_y += 1.0
        if arcade.key.S in hk or arcade.key.DOWN in hk:
            move_y -= 1.0
        if arcade.key.A in hk or arcade.key.LEFT in hk:
            move_x -= 1.0
        if arcade.key.D in hk or arcade.key.RIGHT in hk:
            move_x += 1.0
        self.player.update(dt, move_x, move_y, dust_particles=self.dust, bounds=bounds)
        self._resolve_collisions()
        for tp in self.tribespeople:
            tp.update(dt, 0, 0, bounds=bounds)

    def _carry_fade(self, dist):
        """Darken by remaining distance; full black lands before the camp."""
        span = CARRY_FADE_START_DIST - CARRY_FADE_END_DIST
        p = (CARRY_FADE_START_DIST - dist) / span
        self.fade_alpha = 255.0 * max(0.0, min(1.0, p))

    def _carry(self, dt):
        """Walk to the baby dinosaur, then haul it (and the tribe) to camp."""
        bounds = (160, WORLD_WIDTH - 160, 200, WORLD_HEIGHT - 200)
        # Brief rope-handoff pause once attached.
        if self._carry_attached and self.phase_timer < 0.9:
            self._idle_cast(dt)
            return
        # Sub-step 1: reach the dinosaur if the player roamed away during free roam.
        if not self._carry_attached:
            dx = self.dino_x - self.player.x
            dy = self.dino_y - self.player.y
            dist = math.hypot(dx, dy)
            if dist > 50:
                ux, uy = dx / dist, dy / dist
                self.player.update(dt, ux, uy, dust_particles=self.dust, bounds=bounds)
                for tp in self.tribespeople:
                    tp.update(dt, ux, uy, bounds=bounds)
                return
            self._carry_attached = True
        # Sub-step 2: haul everything toward the camp hearth.
        dx = CAMP_X - self.player.x
        dy = CAMP_Y - self.player.y
        dist = math.hypot(dx, dy)
        self._carry_fade(dist)
        if self.fade_alpha >= 255 or self.phase_timer >= 16.0:
            self.fade_alpha = 255
            from scenes.scene_11_view import Scene11View
            self.window.show_view(Scene11View())
            return
        ux, uy = dx / dist, dy / dist
        speed = 170.0
        self.player.update(dt, ux, uy, dust_particles=self.dust, bounds=bounds)
        for tp in self.tribespeople:
            tp.update(dt, ux, uy, bounds=bounds)
        self.dino_x += ux * speed * dt
        self.dino_y += uy * speed * dt

    # ===================================================================
    # INPUT
    # ===================================================================
    def on_key_press(self, key, modifiers):
        if self.handle_pause_key(key):
            return
        # Free-roam: real WASD/arrow control, keys feed the held-keys set.
        if self.phase == PHASE_FREE:
            if key in (arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D,
                       arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT,
                       arcade.key.LSHIFT, arcade.key.RSHIFT):
                self.held_keys.add(key)
            return
        # Possession mechanic: movement keys are ignored; the body moves alone.
        if self.phase in (PHASE_MAP, PHASE_HANDS, PHASE_APPROACH) and key in (
            arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D,
            arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT,
        ):
            self.ignored_flash = 0.6
            return
        if self.dialogue.active and key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
            self.dialogue.advance()
            return
        if self.phase == PHASE_END and key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
            from scenes.scene_11_view import Scene11View
            self.window.show_view(Scene11View())

    def on_mouse_press(self, x, y, button, modifiers):
        if self.handle_pause_mouse_press(x, y, button):
            return
        if self.phase == PHASE_FREE:
            self._try_start_carry(x, y)
            return
        if self.dialogue.active:
            self.dialogue.advance()
            return
        if self.phase == PHASE_END:
            from scenes.scene_11_view import Scene11View
            self.window.show_view(Scene11View())
            return

    def on_mouse_motion(self, x, y, dx=0, dy=0):
        self.handle_pause_mouse_motion(x, y)

    def on_key_release(self, key, modifiers):
        if key in (arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D,
                   arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT,
                   arcade.key.LSHIFT, arcade.key.RSHIFT):
            self.held_keys.discard(key)

    # ===================================================================
    # DRAW
    # ===================================================================
    def on_draw(self):
        self.clear(color=(24, 34, 24))
        self._ensure_ground()
        self.use_game_camera()

        # Ground
        self._ground_list.draw()
        # Pond sprite over the baked pond (Scene9View overrides the parent
        # on_draw, so the parent's pond draw never ran for this scene).
        self._draw_pond()

        # Depth-sorted props, tribespeople, dino and the possessed hunter.
        items = []
        for tr in self.trees:
            items.append((tr["y"], lambda tr=tr: self._draw_tree(tr)))
        for rk in self.rocks:
            items.append((rk["y"], lambda rk=rk: self._draw_rock(rk)))
        for fn in self.ferns:
            items.append((fn["y"], lambda fn=fn: self._draw_fern(fn)))
        for mh in self.mushrooms:
            items.append((mh["y"], lambda mh=mh: self._draw_mushroom(mh)))
        for st in self.stones:
            items.append((st["y"], lambda st=st: self._draw_stone(st)))
        items.append((CAMP_Y, self._draw_camp))
        items.append((self.dino_y, self._draw_dino))
        for tp in self.tribespeople:
            # NPCs sort by their foot (lowest point) to match the decor bases.
            items.append((tp.y - FEET_OFFSET, lambda tp=tp: tp.draw(self.aspect_ratio_correction)))
        items.append((self.player.y - FEET_OFFSET, self._draw_player_with_dust))
        # Lower base y = nearer to the camera = drawn last (on top).
        items.sort(key=lambda it: it[0], reverse=True)
        for _, fn in items:
            fn()

        # Embers + smoke above the hearth (world coords).
        for s in self.smoke:
            s.draw()
        for e in self.embers:
            e.draw()

        # Interactive prompt ring around the click target during free roam.
        if self.phase == PHASE_FREE:
            self._draw_dino_marker()

        # Atmosphere in screen space.
        self.window.default_camera.use()
        self._draw_god_rays()
        self._draw_motes()

        # ---- UI / narrative layers (virtual 1280x720 coords) ----
        self._use_ui_camera()

        if self.phase == PHASE_MAP:
            self._draw_map_captions()

        if self.player_msg_shown and self.player_msg_alpha > 0:
            self._draw_player_message()

        if self.phase == PHASE_HANDS:
            self._draw_hands_closeup()

        if self.phase in (PHASE_ENCOUNTER, PHASE_CLOSING):
            self.dialogue.draw(self.aspect_ratio_correction)

        if self.mono_alpha > 0:
            self._draw_monologue()

        if self.phase == PHASE_CARRY:
            self._draw_rope()

        if self.phase == PHASE_FREE:
            self._draw_free_hint()
            self._draw_dino_offscreen_arrow()

        if self.ignored_flash > 0:
            self._draw_ignored_flash()

        # Black overlay (fades / cuts)
        if self.fade_alpha > 0:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (0, 0, 0, int(self.fade_alpha)),
            )

        self.draw_pause_overlay()

    def _use_ui_camera(self):
        """Activate a fixed virtual-resolution camera for UI/narrative overlays."""
        if self.ui_camera is None:
            self.ui_camera = arcade.camera.Camera2D(window=self.window)
        self.ui_camera.viewport = LRBT(0, self.window.width, 0, self.window.height)
        self.ui_camera.projection = LRBT(-SCREEN_WIDTH / 2, SCREEN_WIDTH / 2,
                                         -SCREEN_HEIGHT / 2, SCREEN_HEIGHT / 2)
        self.ui_camera.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        self.ui_camera.use()

    def _draw_player_with_dust(self):
        for d in self.dust:
            d.draw()
        self.player.draw(self.aspect_ratio_correction)

    # ---- Baby dinosaur -----------------------------------------------------
    def _dino_texture(self):
        if self._dino_tex is None:
            self._dino_tex = arcade.load_texture(str(DINO_IMAGE))
        return self._dino_tex

    def _dino_geom(self, tex):
        """Width, height and centre with the bottom blank rows dropped."""
        w = 190 * self.aspect_ratio_correction
        h = w * (tex.height / tex.width)
        lift = h * DINO_EMPTY_BOTTOM_FRAC
        return w, h, self.dino_x, self.dino_y - 6 + h / 2 - lift

    def _draw_dino_marker(self):
        """Pulsing ring + bobbing chevron so the click target is findable."""
        tex = self._dino_texture()
        w, h, cx, cy = self._dino_geom(tex)
        pulse = 0.5 + 0.5 * math.sin(self.t * 4.0)
        r = max(w, h) * 0.5 + 16 + 6 * pulse
        arcade.draw_circle_outline(cx, cy, r, (255, 225, 120, int(120 + 110 * pulse)), 4)
        by = cy - r - 14 - 6 * math.sin(self.t * 4.0)
        arcade.draw_polygon_filled(
            [(cx - 11, by + 14), (cx + 11, by + 14), (cx, by)],
            (255, 225, 120, 220),
        )

    def _draw_free_hint(self):
        w, h = 920, 56
        cx, cy = SCREEN_WIDTH / 2, 72
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, w, h), (10, 16, 10, int(200 * 0.9)))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, w, h), (255, 225, 120, 220), 2)
        self._text_obj(
            "free_hint",
            "Free roam:  [ W A S D / Arrows ]  move    -    click the baby dinosaur to begin the carry",
            15, (255, 245, 225, 240), bold=True,
        )
        self._text["free_hint"].x = cx
        self._text["free_hint"].y = cy
        self._text["free_hint"].draw()

    def _draw_dino_offscreen_arrow(self):
        """During free roam, if the baby dinosaur leaves the view, pin a small
        pulsing arrow to the screen edge that always points back to it."""
        if not self.camera:
            return
        cx, cy = self.camera.position
        half_w, half_h = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        # Inset so the arrow sits just inside the frame edge.
        rx, ry = half_w - 54, half_h - 54
        ddx = self.dino_x - cx
        ddy = self.dino_y - cy
        # On-screen (with margin): the pulsing ring already guides the click.
        if abs(ddx) <= rx and abs(ddy) <= ry:
            return
        if ddx == 0 and ddy == 0:
            return
        sx = rx / abs(ddx) if ddx != 0 else float("inf")
        sy = ry / abs(ddy) if ddy != 0 else float("inf")
        s = min(sx, sy)
        px = SCREEN_WIDTH / 2 + ddx * s
        py = SCREEN_HEIGHT / 2 + ddy * s
        ang = math.atan2(ddy, ddx)
        pulse = 0.6 + 0.4 * math.sin(self.t * 6.0)
        alpha = int(210 * pulse) + 35
        color = (255, 225, 120, alpha)
        cos_a, sin_a = math.cos(ang), math.sin(ang)

        def rot(dx, dy):
            return (px + dx * cos_a - dy * sin_a, py + dx * sin_a + dy * cos_a)

        tip = 24
        back = -16
        wing = 14
        p1 = rot(tip, 0)        # arrow tip (outward, toward the dino)
        p2 = rot(back, wing)    # tail left
        p3 = rot(back, -wing)   # tail right
        arcade.draw_polygon_filled([p1, p2, p3], color)
        arcade.draw_circle_filled(p1[0], p1[1], 3.5, (255, 248, 210, alpha))

    def _try_start_carry(self, x, y):
        """Click hit-test: convert the click to world space and test the dino."""
        res = self.camera.unproject((x, y))
        wx, wy = res[0], res[1]
        tex = self._dino_texture()
        w, h, cx, cy = self._dino_geom(tex)
        pad_w, pad_h = w * 0.5 * 1.6, h * 0.5 * 1.6
        if abs(wx - cx) <= pad_w and abs(wy - cy) <= pad_h:
            self._enter_carry()

    def _draw_dino(self):
        tex = self._dino_texture()
        w, h, cx, cy = self._dino_geom(tex)
        # Contact shadow from sprite geometry; lift puts the body bottom at y - 6.
        sh = h * 0.17
        arcade.draw_ellipse_filled(cx, self.dino_y - 6 - sh * 0.10,
                                   w * 0.86, sh, (18, 32, 18, 110))
        arcade.draw_texture_rect(tex, arcade.XYWH(cx, cy, w, h))

    # ---- Opening narration captions ----------------------------------------
    def _draw_map_captions(self):
        for i, (t0, text) in enumerate(self.map_captions):
            ta = self.phase_timer - t0
            if ta < 0 or ta > 2.6:
                continue
            if ta < 0.4:
                a = int(255 * (ta / 0.4))
            elif ta > 2.1:
                a = int(255 * ((2.6 - ta) / 0.5))
            else:
                a = 255
            self._draw_caption(f"cap_{i}", text, a)

    def _draw_caption(self, key, text, alpha):
        cx, cy = SCREEN_WIDTH / 2, 150
        arcade.draw_rect_filled(
            arcade.XYWH(cx, cy, SCREEN_WIDTH, 74), (8, 12, 10, int(alpha * 0.55)))
        self._text_obj(key, text, 17, (235, 240, 230, alpha), bold=True)
        obj = self._text[key]
        obj.x = cx
        obj.y = cy
        obj.draw()

    # ---- First-person muddy-hands close-up ---------------------------------
    def _hands_texture(self):
        if not hasattr(self, "_hands_tex"):
            self._hands_tex = arcade.load_texture(str(HANDS_IMAGE))
        return self._hands_tex

    def _draw_hands_closeup(self):
        arcade.draw_rect_filled(
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
            (10, 8, 7, 255),
        )
        tex = self._hands_texture()
        progress = min(1.0, self.phase_timer / 3.4)
        zoom = 1.04 + progress * 0.06 + 0.008 * math.sin(self.t * 1.6)
        scale = max(SCREEN_WIDTH / tex.width, SCREEN_HEIGHT / tex.height) * zoom
        w, h = tex.width * scale, tex.height * scale
        arcade.draw_texture_rect(
            tex,
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, w, h),
        )
        for i in range(0, 120, 6):
            a = int(170 * (1 - i / 120))
            arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, i, SCREEN_WIDTH, 6), (0, 0, 0, a))
            arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT - i, SCREEN_WIDTH, 6), (0, 0, 0, a))
            arcade.draw_rect_filled(arcade.XYWH(i, SCREEN_HEIGHT / 2, 6, SCREEN_HEIGHT), (0, 0, 0, a))
            arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH - i, SCREEN_HEIGHT / 2, 6, SCREEN_HEIGHT), (0, 0, 0, a))

    # ---- One-time player message -------------------------------------------
    def _draw_player_message(self):
        a = int(self.player_msg_alpha)
        w, h = 800, 70
        cx, cy = SCREEN_WIDTH / 2, 250
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, w, h), (10, 12, 18, int(a * 0.9)))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, w, h), (COLOR_GOLD[0], COLOR_GOLD[1], COLOR_GOLD[2], a), 2)
        self._text_obj("player_msg", "You are experiencing a memory that has already happened.", 16,
                       (255, 250, 235, a), bold=True)
        self._text["player_msg"].x = cx
        self._text["player_msg"].y = cy
        self._text["player_msg"].draw()

    # ---- Internal monologue --------------------------------------------------
    def _draw_monologue(self):
        a = int(self.mono_alpha)
        cx = SCREEN_WIDTH / 2
        cy = 200
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, SCREEN_WIDTH, 90), (6, 10, 18, int(a * 0.55)))
        self._text_obj("mono", self.monologue_text, 22,
                       (COLOR_CHEF_INTERNAL[0], COLOR_CHEF_INTERNAL[1], COLOR_CHEF_INTERNAL[2], a),
                       italic=True)
        self._text["mono"].x = cx
        self._text["mono"].y = cy
        self._text["mono"].draw()

    # ---- Rope during carry ----------------------------------------------------
    def _draw_rope(self):
        hx, hy = self.player.x, self.player.y
        arcade.draw_line(hx - 18, hy - 20, self.dino_x + 60, self.dino_y,
                         (180, 150, 90, 220), 3)

    # ---- Ignored-input flash ---------------------------------------------------
    def _draw_ignored_flash(self):
        a = int(220 * (self.ignored_flash / 0.6))
        self._text_obj("ignored", "[ Your body moves on its own ]", 14, (255, 120, 110, a), bold=True)
        self._text["ignored"].x = SCREEN_WIDTH / 2
        self._text["ignored"].y = 110
        self._text["ignored"].draw()

    # ---- Lazy Text object factory ---------------------------------------------
    def _text_obj(self, key, text, size, color, bold=False, italic=False):
        if key not in self._text:
            self._text[key] = arcade.Text(
                text, 0, 0,
                color=color,
                font_name=("Segoe UI", "Calibri", "Arial"),
                font_size=size, bold=bold, italic=italic,
                anchor_x="center", anchor_y="center",
            )
        else:
            obj = self._text[key]
            obj.text = text
            obj.color = color
            obj.font_size = size
            obj.bold = bold
            obj.italic = italic
        return self._text[key]
