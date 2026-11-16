"""Scene 3 / Act III: Royal Court — c. 1910 (S14 - S20).
Adapted from TheLastIngredientRoyal prototype into the standard BaseGameView architecture.

Scenes Implemented:
  S14  The Girl at the Kitchen Door  - establishing dialogue at the doorway
  S15  The Sun and the Vines        - the sun-and-vine ring heirloom conversation
  S16  Vegetable Soup on the Stove  - cutting on prep board, closed coal range heat management,
                                      dragging boiling pot, stirring in circles, tasting
  S17  When He Returns              - washing hands, mysterious collision in empty kitchen,
                                      seasoning with the salt jar, ladling into bowl
  S18  Soup in the Dining Room      - delivering to small dining room, girl sips soup, line broken
  S19  No Chance to Explain         - spoon falls, ring slips, guards rush in, memory closes
  S20  Six in the Morning           - 06:00 AM wake up in modern kitchen, Crown card fades,
                                      Gear card pulses, transition to Future Neural Lab (S21)

Conforms to APU CT029-3-2 Special Effects, 16:10 / 16:9 adaptive zero-stretch, and Project Directives.
"""
from __future__ import annotations
import math
import json
import random
import struct
import wave
from functools import lru_cache
from pathlib import Path

import arcade
from arcade.types.rect import LRBT

from core.base_view import BaseGameView
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD, ASSETS_DIR
from core.audio import AudioManager
from core.player import Player
from core.dialogue import DialogueBox

from scenes.royal_model import Cooking
from scenes.royal_exploration import KitchenWalker
from scenes.royal_display import Canvas, MapCanvas
from scenes.royal_alignment import StovetopAlignment
from scenes.royal_workstation import RoyalWorkstation
from scenes.royal_departure import RoyalDeparture
from scenes.royal_seasoning import RoyalSeasoning
from scenes.royal_serving import RoyalServing
from scenes.royal_immersion import RoyalImmersion

ROOT = Path(__file__).resolve().parent.parent
PRINCESS_ASSETS = Path(__file__).resolve().parent.parent / "assets" / "princess_v2"
ROYAL_ASSETS = ROOT / "assets" / "royal"

W, H = 1440, 900
SY, SH = 170, 611
GOLD = COLOR_GOLD
WHITE = (244, 235, 214)
MUTED = (187, 180, 164)
DARK = (22, 22, 27)
TEAL = (137, 205, 183)
FONT = ("Segoe UI", "Calibri", "Arial")
LEFT_HOB = (301, 525)
RIGHT_HOB = (410, 522)
SPOON_REST_POS = (912, 560)
RESTING_SPOON_RECT = arcade.XYWH(952, 603, 180, 118)
CLOSEUP_POT = (440, 565)  # first-person pot centre; art and hit zones share it
ONION_SCALE = .55  # board onion; cut lines and discards must use the same value
POT_WIDTH = 72


def box(x, y, w, h, color, border=None):
    arcade.draw_lrbt_rectangle_filled(x, x + w, y, y + h, color)
    if border:
        arcade.draw_lrbt_rectangle_outline(x, x + w, y, y + h, border, 1)


@lru_cache(maxsize=1200)
def cached_text(s, x, y, size, color, width, bold, anchor_x="left", anchor_y="baseline"):
    try:
        safe_size = max(8, int(size or 8))
    except Exception:
        safe_size = 12
    safe_w = max(10, int(width)) if width is not None else None
    return arcade.Text(str(s), x, y, color, safe_size, width=safe_w, multiline=safe_w is not None,
                       font_name=FONT, bold=bold, anchor_x=anchor_x, anchor_y=anchor_y)


def text(s, x, y, size=17, color=WHITE, width=None, bold=False, anchor_x="left", anchor_y="baseline"):
    cached_text(str(s), x, y, size, tuple(color), width, bold, anchor_x, anchor_y).draw()


def image(tex, x, y, w, h=None, alpha=255):
    if h is None:
        h = w * tex.height / tex.width
    else:
        scale = (max if w == W and h == H else min)(w / tex.width, h / tex.height)
        w, h = tex.width * scale, tex.height * scale
    arcade.draw_texture_rect(tex, arcade.XYWH(x, y, w, h), alpha=alpha)


def meter(x, y, w, value, title, color=TEAL):
    text(title, x, y + 18, 13, MUTED)
    box(x, y, w, 7, (66, 62, 58))
    box(x, y, w * max(0.0, min(1.0, value)), 7, color)


