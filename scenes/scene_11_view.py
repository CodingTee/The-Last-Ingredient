"""Scene 11 (S11) The Village: the tribe's home the baby dinosaur is carried to.

Same skeleton as prehistoric_explore_view (free WASD roam, follow camera,
2.5D depth sorting, hearth fire with embers/smoke, god rays, motes) but the map
is the village clearing instead of the hunting forest.

Split out of the scene-9 handoff on 2026-10-25: scene 9 no longer jumps here
at its end card, so this scene is entered on its own (run_scene_10.py) until
the story wiring is ready.

Split of assets (this matters for occlusion):
  * village_ground.png is partly AI paint and partly procedural. The ring of
    forest around the village is the AI render; every hard-edged thing inside
    the palisade was baked procedurally at 1 world px == 1 image px by
    tools/rebake_village.py, so the plaza rim, spokes, hut pads, palisade
    posts, tower mounds and the fire ring stay crisp at any view scale.
  * huts / watchtowers / gateway / meat-drying racks / fences are runtime sprites
    with world anchors, sorted by base y like every other prop.

Everything was measured off the baked ground, not guessed: the hut sites are
the separate trodden pads, the two watchtower platforms are the earth mounds
either side of the south gate, and the palisade collision ellipse sits just
inside the painted post line so nobody walks through the logs. The hearth is
the centre of a large empty plaza, so there is room to walk all the way around
the fire instead of the fire being the centre of the map.
"""
import math
import numpy as np
import random
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import arcade
from arcade.types.rect import LRBT

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, CHARACTERS_DIR, COLOR_GOLD
from core.player import Player, FEET_OFFSET
from core.base_view import BaseGameView
from core.prehistoric_meal import RoastMeal
from scenes.prehistoric_explore_view import (
    EmberParticle, SmokeParticle, PollenMote,
)

# ---- World dimensions (matches the baked ground texture) ------------------
WORLD_WIDTH = 4000.0
WORLD_HEIGHT = 2600.0
VILLAGE_DIR = ROOT_DIR / "assets" / "prehistoric" / "village"
# 16-bit pixel style (2026-10-28): the ground is baked at 1000x650 and scaled
# x4, so every sprite here is stored pre-upscaled at exactly the size the scene
# draws it at. Mixing painted art on top of it looked wrong.
PIXEL_DIR = VILLAGE_DIR / "pixel"
# Characters keep their original painted art (not pixelised): they are the
# focal point, so they stay crisp while the map and props are the pixel layer.
CHARS_DIR = CHARACTERS_DIR
# Smaller than the 0.22 canonical scale: at 0.22 the figures read as too big
# against the chunky pixel huts, so the village uses a reduced factor.
CHAR_SCALE = 0.15
GROUND_PATH = VILLAGE_DIR / "village_ground.png"
# Script-accurate: the juvenile dinosaur is the tribe's KILL (scene S09/S10),
# not a pet. Art is the dead juvenile, lying on its side.
DINO_IMAGE = ROOT_DIR / "assets" / "Scene 9" / "Juvenile Dino.png"
# The art is 1536x1024 but the body occupies image rows 216..825: the rows below
# the corpse are empty canvas, so aligning the sprite's bottom edge to the base
# point would float it. This fraction of the height is skipped.
DINO_EMPTY_BOTTOM_FRAC = (1024 - 825) / 1024.0

# Animated painted campfire (41 frames @10fps) extracted from the artist's
# campfire.gif by tools/make_campfire_frames.py. Mirrors prehistoric_explore_view so
# the village hearth uses the same fire as the forest camp.
CAMPFIRE_DIR = ROOT_DIR / "assets" / "prehistoric" / "campfire_frames"
CAMPFIRE_WORLD_WIDTH = 135.0    # smaller hearth; 240x322 art
CAMPFIRE_BASE_LIFT = 20.0       # ground row of the art sits this far above HEARTH_Y (smaller hearth)
CAMPFIRE_FPS = 10.0             # the GIF's own frame rate
# Roasting spit that stands over the hearth.
GRILL_PATH = ROOT_DIR / "assets" / "prehistoric" / "cooking_v2" / "spit.png"
GRILL_WORLD_WIDTH = 173.8       # a touch wider than the hearth so the forked feet straddle it
GRILL_FEET_OFFSET = 12.0        # world px the spit feet sit above the log line (tuned vs frame_00)
VILLAGE_DIR
SPRITE_PATHS = {
    # Reverted to the painted (smooth) originals on 2026-11-01: the pixel pass
    # (2026-10-28) had downsampled these to chunky pixels. User wants the normal
    # painted look back. The scene scales by width/tex.width, so the on-screen
    # size is unchanged; only the style differs. hut3/hut4 are flipped twins.
    "hut": VILLAGE_DIR / "hut.png",
    "hut2": VILLAGE_DIR / "hut2.png",
    "hut3": VILLAGE_DIR / "hut3.png",
    "hut4": VILLAGE_DIR / "hut4.png",
    "totem": VILLAGE_DIR / "totem.png",
    "rack": VILLAGE_DIR / "rack.png",
    # Still pixel: not part of this revert (user scoped totem / rack / grass huts).
    "fence": PIXEL_DIR / "fence.png",
    "watchtower": PIXEL_DIR / "watchtower.png",
    "watchtower_guard_a": PIXEL_DIR / "watchtower_guard_a_v2.png",
    "watchtower_guard_b": PIXEL_DIR / "watchtower_guard_b_v2.png",
    "watchtower_overlay": PIXEL_DIR / "watchtower_overlay.png",
    "gate": PIXEL_DIR / "gate.png",
    "woodpile": PIXEL_DIR / "woodpile.png",
}

