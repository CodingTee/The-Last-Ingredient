"""Integrated Future Laboratory Scene View.
Unifies Future Exploration, Narrative Branching, Physical Collision, and Dual Endings (BE / HE).
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import arcade
from arcade.types.rect import LRBT

from core.base_view import BaseGameView
from core.constants import ASSETS_DIR, COLOR_GOLD, SCREEN_WIDTH, SCREEN_HEIGHT, START_FULLSCREEN
from core.player import Player, FEET_OFFSET
from core.audio import AudioManager
from scenes.future_investigation_ui import FutureInvestigationUI, EVIDENCE, REALISATION

ASSET_DIR = ASSETS_DIR / "future_lab"
WORLD_W, WORLD_H = 1983, 793

# Ground footprints for physical collisions
FOOTPRINTS = {
    "fridge": (0, 205, 260, 620),
    "kitchen_base": (205, 290, 350, 620),
    "kitchen_step1": (290, 340, 385, 620),
    "kitchen_step2": (340, 390, 430, 620),
    "kitchen_step3": (390, 440, 475, 620),
    "kitchen_step4": (440, 490, 520, 620),
    "archive": (560, 784, 500, 530),
    "analysis_desk": (864, 1386, 455, 525),
    "analysis_stool": (1080, 1164, 445, 500),
    "time_capsule": (1490, 1686, 435, 518),
    "equipment_locker": (1676, 1810, 483, 535),
    "central_research_table": (891.6, 1170.4, 120.0, 235.0),
    "sofa": (75, 282, 80, 187),
    "coffee_table": (264, 417, 84, 162),
    "return_chair": (1690, 1908, 126, 245),
    "side_table": (1843, 1946, 120, 210),
    "orb_lamp": (30, 78, 48, 78),
}

# Accessible workstations in the laboratory
STATIONS = (
    ("kitchen", "Food Synthesizer", (390, 345),
     "Interactive cooking station. Synthesizes meals with automated heating and mechanical stirring arms."),
    ("analysis", "Evidence I: Holographic Wound Analysis", (1020, 416),
     "Holographic ballistic projector. Compares prehistoric wound morphology with laboratory weaponry."),
    ("sample", "Evidence II: Sealed Neuro-Compound", (1275, 416),
     "Spectrometer & chemical sample bay. Analyzes the active blue liquid and historical salt residue."),
    ("archive", "Evidence III: Historical Research Archive", (683, 444),
     "Decentralized lab database. Tracks ancient excavation files and the modern restaurant food poisoning logs."),
    ("island", "Research Island Desk", (1030, 82),
     "Central floating work surface with cold storage cartridges and quantum calculation slates."),
    ("capsule", "Physical Jump Capsule", (1567, 400),
     "Transports a physical body and heavy field equipment into historical eras. (Triggers Bad Ending)."),
    ("chair", "Consciousness Return Chair", (1590, 191),
     "Transfers the mind back to modern reality. Physical items cannot travel. (Triggers Happy Ending)."),
)


def bob_offset(layer, seconds):
    return layer["amplitude"] * math.sin(seconds * math.tau / layer["period"] + layer["phase"])


def get_future_lab_obstacles(layer_data=None):
    """Unified HE-grade physical collision system for the Future Laboratory.
    Ensures identical collision mechanics everywhere:
    - Base footprints (fridge blocked behind, central table lowered, sofa, capsule, etc.)
    - Stepped prep table boundary (walkable floor space up to counter edge)
    - Contact points for all layout layers
    - Strict furniture alpha ground mask (player feet may only land on visible floor)
    """
    obstacles = list(FOOTPRINTS.values())

    # Fine-grained stepped prep table boundary
    for x in range(203, 479, 6):
        edge = 340 + (x - 220) * (10 / 70) if x < 290 else 350 + (x - 290) * (120 / 180)
        obstacles.append((x, x + 6, edge - 10, 620))

    if layer_data:
        from scenes.he_cooking_scene import ground_mask_rects
        for item in layer_data:
            contact = item.get("floor_contact")
            if contact:
                x, y, radius = contact["x"], contact["y"], contact["width"] * 0.43
                obstacles.append((x - radius, x + radius, y - 3, y + 10))
        obstacles += ground_mask_rects(ASSET_DIR, layer_data)

    return obstacles


class FutureLabView(BaseGameView):
    """Integrated Future Laboratory Scene View.
    Unifies Future Exploration, Narrative Branching, and HE Collision System.
    """
    def __init__(self, start_branch=None):
        super().__init__()
        self.start_branch = start_branch
        self.elapsed = 0.0
        self.keys = set()
        self.panel = None
        self.nearest = None
        self.float_enabled = True
        self.world_camera = None

        self.audio = AudioManager()

        # BE Mission state (Directly active in BE scene, no transition step required)
        self.transit_committed = True
        self.nutrient_consumed = False
        self.cooking_complete = False
        self.nutrient_view = None
        self.departure_view = None

        # Evidence collection states (S24 - S27)
        self.evidence_wound = False       # Evidence I (Station: analysis)
        self.evidence_salt_jar = False    # Evidence 2 (Station: sample)
        self.evidence_modern = False      # Evidence 3 (Station: archive)
        self.truth_understood = (start_branch == 'he')  # True if HE branch
        self.showing_realisation = False  # S27 Epiphany modal active

        if start_branch in ('be', 'he'):
            self.intro_active = False
            self.notice_title = ""
            self.notice_message = None
        else:
            self.intro_active = True
            self.notice_title = "S21 - An Autonomous Connection"
            self.notice_message = (
                "Consciousness connection established. Autonomous control enabled.\n\n"
                "You raise your right hand. It obeys.\n"
                'Chef: "This time... I\'m in control."'
            )

        # Visual assets
        self.layer_data = json.loads((ASSET_DIR / "layout.json").read_text(encoding="utf-8"))["layers"]
        self.background = arcade.load_texture(ASSET_DIR / "room_background.png")
        self.layers = [(item, arcade.load_texture(ASSET_DIR / item["file"])) for item in self.layer_data]
        self.nutrient_station_texture = arcade.load_texture(ASSET_DIR / "cooking_station_be.png")
        self.hologram = arcade.load_texture(ASSET_DIR / "hologram_analysis.png")
        self.table_shadow = arcade.load_texture(ASSET_DIR / "table_shadow.png")
        self.hint_arrow_texture = arcade.load_texture(ASSETS_DIR / "he_cooking" / "switch_hint_arrow.png")

        # Player entity
        self.occupied_chair_texture = arcade.load_texture(ASSET_DIR / "return_chair_occupied.png")
        self.player = Player(1640, 190 + FEET_OFFSET, "astronaut")

        # Physical Collision System (Unified HE Mechanics)
        self.obstacles = get_future_lab_obstacles(self.layer_data)

        self._texts = {}
        self.investigation = FutureInvestigationUI(self)

    def on_show_view(self):
        super().on_show_view()
        self.keys.clear()
        self._fit_world()
        if self.start_branch:
            branch = self.start_branch
            self.start_branch = None
            if branch == 'he':
                self.truth_understood = True
            self._on_kitchen_interact()

    def on_hide_view(self):
        self.keys.clear()

    def _fit_world(self):
        if not self.window:
            return
        width, height = self.window.width, self.window.height
        aspect = width / max(1, height)
        view_h = min(720.0, WORLD_H, WORLD_W / aspect)
        view_w = view_h * aspect
        self._view_w, self._view_h = view_w, view_h
        if self.world_camera is None:
            self.world_camera = arcade.Camera2D(window=self.window)
        self.world_camera.viewport = LRBT(0, width, 0, height)
        self.world_camera.projection = LRBT(-view_w / 2, view_w / 2, -view_h / 2, view_h / 2)
        self._follow_camera(snap=True)

    def _follow_camera(self, dt=0.0, snap=False):
        if self.world_camera is None:
            return
        hx, hy = self._view_w / 2, self._view_h / 2
        target_x = max(hx, min(WORLD_W - hx, self.player.x))
        target_y = max(hy, min(WORLD_H - hy, self.player.y))
        if snap:
            self.world_camera.position = (target_x, target_y)
        else:
            x, y = self.world_camera.position
            blend = 1.0 - math.exp(-9.0 * dt)
            self.world_camera.position = (
                max(hx, min(WORLD_W - hx, x + (target_x - x) * blend)),
                max(hy, min(WORLD_H - hy, y + (target_y - y) * blend))
            )

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self._fit_world()

    def on_update(self, dt):
        if self.is_paused or self.panel or self.showing_realisation or self.notice_message:
            return
        dt = min(dt, 0.05)
        self.elapsed += dt

        mx = int(bool(self.keys & {arcade.key.D, arcade.key.RIGHT})) - int(bool(self.keys & {arcade.key.A, arcade.key.LEFT}))
        my = int(bool(self.keys & {arcade.key.W, arcade.key.UP})) - int(bool(self.keys & {arcade.key.S, arcade.key.DOWN}))
        self.player.update(dt, mx, my, bounds=(125, 1860, 72 + FEET_OFFSET, 441 + FEET_OFFSET), obstacles=self.obstacles)

        feet = self.player.y - FEET_OFFSET
        edge = max(125, 125 + (feet - 290) * 1.2)
        self.player.place(max(edge, min(WORLD_W - edge, self.player.x)), self.player.y)
        self._follow_camera(dt)

        # Station proximity detection
        def _station_dist(s):
            if s[0] == "kitchen":
                def _seg(x1, y1, x2, y2):
                    dx, dy = x2 - x1, y2 - y1
                    t = max(0.0, min(1.0, ((self.player.x - x1) * dx + (feet - y1) * dy) / (dx * dx + dy * dy)))
                    return math.hypot(self.player.x - (x1 + t * dx), feet - (y1 + t * dy))
                return min(_seg(220.0, 340.0, 290.0, 350.0), _seg(290.0, 350.0, 470.0, 470.0))
            return math.hypot(self.player.x - s[2][0], feet - s[2][1])

        best = min(STATIONS, key=_station_dist)
        self.nearest = best if _station_dist(best) < 125 else None

    def _draw_layer(self, item, texture):
        if item.get("architecture_baked"):
            return
        dy = bob_offset(item, self.elapsed) if self.float_enabled else 0
        # In the free exploration BE laboratory, kitchen station is directly the BE nutrient station
        if item["id"] == "cooking_station":
            texture = self.nutrient_station_texture
        elif item["id"] == "return_chair" and self.intro_active:
            texture = self.occupied_chair_texture
        arcade.draw_texture_rect(texture, arcade.XYWH(
            item["x"] + item["width"] / 2,
            WORLD_H - item["y"] - item["height"] / 2 - dy,
            item["width"], item["height"]))

    def _text(self, content, x, y, size=14, color=(211, 236, 248), width=None, bold=False, center=False):
        key = (content, x, y, size, color, width, bold, center)
        ax = "center" if center else "left"
        if key not in self._texts:
            self._texts[key] = arcade.Text(content, x, y, color, size, width=width or 0,
                                           multiline=width is not None, bold=bold,
                                           font_name=("Segoe UI", "Calibri", "Arial"),
                                           anchor_x=ax, anchor_y="center")
        self._texts[key].draw()

    # =========================================================================
    # RENDER LOOP
    # =========================================================================
    def on_draw(self):
        self.clear((7, 20, 34))
        if self.world_camera is None:
            self._fit_world()
        self.world_camera.use()

        # 1. Background
        arcade.draw_texture_rect(self.background, arcade.XYWH(WORLD_W / 2, WORLD_H / 2, WORLD_W, WORLD_H))

        # 2. Contact Shadows
        for item, _ in self.layers:
            if item.get("architecture_baked") or item.get("architecture_shadow_baked"):
                continue
            contact = item.get("floor_contact")
            if contact:
                x, y, width = contact["x"], contact["y"], contact["width"]
                arcade.draw_texture_rect(self.table_shadow, arcade.XYWH(x, y, width * 1.35, 18))
                arcade.draw_ellipse_filled(x, y, width, 9, (10, 19, 34, 145))
            footprint = FOOTPRINTS.get(item["id"])
            if footprint:
                x1, x2, y1, y2 = footprint
                if item["id"] == "central_research_table":
                    rect = arcade.XYWH(1030, 136, 367.2, 80.2)
                else:
                    rect = arcade.XYWH((x1 + x2) / 2, y1 + 8, max(28, (x2 - x1) * 0.88), min(45, max(18, (y2 - y1) * 0.45)))
                arcade.draw_texture_rect(self.table_shadow, rect)

        # 3. Y-Sorted Furniture and Player (BE Scene Appearance)
        ordered = []
        for item, texture in self.layers:
            footprint = FOOTPRINTS.get(item["id"])
            baseline = item.get("depth_y", footprint[2] if footprint else WORLD_H - item["y"] - item["height"])
            ordered.append((baseline, item, texture))
        player_depth = self.player.y - FEET_OFFSET
        inserted = self.intro_active
        for baseline, item, texture in sorted(ordered, key=lambda row: row[0], reverse=True):
            if not inserted and player_depth > baseline:
                self.player.draw(1.0)
                inserted = True
            self._draw_layer(item, texture)
        if not inserted:
            self.player.draw(1.0)

        # 4. Hologram Analysis Desk Projection
        dy = 5 * math.sin(self.elapsed * math.tau / 3.6) if self.float_enabled else 0
        arcade.draw_texture_rect(self.hologram, arcade.XYWH(1121, WORLD_H - 148.5 - dy, 366, 183), alpha=225)

        # 5. Station Visual Cues (Floating tailless yellow arrow)
        if self.nearest:
            nid = self.nearest[0]
            if nid == "kitchen":
                target_x = 344
                target_y = WORLD_H - 263 + 46
            else:
                x, y = self.nearest[2]
                target_x = x
                target_y = y + 42
            bob = 5.0 * math.sin(self.elapsed * 4.5)
            pulse = int(210 + 45 * math.sin(self.elapsed * 4.5))
            arcade.draw_texture_rect(
                self.hint_arrow_texture,
                arcade.XYWH(target_x, target_y + bob, 42, 30),
                alpha=pulse,
            )

        # 6. Switch to UI Camera
        self.window.default_camera.use()
        w, h = self.window.width, self.window.height

        # Evidence Tracker HUD
        self._draw_evidence_hud(w, h)

        # Interaction Prompt
        if self.nearest and not self.panel and not self.showing_realisation and not self.notice_message:
            nid = self.nearest[0]
            if nid == "kitchen":
                if self.truth_understood:
                    hint = "[E]  Food Synthesizer: Prepare Meal (Childhood Egg Noodle Soup)"
                else:
                    hint = "[E]  Food Synthesizer: Synthesize Field Nutrient Block"
            elif nid == "capsule":
                if self.truth_understood:
                    hint = "[E]  Physical Jump Capsule (Locked - Dangerous Loop)"
                elif self.nutrient_consumed:
                    hint = "[E]  Physical Jump Capsule: Enter Departure Bay"
                else:
                    hint = "[E]  Physical Jump Capsule: Departure Bay (Nutrient Required)"
            elif nid == "chair":
                if self.truth_understood:
                    hint = "[E]  Consciousness Return Chair (Prepare Meal First)"
                else:
                    hint = "[E]  Consciousness Return Chair (Coordinates Locked)"
            else:
                hint = "[E]  " + self.nearest[1]
            self._text(hint, 24, 52, 15, (120, 242, 255), bold=True)

        # Modal Overlays
        if self.showing_realisation:
            self.investigation.draw_realisation(w, h)
        elif self.panel:
            self.investigation.draw_panel(w, h, self.panel)
        elif self.notice_message:
            self._draw_notice_dialog(w, h)

        self.draw_pause_overlay()

    # -------------------------------------------------------------------------
    # Evidence HUD
    # -------------------------------------------------------------------------
    def _draw_evidence_hud(self, w: float, h: float):
        bx = w - 210
        by = h - 55
        arcade.draw_rect_filled(arcade.XYWH(bx, by, 390, 78), (10, 18, 28, 220))
        border_col = COLOR_GOLD if self.truth_understood else (60, 160, 210, 180)
        arcade.draw_rect_outline(arcade.XYWH(bx, by, 390, 78), border_col, 1.8)

        self._text("INVESTIGATION EVIDENCE (S24 - S27)", bx - 180, by + 24, 11, COLOR_GOLD, bold=True)

        w1 = "OK" if self.evidence_wound else "--"
        w2 = "OK" if self.evidence_salt_jar else "--"
        w3 = "OK" if self.evidence_modern else "--"
        c1 = (100, 255, 160) if self.evidence_wound else (160, 170, 180)
        c2 = (100, 255, 160) if self.evidence_salt_jar else (160, 170, 180)
        c3 = (100, 255, 160) if self.evidence_modern else (160, 170, 180)

        self._text(f"[1] Wound: {w1}", bx - 180, by - 2, 11, c1, bold=self.evidence_wound)
        self._text(f"[2] Salt Jar: {w2}", bx - 65, by - 2, 11, c2, bold=self.evidence_salt_jar)
        self._text(f"[3] Sample: {w3}", bx + 55, by - 2, 11, c3, bold=self.evidence_modern)

        if self.truth_understood:
            pulse = int(200 + 55 * math.sin(self.elapsed * 5.0))
            self._text("STATUS: TRUTH UNDERSTOOD (HAPPY ENDING AVAILABLE)", bx - 180, by - 24, 11, (255, 215, 100, pulse), bold=True)
        else:
            collected = sum([self.evidence_wound, self.evidence_salt_jar, self.evidence_modern])
            self._text(f"STATUS: RECORDED {collected}/3 | R: REVIEW WHEN COMPLETE", bx - 180, by - 24, 11, (180, 210, 235))

    # -------------------------------------------------------------------------
    # In-Game Notice Dialog
    # -------------------------------------------------------------------------
    def _draw_notice_dialog(self, w: float, h: float):
        pw, ph = 740, 260
        cx, cy = w / 2, h / 2
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, pw, ph), (10, 18, 28, 245))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, pw, ph), (96, 207, 231), 2)
        self._text(self.notice_title, cx, cy + 80, 18, COLOR_GOLD, bold=True, center=True)
        self._text(self.notice_message, cx, cy + 15, 14, (230, 240, 248), width=pw - 80, center=True)
        arcade.draw_rect_filled(arcade.XYWH(cx, cy - 80, 220, 40), (24, 63, 82))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy - 80, 220, 40), (128, 224, 247), 1.5)
        self._text("[ ENTER / E / ESC ]  OK", cx, cy - 80, 13, (240, 248, 255), bold=True, center=True)

    def _show_notice(self, title: str, message: str):
        self.notice_title = title
        self.notice_message = message
        self.keys.clear()
        self.audio.play("click", volume_scale=0.7)

    def _close_notice(self):
        self.intro_active = False
        self.notice_message = None
        self.notice_title = ""
        self.keys.clear()

    # -------------------------------------------------------------------------
    # Input Handling
    # -------------------------------------------------------------------------
    def on_deactivate(self):
        self.keys.clear()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.F11:
            self.keys.clear()
            self.toggle_fullscreen()
            self._fit_world()
            return
        if self.is_paused:
            self.handle_pause_key(key)
            self.keys.clear()
            return
        if key == arcade.key.P:
            self.is_paused = True
            self.keys.clear()
            return

        if self.notice_message:
            if key in (arcade.key.ESCAPE, arcade.key.E, arcade.key.ENTER, arcade.key.SPACE):
                self._close_notice()
            return

        if self.showing_realisation:
            ui = self.investigation
            if key in (arcade.key.ESCAPE, arcade.key.E):
                ui.act("dismiss_review")
            elif key == arcade.key.LEFT:
                ui.act("real_previous")
            elif key == arcade.key.RIGHT:
                if ui.realisation_page < len(REALISATION) - 1:
                    ui.act("real_next")
            elif key in (arcade.key.ENTER, arcade.key.SPACE):
                ui.act("understand" if ui.realisation_page == len(REALISATION) - 1 else "real_next")
            return

        if self.panel:
            nid = self.panel[0]
            ui = self.investigation
            if ui.showing_image:
                if key in (arcade.key.ESCAPE, arcade.key.E, arcade.key.I):
                    ui.act("hide_image")
                return
            if nid in EVIDENCE and key == arcade.key.I:
                ui.act("show_image")
                return
            if key in (arcade.key.ESCAPE, arcade.key.E):
                self._close_panel()
                return
            if nid in EVIDENCE:
                if key == arcade.key.LEFT:
                    ui.act("previous")
                elif key == arcade.key.RIGHT:
                    if ui.page < len(EVIDENCE[nid][2]) - 1:
                        ui.act("next")
                elif key in (arcade.key.ENTER, arcade.key.SPACE):
                    ui.act("record" if ui.page == len(EVIDENCE[nid][2]) - 1 else "next")
            elif key == arcade.key.ENTER:
                if nid == "capsule":
                    self._on_capsule_interact()
                elif nid == "chair":
                    self._on_chair_interact()
                elif nid == "kitchen":
                    self._on_kitchen_interact()
                else:
                    self._close_panel()
            return

        if self.handle_pause_key(key):
            self.keys.clear()
            return

        if key == arcade.key.R and self._all_evidence():
            self._begin_realisation()
            return

        if key == arcade.key.E and self.nearest:
            self.keys.clear()
            nid = self.nearest[0]
            if nid == "kitchen":
                self._on_kitchen_interact()
            elif nid == "capsule":
                self._on_capsule_interact()
            elif nid == "chair":
                self._on_chair_interact()
            else:
                self._open_panel(self.nearest)
        elif key == arcade.key.F:
            self.float_enabled = not self.float_enabled
        else:
            self.keys.add(key)

    def on_key_release(self, key, modifiers):
        self.keys.discard(key)

    def on_mouse_press(self, x, y, button, modifiers):
        if button != arcade.MOUSE_BUTTON_LEFT:
            return
        if self.handle_pause_mouse_press(x, y, button):
            return
        if self.notice_message:
            self._close_notice()
            return
        if self.showing_realisation or self.panel:
            action = self.investigation.hit(x, y)
            if action:
                if action == "launch":
                    self._on_capsule_interact()
                elif action == "abort":
                    self._on_chair_interact()
                elif action in ("practice", "nutrient"):
                    self._on_kitchen_interact()
                else:
                    self.investigation.act(action)

    def on_mouse_motion(self, x, y, dx, dy):
        self.handle_pause_mouse_motion(x, y)

    # -------------------------------------------------------------------------
    # Evidence & Deduction Logic
    # -------------------------------------------------------------------------
    def _all_evidence(self):
        return self.evidence_wound and self.evidence_salt_jar and self.evidence_modern

    def _open_panel(self, station):
        self.panel = station
        self.investigation.page = 0
        self.investigation.showing_image = False
        self.investigation.buttons = []
        self.keys.clear()
        self.audio.play("click", volume_scale=0.7)

    def _record_evidence(self):
        if not self.panel or self.panel[0] not in EVIDENCE:
            return False
        title, field, pages = EVIDENCE[self.panel[0]]
        if self.investigation.page != len(pages) - 1:
            return False
        if not getattr(self, field):
            setattr(self, field, True)
            self.audio.play("clue_match", volume_scale=0.9)
        self._close_panel()
        return True

    def _close_panel(self):
        self.panel = None
        self.investigation.buttons = []
        self.keys.clear()
        if self._all_evidence() and not self.truth_understood:
            self._begin_realisation()

    def _begin_realisation(self):
        if not self._all_evidence():
            return False
        self.panel = None
        self.showing_realisation = True
        self.investigation.realisation_page = 0
        self.investigation.seen = set()
        self.investigation.buttons = []
        self.keys.clear()
        return True

    def _dismiss_realisation(self):
        ui = self.investigation
        if not self.showing_realisation or not self._all_evidence():
            return False
        if ui.realisation_page != len(REALISATION) - 1:
            return False
        ui.seen.add(ui.realisation_page)
        if ui.seen != set(range(len(REALISATION))):
            return False
        self.showing_realisation = False
        self.truth_understood = True
        ui.buttons = []
        self.keys.clear()
        self.audio.play("achievement", volume_scale=0.8)
        return True

    # -------------------------------------------------------------------------
    # Core Narrative Branching (BE / HE)
    # -------------------------------------------------------------------------
    def _on_kitchen_interact(self):
        """Food Synthesizer interaction:
        - If truth NOT understood:
          Directly enters BE nutrient preparation (NutrientPrepView).
          No B01 transition screen! The exploration is already the BE mission scene.
        - If truth understood:
          Branch into Happy Ending (HE cooking counter -> lab map).
        """
        self.panel = None
        self.keys.clear()
        if self.truth_understood:
            # HE Branch: Start HE Cooking Scene in counter mode first
            from scenes.happy_ending_view import HappyEndingView
            from scenes.he_cooking_scene import HECookingScene
            ending = HappyEndingView(start_stage="H01")
            ending.h01_confirmed = True
            # Initial mode counter: cook food first, then enter HE lab map upon picking up bowl
            he_cooking = HECookingScene(ending, initial_mode="counter")
            self.audio.play("click", volume_scale=0.8)
            self.window.show_view(he_cooking)
        else:
            # BE Branch: Direct cooking opens NutrientPrepView without any B01 transition card
            from scenes.future_nutrient_view import NutrientPrepView
            if self.nutrient_view is None:
                self.nutrient_view = NutrientPrepView(self)
            self.audio.play("click", volume_scale=0.8)
            self.window.show_view(self.nutrient_view)

    def _on_capsule_interact(self):
        """Physical Jump Capsule interaction:
        - If truth understood: Warns that physical jump is the cause of the loop.
        - If truth NOT understood:
          Directly checks departure (if nutrient eaten -> opens TransitDepartureView,
          otherwise prompts to synthesize nutrient block first).
          No B01 transition card!
        """
        self.panel = None
        self.keys.clear()
        if self.truth_understood:
            self._show_notice(
                "Physical Jump Capsule — Danger",
                "You have understood the truth of the closed loop.\n"
                "Physically transporting your body and weapons to the past will only recreate the disasters.\n\n"
                "Prepare a meal at the Food Synthesizer and return empty-handed via Consciousness Return."
            )
        else:
            if not self.nutrient_consumed:
                self._show_notice(
                    "Physical Departure Bay",
                    "Nutritional preparation required.\n\n"
                    "Synthesize and consume standard field ration at the Food Synthesizer before capsule launch."
                )
            else:
                from scenes.future_nutrient_view import TransitDepartureView
                if self.departure_view is None:
                    self.departure_view = TransitDepartureView(self)
                self.audio.play("lock_click", volume_scale=0.7)
                self.window.show_view(self.departure_view)

    def _on_chair_interact(self):
        """Consciousness Return Chair interaction."""
        self.panel = None
        self.keys.clear()
        if not self.truth_understood:
            self._show_notice(
                "Consciousness Return — Coordinates Locked",
                "Primary terminal locked. Unverified temporal anomalies detected.\n\n"
                "Investigate the three laboratory workstations (Holographic Analysis, "
                "Chemical Sample, Research Archive) before initiating return."
            )
        else:
            self._show_notice(
                "Consciousness Return — Preparation",
                "Chef (Internal):\n"
                "\"Before I return to my time... I want to make something warm with my own hands.\n"
                "Not to change history, but for myself.\"\n\n"
                "Step up to the Food Synthesizer to prepare the meal first."
            )


# Alias for backward compatibility with existing callers
IntegratedFutureLabView = FutureLabView


if __name__ == "__main__":
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, "The Last Ingredient | Future Laboratory", resizable=True, fullscreen=START_FULLSCREEN)
    if START_FULLSCREEN:
        window.set_fullscreen(True)
    view = FutureLabView()
    window.show_view(view)
    arcade.run()


__all__ = [
    "FOOTPRINTS",
    "STATIONS",
    "WORLD_W",
    "WORLD_H",
    "bob_offset",
    "get_future_lab_obstacles",
    "FutureLabView",
    "IntegratedFutureLabView",
]
