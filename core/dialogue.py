"""Cinematic dialogue and narrative presentation system for The Last Ingredient (Option A Unified).
Features:
- Dual-Mode Architecture:
  1. Character Dialogue Mode: Floating glassmorphic panel with character avatar portrait
     (Protagonist on the left, Interlocutor on the right) and themed nameplate badge.
  2. Cinematic Letterbox Mode (Scene 19 Style): Full-width bottom letterbox bar with centered
     gold narration tag, centered high-contrast subtitle text, and subtle breathing continue prompt.
- Automatic Avatar Resolution: If no explicit portrait is supplied for a character line,
  DialogueBox automatically resolves and renders the appropriate era/character portrait bust!
- Pre-computed natural word-wrapping with orphan/widow word balancing (zero mid-word line-jumps).
- Sub-pixel free, ultra-crisp typography with Segoe UI font stack & drop-shadow contrast.
"""
from __future__ import annotations
import math
from pathlib import Path
import arcade
from core.audio import AudioManager
from core.constants import ASSETS_DIR, COLOR_TEXT_WHITE

DIALOG_W = 1120
DIALOG_H = 152
DIALOG_X = 640
DIALOG_Y = 110

FONT_FAMILY = ("Segoe UI", "Calibri", "Helvetica Neue", "Arial")
FONT_SIZE_BODY = 16
FONT_SIZE_SPEAKER = 13
FONT_SIZE_PROMPT = 12
FONT_SIZE_CINEMATIC = 17


class AvatarRegistry:
    """Lazy cache for high-resolution character avatar textures across all eras."""
    _cache: dict[str, arcade.Texture | None] = {}

    @classmethod
    def get(cls, speaker: str, side: str = "left", era_hint: str = "") -> arcade.Texture | None:
        key = (speaker.lower().strip(), side, era_hint)
        if key in cls._cache:
            return cls._cache[key]

        sp = speaker.lower().strip()
        tex = None
        try:
            if any(k in sp for k in ("investigator", "detective", "interrogator")):
                # Check for investigator texture or use sleek authority silhouette
                path = ASSETS_DIR / "Scene 4" / "Investigator.png"
                if not path.exists():
                    path = ASSETS_DIR / "characters" / "modern" / "char_down_idle.png"
                if path.exists():
                    tex = arcade.load_texture(path)
            elif any(k in sp for k in ("colleague", "apprentice")):
                path = ASSETS_DIR / "Scene 1" / "Apprentice_Dialogue_Full.png"
                if not path.exists():
                    path = ASSETS_DIR / "Scene 1" / "Chief_Apprentice_Worry_Clean.png"
                if path.exists():
                    tex = arcade.load_texture(path)
            elif "supplier" in sp:
                path = ASSETS_DIR / "Scene 2" / "Supplier_Flipped.png"
                if not path.exists():
                    path = ASSETS_DIR / "Scene 1" / "Supplier_Flipped.png"
                if path.exists():
                    tex = arcade.load_texture(path)
            elif any(k in sp for k in ("girl", "princess", "your highness")):
                path = ASSETS_DIR / "princess_v2" / "princess_standing_ring_trimmed.png"
                if not path.exists():
                    path = ASSETS_DIR / "characters" / "_source_concept_art" / "girl_middle_ages.png"
                if path.exists():
                    tex = arcade.load_texture(path)
            elif any(k in sp for k in ("hunter", "savage")):
                path = ASSETS_DIR / "characters" / "savage" / "char_down_idle.png"
                if path.exists():
                    tex = arcade.load_texture(path)
            elif any(k in sp for k in ("tribe", "guard", "elder", "villager")):
                path = ASSETS_DIR / "characters" / "tribe_guard_a" / "char_down_idle.png"
                if not path.exists():
                    path = ASSETS_DIR / "characters" / "tribe_a" / "char_down_idle.png"
                if path.exists():
                    tex = arcade.load_texture(path)
            elif any(k in sp for k in ("astronaut", "researcher", "scientist")):
                path = ASSETS_DIR / "characters" / "astronaut" / "char_down_idle.png"
                if path.exists():
                    tex = arcade.load_texture(path)
            elif any(k in sp for k in ("wife", "family", "mother", "homeowner")):
                path = ASSETS_DIR / "endings" / "happy_ending" / "wife_kitchen_wide.png"
                if not path.exists():
                    path = ASSETS_DIR / "characters" / "_source_concept_art" / "girl_middle_ages.png"
                if path.exists():
                    tex = arcade.load_texture(path)
            elif any(k in sp for k in ("chef", "cook", "me")):
                if "royal" in era_hint or "1910" in era_hint:
                    path = ASSETS_DIR / "characters" / "chef" / "char_down_idle.png"
                elif "ancient" in era_hint or "prehistoric" in era_hint:
                    path = ASSETS_DIR / "characters" / "savage" / "char_down_idle.png"
                elif "future" in era_hint:
                    path = ASSETS_DIR / "characters" / "astronaut" / "char_down_idle.png"
                else:
                    path = ASSETS_DIR / "Scene 1" / "Modern Chief.png"
                if path.exists():
                    tex = arcade.load_texture(path)
        except Exception:
            tex = None

        cls._cache[key] = tex
        return tex


