"""Base view for The Last Ingredient narrative scenes.
Provides resolution-independent fullscreen scaling and coordinate projection.
Ensures the entire game visual fills 100% of the display with zero black letterbox bars.
"""
import sys
import traceback
import types
import arcade
from arcade.types.rect import LRBT
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, START_FULLSCREEN


def disable_windows_ime(window):
    """Disable Windows IME popup and candidate window for the game window.
    Prevents Chinese input method candidate floating boxes from appearing when pressing game keys (E, W, A, S, D).
    """
    if sys.platform != "win32" or not window:
        return
    try:
        import ctypes
        hwnd = getattr(window, "_hwnd", None)
        if hwnd:
            # Disassociate IME context from the Win32 window handle
            ctypes.windll.imm32.ImmAssociateContext(hwnd, 0)

        # Activate US English keyboard layout for the game thread (00000409 = en-US)
        hkl = ctypes.windll.user32.LoadKeyboardLayoutW("00000409", 1)
        if hkl:
            ctypes.windll.user32.ActivateKeyboardLayout(hkl, 0)
    except Exception:
        pass


_WIN32_USER32 = None
if sys.platform == "win32":
    try:
        import ctypes
        from ctypes import wintypes

        class _WIN32_CURSORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("hCursor", wintypes.HANDLE),
                ("ptScreenPos", wintypes.POINT),
            ]

        _u32 = ctypes.WinDLL("user32", use_last_error=True)
        _u32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
        _u32.LoadCursorW.restype = wintypes.HANDLE
        _u32.SetClassLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        _u32.SetClassLongPtrW.restype = ctypes.c_void_p
        _u32.SetCursor.argtypes = [wintypes.HANDLE]
        _u32.SetCursor.restype = wintypes.HANDLE
        _u32.ShowCursor.argtypes = [wintypes.BOOL]
        _u32.ShowCursor.restype = ctypes.c_int
        _u32.GetCursorInfo.argtypes = [ctypes.POINTER(_WIN32_CURSORINFO)]
        _u32.GetCursorInfo.restype = wintypes.BOOL
        _u32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
        _u32.GetCursorPos.restype = wintypes.BOOL
        _u32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        _u32.ScreenToClient.restype = wintypes.BOOL
        _WIN32_USER32 = _u32
    except Exception:
        _WIN32_USER32 = None


def ensure_mouse_cursor_visible(window):
    """Hide OS hardware cursor so the universal in-engine cursor draws with 100% OBS visibility."""
    if not window:
        return
    try:
        window.set_exclusive_mouse(False)
        window.set_mouse_visible(False)
    except Exception:
        pass


def _get_win32_hidden_cursor_client_pos(window):
    """Return (x, y) in Arcade bottom-left pixel coordinates ONLY if Win32 reports cursor is hidden."""
    if sys.platform != "win32" or _WIN32_USER32 is None or not window:
        return None
    if not getattr(window, "_mouse_visible", True) or getattr(window, "_exclusive_mouse", False):
        return None
    try:
        import ctypes
        from ctypes import wintypes
        u32 = _WIN32_USER32
        ci = _WIN32_CURSORINFO(cbSize=ctypes.sizeof(_WIN32_CURSORINFO))
        if not u32.GetCursorInfo(ctypes.byref(ci)):
            return None
        # CURSOR_SHOWING == 1. If it is visible, let the OS draw the native cursor.
        if (ci.flags & 1) and ci.hCursor:
            return None
        pt = wintypes.POINT()
        if not u32.GetCursorPos(ctypes.byref(pt)):
            return None
        hwnd = getattr(window, "_view_hwnd", None) or getattr(window, "_hwnd", None)
        if hwnd and u32.ScreenToClient(hwnd, ctypes.byref(pt)):
            return float(pt.x), float(window.height - pt.y)
        mx = getattr(window, "_mouse_x", None)
        my = getattr(window, "_mouse_y", None)
        if mx is not None and my is not None:
            return float(mx), float(my)
    except Exception:
        return None
    return None


