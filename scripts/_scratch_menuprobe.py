# -*- coding: utf-8 -*-
"""Watch menu state: 0x12B64 selection, int90, slot3, MCB names."""
import ctypes
import sys

sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
from dosbox_rd import get_pid, find_base

k32 = ctypes.windll.kernel32


def state():
    pid = get_pid()
    h = k32.OpenProcess(0x410, False, pid)
    B = find_base(h)

    def rd(a, n):
        b = ctypes.create_string_buffer(n)
        g = ctypes.c_size_t(0)
        r = k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g))
        return b.raw[:g.value] if r else None

    v90 = int.from_bytes(rd(B + 0x240, 4), 'little')
    sel = None
    v = rd(B + 0x12B64, 1)
    if v:
        sel = v[0]
    res = rd(B + 0x043D * 0x10 + 0x100, 0x200)
    slot3 = res[0x14C:0x15B] if res else b''
    mods = []
    s = 0x43C
    for _ in range(8):
        m = rd(B + s * 0x10, 16)
        if not m or chr(m[0]) not in 'MZ':
            break
        size = int.from_bytes(m[3:5], 'little')
        owner = int.from_bytes(m[5:7], 'little')
        nm = m[8:16].split(b'\x00')[0]
        if nm:
            mods.append('%04X:%r' % (owner, nm))
        if chr(m[0]) == 'Z':
            break
        s += size + 1
    k32.CloseHandle(h)
    return 'int90=%04X:%04X sel=%s slot3=%r mods=%s' % (
        v90 >> 16, v90 & 0xFFFF, sel, slot3, mods)


if __name__ == '__main__':
    print(state())
