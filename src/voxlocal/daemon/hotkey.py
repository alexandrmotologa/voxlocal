"""Global system hotkey listener for background meeting recording control."""

import ctypes
import ctypes.wintypes
import logging
import platform
import threading
from collections.abc import Callable

logger = logging.getLogger(__name__)

# Windows hotkey constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
HOTKEY_ID = 101


class GlobalHotkeyListener:
    """Listens for system-wide hotkeys to toggle meeting recording."""

    def __init__(self, callback: Callable[[], None], hotkey_desc: str = "Win+Alt+R"):
        self.callback = callback
        self.hotkey_desc = hotkey_desc
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        """Start listening for global hotkey on a background thread."""
        if platform.system() != "Windows":
            logger.info("Global hotkey registration is currently supported on Windows.")
            return False

        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(target=self._hotkey_loop, daemon=True, name="HotkeyThread")
        self._thread.start()
        logger.info("Registered global hotkey [%s]", self.hotkey_desc)
        return True

    def stop(self) -> None:
        """Unregister hotkey and stop background loop."""
        self._running = False
        if platform.system() == "Windows":
            user32 = ctypes.windll.user32
            user32.PostQuitMessage(0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _hotkey_loop(self) -> None:
        """Windows Win32 message loop listening for WM_HOTKEY."""
        user32 = ctypes.windll.user32

        # Register Win + Alt + R (VK_R = 0x52)
        modifiers = MOD_WIN | MOD_ALT | MOD_NOREPEAT
        vk_code = 0x52  # 'R' key

        if not user32.RegisterHotKey(None, HOTKEY_ID, modifiers, vk_code):
            # Fallback to Ctrl + Alt + R
            modifiers = MOD_CONTROL | MOD_ALT | MOD_NOREPEAT
            if not user32.RegisterHotKey(None, HOTKEY_ID, modifiers, vk_code):
                logger.warning("Could not register system hotkey. Run as administrator or check collisions.")
                self._running = False
                return

        msg = ctypes.wintypes.MSG()
        try:
            while self._running:
                # Non-zero on message, 0 on WM_QUIT, -1 on error
                res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if res <= 0:
                    break
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    try:
                        self.callback()
                    except Exception as exc:
                        logger.error("Error executing hotkey callback: %s", exc)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnregisterHotKey(None, HOTKEY_ID)
            self._running = False
