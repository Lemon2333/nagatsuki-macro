# locator_service.py
import threading
import time
from dataclasses import dataclass
from typing import Optional, Tuple

import ctypes
import ctypes.wintypes as wt

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 全域熱鍵常數
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

WM_HOTKEY = 0x0312

VK_P = 0x50
VK_L = 0x4C

# 結構
@dataclass
class Point:
    x: int
    y: int

@dataclass
class CaptureResult:
    screen: Point
    client: Optional[Point]  # 若無前景窗或轉換失敗則為 None
    hwnd: Optional[int]
    title: str

# 工具函式
def get_cursor_pos() -> Point:
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return Point(pt.x, pt.y)

def get_foreground_hwnd() -> Optional[int]:
    h = user32.GetForegroundWindow()
    return int(h) if h else None

def hwnd_to_title(hwnd: int) -> str:
    if not hwnd:
        return ""
    length = user32.GetWindowTextLengthW(hwnd) + 1
    buf = ctypes.create_unicode_buffer(length)
    user32.GetWindowTextW(hwnd, buf, length)
    return buf.value

def screen_to_client(hwnd: int, x: int, y: int) -> Optional[Point]:
    if not hwnd:
        return None
    pt = wt.POINT(x, y)
    if not user32.ScreenToClient(hwnd, ctypes.byref(pt)):
        return None
    return Point(pt.x, pt.y)

def copy_to_clipboard(text: str) -> bool:
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        CF_UNICODETEXT = 13
        data = ctypes.create_unicode_buffer(text)
        size = (len(data) + 1) * ctypes.sizeof(ctypes.c_wchar)
        hGlobal = kernel32.GlobalAlloc(0x2000, size)  # GMEM_MOVEABLE
        if not hGlobal:
            return False
        lp = kernel32.GlobalLock(hGlobal)
        ctypes.memmove(lp, ctypes.addressof(data), size)
        kernel32.GlobalUnlock(hGlobal)
        user32.SetClipboardData(CF_UNICODETEXT, hGlobal)
        return True
    finally:
        user32.CloseClipboard()

class LocatorService:
    """
    以全域熱鍵運作的定位模式：
    - Ctrl+Alt+L: 切換定位模式（開/關）
    - Ctrl+Alt+P: 擷取一次座標，輸出到 console 並複製到剪貼簿
    可注入：自訂熱鍵、回呼函式（例如推送到你的 UI / OSD）。
    """
    def __init__(self,
                 toggle_mods=MOD_CONTROL | MOD_ALT,
                 toggle_vk=VK_L,
                 capture_mods=MOD_CONTROL | MOD_ALT,
                 capture_vk=VK_P,
                 show_osd: bool = False,
                 callback=None):
        self.toggle_mods = toggle_mods
        self.toggle_vk = toggle_vk
        self.capture_mods = capture_mods
        self.capture_vk = capture_vk
        self.show_osd = show_osd
        self.callback = callback  # callback(CaptureResult)
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._registered = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[Locator] started (Ctrl+Alt+L toggle, Ctrl+Alt+P capture)")

    def stop(self):
        self._running = False
        # 發送一個假訊息讓 PeekMessage 返回
        user32.PostThreadMessageW(kernel32.GetCurrentThreadId(), 0, 0, 0)
        print("[Locator] stopping...")

    def _register_hotkeys(self):
        if self._registered:
            return
        if not user32.RegisterHotKey(None, 1, self.toggle_mods, self.toggle_vk):
            print("[Locator] RegisterHotKey toggle failed")
        if not user32.RegisterHotKey(None, 2, self.capture_mods, self.capture_vk):
            print("[Locator] RegisterHotKey capture failed")
        self._registered = True

    def _unregister_hotkeys(self):
        if not self._registered:
            return
        user32.UnregisterHotKey(None, 1)
        user32.UnregisterHotKey(None, 2)
        self._registered = False

    def _loop(self):
        self._register_hotkeys()
        active = False
        msg = wt.MSG()
        while self._running:
            if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                if msg.message == WM_HOTKEY:
                    hotkey_id = msg.wParam
                    if hotkey_id == 1:  # toggle
                        active = not active
                        print(f"[Locator] {'ON' if active else 'OFF'}")
                    elif hotkey_id == 2 and active:  # capture
                        res = self.capture_once()
                        self._handle_capture(res)
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                time.sleep(0.01)
        self._unregister_hotkeys()
        print("[Locator] stopped")

    def capture_once(self) -> CaptureResult:
        screen = get_cursor_pos()
        hwnd = get_foreground_hwnd()
        title = hwnd_to_title(hwnd) if hwnd else ""
        client_pt = screen_to_client(hwnd, screen.x, screen.y) if hwnd else None
        return CaptureResult(screen=screen, client=client_pt, hwnd=hwnd, title=title)

    def _handle_capture(self, res: CaptureResult):
        scr = f"screen=({res.screen.x},{res.screen.y})"
        cli = f" client=({res.client.x},{res.client.y})" if res.client else " client=(n/a)"
        txt = f"{scr}{cli} title='{res.title}' hwnd={res.hwnd}"
        print("[Locator] " + txt)
        copy_to_clipboard(txt)
        if self.callback:
            try:
                self.callback(res)
            except Exception as e:
                print(f"[Locator] callback error: {e}")