# Hearth = the centre of the plaza, where the baked stone ring is. The plaza
# reaches 340 units in every direction from here, so there is room to walk all
# the way round the fire: only the stone ring itself blocks.
HEARTH_X, HEARTH_Y = 2000.0, 1250.0
# Unified hearth collision ellipse: tightly encloses the outer stone ring,
# logs, and spit legs. Stops player from stepping onto any stone below (y=1253)
# and seals off empty space above the spit/fire (y=1383).
HEARTH_COLLISION_X = 2000.0
HEARTH_COLLISION_Y = 1318.0
HEARTH_COLLISION_RX = 95.0
HEARTH_COLLISION_RY = 65.0
HEARTH_DEPTH_Y = 1318.0

# The palisade posts are painted with their bases on an ellipse of
# 1250 x 980 (tools/rebake_village.py, user: not a rigid circle). Walkable area
# is clamped tighter so the player never stands on the logs.
PALISADE_CENTRE = (2000.0, 1330.0)
PALISADE_RX, PALISADE_RY = 1192.0, 922.0

# The juvenile rests beside the cooking area, east of the fire and spit.
# Leave a clear approach to both the wound inspection and the BBQ station.
DINO_SPOT = (2260.0, 1315.0)

# Dinosaur collision: an ellipse hugging the resting body so the floor in front
# of (south of) the dino stays walkable. The art is ~206w x 83h world units and
# its bottom edge (feet) sits on DINO_SPOT[1]+6. Keep the ellipse BOTTOM on the
# feet (1321) so the ground below stays open, but push the TOP a little past the
# head (1404) to ~1422 so the player is shoved clear of the back instead of being
# pinned on it. rx adds FOOT_RADIUS so the flanks do not overlap the player body.
DINO_COLLISION_CX = DINO_SPOT[0]
DINO_COLLISION_CY = 1371.5                      # (top 1422 + bottom 1321) / 2
DINO_COLLISION_RX = 103.0 + 42.0                # half body width + FOOT_RADIUS
DINO_COLLISION_RY = 50.5                        # (1422 - 1321) / 2; bottom == feet, top clears head

# Enter cooking beside the spit over the hearth, outside its collision ring.
BBQ_ZONE_R = 170.0


# Watchtowers. Their bases are the two earth mounds baked INSIDE the entrance,
# flanking the approach (tools/rebake_village.py MOUND_DX / MOUND_Y). The gate
# arch sits further south, in the fence gap, so it is not wedged between them.
WATCHTOWER_WIDTH = 204.0
WATCHTOWER_BASES = ((1700.0, 580.0), (2300.0, 580.0))

# Sentries stand inside the upper platform, behind its roof and front railing.
WATCHTOWER_HEIGHT = WATCHTOWER_WIDTH * 503.0 / 405.0     # source art aspect
SENTRY_LIFT = WATCHTOWER_HEIGHT - 166.0
SENTRY_X_OFFSET = 24.0
SENTRY_HEIGHT = 110.0     # Preserve the original full guard size; tower layers occlude it.
SENTRY_CHARS = ("tribe_guard_a", "tribe_guard_b")   # distinct guards, not villagers

# Prop layout: (kind, x, y, width_in_world_px[, modifiers...]).
# width_in_world_px: on-screen WIDTH of the prop in world pixels. A number is an
#   absolute size pinned to the baked ground (hut 280 vs the 276px trodden pad;
#   tower/gate/woodpile are 1:1 with their art). None means "use
#   PROP_HEIGHT[kind] as the HEIGHT instead".
# Trailing modifiers, type-driven and order-free:
#   number -> size multiplier on top of that base size (1.0 = unchanged)
#   bool   -> horizontal mirror flip when True
# Sprites are anchored so their BOTTOM edge sits on the base point (x, y),
# exactly like the rocks in the forest scene.
# The five hut positions are the trodden pads baked into the ground
# (tools/rebake_village.py PAD_DEG / PAD_RX / PAD_RY), so every hut stands on
# its own pad with grass between neighbours instead of one packed plaza. South
# is left empty on purpose: that is the entrance.
PROP_LAYOUT = [
    # Five hut pads on ONE circle of equal radius: every spoke from the plaza
    # rim is the same length, so no hut reads as nearer than the others.
    ("hut",  2740.0, 1330.0, 280.0),   # east
    ("hut3", 2523.0, 1853.0, 280.0),   # north-east
    ("hut2", 2000.0, 2070.0, 280.0),   # north
    ("hut4", 1477.0, 1853.0, 280.0),   # north-west
    ("hut3", 1260.0, 1330.0, 280.0),   # west
    # Two watchtowers on the baked earth mounds flanking the entrance, set
    # back north of the gate arch which sits in the fence gap.
    ("watchtower", 1700.0, 580.0, WATCHTOWER_WIDTH),
    ("watchtower", 2300.0, 580.0, WATCHTOWER_WIDTH),
    ("gate", 2000.0, 276.0, 300.0),
    # Loose props on their own trodden pads (rebake PROP_PATCH), clear of huts.
    ("woodpile", 2150.0, 1560.0, 170.0),
    ("woodpile", 1850.0, 1560.0, 170.0),
    ("totem", 1850.0,  935.0, None),
    ("rack",  2325.0, 1100.0, None, True, 0.9),
    ("rack",  1670.0, 1100.0, None, False, 0.9),
]

# Fallback heights, used only when a layout entry gives width=None.
PROP_HEIGHT = {"totem": 260.0, "rack": 190.0}

