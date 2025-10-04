# input_controller.py
# -*- coding: utf-8 -*-
import ctypes
import time
import ctypes.wintypes as wt



from typing import Iterable, Optional, Tuple, List, Callable, Union

# ========== Win32 結構與常量 ==========
PUL = ctypes.POINTER(ctypes.c_ulong)
ULONG_PTR = ctypes.POINTER(ctypes.c_ulong)

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]

class MouseInput(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]

class KeyboardInput(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", PUL),
    ]

class HardwareInput(ctypes.Structure):
    _fields_ = [
        ("uMsg", ctypes.c_ulong),
        ("wParamL", ctypes.c_short),
        ("wParamH", ctypes.c_ushort),
    ]

class Input_I(ctypes.Union):
    _fields_ = [
        ("mi", MouseInput),
        ("ki", KeyboardInput),
        ("hi", HardwareInput),
    ]

class Input(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("ii", Input_I)]

# INPUT 類型
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# Mouse flags
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_HWHEEL = 0x01000
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_MOVE_NOCOALESCE = 0x2000
MOUSEEVENTF_VIRTUALDESK = 0x4000

# Keyboard flags
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# 常用虛擬鍵碼
VK = {
    "LBUTTON": 0x01,
    "RBUTTON": 0x02,
    "MBUTTON": 0x04,
    "BACK": 0x08,
    "TAB": 0x09,
    "RETURN": 0x0D,
    "SHIFT": 0x10,
    "CONTROL": 0x11,
    "MENU": 0x12,
    "ESCAPE": 0x1B,
    "SPACE": 0x20,
    "LEFT": 0x25,
    "UP": 0x26,
    "RIGHT": 0x27,
    "DOWN": 0x28,
    "INSERT": 0x2D,
    "DELETE": 0x2E,
    "KEY_0": 0x30, "KEY_1": 0x31, "KEY_2": 0x32, "KEY_3": 0x33,
    "KEY_4": 0x34, "KEY_5": 0x35, "KEY_6": 0x36, "KEY_7": 0x37,
    "KEY_8": 0x38, "KEY_9": 0x39,
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45, "F": 0x46,
    "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A, "K": 0x4B, "L": 0x4C,
    "M": 0x4D, "N": 0x4E, "O": 0x4F, "P": 0x50, "Q": 0x51, "R": 0x52,
    "S": 0x53, "T": 0x54, "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58,
    "Y": 0x59, "Z": 0x5A,
    "LWIN": 0x5B, "RWIN": 0x5C,
    "APPS": 0x5D,
    "NUMPAD0": 0x60, "NUMPAD1": 0x61, "NUMPAD2": 0x62, "NUMPAD3": 0x63,
    "NUMPAD4": 0x64, "NUMPAD5": 0x65, "NUMPAD6": 0x66, "NUMPAD7": 0x67,
    "NUMPAD8": 0x68, "NUMPAD9": 0x69,
    "MULTIPLY": 0x6A, "ADD": 0x6B, "SEPARATOR": 0x6C, "SUBTRACT": 0x6D,
    "DECIMAL": 0x6E, "DIVIDE": 0x6F,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74,
    "F6": 0x75, "F7": 0x76, "F8": 0x77, "F9": 0x78, "F10": 0x79,
    "F11": 0x7A, "F12": 0x7B,
    "NUMLOCK": 0x90, "SCROLL": 0x91,
    "LSHIFT": 0xA0, "RSHIFT": 0xA1,
    "LCONTROL": 0xA2, "RCONTROL": 0xA3,
    "LMENU": 0xA4, "RMENU": 0xA5,
}

# API
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SendInput = user32.SendInput
GetSystemMetrics = user32.GetSystemMetrics
GetCursorPos = user32.GetCursorPos
SetCursorPos = user32.SetCursorPos
WindowFromPoint = user32.WindowFromPoint
ScreenToClient = user32.ScreenToClient
ClientToScreen = user32.ClientToScreen
GetWindowRect = user32.GetWindowRect
GetClientRect = user32.GetClientRect
GetForegroundWindow = user32.GetForegroundWindow
SetForegroundWindow = user32.SetForegroundWindow
SetFocus = user32.SetFocus
ShowWindow = user32.ShowWindow
IsIconic = user32.IsIconic
BringWindowToTop = user32.BringWindowToTop
SetWindowPos = user32.SetWindowPos
AttachThreadInput = user32.AttachThreadInput
GetWindowThreadProcessId = user32.GetWindowThreadProcessId
GetCurrentThreadId = kernel32.GetCurrentThreadId
EnumWindows = user32.EnumWindows
EnumChildWindows = user32.EnumChildWindows
GetWindowTextW = user32.GetWindowTextW
GetClassNameW = user32.GetClassNameW
IsWindowVisible = user32.IsWindowVisible

