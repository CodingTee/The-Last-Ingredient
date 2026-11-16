"""Sprite-based BE nutrient ration preparation and physical-departure close-ups.

Optimized layout:
- Robotic arm mounted on the upper right (mount ~ 1160, 685), matching Happy Ending.
- Synthesis apparatus shifted to the left (INST_X = 580) to prevent overlap.
- All holographic screen content (including Recipe, Body Scan, Cartridges, Mixing,
  Synthesis cycle, and Controls) strictly confined inside the right-hand holo panel.
"""
import math
from pathlib import Path
import arcade
from scenes.kitchen_shared import CONSOLE_ART, LIFT_ART, SWITCH, CONSOLE_WIPE, advance_console, draw_console_chrome, draw_rising_cartridge
from core.base_view import BaseGameView
from core.constants import ASSETS_DIR
from scenes.future_nutrient_state import (NutrientPreparation, Phase, TRANSFER_SECONDS,
    HOOD_OPEN_SECONDS, TRAY_DELIVERY_SECONDS, TRAY_TRANSFER_SECONDS, EAT_SECONDS)

ART = ASSETS_DIR / 'future_lab' / 'nutrient'
HE_ART = ASSETS_DIR / 'he_cooking'

CYAN = (103, 231, 255)
WHITE = (235, 245, 250)
MUTED = (159, 187, 204)
GOLD = (255, 212, 124)
GREEN = (136, 242, 185)

# Center of the physical synthesizer apparatus (comfortably centered to the right)
INST_X = 730
INST_Y = 480

# Holographic screen bounds on the right (shared with HE console)
HOLO = (1330, 506, 484, 730)
# Holographic action button located at bottom of the holo screen
ACTION = (1330, 215, 340, 50)
# Bottom-left exit button on the physical station
BACK = (135, 58, 160, 44)
# Finished nutrient block tray on the right side of the apparatus
TRAY_BOX = (975, 215, 260, 130)


ARM_ART = ('arm_mount', 'arm_link', 'arm_stir', 'arm_grip')


class SpriteStationView(BaseGameView):
    """Responsive scene canvas; image objects are real Arcade Sprite instances."""
    def __init__(self, laboratory, names, background):
        super().__init__()
        self.laboratory = laboratory
        self.elapsed = 0.
        self.fade = 1.
        self._texts = {}
        self.images = {name: arcade.Sprite(ART / (name + '.png')) for name in names}
        self.background_name = background
        self.images[background] = arcade.Sprite(ART / (background + '.png'))
        self.audio = laboratory.audio

    def on_show_view(self):
        super().on_show_view()
        self.fit()
        self.fade = 1.
        self.window.push_handlers(on_deactivate=self._lost_focus)

    def _lost_focus(self):
        self.stirring = False

    def on_hide_view(self):
        if self.window:
            self.window.remove_handlers(on_deactivate=self._lost_focus)

    def fit(self):
        w, h = self.window.width, self.window.height
        self.scale = min(w / 1600, h / 900)
        self.ox, self.oy = (w - 1600 * self.scale) / 2, (h - 900 * self.scale) / 2

    def on_resize(self, w, h):
        super().on_resize(w, h)
        self.fit()

    def xy(self, x, y):
        return self.ox + x * self.scale, self.oy + y * self.scale

    def virtual(self, x, y):
        return (x - self.ox) / self.scale, (y - self.oy) / self.scale

    @staticmethod
    def inside(x, y, box):
        cx, cy, w, h = box
        return abs(x - cx) <= w / 2 and abs(y - cy) <= h / 2

    def sprite(self, name, x, y=None, w=None, h=None, angle=0, alpha=255):
        if y is None and isinstance(x, (tuple, list)):
            x, y, w, h = x
        s = self.images[name]
        size = min(w / s.texture.width, h / s.texture.height) * self.scale
        s.scale = size
        s.position = self.xy(x, y)
        s.angle = angle
        s.alpha = max(0, min(255, int(alpha)))
        arcade.draw_sprite(s)

    def rect(self, box, color=None, outline=None):
        x, y, w, h = box
        r = arcade.XYWH(*self.xy(x, y), w * self.scale, h * self.scale)
        if color is not None:
            arcade.draw_rect_filled(r, color)
        if outline is not None:
            arcade.draw_rect_outline(r, outline, 2 * self.scale)

    def box(self, bounds, color=None, border=None):
        self.rect(bounds, color, border)

    def text(self, t, x, y, size=16, color=WHITE, center=False, width=None, bold=False, anchor_y=None, anchor_x=None):
        if anchor_y is None:
            anchor_y = 'center' if center else 'baseline'
        if anchor_x is None:
            anchor_x = 'center' if center else 'left'
        key = (t, x, y, size, color, center, width, bold, anchor_y, anchor_x, self.window.width, self.window.height)
        if key not in self._texts:
            if len(self._texts) > 250:
                self._texts.clear()
            self._texts[key] = arcade.Text(t, *self.xy(x, y), color, size * self.scale,
                anchor_x=anchor_x,
                anchor_y=anchor_y,
                width=int(width * self.scale) if width else 0,
                multiline=bool(width), font_name=('Segoe UI', 'Calibri', 'Arial'), bold=bold)
        self._texts[key].draw()

    def begin_draw(self):
        self.clear((7, 19, 32))
        self.window.default_camera.use()
        bg = self.images[self.background_name]
        bg.scale = max(self.window.width / bg.texture.width, self.window.height / bg.texture.height)
        bg.position = (self.window.width / 2, self.window.height / 2)
        bg.alpha = 255
        arcade.draw_sprite(bg)

    def end_draw(self):
        if self.fade:
            self.rect((800, 450, 1800, 1100), (4, 12, 20, int(self.fade * 255)))
        self.draw_pause_overlay()

    def leave(self):
        self.laboratory.keys.clear()
        self.window.show_view(self.laboratory)

    def common_key(self, key):
        if key == arcade.key.F11:
            self.toggle_fullscreen()
            self.fit()
            return True
        if key == arcade.key.P:
            self.is_paused = not self.is_paused
            self.hovered_pause_btn = None
            return True
        if key == arcade.key.ESCAPE:
            if self.is_paused:
                self.is_paused = False
            else:
                self.leave()
            return True
        if self.is_paused:
            self.handle_pause_key(key)
            return True
        return False

    def on_mouse_motion(self, x, y, dx, dy):
        if self.is_paused:
            self.handle_pause_mouse_motion(x, y)