def setup_window_ime(window):
    """Apply IME suppression and register an on_activate handler to persist on focus regain."""
    if sys.platform != "win32" or not window:
        return

    disable_windows_ime(window)
    configure_window_for_recording(window)

    # Re-apply whenever the window regains focus (e.g. after Alt+Tab)
    if not getattr(window, "_ime_handler_attached", False):
        try:
            def _on_activate():
                disable_windows_ime(window)
                configure_window_for_recording(window)
                try:
                    if getattr(window, "_mouse_visible", True):
                        ensure_mouse_cursor_visible(window)
                except Exception:
                    pass
            window.push_handlers(on_activate=_on_activate)
            window._ime_handler_attached = True
        except Exception:
            pass


def configure_window_for_recording(window):
    """Ensure the window has taskbar visibility, clean title, and Win32 composite flags
    so OBS Studio (Window Capture & Game Capture) detects and captures it with 100% reliability,
    matching Pygame / SDL2 behavior.
    """
    if sys.platform != "win32" or not window:
        return
    try:
        import ctypes
        u32 = ctypes.windll.user32
        hwnd = getattr(window, "_hwnd", None)
        view_hwnd = getattr(window, "_view_hwnd", None)
        if hwnd:
            # 1. Force WS_EX_APPWINDOW (0x00040000) so Windows Taskbar, Alt+Tab, and OBS Window Capture register it
            WS_EX_APPWINDOW = 0x00040000
            ex_style = u32.GetWindowLongW(hwnd, -20)
            u32.SetWindowLongW(hwnd, -20, ex_style | WS_EX_APPWINDOW)

            # 2. Add WS_CLIPCHILDREN (0x02000000) & WS_CLIPSIBLINGS (0x04000000)
            # Ensures Windows DWM composes the OpenGL child window cleanly into the captured frame
            WS_CLIPCHILDREN = 0x02000000
            WS_CLIPSIBLINGS = 0x04000000
            style = u32.GetWindowLongW(hwnd, -16)
            u32.SetWindowLongW(hwnd, -16, style | WS_CLIPCHILDREN | WS_CLIPSIBLINGS)

            # 3. Synchronize clean ASCII caption to both outer hwnd and OpenGL view_hwnd
            caption = getattr(window, "caption", None) or "The Last Ingredient - One Chance to Begin Again"
            caption = str(caption).replace("Â·", "-").replace("·", "-")
            u32.SetWindowTextW(hwnd, caption)
            if view_hwnd:
                u32.SetWindowTextW(view_hwnd, caption)

            # 4. Trigger frame update without changing size or position
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            u32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER)
    except Exception:
        pass


