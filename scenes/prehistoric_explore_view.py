"""Prehistoric forest free-roam exploration view (shared by S09-S13).

Mirrors the richness of clearing_simulation.py (free WASD / arrow movement,
camera follows the character, footstep dust, 2.5D depth sorting, a lit campfire
with ember + smoke particle systems, glowing standing stones, drifting wind
motes, day lighting tint, info panel and radar minimap) restyled to the
prehistoric jungle.
"""
import json
import math
import random
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import arcade
from arcade.types.rect import LRBT

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, CHARACTERS_DIR
from core.player import Player, FEET_OFFSET
from core.particles import FootstepDust
from core.base_view import BaseGameView

# ---- World dimensions (matches the pre-baked ground texture) ---------------
WORLD_WIDTH = 2600.0
WORLD_HEIGHT = 1600.0
GROUND_PATH = ROOT_DIR / "assets" / "prehistoric" / "prehistoric_ground.png"
# Pond lifted out of the baked ground as a runtime sprite (2026-10-20): it covers
# the baked pond's rim/contour defects and the removed-log ghost smudges inside
# the water with a slightly larger, soft-shorelined pond. Built by
# tools/make_pond_sprite.py; world centre is the pond's image centre (1950,1140)
# mapped via world_y = 1600 - img_y -> (1950, 460), scale 1.0.
POND_SPRITE_PATH = ROOT_DIR / "assets" / "prehistoric" / "pond_sprite.png"
POND_CENTRE_X = 1975.0
POND_CENTRE_Y = 510.0
DECOR_DIR = ROOT_DIR / "assets" / "prehistoric" / "decor"
LOG_META_PATH = ROOT_DIR / "assets" / "prehistoric" / "log_meta.json"
# Animated painted campfire (41 frames @10fps, looped) extracted from the
# artist's campfire.gif by tools/make_campfire_frames.py. Replaces the procedural
# stones/logs/flame that _draw_camp used to build out of circles.
CAMPFIRE_DIR = ROOT_DIR / "assets" / "prehistoric" / "campfire_frames"
CAMPFIRE_WORLD_WIDTH = 200.0    # 240x322 art; widest row lands on HEARTH_RADIUS
CAMPFIRE_BASE_LIFT = 26.0       # ground row of the art sits this far above CAMP_Y
CAMPFIRE_FPS = 10.0             # the GIF's own frame rate

# Animated pond water (16 frames @8fps = 2s loop).
POND_FRAMES_DIR = ROOT_DIR / "assets" / "prehistoric" / "pond_frames"
POND_FPS = 8.0

# The drawn sprite centre. POND_CENTRE_* above belongs to tree avoidance.
POND_DRAW_X, POND_DRAW_Y = 1950.0, 460.0
# Water half-axes measured from pond_sprite.png.
POND_WATER_RX, POND_WATER_RY = 267.0, 188.5

CAMP_X = WORLD_WIDTH * 0.5
CAMP_Y = WORLD_HEIGHT * 0.5 - 80.0      # hearth art / collision / particles
# The hearth's ORIGINAL centre, frozen for PLACEMENT. CAMP_Y feeds three early
# layout computations (clear zone, stone ring, occupied seed), so letting it
# move would branch the seeded RNG stream and reshuffle every tree, rock and
# mushroom on the map. Placement uses this constant, everything visual uses
# the live CAMP_Y above.
CAMP_CLEAR_Y = WORLD_HEIGHT * 0.5

# A tree standing in (or right at the edge of) the pond reads as broken. The
# default layout has trees at 22px and 61px from the water; the next closest
# is 176px, so TREE_WATER_TRIGGER only catches the two real offenders, while
# the wider RESITE_CLEARANCE makes sure a moved tree lands well inland instead
# of on the next shoreline.
TREE_WATER_TRIGGER = 150.0
TREE_WATER_RESITE = 220.0
_WATER_CELL = 4        # px per cell in the coarse water grid
_WATER_BAND = 240.0    # flood-fill depth; must exceed both thresholds
_water_grid_cache = None


