"""B03 opening: physical arrival above the prehistoric forest.

Features high-tech holographic teleportation effects covering around the
protagonist: sci-fi floor pedestal, cylindrical cyber shield panels, mid-air
holographic rings, vertical ascension beams, and 3D depth-layered particles.
Dissipation is performed strictly top-to-bottom (downward wipe / collapse),
retracting the energy field downwards from the sky into the ground.
All effect positions remain strictly anchored to the protagonist's normalized
coordinates with full 16:10 / 16:9 adaptive preservation.
"""
import math
import random

import arcade

from core.base_view import BaseGameView
from core.constants import ASSETS_DIR
from core.audio import AudioManager
from scenes.b03_atmosphere import distance_texture, shade_color
from arcade.types.rect import LRBT


class B03ArrivalView(BaseGameView):
    DURATION = 3.0

    def __init__(self, truth_understood=False, on_return=None):
        super().__init__()
        self.truth_understood = truth_understood
        self.on_return = on_return
        folder = ASSETS_DIR / 'endings' / 'bad_ending' / 'b03_arrival'
        self.full = arcade.load_texture(folder / 'arrival_16x10.png')
        self.wide = arcade.load_texture(folder / 'arrival_16x9.png')
        crop_path = folder / 'character_occlusion_crop.png'
        if crop_path.exists():
            self.character = arcade.load_texture(crop_path)
            self.char_cropped = True
        else:
            self.character = arcade.load_texture(folder / 'character_occlusion.png')
            self.char_cropped = False
        self.pov_full = arcade.load_texture(folder / 'pov_forest_16x10.png')
        self.pov_wide = arcade.load_texture(folder / 'pov_forest_16x9.png')
        self.dinosaur = distance_texture(arcade.load_texture(folder / 'distant_dinosaur.png'),far=True)
        self.leaf_patch = arcade.load_texture(folder / 'foreground_leaves.png')
        self.ambience = arcade.load_sound(ASSETS_DIR / 'sounds' / 'b03_forest_air.wav')
        self.ambient_player = None

        # Holographic cyber panels layout (Image 1 sci-fi cylindrical barrier)
        rng = random.Random(303)
        self.cyber_panels = []
        num_panels = 18
        for i in range(num_panels):
            base_angle = (i * 2 * math.pi / num_panels) + rng.uniform(-0.06, 0.06)
            ang_w = rng.uniform(0.24, 0.36)
            h_base = rng.choice([0, 15, 30, 55, 90])
            h_top = rng.choice([210, 270, 330, 400, 470, 530])
            tone = rng.choice([
                (25, 195, 255),
                (0, 230, 255),
                (70, 240, 255),
                (140, 245, 255),
                (0, 165, 240)
            ])
            has_stripes = rng.random() < 0.65
            self.cyber_panels.append({
                'angle': base_angle,
                'ang_w': ang_w,
                'h_base': h_base,
                'h_top': h_top,
                'tone': tone,
                'alpha': rng.uniform(45, 80),
                'has_stripes': has_stripes,
                'rot_speed': rng.uniform(0.20, 0.30)
            })

        self.restart()

    def restart(self):
        self.elapsed = 0.0
        self.residual_clock = 0.0
        self.residual = []
        self.residual_rng = random.Random(304)
        rng = random.Random(303)

        # Full-height ascending cyber motes and sparks (Image 2)
        self.particles = []
        for _ in range(160):
            ang = rng.uniform(0, math.tau)
            r = rng.uniform(45, 165)
            h = rng.uniform(0, 600)
            spd = rng.uniform(90, 210)
            life = rng.uniform(1.8, 3.4)
            size = rng.uniform(1.6, 3.8)
            phase = rng.uniform(0, math.tau)
            self.particles.append([ang, r, h, spd, life, size, phase])

    def on_show_view(self):
        super().on_show_view()
        self.clean_texture_atlas()
        AudioManager().play('b03_arrival_warp', volume_scale=.65)
        self.ambient_player = self.ambience.play(volume=0, loop=True)

    def on_hide_view(self):
        if self.ambient_player:
            arcade.stop_sound(self.ambient_player)
            self.ambient_player = None

    def on_update(self, dt):
        if self.ambient_player:
            self.ambient_player.volume = 0 if self.is_paused else .24*min(1., self.elapsed/3)
        if not self.is_paused:
            dt = min(dt, .1)
            self.elapsed += dt

            # Update lingering residual sparks at boots
            self.residual = [(*p[:5], p[5]+dt) for p in self.residual
                             if p[5]+dt < p[4]]
            self.residual_clock += dt
            if self.elapsed < 3.8:
                while self.residual_clock >= .12:
                    self.residual_clock -= .12
                    rng = self.residual_rng
                    angle = rng.uniform(0, math.tau)
                    radius = rng.uniform(120, 155)
                    self.residual.append((math.cos(angle)*radius,
                                          math.sin(angle)*radius*.28, rng.uniform(-3, 3),
                                          rng.uniform(13, 23), rng.uniform(2.0, 2.8), 0.0))

    def on_draw(self):
        self.clear((9, 20, 18))
        w, h = self.window.width, self.window.height
        if not hasattr(self, 'pixel_camera'):
            self.pixel_camera = arcade.camera.Camera2D(window=self.window)
        self.pixel_camera.viewport = LRBT(0, w, 0, h)
        self.pixel_camera.projection = LRBT(-w/2, w/2, -h/2, h/2)
        self.pixel_camera.position = (w/2, h/2)
        self.pixel_camera.use()

        tex = self.full if abs(w/h-1.6) < abs(w/h-16/9) else self.wide
        if self.elapsed >= 4.4:
            self._draw_pov(w, h, 255)
            self.draw_pause_overlay()
            return

        # Uniform cover for arbitrary windows. Never stretch either image.
        progress = max(0., min(1., self.elapsed-3.0))
        ease = progress*progress*(3-2*progress)
        scale = max(w/tex.width, h/tex.height)*(1+.05*ease)
        dw, dh = tex.width*scale, tex.height*scale
        left, bottom = (w-dw)/2, (h-dh)/2
        arcade.draw_texture_rect(tex, arcade.XYWH(w/2, h/2, dw, dh))

        # Anchor coordinates to protagonist
        crop_y = (self.full.height-tex.height)/2
        x = left + self.full.width*.235*scale
        y = bottom + (self.full.height*.235-crop_y)*scale
        unit = self.full.width*scale/1584
        t = self.elapsed

        # Top-down disappearance (wipe ceiling sweeping downwards from top to bottom)
        # Full arrival hold until t=0.8s, then smoothly descends to ground at t=2.8s
        wipe_start = 0.8
        wipe_end = 2.8
        if t <= wipe_start:
            wipe_prog = 0.0
        elif t >= wipe_end:
            wipe_prog = 1.0
        else:
            wipe_prog = (t - wipe_start) / (wipe_end - wipe_start)

        ease_wipe = wipe_prog * wipe_prog * (3 - 2 * wipe_prog)
        ceiling_h = 750.0 * (1.0 - ease_wipe)
        energy = max(0.0, 1.0 - wipe_prog ** 1.6)

        # 1. Sci-fi floor pedestal on ground (persists until wipe reaches ground)
        if t <= 2.0:
            pedestal_energy = 1.0
        elif t >= wipe_end + 0.1:
            pedestal_energy = 0.0
        else:
            pedestal_energy = max(0.0, 1.0 - (t - 2.0) / (wipe_end + 0.1 - 2.0)) ** 1.4

        self._draw_floor_pedestal(x, y, unit, pedestal_energy, t)

        # 2. Behind layers (central energy beam, back of rings, back cyber panels, back sparks)
        self._draw_cyber_cage(x, y, unit, energy, ceiling_h, t, behind=True)

        # 3. Protagonist character occlusion layer
        if getattr(self, 'char_cropped', False):
            # Tightly cropped 315x626 character texture within original 1584x990 coordinate plane
            char_w = 315 * scale
            char_h = 626 * scale
            char_cx = left + 349.5 * scale
            char_cy = bottom + (528.0 - crop_y) * scale
            arcade.draw_texture_rect(self.character, arcade.XYWH(char_cx, char_cy, char_w, char_h))
        else:
            arcade.draw_texture_rect(self.character, arcade.XYWH(
                left+self.full.width*scale/2,
                bottom+(self.full.height/2-crop_y)*scale,
                self.full.width*scale, self.full.height*scale))

        # 4. Front layers (front cyber panels, front of rings, front beams, front sparks)
        self._draw_cyber_cage(x, y, unit, energy, ceiling_h, t, behind=False)

        # Initial arrival flash fades quickly
        flash = int(145*max(0., 1-t/.85)**2)
        if flash:
            arcade.draw_rect_filled(arcade.XYWH(w/2, h/2, w, h), (170, 240, 255, flash))

        if self.elapsed > 4.0:
            self._draw_pov(w, h, int(255*min(1., (self.elapsed-4.0)/.4)))
        self.draw_pause_overlay()

    def _draw_floor_pedestal(self, x, y, unit, energy, t):
        if energy <= 0:
            return
        flat = 0.32

        # Layered soft glowing pool
        for r in range(150, 10, -15):
            alpha = int(15 * energy * (1 - r/165))
            arcade.draw_ellipse_filled(x, y, r*2*unit, r*flat*2*unit, (0, 210, 255, alpha))

        # Bright inner core
        arcade.draw_ellipse_filled(x, y, 75*unit, 75*flat*unit, (140, 245, 255, int(135*energy)))
        arcade.draw_ellipse_filled(x, y, 36*unit, 36*flat*unit, (230, 255, 255, int(195*energy)))

        # Outer tech ring with compass triangles (Image 1)
        r_outer = 186 * unit
        arcade.draw_ellipse_outline(x, y, r_outer*2, r_outer*flat*2, (0, 225, 255, int(145*energy)), max(1, 2*unit))
        for deg in (0, 90, 180, 270):
            rad = math.radians(deg)
            cx = x + math.cos(rad) * r_outer
            cy = y + math.sin(rad) * r_outer * flat
            dx = math.cos(rad) * 10 * unit
            dy = math.sin(rad) * 10 * unit * flat
            nx = -math.sin(rad) * 7 * unit
            ny = math.cos(rad) * 7 * unit * flat
            p1 = (cx + dx, cy + dy)
            p2 = (cx - dx*0.4 + nx, cy - dy*0.4 + ny)
            p3 = (cx - dx*0.4 - nx, cy - dy*0.4 - ny)
            arcade.draw_polygon_filled([p1, p2, p3], (80, 240, 255, int(205*energy)))

        # Segmented rotating cyber arc ring
        rot_deg = (t * 22) % 360
        for i in range(4):
            s_deg = (rot_deg + i * 90) % 360
            e_deg = (s_deg + 65) % 360
            if s_deg < e_deg:
                arcade.draw_arc_outline(x, y, 160*unit*2, 160*unit*flat*2, (80, 240, 255, int(180*energy)), s_deg, e_deg, max(1, 2*unit))
            else:
                arcade.draw_arc_outline(x, y, 160*unit*2, 160*unit*flat*2, (80, 240, 255, int(180*energy)), s_deg, 360, max(1, 2*unit))
                arcade.draw_arc_outline(x, y, 160*unit*2, 160*unit*flat*2, (80, 240, 255, int(180*energy)), 0, e_deg, max(1, 2*unit))

        # Thin inner concentric tech circles
        for r_inner in (132, 98):
            arcade.draw_ellipse_outline(x, y, r_inner*unit*2, r_inner*unit*flat*2, (0, 205, 255, int(95*energy)), max(1, 1.2*unit))

        # Expanding ripple shockwaves
        for delay in (0., 0.35, 0.75):
            age = (t - delay) % 1.5
            if age >= 0:
                rw = (40 + age * 115) * unit
                a_wave = int(120 * energy * (1 - age/1.5)**2)
                if a_wave > 0:
                    arcade.draw_ellipse_outline(x, y, rw*2, rw*flat*2, (100, 240, 255, a_wave), max(1, 1.8*unit))

    def _draw_cyber_cage(self, x, y, unit, energy, ceiling_h, t, behind):
        if energy <= 0 or ceiling_h <= 0:
            self._draw_residual_sparks(x, y, unit, behind)
            return

        R = 154 * unit
        flat = 0.32

        # Central vertical energy beam (retracts downwards as ceiling_h drops)
        if behind:
            beam_h = max(0.0, min(670.0, ceiling_h)) * unit
            if beam_h > 0:
                arcade.draw_polygon_filled([
                    (x - 22*unit, y), (x + 22*unit, y),
                    (x + 12*unit, y + beam_h), (x - 12*unit, y + beam_h)
                ], (0, 185, 255, int(45*energy)))
                arcade.draw_polygon_filled([
                    (x - 6*unit, y), (x + 6*unit, y),
                    (x + 2*unit, y + beam_h), (x - 2*unit, y + beam_h)
                ], (150, 245, 255, int(160*energy)))
                arcade.draw_line(x, y, x, y + beam_h, (240, 255, 255, int(235*energy)), max(1, 2*unit))

        # Mid-air Horizontal Holographic Rings (Image 1 & 2)
        # Ring 1: Waist level (h=225)
        # Ring 2: Chest level (h=395)
        # Each ring naturally vanishes as the top-to-bottom wipe sweeps past its height
        for h_ring, r_ring in [(225, 152), (395, 142)]:
            ring_factor = max(0.0, min(1.0, (ceiling_h - (h_ring - 25)) / 60.0))
            if ring_factor <= 0:
                continue
            ring_energy = energy * ring_factor
            ry = y + h_ring * unit
            rw = r_ring * unit
            arc_s = 0 if behind else 180
            arc_e = 180 if behind else 360
            arcade.draw_arc_outline(x, ry, rw*2, rw*flat*2, (0, 210, 255, int(75*ring_energy)), arc_s, arc_e, max(1, 3.5*unit))
            arcade.draw_arc_outline(x, ry, rw*2, rw*flat*2, (180, 250, 255, int(195*ring_energy)), arc_s, arc_e, max(1, 1.5*unit))
            for tick_i in range(8):
                deg = ((t * 40) + tick_i * 45) % 360
                in_segment = (0 <= deg < 180) if behind else (180 <= deg < 360)
                if in_segment:
                    rad = math.radians(deg)
                    tx = x + math.cos(rad) * rw
                    ty = ry + math.sin(rad) * rw * flat
                    arcade.draw_line(tx, ty - 6*unit, tx, ty + 6*unit, (220, 255, 255, int(225*ring_energy)), max(1, 1.8*unit))

        # Active dematerialization cutting plane ring at the top-down wipe boundary
        if 25 < ceiling_h < 680:
            slice_y = y + ceiling_h * unit
            slice_r = R * (0.97 + 0.05 * math.sin(t * 16))
            slice_alpha = int(230 * min(1.0, (700 - ceiling_h)/70) * min(1.0, ceiling_h/35))
            if slice_alpha > 0:
                arc_s = 0 if behind else 180
                arc_e = 180 if behind else 360
                arcade.draw_arc_outline(x, slice_y, slice_r * 2, slice_r * flat * 2,
                                        (0, 220, 255, int(slice_alpha * 0.4)), arc_s, arc_e, max(1, 3.5 * unit))
                arcade.draw_arc_outline(x, slice_y, slice_r * 2, slice_r * flat * 2,
                                        (230, 255, 255, slice_alpha), arc_s, arc_e, max(1, 1.8 * unit))

        # Cylindrical Holographic Data Panels (Image 1 Cyber Shield)
        # Sliced and retracted downwards as ceiling_h drops
        for p in self.cyber_panels:
            if ceiling_h <= p['h_base']:
                continue

            cur_ang = (p['angle'] + t * p['rot_speed']) % math.tau
            is_behind = math.sin(cur_ang) > 0
            if is_behind != behind:
                continue

            eff_top = min(p['h_top'], ceiling_h)
            if eff_top <= p['h_base'] + 2:
                continue

            ang_a = cur_ang - p['ang_w'] * 0.5
            ang_b = cur_ang + p['ang_w'] * 0.5

            xa = x + math.cos(ang_a) * R
            ya_base = y + math.sin(ang_a) * R * flat + p['h_base'] * unit
            ya_top = ya_base + (eff_top - p['h_base']) * unit

            xb = x + math.cos(ang_b) * R
            yb_base = y + math.sin(ang_b) * R * flat + p['h_base'] * unit
            yb_top = yb_base + (eff_top - p['h_base']) * unit

            depth_factor = 0.72 if behind else 1.0
            r, g, b = p['tone']
            p_alpha = int(p['alpha'] * energy * depth_factor)
            border_alpha = int(min(255, (p['alpha'] + 70) * energy * depth_factor))

            quad = [(xa, ya_base), (xb, yb_base), (xb, yb_top), (xa, ya_top)]
            arcade.draw_polygon_filled(quad, (r, g, b, p_alpha))

            # Border highlights: top, bottom, and side frame
            top_color = (240, 255, 255, border_alpha) if eff_top < p['h_top'] else (180, 245, 255, border_alpha)
            top_width = max(1, 2.2 * unit) if eff_top < p['h_top'] else max(1, 1.5 * unit)
            arcade.draw_line(xa, ya_top, xb, yb_top, top_color, top_width)
            arcade.draw_line(xa, ya_base, xb, yb_base, (180, 245, 255, border_alpha), max(1, 1.5*unit))
            arcade.draw_line(xa, ya_base, xa, ya_top, (120, 235, 255, int(border_alpha * 0.6)), max(1, 1.0*unit))
            arcade.draw_line(xb, yb_base, xb, yb_top, (120, 235, 255, int(border_alpha * 0.6)), max(1, 1.0*unit))

            # Inner HUD stripes/data ticks
            if p['has_stripes'] and (eff_top - p['h_base']) > 50:
                num_stripes = 3
                for s in range(1, num_stripes + 1):
                    frac = s / (num_stripes + 1)
                    sy_a = ya_base + (ya_top - ya_base) * frac
                    sy_b = yb_base + (yb_top - yb_base) * frac
                    arcade.draw_line(xa, sy_a, xb, sy_b, (200, 250, 255, int(border_alpha * 0.45)), max(1, 1.0*unit))

        # Vertical Laser Beams / Light Streaks along perimeter (retract downwards)
        num_streaks = 14
        for i in range(num_streaks):
            beam_ang = (i * math.tau / num_streaks + t * 0.15) % math.tau
            is_behind = math.sin(beam_ang) > 0
            if is_behind != behind:
                continue
            bx = x + math.cos(beam_ang) * (R + 4*unit)
            by_base = y + math.sin(beam_ang) * (R + 4*unit) * flat
            raw_len = 280 + 190 * math.sin(i * 1.7 + t * 3.2)
            base_offset_u = math.sin(beam_ang) * (R + 4*unit) * flat / unit
            eff_len = max(0.0, min(raw_len, ceiling_h - base_offset_u)) * unit
            if eff_len > 0:
                arcade.draw_line(bx, by_base, bx, by_base + eff_len, (0, 215, 255, int(75*energy)), max(1, 3.5*unit))
                arcade.draw_line(bx, by_base, bx, by_base + eff_len, (200, 250, 255, int(185*energy)), max(1, 1.2*unit))

        # Ascending cyber particles & data motes (dissolves above ceiling_h)
        for p in self.particles:
            ang, rad_base, h_start, spd, life, sz, phase = p
            cur_h = (h_start + t * spd) % 640
            if cur_h > ceiling_h + 15:
                continue
            cur_ang = (ang + t * 0.4) % math.tau
            is_behind = math.sin(cur_ang) > 0
            if is_behind != behind:
                continue
            px = x + math.cos(cur_ang) * (rad_base * unit)
            py = y + math.sin(cur_ang) * (rad_base * unit) * flat + cur_h * unit
            wipe_fade = min(1.0, max(0.0, (ceiling_h + 15 - cur_h) / 45.0))
            p_alpha = int(220 * energy * wipe_fade * (1 - cur_h / 650)**0.8)
            if p_alpha > 0:
                pr = sz * unit
                arcade.draw_circle_filled(px, py, pr*3, (0, 200, 255, int(p_alpha * 0.2)))
                arcade.draw_circle_filled(px, py, pr, (180, 250, 255, p_alpha))

        # Lingering residual sparks around boots
        self._draw_residual_sparks(x, y, unit, behind)

    def _draw_residual_sparks(self, x, y, unit, behind):
        sparks = []
        for px, py, vx, vy, life, age in self.residual:
            if (py >= 0) == behind:
                fade = min(1., age/.2)*(1-age/life)**1.2
                sparks.append((px+vx*age+math.sin(age*2+px)*3,
                               py+vy*age, 2.4, int(220*fade)))
        for px, py, size, alpha in sparks:
            sx, sy = x+px*unit, y+py*unit
            r = size*unit
            arcade.draw_circle_filled(sx, sy, r*3.5, (35, 205, 255, int(alpha*.14)))
            arcade.draw_circle_filled(sx, sy, r, (160, 250, 255, alpha))

    def _draw_pov(self, w, h, alpha):
        tex = self.pov_full if abs(w/h-1.6) < abs(w/h-16/9) else self.pov_wide
        scale = max(w/tex.width, h/tex.height)
        left, bottom = (w-tex.width*scale)/2, (h-tex.height*scale)/2
        arcade.draw_texture_rect(tex, arcade.XYWH(w/2, h/2, tex.width*scale, tex.height*scale), alpha=alpha)
        crop_y = (self.pov_full.height-tex.height)/2

        # Barely visible green air over the middle-distance tree crowns.
        # Feathered bands avoid a hard rectangle and leave the foreground crisp.
        for i in range(20):
            k=(i+.5)/20
            mist=int(8*math.sin(math.pi*k)*alpha/255)
            arcade.draw_rect_filled(arcade.XYWH(w/2,h*(.36+.42*k),w,h*.022),
                                    (112,145,127,mist))

        # Small one-way movement, then settle; never slide back and forth.
        age = max(0., self.elapsed-5.4)
        move = min(1., age/5.)
        dx, dy = -17*move, -7*move
        bob = math.sin(age*5)*.6 if 0 < age < 5 else 0
        x = left+(1167.5+dx)*scale
        y = bottom+(self.pov_full.height-547.5-crop_y-dy+bob)*scale
        # Soft local canopy shade over the distant walking route. The
        # silhouette retains green color and never becomes solid black.
        shade=.25+.22*math.sin((1167.5+dx)*.045+547.5*.02)
        arcade.draw_texture_rect(self.dinosaur, arcade.XYWH(x, y, 95*scale, 45*scale),
                                 alpha=alpha,color=shade_color(shade))

        # Foreground leaves sway gently
        sway = math.sin(max(0., self.elapsed-4.4)*1.4)*1.8*scale
        if hasattr(self, 'leaf_patch'):
            arcade.draw_texture_rect(self.leaf_patch, arcade.XYWH(
                left+145*scale+sway,
                bottom+(self.pov_full.height-390-crop_y)*scale,
                290*scale, 220*scale), alpha=alpha)

        if self.elapsed >= 6.6:
            if self.elapsed < 9.8:
                text = "Something’s moving down there…"
                began = 6.6
            elif self.elapsed < 13.5:
                text = "That silhouette… the beast near the cave."
                began = 9.8
            elif self.elapsed < 16.8:
                text = "It’s heading towards the camp."
                began = 13.5
            else:
                text = "I can't let it get there."
                began = 16.8
            opacity = int(255*min(1., (self.elapsed-began)/.45))
            arcade.draw_rect_filled(arcade.XYWH(w/2, h*.095, w*.74, h*.075), (5, 15, 19, int(opacity*.75)))
            arcade.draw_text(text, w/2, h*.095, (240, 245, 240, opacity),
                             max(14, int(h*.023)), anchor_x='center', anchor_y='center')
            if self.elapsed >= 18.0:
                arcade.draw_text('ENTER / CLICK TO RAISE THE DART LAUNCHER',
                                 w/2, h*.035, (185,205,185), 11, anchor_x='center')

    def _enter_hunt(self):
        from scenes.b03_hunt_view import B03HuntView
        self.window.show_view(B03HuntView(self.truth_understood, self.on_return))

    def on_mouse_press(self, x, y, button, modifiers):
        if self.is_paused:
            self.handle_pause_mouse_press(x, y, button)
        elif button == arcade.MOUSE_BUTTON_LEFT and self.elapsed >= 18.0:
            self._enter_hunt()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.F11:
            self.toggle_fullscreen()
        elif self.handle_pause_key(key):
            return
        elif not self.is_paused and key == arcade.key.ENTER and self.elapsed >= 18.0:
            self._enter_hunt()
        elif not self.is_paused and key == arcade.key.R:
            self.restart()
            AudioManager().play('b03_arrival_warp', volume_scale=.65)
