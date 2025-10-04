import struct
from pymem import Pymem
from pymem.process import module_from_name

PROCESS_NAME = "game.exe"
MODULE_NAME = "game.exe"
BASE_OFFSET = 0x16920

# 全 10 個偏移，含最終字段偏移（X/Y/Z 各不同第一個數）
OFFSETS_X = [0x68, 0xD0, 0x70, 0x3C0, 0x70, 0x08, 0xC0, 0x08, 0x30, 0x20]
OFFSETS_Y = [0x70, 0xD0, 0x70, 0x3C0, 0x70, 0x08, 0xC0, 0x08, 0x30, 0x20]
OFFSETS_Z = [0x6C, 0xD0, 0x70, 0x3C0, 0x70, 0x08, 0xC0, 0x08, 0x30, 0x20]

def resolve(pm, base_addr, offsets):
    # 先讀一次 base 指針
    ptr = pm.read_ulonglong(base_addr)
    # 逆序走：把 offsets 反過來；每步先加偏移再讀指針，最後一層只加偏移不再讀
    # 這種方式要和 CE 的實際鏈條一致，否則會錯。
    for i, off in enumerate(reversed(offsets)):
        addr = ptr + off
        if i < len(offsets) - 1:
            ptr = pm.read_ulonglong(addr)
        else:
            ptr = addr
    return ptr

def read_float(pm, addr):
    import struct
    return struct.unpack('f', pm.read_bytes(addr, 4))[0]

def main():
    pm = Pymem(PROCESS_NAME)
    module = module_from_name(pm.process_handle, MODULE_NAME)
    base = module.lpBaseOfDll + BASE_OFFSET

    addr_x = resolve(pm, base, OFFSETS_X)
    addr_y = resolve(pm, base, OFFSETS_Y)
    addr_z = resolve(pm, base, OFFSETS_Z)

    print(read_float(pm, addr_x), read_float(pm, addr_y), read_float(pm, addr_z))

if __name__ == "__main__":
    main()