class RoyalKitchenView(BaseGameView):
    """Act III Royal Court c. 1910 (S14 - S20)."""

    def __init__(self):
        super().__init__()
        self.audio = AudioManager()
        self.CLOSEUP_POT = CLOSEUP_POT
        self.clock = 0.0
        self.mouse = (0.0, 0.0)
        self.buttons = []
        self.page = "dialogue"  # 'menu' -> 'dialogue' -> 'cooking' -> 'absence' -> 'dining' -> 'end'
        self.speed = 1.0
        self.drag = None
        self.hold = None
        self.lines = []
        self.line = 0
        self.dialogue = DialogueBox(era_hint="royal")
        self.after = None
        self.location = "kitchen"
        self.note = ""
        self.note_time = 0.0
        self.coal_motion = None
        self.inspect_motion = None
        self.dilute_motion = None
        self.drain_motion = None
        self.barley_intro_until = 0
        self.soup_sample = None
        self.cook = Cooking()
        self.chop_item = "onion"
        self.onion_pile_started = None
        self.carrot_pile_started = None
        self.onion_corner_started = None
        self.carrot_corner_started = None
        self.onion_turn_motion = None
        self.carrot_fly = None
        self.chop_motion = None
        self.prep_shake = 0.0
        self.kitchen_mode = "explore"
        self.walker = KitchenWalker()
        self.player = Player(1110, 250, char_id="chef", scale=0.28)
        self.player.footstep_sound = "Walk with leather shoes"
        self.walk_keys = set()
        self.stir_angle = None
        self.stir_travel = 0.0
        self.stir_phase = 0.0
        self.pot_pos = LEFT_HOB
        self.corrupted = False
        self.absence = 0.0
        self.dining_step = 0
        self.reveal = False

        # Cameras
        self.canvas = Canvas(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.ui_camera = arcade.Camera2D(position=(W / 2, H / 2),
                                         projection=arcade.LRBT(-W / 2, W / 2, -H / 2, H / 2))
        self.map_camera = arcade.Camera2D(position=(W / 2, H / 2))

        # Assets
        self.stove_alignment = None
        self.scene_backgrounds = {}
        self.dining = None
        self.menu_backgrounds = {}
        self.map_backgrounds = {}
        self.table_front = None
        self.table_foreground = None
        self.sprites = {}
        self.sounds = {}

        self.coal_motion = None
        self.pour_pose = 0.0
        self._loaded = False
        self._started = False
        self.workstation = None
        self.batch_tray = None
        self.range_hardware = None
        self.departure = None
        self.seasoning = None
        self.serving = None
        self.end_page_timer = 0.0

    def on_show_view(self):
        super().on_show_view()
        if not self._loaded and self.window:
            self._load_royal_assets()
            self._loaded = True
        self.resize_canvas(self.window.width, self.window.height)
        # Directly launch memory when entering from main storyline
        if not self._started:
            self._started=True
            self.start()

    def _load_royal_assets(self):
        self.boil_sprites={name:arcade.load_texture(ROYAL_ASSETS/'boil_sprites_v1'/(name+'.png')) for name in ('coal_bucket','coal_shovel','air_lever','barley','firebox_open')}
        self.boil_sprites['barley'] = arcade.load_texture(ROYAL_ASSETS / 'barley_v2/pearl_barley.png')
        self.food_pieces={name:[arcade.load_texture(path) for path in sorted((ROYAL_ASSETS/'boil_sprites_v1').glob(name+'_piece_*.png'))] for name in ('onion','carrot')}
        self.simmer_sprites={name:arcade.load_texture(ROYAL_ASSETS/'simmer_sprites_v1'/(name+'.png')) for name in ('ladle',)}
        self.soup_check_sprites={name:arcade.load_texture(ROYAL_ASSETS/'soup_check_v1'/(name+'.png')) for name in ('thin','balanced','thick')}
        self.fill_background = arcade.load_texture(ROYAL_ASSETS / "range_fill_closeup_v1.png")
        ctx = self.window.ctx
        self.stove_alignment = None  # v21 lids are painted correctly; no v11 pixel warp.
        self.scene_backgrounds = {
            state: {ratio: arcade.load_texture(ROYAL_ASSETS / f"kitchen_v21_{ratio}.png")
                    for ratio in ("16x10", "16x9")}
            for state in ("raw", "prepared", "boil", "simmer", "transfer")
        }
        self.kitchen = self.scene_backgrounds["raw"]["16x9"]
        self.dining = arcade.load_texture(ROYAL_ASSETS / "dining_1910.png")
        self.menu_backgrounds = self.scene_backgrounds["raw"]
        room = {ratio: arcade.load_texture(ROYAL_ASSETS / f"kitchen_layered_{ratio}.png")
                for ratio in ("16x10", "16x9")}
        self.map_backgrounds = {state: room for state in ("raw", "prepared")}
        self.open_door_backgrounds = {
            ratio: arcade.load_texture(ROYAL_ASSETS / f"kitchen_open_door_matched_{ratio}.png")
            for ratio in ("16x10", "16x9")
        }

        tw, th = self.dining.width, self.dining.height
        self.table_front = self.dining.crop(round(tw * 0.278), round(th * 0.555), round(tw * 0.484), round(th * 0.145))

        self.table_foreground = self.load_shaded_prep_table("prep_table_layer.png")
        self.prep_floor_props = []
        for name, x, bottom, width in (("prep_floor_barrel", 430, 193, 123.5185875), ("prep_sack_crate_mirrored", 1055, 199, 153.6570243648)):
            texture = arcade.load_texture(ROYAL_ASSETS / f"{name}.png")
            left, top, right, alpha_bottom = texture.image.getchannel("A").getbbox()
            texture = texture.crop(left, top, right - left, alpha_bottom - top)
            height = 152.8065 if name == "prep_floor_barrel" else width * texture.height / texture.width
            tint = arcade.types.Color(196, 191, 184) if name == "prep_sack_crate_mirrored" else arcade.types.Color(230, 230, 230)
            self.prep_floor_props.append((texture, x, bottom, width, height, tint))
        self.prepared_table = self.load_shaded_prep_table("prep_table_knife_only.png")
        self.no_jug_table = self.load_shaded_prep_table("prep_table_knife_no_jug.png")
        self.no_salt_table = self.load_shaded_prep_table("prep_table_no_salt.png")


        atlas = arcade.load_texture(ROYAL_ASSETS / "sprites_1910.png")
        names = ["girl", "fallen", "cook", "visitor", "pot", "ring", "carrot", "onion"]
        for i, name in enumerate(names):
            col, row = i % 4, i // 4
            x0 = round(col * atlas.width / 4)
            x1 = round((col + 1) * atlas.width / 4)
            y0, y1 = (0, round(atlas.height * 0.60)) if row == 0 else (round(atlas.height * 0.60), atlas.height)
            tile = atlas.crop(x0, y0, x1 - x0, y1 - y0)
            bounds = tile.image.getchannel("A").point(lambda a: 255 if a > 32 else 0).getbbox()
            if bounds:
                a, b, c, d = bounds
                tile = tile.crop(a, b, c - a, d - b)
            self.sprites[name] = tile
        chef_dir = ROOT / "assets" / "characters" / "chef"
        if (chef_dir / "char_right_idle.png").exists():
            self.sprites["cook"] = arcade.load_texture(chef_dir / "char_right_idle.png")

        self.carrot_frames = [arcade.load_texture(ROYAL_ASSETS/'carrot_cutting_states_v1'/name) for name in (
            'carrot_00_whole.png', 'carrot_01_trimmed.png', 'carrot_02_slice1.png',
            'carrot_03_slice2.png', 'carrot_04_slice3.png', 'carrot_05_slice4.png', 'carrot_06_slice5.png')]
        # Keep complete, identically sized canvases: never trim each animation frame.
        self.onion_knife = arcade.load_texture(ROYAL_ASSETS / 'knife_edge_v2' / 'knife_spine.png')
        self.onion_knife_raised = arcade.load_texture(ROYAL_ASSETS / 'knife_edge_v3' / 'raised_45.png')
        self.onion_frames = [arcade.load_texture(ROYAL_ASSETS/'onion_overhead_v3'/name) for name in (
            'onion_00_whole.png', 'onion_01_top_removed.png', 'onion_02_both_trimmed.png',
            'onion_03_1-4.png', 'onion_04_1-1-3.png', 'onion_05_1-1-1-2.png',
            'onion_06_1-1-1-1-1.png')]
        self.onion_cut_targets = json.loads((ROYAL_ASSETS / 'onion_overhead_v3/cut_targets.json').read_text())
        self.onion_frames.extend(arcade.load_texture(ROYAL_ASSETS / 'onion_crosscut_v1' / ('onion_' + str(index).zfill(2) + '.png')) for index in range(7, 11))
        from scenes.royal_onion import OnionSlices
        self.onion_slices = OnionSlices(self.onion_frames[0])
        from scenes.royal_carrot import CarrotSlices
        self.carrot_slices = CarrotSlices(self.carrot_frames[0])
        self.food_pieces['onion'] = [self.onion_slices.tile(l,t,l+27,t+29) for l,t in ((434,140),(462,170),(490,200),(518,230),(546,260))]
        self.food_pieces['carrot'] = [self.carrot_slices.tile(l,t,l+37,t+27) for l,t in ((216,160),(330,188),(444,188),(558,188),(672,188))]
        props = arcade.load_texture(ROYAL_ASSETS / "props.png")
        for i, name in enumerate(["salt", "empty_bowl", "soup_bowl", "jug", "knife", "tray"]):
            col, row = i % 3, i // 3
            tile = props.crop(col * 512, row * 512, 512, 512)
            bounds = tile.image.getchannel("A").point(lambda a: 255 if a > 32 else 0).getbbox()
            if bounds:
                a, b, c, d = bounds
                tile = tile.crop(a, b, c - a, d - b)
            self.sprites[name] = tile

        from scenes.royal_pot_surface import RoyalPotSurface
        self.pot_renderer = RoyalPotSurface(self, ROYAL_ASSETS)
        self.map_pot_renderer = RoyalPotSurface(self, ROYAL_ASSETS, angle='wide')
        self.sprites["royal_pot"] = self.pot_renderer.texture

        self.sprites["girl_display"] = arcade.load_texture(PRINCESS_ASSETS / "princess_standing_ring_trimmed.png")
        self.sprites["girl"] = arcade.load_texture(PRINCESS_ASSETS / "princess_idle_wearing_ring_trimmed.png")
        self.sprites["girl_seated"] = arcade.load_texture(PRINCESS_ASSETS / "princess_seated_wearing_ring_trimmed.png")
        # Both standing poses use the SAME head pixels, not regenerated colors.
        master = self.sprites["girl"]
        split = round(master.height * 0.37)
        self.princess_head = master.crop(0, 0, master.width, split)
        self.princess_head_fraction = split / master.height
        # One sampled fabric palette for both poses; never copy fold geometry.
        import numpy as np
        from PIL import Image
        reference = np.asarray(master.image.convert("RGBA"))
        def cloth_mask(rgba):
            hsv = np.asarray(Image.fromarray(rgba).convert("RGB").convert("HSV"))
            row = np.arange(rgba.shape[0])[:, None] / rgba.shape[0]
            return ((row > .40) & (row < .88) & (rgba[:, :, 3] > 220)
                    & (hsv[:, :, 0] > 232) & (hsv[:, :, 1] > 45)
                    & (rgba[:, :, 2].astype(float) > rgba[:, :, 1] * 1.02))
        rgb = reference[:, :, :3][cloth_mask(reference)]
        luminance_weights = np.array([.2126, .7152, .0722])
        light = rgb @ luminance_weights
        edges = np.quantile(light, np.linspace(0, 1, 13))
        palette = []
        for low, high in zip(edges[:-1], edges[1:]):
            band = rgb[(light >= low) & (light <= high)]
            colors, counts = np.unique(band, axis=0, return_counts=True)
            palette.append(colors[np.argmax(counts)])
        palette = np.asarray(palette, dtype=np.uint8)
        self.princess_cloth_palette = palette
        for pose in ("girl", "girl_display"):
            pixels = np.array(self.sprites[pose].image.convert("RGBA"))
            mask = cloth_mask(pixels)
            brightness = pixels[:, :, :3][mask] @ luminance_weights
            band = np.clip(np.searchsorted(edges[1:-1], brightness), 0, 11)
            pixels[:, :, :3][mask] = palette[band]
            self.sprites[pose] = arcade.Texture(Image.fromarray(pixels))
        # Reuse original lower-hair pixels, not a palette approximation.
        def tail_mask(rgba):
            hsv = np.asarray(Image.fromarray(rgba).convert("RGB").convert("HSV"))
            row = np.arange(rgba.shape[0])[:, None] / rgba.shape[0]
            col = np.arange(rgba.shape[1])[None, :] / rgba.shape[1]
            return ((row >= self.princess_head_fraction) & (row < .59)
                    & (col > .55) & ((row > .40) | (col > .70))
                    & (rgba[:, :, 3] > 20) & (hsv[:, :, 0] >= 3)
                    & (hsv[:, :, 0] <= 30) & (hsv[:, :, 1] > 55)
                    & (rgba[:, :, 0] < 230)
                    & (rgba[:, :, 2].astype(float) < rgba[:, :, 1] * .97))
        row = np.arange(master.height)[:, None] / master.height
        col = np.arange(master.width)[None, :] / master.width
        # Include the outer silhouette and transparent border, so no old curl
        # outline remains beyond the shared hair. This also shares the back bow.
        tail_border = ((row >= self.princess_head_fraction) & (row < .59) & (col > .70))
        shared_tail = tail_mask(reference) | tail_border
        self.princess_shared_tail_mask = shared_tail
        for pose in ("girl", "girl_display"):
            texture = self.sprites[pose]
            rgba = np.array(texture.image.convert("RGBA").resize(
                (master.width, master.height), Image.Resampling.LANCZOS))
            # Remove that pose's old hair before placing the identical reference.
            old_tail = tail_mask(rgba)
            rgba[old_tail, 3] = 0
            rgba[shared_tail] = reference[shared_tail]
            self.sprites[pose] = arcade.Texture(Image.fromarray(rgba))
        self.princess_bodies = {}
        for pose in ("girl", "girl_display"):
            texture = self.sprites[pose]
            cut = round(texture.height * self.princess_head_fraction)
            self.princess_bodies[pose] = texture.crop(0, cut, texture.width, texture.height-cut)
        chef = self.sprites["cook"]
        cb = chef.image.getchannel("A").point(lambda a: 255 if a > 180 else 0).getbbox()
        if cb:
            chef = chef.crop(cb[0], cb[1], cb[2]-cb[0], cb[3]-cb[1])
        self.sprites["cook"] = chef
        self.ring_closeup = arcade.load_texture(PRINCESS_ASSETS / "ring_hands_closeup.png")
        # Measure opaque chef height; transparent canvas and hat must not inflate the girl.
        chef_image = self.player.textures["right"]["idle"].image
        bounds = chef_image.getchannel("A").point(lambda a: 255 if a > 180 else 0).getbbox()
        sheet = arcade.load_texture(PRINCESS_ASSETS / "princess_walk_away.png")
        self.princess_walk_frames = []
        for index in range(3):
            left = round(index * sheet.width / 3)
            right = round((index + 1) * sheet.width / 3)
            frame = sheet.crop(left, 0, right - left, sheet.height)
            x0, y0, x1, y1 = frame.image.getchannel("A").getbbox()
            self.princess_walk_frames.append(frame.crop(x0, y0, x1 - x0, y1 - y0))
        self.princess_height = (bounds[3] - bounds[1]) * self.player.character_scale * 0.68

        self.make_sounds()
        self.chop_sounds = [arcade.load_sound(ROYAL_ASSETS / 'audio' / f'chop_wood_v1_{i}.wav') for i in range(3)]
        self.workstation=RoyalWorkstation(self,ROYAL_ASSETS)
        self.departure=RoyalDeparture(self,ROYAL_ASSETS)
        self.seasoning=RoyalSeasoning(self,ROYAL_ASSETS)
        self.serving=RoyalServing(self,ROYAL_ASSETS)
        self.immersion=RoyalImmersion(self, ROYAL_ASSETS)
        from scenes.royal_batch_tray import RoyalBatchTray
        from scenes.royal_range_hardware import RoyalRangeHardware
        self.batch_tray=RoyalBatchTray(self,ROYAL_ASSETS)
        self.range_hardware=RoyalRangeHardware(self,ROYAL_ASSETS)

    def make_sounds(self):
        sound_dir = ROYAL_ASSETS / "audio"
        sound_dir.mkdir(exist_ok=True)
        for name, hz, duration in [("click", 520, 0.07), ("chop", 120, 0.06), ("chime", 740, 0.25), ("impact", 170, 0.18)]:
            path = sound_dir / f"{name}.wav"
            if not path.exists():
                n = int(22050 * duration)
                data = [int(2400 * math.sin(2 * math.pi * hz * i / 22050) * (1 - i / n) ** 2) for i in range(n)]
                with wave.open(str(path), "wb") as f:
                    f.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
                    f.writeframes(struct.pack("<" + "h" * n, *data))
            try:
                self.sounds[name] = arcade.load_sound(path)
            except Exception:
                pass

    def play_walk_step(self, before, after, frame_interval):
        previous_frame = int(before / frame_interval)
        current_frame = int(after / frame_interval)
        if current_frame > previous_frame and current_frame % 2:
            self.audio.play_footstep("Walk with leather shoes")

    def ping(self, name="click"):
        if name == 'chop' and self.chop_sounds:
            arcade.play_sound(random.choice(self.chop_sounds), volume=.60)
            return
        if name in self.sounds:
            arcade.play_sound(self.sounds[name], volume=0.35)

    def say(self, message):
        self.note = message
        self.note_time = 5.0

    def button(self, title, x, y, w, h, action, enabled=True):
        if action in {'select_onion','select_carrot','fill','boil','drain','check_soup','leave'} and self.page!='end':return
        if action in {'work_exit','prep_exit'}:
            visible_top = H / 2 + self.window.height / self.canvas.scale / 2
            x,y,w,h=20,visible_top - 75,60,55
            text('‹',x+15,y+10,30,GOLD if enabled else MUTED)
            self.buttons.append((x,y,w,h,action,enabled,'Back'))
            return
        if self.page in {'cooking','departure','delivery'}:
            self.buttons.append((x,y,w,h,action,enabled,title))
            if enabled and x<=self.mouse[0]<=x+w and y<=self.mouse[1]<=y+h:text(title,self.mouse[0]+16,self.mouse[1]+22,14,GOLD)
            return
        hover = x <= self.mouse[0] <= x + w and y <= self.mouse[1] <= y + h
        col = (91, 70, 44) if hover and enabled else (40, 36, 34)
        box(x, y, w, h, col, GOLD if enabled else (87, 82, 75))
        text(title, x + 14, y + h / 2 - 7, 13, GOLD if enabled else (124, 118, 108))
        self.buttons.append((x, y, w, h, action, enabled, title))
    def story(self, lines, after, location="kitchen"):
        self.page = "dialogue"
        self.lines = lines
        self.line = 0
        self.after = after
        self.dialogue_line_started = self.clock
        self.location = location
        self.hold = None
        self.drag = None
        self.dialogue.start_dialogue(lines, on_complete=self._on_story_complete)

    def _on_story_complete(self):
        cb = self.after
        self.after = None
        if cb:
            cb()

    def advance(self):
        if self.page != "dialogue":
            return
        self.ping()
        previous_line = self.line
        self.dialogue.advance()
        self.line = self.dialogue.current_idx
        if self.page == "dialogue" and self.line != previous_line:
            self.dialogue_line_started = self.clock

    def start(self):
        if getattr(self,'batch_tray',None):self.batch_tray.reset()
        if getattr(self,'range_hardware',None):self.range_hardware.reset()
        if getattr(self,"serving",None):self.serving.reset()
        if getattr(self,"seasoning",None):self.seasoning.reset()
        if getattr(self,"departure",None):self.departure.stop()
        if self.workstation:
            self.workstation.stop_input()
            self.workstation.motion=None
            self.workstation.washed=0.0
        self.coal_motion = None
        self.inspect_motion = None
        self.dilute_motion = None
        self.drain_motion = None
        self.barley_intro_until = 0
        self.soup_sample = None
        self.cook = Cooking()
        self.speed = 1.0
        self.corrupted = False
        self.reveal = False
        self.dining_step = 0
        self.pot_pos = LEFT_HOB
        self.note = ""
        self.note_time = 0.0
        self.chop_item = "onion"
        self.onion_pile_started = None
        self.carrot_pile_started = None
        self.onion_corner_started = None
        self.carrot_corner_started = None
        self.onion_turn_motion = None
        self.carrot_fly = None
        self.hold = None
        self.drag = None
        self.chop_motion = None
        self.prep_shake = 0.0
        self.kitchen_mode = "explore"
        self.walker = KitchenWalker()
        self.player = Player(1110, 250, char_id="chef", scale=0.28)
        self.player.footstep_sound = "Walk with leather shoes"
        self.walk_keys.clear()
        self.story([
            ("Girl", "The kitchen is still awake, isn't it?"),
            ("Chef", "Hungry again, Your Highness? Let me make you some warm vegetable soup."),
            ("Girl", "This is Mother's ring... When I grow up, I will give it to my child."),
            ("Chef", "Wait in the dining room, Your Highness. I will bring your soup right over."),
        ], self.begin_cooking)

    def begin_cooking(self):
        self.page = "cooking"
        self.location = "kitchen"
        self.player.facing = "right"
        self.player.sprite.texture = self.player.textures["right"]["idle"]
        self.player.x = self.walker.x
        self.player.y = self.walker.y + self.player.feet_offset
        self.say("WASD / arrow keys: Walk to the central prep table, then press [E] or click Prepare ingredients.")

    def next_fill(self):
        if self.cook.start_fill():
            self.kitchen_mode = "cooking"
            self.walk_keys.clear()
            self.say("Hold Pour to reach the gold range (45%-72%). Add all three ingredients.")

    def begin_boil(self):
        if self.cook.start_boil():
            self.note = ""
            self.note_time = 0.0
        else:
            self.say("Add all three ingredients (Onion, Carrot, Barley). Keep water between 45% and 72%.")

    def taste(self):
        self.ping("chime")
        self.say(self.cook.taste())

    def leave(self):
        if not self.cook.ready:
            self.say(self.cook.taste())
            return
        self._auto_departure_done = True
        self.departure.start()

    def empty_kitchen(self):
        self.page = "absence"
        self.absence = 0.0

    def returned(self):
        self.departure.stop()
        self.corrupted=True
        self.cook.stage='returned'
        self.seasoning.begin_return()

    def returned_dialogue(self):
        self.story([
            ('Sound','A quiet clink came from inside the kitchen.'),
            ('Inner voice','Wait... what was that sound?'),
            ('Memory','The kitchen is empty. The familiar salt jar is still in its usual place.'),
        ],self.returned_map)

    def returned_map(self):
        self.page='cooking';self.kitchen_mode='explore'
        self.workstation.stop_input()
        self.say('Walk to the salt jar on the left side of the table and press E.')

    def season(self):
        if self.seasoning.salt_collected and self.cook.season():
            self.ping("click")
            self.say("The salt is in. Drag the wooden spoon around the pot twice.")

    def deliver(self):
        self.serving.begin_delivery()

    def deliver_story(self):
        if not self.cook.finish():
            return
        self.location = "dining"
        self.dining_step = 0
        self.story([
            ("Chef", "Sorry to keep you waiting. Careful, it is hot."),
            ("Girl", "It smells lovely."),
            ("Girl", "Today it is just as--"),
        ], self.show_scene_19, "dining")

    def show_scene_19(self):
        from scenes.scene_19_view import Scene19View

        self.window.show_view(Scene19View())

    def resize_canvas(self, width, height):
        width = max(1, width)
        height = max(1, height)
        self.canvas = Canvas(width, height)
        self.ui_camera.viewport = arcade.LBWH(0, 0, width, height)
        view_width = width / self.canvas.scale
        view_height = height / self.canvas.scale
        self.ui_camera.position = (W / 2, H / 2)
        self.ui_camera.projection = arcade.LRBT(
            -view_width / 2, view_width / 2,
            -view_height / 2, view_height / 2,
        )
        self.map_canvas = MapCanvas(width, height)
        self.map_camera.viewport = arcade.LBWH(0, 0, width, height)
        self.map_camera.projection = arcade.LRBT(
            -self.map_canvas.view_width / 2, self.map_canvas.view_width / 2,
            -self.map_canvas.view_height / 2, self.map_canvas.view_height / 2,
        )

    def in_map(self):
        return (self.page=='delivery' and self.serving.mode=='walk') or (self.page=='departure' and self.departure.mode=='walk') or (self.page == "cooking" and self.kitchen_mode == "explore")

    def pointer_coords(self, x, y):
        cam = self.map_canvas if self.in_map() else self.canvas
        return cam.unproject(x, y)

    def on_deactivate(self):
        if self.workstation:self.workstation.stop_input()

    def on_hide_view(self):
        if self.workstation:self.workstation.stop_input()

    def on_resize(self, width: int, height: int):
        if getattr(self,"workstation",None):self.workstation.stop_input()
        super().on_resize(width, height)
        if hasattr(self, "ui_camera"):
            self.resize_canvas(width, height)

    def vessel_draw(self, px, py, contents=None, shadow=True):
        if "royal_pot" not in self.sprites:
            return
        renderer = self.map_pot_renderer
        height = POT_WIDTH * renderer.texture.height / renderer.texture.width
        base_y = py - 7
        if shadow:
            arcade.draw_ellipse_filled(px, base_y + 2, POT_WIDTH * .65, 5, (13, 10, 8, 95))
        override = 0 if contents == 'empty' else (.6 if contents in {'soup', 'water'} else None)
        renderer.draw(px, base_y + height / 2, width=POT_WIDTH, water_override=override)

    def pot_draw(self):
        px, py = self.mouse if self.drag == "pot" else self.pot_pos
        py -= SY - (H - SH) / 2
        self.vessel_draw(px, py, shadow=self.drag != "pot")
        if self.page == "cooking" and self.cook.boiled and self.cook.stage == "boil":
            arcade.draw_circle_outline(px, py, 65, GOLD, 2)
            text("Simmering on low heat", 390, 623, 14, GOLD)
        if self.cook.stage in {"boil", "simmer", "away", "returned", "serve", "complete"}:
            for i in range(7):
                phase = (self.clock * 0.24 + i * 0.14) % 1
                sx = px + math.sin(i * 3 + self.clock) * 15
                arcade.draw_circle_filled(sx, py + 19 + phase * 47, 3 + phase * 5, (230, 221, 201, round((1 - phase) * 65)))
            if self.cook.stage == "boil" and self.cook.temperature > 85:
                for i in range(4):
                    a = self.clock * 3 + i * 2
                    arcade.draw_circle_outline(px + math.sin(a) * 20, py + 11 + math.cos(a) * 3, 2 + (a % 1) * 2, (235, 220, 188, 145), 1)

    def salt_draw(self):
        x, y = 554, 370
        if self.corrupted:
            arcade.draw_line(x - 15, y + 18, x - 6, y + 18, (92, 123, 172), 2)
        if self.page == "cooking" and self.cook.stage == "returned":
            arcade.draw_circle_outline(x, y, 36, GOLD, 2)
            text("Last spoon of salt", x - 39, y + 43, 12, GOLD)

    def bowl_draw(self, x, y, fill=0):
        image(self.sprites["soup_bowl" if fill else "empty_bowl"], x, y, 76, 43)

    def actor(self, name, x, y, height):
        if name in self.sprites:
            tex = self.sprites[name]
            if name in ("girl", "girl_display"):
                # Fixed full-body registration keeps head size/position invariant.
                master = self.sprites["girl"]
                width = height * master.width / master.height
                top = y + height / 2
                head_h = height * self.princess_head_fraction
                body_h = height - head_h
                arcade.draw_texture_rect(self.princess_bodies[name],
                    arcade.XYWH(x, top-head_h-body_h/2, width, body_h))
                arcade.draw_texture_rect(self.princess_head,
                    arcade.XYWH(x, top-head_h/2, width, head_h))
                return
            image(tex, x, y, height * tex.width / tex.height, height)

    @property
    def princess_showing_ring(self):
        """Show the heirloom only during the princess's line about her ring."""
        return (self.page == "dialogue" and self.location == "kitchen"
                and self.cook.stage == "prep" and not self.reveal
                and self.line == 2)

    def world(self):
        if self.location == "kitchen":
            # Canonical exploration map is the absolute standard!
            opening_dialogue = self.page == "dialogue" and not self.reveal and self.cook.stage == "prep"
            princess_leaving = opening_dialogue and self.line == len(self.lines) - 1
            returned_door_open = self.cook.stage == "returned" and self.walker.door_open
            self.draw_kitchen_map_base(door_fully_open=princess_leaving or returned_door_open)

            if opening_dialogue:
                # Girl stands in front of the door in the canonical world coordinate
                pose = "girl_display" if self.princess_showing_ring else "girl"
                if princess_leaving:
                    self.draw_princess_exit()
                else:
                    self.actor(pose, 1240, 250 + self.princess_height / 2, self.princess_height)

                # Chef stands near the doorway facing the girl
                self.player.facing = "right"
                self.player.x = 1130
                self.player.y = 250 + self.player.feet_offset
                self.player.sprite.texture = self.player.textures["right"]["idle"]
                self.player.sprite.center_x = self.player.x
                self.player.sprite.center_y = self.player.y
                self.player.sprite_list.draw()

                if self.princess_showing_ring:
                    self.ui_camera.use()
                    # A wordless hand insert makes the heirloom legible at map scale.
                    box(74, 420, 492, 316, (25, 23, 29, 245), GOLD)
                    image(self.ring_closeup, 320, 578, 480, 304)
        elif self.location == "dining":
            self.ui_camera.use()
            image(self.serving.dining, 720, 450, W, H)
            self.actor("girl_seated", 900, 469, 198)
            self.serving.draw_dining_chef()
            image(self.serving.table_front, 720, 450, W, H)
            self.serving.draw_bowl_at(*self.serving.TABLE_SOUP)

    def draw_princess_exit(self):
        self.draw_hall_exit(
            self.princess_walk_frames, self.clock - self.dialogue_line_started,
            (1240, 250), self.princess_height * 1.10,
        )

    def draw_hall_exit(self, frames, elapsed, start, start_height):
        duration = RoyalDeparture.HALL_EXIT_DURATION
        if elapsed >= duration:
            return
        progress = min(1, max(0, (elapsed - .16) / (duration - .16)))
        cycle = (0, 1, 0, 2)
        frame = frames[cycle[int(elapsed / .14) % len(cycle)]]
        start_x, start_y = start
        x = start_x + (1177 - start_x) * min(1, progress * 2)
        feet_y = start_y + (463 - start_y) * progress
        height = start_height * (1 - .35 * progress)
        alpha = round(255 * min(1, (1 - progress) / .22))
        image(frame, x, feet_y + height / 2, height * frame.width / frame.height, height, alpha)

    def header(self, subtitle):
        pass

    def footer(self, speaker, line, advance=False):
        pass

    def panel(self):
        c = self.cook
        stage = c.stage
        box(27, 548, 263, 216, (24, 24, 29, 240), (114, 88, 51))
        names = {"prep": "01 Prepare", "fill": "02 Water & ingredients", "boil": "03 Bring to a boil",
                 "simmer": "04 Gentle hob", "returned": "05 Final seasoning", "serve": "06 Serve"}
        text(names.get(stage, "Royal memory"), 45, 730, 18, GOLD, bold=True)
        if stage == "prep":
            text("Onion: " + str(c.cuts["onion"]) + " / " + str(c.cut_goal("onion")), 45, 692, 17)
            text("Carrot: " + str(c.cuts["carrot"]) + " / " + str(c.cut_goal("carrot")), 45, 660, 17)
            text("Select food; click the gold line.", 45, 624, 12, MUTED)
            self.button("Finish prep", 45, 566, 220, 39, "fill", c.prepared and self.chop_motion is None)
        elif stage == "fill":
            meter(46, 678, 220, c.water, "Water: " + str(round(c.water * 100)) + "%")
            box(46 + 220 * 0.45, 676, 220 * 0.27, 11, (221, 181, 102, 75))
            text("Ingredients: " + str(len(c.ingredients)) + " / 3", 46, 645, 17)
            self.button("Hold Pour", 45, 594, 103, 36, "pour")
            self.button("Drain", 158, 594, 107, 36, "drain")
            self.button("Heat soup", 45, 552, 220, 36, "boil", 0.45 <= c.water <= 0.72 and len(c.ingredients) == 3)
        elif stage == "boil":
            meter(46, 682, 220, (c.temperature - 18) / 82, "Bubbles and heat")
            text("Coal: " + ["Low", "Medium", "High"][c.heat], 46, 649, 16)
            text(f"Air: {c.air_opening:.0%}", 46, 621, 16)
            self.button("Coal", 45, 570, 68, 35, "fuel")
            self.button("Air -", 120, 570, 68, 35, "raise")
            self.button("Air +", 195, 570, 68, 35, "lower")
        elif stage == "simmer":
            meter(46, 683, 220, c.softness, "Tenderness")
            meter(46, 637, 220, c.thickness, "Thickness | target 25%-75%")
            text("Hob heat: " + ("Gentle" if c.simmer_heat > 0.45 else "Weak"), 46, 605, 15)
            self.button("Coal", 45, 565, 68, 35, "fuel")
            self.button("Air -", 120, 565, 68, 35, "raise")
            self.button("Air +", 195, 565, 80, 35, "lower")
        elif stage == "returned":
            text("The kitchen is empty.", 46, 684, 17)
            text("Click the salt jar at the left end of the table.", 46, 646, 15, MUTED, width=220)
            text("A fixed memory: its outcome cannot change here.", 46, 584, 13, MUTED, width=215)
        elif stage == "serve":
            meter(46, 680, 220, c.served, "Bowl fill")
            self.button("Hold Ladle", 45, 606, 220, 40, "ladle")
            self.button("To dining room", 45, 555, 220, 40, "deliver", c.served >= 1)

        if stage == "fill":
            for i, (key, title) in enumerate([("onion", "Onion"), ("carrot", "Carrot"), ("barley", "Barley")]):
                self.button(("Added " if key in c.ingredients else "Add ") + title, 620 + i * 156, 245, 145, 42, "add_" + key, key not in c.ingredients)
        if stage == "prep":
            if getattr(self, "prep_shake", 0.0) > 0:
                import random
                sox = random.uniform(-self.prep_shake, self.prep_shake)
                soy = random.uniform(-self.prep_shake, self.prep_shake)
                self.ui_camera.position = (W / 2 + sox, H / 2 + soy)
                self.ui_camera.use()
            self.prep_board()
            if getattr(self, "prep_shake", 0.0) > 0:
                self.ui_camera.position = (W / 2, H / 2)
                self.ui_camera.use()
        if stage == "simmer":
            self.button("Taste", 372, 250, 113, 40, "taste")
            self.button("Add water", 498, 250, 128, 40, "water")
            self.button("Tend range", 639, 250, 128, 40, "embers")
            self.button("Wash hands", 780, 250, 138, 40, "leave", c.ready)
        if stage == "boil" and c.boiled:
            arcade.draw_circle_outline(*RIGHT_HOB, 45, GOLD, 2)
            text("Gentle hob", 340, 605, 14, GOLD)

    def knife_target(self, item=None, n=None):
        item = item or self.chop_item
        n = self.cook.cuts[item] if n is None else n
        if item == 'onion':
            if n < 2:
                return 740 + ((630 if n == 0 else 350) - 500) * ONION_SCALE
            if n < 6:
                return 740 + (350 + (n - 1) * 56 - 500) * ONION_SCALE
            return 740 - (290 - (n - 6) * 60 - 210) * ONION_SCALE
        if n == 0: return 740 + (140 - 520) * .30
        if n < 6: return 740 + (270 + (n - 1) * 130 - 520) * .30
        if n < 8: return 740 + ((177 if n == 6 else 253) - 210) * .30
        return 740 + ((195 if n == 8 else 235) - 210) * .30

    def chop_hit(self, x, y):
        """Blade-aware click test. The carrot's blade is 280px (440px once turned)
        tall, so a band around the gold line mostly hit empty board while the
        visible blade did nothing. Food spans x 584..1002, y 292..482."""
        item = self.chop_item
        if self.cook.cuts[item] >= self.cook.cut_goal(item):
            return False
        if not 190 < y < 600:
            return False
        return abs(x - self.knife_target()) <= 40

    def prep_board(self):
        count = self.cook.cuts[self.chop_item]
        goal = self.cook.cut_goal(self.chop_item)
        stroke = self.chop_motion
        frames = self.onion_frames if self.chop_item == 'onion' else self.carrot_frames
        if self.chop_item in {'onion','carrot'}:
            is_onion = self.chop_item == 'onion'
            turned = self.cook.onion_turned if is_onion else self.cook.carrot_turned
            pile_started = self.onion_pile_started if is_onion else self.carrot_pile_started
            renderer = self.onion_slices if is_onion else self.carrot_slices
            corner_start = self.onion_corner_started if is_onion else self.carrot_corner_started
            corner_t = (self.clock - corner_start) if corner_start is not None else None
            if self.onion_turn_motion is not None:
                progress = min(1, self.onion_turn_motion / .45)
                angle = 90 * progress * progress * (3 - 2 * progress)
                # Lift the piece off the board during the flip so it reads as the
                # cook picking it up and turning it over, not a sticker spinning.
                lift = math.sin(progress * math.pi) * 26
            else:
                angle = 90 if turned else 0
                lift = 0
            impact_age = stroke['time'] - .16 if stroke else -1
            shake = math.sin(impact_age * 160) * 1.6 * max(0, 1-impact_age/.12) if 0 <= impact_age < .12 else 0
            # Draw persistent onion mise-en-place cleanly ON the wooden cutting board (never floating)
            if self.chop_item == 'carrot' and self.cook.cuts['onion'] >= 10:
                shift_start = getattr(self, 'onion_shift_started', None)
                if shift_start is None:
                    pile_cx, pile_cy = 450, 435
                else:
                    p = min(1.0, max(0.0, (self.clock - shift_start) / 0.35))
                    ease = p * p * (3 - 2 * p)
                    pile_cx = 740 + (450 - 740) * ease
                    pile_cy = 400 + (435 - 400) * ease
                self.onion_slices.draw_pile((pile_cx, pile_cy), scale=0.40, progress=1.0)
            if self.chop_item == 'carrot' and self.cook.cuts['onion'] >= 1:
                self.onion_slices.draw_discards(self.cook.cuts['onion'], center=(740, 400), scale=ONION_SCALE)
            if self.chop_item == 'onion' and self.cook.cuts['carrot'] >= 1:
                self.carrot_slices.draw_tip_discard(self.cook.cuts['carrot'], center=(740, 390), scale=0.30)

            if is_onion:
                renderer.draw(count, angle, center=(740,400+shake-lift), scale=ONION_SCALE,
                    pile_progress=min(1,(self.clock-pile_started)/.55) if pile_started is not None else 1,
                    stroke=stroke, corner_t=corner_t)
            else:
                if count >= 8:
                    g2_elapsed = self.clock - getattr(self, 'carrot_group2_shift_started', self.clock)
                    g2_prog = min(1.0, max(0.0, g2_elapsed / 0.40))
                else:
                    g2_prog = 0.0
                renderer.draw(count, angle, center=(740,390+shake-lift),
                    pile_progress=min(1,(self.clock-pile_started)/.55) if pile_started is not None else 1,
                    group2_progress=g2_prog, stroke=stroke, corner_t=corner_t)
            if self.onion_turn_motion is not None:
                return
            # Carrot flying in from the left tray onto the board after the player
            # clicks it. It stays upright at the start and lies down as it lands.
            if self.carrot_fly is not None:
                fp = min(1.0, self.carrot_fly / 0.40)
                fe = fp * fp * (3 - 2 * fp)
                fx = 120 + (740 - 120) * fe
                fy = 370 + (390 - 370) * fe
                fw = 200 + (300 - 200) * fe
                fh = 84 + (126 - 84) * fe
                arcade.draw_texture_rect(self.carrot_frames[0],
                    arcade.XYWH(fx, fy, fw, fh), angle=0)
        else:
            image(frames[count], 740, 400, 600)
        if count >= goal and stroke is None:
            return
        target = stroke['x'] if stroke else self.knife_target()
        elapsed = stroke['time'] if stroke else 0
        if stroke is None:
            arcade.draw_line(target, 345, target, 425, GOLD, 2)
        depth = min(1, elapsed / .16) if elapsed < .16 else max(0, 1 - (elapsed - .16) / .24)
        if self.chop_item in {'onion','carrot'}:
            # View along the spine: screen-vertical blade, handle toward the player.
            # Raised pose shows a little blade face, the impact pose shows its spine.
            knife = self.onion_knife if depth >= .55 else self.onion_knife_raised
            height = 260 + 40 * depth
            width = height * knife.width / knife.height
            center_y = 400 + 48 * (1 - depth)
            if is_onion:
                center_y -= 20  # both halves: blade was floating above the bulb
                if turned:
                    center_y -= 32  # turned onion sits lower (y 310..478)
            if self.chop_item == 'carrot':
                # Keep a stable spine silhouette: actual downward travel, not growth.
                knife = self.onion_knife
                height = 280
                width = height * knife.width / knife.height
                if stroke is None:
                    travel = 0
                elif elapsed < .16:
                    travel = (elapsed / .16) ** 2
                else:
                    recovery = min(1, (elapsed - .16) / .24)
                    travel = 1 - recovery * recovery * (3 - 2 * recovery)
                if turned:
                    center_y = 390 - 25 * travel
                else:
                    center_y = 442 - 64 * travel
            arcade.draw_texture_rect(knife, arcade.XYWH(target, center_y, width, height))
        else:
            knife = self.sprites['knife']
            arcade.draw_texture_rect(knife, arcade.XYWH(target, 477 - 48 * depth, 142, 142 * knife.height / knife.width), angle=-90)
        if stroke and .16 <= elapsed < .40:
            age = elapsed - .16
            fade = max(0, 1 - age / .24)
            color = (246, 235, 194) if self.chop_item == 'onion' else (242, 151, 56)
            # A brief contact accent and tiny food flecks, never a full-screen flash.
            if age < .075:
                arcade.draw_ellipse_outline(target, 396, 14+age*160, 5+age*40, (*color,round(150*fade)), 1.5)
            for j in range(5):
                vx = (-1 if j%2 else 1) * (24+j*14)
                vy = 44+(j%3)*17
                arcade.draw_circle_filled(target+vx*age,396+vy*age-160*age*age,1.2+(j%2)*.6,(*color,round(210*fade)))

    def fill_closeup(self, heating=False):
        # The same registered pot cutout, enlarged for the first-person view.
        image(self.fill_background,720,450,1440,900)
        simmer=self.cook.stage in {'simmer','away'}
        self.draw_spoon_rest()
        if not simmer:
            self.draw_resting_spoon()
        px,py=CLOSEUP_POT
        mx,my,rx,ry=self.pot_renderer.draw(px,py,heating=heating)
        if not heating:self.range_hardware.draw_air()
        if heating:
            if simmer:self.simmer_controls()
            else:
                jug = self.sprites['jug']
                pose = self.pour_pose
                arcade.draw_texture_rect(jug,arcade.XYWH(1230-420*pose,620+75*pose,180,180*jug.height/jug.width),angle=-35*pose)
                self.boil_controls()
            return
        pose=self.pour_pose;jug=self.sprites['jug'];jx=1230-420*pose;jy=620+75*pose
        if self.hold=='pour' and not self.is_paused and self.cook.water<.85 and not self.cook.ingredients:
            # A visible stream connects the tilted jug spout to the pot opening.
            sx,sy=jx-107,jy+13;ex,ey=mx+45,my
            points=[(sx+(ex-sx)*i/16,sy+(ey-sy)*(i/16)**1.4) for i in range(17)]
            arcade.draw_line_strip(points,(129,188,211,210),8)
            arcade.draw_line_strip(points,(216,237,241,220),2)
            for i in range(3):
                r=8+((self.clock*28+i*9)%28)
                arcade.draw_ellipse_outline(ex,ey,r*2,r*.35,(181,218,225,145),1)
        arcade.draw_texture_rect(jug,arcade.XYWH(jx,jy,180,180*jug.height/jug.width),angle=-35*pose)
        if self.hold!='pour':None
        None
        None
        None
        None
        status='Too much water - drain a little' if self.cook.water>.72 else ('Enough water' if self.cook.water>=.45 else 'Fill to the green zone')
        None
        self.button('Drain a little',55,650,190,42,'drain')
        self.workstation.fill_ingredients()
        from scenes.royal_water_feedback import draw_water_feedback
        draw_water_feedback(self,mx,my,rx,ry)
        ready=.45<=self.cook.water<=.72 and len(self.cook.ingredients)==3
        self.button('Start heating',1080,105,290,46,'boil',ready)
        None

    def boil_controls(self):
        self.range_hardware.draw()
        c=self.cook
        if c.spill_cooldown>0:
            for i in range(8):arcade.draw_circle_filled(350+i*27,490-((self.clock*65+i*13)%65),3,(170,194,182,150))

    def draw_spoon_rest(self):
        image(self.departure.tex['spoon_rest'], *SPOON_REST_POS, 170, 75)

    def spoon_rect(self):
        if self.hold == 'stir':
            x, y = self.mouse
            spoon = self.simmer_sprites['ladle']
            return arcade.XYWH(x + 80, y + 65, 220, 220 * spoon.height / spoon.width)
        return RESTING_SPOON_RECT

    def draw_resting_spoon(self):
        arcade.draw_texture_rect(self.simmer_sprites['ladle'], RESTING_SPOON_RECT)

    def simmer_controls(self):
        c=self.cook
        None
        None
        None
        None
        None
        pose=0.0
        if self.dilute_motion is not None:
            t=self.dilute_motion
            pose=min(1,t/.3) if t<.3 else (1 if t<.8 else max(0,1-(t-.8)/.4))
        jx,jy=1230-420*pose,620+75*pose
        jug=self.sprites['jug']
        if self.dilute_motion is not None and .3<=self.dilute_motion<.8:
            points=[(jx-107+(CLOSEUP_POT[0]-(jx-107))*i/12,jy+9+(615-(jy+9))*(i/12)**1.4) for i in range(13)]
            arcade.draw_line_strip(points,(148,203,224,210),5)
            arcade.draw_ellipse_outline(CLOSEUP_POT[0],615,45,10,(187,220,224),1)
        arcade.draw_texture_rect(jug,arcade.XYWH(jx,jy,180,180*jug.height/jug.width),angle=-35*pose)
        self.range_hardware.draw()
        if self.page == 'departure':
            self.departure.draw_spoon_putdown(RESTING_SPOON_RECT)
            return
        if self.inspect_motion is not None:
            t=self.inspect_motion
            lift=min(1,t/.5) if t<.5 else (1 if t<2.3 else max(0,1-(t-2.3)/.5))
            sample=self.soup_sample
            image(self.soup_check_sprites[sample['kind']],1100-410*lift,680+35*lift,330,230)
            if lift>.8:
                None
                None
                None
        elif self.hold=='stir':
            arcade.draw_texture_rect(self.simmer_sprites['ladle'], self.spoon_rect())
        else:
            self.draw_resting_spoon()
        None
        self.button('Check soup',760,130,180,45,'check_soup',self.inspect_motion is None and self.dilute_motion is None)
        can_add = c.can_add_water and self.dilute_motion is None and self.inspect_motion is None
        if c.water < 0.65 or c.thickness > 0.60:
            self.button('Add water', 960, 130, 150, 45, 'water', can_add)
            self.button('Finish simmering', 1130, 130, 260, 45, 'leave', c.ready and self.inspect_motion is None and self.dilute_motion is None)
        else:
            self.button('Finish simmering', 960, 130, 360, 45, 'leave', c.ready and self.inspect_motion is None and self.dilute_motion is None)

    def check_soup(self):
        if self.cook.stage!='simmer' or self.inspect_motion is not None or self.dilute_motion is not None:return
        c=self.cook
        kind=c.inspect_consistency()
        sprite_key = 'thick' if kind == 'scorched' else kind
        if kind == 'scorched':
            advice = 'Scorching! Add water immediately and turn vent to Low!'
        elif kind == 'thick':
            advice = 'Add a small splash of water.'
        elif kind == 'thin':
            advice = 'Simmer a little longer.'
        elif c.softness < 1.0:
            advice = 'Vegetables still firm. Keep simmering on gentle heat.'
        else:
            advice = 'Vegetables are tender and broth is rich. Ready to finish!'
        self.soup_sample={'kind':sprite_key,'advice':advice}
        self.inspect_motion=0.0;self.hold=None;self.taste()

    def prep_closeup(self):
        self.immersion.prep_background()

    def scene_state(self):
        if self.drag == "pot":
            return "transfer"
        if self.cook.stage in {"prep", "fill"}:
            return "prepared" if self.cook.prepared else "raw"
        if self.cook.stage == "boil":
            return "boil"
        return "simmer"

    def _draw_world_prompt(self, wx, wy, text, scale=1.0, highlight=False, action=None):
        """Draw an interactive prompt card matching Scene 7 styling with popup jump effect."""
        if scale < 0.2:
            return
        scale = max(0.2, min(1.3, scale))
        bw = max(260.0, (len(text) * 9.6 + 50.0)) * scale
        bh = 46.0 * scale

        mx, my = self.mouse
        hover = (wx - bw / 2 <= mx <= wx + bw / 2 and wy - bh / 2 <= my <= wy + bh / 2)

        if hover:
            bg_col = (45, 52, 70, 240)
            border_col = (255, 225, 140)
            border_width = 2.4
        elif highlight:
            bg_col = (26, 32, 48, 230)
            border_col = GOLD
            border_width = 2.0
        else:
            bg_col = (20, 24, 34, 215)
            border_col = (140, 180, 220)
            border_width = 1.4

        # Soft drop shadow for floating depth
        arcade.draw_rect_filled(arcade.XYWH(wx, wy - 4 * scale, bw + 6 * scale, bh + 4 * scale), (8, 10, 15, 120))

        # Main popup card
        arcade.draw_rect_filled(arcade.XYWH(wx, wy, bw, bh), bg_col)
        arcade.draw_rect_outline(arcade.XYWH(wx, wy, bw, bh), border_col, border_width)

        # Dedicated [E] keycap badge on the left side of the prompt
        badge_w = 32.0 * scale
        badge_h = 30.0 * scale
        badge_x = wx - bw / 2 + 26.0 * scale
        badge_y = wy
        arcade.draw_rect_filled(arcade.XYWH(badge_x, badge_y - 2 * scale, badge_w, badge_h), (12, 14, 20, 200))
        arcade.draw_rect_filled(arcade.XYWH(badge_x, badge_y, badge_w, badge_h), GOLD if highlight or hover else (240, 245, 255))
        arcade.draw_rect_outline(arcade.XYWH(badge_x, badge_y, badge_w, badge_h), (255, 255, 255), 1.2)
        cached_text("E", badge_x - 5 * scale, badge_y - 7 * scale, max(9, int(13 * scale)), (20, 22, 30), None, True).draw()

        # Action text on the right of the badge
        label_text = text[4:] if text.startswith("[E] ") else (text[3:] if text.startswith("[E]") else text)
        text_x = wx + 16.0 * scale
        text_col = (255, 255, 255) if (highlight or hover) else (230, 240, 255)
        text_w = len(label_text) * 7.5 * scale
        cached_text(label_text, text_x - text_w / 2, wy - 6 * scale, max(9, int(12 * scale)), text_col, None, True).draw()

        # Register button so clicking the popup directly triggers interaction
        if action:
            self.buttons.append((wx - bw / 2, wy - bh / 2, bw, bh, action, True, text))

    def load_shaded_prep_table(self, filename):
        import numpy as np
        from PIL import Image

        texture = arcade.load_texture(ROYAL_ASSETS / filename)
        pixels = np.array(texture.image.convert("RGBA"))
        rows = np.linspace(0, 1, texture.height)
        shade = 1 - .14 * np.clip((rows - .65) / .35, 0, 1)
        pixels[:, :, :3] = np.rint(pixels[:, :, :3] * shade[:, None, None])
        return arcade.Texture(Image.fromarray(pixels))

    def draw_prep_table(self):
        width = 580
        if self.seasoning.salt_collected:
            texture = self.no_salt_table
        elif self.cook.stage in {"away", "returned", "serve", "complete"}:
            texture = self.no_jug_table
        elif self.cook.prepared:
            texture = self.prepared_table
        else:
            texture = self.table_foreground
        height = width * texture.height / texture.width
        # Soft contact shadows beneath the table legs, barrel and sack crate.
        for x, y, shadow_width, shadow_height, strength in (
            (502, 201, 76, 19, 1),
            (997, 201, 76, 19, 1),
            (379, 194, 116, 24, 2),
            (1055, 199, 128, 22, 2),
        ):
            for scale, alpha in ((1.0, 8), (.82, 10), (.65, 13)):
                arcade.draw_ellipse_filled(
                    x, y, shadow_width * scale, shadow_height * scale,
                    (24, 16, 12, alpha * strength),
                )
        for prop, x, bottom, prop_width, prop_height, tint in self.prep_floor_props:
            arcade.draw_texture_rect(prop, arcade.XYWH(x, bottom + prop_height / 2, prop_width, prop_height), color=tint)
        image(texture, 750, 200 + height / 2, width)

    def draw_kitchen_map_base(self, include_table=True, door_fully_open=False):
        """Canonical exploration background map - the single source of truth."""
        self.map_camera.use()
        variant = "16x9" if self.window.width / max(1, self.window.height) >= 1.77 else "16x10"
        state = "prepared" if self.cook.prepared else "raw"
        tex = self.open_door_backgrounds[variant] if door_fully_open else self.map_backgrounds[state][variant]
        scale = W / tex.width
        if self.stove_alignment:
            self.stove_alignment.draw(tex, W / 2, H / 2, tex.width * scale, tex.height * scale)
        else:
            image(tex, W / 2, H / 2, tex.width * scale, tex.height * scale)

        self.vessel_draw(self.pot_pos[0], self.pot_pos[1] - SY + (H - SH) / 2)

        if include_table:
            self.draw_prep_table()

    def exploration_draw(self):
        open_door = self.walker.door_open
        self.draw_kitchen_map_base(include_table=self.walker.y < 220, door_fully_open=open_door)
        p = self.walker
        self.player.x = p.x
        self.player.y = p.y + self.player.feet_offset
        self.player.sprite.center_x = self.player.x
        self.player.sprite.center_y = self.player.y
        self.player.sprite_list.draw()
        if self.walker.y >= 220:
            self.draw_prep_table()
        # Check active interactive stations and render Scene-7 style popup prompt
        anim = getattr(self, "prompt_anim", 0.0)
        if anim > 0.01:
            pop_bounce = math.sin(anim * math.pi * 0.5)
            overshoot = 0.20 * math.sin(anim * math.pi) * (1.0 - anim)
            float_y = 5.0 * math.sin(self.clock * 4.0)
            pulse = 1.0 + 0.04 * math.sin(self.clock * 5.0)
            scale = (pop_bounce + overshoot) * pulse
            jump_y = (1.0 - pop_bounce) * (-22.0) + float_y

            if self.walker.near("door"):
                wx, wy = 1195, 530 + jump_y
                door_label = "[E] Close Door" if self.walker.door_open else "[E] Open Door"
                self._draw_world_prompt(wx, wy, door_label, scale=scale, highlight=True, action="toggle_door")
            elif not self.cook.prepared:
                wy_offset = 110 if self.walker.y >= 220 else 0
                wx, wy = 790, 410 + wy_offset + jump_y
                self._draw_world_prompt(wx, wy, "[E] Prepare Ingredients", scale=scale, highlight=True, action="prep_enter")
            elif self.cook.stage == "prep":
                wx, wy = 330, 550 + jump_y
                self._draw_world_prompt(wx, wy, "[E] Start Cooking on Stove", scale=scale, highlight=True, action="range_enter")
            elif self.cook.stage == "returned":
                wx, wy = 330, 550 + jump_y
                if self.seasoning.salt_collected and self.walker.near("range"):
                    self._draw_world_prompt(wx, wy, "[E] Add Final Spoon of Salt", scale=scale, highlight=True, action="range_enter")
                elif not self.seasoning.salt_collected and self.seasoning.near_salt():
                    sx, sy = self.seasoning.SALT_POS
                    self._draw_world_prompt(sx, sy + 65 + jump_y, "[E] Take Salt", scale=scale, highlight=True, action="take_salt")
            else:
                wx, wy = 330, 550 + jump_y
                self._draw_world_prompt(wx, wy, "[E] Resume Cooking", scale=scale, highlight=True, action="range_enter")

    # =========================================================================
    # DRAW LOOP
    # =========================================================================
    def on_draw(self):
        self.clear((15, 17, 22))
        self.buttons = []
        self.ui_camera.use()

        if self.page=='delivery':
            self.serving.draw_delivery()
            self.immersion.overlay()
            self.draw_pause_overlay()
            return
        if self.page=='return_entry':
            self.seasoning.draw_return()
            self.immersion.overlay()
            self.draw_pause_overlay()
            return
        if self.page in {'departure','absence'}:
            self.departure.draw()
            self.immersion.overlay()
            self.draw_pause_overlay()
            return
        if self.page=='wash':
            self.workstation.wash_draw()
            self.immersion.overlay()
            self.draw_pause_overlay()
            return
        if self.in_map():
            self.exploration_draw()
            self.immersion.overlay()
            self.draw_pause_overlay()
            return
        if self.page=='cooking' and self.cook.stage=='returned':
            self.seasoning.draw()
            self.immersion.overlay()
            self.draw_pause_overlay()
            return
        if self.page=='cooking' and self.cook.stage=='serve':
            self.serving.draw()
            self.immersion.overlay()
            self.draw_pause_overlay()
            return
        if self.page=='cooking' and self.cook.stage in {'returned','serve'}:
            self.workstation.finish_draw()
            self.button('Back to kitchen',1170,828,220,40,'work_exit')
            self.immersion.overlay()
            self.draw_pause_overlay()
            return

        if self.page == 'cooking' and self.cook.stage in {'fill','boil','simmer'}:
            self.fill_closeup(heating=self.cook.stage in {'boil','simmer'})
            self.button('Back to kitchen',1170,828,220,40,'work_exit')
            self.immersion.overlay()
            self.draw_pause_overlay()
            return

        if self.page == "cooking" and self.cook.stage == "prep":
            if self.kitchen_mode == "explore":
                self.exploration_draw()
            else:
                self.prep_closeup()
            self.immersion.overlay()
            self.draw_pause_overlay()
            return

        self.location = "dining" if self.page == "dialogue" and self.location == "dining" else self.location
        if self.location != "dark":
            self.world()
        else:
            # 06:00 Modern Awakening Cutscene (S20)
            box(0, SY, W, SH, (14, 18, 26))
            arcade.draw_circle_outline(720, 490, 95, (155, 150, 140), 3)
            for i in range(12):
                a = i * math.pi / 6
                arcade.draw_circle_filled(720 + 80 * math.sin(a), 490 + 80 * math.cos(a), 2, MUTED)
            arcade.draw_line(720, 490, 720, 560, WHITE, 3)
            arcade.draw_line(720, 490, 720, 435, WHITE, 4)
            text("06:00", 675, 359, 27, GOLD)

        if self.page == "cooking":
            self.header("Watch the cooking state. Mistakes can be corrected.")
            self.panel()
            instructions = {
                "prep": "Select a vegetable, then cut along the gold lines on the enlarged board.",
                "fill": "Reach the water target and add all three ingredients before heating.",
                "boil": "Open the air vent to heat the soup. Reduce it once the soup boils.",
                "simmer": "Hold near pot and stir in circles. Taste, adjust, then wash hands when ready.",
                "returned": "Follow the remembered action: Add the last spoon of salt.",
                "serve": "Hold Ladle to fill the bowl, then carry it to the separate dining room."
            }
            self.footer("Current task", self.note if self.note_time > 0 else instructions.get(self.cook.stage, ""))
            if self.hold == "stir":
                arcade.draw_line(self.pot_pos[0], self.pot_pos[1] + 17, *self.mouse, GOLD, 4)
            if self.cook.stage == "simmer" and self.cook.unstirred > 12:
                text("Food is settling. Give it a gentle stir.", 393, 704, 19, GOLD)
        elif self.page == "dialogue":
            self.ui_camera.use()
            self.dialogue.draw()
        elif self.page == "absence":
            arcade.draw_lrbt_rectangle_filled(0, W, 0, 110, (11, 8, 14, 225))
            arcade.draw_line(0, 110, W, 110, (218, 165, 32, 140), 1.5)
            text("❖   EMPTY KITCHEN   ❖", W / 2, 82, 12, GOLD, bold=True, anchor_x="center")
            text("The soup stays on gentle heat. Footsteps approach along the corridor...", W / 2, 48, 16, WHITE, anchor_x="center")
            box(0, SY, W, SH, (13, 17, 25, int(min(1, self.absence / 2) * 75)))
        elif self.page == "end":
            # S20 Royal memory conclusion & Transition to Future Era
            box(0, 0, W, H, (10, 13, 21, 235))
            text("She only wanted a bowl of soup.", 370, 621, 34, GOLD, bold=True)
            text("Royal Memory Complete (S14 - S20)", 370, 562, 22)
            text("The Crown card has faded into ash. The Gear card pulses with cold neon light.",
                 370, 513, 19, MUTED, width=730)
            text("The truth of what contaminated the salt jar awaits in the Future Neural Lab.",
                 370, 466, 16, (180, 215, 240))

            # Proceed action prompt (unskippable for first 1.0s, no menu choice)
            can_skip = getattr(self, "end_page_timer", 0.0) >= 1.0
            lbl = "▶  [ SPACE / ENTER ] Proceed to Future Lab (S21)" if can_skip else "✦ Royal Chapter Concluded ✦"
            self.button(lbl, 371, 357, 480, 50, "proceed_future" if can_skip else None)

        self.immersion.overlay()
        self.draw_pause_overlay()

    # =========================================================================
    # UPDATE
    # =========================================================================
    def on_update(self, dt: float):
        if self.is_paused:
            return
        dt = min(dt * self.speed, 0.05)
        self.clock += dt
        if self.page == "end":
            self.end_page_timer = getattr(self, "end_page_timer", 0.0) + dt
        if self.page == "dialogue":
            self.dialogue.update(dt)
            self.line = self.dialogue.current_idx
        if self.onion_turn_motion is not None:
            self.onion_turn_motion += dt
            if self.onion_turn_motion >= .45:
                if self.chop_item == 'onion':self.cook.turn_onion()
                else:self.cook.turn_carrot()
                self.onion_turn_motion = None
        if self.carrot_fly is not None:
            self.carrot_fly += dt
            if self.carrot_fly >= .40:
                self.chop_item = 'carrot'
                if self.cook.cuts['onion'] >= 10:
                    self.onion_shift_started = self.clock
                self.carrot_fly = None
                self.ping()
        if self.drain_motion is not None:
            before=self.drain_motion;self.drain_motion+=dt
            if before<.55<=self.drain_motion:self.cook.drain()
            if self.drain_motion>=.9:self.drain_motion=None
        if self.batch_tray: self.batch_tray.update(dt)
        if self.range_hardware: self.range_hardware.update(dt)
        if self.departure: self.departure.update(dt)
        if self.seasoning: self.seasoning.update(dt)
        if self.serving: self.serving.update(dt)
        if self.workstation: self.workstation.update(dt)
        if self.inspect_motion is not None:
            self.inspect_motion+=dt
            if self.inspect_motion>=2.8:self.inspect_motion=None
        if self.dilute_motion is not None:
            before=self.dilute_motion;self.dilute_motion+=dt
            if before<.55<=self.dilute_motion:
                self.cook.add_water()
                self.say('A small splash added. Stir and check again.')
            if self.dilute_motion>=1.2:self.dilute_motion=None
        target=1.0 if self.hold=='pour' and self.cook.stage=='fill' else 0.0
        self.pour_pose += (target-self.pour_pose)*min(1,dt*12)
        self.note_time = max(0, self.note_time - dt)

        # When soup is fully cooked, automatically trigger urgent departure cutscene
        if self.page == "cooking" and self.cook.stage == "simmer" and self.cook.ready:
            if not getattr(self, "_auto_departure_done", False):
                self._auto_departure_timer = getattr(self, "_auto_departure_timer", 0.0) + dt
                if self._auto_departure_timer >= 0.7 and self.inspect_motion is None and self.dilute_motion is None:
                    self._auto_departure_done = True
                    self.leave()

        # Scene 7 popup jump prompt animation
        if self.cook.stage == "returned":
            near_work = self.walker.near("range") if self.seasoning.salt_collected else self.seasoning.near_salt()
        else:
            near_work = self.walker.near("range" if self.cook.prepared else "prep")
        near_door = self.walker.near("door")
        target_near = near_work or near_door
        if self.page == "cooking" and self.kitchen_mode == "explore" and target_near:
            self.prompt_anim = min(1.0, getattr(self, "prompt_anim", 0.0) + dt * 6.5)
        else:
            self.prompt_anim = max(0.0, getattr(self, "prompt_anim", 0.0) - dt * 8.0)

        # Keyboard movement in explore mode
        if self.page == "cooking" and self.kitchen_mode == "explore":
            dx = int(bool(self.walk_keys & {arcade.key.D, arcade.key.RIGHT})) - int(bool(self.walk_keys & {arcade.key.A, arcade.key.LEFT}))
            dy = int(bool(self.walk_keys & {arcade.key.W, arcade.key.UP})) - int(bool(self.walk_keys & {arcade.key.S, arcade.key.DOWN}))
            self.walker.move(dx, dy, dt)
            self.player.x = self.walker.x
            self.player.y = self.walker.y + self.player.feet_offset
            self.player.update(dt, dx, dy, bounds=(0, 2000, 0, 2000))
            self.player.x = self.walker.x
            self.player.y = self.walker.y + self.player.feet_offset
            self.player.sprite.center_x = self.player.x
            self.player.sprite.center_y = self.player.y

        # Cutting animation
        if self.chop_motion:
            self.chop_motion["time"] += dt
            if self.chop_motion["time"] >= 0.16 and not self.chop_motion["hit"]:
                self.chop_motion["hit"] = True
                self.cook.chop(self.chop_motion["item"])
                if self.chop_motion['item'] == 'onion' and self.cook.cuts['onion'] == 10:
                    self.onion_pile_started = self.clock
                if self.chop_motion['item'] == 'carrot' and self.cook.cuts['carrot'] == 8:
                    self.carrot_group2_shift_started = self.clock
                if self.chop_motion['item'] == 'carrot' and self.cook.cuts['carrot'] == 10:
                    self.carrot_pile_started = self.clock
                self.ping("chop")
                self.prep_shake = 6.0
            if self.chop_motion["time"] >= 0.40:
                self.chop_motion = None
                # Phase 1 finished (6th cut landed): auto-start the 90-degree turn
                # instead of waiting for a hidden click. Locks input briefly.
                if self.cook.stage == 'prep' and self.chop_item in ('onion', 'carrot'):
                    n = self.cook.cuts[self.chop_item]
                    turned = self.cook.onion_turned if self.chop_item == 'onion' else self.cook.carrot_turned
                    if n == 6 and not turned and self.onion_turn_motion is None:
                        self.onion_turn_motion = 0.0
                        self.ping()
                if self.cook.prepared and all(t is None or self.clock-t >= .65 for t in (self.onion_pile_started,self.carrot_pile_started)):self.kitchen_mode='explore'

        if self.cook.stage == 'prep' and self.cook.prepared and self.chop_motion is None and all(t is None or self.clock-t >= .65 for t in (self.onion_pile_started,self.carrot_pile_started)):
            self.kitchen_mode = 'explore'

        if getattr(self, "prep_shake", 0.0) > 0:
            self.prep_shake = max(0.0, self.prep_shake - dt * 25.0)

        # Continuous actions
        if self.hold == "pour":
            self.cook.pour(dt)
        elif self.hold == "ladle":
            self.cook.ladle(dt)
            if self.cook.served>=1:
                self.hold=None
                self.workstation.selected=None
                self.workstation.loaded=False
                self.say('The bowl is full. Click it to carry the soup to the dining room.')

        if not self.in_map():self.cook.tick(dt)

        if self.page == "absence":
            self.absence += dt
            if self.absence >= 2.8:
                self.returned()

    # =========================================================================
    # INPUT
    # =========================================================================
    def action(self, key):
        if self.cook.stage=='fill' and self.batch_tray.dragging:return
        if self.drain_motion is not None and self.cook.stage=='fill':return
        if (self.onion_turn_motion is not None or self.carrot_fly is not None) and key in {'prep_exit', 'work_exit', 'select_onion', 'select_carrot'}:
            return
        if self.workstation and self.workstation.motion:
            self.say('Let the current item movement finish first.')
            return
        if key=='delivery_door':
            self.serving.enter_door()
            return
        if key=='work_exit' and self.serving.busy:
            self.say('Let the ladle finish moving first.')
            return
        if key=='departure_door':
            self.departure.enter_door()
            return
        if key=='work_exit' and self.seasoning.busy:
            self.say('Let the spoon movement finish first.')
            return
        if key=='work_exit':
            if self.coal_motion is not None or self.inspect_motion is not None or self.dilute_motion is not None:
                self.say('Let the current movement finish first.')
                return
            self.workstation.stop_input()
            self.kitchen_mode='explore'
            return
        if key=='wash_done':
            if self.workstation.washed>=1:
                self.workstation.stop_input()
                self.empty_kitchen()
            return
        self.ping()
        if key == "start":
            self.start()
        elif key == "proceed_future":
            if getattr(self, "end_page_timer", 0.0) >= 1.0:
                from scenes.future_integrated_view import FutureLabView
                self.window.show_view(FutureLabView())
        elif key == "toggle_door":
            if self.kitchen_mode == "explore":
                self.walker.toggle_door()
                if self.walker.door_open:
                    self.say("The kitchen door opens.")
                else:
                    self.say("The door is closed.")
                self.ping()
        elif key == "prep_enter":
            if self.kitchen_mode == "explore" and self.walker.near("prep") and not self.cook.prepared:
                self.kitchen_mode = "prep"
                self.walk_keys.clear()
        elif key == "prep_exit":
            if self.chop_motion is None:
                self.kitchen_mode = "explore"
        elif key == "take_salt":
            if (self.page == "cooking" and self.kitchen_mode == "explore" and self.cook.stage == "returned"
                    and not self.seasoning.salt_collected and self.seasoning.near_salt()):
                self.seasoning.salt_collected = True
                self.say("Salt collected. Go to the range and press E to season the soup.")
                self.ping()
        elif key == "range_enter":
            if self.kitchen_mode == "explore" and self.walker.near("range"):
                if self.cook.stage == "returned" and not self.seasoning.salt_collected:
                    self.say("Take the salt from the left side of the table first.")
                    return
                if self.cook.stage=="prep":self.next_fill()
                else:
                    self.kitchen_mode="cooking"
                    self.walk_keys.clear()
        elif key == "menu":
            from scenes.menu_view import MenuView
            self.window.show_view(MenuView())
        elif key == "advance":
            self.advance()
        elif key == "fill":
            if self.cook.prepared and self.chop_motion is None:
                self.kitchen_mode = "explore"
        elif key.startswith("select_"):
            if self.chop_motion is None and self.carrot_fly is None:
                item = key[7:]
                if item == "carrot":
                    # Fly the carrot from the left tray onto the board instead of
                    # an instant swap. The onion stays on the board until it lands.
                    self.carrot_fly = 0.0
                    self.ping()
                else:
                    self.chop_item = item
        elif key.startswith("add_"):
            self.cook.add(key[4:])
            self.say("Ingredient added to the pot.")
        elif key == "pour":
            if self.cook.stage=='fill' and not self.cook.ingredients:self.hold = 'pour' 
        elif key == "drain":
            if self.cook.stage=='fill' and not self.cook.ingredients and self.cook.water>0:
                self.hold=None;self.drain_motion=0.0
        elif key == "boil":
            self.begin_boil()
            if self.cook.stage == "boil" and self.coal_motion is None:
                self.range_hardware.press(1170, 465)
        elif key == "fuel":
            self.cook.heat = min(2, self.cook.heat + 1)
        elif key == "raise":
            self.cook.air_opening = max(0, self.cook.air_opening - .10)
            self.say("Less combustion air. Stored heat will fade gradually.")
        elif key == "lower":
            self.cook.air_opening = min(1, self.cook.air_opening + .10)
            self.say("More combustion air. Fire and plate heat rise gradually.")
        elif key == 'check_soup':
            self.check_soup()
        elif key == "taste":
            self.taste()
        elif key == 'water':
            if self.cook.can_add_water and self.dilute_motion is None and self.inspect_motion is None:
                self.dilute_motion=0.0
                self.hold=None
        elif key == "embers":
            self.cook.tend_fire()
        elif key == "leave":
            self.leave()
        elif key == "ladle":
            self.hold = "ladle"
        elif key == "deliver":
            self.deliver()

    def on_mouse_press(self, x, y, button, modifiers):
        if self.handle_pause_mouse_press(x, y, button):
            return
        x, y = self.pointer_coords(x, y)
        if self.drain_motion is not None and self.page=='cooking' and self.cook.stage=='fill':return
        if button==arcade.MOUSE_BUTTON_RIGHT and self.page=='cooking' and self.cook.stage=='fill' and not self.in_map():
            self.action('drain')
            return
        if button==arcade.MOUSE_BUTTON_RIGHT and self.page=='cooking' and self.cook.stage=='serve' and not self.in_map():
            self.serving.click(x,y,button)
            return
        if button==arcade.MOUSE_BUTTON_RIGHT and self.page=='cooking' and self.cook.stage=='returned' and not self.in_map():
            self.seasoning.click(x,y,button)
            return
        if button==arcade.MOUSE_BUTTON_RIGHT:
            if self.workstation:self.workstation.stop_input()
            return
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        self.mouse = (x, y)
        for bx, by, bw, bh, act, enabled, _ in reversed(self.buttons):
            if bx <= x <= bx + bw and by <= y <= by + bh:
                if enabled:
                    self.action(act)
                return

        if self.in_map():return
        if self.page=='wash':
            self.workstation.wash_click(x,y,button)
            return
        if self.page=='cooking' and self.cook.stage=='returned' and not self.in_map():
            self.seasoning.click(x,y,button)
            return
        if self.page=='cooking' and self.cook.stage=='serve' and not self.in_map():
            self.serving.click(x,y,button)
            return
        if self.page=='cooking' and not self.in_map() and self.cook.stage in {'returned','serve'}:
            self.workstation.finish_click(x,y,button)
            return
        if self.page=='cooking' and not self.in_map() and self.cook.stage=='fill':
            if self.workstation.handle_fill(x,y,button):return

        if self.page=='departure':
            if self.departure.mode=='walk' and math.dist((x,y),(1195,510))<160:self.departure.enter_door()
            return
        if self.page == "dialogue":
            self.advance()
            return
        if self.page != "cooking":
            return

        c = self.cook
        if c.stage in {'boil','simmer'} and self.range_hardware.press(x,y):return
        if c.stage=='simmer':
            if self.inspect_motion is not None or self.dilute_motion is not None:return
            if 1140<x<1340 and 510<y<740:
                self.action('water')
            elif (RESTING_SPOON_RECT.left <= x <= RESTING_SPOON_RECT.right
                  and RESTING_SPOON_RECT.bottom <= y <= RESTING_SPOON_RECT.top):
                self.hold = 'spoon_pending'
                self.spoon_press = (x,y)
                self.stir_angle = None
                self.stir_travel = 0
            return
        if c.stage=='boil':
            return
        if c.stage == 'fill' and not c.ingredients and 1140<x<1340 and 510<y<740:
            self.hold='pour'
            return
        if c.stage == "prep":
            if self.kitchen_mode != "prep" or self.chop_motion is not None:
                return
            if self.onion_turn_motion is not None:
                return
            if self.chop_hit(x, y):
                self.chop_motion = {"item": self.chop_item, "x": self.knife_target(), "time": 0, "hit": False}
                # Start the move-to-corner the instant the head-finishing cut begins,
                # so the tip glides during the wind-up instead of sitting on the body
                # and then snapping back to the uncut position before flying.
                if self.chop_motion["item"] == "onion" and self.cook.cuts["onion"] == 2:
                    self.onion_corner_started = self.clock
                if self.chop_motion["item"] == "carrot" and self.cook.cuts["carrot"] == 1:
                    self.carrot_corner_started = self.clock
        elif c.stage == "boil" and c.boiled and math.dist((x, y), self.pot_pos) < 70:
            self.drag = "pot"
        elif c.stage == "simmer" and math.dist((x, y), self.pot_pos) < 85:
            self.hold = "stir"
            self.stir_angle = math.atan2(y - self.pot_pos[1], x - self.pot_pos[0])
            self.stir_travel = 0
        elif c.stage == "returned" and 520 < x < 605 and 335 < y < 415:
            self.season()

    def on_mouse_motion(self, x, y, dx, dy):
        if self.handle_pause_mouse_motion(x,y):return
        self.mouse = self.pointer_coords(x, y)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.is_paused:return
        x, y = self.pointer_coords(x, y)
        self.mouse = (x, y)
        if self.hold=='air' and self.cook.stage in {'boil','simmer'} and not self.is_paused:
            self.range_hardware.set_air(x,y)
            return
        if self.hold == 'spoon_pending' and math.dist((x,y), self.spoon_press) >= 12:
            self.hold = 'stir'
        if self.hold == 'stir' and self.cook.stage in {'simmer', 'returned'}:
            cx,cy,rx,ry=self.pot_renderer.surface(self.cook.water,*CLOSEUP_POT)
            a=math.atan2((y-cy)/ry,(x-cx)/rx)
            inside = .03 <= ((x-cx)/rx)**2+((y-cy)/ry)**2 <= 1.3
            if self.stir_angle is not None and inside:
                delta=(a-self.stir_angle+math.pi)%(2*math.pi)-math.pi
                self.stir_travel+=delta;self.stir_phase+=delta
            self.stir_angle=a if inside else None
            required_turns = 2 if self.cook.stage == 'returned' else 1
            if abs(self.stir_travel) >= math.tau * required_turns:
                self.stir_travel = 0
                if self.cook.stage == 'returned':
                    if self.cook.finish_seasoning():
                        self.hold = None
                        self.say('Ready to serve.')
                        self.ping()
                else:
                    self.cook.stir()
                    self.say('Gently stirred. The barley is no longer sticking.')
            return
        if self.hold == "stir" and not self.is_paused:
            a = math.atan2(y - self.pot_pos[1], x - self.pot_pos[0])
            if self.stir_angle is not None:
                delta = (a - self.stir_angle + math.pi) % (2 * math.pi) - math.pi
                if math.dist((x, y), self.pot_pos) < 105:
                    self.stir_travel += abs(delta)
            self.stir_angle = a
            if self.stir_travel > math.pi * 2:
                self.cook.stir()
                self.stir_travel = 0
                self.say("Gently stirred. The barley is no longer sticking.")

    def on_mouse_release(self, x, y, button, modifiers):
        if button!=arcade.MOUSE_BUTTON_LEFT:return
        if self.workstation:
            self.workstation.wash_hold=False
            if self.hold=='ladle':self.workstation.loaded=False
        x, y = self.pointer_coords(x, y)
        if self.batch_tray.dragging:self.batch_tray.release()
        if self.hold == "spoon_pending" and not self.is_paused and math.dist((x,y), self.spoon_press) < 12:
            self.check_soup()
        self.drag = None
        self.hold = None
        self.stir_angle = None

    def on_key_press(self, key, modifiers):
        if key == arcade.key.F11:
            if self.workstation:self.workstation.stop_input()
            self.toggle_fullscreen()
            return
        if self.handle_pause_key(key):
            if self.workstation:self.workstation.stop_input()
            return

        if self.page == 'return_entry':
            if self.seasoning.mode == 'corridor' and key in (arcade.key.W, arcade.key.UP, arcade.key.S, arcade.key.DOWN):
                self.walk_keys.add(key)
            return

        if self.page=='delivery':
            if self.serving.mode=='walk':
                if key in (arcade.key.W,arcade.key.A,arcade.key.S,arcade.key.D,arcade.key.UP,arcade.key.DOWN,arcade.key.LEFT,arcade.key.RIGHT):self.walk_keys.add(key)
                if key==arcade.key.E:self.serving.enter_door()
            return

        if self.page=='departure':
            if self.departure.mode=='walk':
                if key in (arcade.key.W,arcade.key.A,arcade.key.S,arcade.key.D,arcade.key.UP,arcade.key.DOWN,arcade.key.LEFT,arcade.key.RIGHT):self.walk_keys.add(key)
                if key==arcade.key.E:self.departure.enter_door()
            return

        if key in (arcade.key.W, arcade.key.A, arcade.key.S, arcade.key.D,
                   arcade.key.UP, arcade.key.DOWN, arcade.key.LEFT, arcade.key.RIGHT):
            if self.page == "cooking" and self.kitchen_mode == "explore":
                self.walk_keys.add(key)
            return

        if key == arcade.key.E and self.page == "cooking" and self.kitchen_mode == "explore":
            if self.walker.near("door"):
                self.action("toggle_door")
                return
            if self.cook.stage == "returned" and not self.seasoning.salt_collected and self.seasoning.near_salt():
                self.action("take_salt")
                return
            if self.walker.near("prep") and not self.cook.prepared:
                self.action("prep_enter")
                return
            if self.walker.near("range"):
                self.action("range_enter")
                return
            if self.walker.near("prep"):
                self.action("prep_enter")
                return
            return

        if key in (arcade.key.SPACE, arcade.key.ENTER):
            if self.page == "dialogue":
                self.advance()
            elif self.page == "end":
                self.action("proceed_future")
            return

    def on_key_release(self, key, modifiers):
        self.walk_keys.discard(key)
        if not self.walk_keys:
            if hasattr(self, 'player') and self.player:
                self.player.stop_footstep()
            self.audio.stop_footstep()
