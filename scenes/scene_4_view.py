"""Scene 4: S04 The Investigation and the Loss
Cinematic Revamped Master Edition:
1. Dynamic Camera & Atmosphere:
   - Cinematic Dolly Zoom (1.0x to 1.25x) during the fatal news reveal.
   - Table Slam Shockwave (screen shake + resonant table thud).
   - Fluorescent interrogation room lighting flicker & deep vignette focus.
2. High-Impact Condensed Script:
   - Punchy, high-tension dramatic pacing without tedious exposition.
3. Interactive Mechanics:
   - Interaction C: Interactive forensic microscope with focus knob revealing the branching hexagonal crystal lattice (Compound CX-47).
   - Interaction B: Branching interrogation response choices (Plead Ignorance vs Face the Blame).
   - Interaction A: Interactive signing of the "Notice of Judicial Liquidation" with pen ink drawing and violent [ REVOKED & SEIZED ] rubber stamp slam.
4. Seamless Transition into Scene 5 (Outside His Old Home).
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
from arcade.types import Color
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD,
    SCENE_4_DIR, START_FULLSCREEN
)
from core.dialogue import DialogueBox
from core.audio import AudioManager
from core.base_view import BaseGameView

# Scene 4 Narrative Phases
PHASE_PART1_INQUIRY = 0         # Opening inquiry across the desk
PHASE_MICROSCOPE_FOCUS = 1      # Interactive forensic microscope focus on CX-47 crystals
PHASE_PART2_FATAL_NEWS = 2      # Table slam, dolly zoom (1.25x), customer death & ruin
PHASE_CHOICE_BRANCH = 3         # Interrogation branching psychological response
PHASE_PART3_REMORSE = 4         # Background 2 crossfade, chef admits negligence
PHASE_SIGN_DOCUMENT = 5         # Interactive signing of Liquidation Notice & [REVOKED & SEIZED] stamp
PHASE_PART4_LOSS_MONTAGE = 6    # Cinematic loss narrative
PHASE_COMPLETED = 7             # Step into rainy street


class Scene4View(BaseGameView):
    """Revamped Cinematic Scene 4 View: S04 The Investigation and the Loss."""

    def __init__(self):
        super().__init__()
        self.audio = AudioManager()
        self.t = 0.0
        self.phase = PHASE_PART1_INQUIRY

        # ---- Load Scene 4 Adaptive Textures (16:10 original & 16:9 cropped per GEMINI.md)
        bg1_16_10_path = SCENE_4_DIR / "Background 1.png"
        bg1_16_9_path = SCENE_4_DIR / "Background 1_1280x720.png"
        bg2_16_10_path = SCENE_4_DIR / "Background 2.png"
        bg2_16_9_path = SCENE_4_DIR / "Background 2_1280x720.png"

        self.bg1_16_10 = arcade.load_texture(str(bg1_16_10_path))
        self.bg1_16_9 = arcade.load_texture(str(bg1_16_9_path)) if bg1_16_9_path.exists() else self.bg1_16_10
        self.bg2_16_10 = arcade.load_texture(str(bg2_16_10_path))
        self.bg2_16_9 = arcade.load_texture(str(bg2_16_9_path)) if bg2_16_9_path.exists() else self.bg2_16_10

        # Smooth Background Crossfade State (0.0 = Background 1, 1.0 = Background 2)
        self.bg2_alpha = 0.0
        self.target_bg2_alpha = 0.0

        # Cinematic Camera Dolly Zoom & Shake
        self.camera_zoom = 1.0
        self.target_zoom = 1.0
        self.shake_duration = 0.0
        self.shake_intensity = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0

        # Fluorescent light flicker effect
        self.flicker_alpha = 0

        # Loss vignette darkness (0.0 = normal, 1.0 = deep cinematic dark)
        self.vignette_alpha = 0.0
        self.target_vignette_alpha = 0.0

        # ---- Interaction C: Microscope Focus State
        self.microscope_focus = 0.25   # 0.0 (very blurry) to 1.0 (razor-sharp)
        self.slider_dragging = False
        self.focus_btn_hovered = False
        self.confirm_focus_hovered = False

        # ---- Interaction B: Dialogue Branch Choices
        self.choice_hovered = None     # 0 or 1
        self.chosen_branch = None      # "ignorance" or "blame"

        # ---- Interaction A: Notice of Liquidation & Signature State
        self.doc_signed = False
        self.signing_active = False
        self.signature_points = []     # List of (x, y) stroke points drawn by user
        self.sign_btn_hovered = False
        self.stamp_anim_timer = 0.0    # Counts up when signed to drop stamp
        self.stamp_applied = False
        self.proceed_loss_hovered = False

        # Transition State
        self.transitioning = False
        self.fade_alpha = 0.0

        # Dialogue System
        self.dialogue = DialogueBox()

        # Audio paper slide on scene start
        self.audio.play("paper_slide", volume_scale=0.85)

        # Start initial dialogue sequence
        self._start_part1_dialogue()

    # ---------------------------------------------------------------- Script & Sequences
    def _start_part1_dialogue(self):
        """Part 1: The opening statement and presentation of forensic findings."""
        self.phase = PHASE_PART1_INQUIRY
        self.target_zoom = 1.0
        script = [
            (
                "Investigator",
                "\"The substance from your kitchen line wasn't food. It's a military-grade neurotoxin.\"",
                (235, 140, 130)
            ),
            (
                "Investigator",
                "\"Take the microscope. Inspect the crystalline lattice yourself.\"",
                (235, 140, 130)
            ),
        ]
        self.dialogue.start_dialogue(script, on_complete=self._on_part1_finished)

    def _on_part1_finished(self):
        """Open the interactive microscope viewer (Interaction C)."""
        self.phase = PHASE_MICROSCOPE_FOCUS
        self.audio.play("click", volume_scale=0.7)

    def _finish_microscope_inspection(self):
        """Called when player confirms the focused forensic evidence."""
        self.audio.play("click", volume_scale=0.7)
        self._start_part2_fatal_news()

    def _start_part2_fatal_news(self):
        """Part 2: Table slam shockwave, dolly zoom (1.25x), and fatal revelation."""
        self.phase = PHASE_PART2_FATAL_NEWS

        # 1. Table Slam Shockwave & Camera Jolt
        self.shake_duration = 0.65
        self.shake_intensity = 26.0
        self.audio.play("table_slam", volume_scale=1.0)
        self.audio.play("choking_heartbeat", volume_scale=0.85)

        # 2. Cinematic Dolly Zoom in onto the confrontation
        self.target_zoom = 1.25

        script = [
            (
                "Investigator",
                "\"The patron who consumed your special tonight... is dead.\"",
                (255, 50, 45)
            ),
            (
                "Chef",
                "\"Dead...? No... God, no...\"",
                (240, 215, 160)
            ),
            (
                "Investigator",
                "\"Manslaughter charges are filed. Civil restitution will liquidate everything you own.\"",
                (235, 140, 130)
            ),
        ]
        self.dialogue.start_dialogue(script, on_complete=self._on_part2_finished)

    def _on_part2_finished(self):
        """Trigger branching psychological response (Interaction B)."""
        self.phase = PHASE_CHOICE_BRANCH

    def _choose_branch(self, branch_idx: int):
        """Handle player's dialogue choice."""
        self.audio.play("click", volume_scale=0.75)
        if branch_idx == 0:
            self.chosen_branch = "ignorance"
            branch_script = [
                (
                    "Chef",
                    "\"I thought the outer carton was genuine! I never imagined someone would disguise lethal poison as seasoning!\"",
                    (240, 215, 160)
                ),
                (
                    "Investigator",
                    "\"Ignorance is no defense when someone dies on your dining floor. You knew the warning label was torn, yet you left it in reach.\"",
                    (235, 140, 130)
                ),
            ]
        else:
            self.chosen_branch = "blame"
            branch_script = [
                (
                    "Chef",
                    "\"It was my arrogance... I was obsessing over that missing flavor, and I gambled with an untested sample.\"",
                    (240, 215, 160)
                ),
                (
                    "Investigator",
                    "\"At least you spare us hollow excuses. But remorse will not resurrect the patron, nor will it satisfy the courts.\"",
                    (235, 140, 130)
                ),
            ]

        self.phase = PHASE_PART3_REMORSE
        # Smoothly crossfade to Background 2 (Chef lowers head in remorse)
        self.target_bg2_alpha = 1.0
        self.target_zoom = 1.15
        self.dialogue.start_dialogue(branch_script, on_complete=self._on_part3_finished)

    def _on_part3_finished(self):
        """Transition into Interaction A: Signing the Judicial Liquidation Notice."""
        self.phase = PHASE_SIGN_DOCUMENT
        self.target_zoom = 1.0  # Reset zoom to inspect document
        self.audio.play("paper_slide", volume_scale=0.9)

    def _apply_court_stamp(self):
        """Slam the [REVOKED & SEIZED] rubber stamp onto the signed document."""
        self.stamp_applied = True
        self.shake_duration = 0.50
        self.shake_intensity = 22.0
        self.audio.play("stamp_seal", volume_scale=1.0)
        self.audio.play("montage_impact", volume_scale=0.75)

    def _start_loss_montage(self):
        """Begin the poignant loss epilogue."""
        self.phase = PHASE_PART4_LOSS_MONTAGE
        self.target_vignette_alpha = 0.84
        self.audio.play("clock_chime", volume_scale=0.75)

        script = [
            (
                "Narrator",
                "The restaurant doors were padlocked. Decades of savings were liquidated under crushing debt.",
                (215, 210, 200)
            ),
            (
                "Narrator",
                "Surrendering his keys to the liquidator, he stepped out into the freezing rain.",
                (215, 210, 200)
            ),
        ]
        self.dialogue.start_dialogue(script, on_complete=self._on_loss_finished)

    def _on_loss_finished(self):
        """Dialogue sequence complete; prompt transition into rainy street."""
        self.phase = PHASE_COMPLETED

    def _proceed_to_next_scene(self):
        """Transition into Scene 5: S05 Outside His Old Home."""
        from scenes.scene_5_view import Scene5View
        self.window.show_view(Scene5View(from_scene_1=False))

    # ---------------------------------------------------------------- Update Loop
    def on_update(self, dt: float):
        if self.is_paused:
            return
        self.t += dt

        # Smooth camera zoom interpolation
        if abs(self.camera_zoom - self.target_zoom) > 0.001:
            self.camera_zoom += (self.target_zoom - self.camera_zoom) * min(1.0, dt * 4.0)

        # Screen shake update
        if self.shake_duration > 0:
            self.shake_duration -= dt
            decay = max(0.0, self.shake_duration / 0.65)
            self.shake_offset_x = random.uniform(-self.shake_intensity, self.shake_intensity) * decay
            self.shake_offset_y = random.uniform(-self.shake_intensity, self.shake_intensity) * decay
        else:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0

        # Subtly flickering fluorescent light
        if random.random() < 0.05:
            self.flicker_alpha = random.randint(15, 38)
        else:
            self.flicker_alpha = max(0, int(self.flicker_alpha - dt * 120))

        # Smooth crossfade to Background 2
        if abs(self.bg2_alpha - self.target_bg2_alpha) > 0.001:
            diff = self.target_bg2_alpha - self.bg2_alpha
            self.bg2_alpha += diff * min(1.0, dt * 3.5)

        # Smooth vignette dark overlay
        if abs(self.vignette_alpha - self.target_vignette_alpha) > 0.001:
            diff = self.target_vignette_alpha - self.vignette_alpha
            self.vignette_alpha += diff * min(1.0, dt * 2.5)

        # Update dialogue system
        if self.dialogue.active:
            self.dialogue.update(dt)

        # Handle stamp animation timer
        if self.doc_signed and not self.stamp_applied:
            self.stamp_anim_timer += dt
            if self.stamp_anim_timer >= 0.40:
                self._apply_court_stamp()

        # Handle scene fade-to-black exit
        if self.transitioning:
            self.fade_alpha = min(1.0, self.fade_alpha + dt * 2.0)
            if self.fade_alpha >= 1.0:
                self._proceed_to_next_scene()

    # ---------------------------------------------------------------- Draw Loop
    def on_draw(self):
        self.clear(color=(12, 10, 16))
        self.use_game_camera()

        corr = self.aspect_ratio_correction

        # Apply Camera Zoom & Screen Shake to World Camera
        if self.camera:
            self.camera.zoom = self.camera_zoom
            # Center of zoom is the table / interview desk (cx=640, cy=380)
            center_x = SCREEN_WIDTH / 2
            center_y = SCREEN_HEIGHT / 2 + 10
            self.camera.position = (center_x + self.shake_offset_x, center_y + self.shake_offset_y)

        # 1. Base Interrogation Background (Adaptive 16:9 / 16:10 per GEMINI.md)
        bg_interrogation = self.get_adaptive_texture(self.bg1_16_9, self.bg1_16_10)
        arcade.draw_texture_rect(
            bg_interrogation,
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        )

        # 2. Remorse Background Layer with Smooth Crossfade (Adaptive 16:9 / 16:10)
        if self.bg2_alpha > 0.001:
            bg_remorse = self.get_adaptive_texture(self.bg2_16_9, self.bg2_16_10)
            alpha_byte = int(max(0.0, min(1.0, self.bg2_alpha)) * 255)
            arcade.draw_texture_rect(
                bg_remorse,
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                color=Color(255, 255, 255, alpha_byte)
            )

        # 3. Interrogation Room Fluorescent Light Flicker Overlay
        if self.flicker_alpha > 0:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (200, 225, 255, self.flicker_alpha)
            )

        # 4. Cinematic Vignette Overlay (Darkens during loss epilogue & remorse)
        if self.vignette_alpha > 0.01:
            vig_byte = int(self.vignette_alpha * 255)
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (6, 6, 10, vig_byte)
            )

        # Reset camera zoom and position for clean, razor-sharp UI / Modals rendering
        if self.camera:
            self.camera.zoom = 1.0
            self.camera.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

        # 5. Cinematic Dialogue Box (When active and not in modal interactions)
        if self.dialogue.active and self.phase not in (PHASE_MICROSCOPE_FOCUS, PHASE_CHOICE_BRANCH, PHASE_SIGN_DOCUMENT):
            self.dialogue.draw(corr)

        # 6. Interaction C: Microscope Focus Viewer
        if self.phase == PHASE_MICROSCOPE_FOCUS:
            self._draw_microscope_modal(corr)

        # 7. Interaction B: Interrogation Choice Branch
        elif self.phase == PHASE_CHOICE_BRANCH:
            self._draw_choice_modal(corr)

        # 8. Interaction A: Notice of Liquidation Signing
        elif self.phase == PHASE_SIGN_DOCUMENT:
            self._draw_document_signing_modal(corr)

        # 9. Completed Scene Prompt (Step into Rainy Street)
        elif self.phase == PHASE_COMPLETED and not self.transitioning:
            self._draw_proceed_prompt_button(corr)

        # 10. Fade-to-black transition overlay
        if self.fade_alpha > 0.01:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (0, 0, 0, int(self.fade_alpha * 255))
            )

        # 11. Global Pause Overlay (BaseGameView)
        self.draw_pause_overlay()

    # ---------------------------------------------------------------- Interaction C: Microscope
    def _draw_microscope_modal(self, corr: float):
        """Draw interactive microscope viewer with adjustable focus knob/slider."""
        arcade.draw_rect_filled(
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
            (8, 9, 14, 230)
        )

        cx = SCREEN_WIDTH / 2
        cy = SCREEN_HEIGHT / 2
        mw = 880 * corr
        mh = 560

        # Dossier Chassis
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, mw, mh), (18, 22, 30, 252))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, mw + 4, mh + 4), (195, 160, 90), 2.2)

        # Header Title
        arcade.draw_text(
            "FORENSIC OPTICAL MICROSCOPY · SAMPLE CX-47",
            cx, cy + mh / 2 - 36,
            (255, 215, 95), 15, anchor_x="center", bold=True
        )
        arcade.draw_text(
            "Rotate focus knob or drag slider until crystalline structure resolves into sharp focus.",
            cx, cy + mh / 2 - 58,
            (175, 190, 215), 11, anchor_x="center"
        )
        arcade.draw_line(
            cx - 390 * corr, cy + mh / 2 - 70,
            cx + 390 * corr, cy + mh / 2 - 70,
            (195, 160, 90, 180), 1.5
        )

        # Microscope Circular Viewport (Left)
        view_cx = cx - 210 * corr
        view_cy = cy + 15
        view_radius = 145

        arcade.draw_circle_filled(view_cx, view_cy, view_radius, (10, 14, 24))
        arcade.draw_circle_outline(view_cx, view_cy, view_radius + 4, (80, 120, 175), 2.5)

        # Draw Crosshair Reticle
        arcade.draw_line(view_cx - view_radius, view_cy, view_cx + view_radius, view_cy, (60, 90, 130, 130), 1.0)
        arcade.draw_line(view_cx, view_cy - view_radius, view_cx, view_cy + view_radius, (60, 90, 130, 130), 1.0)
        arcade.draw_circle_outline(view_cx, view_cy, 45, (60, 90, 130, 120), 1.0)

        # Draw Branching Crystals with sharpness based on self.microscope_focus
        sharpness = max(0.0, min(1.0, self.microscope_focus))
        self._draw_focused_crystals(view_cx, view_cy, 68 * corr, sharpness)

        # Reticle HUD readout
        arcade.draw_text(
            f"MAGNIFICATION: 1200X   |   FOCUS: {int(sharpness * 100)}%",
            view_cx, view_cy - view_radius - 24,
            (140, 200, 255), 10.5, anchor_x="center", bold=True
        )

        # Right Side Information & Analysis
        rx = cx + 10 * corr
        ry = cy + mh / 2 - 100

        arcade.draw_text("FORENSIC ANALYSIS SUMMARY:", rx, ry, (255, 235, 180), 13, bold=True)
        ry -= 26
        arcade.draw_text("Compound: Weaponised Neuro-Active CX-47", rx, ry, (255, 135, 120), 11, bold=True)
        ry -= 22
        arcade.draw_text("Culinary Clearance: ZERO (Instant Respiratory Arrest)", rx, ry, (255, 80, 70), 11, bold=True)

        # Focus Control Section
        card_cx = rx + 195 * corr
        card_cy = cy - 25
        card_w = 400 * corr
        card_h = 165
        arcade.draw_rect_filled(arcade.XYWH(card_cx, card_cy, card_w, card_h), (26, 32, 44, 240))
        arcade.draw_rect_outline(arcade.XYWH(card_cx, card_cy, card_w, card_h), (80, 140, 220), 1.6)

        arcade.draw_text("INTERACTIVE FOCUS ADJUSTMENT", card_cx - card_w / 2 + 16, card_cy + card_h / 2 - 24, (255, 215, 100), 11, bold=True)
        arcade.draw_text("Drag slider or click 'Tune Focus' to resolve hexagonal dendrites:", card_cx - card_w / 2 + 16, card_cy + card_h / 2 - 42, (235, 245, 255), 11)

        # Slider Track
        slider_x = card_cx
        slider_y = card_cy - 12
        slider_w = 320 * corr
        slider_h = 10
        arcade.draw_rect_filled(arcade.XYWH(slider_x, slider_y, slider_w, slider_h), (14, 18, 26))
        arcade.draw_rect_outline(arcade.XYWH(slider_x, slider_y, slider_w, slider_h), (100, 160, 240), 1.2)

        # Filled track up to handle
        handle_x = (slider_x - slider_w / 2) + slider_w * sharpness
        fill_w = max(4.0, handle_x - (slider_x - slider_w / 2))
        arcade.draw_rect_filled(arcade.XYWH((slider_x - slider_w / 2) + fill_w / 2, slider_y, fill_w, slider_h - 2), (60, 180, 240, 200))

        # Slider Handle Knob
        knob_color = (255, 235, 120) if not self.slider_dragging else (255, 255, 255)
        arcade.draw_circle_filled(handle_x, slider_y, 11, knob_color)
        arcade.draw_circle_outline(handle_x, slider_y, 11, (30, 60, 100), 2.0)

        # Quick Tune Button
        btn_y = card_cy - 52
        btn_w = 170 * corr
        btn_h = 32
        btn_bg = (40, 60, 90) if not self.focus_btn_hovered else (60, 90, 135)
        arcade.draw_rect_filled(arcade.XYWH(card_cx, btn_y, btn_w, btn_h), btn_bg)
        arcade.draw_rect_outline(arcade.XYWH(card_cx, btn_y, btn_w, btn_h), (120, 180, 255), 1.2)
        arcade.draw_text("[ AUTO-FOCUS + ]", card_cx, btn_y - 5, (240, 248, 255), 11, anchor_x="center", bold=True)

        # Bottom Action Button
        bot_btn_y = cy - mh / 2 + 40
        bot_btn_w = 460 * corr
        bot_btn_h = 44
        is_focused = sharpness >= 0.85

        if is_focused:
            pulse = math.sin(self.t * 4.0) * 0.25 + 0.75
            btn_col = (45, 36, 18) if not self.confirm_focus_hovered else (75, 58, 26)
            border_col = (255, 215, 80, int(255 * pulse))
            text_str = "▶  [ CONFIRM CRYSTALLINE MATCH · CONFRONT INVESTIGATOR ]"
            text_col = (255, 245, 220, int(255 * pulse))
        else:
            btn_col = (28, 30, 36)
            border_col = (80, 85, 95)
            text_str = "[ ADJUST FOCUS ABOVE 85% TO PROCEED ]"
            text_col = (180, 185, 195)

        arcade.draw_rect_filled(arcade.XYWH(cx, bot_btn_y, bot_btn_w, bot_btn_h), btn_col)
        arcade.draw_rect_outline(arcade.XYWH(cx, bot_btn_y, bot_btn_w, bot_btn_h), border_col, 2.0)
        arcade.draw_text(text_str, cx, bot_btn_y - 6, text_col, 12, anchor_x="center", bold=True)

    def _draw_focused_crystals(self, cx: float, cy: float, radius: float, sharpness: float):
        """Draw hexagonal crystal lattice that dynamically shifts from blurry liquid bokeh to sharp branching dendrites."""
        blur_factor = 1.0 - sharpness

        # 1. Realistic Multi-Layer Optical Bokeh Haze (Simulates out-of-focus liquid droplet on glass slide)
        if blur_factor > 0.02:
            # Concentric feathering rings create a smooth Gaussian-like optical blur gradient
            for step in range(9, 0, -1):
                r_step = radius * (0.35 + step * 0.14 * (1.0 + blur_factor * 0.5))
                a_step = int(22 * blur_factor * (1.0 - (step / 10.0) ** 1.3))
                if a_step > 0:
                    arcade.draw_circle_filled(cx, cy, r_step, (35, 95, 180, a_step))
                    # Subtle secondary optical refraction lobe
                    lobe_x = cx + math.sin(self.t * 0.7) * 4
                    lobe_y = cy + math.cos(self.t * 0.6) * 3
                    arcade.draw_circle_filled(lobe_x, lobe_y, r_step * 0.72, (60, 145, 235, int(a_step * 0.75)))

            # Drifting microscopic suspension particulates in fluid medium
            sample_particulates = [
                (-32, -26, 2.2), (36, 24, 1.8), (-20, 38, 2.5),
                (42, -18, 1.6), (-38, 12, 2.0), (10, -42, 1.9)
            ]
            for idx, (ox, oy, sz) in enumerate(sample_particulates):
                drift_x = cx + ox + math.sin(self.t * 0.9 + idx * 1.3) * 5
                drift_y = cy + oy + math.cos(self.t * 0.7 + idx * 1.7) * 4
                p_alpha = int(55 * blur_factor)
                p_rad = sz + blur_factor * 2.8
                arcade.draw_circle_filled(drift_x, drift_y, p_rad, (110, 185, 255, p_alpha))

        # 2. Crystal Lattice Visibility: Completely hidden at 0%, smoothly coalescing as focus sharpens
        lattice_progress = max(0.0, min(1.0, (sharpness - 0.06) / 0.94))
        if lattice_progress <= 0:
            return

        line_alpha = int(lattice_progress * 255)
        glow_pulse = math.sin(self.t * 3.5) * 0.15 + 0.85

        # Inner crystal core glow
        arcade.draw_circle_filled(
            cx, cy, radius * 0.65 * lattice_progress,
            (60, 180, 240, int(45 * lattice_progress * glow_pulse))
        )

        vertices = []
        for i in range(6):
            angle = i * (math.pi / 3.0)
            vx = cx + math.cos(angle) * radius * (0.8 + 0.2 * lattice_progress)
            vy = cy + math.sin(angle) * radius * (0.8 + 0.2 * lattice_progress)
            vertices.append((vx, vy, angle))

        # Draw Hexagon Outer Ring & Radial Spokes
        for i in range(6):
            p1 = vertices[i]
            p2 = vertices[(i + 1) % 6]
            arcade.draw_line(p1[0], p1[1], p2[0], p2[1], (130, 225, 255, line_alpha), 2.2 * sharpness + 0.8)
            arcade.draw_line(cx, cy, p1[0], p1[1], (80, 160, 230, int(line_alpha * 0.7)), 1.2)

        # Center Crystal Nucleus
        arcade.draw_circle_filled(cx, cy, 5.0 * sharpness + 2.0, (230, 250, 255, line_alpha))

        # 3. Razor-sharp Dendrites branch out as focus reaches high clarity (> 35%)
        if sharpness > 0.35:
            dendrite_mult = (sharpness - 0.35) / 0.65
            for vx, vy, angle in vertices:
                spine_len = radius * 0.65 * dendrite_mult
                tip_x = vx + math.cos(angle) * spine_len
                tip_y = vy + math.sin(angle) * spine_len
                arcade.draw_line(vx, vy, tip_x, tip_y, (140, 230, 255, line_alpha), 2.0)

                for frac in (0.35, 0.70):
                    bx = vx + math.cos(angle) * (spine_len * frac)
                    by = vy + math.sin(angle) * (spine_len * frac)
                    branch_len = radius * 0.28 * dendrite_mult
                    lx = bx + math.cos(angle + math.pi / 4.0) * branch_len
                    ly = by + math.sin(angle + math.pi / 4.0) * branch_len
                    rx_b = bx + math.cos(angle - math.pi / 4.0) * branch_len
                    ry_b = by + math.sin(angle - math.pi / 4.0) * branch_len
                    arcade.draw_line(bx, by, lx, ly, (90, 200, 255, int(line_alpha * 0.85)), 1.5)
                    arcade.draw_line(bx, by, rx_b, ry_b, (90, 200, 255, int(line_alpha * 0.85)), 1.5)

    # ---------------------------------------------------------------- Interaction B: Choice Branch
    def _draw_choice_modal(self, corr: float):
        """Draw high-tension branching response choices."""
        cx = SCREEN_WIDTH / 2
        cy = 145
        bw = 540 * corr
        bh = 54

        # Prompt Header
        arcade.draw_rect_filled(arcade.XYWH(cx, cy + 62, 420 * corr, 28), (14, 18, 26, 235))
        arcade.draw_text("SELECT YOUR RESPONSE TO THE INVESTIGATOR", cx, cy + 56, COLOR_GOLD, 11, anchor_x="center", bold=True)

        # Choice 0: Plead Ignorance
        c0_y = cy + 26
        bg0 = (42, 28, 22) if self.choice_hovered != 0 else (75, 42, 28)
        border0 = (255, 180, 80) if self.choice_hovered != 0 else (255, 235, 140)
        arcade.draw_rect_filled(arcade.XYWH(cx, c0_y, bw, bh), bg0)
        arcade.draw_rect_outline(arcade.XYWH(cx, c0_y, bw, bh), border0, 2.0)
        arcade.draw_text("[ A: Plead Ignorance ]", cx - bw / 2 + 18, c0_y + 8, (255, 215, 100), 12, bold=True)
        arcade.draw_text("\"I thought the carton was genuine! I never imagined someone would disguise poison!\"", cx - bw / 2 + 18, c0_y - 12, (255, 255, 255), 11, bold=True)

        # Choice 1: Face the Blame
        c1_y = cy - 38
        bg1 = (36, 18, 24) if self.choice_hovered != 1 else (68, 28, 38)
        border1 = (255, 90, 85) if self.choice_hovered != 1 else (255, 160, 150)
        arcade.draw_rect_filled(arcade.XYWH(cx, c1_y, bw, bh), bg1)
        arcade.draw_rect_outline(arcade.XYWH(cx, c1_y, bw, bh), border1, 2.0)
        arcade.draw_text("[ B: Face the Blame ]", cx - bw / 2 + 18, c1_y + 8, (255, 130, 120), 12, bold=True)
        arcade.draw_text("\"It was my arrogance... I wanted a flawless taste, and I ignored the torn label.\"", cx - bw / 2 + 18, c1_y - 12, (255, 255, 255), 11, bold=True)

    # ---------------------------------------------------------------- Interaction A: Document Signing
    def _draw_document_signing_modal(self, corr: float):
        """Draw interactive Judicial Liquidation Notice with draggable signature and heavy court seal."""
        # Dimming backdrop
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT), (8, 6, 10, 220))

        cx = SCREEN_WIDTH / 2
        cy = SCREEN_HEIGHT / 2
        dw = 740 * corr
        dh = 570

        # Official Legal Parchment Background
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, dw, dh), (242, 238, 228))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, dw + 4, dh + 4), (160, 140, 110), 2.5)
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, dw - 16, dh - 16), (190, 175, 145), 1.2)

        # Document Header
        arcade.draw_text("MUNICIPAL MAGISTRATE & HEALTH COMMISSION", cx, cy + dh / 2 - 40, (30, 28, 26), 14, anchor_x="center", bold=True)
        arcade.draw_text("NOTICE OF JUDICIAL SEIZURE & TOTAL LIQUIDATION", cx, cy + dh / 2 - 64, (160, 25, 20), 15, anchor_x="center", bold=True)
        arcade.draw_line(cx - 320 * corr, cy + dh / 2 - 76, cx + 320 * corr, cy + dh / 2 - 76, (140, 125, 105), 1.5)

        # Legal Recital
        tx = cx - 310 * corr
        ty = cy + dh / 2 - 105
        arcade.draw_text("CASE NO: CR-2026-904   |   RESPONDENT: HEAD PROPRIETOR", tx, ty, (65, 60, 55), 11, bold=True)
        ty -= 24
        arcade.draw_text("CHARGE: Involuntary Manslaughter & Unverified Chemical Distribution", tx, ty, (160, 30, 25), 11, bold=True)
        ty -= 28

        terms = [
            "1. CATERING LICENSE: Commercial culinary credentials are permanently revoked.",
            "2. RESTITUTION: Total enterprise assets, kitchen ranges, and equipment are seized",
            "   effective immediately to satisfy civil compensation claims.",
            "3. FORECLOSURE: Residential deed and personal securities are transferred to the",
            "   appointed liquidator under court order #884-B."
        ]
        for term in terms:
            arcade.draw_text(term, tx, ty, (35, 30, 25), 11, bold=True)
            ty -= 20

        # Signature Area Box
        sig_box_cx = cx
        sig_box_cy = cy - 80
        sig_box_w = 480 * corr
        sig_box_h = 75

        arcade.draw_rect_filled(arcade.XYWH(sig_box_cx, sig_box_cy, sig_box_w, sig_box_h), (255, 255, 252))
        arcade.draw_rect_outline(arcade.XYWH(sig_box_cx, sig_box_cy, sig_box_w, sig_box_h), (140, 130, 115), 1.5)
        arcade.draw_line(sig_box_cx - sig_box_w / 2 + 20, sig_box_cy - 12, sig_box_cx + sig_box_w / 2 - 20, sig_box_cy - 12, (180, 170, 155), 1.0)

        arcade.draw_text("Signature of Chef / Respondent:  (Click or Drag to Sign)", sig_box_cx - sig_box_w / 2 + 20, sig_box_cy + 18, (100, 90, 75), 11, italic=True)

        # Draw Player's Inked Signature Strokes
        if len(self.signature_points) > 1:
            for i in range(len(self.signature_points) - 1):
                p1 = self.signature_points[i]
                p2 = self.signature_points[i + 1]
                arcade.draw_line(p1[0], p1[1], p2[0], p2[1], (18, 22, 65, 230), 2.5)

        # If not signed yet, provide Quick Sign Button
        if not self.doc_signed:
            btn_y = sig_box_cy - 65
            btn_w = 260 * corr
            btn_h = 36
            btn_bg = (55, 45, 38) if not self.sign_btn_hovered else (95, 75, 55)
            arcade.draw_rect_filled(arcade.XYWH(cx, btn_y, btn_w, btn_h), btn_bg)
            arcade.draw_rect_outline(arcade.XYWH(cx, btn_y, btn_w, btn_h), (210, 180, 120), 1.5)
            arcade.draw_text("✎  [ SIGN NOTICE NOW ]", cx, btn_y - 5, (255, 245, 225), 11, anchor_x="center", bold=True)

        # Violent Court Rubber Stamp [ REVOKED & SEIZED ]
        if self.stamp_applied:
            stamp_cx = cx + 110 * corr
            stamp_cy = cy + 25
            stamp_w = 320 * corr
            stamp_h = 95
            stamp_angle = -14.0

            # Outer Stamped Border
            arcade.draw_rect_outline(
                arcade.XYWH(stamp_cx, stamp_cy, stamp_w, stamp_h),
                (195, 25, 25, 235), 4.0, tilt_angle=stamp_angle
            )
            arcade.draw_rect_outline(
                arcade.XYWH(stamp_cx, stamp_cy, stamp_w - 10, stamp_h - 10),
                (195, 25, 25, 170), 1.5, tilt_angle=stamp_angle
            )

            # Stamped Bold Red Text
            arcade.draw_text(
                "REVOKED  &  SEIZED",
                stamp_cx, stamp_cy + 10,
                (190, 20, 20, 240), 17, anchor_x="center", bold=True, rotation=stamp_angle
            )
            arcade.draw_text(
                "— JUDICIAL LIQUIDATION ORDER —",
                stamp_cx, stamp_cy - 16,
                (170, 20, 20, 220), 10, anchor_x="center", bold=True, rotation=stamp_angle
            )

            # Accept Fate & Continue Button
            acc_y = cy - dh / 2 + 42
            acc_w = 380 * corr
            acc_h = 44
            pulse = math.sin(self.t * 3.5) * 0.25 + 0.75
            acc_bg = (35, 20, 24) if not self.proceed_loss_hovered else (75, 25, 32)
            arcade.draw_rect_filled(arcade.XYWH(cx, acc_y, acc_w, acc_h), acc_bg)
            arcade.draw_rect_outline(arcade.XYWH(cx, acc_y, acc_w, acc_h), (255, 70, 60, int(255 * pulse)), 2.0)
            arcade.draw_text("▶  [ SURRENDER KEYS & ACCEPT FATE ]", cx, acc_y - 6, (255, 235, 230, int(255 * pulse)), 12, anchor_x="center", bold=True)

    def _draw_proceed_prompt_button(self, corr: float):
        """Draw button prompting the player to step out into the rainy street."""
        pulse = math.sin(self.t * 3.5) * 0.25 + 0.75
        bx = SCREEN_WIDTH / 2
        by = 80
        bw = 640 * corr
        bh = 50

        arcade.draw_rect_filled(arcade.XYWH(bx, by, bw, bh), (18, 22, 34, int(230 * pulse)))
        arcade.draw_rect_outline(arcade.XYWH(bx, by, bw, bh), (COLOR_GOLD[0], COLOR_GOLD[1], COLOR_GOLD[2], int(255 * pulse)), 2.0)
        arcade.draw_text(
            "▶  [ CLICK or press SPACE to step into the Rainy Street ]",
            bx, by - 6,
            (255, 255, 255, int(255 * pulse)),
            14, anchor_x="center", bold=True
        )

    # ---------------------------------------------------------------- Input Handlers
    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        if self.handle_pause_mouse_motion(x, y):
            return

        vx, vy = self.to_virtual_coords(x, y)
        corr = self.aspect_ratio_correction

        # Microscope Hover Handlers
        if self.phase == PHASE_MICROSCOPE_FOCUS:
            card_cx = SCREEN_WIDTH / 2 + 205 * corr
            card_cy = SCREEN_HEIGHT / 2 - 25
            btn_y = card_cy - 52
            self.focus_btn_hovered = (abs(vx - card_cx) <= 85 * corr and abs(vy - btn_y) <= 16)

            bot_btn_y = SCREEN_HEIGHT / 2 - 240
            self.confirm_focus_hovered = (abs(vx - SCREEN_WIDTH / 2) <= 230 * corr and abs(vy - bot_btn_y) <= 22)

            if self.slider_dragging:
                slider_x = card_cx
                slider_w = 320 * corr
                new_focus = (vx - (slider_x - slider_w / 2)) / slider_w
                self.microscope_focus = max(0.0, min(1.0, new_focus))

        # Choice Hover Handlers
        elif self.phase == PHASE_CHOICE_BRANCH:
            cx = SCREEN_WIDTH / 2
            bw = 540 * corr
            if abs(vx - cx) <= bw / 2:
                if abs(vy - 171) <= 27:
                    self.choice_hovered = 0
                elif abs(vy - 107) <= 27:
                    self.choice_hovered = 1
                else:
                    self.choice_hovered = None
            else:
                self.choice_hovered = None

        # Document Signing Hover Handlers
        elif self.phase == PHASE_SIGN_DOCUMENT:
            cx = SCREEN_WIDTH / 2
            cy = SCREEN_HEIGHT / 2
            sig_box_y = cy - 80
            btn_y = sig_box_y - 65
            self.sign_btn_hovered = (abs(vx - cx) <= 130 * corr and abs(vy - btn_y) <= 18)

            acc_y = cy - 243
            self.proceed_loss_hovered = (abs(vx - cx) <= 190 * corr and abs(vy - acc_y) <= 22)

            if self.signing_active:
                self.signature_points.append((vx, vy))
                if len(self.signature_points) % 8 == 0:
                    self.audio.play("pen_sign", volume_scale=0.6)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        if self.handle_pause_mouse_press(x, y, button):
            return

        vx, vy = self.to_virtual_coords(x, y)
        corr = self.aspect_ratio_correction

        if self.phase == PHASE_MICROSCOPE_FOCUS:
            card_cx = SCREEN_WIDTH / 2 + 205 * corr
            card_cy = SCREEN_HEIGHT / 2 - 25
            slider_x = card_cx
            slider_y = card_cy - 12
            slider_w = 320 * corr

            # Clicked slider track
            if abs(vx - slider_x) <= slider_w / 2 + 10 and abs(vy - slider_y) <= 16:
                self.slider_dragging = True
                new_focus = (vx - (slider_x - slider_w / 2)) / slider_w
                self.microscope_focus = max(0.0, min(1.0, new_focus))
                self.audio.play("click", volume_scale=0.5)
                return

            # Clicked Quick Auto-focus Button
            btn_y = card_cy - 52
            if abs(vx - card_cx) <= 85 * corr and abs(vy - btn_y) <= 16:
                self.microscope_focus = min(1.0, self.microscope_focus + 0.35)
                self.audio.play("click", volume_scale=0.6)
                return

            # Clicked Confirm Focused Evidence Button
            bot_btn_y = SCREEN_HEIGHT / 2 - 240
            if abs(vx - SCREEN_WIDTH / 2) <= 230 * corr and abs(vy - bot_btn_y) <= 22 and self.microscope_focus >= 0.85:
                self._finish_microscope_inspection()
                return

        elif self.phase == PHASE_CHOICE_BRANCH:
            if self.choice_hovered is not None:
                self._choose_branch(self.choice_hovered)
                return

        elif self.phase == PHASE_SIGN_DOCUMENT:
            cx = SCREEN_WIDTH / 2
            cy = SCREEN_HEIGHT / 2
            sig_box_y = cy - 80
            sig_box_w = 480 * corr
            sig_box_h = 75

            # Click inside signature box to start signing stroke
            if abs(vx - cx) <= sig_box_w / 2 and abs(vy - sig_box_y) <= sig_box_h / 2:
                self.signing_active = True
                self.signature_points = [(vx, vy)]
                self.audio.play("pen_sign", volume_scale=0.7)
                return

            # Click Quick Sign Button
            btn_y = sig_box_y - 65
            if not self.doc_signed and abs(vx - cx) <= 130 * corr and abs(vy - btn_y) <= 18:
                self._quick_sign_document(cx, sig_box_y, corr)
                return

            # Click Surrender Keys Button or click anywhere after stamp applied
            if self.stamp_applied:
                self.audio.play("click", volume_scale=0.6)
                self._start_loss_montage()
                return

        elif self.dialogue.active:
            self.dialogue.advance()
            return

        elif self.phase == PHASE_COMPLETED and not self.transitioning:
            self.transitioning = True
            self.audio.play("click", volume_scale=0.5)

    def on_mouse_release(self, x: float, y: float, button: int, modifiers: int):
        self.slider_dragging = False
        if self.signing_active and len(self.signature_points) > 12:
            self.doc_signed = True
        self.signing_active = False

    def _quick_sign_document(self, cx: float, sig_y: float, corr: float):
        """Generate authentic handwritten signature ink curve across the line."""
        self.audio.play("pen_sign", volume_scale=0.85)
        self.signature_points = []
        start_x = cx - 180 * corr
        for i in range(50):
            frac = i / 49.0
            px = start_x + frac * (360 * corr)
            py = sig_y - 10 + math.sin(frac * 14.0) * 12.0 + (math.cos(frac * 8.0) * 6.0 if frac > 0.4 else 0)
            self.signature_points.append((px, py))
        self.doc_signed = True

    def on_key_press(self, key: int, modifiers: int):
        if self.handle_pause_key(key):
            return

        if key == arcade.key.F11:
            self.toggle_fullscreen()
            return

        if self.phase == PHASE_MICROSCOPE_FOCUS:
            if key in (arcade.key.LEFT, arcade.key.A):
                self.microscope_focus = max(0.0, self.microscope_focus - 0.15)
                self.audio.play("click", volume_scale=0.4)
            elif key in (arcade.key.RIGHT, arcade.key.D, arcade.key.UP, arcade.key.W):
                self.microscope_focus = min(1.0, self.microscope_focus + 0.15)
                self.audio.play("click", volume_scale=0.4)
            elif key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                if self.microscope_focus >= 0.85:
                    self._finish_microscope_inspection()
                else:
                    self.microscope_focus = min(1.0, self.microscope_focus + 0.35)
                    self.audio.play("click", volume_scale=0.5)
                    if self.microscope_focus >= 0.85:
                        self._finish_microscope_inspection()
            return

        if self.phase == PHASE_CHOICE_BRANCH:
            if key in (arcade.key.KEY_1, arcade.key.A):
                self._choose_branch(0)
            elif key in (arcade.key.KEY_2, arcade.key.B):
                self._choose_branch(1)
            return

        if self.phase == PHASE_SIGN_DOCUMENT:
            if not self.doc_signed and key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.S, arcade.key.E):
                corr = self.aspect_ratio_correction
                self._quick_sign_document(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 80, corr)
            elif self.stamp_applied and key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                self.audio.play("click", volume_scale=0.6)
                self._start_loss_montage()
            return

        if self.dialogue.active:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                self.dialogue.advance()
                return

        if self.phase == PHASE_COMPLETED and not self.transitioning:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                self.transitioning = True
                self.audio.play("click", volume_scale=0.5)


# Standalone runner for direct testing
if __name__ == "__main__":
    window = arcade.Window(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Scene 4: S04 The Investigation and the Loss · Master Edition",
        resizable=False,
        fullscreen=START_FULLSCREEN
    )
    if START_FULLSCREEN:
        window.set_fullscreen(True)
    view = Scene4View()
    window.show_view(view)
    arcade.run()