def get_current_viewport_rect():
    """Retrieve current camera visible world bounds (left, right, bottom, top)."""
    win = arcade.get_window()
    if not win:
        return 0.0, 1280.0, 0.0, 720.0
    try:
        cam = getattr(win, "current_camera", None)
        if cam:
            if hasattr(cam, "position") and hasattr(cam, "projection"):
                pos = cam.position
                px = getattr(pos, "x", pos[0] if isinstance(pos, (tuple, list)) else 0.0)
                py = getattr(pos, "y", pos[1] if isinstance(pos, (tuple, list)) else 0.0)
                p = cam.projection
                return float(px + p.left), float(px + p.right), float(py + p.bottom), float(py + p.top)
            if hasattr(cam, "viewport"):
                v = cam.viewport
                return float(v.left), float(v.right), float(v.bottom), float(v.top)
    except Exception:
        pass
    return 0.0, float(getattr(win, "width", 1280.0)), 0.0, float(getattr(win, "height", 720.0))


CHARACTER_KEYWORDS = (
    "chef", "cook", "protagonist",
    "colleague", "apprentice",
    "supplier",
    "investigator", "detective", "interrogator",
    "girl", "princess", "your highness",
    "hunter", "savage", "guard", "elder", "villager", "tribe",
    "astronaut", "scientist", "researcher",
    "wife", "mother", "family"
)


def is_narration_speaker(speaker: str) -> bool:
    """Identify if a speaker name corresponds to narration, thought, system, or ambient."""
    if not speaker or not speaker.strip():
        return True
    sp = speaker.strip().lower()
    if any(n in sp for n in ("narrat", "memory", "sound", "inner voice", "thought", "system", "notice", "tutorial", "clue", "scene")):
        return True
    return not any(c in sp for c in CHARACTER_KEYWORDS)


