# -*- coding: utf-8 -*-
import time
import yaml
import pathlib
import keyboard
import psutil
import re
from typing import Dict, Any, Optional, Tuple, Callable, List, Set
from action.action_dispatcher import ActionDispatcher

# 你的 GameMemory 類（reverse 64-bit 走法）
import struct
from pymem import Pymem
from pymem.process import module_from_name

# 可被 core.yaml 覆蓋
PROCESS_NAME = "game.exe"
MODULE_NAME = "game.exe"
BASE_OFFSET = 0x00016920

OFFSETS_X = [0x68, 0xD0, 0x70, 0x3C0, 0x70, 0x08, 0xC0, 0x08, 0x30, 0x20]
OFFSETS_Y = [0x70, 0xD0, 0x70, 0x3C0, 0x70, 0x08, 0xC0, 0x08, 0x30, 0x20]
# 如需與你先前版本完全一致，可改回 [0x6C, 0xD0, 0x70, 0x3C0, 0x70, 0x08, 0xC0, 0x08, 0x30, 0x20]
OFFSETS_Z = [0x6C, 0xD0, 0x70, 0x3C0, 0x70, 0x08, 0xC0, 0x08, 0x30, 0x20]

NUMPAD_CONCEPT_KEYS = [f"numpad {i}" for i in range(1, 10)]


class GameMemory:
    def __init__(self, pid: int, process_name: str = PROCESS_NAME, module_name: str = MODULE_NAME, base_offset: int = BASE_OFFSET):
        self.pid = pid
        self.process_name = process_name
        self.module_name = module_name
        self.base_offset = base_offset
        self.pm = None
        self.module_base = None
        self.addr_x = None
        self.addr_y = None
        self.addr_z = None
        self.connect()
        self.resolve_xyz()

    def connect(self):
        self.pm = Pymem()
        self.pm.open_process_from_id(self.pid)
        module = module_from_name(self.pm.process_handle, self.module_name)
        self.module_base = module.lpBaseOfDll

    def _read_ptr(self, addr: int) -> int:
        return self.pm.read_ulonglong(addr)

    def _resolve_reverse(self, base_addr: int, offsets_full) -> int:
        ptr = self._read_ptr(base_addr)
        rev = list(reversed(offsets_full))
        for i, off in enumerate(rev):
            addr = ptr + off
            if i < len(rev) - 1:
                ptr = self._read_ptr(addr)
            else:
                return addr
        raise RuntimeError("resolve failed")

    def resolve_xyz(self):
        base = self.module_base + self.base_offset
        self.addr_x = self._resolve_reverse(base, OFFSETS_X)
        self.addr_y = self._resolve_reverse(base, OFFSETS_Y)
        self.addr_z = self._resolve_reverse(base, OFFSETS_Z)
        return self.addr_x, self.addr_y, self.addr_z

    def _unpack_f(self, b: bytes) -> float:
        return struct.unpack('f', b)[0]

    def _pack_f(self, v: float) -> bytes:
        return struct.pack('f', v)

    def read_float(self, addr: int) -> float:
        return self._unpack_f(self.pm.read_bytes(addr, 4))

    def write_float(self, addr: int, v: float):
        self.pm.write_bytes(addr, self._pack_f(v), 4)

    def read_xyz(self):
        x = self.read_float(self.addr_x)
        y = self.read_float(self.addr_y)
        z = self.read_float(self.addr_z)
        return x, y, z

    def write_xyz(self, x=None, y=None, z=None):
        if x is not None:
            self.write_float(self.addr_x, x)
        if y is not None:
            self.write_float(self.addr_y, y)
        if z is not None:
            self.write_float(self.addr_z, z)

    def close(self):
        if self.pm:
            try:
                self.pm.close_process()
            except Exception:
                pass
            self.pm = None


# ========== 多進程管理（含沙盤判斷） ==========
def load_yaml(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}