# Body radius used for collisions (the visible footprint, not the sprite box).
PROP_RADIUS = {"hut": 95.0, "hut2": 95.0, "totem": 30.0, "rack": 55.0,
               "watchtower": 45.0, "woodpile": 45.0}
# A fence is a long thin thing: block it with a chain of circles along its run.
FENCE_CHAIN_HALF = 45.0
FENCE_CHAIN_RADIUS = 24.0

DINO_WIDTH = 210.0


# Tribespeople scattered around the clearing, most of them near their own hut.
# None of them stand in front of the fire: a character nearer than the hearth
# would be drawn over it and swallow the flame, so their x is kept clear of
# the fire's x range when their y is nearer than the hearth.
NPC_SPOTS = [
    # --- original six, kept near their huts (all north of the hearth) ---
    (2820.0, 1530.0, "tribe_a"),   # by the east hut
    (2600.0, 1650.0, "tribe_b"),   # by the north-east hut
    (2000.0, 1820.0, "tribe_c"),   # south of the north hut
    (1400.0, 1650.0, "tribe_a"),   # by the north-west hut
    (1180.0, 1530.0, "tribe_b"),   # by the west hut
    (2900.0, 1450.0, "tribe_c"),   # by the pen
    # --- added variety: newly generated faces, all north of the hearth so none
    #     stand in front of the flame (fire's x range only matters when a
    #     villager is nearer/south of it) ---
    (2700.0, 1450.0, "tribe_d"),   # elder, east of the plaza
    (2450.0, 1700.0, "tribe_e"),   # boy, north-east plaza
    (1700.0, 1450.0, "tribe_f"),   # woman, west-centre plaza
    (1550.0, 1750.0, "tribe_d"),   # elder, north-west plaza
    (2850.0, 1600.0, "tribe_e"),   # boy, by the pen
    (1300.0, 1450.0, "tribe_f"),   # woman, by the west hut
]

# Just inside the gate, north of the two watchtowers, so you arrive looking
# south at the gate arch and the towers flanking the approach.
SPAWN = (2000.0, 780.0)

COLOR_PANEL_BG = (18, 26, 20, 190)
COLOR_PANEL_BORDER = (150, 175, 95, 130)
COLOR_HELP_BG = (18, 26, 20, 170)
COLOR_HELP_TXT = (225, 235, 205)