SW_RESTORE = 9
SW_SHOW = 5
SW_SHOWNA = 8
SW_SHOWNORMAL = 1
HWND_TOP = 0
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040

SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77

def _send_input(inputs):
    n = len(inputs)
    arr = (Input * n)(*inputs)
    cb_size = ctypes.sizeof(Input)
    sent = SendInput(n, ctypes.byref(arr), cb_size)
    if sent != n:
        pass  # 可在此擴展 GetLastError 以除錯

# ========== 螢幕/座標工具 ==========
def _to_absolute_coords(x: int, y: int) -> Tuple[int, int]:
    vx = GetSystemMetrics(SM_XVIRTUALSCREEN)
    vy = GetSystemMetrics(SM_YVIRTUALSCREEN)
    vw = GetSystemMetrics(SM_CXVIRTUALSCREEN)
    vh = GetSystemMetrics(SM_CYVIRTUALSCREEN)
    abs_x = int((x - vx) * 65535 / max(1, (vw - 1)))
    abs_y = int((y - vy) * 65535 / max(1, (vh - 1)))
    return abs_x, abs_y

def _cursor_pos() -> Tuple[int, int]:
    pt = POINT()
    GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y

# ========== 視窗管理 ==========
class WindowInfo:
    def __init__(self, hwnd: int, title: str, cls: str, pid: int, visible: bool):
        self.hwnd = hwnd
        self.title = title
        self.class_name = cls
        self.pid = pid
        self.visible = visible

    def __repr__(self):
        return f"WindowInfo(hwnd=0x{self.hwnd:08X}, pid={self.pid}, cls={self.class_name!r}, title={self.title!r}, visible={self.visible})"