def save_yaml(path: pathlib.Path, data: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")

def ensure_dirs(root: pathlib.Path):
    (root / "config").mkdir(exist_ok=True)
    (root / "config" / "maps").mkdir(parents=True, exist_ok=True)
    (root / "config" / "maps.local").mkdir(parents=True, exist_ok=True)

def pick_map_file(cfg_root: pathlib.Path) -> Optional[pathlib.Path]:
    cur_txt = cfg_root / "config" / "current_map.txt"
    if cur_txt.exists():
        name = cur_txt.read_text(encoding="utf-8").strip()
        if not name.endswith(".yaml"):
            name += ".yaml"
        p_local = cfg_root / "config" / "maps.local" / name
        p_base = cfg_root / "config" / "maps" / name
        if p_local.exists():
            return p_local
        if p_base.exists():
            return p_base
    for p in (cfg_root / "config" / "maps.local").glob("*.yaml"):
        return p
    for p in (cfg_root / "config" / "maps").glob("*.yaml"):
        return p
    return None

def is_sandboxed(proc: psutil.Process, rules: List[Dict[str, str]]) -> bool:
    try:
        exe = proc.exe() if proc.is_running() else ""
        cmd = " ".join(proc.cmdline()) if proc.is_running() else ""
        ppid = proc.ppid()
        parent = psutil.Process(ppid) if ppid else None
        parent_name = parent.name() if parent and parent.is_running() else ""
        for r in rules or []:
            t = (r.get("type") or "").lower()
            v = r.get("value") or ""
            if not v:
                continue
            if t == "module_contains":
                if v.lower() in exe.lower() or v.lower() in cmd.lower():
                    return True
            elif t == "cmdline_regex":
                if re.search(v, cmd, flags=re.IGNORECASE):
                    return True
            elif t == "parent_name_regex":
                if re.search(v, parent_name or "", flags=re.IGNORECASE):
                    return True
            elif t == "exe_regex":
                if re.search(v, exe or "", flags=re.IGNORECASE):
                    return True
    except Exception:
        pass
    return False

class MultiGameManager:
    def __init__(self, process_name: str, module_name: str, base_offset: int, attach_mode: str, sandbox_rules: List[Dict[str, str]]):
        self.process_name = process_name
        self.module_name = module_name
        self.base_offset = base_offset
        self.attach_mode = (attach_mode or "all").lower()
        self.sandbox_rules = sandbox_rules or []
        self.instances: Dict[int, GameMemory] = {}

    def scan_and_attach(self):
        seen_pids: Set[int] = set()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if not proc.is_running():
                    continue
                if (proc.info.get("name") or "").lower() != self.process_name.lower():
                    continue
                sb = is_sandboxed(proc, self.sandbox_rules)
                if self.attach_mode == "only_outside" and sb:
                    continue
                if self.attach_mode == "only_sandbox" and not sb:
                    continue
                pid = proc.pid
                seen_pids.add(pid)
                if pid not in self.instances:
                    try:
                        gm = GameMemory(pid, self.process_name, self.module_name, self.base_offset)
                        self.instances[pid] = gm
                        print(f"[attach] pid={pid} attached (sandboxed={sb})")
                    except Exception as e:
                        print(f"[attach-fail] pid={pid}: {e}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        gone = [pid for pid in list(self.instances.keys()) if pid not in seen_pids]
        for pid in gone:
            try:
                self.instances[pid].close()
            except Exception:
                pass
            del self.instances[pid]
            print(f"[detach] pid={pid} removed")

    def close_all(self):
        for pid, gm in list(self.instances.items()):
            try:
                gm.close()
            except Exception:
                pass
        self.instances.clear()

    def write_xyz_all(self, x=None, y=None, z=None):
        for pid, gm in list(self.instances.items()):
            try:
                gm.write_xyz(x=x, y=y, z=z)
            except Exception as e:
                print(f"[write-fail] pid={pid}: {e}")

    def read_xyz_first(self):
        for pid, gm in self.instances.items():
            try:
                return gm.read_xyz()
            except Exception:
                continue
        return None

# --------------- 綁定與掃描碼 ---------------
def normalize_action(a: Dict[str, Any]) -> Dict[str, Any]:
    if "type" not in a:
        a = {"type": "teleport", **a}
    return a

def build_hotkey_bindings(map_cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mode = (map_cfg.get("mode") or "per_hotkey").lower()
    bindings: Dict[str, Dict[str, Any]] = {}
    if mode == "per_hotkey":
        hks = map_cfg.get("hotkeys", {})
        for k, v in hks.items():
            bindings[str(k)] = normalize_action(v)
    elif mode == "route":
        routes = map_cfg.get("routes", {})
        for k, r in routes.items():
            r = dict(r or {})
            wps = r.get("waypoints", [])  # 向後兼容
            bindings[str(k)] = {
                "type": "path",
                "waypoints": wps,
                "delay_ms": r.get("delay_ms", 150),
                "advance": (r.get("advance") or "one_step").lower(),
                "loop": bool(r.get("loop", True)),
                "reset_hotkey": (r.get("reset_hotkey") or "").strip().lower() or None,
                "steps": r.get("steps", None),  # 傳遞 steps 供 RouteStateManager 使用
            }
    else:
        raise ValueError(f"Unknown mode: {mode}")
    return bindings

def load_scancodes(path: pathlib.Path) -> Dict[str, int]:
    data = load_yaml(path)
    out = {}
    for k, v in (data or {}).items():
        try:
            out[str(k).lower()] = int(v)
        except Exception:
            pass
    return out

def learn_scancodes_interactive(dst_path: pathlib.Path) -> Dict[str, int]:
    print("掃描碼學習模式：請依提示按下小鍵盤鍵（確保 Num Lock 開啟）。按 ESC 可中斷。")
    learned: Dict[str, int] = {}
    order = NUMPAD_CONCEPT_KEYS
    for label in order:
        print(f"請按下：{label} ...")
        while True:
            e = keyboard.read_event()
            if e.event_type != keyboard.KEY_DOWN:
                continue
            if e.name == "esc":
                print("已中斷學習。")
                save_yaml(dst_path, learned)
                return learned
            sc = e.scan_code
            print(f"  捕捉到鍵: name={e.name!r}, scan_code={sc}")
            learned[label] = sc
            time.sleep(0.2)
            break
    save_yaml(dst_path, learned)
    print(f"學習完成，已寫入 {dst_path}")
    return learned

class ScanCodeHotkeyManager:
    def __init__(self):
        self.handlers: Dict[int, Callable[[], None]] = {}
        self._hook = None
        self._pressed_block = set()

    def bind(self, scan_code: int, callback: Callable[[], None]):
        self.handlers[scan_code] = callback

    def start(self):
        if self._hook:
            return
        def _on_event(e: keyboard.KeyboardEvent):
            if e.event_type != keyboard.KEY_DOWN:
                if e.event_type == keyboard.KEY_UP and e.scan_code in self._pressed_block:
                    self._pressed_block.discard(e.scan_code)
                return
            sc = e.scan_code
            cb = self.handlers.get(sc)
            if cb:
                if sc in self._pressed_block:
                    return
                self._pressed_block.add(sc)
                try:
                    cb()
                finally:
                    pass
        self._hook = keyboard.hook(_on_event)

    def stop(self):
        if self._hook:
            keyboard.unhook(self._hook)
            self._hook = None
        self.handlers.clear()
        self._pressed_block.clear()

def try_bind_hotkey(hk_label: str, callback: Callable[[], None], scancodes: Dict[str, int], sc_mgr: ScanCodeHotkeyManager) -> Tuple[bool, str]:
    label_l = hk_label.lower().strip()
    if label_l in scancodes:
        sc = scancodes[label_l]
        try:
            sc_mgr.bind(sc, callback)
            return True, f"scan_code={sc}"
        except Exception as e:
            return False, f"scan_code={sc} 綁定失敗: {e}"
    try:
        keyboard.add_hotkey(label_l, callback)
        return True, f"name={label_l}"
    except Exception as e:
        return False, f"name={label_l} 綁定失敗: {e}"

# --------------- 路線狀態（單步/全跑） ---------------
class RouteStateManager:
    def __init__(self, mgm: 'MultiGameManager', dispatcher: ActionDispatcher):
        self.mgm = mgm
        self.dispatcher = dispatcher
        self.state: Dict[str, Dict[str, Any]] = {}

    def register_route(self, key_label: str, cfg: Dict[str, Any]):
        steps = []
        if cfg.get("steps"):
            for st in cfg["steps"]:
                st = dict(st or {})
                if "waypoint" in st:
                    wp = st["waypoint"]
                    steps.append({"kind": "wp", "wp": wp, "delay_ms": int(st.get("delay_ms", cfg.get("delay_ms", 150)))})
                elif "action" in st:
                    steps.append({"kind": "act", "act": st["action"]})
        else:
            wps = list(cfg.get("waypoints") or [])
            for wp in wps:
                steps.append({"kind": "wp", "wp": wp, "delay_ms": int(cfg.get("delay_ms", 150))})

        self.state[key_label] = {
            "i": 0,
            "steps": steps,
            "advance": (cfg.get("advance") or "one_step").lower(),
            "loop": bool(cfg.get("loop", True)),
        }

    def trigger(self, key_label: str):
        st = self.state.get(key_label)
        if not st:
            return
        steps = st["steps"]
        if not steps:
            return

        adv = st["advance"]
        if adv == "one_step":
            i = st["i"]
            if i >= len(steps):
                if st["loop"]:
                    i = 0
                else:
                    print(f"{key_label}: 已到路線終點（loop=false）。")
                    return
            step = steps[i]
            self._run_step(step)
            st["i"] = (i + 1) if (i + 1) < len(steps) else (0 if st["loop"] else len(steps))
        else:
            for step in steps:
                self._run_step(step)
            st["i"] = 0

    def _run_step(self, step: Dict[str, Any]):
        if step["kind"] == "wp":
            wp = step["wp"]
            self.mgm.write_xyz_all(x=float(wp["x"]), y=float(wp["y"]), z=float(wp["z"]))
            d = float(step.get("delay_ms", 150)) / 1000.0
            if d > 0:
                time.sleep(d)
        elif step["kind"] == "act":
            self.dispatcher.run_action(step["act"])

    def reset(self, key_label: str):
        st = self.state.get(key_label)
        if st:
            st["i"] = 0
            print(f"{key_label}: 已重置到第一步。")

# --------------- 主流程 ---------------
def main():
    root = pathlib.Path(__file__).parent
    ensure_dirs(root)

    detect_flag = (root / "config" / "key_detect.txt").exists()
    learn_flag = (root / "config" / "learn_scancodes.txt").exists()

    if detect_flag and not learn_flag:
        print("鍵名探測模式：按下任意鍵查看名稱與掃描碼（按 ESC 結束）。")
        try:
            while True:
                e = keyboard.read_event()
                if e.event_type == keyboard.KEY_DOWN:
                    print(f"name={e.name!r}, scan_code={e.scan_code}")
                    if e.name == "esc":
                        break
        except KeyboardInterrupt:
            pass
        return

    sc_path = root / "config" / "scancodes.yaml"
    scancodes = load_scancodes(sc_path)

    if learn_flag:
        scancodes = learn_scancodes_interactive(sc_path)
        print("學習完成，將使用新掃描碼綁定熱鍵。")

    core = load_yaml(root / "config" / "core.yaml")
    global PROCESS_NAME, MODULE_NAME, BASE_OFFSET, OFFSETS_X, OFFSETS_Y, OFFSETS_Z
    PROCESS_NAME = core.get("process", {}).get("name", PROCESS_NAME)
    MODULE_NAME = core.get("process", {}).get("module", MODULE_NAME)
    if core.get("memory"):
        base_off = core["memory"].get("base_offset", BASE_OFFSET)
        BASE_OFFSET = int(str(base_off), 0)
        offs = core["memory"].get("offsets", {})
        if offs.get("x"): OFFSETS_X = [int(str(v), 0) for v in offs["x"]]
        if offs.get("y"): OFFSETS_Y = [int(str(v), 0) for v in offs["y"]]
        if offs.get("z"): OFFSETS_Z = [int(str(v), 0) for v in offs["z"]]
    attach_cfg = core.get("attach", {}) or {}
    attach_mode = attach_cfg.get("mode", "all")
    sandbox_rules = attach_cfg.get("sandbox_rules", [])
    refresh_ms = int(attach_cfg.get("refresh_ms", 0))

    map_file = pick_map_file(root)
    if not map_file:
        print("找不到任何地圖配置檔，請先用 gen_config.py 生成。")
        return
    map_cfg = load_yaml(map_file)
    bindings = build_hotkey_bindings(map_cfg)

    print(f"使用地圖檔: {map_file.name}")

    # 正確初始化順序：mgm -> dispatcher -> route_mgr
    mgm = MultiGameManager(PROCESS_NAME, MODULE_NAME, BASE_OFFSET, attach_mode, sandbox_rules)
    mgm.scan_and_attach()

    dispatcher = ActionDispatcher(mgm)
    sc_mgr = ScanCodeHotkeyManager()
    route_mgr = RouteStateManager(mgm, dispatcher)

    any_bound = False
    failed: Dict[str, str] = {}
    print("綁定熱鍵:")

    # 初始化 routes
    reset_map: Dict[str, str] = {}
    for hk, act in bindings.items():
        if act["type"] == "path":
            route_mgr.register_route(hk, act)

    # 建立回呼
    def make_tp_cb(act: Dict[str, Any]):
        return lambda: mgm.write_xyz_all(x=float(act["x"]), y=float(act["y"]), z=float(act["z"]))

    def make_offset_cb(act: Dict[str, Any]):
        def _cb():
            cur = mgm.read_xyz_first()
            if cur is None:
                return
            x, y, z = cur
            mgm.write_xyz_all(
                x=x + float(act.get("dx", 0.0)),
                y=y + float(act.get("dy", 0.0)),
                z=z + float(act.get("dz", 0.0)),
            )
        return _cb

    def make_route_cb(label: str):
        return lambda: route_mgr.trigger(label)

    # 綁定
    for hk, act in bindings.items():
        t = (act.get("type") or "").lower()
        if t in ("teleport", "offset"):
            if t == "teleport":
                ok, info = try_bind_hotkey(hk, make_tp_cb(act), scancodes, sc_mgr)
            else:
                ok, info = try_bind_hotkey(hk, make_offset_cb(act), scancodes, sc_mgr)
        elif t in ("key_tap", "key_chord", "text", "mouse_click", "mouse_click_in_window", "focus_window"):
            ok, info = try_bind_hotkey(hk, lambda a=act: dispatcher.run_action(a), scancodes, sc_mgr)
        elif t == "path":
            ok, info = try_bind_hotkey(hk, make_route_cb(hk), scancodes, sc_mgr)
            rh = act.get("reset_hotkey")
            if rh:
                reset_map[rh] = hk
        else:
            ok, info = False, f"Unknown action type: {act.get('type')}"
        if ok:
            print(f" - {hk} -> {info}: {act['type']}")
            any_bound = True
        else:
            print(f" - {hk} 綁定失敗：{info}")
            failed[hk] = info

    # 綁定 reset_hotkey
    for rh_name, route_label in reset_map.items():
        ok, info = try_bind_hotkey(rh_name, lambda lbl=route_label: route_mgr.reset(lbl), scancodes, sc_mgr)
        if ok:
            print(f" - reset {route_label} -> {info}")
            any_bound = True
        else:
            print(f" - reset_hotkey {rh_name} 綁定失敗：{info}")
            failed[f"reset:{route_label}"] = info

    if any_bound and scancodes:
        sc_mgr.start()

    if not mgm.instances:
        print(f"[警告] 目前未附加到任何 {PROCESS_NAME} 實例。請確保程式已啟動，或調整 attach.mode/sandbox_rules 後重試。")

    if not any_bound:
        print("尚未成功綁定任何熱鍵。")

    last_scan = time.time()
    print("熱鍵已就緒，按 ESC 退出。")
    while True:
        if refresh_ms > 0 and (time.time() - last_scan) * 1000 >= refresh_ms:
            mgm.scan_and_attach()
            last_scan = time.time()
        if keyboard.is_pressed("esc"):
            break
        time.sleep(0.05)

    sc_mgr.stop()
    mgm.close_all()

if __name__ == "__main__":
    main()