class BaseGameView(arcade.View):
    """Base View class providing fullscreen projection, mouse mapping, and pause menu."""

    def __init__(self):
        super().__init__()
        self.camera = None

        # Global Pause & Exit Menu state
        self.is_paused = False
        self.hovered_pause_btn = None
        self.pause_buttons = [
            ("resume", "▶   RESUME GAME", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 38, 340, 48),
            ("menu", "⌂   MAIN MENU", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 26, 340, 48),
            ("exit", "✕   EXIT TO DESKTOP", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 90, 340, 48),
        ]
        # Dedicated UI camera for the pause menu so it stays screen-centered
        # regardless of the active world-follow game camera.
        self._pause_camera = None
        self._cursor_camera = None

        # Crash guard: on any uncaught exception in a view handler we log the
        # full traceback to game_error.log AND paint it onto the game window so
        # the error is visible without a console (the user often cannot capture
        # the red text in a separate terminal).
        self._crash = None
        self._crash_logged = False
        self._install_crash_guard()

    def _install_crash_guard(self):
        for name in ("on_draw", "on_update", "on_key_press", "on_mouse_press", "on_mouse_release",
                     "on_mouse_motion", "on_mouse_drag", "on_mouse_enter", "on_mouse_leave",
                     "on_key_release", "on_show_view", "on_resize"):
            fn = getattr(self, name, None)
            if callable(fn):
                setattr(self, name, self._wrap_handler(name, fn))

    def _wrap_handler(self, name, fn):
        # Must stay a *bound* method (not a plain closure): pyglet's
        # remove_handlers() wraps handlers in WeakMethod on every show_view(),
        # and WeakMethod rejects plain functions -> TypeError on scene switch.
        def safe(inst, *a, **k):
            if inst._crash and name == "on_draw":
                inst._render_crash_screen()
                return
            if name in ("on_mouse_motion", "on_mouse_drag", "on_mouse_press", "on_mouse_release"):
                if len(a) >= 2:
                    inst._cursor_x = float(a[0])
                    inst._cursor_y = float(a[1])
                    if inst.window:
                        inst.window._last_view_mouse_x = float(a[0])
                        inst.window._last_view_mouse_y = float(a[1])
            if name == "on_mouse_press":
                inst._mouse_down = True
            elif name == "on_mouse_release":
                inst._mouse_down = False
            elif name == "on_mouse_leave":
                inst._mouse_in_window = False
            elif name == "on_mouse_enter":
                inst._mouse_in_window = True
            try:
                ret = fn(*a, **k)
                if name == "on_draw":
                    inst._draw_in_engine_cursor()
                return ret
            except Exception:
                inst._record_crash(traceback.format_exc())
                if name == "on_draw":
                    inst._render_crash_screen()
                return
        return types.MethodType(safe, self)

    def _record_crash(self, tb_text):
        self._crash = tb_text
        if self._crash_logged:
            return
        self._crash_logged = True
        try:
            from pathlib import Path
            path = Path(__file__).resolve().parent.parent / "game_error.log"
            with open(path, "a", encoding="utf-8") as f:
                f.write("=" * 70 + "\n")
                f.write(tb_text + "\n")
        except Exception:
            pass

    def _render_crash_screen(self):
        try:
            w = self.window.width if self.window else SCREEN_WIDTH
            h = self.window.height if self.window else SCREEN_HEIGHT
            self.window.default_camera.use()
            arcade.draw_rect_filled(
                arcade.XYWH(w / 2, h / 2, w, h), (12, 0, 0, 235))
            lines = self._crash.strip().split("\n")[-32:]
            y = h - 28
            for ln in lines:
                obj = arcade.Text(
                    ln[:150], 18, y, (255, 210, 210), 12,
                    anchor_x="left", anchor_y="top",
                    font_name=("Consolas", "Courier New", "monospace"),
                )
                obj.draw()
                y -= 16
        except Exception:
            pass


    def setup_camera(self):
        """Initialize or rebind the scaling 2D camera."""
        if not self.window:
            return
        if self.camera is None:
            self.camera = arcade.camera.Camera2D(window=self.window)
        self.update_camera()

    def update_camera(self):
        """Update viewport to cover 100% of the active window / screen."""
        if self.camera and self.window:
            self.camera.viewport = LRBT(0, self.window.width, 0, self.window.height)
            self.camera.projection = LRBT(-SCREEN_WIDTH / 2, SCREEN_WIDTH / 2, -SCREEN_HEIGHT / 2, SCREEN_HEIGHT / 2)
            self.camera.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    def clean_texture_atlas(self):
        """Reset the default texture atlas to free up GPU atlas memory between major scenes."""
        if self.window and hasattr(self.window, "ctx"):
            try:
                from arcade.texture_atlas.atlas_default import DefaultTextureAtlas
                self.window.ctx._atlas = DefaultTextureAtlas((2048, 2048), ctx=self.window.ctx)
            except Exception:
                pass

    def on_show_view(self):
        """Automatically called when view is activated on window."""
        if START_FULLSCREEN and self.window and not self.window.fullscreen:
            self.window.set_fullscreen(True)
            configure_window_for_recording(self.window)
        if self.window:
            ensure_mouse_cursor_visible(self.window)
        setup_window_ime(self.window)
        self.setup_camera()


    def on_resize(self, width: int, height: int):
        """Called whenever window size changes (e.g. F11 fullscreen toggle)."""
        super().on_resize(width, height)
        self.update_camera()
        configure_window_for_recording(self.window)

    def use_game_camera(self):
        """Activate the scaling camera at the start of on_draw()."""
        if self.camera is None and self.window:
            self.setup_camera()
        if self.camera:
            self.camera.use()

    def to_virtual_coords(self, x: float, y: float):
        """Convert physical screen/window pixel coordinates to virtual (1280x720) space.

        The pause menu is drawn (and its buttons hit-tested) in this fixed virtual
        space, independent of the world-follow game camera's position. Using the game
        camera's unproject() here would map screen pixels to world coordinates and the
        buttons could never be hit, so we map linearly to the fixed virtual viewport.
        """
        if not self.window or self.window.height == 0:
            return x, y
        vx = (x / self.window.width) * SCREEN_WIDTH
        vy = (y / self.window.height) * SCREEN_HEIGHT
        return vx, vy

    def _use_pause_camera(self):
        """Switch to a fixed virtual-resolution camera so the pause menu is always
        drawn screen-centered, independent of the world-follow game camera."""
        if self.window is None:
            return
        if self._pause_camera is None:
            self._pause_camera = arcade.camera.Camera2D(window=self.window)
        cam = self._pause_camera
        cam.viewport = LRBT(0, self.window.width, 0, self.window.height)
        cam.projection = LRBT(-SCREEN_WIDTH / 2, SCREEN_WIDTH / 2,
                              -SCREEN_HEIGHT / 2, SCREEN_HEIGHT / 2)
        cam.position = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
        cam.use()

    def toggle_fullscreen(self):
        """Toggle fullscreen mode on the parent window."""
        if self.window:
            self.window.set_fullscreen(not self.window.fullscreen)
            self.update_camera()
            configure_window_for_recording(self.window)
            if getattr(self.window, "_mouse_visible", True):
                ensure_mouse_cursor_visible(self.window)

    @property
    def is_16_10(self) -> bool:
        """Detect whether the current display or window aspect ratio is approximately 16:10 (e.g. 1.60),
        as opposed to standard 16:9 (1.78) or wider.
        """
        if self.window and self.window.height > 0:
            aspect = self.window.width / self.window.height
            return aspect < 1.68
        # Fallback to system display metric if window is not yet attached
        if sys.platform == "win32":
            try:
                import ctypes
                w = ctypes.windll.user32.GetSystemMetrics(0)
                h = ctypes.windll.user32.GetSystemMetrics(1)
                if h > 0:
                    return (w / h) < 1.68
            except Exception:
                pass
        return False

    def get_adaptive_texture(self, texture_16_9: arcade.Texture, texture_16_10: arcade.Texture) -> arcade.Texture:
        """Return the native 16:10 texture if a 16:10 display is detected,
        otherwise return the cropped 16:9 texture.
        """
        return texture_16_10 if self.is_16_10 else texture_16_9

    @property
    def aspect_ratio_correction(self) -> float:
        """Horizontal scale factor to ensure characters and sprites retain their original
        1:1 un-stretched aspect ratio even when the background is stretched to fill widescreen displays.
        """
        if not self.window or self.window.height == 0:
            return 1.0
        current_aspect = self.window.width / self.window.height
        base_aspect = SCREEN_WIDTH / SCREEN_HEIGHT  # 1280 / 720 = 1.7778
        if current_aspect <= 0:
            return 1.0
        return base_aspect / current_aspect

    def handle_pause_key(self, key: int) -> bool:
        """Handle ESC to toggle pause menu, and ENTER while paused. Returns True if handled."""
        if key == arcade.key.ESCAPE:
            self.is_paused = not self.is_paused
            self.hovered_pause_btn = None
            return True

        if self.is_paused:
            if key in (arcade.key.ENTER, arcade.key.SPACE):
                if self.hovered_pause_btn == "menu":
                    self.is_paused = False
                    from scenes.menu_view import MenuView
                    self.window.show_view(MenuView())
                elif self.hovered_pause_btn == "exit":
                    self.window.close()
                else:
                    self.is_paused = False
            return True

        return False

    def handle_pause_mouse_motion(self, x: float, y: float) -> bool:
        """Update hovered pause button. Returns True if paused."""
        if not self.is_paused:
            return False
        vx, vy = self.to_virtual_coords(x, y)
        self.hovered_pause_btn = None
        for btn_id, _, bx, by, bw, bh in self.pause_buttons:
            if abs(vx - bx) <= bw / 2 and abs(vy - by) <= bh / 2:
                self.hovered_pause_btn = btn_id
                break
        return True

    def handle_pause_mouse_press(self, x: float, y: float, button: int) -> bool:
        """Handle clicks on pause buttons. Returns True if paused."""
        if not self.is_paused:
            return False
        vx, vy = self.to_virtual_coords(x, y)
        for btn_id, _, bx, by, bw, bh in self.pause_buttons:
            if abs(vx - bx) <= bw / 2 and abs(vy - by) <= bh / 2:
                if btn_id == "resume":
                    self.is_paused = False
                elif btn_id == "menu":
                    self.is_paused = False
                    from scenes.menu_view import MenuView
                    self.window.show_view(MenuView())
                elif btn_id == "exit":
                    self.window.close()
                break
        return True

    def _draw_in_engine_cursor(self):
        """Draw an ultra-crisp in-engine cursor directly into the OpenGL framebuffer.

        Guarantees 100% visibility on screen and in OBS recordings across
        Game Capture, Window Capture, and Display Capture.
        Hotspot (0.0, 0.0) is mathematically locked to the exact interaction point.
        """
        if getattr(self, "hide_in_game_cursor", False):
            return
        if getattr(self, "scoped", False) and not self.is_paused:
            return
        if not self.window:
            return

        w, h = self.window.width, self.window.height
        if w <= 0 or h <= 0:
            return

        # Ensure OS hardware cursor stays hidden so only our in-engine entity is seen
        if getattr(self.window, "_mouse_visible", False):
            try:
                self.window.set_mouse_visible(False)
            except Exception:
                pass

        # 1. Authoritative: position received by view mouse events (1:1 with view coordinate space)
        mx = getattr(self, "_cursor_x", None)
        my = getattr(self, "_cursor_y", None)
        if (mx is None or my is None) and self.window:
            mx = getattr(self.window, "_last_view_mouse_x", None)
            my = getattr(self.window, "_last_view_mouse_y", None)

        # 2. Live Win32 fallback if mouse hasn't moved yet in this view
        if mx is None or my is None:
            if sys.platform == "win32" and _WIN32_USER32 is not None:
                try:
                    import ctypes
                    from ctypes import wintypes
                    pt = wintypes.POINT()
                    if _WIN32_USER32.GetCursorPos(ctypes.byref(pt)):
                        hwnd = getattr(self.window, "_view_hwnd", None) or getattr(self.window, "_hwnd", None)
                        if hwnd and _WIN32_USER32.ScreenToClient(hwnd, ctypes.byref(pt)):
                            scale = getattr(self.window, "_mouse_scale", 1.0) or 1.0
                            client_rect = wintypes.RECT()
                            _WIN32_USER32.GetClientRect(hwnd, ctypes.byref(client_rect))
                            client_h = float(client_rect.bottom - client_rect.top)
                            mx = float(pt.x) / scale
                            my = (client_h - float(pt.y)) / scale
                except Exception:
                    pass

        # 3. Pyglet internal fallback (scaled by _mouse_scale)
        if mx is None or my is None:
            raw_x = getattr(self.window, "_mouse_x", None)
            raw_y = getattr(self.window, "_mouse_y", None)
            if raw_x is not None and raw_y is not None:
                scale = getattr(self.window, "_mouse_scale", 1.0) or 1.0
                mx = float(raw_x) / scale
                my = float(raw_y) / scale

        if mx is None or my is None:
            return

        if mx < 0 or mx > w or my < 0 or my > h:
            return

        # Ensure scissor test is disabled so cursor is never clipped
        try:
            self.window.ctx.scissor = None
        except Exception:
            pass

        if self._cursor_camera is None or self._cursor_camera.viewport.width != w or self._cursor_camera.viewport.height != h:
            self._cursor_camera = arcade.camera.Camera2D(window=self.window)
            self._cursor_camera.viewport = LRBT(0, w, 0, h)
            self._cursor_camera.projection = LRBT(-w / 2, w / 2, -h / 2, h / 2)
            self._cursor_camera.position = (w / 2, h / 2)

        self._cursor_camera.use()

        is_pressed = getattr(self, "_mouse_down", False)

        # Precise arrow geometry with (0.0, 0.0) as the exact hotspot tip
        arrow_shape = [
            (0.0, 0.0),
            (0.0, -21.0),
            (5.5, -15.5),
            (10.5, -24.5),
            (13.8, -23.0),
            (8.8, -14.0),
            (15.8, -14.0),
        ]

        # 1. Soft ambient drop shadow (offset down-right)
        shadow_pts = [(mx + dx + 1.5, my + dy - 2.0) for dx, dy in arrow_shape]
        arcade.draw_polygon_filled(shadow_pts, (0, 0, 0, 110))

        # 2. Main pointer polygon
        main_pts = [(mx + dx, my + dy) for dx, dy in arrow_shape]

        # 3. Outer obsidian border outline (ensures 100% contrast against all backgrounds)
        arcade.draw_polygon_outline(main_pts, (15, 12, 20, 255), 2.4)

        # 4. Crisp ivory-white body fill (subtle warm tint on click)
        fill_color = (255, 255, 255, 255) if not is_pressed else (240, 230, 195, 255)
        arcade.draw_polygon_filled(main_pts, fill_color)

        # 5. Delicate gold gemstone accent dot at thumb notch (amber flash on click)
        gem_color = (225, 185, 95, 240) if not is_pressed else (255, 160, 60, 255)
        arcade.draw_circle_filled(mx + 3.2, my - 6.5, 2.0, gem_color)

    def draw_pause_overlay(self):
        """Draw the cinematic dark glassmorphic pause/exit menu."""
        if not self.is_paused:
            return

        # Draw in fixed virtual screen space so the menu is always centered,
        # independent of whichever world camera was last active.
        self._use_pause_camera()

        # 1. Darkened cinematic backdrop
        arcade.draw_rect_filled(
            arcade.XYWH(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT),
            (8, 6, 12, 230)
        )

        # 2. Centered Modal Window
        cx = SCREEN_WIDTH / 2
        cy = SCREEN_HEIGHT / 2
        modal_w = 460
        modal_h = 320
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, modal_w + 6, modal_h + 6), (210, 180, 110, 60), 2.0)
        arcade.draw_rect_filled(arcade.XYWH(cx, cy, modal_w, modal_h), (18, 16, 24, 250))
        arcade.draw_rect_outline(arcade.XYWH(cx, cy, modal_w, modal_h), (215, 175, 100), 2.0)

        # Title & Subtitle
        arcade.draw_text("PAUSED", cx, cy + 106, (255, 235, 185), 22, anchor_x="center", bold=True)
        arcade.draw_text("PRESS  [ESC]  TO  RESUME", cx, cy + 80, (185, 175, 195), 11, anchor_x="center")
        arcade.draw_line(cx - 180, cy + 64, cx + 180, cy + 64, (215, 175, 100, 140), 1.5)

        # Buttons
        for btn_id, label, bx, by, bw, bh in self.pause_buttons:
            is_hover = (self.hovered_pause_btn == btn_id)
            if btn_id == "resume":
                bg_col = (34, 98, 64) if is_hover else (24, 38, 32)
                border_col = (90, 235, 145) if is_hover else (65, 115, 85)
            elif btn_id == "menu":
                bg_col = (42, 65, 105) if is_hover else (28, 34, 48)
                border_col = (110, 190, 255) if is_hover else (75, 95, 125)
            else:
                bg_col = (145, 42, 48) if is_hover else (45, 26, 32)
                border_col = (255, 95, 105) if is_hover else (125, 60, 68)

            arcade.draw_rect_filled(arcade.XYWH(bx, by, bw, bh), bg_col)
            arcade.draw_rect_outline(arcade.XYWH(bx, by, bw, bh), border_col, 2.0 if is_hover else 1.2)
            text_col = (255, 255, 255) if is_hover else (235, 230, 225)
            arcade.draw_text(label, bx, by - 6, text_col, 13, anchor_x="center", bold=True)