class NutrientPrepView(SpriteStationView):
    """Refined BE Nutrient Preparation Station.

    Key improvements:
    - Robotic arm positioned on the right (mount = 1160, 685) matching Happy Ending.
    - Synthesizer apparatus moved left (INST_X = 580) to avoid overlap.
    - All holographic console tasks (recipe selection, body scan, cartridge status,
      mixing monitor, synthesis status, and action buttons) strictly inside the holo screen.
    - Station counter kept clean and unobstructed without full-screen letterbox bars.
    """
    def __init__(self, laboratory):
        super().__init__(laboratory,
            ['mold', 'press', 'shield', 'tray', 'scanner', 'base', 'gel', 'binder', 'gantry',
             'mixture', 'block', 'hand', 'arm_fixed', 'spoon', 'grain_pile', 'slurry',
             'crystal', 'crystal_stream', 'mix_gel', 'mix_crystal', 'mix_bound', 'stirred_paste',
             'grain_stream', 'gel_stream', 'water_stream', 'base_open', 'binder_open',
             'block_bite1', 'block_bite2'], 'station')
        for name in (*CONSOLE_ART, *LIFT_ART, *ARM_ART):
            self.images[name] = arcade.Sprite(HE_ART / (name + '.png'))
        self.images['counter'] = arcade.Sprite(ART / 'counter_be.png')
        self.background_name = 'counter'
        self.console_open = True
        self.console_hint = False
        self.console_t = CONSOLE_WIPE
        self.mouse = (0, 0)
        self.model = NutrientPreparation()
        self.stirring = False
        self.last_phase = self.model.phase
        self.bite_cues = set()
        self.bite_sound = arcade.load_sound(ART / 'bite.wav')

    def on_mouse_motion(self, x, y, dx, dy):
        super().on_mouse_motion(x, y, dx, dy)
        self.mouse = self.virtual(x, y)

    def on_hide_view(self):
        self.stirring = False
        super().on_hide_view()

    def leave(self):
        self.stirring = False
        super().leave()

    def on_update(self, dt):
        if self.is_paused:
            self.stirring = False
            return
        dt = min(dt, .1)
        self.elapsed += dt
        self.fade = max(0, self.fade - 2.5 * dt)
        advance_console(self, dt)
        if self.console_open:
            self.model.update(dt, self.stirring)
        if self.model.phase != self.last_phase:
            self.audio.play('lock_click', volume_scale=.5)
            self.last_phase = self.model.phase
            if self.model.phase == Phase.EATING:
                self.bite_cues.clear()
            self.stirring = False
        if self.model.phase == Phase.EATING:
            for cue in (.75, 1.65, 2.55):
                if self.model.age >= cue and cue not in self.bite_cues:
                    self.bite_cues.add(cue)
                    if self.audio.sound_enabled:
                        arcade.play_sound(self.bite_sound, volume=.25)
        if self.model.phase == Phase.DONE:
            self.laboratory.nutrient_consumed = True
            self.laboratory.cooking_complete = True

    def action(self):
        if self.model.phase == Phase.DONE:
            self.leave()
            return
        if self.model.phase == Phase.RECIPE and not self.model.selected:
            self.model.selected = True
        if self.model.phase == Phase.LOAD:
            if self.model.load(len(self.model.ingredients)):
                self.audio.play('salt_pour', volume_scale=.35)
            return
        if self.model.action():
            self.audio.play('click', volume_scale=.65)

    # -------------------------------------------------------------------------
    # Robotic Arm Kinematics (Right-Mounted, matching Happy Ending)
    # -------------------------------------------------------------------------
    def cartridge_pose(self, progress):
        """Shared anchor for the gripper, cartridge and pouring animation."""
        ingredient = self.model.last_ingredient
        name = ('base_open', 'gel', 'crystal', 'binder_open')[ingredient]
        texture = self.images[name].texture
        half_height = min(90 / texture.width, 100 / texture.height) * texture.height / 2
        mouth_offset = 48 - half_height
        pour_x = INST_X + mouth_offset * math.sin(math.radians(145))
        if progress >= .96:
            back = min(1, (progress - .96) / .31)
            if progress < 1.27:
                return (pour_x + (175 - pour_x) * back,
                        511 - 12 * back + 90 * math.sin(math.pi * back), 0)
            release = min(1, (progress - 1.27) / .23)
            return (175 + 805 * release, 499 + 61 * release, 0)
        reach = min(1, max(0, (progress - .10) / .26))
        carry = min(1, max(0, (progress - .36) / .29))
        if progress < .36:
            return (980 - 805 * reach, 560 - 61 * reach, 0)
        tilt_in = min(1, max(0, (progress - .65) / .11))
        tilt_out = min(1, max(0, (.96 - progress) / .06))
        tilt = 145 * tilt_in * tilt_out
        return (175 + (pour_x - 175) * carry,
                499 + 12 * carry + 90 * math.sin(math.pi * carry), tilt)

    @staticmethod
    def wrist_offset(x, y, tilt, distance):
        angle = math.radians(tilt)
        return x - distance * math.sin(angle), y - distance * math.cos(angle)

    def serving_tray_pose(self):
        age = self.model.age
        t = max(0., min(1., (age - .9) / .9))
        x, y, width, height = TRAY_BOX
        return (175 + (x - 175) * t, 431 + (y - 431) * t + 75 * math.sin(math.pi * t),
                172 + (width - 172) * t, 80 + (height - 80) * t)

    def arm_pose(self):
        mount = (1200, 685)
        p = self.model.phase
        if p == Phase.LOAD and self.model.transfer:
            progress = (TRANSFER_SECONDS - self.model.transfer) / 2.8
            x, y, _ = self.cartridge_pose(progress)
            wrist = (x, y)
            elbow = ((mount[0] + wrist[0]) / 2, 640)
        elif p == Phase.CONSUME:
            age = self.model.age
            if age < .9:
                reach = min(1., age / .9)
                wrist = (980 - 805 * reach, 560 - 86 * reach)
            else:
                x, y, _, _ = self.serving_tray_pose()
                release = min(1., (age - TRAY_DELIVERY_SECONDS) / .6) if age >= TRAY_DELIVERY_SECONDS else 0.
                wrist = (x + (980 - x) * release, y + 43 + (517 - y) * release)
            elbow = ((mount[0] + wrist[0]) / 2, 640)
        elif p == Phase.MIX:
            if self.stirring:
                a = self.elapsed * 6
                wrist = (INST_X + 15 + 24 * math.sin(a), 428 + 5 * math.cos(a))
                elbow = ((mount[0] + wrist[0]) / 2 + 10, 615)
            else:
                wrist = (INST_X + 25, 470)
                elbow = ((mount[0] + wrist[0]) / 2 + 15, 625)
        elif p in (Phase.READY, Phase.SYNTHESIZE):
            # Natural full arm span parked safely clear of the press stroke (press right edge = 930)
            wrist = (980, 570)
            elbow = (1095, 640)
        else:
            # Full natural extended arm display matching Happy Ending idle stance
            wrist = (980, 560)
            elbow = (1100, 640)
        return mount, elbow, wrist

    def arm_segment(self, a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        sprite = self.images['arm_link']
        sprite.position = self.xy((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        sprite.width = (length + 28) * self.scale
        sprite.height = 48 * self.scale
        sprite.angle = -math.degrees(math.atan2(dy, dx))
        sprite.alpha = 255
        arcade.draw_sprite(sprite)

    def draw_robot_arm(self):
        mount, elbow, wrist = self.arm_pose()
        self.sprite('arm_mount', mount[0], mount[1], 150, 175)
        self.arm_segment(mount, elbow)
        self.arm_segment(elbow, wrist)
        for pt in (elbow, wrist):
            x, y = self.xy(pt[0], pt[1])
            arcade.draw_circle_filled(x, y, 9 * self.scale, (24, 49, 76))
            arcade.draw_circle_outline(x, y, 9 * self.scale, (100, 206, 238), 2 * self.scale)
        if self.stirring:
            angle = 12 * math.sin(self.elapsed * 10)
            self.sprite('arm_stir', wrist[0], wrist[1] - 40, 60, 110, angle=angle)
        elif self.model.phase == Phase.MIX:
            self.sprite('arm_stir', wrist[0], wrist[1] - 35, 55, 95)
        else:
            tilt = self.cartridge_pose((TRANSFER_SECONDS - self.model.transfer) / 2.8)[2] if self.model.transfer else 0
            grip_x, grip_y = self.wrist_offset(*wrist, tilt, 27)
            self.sprite('arm_grip', grip_x, grip_y, 64, 72, angle=tilt)

    # -------------------------------------------------------------------------
    # Render Loop
    # -------------------------------------------------------------------------
    def on_draw(self):
        self.begin_draw()
        background = self.images['counter']
        background.position = self.xy(800, 450)
        background.width = 1600 * self.scale
        background.height = 900 * self.scale
        arcade.draw_sprite(background)

        m = self.model
        p = m.phase

        # 1. Synthesizer Apparatus (Shifted Left to INST_X = 580)
        self.sprite('gantry', INST_X, 480, 650, 470)
        self.sprite('mold', INST_X, 345, 555, 260)
        if p != Phase.SYNTHESIZE:
            self.sprite('press', INST_X, 560, 400, 200)

        self._draw_food_and_loading()

        if p == Phase.SYNTHESIZE:
            t = m.synthesis_time
            if t >= 4:
                self.sprite('block', INST_X, 358, 290, 130)
            py = 560 - (min(1, max(0, (t - 2) / 1.2)) * 160 if t < 4 else max(0, 1 - (t - 4)) * 160)
            self.sprite('press', INST_X, py, 400, 200)
            hood_y = 365 + max(0, 1 - t / .7) * 160
            self.sprite('shield', INST_X, hood_y, 590, 300, alpha=185)
            if t >= 4:
                for i in range(5):
                    phase = (self.elapsed * .5 + i * .2) % 1
                    x, y = self.xy(INST_X - 90 + i * 45, 440 + phase * 65)
                    arcade.draw_circle_outline(x, y, (5 + phase * 6) * self.scale,
                        (222, 245, 255, int(95 * (1 - phase))), 2 * self.scale)

        if p == Phase.COLLECT:
            if m.age < .7:
                opening = m.age / .7
                self.sprite('shield', INST_X, 365 + 160 * opening, 590, 300, alpha=int(185 * (1 - opening)))
            self.sprite('block', INST_X, 365, 290, 130)

        # Finished Ration Tray (Positioned comfortably on the counter to the right of mold)
        if p == Phase.CONSUME and m.age < .9:
            opening = min(1., m.age / .25)
            rise = max(0., (m.age - .25) / .65)
            draw_rising_cartridge(self, 'tray', (175, 431, 172, 80), opening, rise)
        elif p == Phase.CONSUME:
            self.sprite('tray', *self.serving_tray_pose())
        elif p in (Phase.EATING, Phase.DONE):
            self.sprite('tray', *TRAY_BOX)
        tray_cx, tray_cy = TRAY_BOX[0], TRAY_BOX[1]

        if p == Phase.CONSUME:
            t = max(0., min(1., (m.age - TRAY_DELIVERY_SECONDS) / (TRAY_TRANSFER_SECONDS - TRAY_DELIVERY_SECONDS)))
            t = t * t * (3 - 2 * t)
            bx = INST_X + (tray_cx - INST_X) * t
            by = 365 + (tray_cy + 10 - 365) * t
            self.sprite('block', bx, by, 290 - 55 * t, 130 - 10 * t)
        elif p == Phase.EATING:
            age = m.age
            if age < .8:
                lift = age / .8
                bx, by = tray_cx - 40 * lift, (tray_cy + 10) + 180 * lift
                hand_y = -90 + 410 * lift
                food = 'block'
            elif age < 2.5:
                bite = 0 if age < 1.65 else 1
                bx, by = tray_cx - 40, tray_cy + 190 + 8 * math.sin((age - .8) * 5)
                hand_y = 320
                food = 'block_bite1' if bite == 0 else 'block_bite2'
            else:
                bx, by = tray_cx - 40, tray_cy + 190
                hand_y = 320 - 440 * min(1, (age - 2.5) / .8)
                food = None
            self.sprite('hand', tray_cx + 180, hand_y - 20, 820, 574)
            if food:
                self.sprite(food, bx, by, 235, 120)

        # 2. Robotic Arm on the Right (Mount = 1160, 685, reaching to INST_X)
        self.draw_robot_arm()

        # 3. Holographic Console (All HUD & interactions contained strictly inside)
        self.draw_console()

        # 4. Clean physical station navigation (Bottom-Left exit)
        self.rect(BACK, (13, 39, 57, 245), (69, 113, 135))
        self.text('BACK / ESC', 135, 58, 14, WHITE, True)

        self.end_draw()

    def draw_mold_food(self, name, width, alpha):
        texture = self.images[name].texture
        height = width * texture.height / texture.width
        self.sprite(name, INST_X, 332 + height / 2, width, height, alpha=alpha)

    def _draw_food_and_loading(self):
        m = self.model
        p = m.phase
        pending = p == Phase.LOAD and m.transfer > 0
        t = (TRANSFER_SECONDS - m.transfer) / 2.8 if pending else 0
        delivered = len(m.ingredients) + int(pending and t >= .86)
        if delivered and p < Phase.COLLECT and not (p == Phase.SYNTHESIZE and m.synthesis_time >= 4):
            food = ('grain_pile', 'mix_gel', 'mix_crystal', 'mix_bound')[delivered - 1]
            progress = min(1.0, m.mix_time / 4.0) if p == Phase.MIX else 0.0
            if p in (Phase.READY, Phase.SYNTHESIZE):
                progress = 1.0

            # Both layers stay anchored to the same spot in the mold.
            if progress > 0:
                paste_width = 48 + 84 * progress
                self.draw_mold_food('stirred_paste', paste_width, alpha=255 * (1 - (1 - progress) ** 2))
            if progress < 1:
                self.draw_mold_food(food, 120 * (1 - .6 * progress), alpha=255 * (1 - progress))


        if pending:
            i = m.last_ingredient
            sealed = ('base', 'gel', 'crystal', 'binder')[i]
            if t < .36:
                opening = min(1, t / .12)
                rise = min(1, max(0, (t - .12) / .24))
                draw_rising_cartridge(self, sealed, (175, 451, 90, 100), opening, rise)
                return
            if t >= 1.27:
                descent = min(1, (t - 1.27) / .16)
                opening = min(1, max(0, (1.5 - t) / .07))
                draw_rising_cartridge(self, sealed, (175, 451, 90, 100), opening, 1 - descent)
                return
            x, wrist_y, tilt = self.cartridge_pose(t)
            name = sealed if t < .65 else ('base_open', 'gel', 'crystal', 'binder_open')[i]
            center_x, center_y = self.wrist_offset(x, wrist_y, tilt, 48)
            self.sprite(name, center_x, center_y, 90, 100, angle=tilt)
            if .77 < t < .90:
                stream = ('grain_stream', 'gel_stream', 'crystal_stream', 'water_stream')[i]
                # Anchor the stream to the top edge of the actual fitted cartridge.
                texture = self.images[name].texture
                half_height = min(90 / texture.width, 100 / texture.height) * texture.height / 2
                mouth_x, mouth_y = self.wrist_offset(x, wrist_y, tilt, 48 - half_height)
                landing_y = 356
                self.sprite(stream, mouth_x, (mouth_y + landing_y) / 2, 72, mouth_y - landing_y)

    # -------------------------------------------------------------------------
    # Holographic Console System (Strictly confined inside HOLO = 1330, 506, 484, 730)
    # -------------------------------------------------------------------------
    def draw_console(self):
        if not draw_console_chrome(self):
            return

        m = self.model
        p = m.phase

        # Holographic Header
        self.text('FUTURE LAB · TRANSIT SYNTHESIZER', 1330, 830, 11, CYAN, center=True)
        titles = {
            Phase.RECIPE: '01 / SELECT RECIPE',
            Phase.SCAN: '02 / SCAN BODY',
            Phase.PROFILE: '02 / CONFIRM PROFILE',
            Phase.LOAD: '03 / LOAD CARTRIDGES',
            Phase.MIX: '04 / MIX INGREDIENTS',
            Phase.READY: '05 / SYNTHESIS READY',
            Phase.SYNTHESIZE: '05 / SYNTHESIZING',
            Phase.COLLECT: '06 / COLLECT RATION',
            Phase.CONSUME: '07 / CONSUME RATION',
            Phase.EATING: '07 / EATING RATION',
            Phase.DONE: '08 / READY FOR CAPSULE'
        }
        self.text(titles[p], 1330, 796, 17, WHITE, center=True)
        self.rect((1330, 775, 410, 2), (103, 231, 255, 120))

        # Content Area inside Holo Screen
        if p == Phase.RECIPE:
            self.rect((1330, 545, 390, 370), (12, 36, 56, 160), CYAN)

            # 1. Upper Section: Finished Dish Holographic Preview
            self.text('MILITARY TRANSIT NUTRIENT BLOCK', 1330, 706, 14, CYAN, center=True, bold=True)
            self.text('FORMULA: HIGH-DENSITY COMPACT RATION', 1330, 690, 10, MUTED, center=True)

            # Finished Ration Image on Tray
            self.sprite('tray', 1330, 630, 190, 60)
            self.sprite('block', 1330, 634, 125, 45)

            # Formula status badge
            self.box((1330, 584, 280, 22), (18, 48, 68, 200), (45, 120, 160))
            self.text('STANDARD FORMULA · ACTIVE', 1330, 584, 10, CYAN, center=True, bold=True)

            # Subtle Divider Line between Preview and Components
            self.box((1330, 564, 360, 1), (45, 78, 102))

            # 2. Lower Section: 4 Interactive Component Slots (compact names to prevent overlap)
            slots = [
                ('NUTRIENT BASE', 'ORGANIC · 100%', False),
                ('ENERGY GEL', 'CALORIC · 100%', False),
                ('NEUROTOXIN CRYSTAL', 'ACTIVE · LETHAL', True),
                ('BINDING SOLUTION', 'STABILIZER · 100%', False),
            ]
            slot_y = (538, 496, 454, 412)
            for idx, (name, tag, is_warn) in enumerate(slots):
                sy = slot_y[idx]
                if is_warn:
                    bg = (48, 20, 24, 220)
                    border = (235, 90, 90)
                    col_l = (255, 140, 140)
                    col_r = (255, 100, 100)
                    prefix = '[⚠]'
                else:
                    bg = (14, 34, 52, 200)
                    border = (45, 80, 105)
                    col_l = WHITE
                    col_r = MUTED
                    prefix = '[✓]'

                self.box((1330, sy, 360, 34), bg, border)
                self.text(f'{prefix}  0{idx + 1}. {name}', 1165, sy, 11, col_l, bold=True, anchor_y='center')
                self.text(tag, 1495, sy, 10, col_r, bold=is_warn, anchor_y='center', anchor_x='right')

            self.text('Click components to inspect • All cartridges pre-loaded', 1330, 378, 10, MUTED, center=True)

        elif p in (Phase.SCAN, Phase.PROFILE):
            # BODY SCAN TASK: Fixed strictly inside the holographic screen
            self.rect((1330, 545, 390, 370), (10, 32, 52, 190), GREEN if p == Phase.PROFILE else CYAN)
            self.text('PHYSIOLOGICAL SCANNER', 1330, 702, 14, CYAN, center=True)

            # Holographic Body Scanner Silhouette inside panel
            self.sprite('scanner', 1330, 550, 210, 240)

            if p == Phase.SCAN and m.scan_active:
                sy = 430 + (m.scan_time / 3.0) * 230
                self.rect((1330, sy, 190, 4), (100, 255, 207, 230))
                self.text(f'SCANNING BIOLOGICAL PROFILE... {int(m.scan_time / 3.0 * 100)}%',
                          1330, 400, 12, (100, 255, 207), center=True)
            elif p == Phase.PROFILE:
                self.rect((1330, 550, 200, 230), None, (136, 242, 185))
                self.text('✓ COMPATIBLE: 100%', 1330, 412, 17, GREEN, center=True)
                self.text('Adapted future physiology tolerates compound.', 1330, 388, 11, WHITE, center=True)
            else:
                self.text('Awaiting biometric compatibility check.', 1330, 400, 12, WHITE, center=True)

            self.text('Warning: Applies to current adapted body only.\nNot a safety validation for other eras.',
                      1330, 345, 10, MUTED, center=True, width=360)

        elif p == Phase.LOAD:
            self.rect((1330, 545, 390, 370), (10, 30, 48, 160), CYAN)
            labels = ('NUTRIENT BASE', 'ENERGY GEL', 'WHITE NEUROTOXIN CRYSTALS', 'BINDING SOLUTION')
            for idx, label in enumerate(labels):
                cy = 660 - idx * 72
                current = idx == len(m.ingredients)
                loaded = idx < len(m.ingredients)
                self.rect((1330, cy, 360, 62), (20, 65, 88, 230) if current else (14, 30, 44, 180),
                          GOLD if current else (50, 75, 95))
                self.text(f'{idx + 1}. {label}', 1165, cy + 8, 12, WHITE, bold=True)
                if loaded or current:
                    status = 'ADDED' if loaded else ('ADDING...' if m.transfer else 'SELECT TO ADD')
                    self.text(status, 1165, cy - 15, 10, GREEN if loaded else GOLD)

        elif p == Phase.MIX:
            self.rect((1330, 545, 390, 370), (10, 30, 48, 160), CYAN)
            self.text('HOMOGENIZATION CYCLE', 1330, 702, 14, CYAN, center=True)

            progress = min(1., m.mix_time / 4.0)
            self.text(f'BLEND PROGRESS: {int(progress * 100)}%', 1330, 590, 18, CYAN, center=True)
            self.rect((1330, 540, 330, 16), (30, 50, 66))
            self.rect((1165 + 165 * progress, 540, 330 * progress, 16), CYAN)

            hint = 'HOLD [SPACE] TO STIR WITH ROBOTIC ARM' if not self.stirring else 'STIRRING IN PROGRESS...'
            self.text(hint, 1330, 475, 13, GOLD if not self.stirring else GREEN, center=True)
            self.text('Uniform mixture required before high-pressure compression.', 1330, 400, 11, MUTED, center=True, width=350)

        elif p in (Phase.READY, Phase.SYNTHESIZE):
            self.rect((1330, 545, 390, 370), (10, 30, 48, 160), CYAN)
            self.text('HYDRAULIC PRESS & COMPACTION', 1330, 702, 14, CYAN, center=True)
            if p == Phase.READY:
                self.text('PARAMETERS LOCKED & READY', 1330, 640, 16, GREEN, center=True)
                self.text('• Compression: 12.4 MPa\n• Target Density: 1.42 g/cm³\n• Thermal Set: 180°C Cryo-stabilized',
                          1165, 530, 12, WHITE, width=340)
                self.text('Arm retracted. Press button to initiate cycle.', 1330, 420, 11, CYAN, center=True)
            else:
                t = m.synthesis_time
                stage_label = '1. STABILIZE' if t < 2 else ('2. COMPRESSION' if t < 4 else '3. CRYOGENIC COOL')
                self.text(stage_label, 1330, 645, 20, CYAN, center=True)
                prog = min(1., t / 6.0)
                self.rect((1330, 575, 330, 16), (30, 50, 66))
                self.rect((1165 + 165 * prog, 575, 330 * prog, 16), CYAN)
                self.text(f'MACHINE CYCLE: {int(prog * 100)}%', 1330, 535, 13, WHITE, center=True)
                self.text('Protective shield engaged. Do not reach into mold.', 1330, 420, 11, MUTED, center=True)

        elif p == Phase.COLLECT:
            self.rect((1330, 545, 390, 370), (10, 30, 48, 160), GREEN)
            self.text('COMPACTION COMPLETE', 1330, 702, 15, GREEN, center=True)
            self.text('RATION FORMED IN MOLD', 1330, 645, 17, WHITE, center=True)
            self.text('Protective hood has opened.\nRetrieve the solid nutrient block.',
                      1330, 540, 13, MUTED, center=True, width=340)
            self.text('Click block in mold or click button below.', 1330, 430, 11, CYAN, center=True)

        elif p in (Phase.CONSUME, Phase.EATING):
            self.rect((1330, 545, 390, 370), (10, 30, 48, 160), CYAN)
            self.text('NUTRITION INGESTION', 1330, 702, 15, CYAN, center=True)
            if p == Phase.CONSUME:
                self.text('RATION MOVED TO TRAY', 1330, 640, 16, WHITE, center=True)
                self.text('Consume ration to sustain biological energy\nduring physical time jump.',
                          1330, 550, 12, MUTED, center=True, width=340)
            else:
                prog = min(1., m.age / EAT_SECONDS)
                self.text('CONSUMING FIELD RATION...', 1330, 645, 16, GOLD, center=True)
                self.rect((1330, 580, 330, 16), (30, 50, 66))
                self.rect((1165 + 165 * prog, 580, 330 * prog, 16), GREEN)
                self.text('Metabolic absorption: Optimal (Adapted)', 1330, 520, 12, (136, 242, 185), center=True)

        elif p == Phase.DONE:
            self.rect((1330, 545, 390, 370), (10, 35, 52, 220), GREEN)
            self.text('PREPARATION COMPLETE', 1330, 685, 17, GREEN, center=True)
            self.text('Biological energy: 100%\nNutrient block consumed.', 1330, 610, 13, WHITE, center=True, width=340)
            self.text('Proceed to the Physical Jump Capsule\nto initiate departure.',
                      1330, 500, 13, CYAN, center=True, width=340)

        # Holo Status Message Bar (Comfortable padding, perfectly centered)
        self.rect((1330, 290, 390, 60), (8, 26, 42, 220), (45, 78, 102))
        self.text(m.message, 1330, 290, 11, WHITE, center=True, width=360, anchor_y='center')

        # Primary Holographic Action Button
        actions = {
            Phase.RECIPE: 'CONFIRM RECIPE',
            Phase.SCAN: 'SCAN COMPATIBILITY' if not m.scan_active else 'SCANNING...',
            Phase.PROFILE: 'CONFIRM BODY PROFILE',
            Phase.LOAD: 'DISPENSE CARTRIDGE' if not m.transfer else 'DISPENSING...',
            Phase.MIX: 'HOLD SPACE TO MIX',
            Phase.READY: 'START SYNTHESIS',
            Phase.SYNTHESIZE: 'SYNTHESIS IN PROGRESS',
            Phase.COLLECT: 'COLLECT RATION' if m.can_action else 'OPENING HOOD...',
            Phase.CONSUME: 'CONSUME RATION' if m.can_action else ('RETRIEVING TRAY...' if m.age < TRAY_DELIVERY_SECONDS else 'MOVING TO TRAY...'),
            Phase.EATING: 'EATING...',
            Phase.DONE: 'RETURN TO LAB'
        }
        enabled = m.can_action or (p == Phase.LOAD and not m.transfer)
        btn_hover = self.inside(self.mouse[0], self.mouse[1], ACTION)
        btn_bg = (32, 125, 155) if (enabled and btn_hover) else ((24, 103, 126) if enabled else (25, 42, 55))
        self.rect(ACTION, btn_bg, CYAN if enabled else (50, 70, 85))
        self.text(actions[p], 1330, 210, 14, WHITE if enabled else MUTED, center=True, bold=True)

    # -------------------------------------------------------------------------
    # Input Handling
    # -------------------------------------------------------------------------
    def on_key_press(self, key, modifiers):
        if self.common_key(key):
            self.stirring = False
            return
        if self.is_paused or not self.console_open:
            return
        if key in (arcade.key.ENTER, arcade.key.SPACE) and self.model.phase != Phase.MIX:
            self.action()
            return
        if key in (arcade.key.KEY_1, arcade.key.KEY_2, arcade.key.KEY_3, arcade.key.KEY_4) and self.model.phase == Phase.LOAD:
            if self.model.load(key - arcade.key.KEY_1):
                self.audio.play('salt_pour', volume_scale=.35)
            return
        if key == arcade.key.SPACE and self.model.phase == Phase.MIX:
            self.stirring = True

    def on_key_release(self, key, modifiers):
        if key == arcade.key.SPACE:
            self.stirring = False

    def on_mouse_press(self, x, y, button, modifiers):
        if self.is_paused:
            if button == arcade.MOUSE_BUTTON_LEFT:
                self.handle_pause_mouse_press(x, y, button)
            return
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        x, y = self.virtual(x, y)
        if self.inside(x, y, BACK):
            self.leave()
            return
        if self.inside(x, y, SWITCH):
            self.console_open = not self.console_open
            self.console_hint = False
            if self.console_open:
                self.console_t = CONSOLE_WIPE
            self.stirring = False
            self.audio.play('click')
            return
        if not self.console_open:
            return

        m = self.model
        if m.phase == Phase.RECIPE and self.inside(x, y, (1330, 545, 390, 370)):
            m.selected = True
            self.audio.play('click')
            if self.inside(x, y, (1330, 454, 360, 34)):
                m.message = 'WARNING: White neurotoxin crystals. Active for physical jump.'
            elif self.inside(x, y, (1330, 538, 360, 34)):
                m.message = 'Nutrient Base: High-density powdered protein and carbohydrates.'
            elif self.inside(x, y, (1330, 496, 360, 34)):
                m.message = 'Energy Gel: Lipids and electrolytes for long-distance transit.'
            elif self.inside(x, y, (1330, 412, 360, 34)):
                m.message = 'Binding Solution: Chemical hardener for mechanical extrusion.'
            else:
                m.message = 'Transit ration selected. Confirm recipe below.'
            return

        if m.phase in (Phase.SCAN, Phase.PROFILE) and self.inside(x, y, (1330, 545, 390, 370)):
            self.action()
            return

        if m.phase == Phase.LOAD:
            for idx in range(4):
                cy = 660 - idx * 72
                if self.inside(x, y, (1330, cy, 360, 62)):
                    if m.load(idx):
                        self.audio.play('salt_pour', volume_scale=.35)
                    return

        if m.phase == Phase.COLLECT and (self.inside(x, y, (INST_X, 365, 300, 145)) or self.inside(x, y, ACTION)):
            self.action()
            return

        if m.phase == Phase.CONSUME and (self.inside(x, y, TRAY_BOX) or self.inside(x, y, ACTION)):
            self.action()
            return

        if m.phase == Phase.MIX and self.inside(x, y, ACTION):
            self.stirring = True
            return

        if self.inside(x, y, ACTION):
            self.action()

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT and self.model.phase == Phase.MIX:
            self.stirring = False


class TransitDepartureView(SpriteStationView):
    """The in-capsule interface for the three successive bad-ending jumps."""

    DESTINATIONS = ("Prehistoric Era", "Last Century - Royal Kitchen", "Return to Modern Era")
    ROWS = ((800, 530, 510, 64), (800, 450, 510, 64), (800, 370, 510, 64))
    CONFIRM = (935, 410, 220, 64)
    CANCEL = (665, 410, 220, 64)

    def __init__(self, laboratory, next_destination=0):
        super().__init__(laboratory, [], 'capsule_interior')
        self.next_destination = next_destination
        self.confirming = False
        self.countdown = None

    @classmethod
    def open_modern_return(cls, window, truth_understood):
        from scenes.future_integrated_view import FutureLabView

        laboratory = FutureLabView(start_branch='be')
        laboratory.truth_understood = truth_understood
        laboratory.nutrient_consumed = True
        laboratory.departure_view = cls(laboratory, next_destination=2)
        window.show_view(laboratory.departure_view)

    def return_to_capsule(self):
        self.next_destination += 1
        self.countdown = None
        self.confirming = False
        self.window.show_view(self)

    def leave(self):
        if self.countdown is None:
            self.confirming = False
            super().leave()

    def launch(self):
        if self.confirming and self.countdown is None:
            self.countdown = 3.
            self.audio.play('time_warp', volume_scale=.7)

    def on_update(self, dt):
        if self.is_paused:
            return
        dt = min(dt, .1)
        self.fade = max(0, self.fade - 2.5 * dt)
        if self.countdown is None:
            return
        self.countdown = max(0, self.countdown - dt)
        if self.countdown > 1e-6:
            return

        truth = self.laboratory.truth_understood
        if self.next_destination == 0:
            from scenes.b03_arrival_view import B03ArrivalView
            view = B03ArrivalView(truth, on_return=self.return_to_capsule)
        elif self.next_destination == 1:
            from scenes.scene_b05 import SceneB05View
            view = SceneB05View(truth, story_mode=True, on_return=self.return_to_capsule)
        else:
            from scenes.bad_ending_view import BadEndingView
            view = BadEndingView(truth, start_stage="B07")
        self.window.show_view(view)

    def draw_button(self, box, label, enabled=True):
        self.rect(box, (20, 78, 103) if enabled else (31, 38, 49), CYAN if enabled else None)
        self.text(label, box[0], box[1] - 7, 17, WHITE if enabled else MUTED, center=True)

    def destination_rows(self):
        if self.next_destination == 2:
            return ((2, self.ROWS[1]),)
        return tuple(enumerate(self.ROWS))

    def on_draw(self):
        self.begin_draw()
        self.rect((800, 475, 650, 370), (8, 26, 42, 224), CYAN)
        if self.countdown is not None:
            self.text('CONSCIOUSNESS RETURN' if self.next_destination == 2 else 'PHYSICAL TRANSIT',
                      800, 550, 24, CYAN, center=True)
            self.text(str(max(1, math.ceil(self.countdown))), 800, 430, 48, WHITE, center=True)
            if self.countdown < .65:
                self.rect((800, 450, 1800, 1100), (130, 223, 255, int((1 - self.countdown / .65) * 210)))
        elif self.confirming:
            self.text('CONFIRM DESTINATION', 800, 608, 23, CYAN, center=True)
            self.text(self.DESTINATIONS[self.next_destination], 800, 513, 22, WHITE, center=True)
            self.draw_button(self.CANCEL, 'Cancel [Esc]')
            self.draw_button(self.CONFIRM, 'Confirm [Enter]')
        else:
            self.text('SELECT DESTINATION', 800, 608, 23, CYAN, center=True)
            for index, box in self.destination_rows():
                enabled = index == self.next_destination
                label = self.DESTINATIONS[index]
                if not enabled:
                    label += ' - COMPLETE' if index < self.next_destination else ' - LOCKED'
                self.draw_button(box, label, enabled)
            self.draw_button(BACK, 'Back [Esc]')
        self.end_draw()

    def on_key_press(self, key, modifiers):
        if not self.is_paused and key == arcade.key.ESCAPE and self.confirming:
            if self.countdown is None:
                self.confirming = False
            return
        if not self.common_key(key) and key == arcade.key.ENTER:
            self.launch()

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        if self.is_paused:
            self.handle_pause_mouse_press(x, y, button)
            return
        if self.countdown is not None:
            return
        x, y = self.virtual(x, y)
        if self.confirming:
            if self.inside(x, y, self.CANCEL):
                self.confirming = False
            elif self.inside(x, y, self.CONFIRM):
                self.launch()
            return
        if self.inside(x, y, BACK):
            self.leave()
            return
        for index, box in self.destination_rows():
            if index == self.next_destination and self.inside(x, y, box):
                self.confirming = True
                return
