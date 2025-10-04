# -*- coding: utf-8 -*-
import time
from typing import Any, Dict, List, Optional

from .input_controller import WindowManager, Mouse, Keyboard, VK


def _ms(v: Optional[int], default_ms: int = 10) -> float:
    """毫秒轉秒，若 v 無效則用 default_ms。"""
    return float(v if isinstance(v, (int, float)) else default_ms) / 1000.0


def _find_window(find: Dict[str, Any]) -> Optional[int]:
    """依條件尋找視窗，回傳 hwnd 或 None。"""
    if not find:
        return None
    title_equals = find.get("title_equals")
    title_contains = find.get("title_contains")
    class_equals = find.get("class_equals")
    class_contains = find.get("class_contains")
    pid = find.get("pid")
    visible_only = bool(find.get("visible_only", True))
    wins = WindowManager.find_windows(
        title_equals=title_equals,
        title_contains=title_contains,
        class_equals=class_equals,
        class_contains=class_contains,
        pid=pid,
        visible_only=visible_only,
    )
    return wins[0].hwnd if wins else None


def _vk_from_name(name: str) -> int:
    key = str(name).upper()
    if key in VK:
        return VK[key]
    raise ValueError(f"未知虛擬鍵名 {name}")


class ActionDispatcher:
    def __init__(self, mgm):
        self.mgm = mgm  # MultiGameManager

    # 單一 action 執行
    def run_action(self, act: Dict[str, Any]):
        t = (act.get("type") or "").lower()
        if not t:
            return

        if t == "teleport":
            self._act_teleport(act)
        elif t == "offset":
            self._act_offset(act)
        elif t == "key_tap":
            self._act_key_tap(act)
        elif t == "key_chord":
            self._act_key_chord(act)
        elif t == "text":
            self._act_text(act)
        elif t == "mouse_click":
            self._act_mouse_click(act)
        elif t == "mouse_click_in_window":
            self._act_mouse_click_in_window(act)
        elif t == "focus_window":
            self._act_focus_window(act)
        elif t == "route_trigger":
            # 建議在 main.py 外層注入回呼；此處留白即可
            pass
        else:
            print(f"[warn] 未知 action.type {t}")

    # 具體行為
    def _act_teleport(self, a: Dict[str, Any]):
        x = float(a["x"])
        y = float(a["y"])
        z = float(a["z"])
        self.mgm.write_xyz_all(x=x, y=y, z=z)

    def _act_offset(self, a: Dict[str, Any]):
        cur = self.mgm.read_xyz_first()
        if cur is None:
            return
        x, y, z = cur
        dx = float(a.get("dx", 0.0))
        dy = float(a.get("dy", 0.0))
        dz = float(a.get("dz", 0.0))
        self.mgm.write_xyz_all(x=x + dx, y=y + dy, z=z + dz)

    def _act_key_tap(self, a: Dict[str, Any]):
        vk = _vk_from_name(a["vk"])
        delay = _ms(a.get("delay_ms"), 10)
        Keyboard.tap(vk, delay)

    def _act_key_chord(self, a: Dict[str, Any]):
        vks = a.get("vks") or []
        if not vks:
            return
        vks_num = [_vk_from_name(v) for v in vks]
        p = _ms(a.get("press_delay_ms"), 10)
        r = _ms(a.get("release_delay_ms"), 10)
        Keyboard.chord(vks_num, press_delay=p, release_delay=r)

    def _act_text(self, a: Dict[str, Any]):
        s = str(a.get("value") or "")
        kd = _ms(a.get("key_delay_ms"), 0)
        Keyboard.text_utf16(s, key_delay=kd)

    def _act_mouse_click(self, a: Dict[str, Any]):
        btn = str(a.get("button", "left")).lower()
        at = a.get("at")  # {screen: [x,y]} 或 {relative: [dx,dy]}
        d = _ms(a.get("delay_ms"), 10)
        if isinstance(at, dict) and "screen" in at:
            x, y = at["screen"]
            Mouse.click_at(int(x), int(y), button=btn, delay=d)
        elif isinstance(at, dict) and "relative" in at:
            dx, dy = at["relative"]
            Mouse.click_relative(int(dx), int(dy), button=btn, delay=d)
        else:
            # 沒有座標就直接點擊當前位置
            Mouse.click(button=btn, delay=d)

    def _act_mouse_click_in_window(self, a: Dict[str, Any]):
        btn = str(a.get("button", "left")).lower()
        d = _ms(a.get("delay_ms"), 10)
        find = a.get("find") or {}
        hwnd = _find_window(find)
        if not hwnd:
            print("[warn] 未找到匹配視窗 (mouse_click_in_window)")
            return
        client = a.get("client")
        if not client or len(client) < 2:
            print("[warn] 缺少 client 座標")
            return
        cx, cy = int(client[0]), int(client[1])
        Mouse.click_in_window(hwnd, cx, cy, button=btn, delay=d, client_coords=True)

    def _act_focus_window(self, a: Dict[str, Any]):
        find = a.get("find") or {}
        hwnd = _find_window(find)
        if not hwnd:
            print("[warn] 未找到匹配視窗 (focus_window)")
            return
        timeout = _ms(a.get("timeout_ms"), 800)
        ok = WindowManager.focus_window(hwnd, timeout=timeout)
        if not ok:
            print("[warn] 視窗前置失敗")