class WindowManager:
    @staticmethod
    def enum_windows(filter_fn: Optional[Callable[[int], bool]] = None) -> List[int]:
        hwnds: List[int] = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def _enum_proc(hwnd, lParam):
            if filter_fn is None or filter_fn(hwnd):
                hwnds.append(hwnd)
            return True

        EnumWindows(_enum_proc, 0)
        return hwnds

    @staticmethod
    def get_window_text(hwnd: int) -> str:
        buf = ctypes.create_unicode_buffer(512)
        GetWindowTextW(hwnd, buf, 512)
        return buf.value

    @staticmethod
    def get_class_name(hwnd: int) -> str:
        buf = ctypes.create_unicode_buffer(256)
        GetClassNameW(hwnd, buf, 256)
        return buf.value

    @staticmethod
    def get_pid(hwnd: int) -> int:
        pid = ctypes.c_ulong(0)
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value

    @staticmethod
    def is_visible(hwnd: int) -> bool:
        return bool(IsWindowVisible(hwnd))

    @staticmethod
    def get_window_rect(hwnd: int) -> RECT:
        rc = RECT()
        GetWindowRect(hwnd, ctypes.byref(rc))
        return rc

    @staticmethod
    def get_client_rect(hwnd: int) -> RECT:
        rc = RECT()
        GetClientRect(hwnd, ctypes.byref(rc))
        return rc

    @staticmethod
    def client_to_screen(hwnd: int, x: int, y: int) -> Tuple[int, int]:
        pt = POINT(x, y)
        ClientToScreen(hwnd, ctypes.byref(pt))
        return pt.x, pt.y

    @staticmethod
    def screen_to_client(hwnd: int, x: int, y: int) -> Tuple[int, int]:
        pt = POINT(x, y)
        ScreenToClient(hwnd, ctypes.byref(pt))
        return pt.x, pt.y

    @staticmethod
    def get_window_info(hwnd: int) -> WindowInfo:
        return WindowInfo(
            hwnd=hwnd,
            title=WindowManager.get_window_text(hwnd),
            cls=WindowManager.get_class_name(hwnd),
            pid=WindowManager.get_pid(hwnd),
            visible=WindowManager.is_visible(hwnd),
        )

    @staticmethod
    def find_windows(
        title_equals: Optional[str] = None,
        title_contains: Optional[str] = None,
        class_equals: Optional[str] = None,
        class_contains: Optional[str] = None,
        pid: Optional[int] = None,
        visible_only: bool = True,
    ) -> List[WindowInfo]:
        def match(hwnd: int) -> bool:
            if visible_only and not WindowManager.is_visible(hwnd):
                return False
            t = WindowManager.get_window_text(hwnd)
            c = WindowManager.get_class_name(hwnd)
            p = WindowManager.get_pid(hwnd)
            if title_equals is not None and t != title_equals:
                return False
            if title_contains is not None and (t is None or title_contains not in t):
                return False
            if class_equals is not None and c != class_equals:
                return False
            if class_contains is not None and (c is None or class_contains not in c):
                return False
            if pid is not None and p != pid:
                return False
            return True

        hwnds = WindowManager.enum_windows(match)
        return [WindowManager.get_window_info(h) for h in hwnds]

    @staticmethod
    def focus_window(hwnd: int, timeout: float = 1.0) -> bool:
        # 穩健前置策略，對 Sandboxie、多視窗有較好兼容性
        # 1) 還原/顯示
        if IsIconic(hwnd):
            ShowWindow(hwnd, SW_RESTORE)
            time.sleep(0.02)
        else:
            ShowWindow(hwnd, SW_SHOWNORMAL)
            time.sleep(0.02)

        # 2) 提到頂部
        BringWindowToTop(hwnd)
        SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        time.sleep(0.02)

        # 3) 嘗試直接前景
        if SetForegroundWindow(hwnd):
            return True

        # 4) 附加執行緒輸入，繞過前景限制
        target_tid = GetWindowThreadProcessId(hwnd, ctypes.c_void_p())
        curr_tid = GetCurrentThreadId()
        AttachThreadInput(curr_tid, target_tid, True)
        try:
            BringWindowToTop(hwnd)
            ShowWindow(hwnd, SW_SHOW)
            SetForegroundWindow(hwnd)
            SetFocus(hwnd)
        finally:
            AttachThreadInput(curr_tid, target_tid, False)

        # 5) 等待前景確認
        start = time.time()
        while time.time() - start < timeout:
            if GetForegroundWindow() == hwnd:
                return True
            time.sleep(0.02)
        return GetForegroundWindow() == hwnd

# ========== 滑鼠控制 ==========
class Mouse:
    @staticmethod
    def move(x: int, y: int, absolute: bool = False, relative: bool = False, no_coalesce: bool = False):
        flags = MOUSEEVENTF_MOVE
        dx, dy = x, y
        if absolute:
            flags |= MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
            ax, ay = _to_absolute_coords(x, y)
            dx, dy = ax, ay
        elif relative:
            pass  # dx, dy 為相對偏移
        if no_coalesce:
            flags |= MOUSEEVENTF_MOVE_NOCOALESCE
        inp = Input(type=INPUT_MOUSE, ii=Input_I(mi=MouseInput(dx, dy, 0, flags, 0, None)))
        _send_input([inp])

    @staticmethod
    def move_relative(dx: int, dy: int):
        Mouse.move(dx, dy, absolute=False, relative=True)

    @staticmethod
    def click(button: str = "left", delay: float = 0.01):
        btn = button.lower()
        if btn == "left":
            down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
        elif btn == "right":
            down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        elif btn == "middle":
            down, up = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP
        else:
            raise ValueError("button 必須是 left/right/middle")

        down_inp = Input(type=INPUT_MOUSE, ii=Input_I(mi=MouseInput(0, 0, 0, down, 0, None)))
        up_inp = Input(type=INPUT_MOUSE, ii=Input_I(mi=MouseInput(0, 0, 0, up, 0, None)))
        _send_input([down_inp])
        if delay > 0:
            time.sleep(delay)
        _send_input([up_inp])

    @staticmethod
    def click_at(x: int, y: int, button: str = "left", delay: float = 0.01):
        Mouse.move(x, y, absolute=True)
        if delay > 0:
            time.sleep(delay)
        Mouse.click(button=button, delay=delay)

    @staticmethod
    def click_relative(dx: int, dy: int, button: str = "left", delay: float = 0.01):
        # 以目前游標位置為基準相對偏移
        Mouse.move_relative(dx, dy)
        if delay > 0:
            time.sleep(delay)
        Mouse.click(button=button, delay=delay)

    @staticmethod
    def click_in_window(hwnd: int, x: int, y: int, button: str = "left", delay: float = 0.01, client_coords: bool = True):
        """
        在指定窗口內點擊：
        - client_coords=True: x,y 為客戶區座標（不含標題欄與邊框），會自動轉為螢幕座標
        - client_coords=False: x,y 已是螢幕座標
        """
        if client_coords:
            sx, sy = WindowManager.client_to_screen(hwnd, x, y)
        else:
            sx, sy = x, y
        Mouse.click_at(sx, sy, button=button, delay=delay)

    @staticmethod
    def scroll(vertical: int = 0, horizontal: int = 0):
        inputs = []
        if vertical:
            inputs.append(Input(type=INPUT_MOUSE, ii=Input_I(mi=MouseInput(0, 0, vertical, MOUSEEVENTF_WHEEL, 0, None))))
        if horizontal:
            inputs.append(Input(type=INPUT_MOUSE, ii=Input_I(mi=MouseInput(0, 0, horizontal, MOUSEEVENTF_HWHEEL, 0, None))))
        if inputs:
            _send_input(inputs)

