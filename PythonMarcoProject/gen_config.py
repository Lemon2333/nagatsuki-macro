# gen_config.py
# -*- coding: utf-8 -*-
import pathlib
import yaml
import re

def ensure_dirs(root: pathlib.Path):
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "maps").mkdir(parents=True, exist_ok=True)
    (root / "config" / "maps.local").mkdir(parents=True, exist_ok=True)

def sanitize_filename(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9-_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "map"

def ask(prompt: str, default=None):
    if default is not None:
        v = input(f"{prompt} [{default}]: ").strip()
        return v if v else default
    return input(f"{prompt}: ").strip()

def ask_int(prompt: str, default=None) -> int:
    while True:
        v = ask(prompt, None if default is None else str(default))
        try:
            return int(v)
        except Exception:
            print("請輸入整數。")

def ask_float(prompt: str, default=None) -> float:
    while True:
        v = ask(prompt, None if default is None else str(default))
        try:
            return float(v)
        except Exception:
            print("請輸入數值。")

def ask_yesno(prompt: str, default=False) -> bool:
    d = "Y/n" if default else "y/N"
    v = ask(f"{prompt} ({d})", "").strip().lower()
    if not v:
        return default
    return v in ("y", "yes", "1", "true", "t")

def select_mode() -> str:
    while True:
        v = ask("選擇模式 (1=per_hotkey, 2=route)", "1")
        if v in ("1", "per_hotkey"):
            return "per_hotkey"
        if v in ("2", "route"):
            return "route"
        print("無效選擇。")

def list_hotkeys_default():
    # 預設使用概念鍵名 numpad 1 ~ numpad 9（實際綁定用掃描碼）
    return [f"numpad {i}" for i in range(1, 10)]

# ========== Actions 建構器 ==========
def build_action_key_tap():
    vk = ask("  虛擬鍵名 VK（例：F8、CONTROL、A）", "F8").upper()
    delay = ask_int("  按下與釋放間延遲 (ms)", 10)
    return {"type": "key_tap", "vk": vk, "delay_ms": delay}

def build_action_key_chord():
    print("  鍵名以逗號分隔，例如：CONTROL,SHIFT,ESCAPE 或 CONTROL,N")
    vks = [s.strip().upper() for s in ask("  鍵名列表", "CONTROL,SHIFT,ESCAPE").split(",") if s.strip()]
    press_d = ask_int("  逐鍵按下間延遲 (ms)", 10)
    release_d = ask_int("  逐鍵釋放間延遲 (ms)", 10)
    return {"type": "key_chord", "vks": vks, "press_delay_ms": press_d, "release_delay_ms": release_d}

def build_action_text():
    val = ask("  要輸入的文字", "你好，世界")
    kd = ask_int("  每字元間延遲 (ms，0為無)", 0)
    return {"type": "text", "value": val, "key_delay_ms": kd}

def build_action_mouse_click():
    btn = ask("  滑鼠按鍵 (left/right/middle)", "left").lower()
    coord_mode = ask("  座標模式 (1=screen, 2=relative, 3=current)", "1")
    delay = ask_int("  按下與釋放間延遲 (ms)", 10)
    act = {"type": "mouse_click", "button": btn, "delay_ms": delay}
    if coord_mode in ("1", "screen"):
        x = ask_int("    螢幕座標 x", 800)
        y = ask_int("    螢幕座標 y", 450)
        act["at"] = {"screen": [x, y]}
    elif coord_mode in ("2", "relative"):
        dx = ask_int("    相對偏移 dx", 0)
        dy = ask_int("    相對偏移 dy", 0)
        act["at"] = {"relative": [dx, dy]}
    else:
        # current 位置，無額外座標
        pass
    return act

def build_action_find_block() -> dict:
    print("  視窗查找條件（可留空任何一項）")
    tc = ask("    title_contains", "")
    te = ask("    title_equals", "")
    cc = ask("    class_contains", "")
    ce = ask("    class_equals", "")
    pid = ask("    pid (整數，可空)", "")
    vo = ask("    visible_only (true/false，可空)", "true")
    find = {}
    if tc: find["title_contains"] = tc
    if te: find["title_equals"] = te
    if cc: find["class_contains"] = cc
    if ce: find["class_equals"] = ce
    if pid.strip().isdigit(): find["pid"] = int(pid.strip())
    if vo.lower() in ("false", "0", "no", "n"):
        find["visible_only"] = False
    return find

def build_action_focus_window():
    find = build_action_find_block()
    t = ask_int("  超時 (ms)", 800)
    return {"type": "focus_window", "find": find, "timeout_ms": t}

def build_action_mouse_click_in_window():
    find = build_action_find_block()
    cx = ask_int("  客戶區 x", 100)
    cy = ask_int("  客戶區 y", 50)
    btn = ask("  滑鼠按鍵 (left/right/middle)", "left").lower()
    delay = ask_int("  按下與釋放間延遲 (ms)", 10)
    return {"type": "mouse_click_in_window", "find": find, "client": [cx, cy], "button": btn, "delay_ms": delay}

def select_action_type() -> str:
    items = [
        ("1", "key_tap"), ("2", "key_chord"), ("3", "text"),
        ("4", "mouse_click"), ("5", "mouse_click_in_window"), ("6", "focus_window")
    ]
    print("可選動作類型：")
    for k, name in items:
        print(f"  {k}) {name}")
    while True:
        v = ask("選擇動作類型", "4")
        for k, name in items:
            if v == k or v == name:
                return name
        print("無效選擇。")

def build_one_action():
    t = select_action_type()
    if t == "key_tap":
        return build_action_key_tap()
    if t == "key_chord":
        return build_action_key_chord()
    if t == "text":
        return build_action_text()
    if t == "mouse_click":
        return build_action_mouse_click()
    if t == "mouse_click_in_window":
        return build_action_mouse_click_in_window()
    if t == "focus_window":
        return build_action_focus_window()
    raise ValueError("未知動作類型")

# ========== per_hotkey ==========
def create_per_hotkey():
    hotkeys = {}
    print("建立 per_hotkey 設定。可為熱鍵指定下列任一：teleport / offset / action（鍵鼠/視窗）。")
    while True:
        k = ask("輸入熱鍵（例如 numpad 1，留空結束）", "")
        if not k:
            break
        k = " ".join(k.strip().lower().split())
        kind = ask("  類型 (1=teleport, 2=offset, 3=action)", "1")
        if kind in ("1", "teleport"):
            x = ask_float("    x")
            y = ask_float("    y")
            z = ask_float("    z")
            hotkeys[k] = {"type": "teleport", "x": x, "y": y, "z": z}
        elif kind in ("2", "offset"):
            dx = ask_float("    dx", 0.0)
            dy = ask_float("    dy", 0.0)
            dz = ask_float("    dz", 0.0)
            hotkeys[k] = {"type": "offset", "dx": dx, "dy": dy, "dz": dz}
        else:
            act = build_one_action()
            hotkeys[k] = act
    return {"mode": "per_hotkey", "hotkeys": hotkeys}

# ========== route ==========
def create_route_waypoints() -> dict:
    routes = {}
    print("建立 route（傳統 waypoints 版本）。")
    while True:
        k = ask("  熱鍵（例如 numpad 1，留空結束）", "")
        if not k:
            break
        k = " ".join(k.strip().lower().split())
        waypoints = []
        while True:
            add = ask("    新增 waypoint? (y/N)", "N").lower()
            if add != "y":
                break
            x = ask_float("      x")
            y = ask_float("      y")
            z = ask_float("      z")
            waypoints.append({"x": x, "y": y, "z": z})
        if not waypoints:
            print("    未新增節點，略過該熱鍵。")
            continue
        delay = ask_int("    節點間延遲毫秒", 150)
        advance = ask("    前進方式 one_step/all", "one_step").lower()
        loop = ask_yesno("    是否迴圈 loop", True)
        rh = ask("    reset_hotkey（可空）", "").strip().lower() or None
        routes[k] = {
            "waypoints": waypoints,
            "delay_ms": delay,
            "advance": advance,
            "loop": loop,
            "reset_hotkey": rh,
        }
    return {"mode": "route", "routes": routes}

def create_route_steps() -> dict:
    routes = {}
    print("建立 route（steps 混合 waypoint/action 版本）。")
    while True:
        k = ask("  熱鍵（例如 numpad 1，留空結束）", "")
        if not k:
            break
        k = " ".join(k.strip().lower().split())
        steps = []
        while True:
            what = ask("    新增 (1=waypoint, 2=action, Enter 結束此路線)", "")
            if not what:
                break
            if what in ("1", "waypoint", "wp"):
                x = ask_float("      x")
                y = ask_float("      y")
                z = ask_float("      z")
                d = ask_int("      之後延遲 (ms)", 150)
                steps.append({"waypoint": {"x": x, "y": y, "z": z}, "delay_ms": d})
            else:
                act = build_one_action()
                steps.append({"action": act})
        if not steps:
            print("    未新增步驟，略過該熱鍵。")
            continue
        advance = ask("    前進方式 one_step/all", "one_step").lower()
        loop = ask_yesno("    是否迴圈 loop", True)
        rh = ask("    reset_hotkey（可空）", "").strip().lower() or None
        default_delay = ask_int("    預設延遲 (ms, 給未指定延遲的 waypoint 用)", 150)
        routes[k] = {
            "steps": steps,
            "delay_ms": default_delay,
            "advance": advance,
            "loop": loop,
            "reset_hotkey": rh,
        }
    return {"mode": "route", "routes": routes}

def create_route():
    mode = ask("Route 風格 (1=waypoints 傳統, 2=steps 混合)", "2")
    if mode in ("1", "waypoints"):
        return create_route_waypoints()
    return create_route_steps()

# ========== 主入口 ==========
def main():
    root = pathlib.Path(__file__).parent
    ensure_dirs(root)

    name = ask("輸入地圖名稱（做為檔名）")
    fname = sanitize_filename(name) + ".yaml"
    key_default = sanitize_filename(name)
    key = ask("地圖 key（可留空自動用檔名）", key_default)

    mode = select_mode()
    if mode == "per_hotkey":
        body = create_per_hotkey()
    else:
        body = create_route()

    # 兼容你現有主程式可能使用的字段
    default_scheme = ask("方案名稱（預設 default）", "default")

    data = {
        "key": key,
        "default_scheme": default_scheme,
    }

    if mode == "per_hotkey":
        data["mode"] = "per_hotkey"
        data["hotkeys"] = body["hotkeys"]
    else:
        data["mode"] = "route"
        data["routes"] = body["routes"]

    # 保存到 maps.local
    dst = root / "config" / "maps.local" / fname
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
    print(f"已寫入 {dst}")

    # 指定為當前地圖
    (root / "config" / "current_map.txt").write_text(dst.name, encoding="utf-8")
    print("已更新 config/current_map.txt 指向該檔案。")

    print("\n下一步建議：")
    print("  1) 在 config/ 建立一個空檔 learn_scancodes.txt（如需掃描碼綁定）")
    print("  2) 執行 python main.py，依指示按 numpad 1~9 完成學習（或直接用鍵名綁定）")
    print("  3) 刪除 learn_scancodes.txt 後再執行，優先使用掃描碼綁定（可與上排數字區分）")

if __name__ == "__main__":
    main()