# ===========================================================================
class Scene11View(BaseGameView):
    """The tribe's village clearing. The hunter is player-controlled."""

    def __init__(self):
        super().__init__()
        self.t = 0.0

        # BBQ roasting closeup hand-off & Dino clue inspection.
        self.near_bbq = False
        self.near_guards = False
        self.meal = RoastMeal()
        self._meal_sprites = None
        self.bbq_done = False
        self.near_dino = False
        self.inspecting_dino = False
        self.inspected_wound = False

        self.player = Player(*SPAWN, char_id="savage", sprites_dir=CHARS_DIR, scale=CHAR_SCALE)
        self.held_keys = set()
        self.dust = []

        # Pre-baked ground + prop sprites (lazy-loaded on first draw).
        self._ground_tex = None
        self._ground_list = None
        self._prop_tex = {}
        self._props_ready = False
        self._fire_texs = None
        self._grill_tex = None

        self._build_props()
        self._build_tribespeople()

        # Hearth fire particles (use the same classes as the forest camp).
        self.embers = [EmberParticle(HEARTH_X, HEARTH_Y + 85) for _ in range(30)]
        self.smoke = [SmokeParticle(HEARTH_X, HEARTH_Y + 110) for _ in range(18)]

        # Arrival fade: S09 fades to black while the dino is carried home, so
        # the village fades back in from black.
        self.fade_alpha = 255.0

        self.motes = [PollenMote(SCREEN_WIDTH, SCREEN_HEIGHT) for _ in range(50)]
        self.god_rays = [
            (0.12, 0.07, 0.15, 16, random.uniform(0, 6.28)),
            (0.34, 0.11, 0.18, 24, random.uniform(0, 6.28)),
            (0.58, 0.08, 0.16, 18, random.uniform(0, 6.28)),
            (0.81, 0.10, 0.17, 20, random.uniform(0, 6.28)),
        ]

        self._text = {}

    # ===================================================================
    # SETUP
    # ===================================================================
    def on_show_view(self):
        super().on_show_view()
        # Persist the "already roasted" flag set by the closeup across the
        # view switch so the rack stops prompting after the first cook.
        self.bbq_done = getattr(self.window, "bbq_done", False)
        self.meal = RoastMeal.restore(getattr(self.window, "bbq_progress", None))
        self.held_keys.clear()
        self._props_ready=False

    def _build_props(self):
        self.props = []
        tower_idx = 0
        for item in PROP_LAYOUT:
            kind, x, y, width = item[:4]
            # Trailing modifiers are type-driven and order-free:
            #   a bool   -> horizontal mirror flip (True = flipped)
            #   a number -> size multiplier (1.0 = unchanged, 1.3 = 30% bigger)
            size_mult, flip = 1.0, False
            for m in item[4:]:
                if isinstance(m, bool):
                    flip = m
                elif isinstance(m, (int, float)):
                    size_mult = float(m)
            prop = {
                "kind": kind, "x": x, "y": y,
                "width": width, "height": PROP_HEIGHT.get(kind),
                "sp": None, "cr": PROP_RADIUS.get(kind, 40.0),
                "size_mult": size_mult, "flip": flip,
            }
            if kind == "watchtower":
                # Generated complete tower includes its guard and natural occlusion.
                prop["tower_texture"] = ("watchtower_guard_a", "watchtower_guard_b")[tower_idx % 2]
                tower_idx += 1
            self.props.append(prop)
        # The dino is a prop too, so it depth-sorts with everything else.
        self.dino_prop = {"kind": "dino", "x": DINO_SPOT[0], "y": DINO_SPOT[1] + 6.0,
                          "width": DINO_WIDTH, "height": None, "sp": None, "cr": 80.0,
                          "size_mult": 1.0, "flip": False}

    @staticmethod
    def _make_sentry(x, y, idx):
        """One guard per tower, each his own look so they do not clone."""
        cid = SENTRY_CHARS[idx % len(SENTRY_CHARS)]
        return Player(x + SENTRY_X_OFFSET, y + SENTRY_LIFT, char_id=cid, sprites_dir=CHARS_DIR, scale=CHAR_SCALE)

    def _build_tribespeople(self):
        self.tribespeople = [Player(x, y, char_id=cid, sprites_dir=CHARS_DIR, scale=CHAR_SCALE)
                             for x, y, cid in NPC_SPOTS]

    # ===================================================================
    # LAZY TEXTURE LOADING
    # ===================================================================
    def _tex(self, kind):
        if kind not in self._prop_tex:
            self._prop_tex[kind] = arcade.load_texture(str(SPRITE_PATHS[kind]))
        return self._prop_tex[kind]

    def _ensure_ground(self):
        if self._ground_tex is None:
            self._ground_tex = arcade.load_texture(str(GROUND_PATH))
            self._ground_sprite = arcade.Sprite(self._ground_tex, scale=1.0)
            self._ground_sprite.center_x = WORLD_WIDTH / 2
            self._ground_sprite.center_y = WORLD_HEIGHT / 2
            self._ground_list = arcade.SpriteList()
            self._ground_list.append(self._ground_sprite)

    def _ensure_prop_sprites(self):
        if self._props_ready:
            return
        for p in self.props + [self.dino_prop]:
            kind = p["kind"]
            if kind == "dino":
                path, native_w = DINO_IMAGE, 1536.0
            else:
                path, native_w = SPRITE_PATHS[kind], None
            if kind == "dino":
                tex = arcade.load_texture(str(DINO_IMAGE))
                if self.meal.prep_cuts:
                    atlas=arcade.load_texture(str(ROOT_DIR/'assets/prehistoric/cooking_v2/dinosaur_prep_atlas_v1.png'))
                    tex=atlas.crop(min(2,self.meal.prep_cuts)*512,0,512,512)
                scale = DINO_WIDTH / tex.width
            else:
                tex = self._tex(p.get("tower_texture", kind))
                if p["flip"]:
                    tex = tex.flip_left_right()
                scale = (p["width"] / tex.width) if p["width"] else (p["height"] / tex.height)
            scale *= p["size_mult"]
            sp = arcade.Sprite(tex, scale=scale)
            sp.center_x = p["x"]
            # Bottom edge ON the base point: the baked contact shadow then
            # sits at the base line instead of spilling onto nearer ground.
            # The juvenile art carries empty canvas under the corpse, so drop it
            # by that much or the body floats above its own shadow.
            lift = (sp.height * DINO_EMPTY_BOTTOM_FRAC) if kind == "dino" else 0.0
            sp.center_y = p["y"] + sp.height / 2.0 - lift
            p["sp"] = sp
            p["scale"] = scale

        self._props_ready = True

    # ===================================================================
    # CAMERA
    # ===================================================================
    def update_camera(self):
        if self.camera and self.window:
            self.camera.viewport = LRBT(0, self.window.width, 0, self.window.height)
            self.camera.projection = LRBT(-SCREEN_WIDTH / 2, SCREEN_WIDTH / 2,
                                          -SCREEN_HEIGHT / 2, SCREEN_HEIGHT / 2)
            self._follow_camera()

    def _follow_camera(self):
        px, py = self.player.x, self.player.y
        half_w, half_h = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        cx = max(half_w, min(WORLD_WIDTH - half_w, px))
        cy = max(half_h, min(WORLD_HEIGHT - half_h, py))
        self.camera.position = (cx, cy)

    # ===================================================================
    # COLLISION
    # ===================================================================
    FOOT_RADIUS = 42.0

    def _solid_push(self, px, py, ox, oy, orad):
        r = orad + self.FOOT_RADIUS
        dx, dy = px - ox, py - oy
        d = math.hypot(dx, dy)
        if d >= r:
            return px, py
        if d < 0.001:
            return ox + r, py
        return ox + dx / d * r, oy + dy / d * r

    def _push_ellipse(self, px, py, cx, cy, rx, ry):
        dx = px - cx
        dy = py - cy
        norm = (dx / rx) ** 2 + (dy / ry) ** 2
        if norm >= 1.0:
            return px, py
        if norm < 0.0001:
            return cx, cy - ry
        scale = 1.0 / math.sqrt(norm)
        return cx + dx * scale, cy + dy * scale

    def _clamp_to_palisade(self, fx, fy):
        """Keep the player inside the baked palisade ring.

        The ring is painted into the ground, so it cannot collide like a
        sprite: an invisible ellipse 100 units tighter than the painted logs
        does the job instead.
        """
        nx = (fx - PALISADE_CENTRE[0]) / PALISADE_RX
        ny = (fy - PALISADE_CENTRE[1]) / PALISADE_RY
        d = math.hypot(nx, ny)
        if d <= 1.0:
            return fx, fy
        return (PALISADE_CENTRE[0] + nx / d * PALISADE_RX,
                PALISADE_CENTRE[1] + ny / d * PALISADE_RY)

    def _resolve_collisions(self):
        fx = self.player.x
        fy = self.player.y - self.player.feet_offset
        for p in self.props:
            if p["kind"] == "fence":
                for cx in (-FENCE_CHAIN_HALF, 0.0, FENCE_CHAIN_HALF):
                    fx, fy = self._solid_push(fx, fy, p["x"] + cx, p["y"],
                                              FENCE_CHAIN_RADIUS)
            elif p["kind"] == "gate":
                continue        # two posts with a gap you are meant to walk through
            else:
                fx, fy = self._solid_push(fx, fy, p["x"], p["y"], p["cr"])
        fx, fy = self._push_ellipse(fx, fy, DINO_COLLISION_CX, DINO_COLLISION_CY,
                                    DINO_COLLISION_RX, DINO_COLLISION_RY)
        fx, fy = self._push_ellipse(fx, fy, HEARTH_COLLISION_X, HEARTH_COLLISION_Y,
                                    HEARTH_COLLISION_RX, HEARTH_COLLISION_RY)
        fx, fy = self._clamp_to_palisade(fx, fy)
        px = max(300.0, min(WORLD_WIDTH - 300.0, fx))
        py = max(110.0 + self.player.feet_offset,
                 min(WORLD_HEIGHT - 130.0, fy + self.player.feet_offset))
        self.player.x, self.player.y = px, py

    # ===================================================================
    # UPDATE
    # ===================================================================
    def on_update(self, dt):
        if self.is_paused:
            return
        # Loading the 3000x1840 ground makes the first frame take seconds.
        # Without a clamp that one frame swallows the whole arrival card.
        dt = min(dt, 0.05)
        self.t += dt

        move_x, move_y = 0.0, 0.0
        if arcade.key.W in self.held_keys or arcade.key.UP in self.held_keys:
            move_y += 1.0
        if arcade.key.S in self.held_keys or arcade.key.DOWN in self.held_keys:
            move_y -= 1.0
        if arcade.key.A in self.held_keys or arcade.key.LEFT in self.held_keys:
            move_x -= 1.0
        if arcade.key.D in self.held_keys or arcade.key.RIGHT in self.held_keys:
            move_x += 1.0

        bounds = (300, WORLD_WIDTH - 300, 110, WORLD_HEIGHT - 130)
        self.player.update(dt, move_x, move_y, dust_particles=self.dust, bounds=bounds)
        self._resolve_collisions()

        # The hearth spit is the cooking station; approach outside the fire collision.
        pfx, pfy = self.player.x, self.player.y - self.player.feet_offset
        d_bbq = math.hypot(pfx - HEARTH_COLLISION_X, pfy - HEARTH_COLLISION_Y)
        d_dino = math.hypot(pfx - DINO_SPOT[0], pfy - DINO_SPOT[1])
        d_guards = math.hypot(pfx - 2000.0, pfy - 720.0)

        in_bbq = (d_bbq < 165.0) and (self.meal.stage not in ('carry', 'wake'))
        in_dino = (d_dino < 170.0)
        in_guards = (d_guards < 180.0) and (self.meal.stage == 'carry')

        # Strictly mutually exclusive: hearth and dinosaur prompts never appear together
        if in_bbq and in_dino:
            if d_dino < d_bbq:
                in_bbq = False
            else:
                in_dino = False

        if in_guards:
            in_bbq = False
            in_dino = False

        self.near_bbq = in_bbq
        self.near_dino = in_dino
        self.near_guards = in_guards

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

        if self.fade_alpha > 0:
            self.fade_alpha = max(0.0, self.fade_alpha - dt * 190.0)

        if self.camera:
            self._follow_camera()

    # ===================================================================
    # INPUT
    # ===================================================================
    def on_key_press(self, key, modifiers):
        if self.inspecting_dino and not self.is_paused:
            if key in (arcade.key.E, arcade.key.ESCAPE, arcade.key.SPACE, arcade.key.ENTER):
                self.inspecting_dino = False
            return
        if self.handle_pause_key(key):
            self.held_keys.clear()
            return
        if key == arcade.key.E:
            if self.near_dino:
                self.inspecting_dino = True
                self.held_keys.clear()
                self.inspected_wound = True
                self.meal.clue_seen = True
                self.window.bbq_progress = self.meal.save()
                return
            from scenes.prehistoric_bbq_view import BBQCookingView
            if self.near_guards and self.meal.stage == 'carry':
                self.held_keys.clear()
                self.window.show_view(BBQCookingView(return_view=self, meal=self.meal, mode='handoff'))
                return
            if self.near_bbq and self.meal.stage not in ('carry', 'wake'):
                self.held_keys.clear()
                mode = 'cook'
                if not self.meal.prepared and self.meal.stage=='place':
                    from scenes.prehistoric_prep_view import DinosaurPrepView
                    self.window.show_view(DinosaurPrepView(return_view=self,meal=self.meal))
                else:
                    self.window.show_view(BBQCookingView(return_view=self, meal=self.meal, mode=mode))
                return
        self.held_keys.add(key)

    def on_key_release(self, key, modifiers):
        self.held_keys.discard(key)

    def on_mouse_motion(self, x, y, dx=0, dy=0):
        self.handle_pause_mouse_motion(x, y)

    def screen_to_world(self, x: float, y: float):
        """Map screen mouse coordinates to world coordinates using current camera."""
        vx, vy = self.to_virtual_coords(x, y)
        if self.camera:
            cx, cy = self.camera.position
            return cx - SCREEN_WIDTH / 2.0 + vx, cy - SCREEN_HEIGHT / 2.0 + vy
        return vx, vy

    def on_mouse_press(self, x, y, button, modifiers):
        if self.handle_pause_mouse_press(x, y, button):
            return
        if self.inspecting_dino:
            self.inspecting_dino = False
            return
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        wx, wy = self.screen_to_world(x, y)
        if self.near_dino:
            if abs(wx - DINO_SPOT[0]) < 130 and abs(wy - (DINO_SPOT[1] + 45)) < 90:
                self.inspecting_dino = True
                self.held_keys.clear()
                self.inspected_wound = True
                self.meal.clue_seen = True
                self.window.bbq_progress = self.meal.save()
                return
        if self.near_bbq and self.meal.stage not in ('carry', 'wake'):
            if abs(wx - HEARTH_X) < 130 and abs(wy - (HEARTH_Y + 80)) < 110:
                self.held_keys.clear()
                if not self.meal.prepared and self.meal.stage == 'place':
                    from scenes.prehistoric_prep_view import DinosaurPrepView
                    self.window.show_view(DinosaurPrepView(return_view=self, meal=self.meal))
                else:
                    from scenes.prehistoric_bbq_view import BBQCookingView
                    self.window.show_view(BBQCookingView(return_view=self, meal=self.meal, mode='cook'))
                return
        if self.near_guards and self.meal.stage == 'carry':
            if math.hypot(wx - 2000.0, wy - 750.0) < 120:
                self.held_keys.clear()
                from scenes.prehistoric_bbq_view import BBQCookingView
                self.window.show_view(BBQCookingView(return_view=self, meal=self.meal, mode='handoff'))
                return

    # ===================================================================
    # DRAW
    # ===================================================================
    def on_draw(self):
        self.clear(color=(24, 34, 24))
        self._ensure_ground()
        self._ensure_prop_sprites()
        self.use_game_camera()

        self._ground_list.draw()

        # Depth-sorted props + NPCs + player.
        # Lower base y = nearer = drawn last, so it covers things further away.
        items = []
        for p in self.props + [self.dino_prop]:
            items.append((p["y"], lambda p=p: self._draw_prop(p)))
        for i, npc in enumerate(self.tribespeople):
            items.append((npc.y - npc.feet_offset,
                          lambda npc=npc: npc.draw(self.aspect_ratio_correction)))
        items.append((HEARTH_DEPTH_Y, self._draw_camp))
        items.append((self.player.y - self.player.feet_offset, self._draw_player))
        items.sort(key=lambda it: it[0], reverse=True)
        for _, fn in items:
            fn()

        for s in self.smoke:
            s.draw()
        for e in self.embers:
            e.draw()

        # World-space interactive prompt, identical to Scene 7 (clean, non-intrusive)
        if self.t > 4.6 and not self.inspecting_dino:
            self._draw_world_prompts()

        self.window.default_camera.use()
        self._draw_god_rays()
        self._draw_motes()
        if self.inspecting_dino:
            self._draw_dino_modal()
        self._draw_arrival()

        # Black fade-in, painted last so it covers the whole screen space.
        if self.fade_alpha > 0:
            w, h = self.window.width, self.window.height
            arcade.draw_rect_filled(arcade.XYWH(w / 2, h / 2, w, h),
                                    (0, 0, 0, int(self.fade_alpha)))

        self.use_game_camera()
        self.draw_pause_overlay()

    def _draw_prop(self, p):
        arcade.draw_sprite(p["sp"])
        if p.get("sentry") is not None:
            self._draw_sentry(p["sentry"])
            # Same canvas and transform as the tower: foreground architecture
            # occludes the guard while the rear platform stays behind him.
            arcade.draw_texture_rect(self._tex("watchtower_overlay"),
                                     arcade.XYWH(p["sp"].center_x, p["sp"].center_y,
                                                 p["sp"].width, p["sp"].height))

    def _draw_sentry(self, sentry):
        """Draw inside the tower; its foreground layer is composited afterward."""
        tex = sentry.textures["down"]["idle"]
        h = SENTRY_HEIGHT
        w = h * tex.width / tex.height
        bob = 0.0  # Keep the feet planted on the upper deck.
        arcade.draw_texture_rect(tex, arcade.XYWH(sentry.x,
                                                  sentry.y + h / 2.0 + bob,
                                                  w, h))

    def _fire_textures(self):
        """Lazy-load the 41 campfire frames (black background already keyed)."""
        if self._fire_texs is None:
            self._fire_texs = [
                arcade.load_texture(str(p))
                for p in sorted(CAMPFIRE_DIR.glob("frame_*.png"))
            ]
        return self._fire_texs

    def _grill_texture(self):
        """Lazy-load the roasting spit standing over the hearth."""
        if self._grill_tex is None:
            self._grill_tex = arcade.load_texture(str(GRILL_PATH))
        return self._grill_tex

    def _draw_camp(self):
        """Animated painted fire from campfire gif plus the roasting spit standing
        over it. The fire sprite carries its own log pile and stone ring, so
        nothing is drawn procedurally here. The spit is drawn on top so its
        crossbar sits in the flame column and its forked feet straddle the
        hearth. A static warm light spill lies flat on the ground."""
        cx, cy = HEARTH_X, HEARTH_Y
        arcade.draw_ellipse_filled(cx, cy + 8, 95, 25, (255, 120, 40, 9))  # smaller glow to match smaller hearth
        texs = self._fire_textures()
        base = cy + CAMPFIRE_BASE_LIFT
        if texs:
            tex = texs[int(self.t * CAMPFIRE_FPS) % len(texs)]
            w = CAMPFIRE_WORLD_WIDTH
            h = w * (tex.height / tex.width)
            arcade.draw_texture_rect(tex, arcade.XYWH(cx, base + h / 2.0, w, h))
        # Roasting spit drawn on top of the fire.
        gtex = self._grill_texture()
        if gtex:
            gw = GRILL_WORLD_WIDTH
            gh = gw * (gtex.height / gtex.width)
            gy = base + GRILL_FEET_OFFSET + gh / 2.0   # feet sit at the log line
            arcade.draw_texture_rect(gtex, arcade.XYWH(cx, gy, gw, gh))
            stage = self.meal.stage
            if stage in ('roast_a', 'turn', 'roast_b', 'lift'):
                progress = self.meal.side_b if stage == 'roast_b' else self.meal.side_a
                name = 'done' if stage == 'lift' or progress >= .8 else 'half' if progress >= .32 else 'raw'
                if not hasattr(self, '_map_meat'):
                    self._map_meat = {}
                if name not in self._map_meat:
                    self._map_meat[name] = arcade.load_texture(str(ROOT_DIR / 'assets/prehistoric/cooking_v2' / (name + '.png')))
                meat = self._map_meat[name]
                mw = 76.0
                arcade.draw_texture_rect(meat, arcade.XYWH(cx, base + GRILL_FEET_OFFSET + gh * .75,
                                                          mw, mw * meat.height / meat.width))

    def _draw_player(self):
        self.player.draw(self.aspect_ratio_correction)
        if self.meal.stage == 'carry':
            if self._meal_sprites is None:
                art = ROOT_DIR / 'assets' / 'prehistoric' / 'cooking_v2'
                self._meal_sprites = arcade.SpriteList()
                for name in ('plate', 'slices'):
                    self._meal_sprites.append(arcade.Sprite(str(art / (name + '.png'))))
            for i, sp in enumerate(self._meal_sprites):
                sp.scale = (66 if i == 0 else 46) / sp.texture.width
                sp.center_x = self.player.x
                sp.center_y = self.player.y - 34 + i * 7
            self._meal_sprites.draw()
        for d in self.dust:
            d.draw()

    # ---- Atmosphere ------------------------------------------------------
    def _draw_god_rays(self):
        w, h = self.window.width, self.window.height
        for top_x, wf, slant_f, base_a, phase in self.god_rays:
            pulse = 0.75 + 0.25 * math.sin(self.t * 0.8 + phase)
            a = int(base_a * pulse)
            rx_top = top_x * w
            rw = wf * w
            slant = slant_f * w
            arcade.draw_polygon_filled([
                (rx_top - rw / 2, h + 20),
                (rx_top + rw / 2, h + 20),
                (rx_top + rw / 2 + slant, h * 0.32),
                (rx_top - rw / 2 + slant, h * 0.32),
            ], (255, 220, 150, a))

    def _draw_motes(self):
        for m in self.motes:
            m.draw()

    def _draw_world_prompt(self, wx, wy, text, scale=1.0, highlight=False):
        """World-space interactive prompt, strictly matching Scene 7 styling."""
        bw = max(220.0, (len(text) * 9.2 + 38.0)) * scale
        bh = 42.0 * scale
        bg_col = (180, 70, 50, 220) if highlight else (25, 32, 45, 210)
        border_col = COLOR_GOLD if highlight else (110, 180, 245)
        arcade.draw_rect_filled(arcade.XYWH(wx, wy, bw, bh), bg_col)
        arcade.draw_rect_outline(arcade.XYWH(wx, wy, bw, bh), border_col, 2.0 if highlight else 1.2)
        arcade.draw_text(text, wx, wy - 5.0 * scale,
                         (255, 255, 255) if highlight else (230, 240, 255),
                         int(11 * scale), anchor_x="center", bold=True)

    def _draw_world_prompts(self):
        """Interactive prompt tags floating over the target landmarks (Scene 7 design).
        Strictly mutually exclusive so hearth and dinosaur prompts never appear together.
        """
        # 1. Entrance Guards (Meal Delivery)
        if self.near_guards and self.meal.stage == 'carry':
            self._draw_world_prompt(2000.0, 785.0, '[E] Give Meal to Entrance Guards', highlight=True)
            return

        # 2. Fireplace / Roasting Spit
        if self.near_bbq and self.meal.stage not in ('carry', 'wake'):
            prompt = ('[E] Prepare Next Batch' if self.meal.stage == 'return_fire'
                      else '[E] Prepare Dinosaur' if not self.meal.prepared and self.meal.stage=='place'
                      else '[E] Cook Meat at Hearth')
            self._draw_world_prompt(HEARTH_X, HEARTH_Y + 160.0, prompt, highlight=True)
            return

        # 3. Juvenile Dinosaur Inspection
        if self.near_dino and not self.inspecting_dino:
            self._draw_world_prompt(DINO_SPOT[0], DINO_SPOT[1] + 90.0,
                                    "[E] Check on Dinosaur",
                                    highlight=not self.inspected_wound)
            return

    def _draw_arrival(self):
        """One-shot arrival card, fading out a few seconds after the fade-in."""
        if self.t > 4.6:
            return
        if self.t < 1.3:
            a = 255.0 * (self.t / 1.3)
        else:
            a = 255.0 * max(0.0, 1.0 - (self.t - 1.3) / 2.6)
        a = int(max(0.0, min(255.0, a)))
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT * 0.24
        arcade.draw_rect_filled(arcade.XYWH(cx, cy - 8, 760, 96),
                                (8, 10, 8, int(a * 0.93)))
        arcade.draw_line(cx - 300, cy + 28, cx + 300, cy + 28, (215, 180, 110, int(a * 0.6)), 1.5)
        arcade.draw_line(cx - 300, cy - 44, cx + 300, cy - 44, (215, 180, 110, int(a * 0.6)), 1.5)
        self._label("arr_title", "THE VILLAGE", 26, (255, 240, 205, a),
                    cx, cy + 8, bold=True, anchor_x="center")
        self._label("arr_sub", "You carried the little one home.", 15,
                    (244, 238, 224, a), cx, cy - 24, anchor_x="center")

    def _draw_dino_modal(self):
        """Inspection of the resting juvenile dinosaur."""
        self._use_pause_camera()
        cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2
        mw, mh = 840, 570

        # Darkened cinematic backdrop
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, SCREEN_WIDTH, SCREEN_HEIGHT), (8, 12, 10, 235))

        # Modal window chassis with layered frame & stone styling
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, mw, mh), (15, 18, 16, 252))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, mw, mh), (65, 85, 75), 1.5)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, mw - 8, mh - 8), (140, 170, 150, 45), 1.0)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, mw + 6, mh + 6), (10, 15, 12, 200), 2.5)

        # Dinosaur closeup artwork (clean frame, no clue title)
        if not hasattr(self, '_wound_tex') or self._wound_tex is None:
            wound_path = ROOT_DIR / 'assets' / 'prehistoric' / 'cooking_v2' / 'dino_wound_closeup.png'
            self._wound_tex = arcade.load_texture(str(wound_path))
        img_w, img_h = 520, 325
        img_y = cy + 82

        # Image frame backing & gold trim border
        arcade.draw_rect_filled(arcade.XYWH(cx, img_y, img_w + 10, img_h + 10), (12, 16, 14))
        arcade.draw_texture_rect(self._wound_tex, arcade.XYWH(cx, img_y, img_w, img_h))
        arcade.draw_rect_outline(arcade.XYWH(cx, img_y, img_w, img_h), (205, 178, 120, 230), 2.0)
        arcade.draw_rect_outline(arcade.XYWH(cx, img_y, img_w + 4, img_h + 4), (205, 178, 120, 75), 1.0)

        # Subtle decorative divider line under image
        div_y = cy - 105
        arcade.draw_line(cx - 240, div_y, cx + 240, div_y, (175, 155, 115, 80), 1.0)
        arcade.draw_circle_filled(cx, div_y, 3.0, (205, 178, 120, 200))
        arcade.draw_circle_outline(cx, div_y, 5.5, (205, 178, 120, 100), 1.0)

        FONT_SERIF = ("Georgia", "Palatino Linotype", "Times New Roman", "serif")
        FONT_SANS = ("Segoe UI", "Calibri", "Helvetica Neue", "Arial")

        # 1. Narrative observation lines (Literary serif, warm ivory)
        self._draw_shadowed_label("dm_line1", "A neat, three-sided puncture pierces the juvenile's neck.",
                                  14.5, (242, 238, 228), cx, cy - 138, FONT_SERIF, bold=False)
        self._draw_shadowed_label("dm_line2", "Pale blue crystals cling to a tiny metallic fragment.",
                                  14.5, (220, 232, 240), cx, cy - 166, FONT_SERIF, bold=False)

        # 2. Player character inner observation (Italic golden amber)
        self._draw_shadowed_label("dm_thought", "“Stone spears do not leave wounds shaped like that...”",
                                  14.0, (250, 220, 140), cx, cy - 212, FONT_SERIF, bold=True, italic=True)

        # 3. Dismissal prompt (Clean modern sans-serif UI tag)
        self._draw_shadowed_label("dm_hint", "[ Click anywhere  /  E  /  ESC  to Close ]",
                                  11.0, (145, 175, 195, 210), cx, cy - 254, FONT_SANS, bold=False)

    # ---- Lazy text factory ----------------------------------------------
    def _text_obj(self, key, text, size, color, bold=False, anchor_x="left", font_name=None, italic=False):
        if font_name is None:
            font_name = ("Segoe UI", "Calibri", "Arial")
        if key not in self._text:
            self._text[key] = arcade.Text(
                text, 0, 0, color=color,
                font_name=font_name,
                font_size=size, bold=bold, italic=italic,
                anchor_x=anchor_x, anchor_y="center",
            )
        else:
            obj = self._text[key]
            obj.text = text
            obj.color = color
            obj.font_size = size
            obj.bold = bold
            obj.italic = italic
            obj.anchor_x = anchor_x
        return self._text[key]

    def _label(self, key, text, size, color, x, y, bold=False, anchor_x="left", font_name=None, italic=False):
        obj = self._text_obj(key, text, size, color, bold, anchor_x, font_name, italic)
        obj.x = x
        obj.y = y
        obj.draw()

    def _draw_shadowed_label(self, key, text, size, color, x, y, font_name, bold=False, italic=False, anchor_x="center"):
        # Shadow
        sh = self._text_obj(key + "_sh", text, size, (0, 0, 0, 240), bold=bold, anchor_x=anchor_x, font_name=font_name, italic=italic)
        sh.x = x + 1.0
        sh.y = y - 1.5
        sh.draw()
        # Foreground
        fg = self._text_obj(key + "_fg", text, size, color, bold=bold, anchor_x=anchor_x, font_name=font_name, italic=italic)
        fg.x = x
        fg.y = y
        fg.draw()


# Menu-hub compatibility alias, mirroring scenes.prehistoric_view.
Scene11HubView = Scene11View