# ========== 鍵盤控制 ==========
class Keyboard:
    @staticmethod
    def key_down(vk: int):
        ki = KeyboardInput(wVk=vk, wScan=0, dwFlags=0, time=0, dwExtraInfo=None)
        _send_input([Input(type=INPUT_KEYBOARD, ii=Input_I(ki=ki))])

    @staticmethod
    def key_up(vk: int):
        ki = KeyboardInput(wVk=vk, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
        _send_input([Input(type=INPUT_KEYBOARD, ii=Input_I(ki=ki))])

    @staticmethod
    def tap(vk: int, delay: float = 0.01):
        Keyboard.key_down(vk)
        if delay > 0:
            time.sleep(delay)
        Keyboard.key_up(vk)

    @staticmethod
    def chord(vks: Iterable[int], press_delay: float = 0.01, release_delay: float = 0.01):
        vks_list = list(vks)
        for vk in vks_list:
            Keyboard.key_down(vk)
            if press_delay > 0:
                time.sleep(press_delay)
        for vk in reversed(vks_list):
            if release_delay > 0:
                time.sleep(release_delay)
            Keyboard.key_up(vk)

    @staticmethod
    def text_utf16(s: str, key_delay: float = 0.0):
        for ch in s:
            code = ord(ch)
            ki_down = KeyboardInput(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE, time=0, dwExtraInfo=None)
            ki_up = KeyboardInput(wVk=0, wScan=code, dwFlags=KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, time=0, dwExtraInfo=None)
            _send_input([Input(type=INPUT_KEYBOARD, ii=Input_I(ki=ki_down))])
            _send_input([Input(type=INPUT_KEYBOARD, ii=Input_I(ki=ki_up))])
            if key_delay > 0:
                time.sleep(key_delay)

# ========== 例子：連續點擊 ==========
def continuous_click(interval: float = 0.5, stop_after: Optional[float] = None):
    start = time.time()
    while True:
        Mouse.click("right", delay=0.01)
        time.sleep(interval)
        Mouse.click("left", delay=0.01)
        time.sleep(interval)
        if stop_after is not None and (time.time() - start) >= stop_after:
            break

# 自測（可刪）
# ====================================
# 1.1 update ###
GetWindowTextLengthW = user32.GetWindowTextLengthW 
SetWindowTextW = user32.SetWindowTextW 
GetWindow = user32.GetWindow 
GW_HWNDFIRST = 0 
GW_HWNDNEXT = 2 
# 取 exe 名稱
QueryFullProcessImageNameW = kernel32.QueryFullProcessImageNameW
OpenProcess = kernel32.OpenProcess
CloseHandle = kernel32.CloseHandle
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
def _get_process_image_name(pid: int) -> str:
    hProc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not hProc:
        return ""
    try:
        buf_len = wt.DWORD(260)
        buf = ctypes.create_unicode_buffer(buf_len.value)
        if QueryFullProcessImageNameW(hProc, 0, buf, ctypes.byref(buf_len)):
            path = buf.value
            # 只取檔名
            return path.split("\\")[-1]
        return ""
    finally:
        CloseHandle(hProc)
def _get_process_image_name(pid: int) -> str:
    hProc = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not hProc:
        return ""
    try:
        buf_len = wt.DWORD(260)
        buf = ctypes.create_unicode_buffer(buf_len.value)
        if QueryFullProcessImageNameW(hProc, 0, buf, ctypes.byref(buf_len)):
            path = buf.value
            # 只取檔名
            return path.split("\\")[-1]
        return ""
    finally:
        CloseHandle(hProc)

# ====== 依進程名過濾與標題重命名 ======
class WindowManager(WindowManager):  # 基於原類別追加方法
    @staticmethod
    def find_windows_advanced(
        title_equals: Optional[str] = None,
        title_contains: Optional[str] = None,
        class_equals: Optional[str] = None,
        class_contains: Optional[str] = None,
        pid: Optional[int] = None,
        process_name: Optional[str] = None,
        visible_only: bool = True,
    ) -> List["WindowInfo"]:
        def match(hwnd: int) -> bool:
            if visible_only and not WindowManager.is_visible(hwnd):
                return False
            t = WindowManager.get_window_text(hwnd)
            c = WindowManager.get_class_name(hwnd)
            p = WindowManager.get_pid(hwnd)
            if title_equals is not None and t != title_equals:
                return False
            if title_contains is not None and (t is None or title_contains not in t):
                return False
            if class_equals is not None and c != class_equals:
                return False
            if class_contains is not None and (c is None or class_contains not in c):
                return False
            if pid is not None and p != pid:
                return False
            if process_name is not None:
                exe = _get_process_image_name(p)
                if not exe or exe.lower() != process_name.lower():
                    return False
            return True

        hwnds = WindowManager.enum_windows(match)
        return [WindowManager.get_window_info(h) for h in hwnds]

    @staticmethod
    def set_window_title(hwnd: int, new_title: str) -> bool:
        return bool(SetWindowTextW(hwnd, ctypes.c_wchar_p(new_title)))

    @staticmethod
    def rename_same_title_windows(
        base_title: str,
        process_name: Optional[str] = None,
        title_contains: Optional[str] = None,
        visible_only: bool = True,
        pattern: str = "{base} [{index}]",
        start_index: int = 1,
        sort_by_hwnd: bool = True,
    ) -> List["WindowInfo"]:
        """
        將同名視窗改名為 base_title + 序號：
        - base_title: 基礎標題（通常為當前所有視窗共用的標題），可搭配 title_contains 使用
        - process_name: 僅匹配特定進程名，例如 "game.exe"
        - pattern: 樣式，支援 {base}, {index}，例："{base} [{index}]"
        - start_index: 起始編號，預設 1
        - sort_by_hwnd: 是否按 hwnd 排序（穩定且可預期），否則使用列舉順序
        回傳：成功改名後的 WindowInfo 列表（新標題已生效）
        """
        wins = WindowManager.find_windows_advanced(
            title_equals=base_title if base_title else None,
            title_contains=title_contains,
            process_name=process_name,
            visible_only=visible_only,
        )
        if not wins:
            return []

        # 排序確定序
        arr = list(wins)
        if sort_by_hwnd:
            arr.sort(key=lambda w: w.hwnd)

        # 改名
        idx = start_index
        for w in arr:
            new_title = pattern.format(base=base_title or (title_contains or ""), index=idx)
            WindowManager.set_window_title(w.hwnd, new_title)
            idx += 1

        # 回讀資訊（確認新標題）
        result = []
        for w in arr:
            info = WindowManager.get_window_info(w.hwnd)
            result.append(info)
        return result
##### 1.1 update End #####
# ====================================
if __name__ == "__main__":
    # 嘗試列出 Sandboxie 視窗（標題帶有 [#] 僅示例，請按實際關鍵字調整）
    wins = WindowManager.find_windows(title_contains="#", visible_only=True)
    print("Matched windows:")
    for w in wins:
        print(" -", w)

    # 若找到第一個視窗，嘗試前置並在其客戶區中心點擊
    if wins:
        hwnd = wins[0].hwnd
        focused = WindowManager.focus_window(hwnd)
        print("Focus:", focused)
        rc_client = WindowManager.get_client_rect(hwnd)
        cx = (rc_client.right - rc_client.left) // 2
        cy = (rc_client.bottom - rc_client.top) // 2
        Mouse.click_in_window(hwnd, cx, cy, button="left", delay=0.02, client_coords=True)
        Keyboard.text_utf16("Hello Sandboxie", key_delay=0.01)