class DialogueBox:
    def __init__(self, era_hint: str = ""):
        self.lines = []
        self._wrapped_lines = []
        self.current_idx = 0
        self.active = False
        self.text_progress = 0
        self.type_speed = 52.0  # chars per second
        self.type_timer = 0.0
        self.on_complete = None
        self.audio = AudioManager()
        self.blink_timer = 0.0
        self.era_hint = era_hint

        # Cached text objects for character mode
        self._body_text_obj = None
        self._shadow_text_obj = None
        self._speaker_text_obj = None
        self._prompt_text_obj = None
        self._measure_text_obj = None

        # Cached text objects for cinematic narration mode (Scene 19 style)
        self._cine_tag_obj = None
        self._cine_body_obj = None
        self._cine_shadow_obj = None
        self._cine_prompt_obj = None

    def _ensure_text_objects(self):
        """Lazily initialize text rendering objects once OpenGL context is ready."""
        if self._body_text_obj is None:
            self._body_text_obj = arcade.Text(
                "", 0, 0,
                color=(COLOR_TEXT_WHITE[0], COLOR_TEXT_WHITE[1], COLOR_TEXT_WHITE[2], 255),
                font_name=FONT_FAMILY,
                font_size=FONT_SIZE_BODY,
                bold=True,
                multiline=True,
                width=DIALOG_W,
                anchor_x="left",
                anchor_y="top"
            )
            self._shadow_text_obj = arcade.Text(
                "", 0, 0,
                color=(0, 0, 0, 240),
                font_name=FONT_FAMILY,
                font_size=FONT_SIZE_BODY,
                bold=True,
                multiline=True,
                width=DIALOG_W,
                anchor_x="left",
                anchor_y="top"
            )
            self._speaker_text_obj = arcade.Text(
                "", 0, 0,
                color=(255, 255, 255, 255),
                font_name=FONT_FAMILY,
                font_size=FONT_SIZE_SPEAKER,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )
            self._prompt_text_obj = arcade.Text(
                "▶  [SPACE / CLICK to continue]", 0, 0,
                color=(240, 200, 110, 240),
                font_name=FONT_FAMILY,
                font_size=FONT_SIZE_PROMPT,
                bold=True,
                anchor_x="right",
                anchor_y="center"
            )
            self._measure_text_obj = arcade.Text(
                "", 0, 0,
                font_name=FONT_FAMILY,
                font_size=FONT_SIZE_BODY
            )

            # Cinematic subtitle objects (Scene 19 style)
            self._cine_tag_obj = arcade.Text(
                "", 0, 0,
                color=(235, 198, 110, 255),
                font_name=FONT_FAMILY,
                font_size=11.5,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )
            self._cine_body_obj = arcade.Text(
                "", 0, 0,
                color=(255, 248, 238, 255),
                font_name=FONT_FAMILY,
                font_size=FONT_SIZE_CINEMATIC,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )
            self._cine_shadow_obj = arcade.Text(
                "", 0, 0,
                color=(0, 0, 0, 240),
                font_name=FONT_FAMILY,
                font_size=FONT_SIZE_CINEMATIC,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )
            self._cine_prompt_obj = arcade.Text(
                "[ SPACE / ENTER / CLICK to continue ]", 0, 0,
                color=(200, 195, 185, 210),
                font_name=FONT_FAMILY,
                font_size=10.5,
                bold=True,
                anchor_x="center",
                anchor_y="center"
            )

    def _precompute_smart_wrap(self, text: str, max_width: float) -> str:
        """Pre-compute stable line breaks with orphan/widow word prevention."""
        self._ensure_text_objects()
        paragraphs = text.split("\n")
        all_wrapped_paragraphs = []

        for p in paragraphs:
            raw_words = p.split(" ")
            words = [w.strip() for w in raw_words if w.strip()]
            if not words:
                all_wrapped_paragraphs.append("")
                continue

            lines = []
            curr_line = []

            for word in words:
                test_line = " ".join(curr_line + [word])
                self._measure_text_obj.font_size = FONT_SIZE_BODY
                self._measure_text_obj.text = test_line
                if self._measure_text_obj.content_width <= max_width or not curr_line:
                    curr_line.append(word)
                else:
                    lines.append(" ".join(curr_line))
                    curr_line = [word]

            if curr_line:
                lines.append(" ".join(curr_line))

            if len(lines) > 1 and len(lines[-1].split(" ")) == 1:
                prev_words = lines[-2].split(" ")
                if len(prev_words) >= 3:
                    carried_word = prev_words.pop()
                    lines[-2] = " ".join(prev_words)
                    lines[-1] = carried_word + " " + lines[-1].strip()

            all_wrapped_paragraphs.append("\n".join(lines))

        return "\n".join(all_wrapped_paragraphs)

    @staticmethod
    def is_narration_speaker(speaker: str) -> bool:
        """Check if speaker should be rendered in Scene 19 style Cinematic Subtitle mode."""
        return is_narration_speaker(speaker)

    def start_dialogue(self, script_lines, on_complete=None):
        """script_lines: list of (speaker, text[, color[, portrait_texture[, side]]]) tuples."""
        self._ensure_text_objects()
        self.lines = list(script_lines)
        self._wrapped_lines = []

        for line in self.lines:
            speaker = line[0] if line and line[0] else ""
            raw_text = line[1]
            is_narrator = self.is_narration_speaker(speaker)

            # In narrator mode, use wider screen width; in character mode, leave room for portraits
            if is_narrator:
                max_w = 1140
            else:
                max_w = DIALOG_W - 150 - 72

            wrapped = self._precompute_smart_wrap(raw_text, max_w)
            self._wrapped_lines.append(wrapped)

        self.current_idx = 0
        self.active = True
        self.text_progress = 0
        self.type_timer = 0.0
        self.on_complete = on_complete
        self.audio.play("click", volume_scale=0.4)

    def advance(self):
        if not self.active or self.current_idx >= len(self._wrapped_lines):
            return

        current_text = self._wrapped_lines[self.current_idx]
        if self.text_progress < len(current_text):
            self.text_progress = len(current_text)
            self.audio.play("click", volume_scale=0.3)
        else:
            self.current_idx += 1
            if self.current_idx >= len(self.lines):
                self.active = False
                if self.on_complete:
                    callback = self.on_complete
                    self.on_complete = None
                    callback()
            else:
                self.text_progress = 0
                self.type_timer = 0.0
                self.audio.play("click", volume_scale=0.3)

    def update(self, dt):
        if not self.active or self.current_idx >= len(self._wrapped_lines):
            return

        self.blink_timer += dt
        current_text = self._wrapped_lines[self.current_idx]
        if self.text_progress < len(current_text):
            self.type_timer += dt
            new_chars = int(self.type_timer * self.type_speed)
            if new_chars > self.text_progress:
                self.text_progress = min(len(current_text), new_chars)

    def draw(self, aspect_correction: float = 1.0):
        if not self.active or self.current_idx >= len(self._wrapped_lines):
            return

        self._ensure_text_objects()

        line = self.lines[self.current_idx]
        speaker = line[0] if line[0] else ""
        raw_color = line[2] if len(line) > 2 else (235, 198, 110)
        tag_color = raw_color if isinstance(raw_color, (tuple, list)) else (235, 198, 110)
        portrait = line[3] if len(line) > 3 else None

        # Determine side (protagonist left, interlocutors right)
        if len(line) > 4 and line[4] in ("left", "right"):
            side = line[4]
        else:
            sp_lower = speaker.lower()
            if any(s in sp_lower for s in ("colleague", "apprentice", "supplier", "girl", "princess", "guard", "wife")):
                side = "right"
            else:
                side = "left"

        # Resolve avatar if character speaks and no explicit portrait passed
        is_narrator = self.is_narration_speaker(speaker)
        if not is_narrator and portrait is None:
            portrait = AvatarRegistry.get(speaker, side, self.era_hint)

        full_wrapped_text = self._wrapped_lines[self.current_idx]
        display_text = full_wrapped_text[:int(self.text_progress)]

        # =====================================================================
        # OPTION A: BRANCH 1 - CINEMATIC LETTERBOX SUBTITLE BAR (SCENE 19 STYLE)
        # =====================================================================
        if is_narrator:
            self._draw_cinematic_letterbox(speaker, display_text, full_wrapped_text, tag_color)
            return

        # =====================================================================
        # OPTION A: BRANCH 2 - UNIFIED CHARACTER DIALOGUE BOX WITH AVATAR BUST
        # =====================================================================
        self._draw_character_dialogue(speaker, display_text, full_wrapped_text, tag_color, portrait, side, aspect_correction)

    def _draw_cinematic_letterbox(self, speaker: str, display_text: str, full_text: str, tag_color: tuple):
        """Render Scene 19 style full-width cinematic letterbox subtitle bar."""
        left, right, bottom, top = get_current_viewport_rect()
        screen_w = right - left
        bar_h = 136
        cx = left + screen_w / 2
        cy = bottom + bar_h / 2

        # 1. Full-width dark obsidian letterbox background
        arcade.draw_rect_filled(
            arcade.XYWH(cx, cy, screen_w, bar_h),
            (11, 8, 14, 225)
        )
        # Top specular sheen line
        arcade.draw_line(left, bottom + bar_h, right, bottom + bar_h, (tag_color[0], tag_color[1], tag_color[2], 140), 1.5)
        arcade.draw_line(left, bottom + bar_h - 1, right, bottom + bar_h - 1, (255, 255, 255, 30), 1.0)

        # 2. Golden Header Tag (Centered)
        tag_text = speaker.upper() if speaker.strip() else "NARRATION"
        if not tag_text.startswith("❖"):
            tag_text = f"❖   {tag_text}   ❖"

        self._cine_tag_obj.text = tag_text
        self._cine_tag_obj.x = cx
        self._cine_tag_obj.y = bottom + bar_h - 26
        self._cine_tag_obj.color = (tag_color[0], tag_color[1], tag_color[2], 255)
        self._cine_tag_obj.draw()

        # 3. Subtitle Body (Centered with drop shadow)
        body_y = bottom + bar_h / 2 - 2
        self._cine_shadow_obj.text = display_text
        self._cine_shadow_obj.x = cx + 1
        self._cine_shadow_obj.y = body_y - 2
        self._cine_shadow_obj.draw()

        self._cine_body_obj.text = display_text
        self._cine_body_obj.x = cx
        self._cine_body_obj.y = body_y
        self._cine_body_obj.draw()

        # 4. Breathing Continue Prompt (Centered bottom)
        if self.text_progress >= len(full_text):
            pulse = math.sin(self.blink_timer * 4.5)
            alpha = int(170 + 75 * pulse)
            self._cine_prompt_obj.color = (215, 203, 190, alpha)
            self._cine_prompt_obj.x = cx
            self._cine_prompt_obj.y = bottom + 22
            self._cine_prompt_obj.draw()

    def _draw_character_dialogue(self, speaker: str, display_text: str, full_text: str, tag_color: tuple, portrait, side: str, aspect_correction: float):
        """Render character dialogue box with portrait bust, nameplate, and typewriter effect."""
        left, right, bottom, top = get_current_viewport_rect()
        screen_w = right - left
        base_dialog_cx = left + screen_w / 2
        base_dialog_cy = bottom + DIALOG_Y
        dialog_box_w = min(float(DIALOG_W), screen_w - 60.0)

        has_portrait = portrait is not None

        # 1. Panel Geometry
        panel_offset_x = 0
        if has_portrait:
            panel_offset_x = -75 if side == "right" else 75
        panel_w = int(dialog_box_w - (150 if has_portrait else 0))
        panel_h = int(DIALOG_H)
        panel_cx = int(base_dialog_cx + panel_offset_x)
        panel_cy = int(base_dialog_cy)
        panel_top = panel_cy + panel_h // 2
        panel_bottom = panel_cy - panel_h // 2
        panel_left = panel_cx - panel_w // 2
        panel_right = panel_cx + panel_w // 2

        # 2. Character Portrait Bust
        if has_portrait:
            if side == "right":
                port_x = int(base_dialog_cx + dialog_box_w / 2 - 75)
                port_y = int(base_dialog_cy + 55)
                tex_aspect = portrait.width / max(1, portrait.height)
                port_h = 226
                port_w = int(min(160, port_h * tex_aspect * aspect_correction))
            else:
                port_x = int(base_dialog_cx - dialog_box_w / 2 + 75)
                port_y = int(base_dialog_cy + 45)
                tex_aspect = portrait.width / max(1, portrait.height)
                port_h = 205
                port_w = int(min(145, port_h * tex_aspect * aspect_correction))

            # Backdrop behind portrait
            arcade.draw_rect_filled(arcade.XYWH(port_x, port_y - 2, port_w + 6, port_h + 6), (5, 4, 8, 160))
            arcade.draw_rect_filled(arcade.XYWH(port_x, port_y, port_w, port_h), (18, 14, 22, 220))
            # Portrait Texture
            arcade.draw_texture_rect(portrait, arcade.XYWH(port_x, port_y, port_w, port_h))
            # Elegant outer rim
            arcade.draw_rect_outline(arcade.XYWH(port_x, port_y, port_w + 2, port_h + 2), (tag_color[0], tag_color[1], tag_color[2], 220), 2.0)

        # 3. Layered Glassmorphic Chassis
        arcade.draw_rect_filled(arcade.XYWH(panel_cx, panel_cy - 3, panel_w + 8, panel_h + 8), (4, 3, 7, 130))
        arcade.draw_rect_filled(arcade.XYWH(panel_cx, panel_cy, panel_w, panel_h), (14, 12, 18, 245))

        # Specular sheen
        sheen_y = panel_top - 1
        arcade.draw_line(panel_left + 6, sheen_y, panel_right - 6, sheen_y, (255, 255, 255, 42), 1.5)

        # Border & inner hairline
        arcade.draw_rect_outline(arcade.XYWH(panel_cx, panel_cy, panel_w, panel_h), (tag_color[0], tag_color[1], tag_color[2], 215), 2.0)
        arcade.draw_rect_outline(arcade.XYWH(panel_cx, panel_cy, panel_w - 6, panel_h - 6), (255, 255, 255, 22), 1.0)

        # Corner HUD Accents
        corner_sz = 9
        for dx, dy in ((-1, -1), (-1, 1), (1, -1), (1, 1)):
            cx = panel_cx + dx * (panel_w // 2 - 3)
            cy = panel_cy + dy * (panel_h // 2 - 3)
            arcade.draw_line(cx, cy, cx - dx * corner_sz, cy, (tag_color[0], tag_color[1], tag_color[2], 230), 2.0)
            arcade.draw_line(cx, cy, cx, cy - dy * corner_sz, (tag_color[0], tag_color[1], tag_color[2], 230), 2.0)

        # 4. Speaker Nameplate
        badge_w = max(136, int(len(speaker) * 10 + 36))
        badge_h = 30
        if has_portrait and side == "right":
            badge_x = int(panel_right - badge_w // 2 - 24)
        else:
            badge_x = int(panel_left + badge_w // 2 + 24)
        badge_y = int(panel_top + badge_h // 2 - 2)

        arcade.draw_rect_filled(arcade.XYWH(badge_x, badge_y, badge_w, badge_h), (20, 16, 26, 252))
        arcade.draw_rect_outline(arcade.XYWH(badge_x, badge_y, badge_w, badge_h), (tag_color[0], tag_color[1], tag_color[2], 240), 1.5)

        gem_x = int(badge_x - badge_w // 2 + 14)
        arcade.draw_circle_filled(gem_x, badge_y, 3.5, (tag_color[0], tag_color[1], tag_color[2], 255))

        self._speaker_text_obj.text = speaker.upper()
        self._speaker_text_obj.x = badge_x + 5
        self._speaker_text_obj.y = badge_y
        self._speaker_text_obj.color = (255, 252, 246, 255)
        self._speaker_text_obj.draw()

        # 5. Dialogue Body Text
        text_x = int(panel_left + 36)
        text_y = int(panel_top - 26)
        text_w = int(panel_w - 72)

        self._shadow_text_obj.width = text_w
        self._shadow_text_obj.text = display_text
        self._shadow_text_obj.x = text_x + 1
        self._shadow_text_obj.y = text_y - 2

        self._body_text_obj.width = text_w
        self._body_text_obj.text = display_text
        self._body_text_obj.x = text_x
        self._body_text_obj.y = text_y
        self._body_text_obj.color = (COLOR_TEXT_WHITE[0], COLOR_TEXT_WHITE[1], COLOR_TEXT_WHITE[2], 255)

        self._shadow_text_obj.draw()
        self._body_text_obj.draw()

        # 6. Breathing Continue Indicator
        if self.text_progress >= len(full_text):
            pulse = math.sin(self.blink_timer * 4.5)
            alpha = int(185 + 70 * pulse)
            shift_x = int(pulse * 3)

            hint_x = int(panel_right - 32 + shift_x)
            hint_y = int(panel_bottom + 20)

            self._prompt_text_obj.x = hint_x
            self._prompt_text_obj.y = hint_y
            self._prompt_text_obj.color = (tag_color[0], tag_color[1], tag_color[2], alpha)
            self._prompt_text_obj.draw()


class NarrationBar(DialogueBox):
    """Direct alias/subclass for Scene 19 style full-width cinematic letterbox."""
    def __init__(self):
        super().__init__()

    def start_narration(self, lines, on_complete=None):
        formatted = []
        for item in lines:
            if isinstance(item, str):
                formatted.append(("NARRATION", item, (235, 198, 110)))
            elif len(item) == 2:
                formatted.append((item[0], item[1], (235, 198, 110)))
            else:
                formatted.append(item)
        self.start_dialogue(formatted, on_complete=on_complete)
