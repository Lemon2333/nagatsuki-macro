import struct
from typing import Tuple, Optional

from pymem import Pymem
from pymem.process import module_from_name

PROCESS_NAME = "game.exe"
MODULE_NAME = "game.exe"
BASE_OFFSET = 0x00016920  # 保留前導零也沒關係

# 你的 CT：全 10 個偏移（含最終字段偏移）
OFFSETS_X = [0x68, 0xD0, 0x70, 0x3C0, 0x70, 0x08, 0xC0, 0x08, 0x30, 0x20]
OFFSETS_Y = [0x70, 0xD0, 0x70, 0x3C0, 0x70, 0x08, 0xC0, 0x08, 0x30, 0x20]
OFFSETS_Z = [0x6C, 0xD0, 0x70, 0x3C0, 0x70, 0x08, 0xC0, 0x08, 0x30, 0x20]

class OnigiriMemoryCoordinate:
    """
    使用 reverse 走法解析指標鏈（64 位）：
      ptr = read_ptr(base)
      for off in reversed(offsets_full):
          addr = ptr + off
          若不是最後一步：ptr = read_ptr(addr)
          最後一步：結果即 addr
    """

    def __init__(self,
                 process_name: str = PROCESS_NAME,
                 module_name: str = MODULE_NAME,
                 base_offset: int = BASE_OFFSET):
        self.process_name = process_name
        self.module_name = module_name
        self.base_offset = base_offset

        self.pm: Optional[Pymem] = None
        self.module_base: Optional[int] = None

        self.addr_x: Optional[int] = None
        self.addr_y: Optional[int] = None
        self.addr_z: Optional[int] = None

        self.connect()
        self.resolve_xyz()

    def connect(self):
        self.pm = Pymem(self.process_name)
        module = module_from_name(self.pm.process_handle, self.module_name)
        self.module_base = module.lpBaseOfDll

    # 64 位指針
    def _read_ptr(self, addr: int) -> int:
        return self.pm.read_ulonglong(addr)  # type: ignore[union-attr]

    def _resolve_reverse(self, base_addr: int, offsets_full) -> int:
        ptr = self._read_ptr(base_addr)
        rev = list(reversed(offsets_full))
        for i, off in enumerate(rev):
            addr = ptr + off
            if i < len(rev) - 1:
                ptr = self._read_ptr(addr)
            else:
                return addr
        raise RuntimeError("resolve failed unexpectedly")

    def resolve_xyz(self):
        base = self.module_base + self.base_offset  # type: ignore[operator]
        self.addr_x = self._resolve_reverse(base, OFFSETS_X)
        self.addr_y = self._resolve_reverse(base, OFFSETS_Y)
        self.addr_z = self._resolve_reverse(base, OFFSETS_Z)
        return self.addr_x, self.addr_y, self.addr_z

    @staticmethod
    def _unpack_f(b: bytes) -> float:
        return struct.unpack('f', b)[0]

    @staticmethod
    def _pack_f(v: float) -> bytes:
        return struct.pack('f', v)

    def read_float(self, addr: int) -> float:
        return self._unpack_f(self.pm.read_bytes(addr, 4))  # type: ignore[union-attr]

    def write_float(self, addr: int, v: float):
        self.pm.write_bytes(addr, self._pack_f(v), 4)  # type: ignore[union-attr]

    def read_xyz(self) -> Tuple[float, float, float]:
        if None in (self.addr_x, self.addr_y, self.addr_z):
            self.resolve_xyz()
        x = self.read_float(self.addr_x)  # type: ignore[arg-type]
        y = self.read_float(self.addr_y)  # type: ignore[arg-type]
        z = self.read_float(self.addr_z)  # type: ignore[arg-type]
        return x, y, z

    def write_xyz(self, x: Optional[float] = None, y: Optional[float] = None, z: Optional[float] = None):
        if x is not None:
            self.write_float(self.addr_x, x)  # type: ignore[arg-type]
        if y is not None:
            self.write_float(self.addr_y, y)  # type: ignore[arg-type]
        if z is not None:
            self.write_float(self.addr_z, z)  # type: ignore[arg-type]

    def close(self):
        if self.pm:
            try:
                self.pm.close_process()
            except Exception:
                pass
            self.pm = None


if __name__ == "__main__":
    gm = OnigiriMemoryCoordinate()
    print("Addresses:", hex(gm.addr_x or 0), hex(gm.addr_y or 0), hex(gm.addr_z or 0))
    print("XYZ:", gm.read_xyz())