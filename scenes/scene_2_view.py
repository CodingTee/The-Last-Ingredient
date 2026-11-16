"""Scene 2: S02 The Unverified Sample
Faithfully following the National Champion Script (Assignment Plot S02):
1. Next morning before service, warm daylight illuminates the kitchen.
2. The regular food ingredient supplier arrives carrying fresh produce and an unverified sample box.
3. Supplier presents the fresh food crate and introduces the mysterious flavour enhancer.
4. Chef scrutinizes the sample, strictly demanding an authorized laboratory inspection report.
5. Chef orders: "PENDING VERIFICATION — DO NOT USE IN PREPARATION!"
6. Interactive sealing: The player drags or clicks the caution tape to seal the sample box on the prep table.
7. Box texture immediately updates to show the sealed yellow warning tape!
8. Forensic inspection modal reveals the fatal oversight: outer carton is sealed, but inner foil sachet has NO warning markings.
9. Phone rings, chef puts the tagged box onto the side prep shelf before taking the call.
"""
import math
import random
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import arcade
from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_GOLD,
    SCENE_1_DIR, SCENE_2_DIR, START_FULLSCREEN
)
from core.dialogue import DialogueBox
from core.audio import AudioManager
from core.base_view import BaseGameView

# Story Phases
PHASE_S02_DELIVERY = 0       # Morning arrival, fresh produce check & dialogue
PHASE_S02_ATTACH_LABEL = 1   # Interactive: Player drags or clicks caution tape to seal the box!
PHASE_S02_INSPECT_MODAL = 2  # Close-up inspection modal showing the newly sealed box & fatal inner flaw
PHASE_S02_PHONE_CALL = 3     # Phone rings, Chef moves box to prep shelf
PHASE_S02_AFTERMATH = 4      # Recap & transition to Scene 3


class SealParticle:
    """Sparkling golden/amber particles that burst when the caution tape is affixed."""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(80, 260)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.radius = random.uniform(3.0, 6.0)
        self.color = random.choice([
            (255, 220, 40),
            (255, 180, 30),
            (255, 255, 210),
            (240, 120, 30),
        ])
        self.life = 0.8
        self.max_life = 0.8

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def draw(self):
        if self.life > 0:
            alpha = int(255 * (self.life / self.max_life))
            arcade.draw_circle_filled(self.x, self.y, self.radius, (*self.color, alpha))


