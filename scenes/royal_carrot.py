"""Consistent carrot slices and dice reuse one sprite throughout preparation."""
import math
import random
import arcade
from .royal_onion import OnionSlices


class CarrotSlices(OnionSlices):
    def __init__(self, texture):
        self.texture = texture
        self.tiles = {}
        self.pile = []
        rng = random.Random(1911)
        for row in range(8):
            for col in range(20):
                l = 140 + col * 38
                t = 100 + row * 28
                # Skip transparent tip/edge cells so the pile has real food.
                if texture.image.getpixel((l + 19, t + 14))[3] < 180:
                    continue
                a = rng.random() * math.tau
                r = math.sqrt(rng.random())
                self.pile.append((l, t, math.cos(a) * 190 * r, math.sin(a) * 90 * r, rng.uniform(-90, 90)))
        self.pile.sort(key=lambda p: -p[3])

    def draw_tip_discard(self, count, center=(740, 400), scale=0.30, stroke=None, corner_t=None):
        if count < 1:
            return
        # Tight opaque crop for carrot head/tip: (100, 148, 140, 298), center=(120, 223)
        tex = self.tile(100, 148, 140, 298)
        w, h = 40 * scale, 150 * scale
        base_x = center[0] + (120 - 520) * scale
        base_y = center[1] + (215 - 223) * scale
        orig_x = base_x - 14
        orig_y = base_y
        dest_x, dest_y = 990, 455  # Top-right corner ON the wooden cutting board

        # Once the head-finishing cut begins, glide the tip to the top-right corner
        # and keep it there. corner_t is a one-shot clock captured at that cut's
        # start, so the motion runs through the wind-up and later cuts can't re-trigger it.
        if corner_t is not None:
            t = min(1.0, max(0.0, corner_t / 0.22))
            ease = t * t * (3 - 2 * t)
            px = orig_x + (dest_x - orig_x) * ease
            py = orig_y + (dest_y - orig_y) * ease
            arcade.draw_texture_rect(tex, arcade.XYWH(px, py, w, h), angle=15 * ease)
            return

        if count == 1:
            sep = min(1.0, max(0.0, (stroke.get('time', 0.4) - 0.16) / 0.14)) if stroke is not None else 1.0
            s_ease = sep * sep * (3 - 2 * sep)
            arcade.draw_texture_rect(tex, arcade.XYWH(base_x - 14 * s_ease, orig_y, w, h))
            return

        # count >= 2 without a corner trigger (e.g. shown while prepping the other
        # vegetable): already set aside at the corner.
        arcade.draw_texture_rect(tex, arcade.XYWH(dest_x, dest_y, w, h), angle=15)

    def draw(self, count, angle=0, center=(740, 390), scale=0.30, pile_progress=1, group2_progress=1.0, stroke=None, corner_t=None):
        p = max(0, min(1, pile_progress))
        ease = p * p * (3 - 2 * p)
        if count >= 10:
            for l, t, tx, ty, rotation in self.pile:
                sx = t + 14 - 215
                sy = l + 19 - 520
                x = (sx + (tx - sx) * ease) * scale
                y = (sy + (ty - sy) * ease) * scale
                arcade.draw_texture_rect(
                    self.tile(l, t, l + 37, t + 27),
                    arcade.XYWH(center[0] + x, center[1] + y + math.sin(p * math.pi) * 5, 37 * scale, 27 * scale),
                    angle=-90 + rotation * ease
                )
            self.draw_tip_discard(count, center=center, scale=scale, stroke=stroke, corner_t=corner_t)
            return

        half_gap = 1.5 / scale

        # Phase 1: Crosswise cuts (cuts 0 to 6)
        # cut 1: tip at 140
        # cuts 2..6: divide body into 6 segments [140..270..400..530..660..790..1000]
        if count < 6 or angle < 1:
            all_cuts = [140, 270, 400, 530, 660, 790]
            cur_cuts = all_cuts[:count]
            xs = [140] if count >= 1 else [0]
            for c in cur_cuts:
                if c not in xs:
                    xs.append(c)
            xs.append(1000)
            xs = sorted(xs)

            for xi, (left, right) in enumerate(zip(xs, xs[1:])):
                l = left + (half_gap if xi else 0)
                r = right - (half_gap if xi < len(xs) - 1 else 0)
                if r <= l:
                    continue
                x = ((l + r) / 2 - 520) * scale
                y = (215 - 210) * scale
                arcade.draw_texture_rect(
                    self.tile(round(l), 0, round(r), 420),
                    arcade.XYWH(center[0] + x, center[1] + y, (r - l) * scale, 420 * scale)
                )

            self.draw_tip_discard(count, center=center, scale=scale, stroke=stroke, corner_t=corner_t)
            return

        # Phase 2 & 3: Sequential two halves (2 cuts each -> total 10 cuts)
        self.draw_tip_discard(count, center=center, scale=scale, stroke=stroke, corner_t=corner_t)

        prog = min(1.0, max(0.0, angle / 90.0))
        turn_ease = prog * prog * (3 - 2 * prog)
        rad = math.radians(90 * turn_ease)
        co, si = math.cos(rad), math.sin(rad)

        # Equal-thirds cuts based on actual opaque carrot thickness per half:
        # First half [100..330] -> cuts at 177, 253 (width ~77px per column)
        # Second half tapered mid [154..276] -> cuts at 195, 235 (width ~40px per column)
        ys_all_1 = [177, 253]
        ys_all_2 = [195, 235]

        # --- FIRST HALF: Segs 1, 2, 3 ([140, 270, 400, 530]) ---
        xs_group1 = [140, 270, 400, 530]
        g1_cuts = max(0, min(2, count - 6))
        ys_group1 = sorted([0, 420] + ys_all_1[:g1_cuts])

        if count < 8:
            g1_cx = center[0]
            g1_cy = center[1]
        else:
            # Push diced first half neatly inside the board (top-middle-right, never floating!)
            g2_ease = max(0.0, min(1.0, group2_progress))
            shift_ease = g2_ease * g2_ease * (3 - 2 * g2_ease)
            g1_cx = center[0] + 125 * shift_ease
            g1_cy = center[1] + 35 * shift_ease

        for xi, (left, right) in enumerate(zip(xs_group1, xs_group1[1:])):
            for yi, (top, bottom) in enumerate(zip(ys_group1, ys_group1[1:])):
                l = left + (half_gap if xi else 0)
                r = right - (half_gap if xi < len(xs_group1) - 1 else 0)
                t = top + (half_gap if yi else 0)
                b = bottom - (half_gap if yi < len(ys_group1) - 1 else 0)
                if r <= l or b <= t:
                    continue
                tile = self.tile(round(l), round(t), round(r), round(b))
                local_x = ((l + r) / 2 - 335) * scale
                local_y = (210 - (t + b) / 2) * scale
                rx = local_x * co - local_y * si
                ry = local_x * si + local_y * co
                arcade.draw_texture_rect(
                    tile,
                    arcade.XYWH(g1_cx + rx, g1_cy + ry, (r - l) * scale, (b - t) * scale),
                    angle=-90 * turn_ease
                )

        # --- SECOND HALF: Segs 4, 5, 6 ([530, 660, 790, 900]) ---
        xs_group2 = [530, 660, 790, 900]
        g2_cuts = max(0, min(2, count - 8))
        ys_group2 = sorted([0, 420] + ys_all_2[:g2_cuts])

        s2_wait_x = 565
        s2_wait_y = 355  # Rests firmly on the wooden board on the left side
        s2_orig_x = center[0] + ((530 + 900) / 2 - 520) * scale

        if count < 8:
            cur_s2_x = s2_orig_x + (s2_wait_x - s2_orig_x) * turn_ease
            cur_s2_y = center[1] + (s2_wait_y - center[1]) * turn_ease
            for xi, (left, right) in enumerate(zip(xs_group2, xs_group2[1:])):
                l = left + (half_gap if xi else 0)
                r = right - (half_gap if xi < len(xs_group2) - 1 else 0)
                if r <= l:
                    continue
                tile = self.tile(round(l), 0, round(r), 420)
                seg_x = cur_s2_x + ((l + r) / 2 - 715) * scale
                arcade.draw_texture_rect(
                    tile,
                    arcade.XYWH(seg_x, cur_s2_y, (r - l) * scale, 420 * scale),
                    angle=0
                )
        else:
            g2_ease = max(0.0, min(1.0, group2_progress))
            shift_ease = g2_ease * g2_ease * (3 - 2 * g2_ease)
            g2_cx = s2_wait_x + (center[0] - s2_wait_x) * shift_ease
            g2_cy = s2_wait_y + (center[1] - s2_wait_y) * shift_ease
            g2_angle = -90.0 * shift_ease

            g2_rad = math.radians(-g2_angle)
            g2_co, g2_si = math.cos(g2_rad), math.sin(g2_rad)

            for xi, (left, right) in enumerate(zip(xs_group2, xs_group2[1:])):
                for yi, (top, bottom) in enumerate(zip(ys_group2, ys_group2[1:])):
                    l = left + (half_gap if xi else 0)
                    r = right - (half_gap if xi < len(xs_group2) - 1 else 0)
                    t = top + (half_gap if yi else 0)
                    b = bottom - (half_gap if yi < len(ys_group2) - 1 else 0)
                    if r <= l or b <= t:
                        continue
                    tile = self.tile(round(l), round(t), round(r), round(b))
                    local_x = ((l + r) / 2 - 715) * scale
                    local_y = (210 - (t + b) / 2) * scale
                    rx = local_x * g2_co - local_y * g2_si
                    ry = local_x * g2_si + local_y * g2_co
                    arcade.draw_texture_rect(
                        tile,
                        arcade.XYWH(g2_cx + rx, g2_cy + ry, (r - l) * scale, (b - t) * scale),
                        angle=g2_angle
                    )