def _water_grid():
    """Distance in px from every cell to the pond, out to _WATER_BAND.

    PIL only (no numpy in the game). The water mask comes from the POND SPRITE
    itself, not from blue pixels in the baked ground: since 2026-10-24 the pond
    is sprite-only, so reading the ground would find no water at all and every
    "keep trees out of the pond" rule would silently stop working.
    """
    global _water_grid_cache
    if _water_grid_cache is not None:
        return _water_grid_cache
    from PIL import Image
    src = Image.open(POND_SPRITE_PATH)
    water_mask = src.split()[-1].point(lambda v: 255 if v > 40 else 0)
    # Rasterise the sprite into the same space as the old ground-based grid.
    full = Image.new("L", (int(WORLD_WIDTH), int(WORLD_HEIGHT)), 0)
    tx = int(round(POND_CENTRE_X - src.width / 2.0))
    ty = int(round(WORLD_HEIGHT - POND_CENTRE_Y - src.height / 2.0))
    full.paste(water_mask, (tx, ty), water_mask)
    coarse = full.resize((int(WORLD_WIDTH) // _WATER_CELL,
                          int(WORLD_HEIGHT) // _WATER_CELL), Image.BOX)
    px = coarse.load()
    cw, ch = coarse.size
    dist = {}
    frontier = []
    for cy in range(ch):
        for cx in range(cw):
            if px[cx, cy] > 192:
                dist[(cx, cy)] = 0
                frontier.append((cx, cy))
    for d in range(1, int(_WATER_BAND // _WATER_CELL) + 1):
        nxt = []
        for cx, cy in frontier:
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if 0 <= nx < cw and 0 <= ny < ch and (nx, ny) not in dist:
                    dist[(nx, ny)] = d * _WATER_CELL
                    nxt.append((nx, ny))
        frontier = nxt
        if not frontier:
            break
    _water_grid_cache = (dist, cw, ch)
    return _water_grid_cache


def _water_distance(x, y):
    """Approximate px from world (x, y) to the pond; large when far away."""
    dist, cw, ch = _water_grid()
    cx = int(x) // _WATER_CELL
    cy = int(WORLD_HEIGHT - y) // _WATER_CELL   # world y grows upward
    best = 1e9
    for ny in (cy - 1, cy, cy + 1):
        if not (0 <= ny < ch):
            continue
        for nx in (cx - 1, cx, cx + 1):
            if 0 <= nx < cw:
                best = min(best, dist.get((nx, ny), 1e9))
    return best


def _too_close_to_water(x, y, clearance=TREE_WATER_TRIGGER):
    return _water_distance(x, y) < clearance


def _is_pond_tree(x, y):
    """True for the tree(s) whose trunk sits just below the pond and whose
    canopy overhangs the water. The user wants these kept in place (2026-10-24);
    the water-clearance passes relax their minimum distance (see below) so the
    canopy may sit over the water instead of being pushed ~150px off shore."""
    return (abs(x - POND_CENTRE_X) < 340.0 and
            100.0 <= y <= POND_CENTRE_Y - 200.0)


# ---- north-east exit lane -------------------------------------------------
# Mirrors EXIT_PTS in tools/bake_new_forest.py, converted from image space to
# world space (world_y = 1600 - img_y). It is the one gap the user asked for in
# the treeline: it has to stay EMPTY so it reads as a way out and so the player
# can actually walk up through it. Both runtime sprites and baked props are
# kept out of it, hence keeping the two halves of that definition in sync.
EXIT_LANE = [(2065.0, 840.0), (2120.0, 1130.0),
             (2195.0, 1410.0), (2262.0, 1660.0)]
EXIT_LANE_HALF_IN, EXIT_LANE_HALF_OUT = 214.0, 118.0


def _lane_half_width_at(i, t):
    """Corridor half-width, widest inland and narrowing at the map edge."""
    n = len(EXIT_LANE) - 1
    a = EXIT_LANE_HALF_IN + (EXIT_LANE_HALF_OUT - EXIT_LANE_HALF_IN) * (i / n)
    b = EXIT_LANE_HALF_IN + (EXIT_LANE_HALF_OUT - EXIT_LANE_HALF_IN) * ((i + 1) / n)
    return a + (b - a) * t


def _exit_lane_distance(x, y):
    """px from (x, y) to the lane centreline, and the lane half-width there."""
    best, half = 1e9, 0.0
    for i in range(len(EXIT_LANE) - 1):
        ax, ay = EXIT_LANE[i]
        bx, by = EXIT_LANE[i + 1]
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / seg2))
        h = math.hypot(x - (ax + dx * t), y - (ay + dy * t))
        if h < best:
            best, half = h, _lane_half_width_at(i, t)
    return best, half


def _in_exit_lane(x, y, extra=0.0):
    dist, half = _exit_lane_distance(x, y)
    return dist < half + extra


# Vivid prehistoric palette (warm sunlight + lush greens)
COLOR_HELP_BG = (16, 22, 18, 195)
COLOR_HELP_TXT = (235, 240, 225)
COLOR_PANEL_BG = (16, 22, 18, 205)
COLOR_PANEL_BORDER = (150, 175, 95, 150)


# ===========================================================================
# Ported particle systems (from clearing_simulation, prehistoric reskin)
# ===========================================================================
class EmberParticle:
    """Warm embers rising from the tribal hearth."""
    def __init__(self, cx, cy):
        self.cx, self.cy = cx, cy
        self.reset()

    def reset(self):
        self.x = self.cx + random.uniform(-18, 18)
        self.y = self.cy + random.uniform(-6, 10)
        self.vx = random.uniform(-20, 20)
        self.vy = random.uniform(45, 105)
        self.r = random.uniform(1.8, 3.8)
        self.max_life = random.uniform(0.5, 1.2)
        self.life = self.max_life
        self.color = (255, random.randint(150, 225), 40)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        if self.life <= 0:
            self.reset()

    def draw(self):
        fade = max(0.0, self.life / self.max_life)
        arcade.draw_circle_filled(self.x, self.y, self.r * fade + 0.5, (*self.color, int(230 * fade)))


class SmokeParticle:
    """Soft smoke drifting from the hearth."""
    def __init__(self, cx, cy):
        self.cx, self.cy = cx, cy
        self.reset()

    def reset(self):
        self.x = self.cx + random.uniform(-14, 14)
        self.y = self.cy + random.uniform(10, 25)
        self.vx = random.uniform(-8, 16)
        self.vy = random.uniform(28, 52)
        self.r = random.uniform(7, 13)
        self.max_life = random.uniform(1.6, 2.8)
        self.life = self.max_life

    def update(self, dt):
        self.x += self.vx * dt + math.sin(self.life * 2.5) * 4 * dt
        self.y += self.vy * dt
        self.r += 5.5 * dt
        self.life -= dt
        if self.life <= 0:
            self.reset()

    def draw(self):
        fade = max(0.0, self.life / self.max_life)
        alpha = int(70 * math.sin(fade * math.pi))
        arcade.draw_circle_filled(self.x, self.y, self.r, (225, 225, 212, alpha))


class PollenMote:
    """Drifting dandelion seeds / pollen in the sunbeams."""
    def __init__(self, screen_w, screen_h):
        self.sw, self.sh = screen_w, screen_h
        self.reset(random_y=True)

    def reset(self, random_y=False):
        self.x = random.uniform(0, self.sw)
        self.y = random.uniform(0, self.sh) if random_y else self.sh + random.uniform(5, 30)
        self.vx = random.uniform(10, 40)
        self.vy = random.uniform(-14, 6)
        self.r = random.uniform(1.4, 3.0)
        self.phase = random.uniform(0, math.pi * 2)

    def update(self, dt, t):
        self.x += (self.vx + math.sin(t * 1.3 + self.phase) * 10) * dt
        self.y += self.vy * dt
        if self.y < -20 or self.x > self.sw + 20:
            self.reset()

    def draw(self):
        arcade.draw_circle_filled(self.x, self.y, self.r, (255, 250, 215, 150))


# ===========================================================================
# Main view
# ===========================================================================
class PrehistoricExploreView(BaseGameView):
    """Free-roam prehistoric forest. The hunter (savage) is player-controlled."""

    def __init__(self):
        super().__init__()
        self.t = 0.0

        # Player (the possessed hunter). Spawn in open grass, well clear of
        # the standing-stone ring around the camp.
        self.player = Player(WORLD_WIDTH * 0.25, WORLD_HEIGHT * 0.28, char_id="savage")

        # Footstep dust produced by the player's walk cycle.
        self.dust = []

        # Held keys for immediate, zero-latency response.
        self.held_keys = set()

        # Pre-baked ground (lazy-loaded on first draw).
        self._ground_tex = None
        self._ground_list = None

        # Anime decor sprites (lazy-loaded on first draw).
        self._decor_tex = None
        self._decor_ready = False

        # Animated campfire frames (lazy-loaded on first draw).
        self._fire_texs = None

        # Animated pond water frames (lazy-loaded on first draw).
        self._pond_texs = None

        # World decor (depth-sorted with the player).
        self._build_decor()

        # Campfire particle systems at the tribal hearth. They emit from the
        # middle of the painted flame (2026-10-25): the old spawn sat at the
        # very bottom, which the tall fire art now covers completely, so the
        # embers never made it out into the air.
        self.embers = [EmberParticle(CAMP_X, CAMP_Y + 95) for _ in range(26)]
        self.smoke = [SmokeParticle(CAMP_X, CAMP_Y + 125) for _ in range(16)]

        # Screen-space drifting pollen motes.
        self.motes = [PollenMote(SCREEN_WIDTH, SCREEN_HEIGHT) for _ in range(50)]

        # God rays in screen space.
        self.god_rays = [
            (0.10, 0.06, 0.15, 20, random.uniform(0, 6.28)),
            (0.27, 0.10, 0.18, 28, random.uniform(0, 6.28)),
            (0.44, 0.07, 0.14, 18, random.uniform(0, 6.28)),
            (0.60, 0.12, 0.19, 26, random.uniform(0, 6.28)),
            (0.76, 0.08, 0.16, 20, random.uniform(0, 6.28)),
            (0.92, 0.06, 0.15, 16, random.uniform(0, 6.28)),
        ]

        # Lazy text objects.
        self._text = {}

    # ===================================================================
    # SETUP
    # ===================================================================
    def _build_decor(self):
        rng = random.Random(20261018)

        # Per-sprite half-extents, measured from the actual decor PNGs so the
        # no-overlap test uses real silhouette sizes (not a guess).
        _dims = {}

        def _half_width(kind, style, h):
            key = (kind, style)
            if key not in _dims:
                from PIL import Image
                im = Image.open(DECOR_DIR / f"{kind}_{style}.png")
                _dims[key] = im.size  # (tex_w, tex_h)
            tex_w, tex_h = _dims[key]
            disp_w = h * (tex_w / tex_h)          # world width for target height h
            return 0.5 * disp_w * 1.06            # 6% safety so canopies never touch

        def _col_radius(kind, style, h):
            """Solid radius so the player's BODY can never overlap the prop's
            width at its base. Stones/rocks are widest at the bottom, so use
            the full half-width; trees only block at the trunk."""
            hw = _half_width(kind, style, h)
            if kind == "tree":
                return max(22.0, hw * 0.22)
            return hw

        # Narrative clear zones (2D) so nothing sits on the camp / dino / entrance.
        clear = [
            (CAMP_X, CAMP_CLEAR_Y, 300.0),                         # camp hearth
            (WORLD_WIDTH * 0.26, WORLD_HEIGHT * 0.30, 320.0),     # baby dino
            (WORLD_WIDTH - 240.0, WORLD_HEIGHT - 220.0, 240.0),   # hunter entrance
        ]

        # Glowing mossy standing stones ringed around the camp (circular so
        # adjacent stones never overlap vertically on a flat ellipse).
        self.stones = []
        for i in range(8):
            ang = i / 8 * math.tau
            h = rng.uniform(150, 200)
            self.stones.append({
                "x": CAMP_X + math.cos(ang) * 360,
                "y": CAMP_CLEAR_Y + math.sin(ang) * 360,
                "h": h, "style": i % 3, "phase": rng.uniform(0, 6.28), "sp": None,
                "cr": _col_radius("stone", i % 3, h),
            })

        # User-directed nudge (2026-10-20): the south stone's baked shadow
        # fringe touched the flower cluster just south of it. Shift the stone
        # back so the shadow clears the flowers (they sit nearer).
        self.stones[2]["y"] += 25.0

        # Occupied AABBs: (cx, cy, half_w, half_h). Seed with hearth + stones.
        placed = [(CAMP_X, CAMP_CLEAR_Y, 95.0, 95.0)]
        for st in self.stones:
            placed.append((st["x"], st["y"],
                           _half_width("stone", st["style"], st["h"]),
                           st["h"] * 0.53))

        def add(kind, count, h_lo, h_hi, y_lo, y_hi, camp_clear, margin=38.0, block_rects=None):
            """Rejection-sample props with strict 2D AABB non-overlap."""
            out = []
            tries = 0
            while len(out) < count and tries < 80000:
                tries += 1
                x = rng.uniform(260, WORLD_WIDTH - 260)
                y = rng.uniform(y_lo, y_hi)
                style = rng.randrange(3)
                h = rng.uniform(h_lo, h_hi)
                hw = _half_width(kind, style, h)
                hh = h * 0.53
                # keep out of the narrative clear zones (with extent)
                if any(math.hypot(x - kx, y - ky) < kr + max(hw, hh)
                       for kx, ky, kr in clear):
                    continue
                # strict 2D AABB non-overlap vs everything already placed
                if any(abs(x - px) < hw + phw + margin and
                       abs(y - py) < hh + phh + margin
                       for px, py, phw, phh in placed):
                    continue
                # block_rects: extra world AABBs a prop may never sit inside
                # (e.g. a tree's full sprite box, so small props are not
                # painted over the trunk/canopy by the y-sort).
                if block_rects is not None:
                    if any(abs(x - bx) < hw + bhw + margin and
                           abs(y - by) < hh + bhh + margin
                           for bx, by, bhw, bhh in block_rects):
                        continue
                placed.append((x, y, hw, hh))
                out.append({"x": x, "y": y, "h": h, "style": style,
                            "phase": rng.uniform(0, 6.28), "sp": None,
                            "cr": _col_radius(kind, style, h)})
            return out

        # Anime trees: a few sparse giants, canopies never overlap.
        self.trees = add("tree", 8, 380, 520, 240.0, WORLD_HEIGHT - 240.0, 500.0)
        # A light scatter of rocks / ferns / mushrooms, no overlaps.
        self.rocks = add("rock", 12, 42, 92, 210.0, WORLD_HEIGHT - 210.0, 170.0)
        self.ferns = add("fern", 10, 85, 135, 210.0, WORLD_HEIGHT - 210.0, 160.0)
        # Mushrooms are placed LAST (see below, after the tree re-site), once
        # every tree has its FINAL position, so their no-place boxes are correct.

        # A short rock whose sprite span crosses a tall stone's body gets
        # pasted over the stone's face by the y-sort. Move such rocks to the
        # stone's feet (in front) or above its top; drop the rock if neither
        # spot is free.
        kept = []
        for rk in self.rocks:
            rhw = _half_width("rock", rk["style"], rk["h"])
            rhh = rk["h"] * 0.53
            clash = None
            for st in self.stones:
                shw = _half_width("stone", st["style"], st["h"])
                if abs(rk["x"] - st["x"]) >= rhw + shw:
                    continue
                if rk["y"] < st["y"] + st["h"] and rk["y"] + rk["h"] > st["y"]:
                    clash = st
                    break
            if clash is None:
                kept.append(rk)
                continue
            shw = _half_width("stone", clash["style"], clash["h"])
            stone_entry = (clash["x"], clash["y"], shw, clash["h"] * 0.53)
            placed.remove((rk["x"], rk["y"], rhw, rhh))
            # The clash stone's own seed AABB is not span-accurate; skip it
            # (the new spots below are disjoint from the stone's true span).
            others = [t for t in placed if t != stone_entry]
            for ny in (clash["y"] - rk["h"] - 16.0, clash["y"] + clash["h"] + 16.0):
                if ny < 210.0 or ny > WORLD_HEIGHT - 210.0:
                    continue
                if any(abs(ny - py) < rhh + phh + 38.0 and
                       abs(rk["x"] - px) < rhw + phw + 38.0
                       for px, py, phw, phh in others):
                    continue
                rk["y"] = ny
                placed.append((rk["x"], ny, rhw, rhh))
                kept.append(rk)
                break
        self.rocks = kept

        # Nothing grows in the pond. Re-site any tree standing in the water or
        # on its bank. Own RNG, and runs last so every seeded prop keeps the
        # exact spot it had before.
        wrng = random.Random(77021)
        for tr in self.trees:
            # Pond trees (canopy over the water) are exempt from re-siting
            # unless they are actually standing IN the water; the user wants
            # them kept (2026-10-24). 40px keeps the trunk on land.
            if _is_pond_tree(tr["x"], tr["y"]) and _water_distance(tr["x"], tr["y"]) >= 40.0:
                continue
            if not _too_close_to_water(tr["x"], tr["y"]):
                continue
            hw = _half_width("tree", tr["style"], tr["h"])
            hh = tr["h"] * 0.53
            # Only the trunk has to miss other props; a crown may pass over
            # rocks and ferns. Crown-vs-crown is checked separately below,
            # a full canopy AABB against all 40 props can never find a gap.
            trunk_hw = max(22.0, hw * 0.22)
            others = [o for o in self.trees if o is not tr]
            placed.remove((tr["x"], tr["y"], hw, hh))
            for attempt in range(9000):
                # local search first so the tree stays in its own neighbourhood
                # and the map composition barely changes; fall back to a global
                # sample when the shoreline neighbourhood is boxed in.
                if attempt < 3000:
                    nx = tr["x"] + wrng.uniform(-420.0, 420.0)
                    ny = tr["y"] + wrng.uniform(-420.0, 420.0)
                else:
                    nx = wrng.uniform(300.0, WORLD_WIDTH - 300.0)
                    ny = wrng.uniform(300.0, WORLD_HEIGHT - 260.0)
                nx = min(max(nx, 300.0), WORLD_WIDTH - 300.0)
                ny = min(max(ny, 300.0), WORLD_HEIGHT - 260.0)
                if _too_close_to_water(nx, ny, TREE_WATER_RESITE):
                    continue
                if any(math.hypot(nx - kx, ny - ky) < kr + max(trunk_hw, 40.0)
                       for kx, ky, kr in clear):
                    continue
                if any(abs(nx - px) < trunk_hw + phw + 20.0 and
                       abs(ny - py) < 40.0 + phh + 20.0
                       for px, py, phw, phh in placed):
                    continue
                if any(abs(nx - o["x"]) < hw + _half_width("tree", o["style"], o["h"]) + 38.0 and
                       abs(ny - o["y"]) < hh + o["h"] * 0.53 + 38.0
                       for o in others):
                    continue
                tr["x"], tr["y"] = nx, ny
                placed.append((nx, ny, hw, hh))
                break

        # User-directed move (2026-10-19): runs AFTER the water re-site so the
        # tree's final position is known. The tree left of the pond at its
        # latitude (x < 1717 and 306 <= y <= 614) relocates to the open
        # south-east area, >=220px from water and clear of decor. Keeps the left
        # bank clean without baking anything into the ground.
        for tr in self.trees:
            if tr["x"] < 1717.0 and 306.0 <= tr["y"] <= 614.0:
                _old = (tr["x"], tr["y"], _half_width("tree", tr["style"], tr["h"]), tr["h"] * 0.53)
                # y=265 (not 200): the dark bushes at the SE map edge have
                # bases nearer than 200, so a tree at 200 covered them even
                # though they should occlude it. At 265 the bushes' lower
                # parts stay in front and only their farther canopy tops
                # tuck behind the trunk, which is correct 2.5D.
                tr["x"], tr["y"] = 2400.0, 265.0
                if _old in placed:
                    placed.remove(_old)
                placed.append((tr["x"], tr["y"], _half_width("tree", tr["style"], tr["h"]), tr["h"] * 0.53))

        # User-directed addition (2026-10-20): one extra tree directly below
        # the pond, further left of its centre (~192px). The deconflict pass
        # below relocates it to a fitting spot near the pond (that is why the
        # mossy tree appears at the pond's lower-left); it is a runtime sprite,
        # never baked into the ground.
        _new_tree = {
            "x": 1700.0, "y": 175.0, "h": 430.0, "style": 1,
            "phase": rng.uniform(0, 6.28), "sp": None,
            "cr": _col_radius("tree", 1, 430.0),
        }
        self.trees.append(_new_tree)
        placed.append((_new_tree["x"], _new_tree["y"],
                       _half_width("tree", 1, 430.0), 430.0 * 0.53))

        # User-directed nudge (2026-10-20): the rock nearest the new tree moves
        # up and a little left so the pair reads as two separate props instead
        # of crowding each other at the pond's south-west.
        _near = min(self.rocks, key=lambda rk: math.hypot(rk["x"] - _new_tree["x"],
                                                          rk["y"] - _new_tree["y"]))
        _old_rk = (_near["x"], _near["y"],
                   _half_width("rock", _near["style"], _near["h"]), _near["h"] * 0.53)
        if _old_rk in placed:
            placed.remove(_old_rk)
        _near["x"] -= 57.0
        _near["y"] += 48.0
        placed.append((_near["x"], _near["y"],
                       _half_width("rock", _near["style"], _near["h"]), _near["h"] * 0.53))

        # Mushrooms go LAST, after every tree has been re-sited to avoid water
        # and the user-directed trees added, so their no-place boxes reflect the
        # trees' FINAL positions. Baked ground decor is NOT in that list any
        # more: since 2026-10-24 the bake reads this layout and keeps its own
        # painted pixels clear of the sprite art, so a mushroom can no more
        # sprout on a baked log than the log could be baked under it. Reading
        # the baked boxes here only made the two halves move each other on every
        # re-bake.
        tree_rects = [(tr["x"], tr["y"], _half_width("tree", tr["style"], tr["h"]),
                       tr["h"] * 0.95) for tr in self.trees]
        # The border foliage bands (dark scalloped "trees" baked around the
        # whole map edge) are also ground PNG, not sprites. A mushroom's cap
        # grows UP from its base, so just lifting y_lo is not enough; block the
        # band strips outright so no mushroom (cap included) sits on them.
        edge_rects = [
            (WORLD_WIDTH / 2.0, 107.5, WORLD_WIDTH / 2.0, 107.5),          # bottom band, y in [0, 215]
            (WORLD_WIDTH / 2.0, WORLD_HEIGHT - 107.5, WORLD_WIDTH / 2.0, 107.5),  # top band
        ]
        self.mushrooms = add("mushroom", 9, 52, 95, 255.0, WORLD_HEIGHT - 200.0,
                             200.0, block_rects=tree_rects + edge_rects)

        # ---- final deconflict: no two sprites may cover each other --------
        # Every zone above is enforced WHILE a prop is placed, but three later
        # edits move or add decor afterwards (the water re-site, the
        # user-directed tree move, the extra tree below the pond), and those can
        # drop something on top of something else - two trees once landed on the
        # exact same pixel. So the finished layout is audited once, last,
        # against the sprites' TRUE rendered rectangles. Groups are walked in
        # importance order: the stone ring and the hand-placed trees stay put,
        # small props give way.
        def _sprite_box(kind, d):
            key = (kind, d["style"])
            if key not in _dims:
                from PIL import Image
                im = Image.open(DECOR_DIR / f"{kind}_{d['style']}.png")
                _dims[key] = im.size
            tw, th = _dims[key]
            dw = d["h"] * (tw / th)
            return (d["x"] - dw / 2.0, d["y"], d["x"] + dw / 2.0, d["y"] + d["h"])

        def _boxes_clash(a, b, gap):
            return (a[0] < b[2] + gap and a[2] > b[0] - gap and
                    a[1] < b[3] + gap and a[3] > b[1] - gap)

        # Sprite-vs-baked is deliberately NOT checked here: the bake reads this
        # same layout (tools/_layout.json) and keeps every pixel it paints clear
        # of the sprite art, pixel-exactly. Checking it here as well made the
        # two halves chase each other across re-bakes.
        accepted = []   # (kind, true rendered box) of everything kept so far
        moved = dropped = 0
        for _kind, _grp in (("stone", self.stones), ("tree", self.trees),
                            ("rock", self.rocks), ("fern", self.ferns),
                            ("mushroom", self.mushrooms)):
            keep = []
            for _d in _grp:
                _b = _sprite_box(_kind, _d)
                _thw = (_b[2] - _b[0]) / 2.0     # TRUE half width of the art

                def _fits(x, y):
                    # Only hard rules apply to decor that is already standing:
                    # the placement-time heuristics (camp clear zones, the 6%
                    # width safety) would relocate half the hand-built layout,
                    # including the standing-stone ring.
                    if not (40.0 < x < WORLD_WIDTH - 40.0
                            and 120.0 < y < WORLD_HEIGHT - 120.0):
                        return False
                    _solid = _col_radius(_kind, _d["style"], _d["h"]) + 70.0
                    if _in_exit_lane(x, y, _solid):
                        return False
                    if _kind == "tree":
                        _wd = _water_distance(x, y)
                        # Non-pond trees keep the full clearance from water.
                        # Pond trees may overhang the water but their trunk must
                        # stay on land (>= 40px), never standing in it.
                        if not _is_pond_tree(x, y) and _wd < TREE_WATER_TRIGGER:
                            return False
                        if _is_pond_tree(x, y) and _wd < 40.0:
                            return False
                    box = (x - _thw, y, x + _thw, y + _d["h"])
                    for akind, abox in accepted:
                        # The stone ring is designed as a ring; keep it.
                        if _kind == "stone" and akind == "stone":
                            continue
                        if _boxes_clash(box, abox, 10.0):
                            return False
                    return True

                _fitAt = None
                if _fits(_d["x"], _d["y"]):
                    _fitAt = (_d["x"], _d["y"])
                else:
                    for _rad in (70.0, 140.0, 210.0, 280.0, 350.0, 420.0, 490.0):
                        for _k in range(16):
                            _ang = _k * math.pi / 8.0
                            _nx = _d["x"] + math.cos(_ang) * _rad
                            _ny = _d["y"] + math.sin(_ang) * _rad
                            if _fits(_nx, _ny):
                                _fitAt = (_nx, _ny)
                                break
                        if _fitAt:
                            break
                if _fitAt is None:
                    dropped += 1
                    continue
                if (_fitAt[0], _fitAt[1]) != (_d["x"], _d["y"]):
                    _d["x"], _d["y"] = _fitAt
                    moved += 1
                _d["cr"] = _col_radius(_kind, _d["style"], _d["h"])
                accepted.append((_kind, _sprite_box(_kind, _d)))
                keep.append(_d)
            _grp[:] = keep
        if moved or dropped:
            print(f"[decor] deconflict: moved={moved} dropped={dropped}")

        # User-directed removal (2026-10-24): the single fern standing on the
        # baked dark border foliage at the very top of the map overlaps a baked
        # object. Drop the topmost fern (largest base y) so it no longer paints
        # over the border band. Only one sprite sits on that band, so this is a
        # single, targeted removal.
        if self.ferns:
            _top_fern = max(self.ferns, key=lambda fn: fn["y"])
            if _top_fern["y"] >= 1385.0:
                self.ferns.remove(_top_fern)

        # User-directed removal (2026-10-26): the two mushrooms stacked at the
        # eastern map edge, x~2552 with bases at y 317 and y 492, are painted
        # over the baked dark border foliage. Their whole footprint measures as
        # non-grass ground art at that latitude (the band runs from x~2503 to
        # the map edge), so both are dropped instead of re-sited. Runs after
        # every placement pass so nothing else on the map shifts.
        _bad_spots = ((2552.0, 316.7), (2552.7, 492.2))
        _before = len(self.mushrooms)
        self.mushrooms = [
            m for m in self.mushrooms
            if not any(abs(m["x"] - bx) < 2.0 and abs(m["y"] - by) < 2.0
                       for bx, by in _bad_spots)
        ]
        _cut = _before - len(self.mushrooms)
        if _cut != len(_bad_spots):
            print(f"[decor] edge-band mushrooms: expected to drop "
                  f"{len(_bad_spots)}, dropped {_cut} - re-run "
                  f"tools/qa_mush_score.py to confirm the coordinates")

        # Fallen logs are baked into the ground texture again (user decision
        # 2026-10-20): the sprite pass left inpainting traces around them.
        self.logs = []

    def _ensure_decor_sprites(self):
        """Lazily load decor textures and build one Sprite per decor entry."""
        if self._decor_ready:
            return
        if self._decor_tex is None:
            self._decor_tex = {}
            for kind, n in (("tree", 6), ("fern", 3), ("rock", 3), ("stone", 3), ("mushroom", 3)):
                self._decor_tex[kind] = [arcade.load_texture(str(DECOR_DIR / f"{kind}_{i}.png"))
                                         for i in range(n)]
        for tr in self.trees:
            tex = self._decor_tex["tree"][tr["style"]]
            sp = arcade.Sprite(tex, scale=tr["h"] / tex.height)
            sp.center_x = tr["x"]
            sp.center_y = tr["y"] + tr["h"] / 2
            tr["sp"] = sp
        for group, kind in ((self.rocks, "rock"), (self.ferns, "fern"),
                            (self.stones, "stone"), (self.mushrooms, "mushroom")):
            for d in group:
                tex = self._decor_tex[kind][d["style"]]
                sp = arcade.Sprite(tex, scale=d["h"] / tex.height)
                sp.center_x = d["x"]
                sp.center_y = d["y"] + d["h"] / 2
                d["sp"] = sp
        for lg in self.logs:
            tex = self._decor_tex["log"][lg["style"]]
            sp = arcade.Sprite(tex, scale=lg["h"] / tex.height)
            sp.center_x = lg["x"]
            sp.center_y = lg["y"] + lg["h"] / 2
            lg["sp"] = sp
        self._decor_ready = True

    def _ensure_ground(self):
        if self._ground_tex is None:
            self._ground_tex = arcade.load_texture(str(GROUND_PATH))
            self._ground_sprite = arcade.Sprite(self._ground_tex, scale=1.0)
            self._ground_sprite.center_x = WORLD_WIDTH / 2
            self._ground_sprite.center_y = WORLD_HEIGHT / 2
            self._ground_list = arcade.SpriteList()
            self._ground_list.append(self._ground_sprite)
            # Pond sprite: drawn over the baked pond to mask rim/contour defects.
            # World centre (1950, 460) = pond image centre (1950,1140) via
            # world_y = 1600 - img_y. Scale 1.0 keeps pixel-perfect alignment.
            self._pond_tex = arcade.load_texture(str(POND_SPRITE_PATH))
            self._pond_sprite = arcade.Sprite(self._pond_tex, scale=1.0)
            self._pond_sprite.center_x = 1950.0
            self._pond_sprite.center_y = 460.0
            self._pond_list = arcade.SpriteList()
            self._pond_list.append(self._pond_sprite)

    def _pond_textures(self):
        """Lazy-load the water loop; empty list keeps the static sprite."""
        if self._pond_texs is None:
            self._pond_texs = [
                arcade.load_texture(str(p))
                for p in sorted(POND_FRAMES_DIR.glob("frame_*.png"))
            ]
        return self._pond_texs

    def _draw_pond(self):
        texs = self._pond_textures()
        if not texs:
            self._pond_list.draw()
            return
        tex = texs[int(self.t * POND_FPS) % len(texs)]
        arcade.draw_texture_rect(
            tex, arcade.XYWH(POND_DRAW_X, POND_DRAW_Y, tex.width, tex.height)
        )

    # ===================================================================
    # CAMERA (follow the player, clamped to the world)
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
    # COLLISION (body-vs-base: the player's BODY cylinder vs a prop's base
    # cylinder, so widths can never overlap; the sort key uses the same
    # foot point, so occlusion and blocking always agree)
    # ===================================================================
    FOOT_RADIUS = 42.0   # player body half-width

    # Solid decor collections (each prop carries a precomputed "cr" radius).
    SOLID_KINDS = ("trees", "rocks", "stones")
    HEARTH_RADIUS = 92.0

    def _pond_push(self, px, py):
        """Keep the player's feet outside the water ellipse."""
        rx = POND_WATER_RX + self.FOOT_RADIUS
        ry = POND_WATER_RY + self.FOOT_RADIUS
        dx, dy = px - POND_DRAW_X, py - POND_DRAW_Y
        q = (dx / rx) ** 2 + (dy / ry) ** 2
        if q >= 1.0:
            return px, py
        if q < 1e-9:
            return POND_DRAW_X + rx, py
        s = 1.0 / math.sqrt(q)
        return POND_DRAW_X + dx * s, POND_DRAW_Y + dy * s

    def _solid_push(self, px, py, ox, oy, orad):
        """Push point (px,py) out of a circle at (ox,oy) with radius `orad`."""
        r = orad + self.FOOT_RADIUS
        dx, dy = px - ox, py - oy
        d = math.hypot(dx, dy)
        if d >= r:
            return px, py
        if d < 0.001:
            return ox + r, py
        return ox + dx / d * r, oy + dy / d * r

    def _resolve_collisions(self):
        """Keep the player's FEET out of the ROOT circles of solid props."""
        fx = self.player.x
        fy = self.player.y - FEET_OFFSET
        for kind in self.SOLID_KINDS:
            for p in getattr(self, kind):
                fx, fy = self._solid_push(fx, fy, p["x"], p["y"], p["cr"])
        # Fallen logs block along their length via a chain of circles.
        for lg in self.logs:
            for cx, cy, cr in lg["cols"]:
                fx, fy = self._solid_push(fx, fy, cx, cy, cr)
        # Camp hearth (fire pit + stone ring).
        fx, fy = self._solid_push(fx, fy, CAMP_X, CAMP_Y, self.HEARTH_RADIUS)
        # Pond water is the outermost solid constraint.
        fx, fy = self._pond_push(fx, fy)
        # Convert feet back to the sprite-center anchor, re-clamped to world.
        px = max(160.0, min(WORLD_WIDTH - 160.0, fx))
        py = max(160.0 + FEET_OFFSET, min(WORLD_HEIGHT - 160.0, fy + FEET_OFFSET))
        self.player.x, self.player.y = px, py

    # ===================================================================
    # UPDATE
    # ===================================================================
    def on_update(self, dt):
        if self.is_paused:
            return
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
        is_sprint = (arcade.key.LSHIFT in self.held_keys or arcade.key.RSHIFT in self.held_keys)

        bounds = (160, WORLD_WIDTH - 160, 200, WORLD_HEIGHT - 200)
        self.player.update(dt, move_x, move_y, dust_particles=self.dust, bounds=bounds)
        self._resolve_collisions()

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

        if self.camera:
            self._follow_camera()

    # ===================================================================
    # INPUT
    # ===================================================================
    def on_key_press(self, key, modifiers):
        if self.handle_pause_key(key):
            return
        self.held_keys.add(key)

    def on_key_release(self, key, modifiers):
        self.held_keys.discard(key)
        move_keys = {arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D,
                     arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT}
        if not (self.held_keys & move_keys):
            self.player.stop_footstep()

    def on_mouse_motion(self, x, y, dx=0, dy=0):
        self.handle_pause_mouse_motion(x, y)

    # ===================================================================
    # DRAW
    # ===================================================================
    def on_draw(self):
        self.clear(color=(24, 34, 24))
        self._ensure_ground()
        self.use_game_camera()  # world follow camera

        # Ground
        self._ground_list.draw()
        # Pond sprite (covers baked pond rim/contour defects). Drawn after ground
        # but before depth-sorted decor, so all props still layer on top of it,
        # matching the original baked-pond layering.
        self._draw_pond()

        # Depth-sorted world props + player (lower base y = nearer = drawn last)
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
        for lg in self.logs:
            items.append((lg["y"], lambda lg=lg: self._draw_log(lg)))
        items.append((CAMP_Y, self._draw_camp))
        # Player sorts by its FOOT (lowest point), matching the decor bases.
        items.append((self.player.y - FEET_OFFSET, self._draw_player))
        items.sort(key=lambda it: it[0], reverse=True)
        for _, fn in items:
            fn()

        # Embers + smoke above the hearth (world coords).
        for s in self.smoke:
            s.draw()
        for e in self.embers:
            e.draw()

        # Atmosphere in screen space (always covers the viewport).
        self.window.default_camera.use()
        self._draw_god_rays()
        self._draw_motes()
        self._draw_info_panel()
        self._draw_radar()
        self._draw_help()

        # Pause / exit menu (world virtual coords).
        self.use_game_camera()
        self.draw_pause_overlay()

    # ---- World prop draw helpers ----------------------------------------
    def _draw_tree(self, tr):
        self._ensure_decor_sprites()
        # Shadow centered above the base so its bottom edge sits ON the base
        # line: a shadow must not spill onto ground nearer than the tree.
        arcade.draw_ellipse_filled(tr["x"], tr["y"] + tr["h"] * 0.055, tr["h"] * 0.52, tr["h"] * 0.11,
                                   (18, 32, 18, 110))
        arcade.draw_sprite(tr["sp"])

    def _draw_rock(self, rk):
        self._ensure_decor_sprites()
        arcade.draw_sprite(rk["sp"])  # baked shadow in the sprite

    def _draw_log(self, lg):
        self._ensure_decor_sprites()
        arcade.draw_sprite(lg["sp"])  # baked shadow in the sprite

    def _draw_fern(self, fn):
        self._ensure_decor_sprites()
        arcade.draw_ellipse_filled(fn["x"], fn["y"] + fn["h"] * 0.07, fn["h"] * 0.72, fn["h"] * 0.14,
                                   (18, 32, 18, 80))
        arcade.draw_sprite(fn["sp"])

    def _draw_mushroom(self, mh):
        self._ensure_decor_sprites()
        pulse = 0.55 + 0.45 * math.sin(self.t * 2.2 + mh["phase"])
        glow_r = mh["h"] * (0.40 + 0.12 * pulse)
        arcade.draw_circle_filled(mh["x"], mh["y"] + mh["h"] * 0.45, glow_r,
                                  (150, 240, 195, int(30 * pulse) + 12))
        arcade.draw_sprite(mh["sp"])

    def _draw_stone(self, st):
        self._ensure_decor_sprites()
        pulse = 0.55 + 0.45 * math.sin(self.t * 2.0 + st["phase"])
        arcade.draw_circle_filled(st["x"], st["y"] + st["h"] * 0.45, st["h"] * (0.30 + 0.08 * pulse),
                                  (140, 235, 170, int(26 * pulse) + 10))
        arcade.draw_sprite(st["sp"])

    def _fire_textures(self):
        """Lazy-load the 41 campfire frames (black background already keyed)."""
        if self._fire_texs is None:
            self._fire_texs = [
                arcade.load_texture(str(p))
                for p in sorted(CAMPFIRE_DIR.glob("frame_*.png"))
            ]
        return self._fire_texs

    def _draw_camp(self):
        cx, cy = CAMP_X, CAMP_Y
        # Warm light spill lying flat on the ground under the logs, centred on
        # the hearth's own ground line. Static: the GIF already animates the
        # fire, and anything breathing or resizing here reads as a second,
        # out-of-sync animation.
        arcade.draw_ellipse_filled(cx, cy + 8, 150, 38, (255, 120, 40, 9))
        # The painted animated fire: the sprite carries its own log pile and
        # stone ring, so the old procedural stones/logs/flame circles are gone.
        texs = self._fire_textures()
        if texs:
            tex = texs[int(self.t * CAMPFIRE_FPS) % len(texs)]
            w = CAMPFIRE_WORLD_WIDTH
            h = w * (tex.height / tex.width)
            base = cy + CAMPFIRE_BASE_LIFT
            arcade.draw_texture_rect(tex, arcade.XYWH(cx, base + h / 2.0, w, h))

    def _draw_player(self):
        self.player.draw(self.aspect_ratio_correction)
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
            top_y = h + 20
            bot_y = h * 0.32
            arcade.draw_polygon_filled([
                (rx_top - rw / 2, top_y),
                (rx_top + rw / 2, top_y),
                (rx_top + rw / 2 + slant, bot_y),
                (rx_top - rw / 2 + slant, bot_y),
            ], (255, 248, 205, a))

    def _draw_motes(self):
        for m in self.motes:
            m.draw()

    # ---- UI ---------------------------------------------------------------
    def _draw_info_panel(self):
        w, h = self.window.width, self.window.height
        pw, ph = 320, 104
        px, py = 16, h - 16 - ph
        arcade.draw_rect_filled(arcade.XYWH(px + pw / 2, py + ph / 2, pw, ph), COLOR_PANEL_BG)
        arcade.draw_rect_outline(arcade.XYWH(px + pw / 2, py + ph / 2, pw, ph), COLOR_PANEL_BORDER, 1.5)
        if self.player.is_moving:
            state = "Sprinting" if (arcade.key.LSHIFT in self.held_keys or arcade.key.RSHIFT in self.held_keys) else "Walking"
        else:
            state = "Idle"
        face = {"down": "South", "up": "North", "left": "West", "right": "East"}[self.player.facing]
        self._label("title", "PREHISTORIC FOREST", 15, (255, 235, 175), px + 16, py + ph - 22, bold=True)
        self._label("state", f"State: {state}", 12, (225, 225, 225), px + 16, py + ph - 48)
        self._label("face", f"Facing: {face}", 12, (200, 220, 200), px + 16, py + ph - 70)
        self._label("pos", f"Pos: ({int(self.player.x)}, {int(self.player.y)})", 12, (190, 205, 190), px + 16, py + ph - 92)

    def _draw_radar(self):
        w, h = self.window.width, self.window.height
        size = 140
        rx, ry = w - 16 - size, h - 16 - size
        arcade.draw_rect_filled(arcade.XYWH(rx + size / 2, ry + size / 2, size, size), (20, 40, 26, 205))
        arcade.draw_rect_outline(arcade.XYWH(rx + size / 2, ry + size / 2, size, size), (150, 175, 95, 150), 1.5)
        camp_px = rx + (CAMP_X / WORLD_WIDTH) * size
        camp_py = ry + (CAMP_Y / WORLD_HEIGHT) * size
        arcade.draw_circle_filled(camp_px, camp_py, 4, (255, 140, 30))
        p_px = rx + (self.player.x / WORLD_WIDTH) * size
        p_py = ry + (self.player.y / WORLD_HEIGHT) * size
        glow = int(190 + 65 * math.sin(self.t * 8.0))
        arcade.draw_circle_filled(p_px, p_py, 4.5, (120, 220, 140, glow))

    def _draw_help(self):
        w, h = self.window.width, self.window.height
        bw, bh = 760, 36
        bx, by = w / 2, 26
        arcade.draw_rect_filled(arcade.XYWH(bx, by, bw, bh), COLOR_HELP_BG)
        self._label("help",
                    "[WASD / Arrows] Move   |   [Shift] Sprint   |   [ESC] Pause",
                    13, COLOR_HELP_TXT, bx, by, bold=True)

    # ---- Lazy text factory ----------------------------------------------
    def _text_obj(self, key, text, size, color, bold=False):
        if key not in self._text:
            self._text[key] = arcade.Text(
                text, 0, 0, color=color,
                font_name=("Segoe UI", "Calibri", "Arial"),
                font_size=size, bold=bold, anchor_x="left", anchor_y="center",
            )
        else:
            obj = self._text[key]
            obj.text = text
            obj.color = color
            obj.font_size = size
            obj.bold = bold
        return self._text[key]

    def _label(self, key, text, size, color, x, y, bold=False):
        obj = self._text_obj(key, text, size, color, bold)
        obj.x = x
        obj.y = y
        obj.draw()