class Scene2View(BaseGameView):
    """Scene 2 View: The Unverified Sample delivery in the daytime kitchen."""

    def __init__(self):
        super().__init__()
        self.audio = AudioManager()
        self.t = 0.0
        self.phase = PHASE_S02_DELIVERY

        # ---- Load Scene 2 High-Res Textures (Adaptive 16:9 cropped & 16:10 native)
        bg_16_10_path = SCENE_2_DIR / "scene_02_daytime_kitchen_16_10.png"
        if not bg_16_10_path.exists():
            bg_16_10_path = SCENE_2_DIR / "scene_02_daytime_kitchen_16_10.png"
        bg_16_9_path = SCENE_2_DIR / "scene_02_daytime_kitchen_1280x720.png"

        self.bg_kitchen_16_9 = arcade.load_texture(str(bg_16_9_path))
        self.bg_kitchen_16_10 = arcade.load_texture(str(bg_16_10_path)) if bg_16_10_path.exists() else self.bg_kitchen_16_9
        self.table_foreground = arcade.load_texture(str(SCENE_2_DIR / "Table_Foreground.png"))
        self.trash_can_foreground = arcade.load_texture(str(SCENE_2_DIR / "Trash_Can_Foreground.png"))

        # Protagonist poses
        self.chef_normal = arcade.load_texture(str(SCENE_1_DIR / "Modern Chief.png"))
        self.chef_thinking = arcade.load_texture(str(SCENE_1_DIR / "Chief Thinking.png"))

        # Supplier (Mirrored as requested)
        flipped_path = SCENE_2_DIR / "Supplier_Flipped.png"
        if not flipped_path.exists():
            flipped_path = SCENE_1_DIR / "Supplier_Flipped.png"
        self.supplier_tex = arcade.load_texture(str(flipped_path))

        # Table Food Props
        front_crate_path = SCENE_2_DIR / "Food_Crate_Front.png"
        if not front_crate_path.exists():
            front_crate_path = SCENE_1_DIR / "Food_Crate_Front.png"
        self.crate_tex = arcade.load_texture(str(front_crate_path))

        # 1. Unsealed initial sample box
        sample_path = SCENE_2_DIR / "Sample_Box_Front.png"
        if not sample_path.exists():
            sample_path = SCENE_1_DIR / "Sample_Box_Front.png"
        self.sample_box_unsealed_tex = arcade.load_texture(str(sample_path))

        # 2. Sealed sample box (with yellow caution tape affixed across it)
        labelled_path = SCENE_2_DIR / "Sample_Box_Labelled.png"
        if not labelled_path.exists():
            labelled_path = SCENE_1_DIR / "Sample_Box_Labelled.png"
        self.sample_box_labelled_tex = arcade.load_texture(str(labelled_path))

        # 3. Interactive caution tape tool
        tape_path = SCENE_2_DIR / "caution_tape.png"
        if not tape_path.exists():
            tape_path = SCENE_1_DIR / "caution_tape.png"
        self.caution_tape_tex = arcade.load_texture(str(tape_path))

        # 4. Cinematic Phone Shelf CG (16:10 native and 16:9 vertical cropped per GEMINI.md)
        cg_16_10_path = SCENE_2_DIR / "scene_02_phone_shelf_cg_16_10.png"
        cg_16_9_path = SCENE_2_DIR / "scene_02_phone_shelf_cg_16_9.png"
        self.phone_shelf_cg_16_9 = arcade.load_texture(str(cg_16_9_path))
        self.phone_shelf_cg_16_10 = arcade.load_texture(str(cg_16_10_path)) if cg_16_10_path.exists() else self.phone_shelf_cg_16_9

        # Interactive sealing states (Strict Drag & Drop)
        self.is_box_sealed = False
        self.is_dragging_tape = False
        self.drag_offset_x = 0.0
        self.drag_offset_y = 0.0
        self.is_returning_tape = False
        self.snap_fail_timer = 0.0
        self.tape_base_pos = [SCREEN_WIDTH / 2, 95.0]
        self.tape_pos = list(self.tape_base_pos)
        self.tape_hovered = False
        self.particles: list[SealParticle] = []
        self.seal_success_timer = 0.0

        # Box position & shelf sliding
        y_table_base = 292
        box_h = 121
        self.box_cx = 847.0
        self.box_cy = float(y_table_base + box_h / 2)
        self.box_target_cx = 847.0
        self.box_target_cy = float(y_table_base + box_h / 2)
        self.shelf_moved = False

        # Close-up inspection overlay state
        self.inspect_modal_open = False
        self.pulse_timer = 0.0

        # Dialogue System
        self.dialogue = DialogueBox()
        self._setup_delivery_script()

    @property
    def bg_kitchen(self) -> arcade.Texture:
        """Adaptive texture for Scene 2 kitchen (16:10 native on 16:10 screens, 16:9 cropped on 16:9)."""
        return self.get_adaptive_texture(self.bg_kitchen_16_9, self.bg_kitchen_16_10)

    @property
    def phone_shelf_cg(self) -> arcade.Texture:
        """Adaptive texture for the phone shelf CG (16:10 native on 16:10 screens, 16:9 cropped on 16:9 per GEMINI.md)."""
        return self.get_adaptive_texture(self.phone_shelf_cg_16_9, self.phone_shelf_cg_16_10)

    # ---------------------------------------------------------------- Script Setups
    def _setup_delivery_script(self):
        """Construct S02 dialogue sequence in pure English."""
        self.phase = PHASE_S02_DELIVERY
        script = [
            (
                "Kitchen Before Service",
                "Morning before service. Fresh produce and an unverified sample arrive.",
                (215, 195, 160)
            ),
            (
                "Supplier",
                "\"Morning, Chef! Fresh produce delivery is here.\"",
                (235, 165, 90),
                self.supplier_tex,
                "right"
            ),
            (
                "Chef",
                "\"Thanks. What's inside that smaller carton?\"",
                (210, 175, 120),
                self.chef_normal,
                "left"
            ),
            (
                "Supplier",
                "\"A new seasoning sample. Supposed to intensify natural umami.\"",
                (235, 165, 90),
                self.supplier_tex,
                "right"
            ),
            (
                "Supplier",
                "\"The vendor claims it's revolutionary, but full paperwork is still pending.\"",
                (235, 165, 90),
                self.supplier_tex,
                "right"
            ),
            (
                "Chef",
                "\"Unverified ingredients don't touch my kitchen. Where is the lab report?\"",
                (220, 100, 90),
                self.chef_thinking,
                "left"
            ),
            (
                "Supplier",
                "\"Still waiting on the lab. Just hold onto it for now, Chef.\"",
                (235, 165, 90),
                self.supplier_tex,
                "right"
            ),
            (
                "Chef",
                "\"Mark it with caution tape: DO NOT USE IN PREPARATION.\"",
                (210, 175, 120),
                self.chef_thinking,
                "left"
            ),
        ]
        self.dialogue.start_dialogue(script, on_complete=self._on_dialogue_finished)

    def _on_dialogue_finished(self):
        """Called when main dialogue finishes: prompt player to attach the caution label!"""
        self.phase = PHASE_S02_ATTACH_LABEL
        self.audio.play("paper_slide", volume_scale=0.6)

    # ---------------------------------------------------------------- Update Loop
    def on_update(self, dt):
        if self.is_paused:
            return
        self.t += dt
        self.pulse_timer += dt
        self.dialogue.update(dt)

        # Update bursting particles
        for p in self.particles[:]:
            p.update(dt)
            if p.life <= 0:
                self.particles.remove(p)

        # Smoothly snap tape back to starting dock if released outside target zone
        if self.is_returning_tape:
            speed = min(1.0, dt * 14.0)
            self.tape_pos[0] += (self.tape_base_pos[0] - self.tape_pos[0]) * speed
            self.tape_pos[1] += (self.tape_base_pos[1] - self.tape_pos[1]) * speed
            if abs(self.tape_pos[0] - self.tape_base_pos[0]) < 2.0 and abs(self.tape_pos[1] - self.tape_base_pos[1]) < 2.0:
                self.tape_pos = list(self.tape_base_pos)
                self.is_returning_tape = False

        if self.snap_fail_timer > 0:
            self.snap_fail_timer -= dt

        # Handle seal success animation timer
        if self.seal_success_timer > 0:
            self.seal_success_timer -= dt
            if self.seal_success_timer <= 0:
                # Open inspection modal after sealing!
                self.inspect_modal_open = True
                self.audio.play("clue_match", volume_scale=0.7)

    def _is_tape_over_target(self) -> bool:
        """Strict hit check: Tape center must be dragged inside the designated box target area."""
        # Box center: (self.box_cx, self.box_cy), box_w = 180, box_h = 121
        hw = 90.0
        hh = 65.0
        return (abs(self.tape_pos[0] - self.box_cx) <= hw and abs(self.tape_pos[1] - self.box_cy) <= hh)

    # ---------------------------------------------------------------- Draw Loop
    def on_draw(self):
        self.clear(color=(16, 14, 18))
        self.use_game_camera()

        corr = self.aspect_ratio_correction

        # If in Phone Call / Aftermath phase: Render the new Cinematic Phone Shelf Event CG!
        # (Follows GEMINI.md: 16:10 native on 16:10 displays, 16:9 vertical center-cropped on 16:9 displays)
        if self.phase in (PHASE_S02_PHONE_CALL, PHASE_S02_AFTERMATH):
            arcade.draw_texture_rect(
                self.phone_shelf_cg,
                arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
            )
            if self.dialogue.active:
                self.dialogue.draw(corr)
            self.draw_pause_overlay()
            return

        # 1. 16:9 Daytime Kitchen Background
        arcade.draw_texture_rect(
            self.bg_kitchen,
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        )

        # 2. Chef behind the island table (Natural hero proportion)
        current_chef_tex = self.chef_thinking if self.dialogue.current_idx >= 5 or self.is_box_sealed else self.chef_normal
        chef_cx = 580
        chef_cy = 398
        chef_w = 230 * corr
        chef_h = 345
        arcade.draw_texture_rect(current_chef_tex, arcade.XYWH(chef_cx, chef_cy, chef_w, chef_h))

        # 3. Table Foreground (covers chef's lower body)
        arcade.draw_texture_rect(
            self.table_foreground,
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        )

        # Table surface base plane in 720p
        y_table_base = 292

        # 4. Front-facing Fresh Food Crate (Oriented towards opposite side / chef, grounded on table)
        crate_cx = 382
        crate_w = 187 * corr
        crate_h = 159
        crate_cy = y_table_base + crate_h / 2

        # Realistic Table Contact Shadow & Metallic Reflection for Crate
        arcade.draw_line(crate_cx - crate_w * 0.44, y_table_base, crate_cx + crate_w * 0.44, y_table_base, (8, 6, 12, 240), 3.0)
        arcade.draw_ellipse_filled(crate_cx, y_table_base - 1, crate_w * 0.92, 10, (10, 8, 14, 150))
        arcade.draw_ellipse_filled(crate_cx, y_table_base - 1, crate_w * 1.05, 18, (12, 10, 16, 70))
        arcade.draw_texture_rect(self.crate_tex, arcade.XYWH(crate_cx, crate_cy, crate_w, crate_h))

        # 5. Seasoning Sample Box (Switches to Labelled Box once sealed!)
        box_w = 180 * corr
        box_h = 121
        current_box_tex = self.sample_box_labelled_tex if self.is_box_sealed else self.sample_box_unsealed_tex

        # Realistic Table Contact Shadow for Sample Box
        box_base_y = self.box_cy - box_h / 2
        arcade.draw_line(self.box_cx - box_w * 0.44, box_base_y, self.box_cx + box_w * 0.44, box_base_y, (8, 6, 12, 240), 3.0)
        arcade.draw_ellipse_filled(self.box_cx, box_base_y - 1, box_w * 0.92, 10, (10, 8, 14, 150))
        arcade.draw_ellipse_filled(self.box_cx, box_base_y - 1, box_w * 1.05, 18, (12, 10, 16, 70))
        arcade.draw_texture_rect(current_box_tex, arcade.XYWH(self.box_cx, self.box_cy, box_w, box_h))

        # Interactive Target Area around box during ATTACH_LABEL phase
        if self.phase == PHASE_S02_ATTACH_LABEL and not self.is_box_sealed:
            pulse = math.sin(self.pulse_timer * 5.0) * 0.5 + 0.5
            ring_alpha = int(160 + 95 * pulse)
            is_over = self._is_tape_over_target()

            if is_over:
                target_color = (80, 255, 120, 250)
                tip_text = "✓  RELEASE TO SEAL CARTON  ✓"
                badge_bg = (18, 45, 24, 240)
                badge_fg = (120, 255, 160)
            elif self.is_dragging_tape:
                target_color = (255, 215, 80, ring_alpha)
                tip_text = "▼  DRAG TAPE INTO THIS TARGET  ▼"
                badge_bg = (35, 26, 14, 235)
                badge_fg = (255, 235, 140)
            else:
                target_color = (220, 180, 70, 150)
                tip_text = "[ DESIGNATED SEAL TARGET ]"
                badge_bg = (20, 16, 24, 220)
                badge_fg = (220, 200, 150)

            # Designated target box
            arcade.draw_rect_outline(
                arcade.XYWH(self.box_cx, self.box_cy, box_w + 16, box_h + 16),
                target_color,
                3.5 if is_over else 2.5
            )
            # Target instruction indicator above box
            tip_y = self.box_cy + box_h / 2 + 22
            arcade.draw_rect_filled(arcade.XYWH(self.box_cx, tip_y, 250 * corr, 26), badge_bg)
            arcade.draw_rect_outline(arcade.XYWH(self.box_cx, tip_y, 250 * corr, 26), target_color, 1.5)
            arcade.draw_text(tip_text, self.box_cx, tip_y - 5,
                             badge_fg, 10.5, anchor_x="center", bold=True)

            # Warning alert if user released outside the designated area
            if self.snap_fail_timer > 0:
                alert_y = self.box_cy - box_h / 2 - 20
                arcade.draw_rect_filled(arcade.XYWH(self.box_cx, alert_y, 310 * corr, 24), (45, 16, 18, 235))
                arcade.draw_rect_outline(arcade.XYWH(self.box_cx, alert_y, 310 * corr, 24), (255, 75, 70), 1.5)
                arcade.draw_text("⚠  MISSED TARGET! DRAG DIRECTLY ONTO CARTON  ⚠",
                                 self.box_cx, alert_y - 5, (255, 130, 120), 9.5, anchor_x="center", bold=True)

        # 6. Supplier standing on right aisle (facing Chef)
        supp_cx = 1130
        supp_cy = 320
        supp_w = 370 * corr
        supp_h = 500
        # Soft shadow on floor
        arcade.draw_ellipse_filled(supp_cx, supp_cy - supp_h / 2 + 12, supp_w * 0.7, 18, (12, 12, 18, 150))
        arcade.draw_texture_rect(self.supplier_tex, arcade.XYWH(supp_cx, supp_cy, supp_w, supp_h))

        # 7. Stainless Steel Trash Can Foreground (LAYERED OVER SUPPLIER'S FEET)
        arcade.draw_texture_rect(
            self.trash_can_foreground,
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        )

        # 8. Draw Sparkling Seal Particles
        for p in self.particles:
            p.draw()

        # 9. Draw Interactive Caution Tape Widget (When in ATTACH_LABEL phase)
        if self.phase == PHASE_S02_ATTACH_LABEL and not self.is_box_sealed:
            self._draw_caution_tape_interaction(corr)

        # 10. Visual Seal Success Banner
        if self.seal_success_timer > 0:
            badge_y = self.box_cy + box_h / 2 + 34
            arcade.draw_rect_filled(arcade.XYWH(self.box_cx, badge_y, 280 * corr, 32), (18, 38, 22, 240))
            arcade.draw_rect_outline(arcade.XYWH(self.box_cx, badge_y, 280 * corr, 32), (80, 245, 120), 2.0)
            arcade.draw_text("✓  WARNING LABEL AFFIXED & SEALED!", self.box_cx, badge_y - 6,
                             (120, 255, 160), 11, anchor_x="center", bold=True)

        # 11. Cinematic Dialogue Box (During dialogue phase)
        if self.dialogue.active:
            self.dialogue.draw(corr)

        # 12. Close-up Sample Inspection Modal (When player inspects the sample)
        if self.inspect_modal_open:
            self._draw_sample_inspection_modal(corr)

        # 13. Pause / ESC Menu
        self.draw_pause_overlay()

    def _draw_caution_tape_interaction(self, corr: float):
        """Draw interactive caution tape widget that the player must strictly drag onto the carton."""
        # Top banner instruction
        top_y = SCREEN_HEIGHT - 45
        arcade.draw_rect_filled(arcade.XYWH(SCREEN_WIDTH / 2, top_y, 680 * corr, 36), (18, 16, 24, 235))
        arcade.draw_rect_outline(arcade.XYWH(SCREEN_WIDTH / 2, top_y, 680 * corr, 36), (255, 215, 80), 2.0)
        arcade.draw_text("[ DRAG TAPE ONTO BOX · OR PRESS E / SPACE / CLICK TO SEAL ]",
                         SCREEN_WIDTH / 2, top_y - 6, (255, 225, 120), 11.5, anchor_x="center", bold=True)

        # Draw Tape Widget
        tx, ty = self.tape_pos
        tw, th = 280 * corr, 56

        # Draw glowing outline if hovered or dragging
        pulse = math.sin(self.pulse_timer * 6.0) * 0.5 + 0.5
        outline_alpha = int(190 + 65 * pulse) if self.tape_hovered or self.is_dragging_tape else 140

        # Backplate drop shadow
        arcade.draw_ellipse_filled(tx, ty - th / 2 + 4, tw * 0.9, 14, (10, 8, 12, 160))

        # Caution Tape texture
        border_col = (80, 255, 120, outline_alpha) if self._is_tape_over_target() else (255, 215, 80, outline_alpha)
        arcade.draw_rect_filled(arcade.XYWH(tx, ty, tw + 8, th + 8), (30, 24, 15, 220))
        arcade.draw_rect_outline(arcade.XYWH(tx, ty, tw + 8, th + 8), border_col, 2.5)
        arcade.draw_texture_rect(self.caution_tape_tex, arcade.XYWH(tx, ty, tw, th))

        # Bottom hint if not dragging
        if not self.is_dragging_tape and not self.is_returning_tape:
            arcade.draw_text("◀  HOLD & DRAG TO CARTON  ▶", tx, ty - th / 2 - 16,
                             (255, 215, 80), 10, anchor_x="center", bold=True)

    def _draw_sample_inspection_modal(self, corr: float):
        """Draw close-up forensic inspection of the newly sealed sample box (Pure English)."""
        # Backdrop
        arcade.draw_rect_filled(
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
            (10, 8, 14, 215)
        )

        cx = SCREEN_WIDTH / 2
        cy = SCREEN_HEIGHT / 2
        mw = 760 * corr
        mh = 510

        # Modal Frame
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, mw, mh), (22, 20, 28, 250))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, mw + 4, mh + 4), (255, 205, 75), 2.5)

        # Header Title (English Only)
        arcade.draw_text("EVIDENCE INSPECTION", cx, cy + mh / 2 - 38,
                         COLOR_GOLD, 18, anchor_x="center", bold=True)
        arcade.draw_line(cx - 320 * corr, cy + mh / 2 - 50, cx + 320 * corr, cy + mh / 2 - 50,
                         (180, 140, 65, 180), 1.5)

        # Draw enlarged Sealed Sample Box on the left (showing the caution tape just affixed!)
        box_preview_w = 280 * corr
        box_preview_h = int(280 * 660 / 978)
        box_px = cx - 180 * corr
        box_py = cy + 10
        arcade.draw_texture_rect(self.sample_box_labelled_tex, arcade.XYWH(box_px, box_py, box_preview_w, box_preview_h))
        arcade.draw_rect_outline(arcade.XYWH(box_px, box_py, box_preview_w + 6, box_preview_h + 6),
                                (255, 215, 80, 160), 1.5)

        # Information Card on the right (English Only)
        tx = cx + 20 * corr
        ty = cy + 120
        arcade.draw_text("Item: Unverified Flavor Compound", tx, ty, (255, 235, 185), 14, bold=True)
        arcade.draw_text("Source: Illicit Research Sample (Disguised)", tx, ty - 26, (255, 140, 130), 11, bold=True)
        arcade.draw_text("Status: Sealed [PENDING VERIFICATION]", tx, ty - 50, (100, 245, 140), 11, bold=True)

        # Foreshadowing Hazard Card (Spacious, well-padded, completely enclosed)
        card_cx = tx + 170 * corr
        card_cy = ty - 142
        card_w = 345 * corr
        card_h = 160
        arcade.draw_rect_filled(arcade.XYWH(card_cx, card_cy, card_w, card_h), (42, 18, 22, 245))
        arcade.draw_rect_outline(arcade.XYWH(card_cx, card_cy, card_w, card_h), (255, 80, 70), 1.8)

        # Header inside card
        card_top = card_cy + card_h / 2
        arcade.draw_text("CRITICAL FORESHADOWING", card_cx - card_w / 2 + 16, card_top - 22,
                         (255, 95, 85), 11, bold=True)
        arcade.draw_text("STORAGE & PACKAGING HAZARD", card_cx - card_w / 2 + 16, card_top - 38,
                         (255, 175, 160), 9, bold=True)
        arcade.draw_line(card_cx - card_w / 2 + 16, card_top - 46, card_cx + card_w / 2 - 16, card_top - 46,
                         (180, 60, 60, 180), 1.0)

        bullets = [
            "• Warning label was AFFIXED ONLY to outer carton.",
            "• Inner foil sachet is labelled only as seasoning, with",
            "  NO hazardous material warnings or caution notes.",
            "• Once outer box is discarded, the unmarked sachet",
            "  is easily mistaken for regular kitchen stock!"
        ]
        text_y = card_top - 62
        for b in bullets:
            arcade.draw_text(b, card_cx - card_w / 2 + 16, text_y, (255, 225, 220), 9.5)
            text_y -= 18

        # Close prompt
        arcade.draw_text("[ PRESS  SPACE  /  ENTER  OR  CLICK  TO  CONTINUE ]",
                         cx, cy - mh / 2 + 30, (255, 215, 80), 13, anchor_x="center", bold=True)

    # ---------------------------------------------------------------- Input Handling
    def on_key_press(self, key, modifiers):
        if self.handle_pause_key(key):
            return

        if key == arcade.key.F11:
            self.toggle_fullscreen()
            return

        # Close inspection modal
        if self.inspect_modal_open:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.ESCAPE, arcade.key.E):
                self.inspect_modal_open = False
                self.audio.play("click", volume_scale=0.4)
                self._trigger_phone_call_event()
            return

        # In sealing phase: SPACE / ENTER / E affixes caution seal!
        if self.phase == PHASE_S02_ATTACH_LABEL and not self.is_box_sealed:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                self._apply_seal_to_box()
            return

        # Advance main dialogue
        if self.dialogue.active:
            if key in (arcade.key.SPACE, arcade.key.ENTER, arcade.key.E):
                self.dialogue.advance()
                return

    def on_mouse_motion(self, x, y, dx, dy):
        if self.handle_pause_mouse_motion(x, y):
            return
        vx, vy = self.to_virtual_coords(x, y)

        # Check hover on caution tape
        tx, ty = self.tape_pos
        self.tape_hovered = (abs(vx - tx) <= 150 and abs(vy - ty) <= 35)

        # Update dragged tape position
        if self.is_dragging_tape:
            self.tape_pos = [vx - self.drag_offset_x, vy - self.drag_offset_y]

    def on_mouse_press(self, x, y, button, modifiers):
        if self.handle_pause_mouse_press(x, y, button):
            return

        # Close inspection modal
        if self.inspect_modal_open:
            self.inspect_modal_open = False
            self.audio.play("click", volume_scale=0.4)
            self._trigger_phone_call_event()
            return

        # Interactive sealing phase
        if self.phase == PHASE_S02_ATTACH_LABEL and not self.is_box_sealed:
            vx, vy = self.to_virtual_coords(x, y)
            tx, ty = self.tape_pos
            # Click & hold on tape to drag
            if abs(vx - tx) <= 150 and abs(vy - ty) <= 35:
                self.is_dragging_tape = True
                self.is_returning_tape = False
                self.drag_offset_x = vx - tx
                self.drag_offset_y = vy - ty
                self.audio.play("paper_slide", volume_scale=0.5)
                return
            # Click directly on carton box target area or click anywhere to seal
            self._apply_seal_to_box()
            return

        # Click to advance dialogue
        if self.dialogue.active:
            self.dialogue.advance()

    def on_mouse_release(self, x, y, button, modifiers):
        if self.is_dragging_tape:
            self.is_dragging_tape = False
            # STRICT CHECK: Tape must be dragged into designated target area over the carton!
            if self._is_tape_over_target():
                self._apply_seal_to_box()
            else:
                # Did not drop into target -> snap smoothly back to original position!
                self.is_returning_tape = True
                self.snap_fail_timer = 2.0
                self.audio.play("paper_slide", volume_scale=0.5)

    def _apply_seal_to_box(self):
        """Firmly seal the sample box with yellow caution tape, with audio & particle feedback!"""
        if self.is_box_sealed:
            return
        self.is_box_sealed = True
        self.is_dragging_tape = False

        # Audio feedback: satisfying heavy stamp & discovery chime
        self.audio.play("stamp_seal", volume_scale=0.95)
        self.audio.play("clue_match", volume_scale=0.7)

        # Spawn sparkling particles around the sealed box
        for _ in range(35):
            self.particles.append(SealParticle(self.box_cx, self.box_cy))

        # Set timer for brief celebration before opening inspection modal
        self.seal_success_timer = 0.9

    def _trigger_phone_call_event(self):
        """After inspecting the fatal inner flaw, phone rings and cuts to the dramatic Phone Shelf Event CG."""
        self.phase = PHASE_S02_PHONE_CALL
        # Telephone ring chime
        self.audio.play("clock_chime", volume_scale=0.85)

        script = [
            (
                "Chef",
                "\"Reservations desk, head chef speaking... Table for six? Hold on, let me note down your details...\"",
                (210, 175, 120),
                self.chef_thinking,
                "left"
            ),
            (
                "Preparation Shelf",
                "In the morning rush, the sealed carton remained on the active prep shelf.",
                (235, 100, 90)
            )
        ]
        self.dialogue.start_dialogue(script, on_complete=self._transition_to_scene_3)

    def _transition_to_scene_3(self):
        from scenes.scene_3_view import Scene3View
        self.window.show_view(Scene3View())


# Standalone runner
if __name__ == "__main__":
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, "The Last Ingredient - Scene 2: S02 The Unverified Sample", resizable=False, fullscreen=START_FULLSCREEN)
    if START_FULLSCREEN:
        window.set_fullscreen(True)
    view = Scene2View()
    window.show_view(view)
    arcade.run()
