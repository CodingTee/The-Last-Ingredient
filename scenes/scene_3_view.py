"""Scene 3: S03 The Incident
Faithfully implementing the S03 Incident Montage from the National Champion Script:
1. A dramatic 5-panel comic-montage visual alternating in rhythm:
   - Panel 1: Top connected (inner silver sachet unpacked, torn warning packaging).
   - Panel 2: Bottom connected (pouring mystery powder into kitchen SALT container).
   - Panel 3: Top connected (optimized bottom margin, guest collapses in dining room).
   - Panel 4: Bottom connected (emergency ambulance outside window with flashing red/blue lights).
   - Panel 5: Top connected (police hazard cordon, chef staring at evidence bag & torn label).
2. Rhythmic cut-in timing: Panel 1 at 0.0s, Panel 2 at 1.5s, Panel 3 at 3.0s, Panel 4 at 4.5s, Panel 5 at 6.0s.
3. Visceral cinematic effects: Camera shake shockwave on each cut-in, subtle flash, and customized SFX.
4. Emergency beacon effect for Panel 4 & 5.
5. Dialogue / narrative sequence in pure English after all panels appear.
6. Seamless transition into RainyStreetView (Chapter One: Outside His Old Home).
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
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD,
    SCENE_1_DIR, SCENE_3_DIR, START_FULLSCREEN
)
from core.dialogue import DialogueBox
from core.audio import AudioManager
from core.base_view import BaseGameView


class Scene3View(BaseGameView):
    """Scene 3 View: S03 The Incident Montage."""

    def __init__(self):
        super().__init__()
        self.audio = AudioManager()
        self.t = 0.0
        self.montage_timer = 0.0
        self.revealed_panels = 0  # 0 to 5

        # Screen shake & visual FX state
        self.shake_duration = 0.0
        self.shake_intensity = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0
        self.flash_alpha = 0.0
        # Panel 4 emergency police beacon flash (brief 0.3s on pop-in)
        self.emergency_flash_timer = 0.0

        # Load Scene 3 Textures
        scene3_path = SCENE_3_DIR
        self.bg_tex = arcade.load_texture(str(scene3_path / "scene3_bg.png"))
        self.panel_textures = [
            arcade.load_texture(str(scene3_path / "panel_1_layer.png")),
            arcade.load_texture(str(scene3_path / "panel_2_layer.png")),
            arcade.load_texture(str(scene3_path / "panel_3_layer.png")),
            arcade.load_texture(str(scene3_path / "panel_4_layer.png")),
            arcade.load_texture(str(scene3_path / "panel_5_layer.png")),
        ]

        # Localized Window Beacon Glow Textures (Strictly confined inside Panel 4 window)
        self.beacon_red_tex = arcade.load_texture(str(scene3_path / "beacon_red_glow.png"))
        self.beacon_blue_tex = arcade.load_texture(str(scene3_path / "beacon_blue_glow.png"))

        # Chef thinking portrait for dialogue
        self.chef_portrait = arcade.load_texture(str(SCENE_1_DIR / "Chief Thinking.png"))

        # Dialogue System
        self.dialogue = DialogueBox()
        self.dialogue_started = False
        self.montage_completed = False

        # Transition flag
        self.transitioning = False
        self.fade_alpha = 0.0

    def on_show_view(self):
        super().on_show_view()
        # Reset state upon entering view
        self.montage_timer = 0.0
        self.revealed_panels = 0
        self.dialogue_started = False
        self.montage_completed = False
        self.transitioning = False
        self.fade_alpha = 0.0
        self.emergency_flash_timer = 0.0

    def trigger_panel_reveal(self, panel_idx: int):
        """Trigger visual and audio shockwave when a panel pops in."""
        self.revealed_panels = panel_idx

        # Camera shockwave
        if panel_idx == 4:
            # Panel 4: Visceral freeze micro-shake + 0.3s brief emergency police flash
            self.shake_duration = 0.22
            self.shake_intensity = 8.5
            self.emergency_flash_timer = 0.30
            self.flash_alpha = 0.0
        else:
            self.shake_duration = 0.18
            self.shake_intensity = 7.0 if panel_idx in (1, 3, 5) else 5.0
            self.flash_alpha = 0.40 if panel_idx in (1, 3) else 0.25

        # Play customized SFX per panel
        if panel_idx == 1:
            self.audio.play("montage_impact", volume_scale=0.9)
        elif panel_idx == 2:
            self.audio.play("salt_pour", volume_scale=0.85)
            self.audio.play("chop", volume_scale=0.3)
        elif panel_idx == 3:
            self.audio.play("choking_heartbeat", volume_scale=1.0)
        elif panel_idx == 4:
            self.audio.play("ambulance_siren", volume_scale=0.85)
        elif panel_idx == 5:
            self.audio.play("camera_evidence", volume_scale=0.9)

    def _setup_incident_dialogue(self):
        """Construct S03 narrative sequence in authentic English."""
        script = [
            (
                "Incident Record · S03",
                "Morning prep rush. The outer warning label is torn away.",
                (235, 110, 95)
            ),
            (
                "Kitchen Staff",
                "The unlabelled powder is emptied into the kitchen seasoning container.",
                (220, 180, 130)
            ),
            (
                "Dining Hall",
                "The dish is served. Moments later, a guest collapses in sudden agony.",
                (245, 75, 65)
            ),
            (
                "Chef",
                "\"I labelled it... I told them not to touch it...\"",
                (225, 195, 145),
                self.chef_portrait,
                "left"
            ),
            (
                "Evidence & Closure",
                "Only a torn corner of the yellow warning label remains on the shelf.",
                (205, 190, 170)
            ),
        ]
        self.dialogue.start_dialogue(script, on_complete=self._on_dialogue_finished)

    def _on_dialogue_finished(self):
        self.montage_completed = True

    def on_update(self, dt: float):
        if self.is_paused:
            return

        self.t += dt

        # Camera Shake Decay
        if self.shake_duration > 0:
            self.shake_duration -= dt
            decay = max(0.0, self.shake_duration / 0.22)
            self.shake_offset_x = (random.random() * 2.0 - 1.0) * self.shake_intensity * decay
            self.shake_offset_y = (random.random() * 2.0 - 1.0) * self.shake_intensity * decay
        else:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0

        # Screen Flash Decay (for white shock flashes)
        if self.flash_alpha > 0:
            self.flash_alpha = max(0.0, self.flash_alpha - dt * 3.5)

        # Panel 4: Emergency 0.3s brief police beacon flash decay
        if self.emergency_flash_timer > 0:
            self.emergency_flash_timer = max(0.0, self.emergency_flash_timer - dt)

        # Rhythmic Montage Reveal Schedule
        # 0.0s -> P1, 1.5s -> P2, 3.0s -> P3, 4.5s -> P4, 6.0s -> P5
        if not self.dialogue_started:
            self.montage_timer += dt
            interval = 1.5
            target_panel = min(5, int(self.montage_timer / interval) + 1)
            if target_panel > self.revealed_panels:
                self.trigger_panel_reveal(target_panel)

            # At 7.5s (1.5s after panel 5), start dialogue sequence
            if self.revealed_panels >= 5 and self.montage_timer >= 7.5:
                self.dialogue_started = True
                self._setup_incident_dialogue()

        # Update Dialogue
        if self.dialogue.active:
            self.dialogue.update(dt)

        # Scene Fade Out to Next Era
        if self.transitioning:
            self.fade_alpha = min(1.0, self.fade_alpha + dt * 2.0)
            if self.fade_alpha >= 1.0:
                self._switch_to_next_scene()

    def _switch_to_next_scene(self):
        """Transition into Scene 4: S04 The Investigation and the Loss."""
        from scenes.scene_4_view import Scene4View
        self.window.show_view(Scene4View())

    def on_draw(self):
        self.clear(color=(10, 28, 55))
        self.use_game_camera()

        # Apply screen shake to camera position
        if self.camera:
            self.camera.position = (
                SCREEN_WIDTH / 2 + self.shake_offset_x,
                SCREEN_HEIGHT / 2 + self.shake_offset_y
            )

        # 1. Base Dark Navy Canvas
        arcade.draw_texture_rect(
            self.bg_tex,
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        )

        # 2. Draw Revealed Panels (Comic cut-ins)
        for i in range(self.revealed_panels):
            panel_tex = self.panel_textures[i]
            arcade.draw_texture_rect(
                panel_tex,
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
            )

        # 3. Continuous Localized Ambulance Beacon Strobe (Inside Panel 4 window only)
        if self.revealed_panels >= 4:
            beacon_cycle = (self.t * 3.6) % 2.0  # 0.0 to 2.0
            if beacon_cycle < 1.0:
                pulse = math.sin(beacon_cycle * math.pi)
                red_alpha = max(0.0, pulse) * 0.95
                blue_alpha = 0.0
            else:
                pulse = math.sin((beacon_cycle - 1.0) * math.pi)
                blue_alpha = max(0.0, pulse) * 0.95
                red_alpha = 0.0

            if red_alpha > 0.05:
                arcade.draw_texture_rect(
                    self.beacon_red_tex,
                    arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                    alpha=int(red_alpha * 255)
                )
            if blue_alpha > 0.05:
                arcade.draw_texture_rect(
                    self.beacon_blue_tex,
                    arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                    alpha=int(blue_alpha * 255)
                )

        # 4. Panel 4 Cut-in: Brief 0.3s Fullscreen Police Beacon Flash (Red-Blue dual pulse)
        # Immediately settles into crystal-clear static artwork after 0.3s
        if self.emergency_flash_timer > 0.0:
            p = self.emergency_flash_timer / 0.30  # 1.0 down to 0.0
            if p > 0.5:
                # First 0.15s: Intense emergency red pulse
                red_p = (p - 0.5) / 0.5
                intensity = int(120 * math.sin(red_p * math.pi * 0.5))
                arcade.draw_rect_filled(
                    arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                    (255, 30, 40, intensity)
                )
            else:
                # Second 0.15s: Intense emergency blue pulse
                blue_p = p / 0.5
                intensity = int(120 * math.sin(blue_p * math.pi * 0.5))
                arcade.draw_rect_filled(
                    arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                    (30, 100, 255, intensity)
                )

        # 4. Cinematic White Shock Flash Overlay (for other panels)
        if self.flash_alpha > 0.01:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (255, 255, 255, int(self.flash_alpha * 255))
            )

        # 6. Dialogue Box Rendering
        if self.dialogue.active:
            self.dialogue.draw(self.aspect_ratio_correction)

        # 7. Post-Dialogue Next Scene Prompt
        if self.montage_completed and not self.transitioning:
            pulse = math.sin(self.t * 3.5) * 0.3 + 0.7
            box_w = 540
            box_h = 44
            box_y = 65
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, box_y, box_w, box_h),
                (14, 18, 28, int(220 * pulse))
            )
            arcade.draw_rect_outline(
                arcade.XYWH(SCREEN_WIDTH / 2, box_y, box_w, box_h),
                (COLOR_GOLD[0], COLOR_GOLD[1], COLOR_GOLD[2], int(255 * pulse)),
                1.5
            )
            arcade.draw_text(
                "▶  [ CLICK or press SPACE to enter Chapter One ]",
                SCREEN_WIDTH / 2,
                box_y - 6,
                (255, 240, 210, int(255 * pulse)),
                13,
                anchor_x="center",
                bold=True
            )

        # 8. Fade-to-black transition overlay
        if self.fade_alpha > 0.01:
            arcade.draw_rect_filled(
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
                (0, 0, 0, int(self.fade_alpha * 255))
            )

        # 9. Pause Overlay (BaseGameView)
        self.draw_pause_overlay()

    def on_key_press(self, key: int, modifiers: int):
        if self.handle_pause_key(key):
            return

        if key == arcade.key.F11:
            self.toggle_fullscreen()
            return

        # Advance montage panels or skip to dialogue
        if not self.dialogue_started:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                if self.revealed_panels < 5:
                    self.trigger_panel_reveal(self.revealed_panels + 1)
                    self.montage_timer = self.revealed_panels * 1.5
                else:
                    self.dialogue_started = True
                    self._setup_incident_dialogue()
                return

        # Advance dialogue
        if self.dialogue.active:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                self.dialogue.advance()
                return

        # Proceed to next scene after montage completes
        if self.montage_completed and not self.transitioning:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                self.transitioning = True
                self.audio.play("click", volume_scale=0.5)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        if self.handle_pause_mouse_press(x, y, button):
            return

        # Advance montage panels or skip to dialogue
        if not self.dialogue_started:
            if self.revealed_panels < 5:
                self.trigger_panel_reveal(self.revealed_panels + 1)
                self.montage_timer = self.revealed_panels * 1.5
            else:
                self.dialogue_started = True
                self._setup_incident_dialogue()
            return

        # Advance dialogue
        if self.dialogue.active:
            self.dialogue.advance()
            return

        # Proceed to next scene after montage completes
        if self.montage_completed and not self.transitioning:
            self.transitioning = True
            self.audio.play("click", volume_scale=0.5)

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        self.handle_pause_mouse_motion(x, y)


# Standalone runner for direct testing
if __name__ == "__main__":
    window = arcade.Window(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Scene 3: S03 The Incident · Act I Incident Montage",
        resizable=False,
        fullscreen=START_FULLSCREEN
    )
    if START_FULLSCREEN:
        window.set_fullscreen(True)
    view = Scene3View()
    window.show_view(view)
    arcade.run()
