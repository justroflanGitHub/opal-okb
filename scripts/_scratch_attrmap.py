# -*- coding: utf-8 -*-
"""Dump B800 attrs: histogram + non-space cells + cursor pos."""
import ctypes, subprocess, sys
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
from dosbox_rd import get_pid, find_base  # noqa

k32 = ctypes.windll.kernel32
pid = get_pid()
h = k32.OpenProcess(0x410, False, pid)
B = find_base(h)
def read(a, n):
    b = ctypes.create_string_buffer(n); g = ctypes.c_size_t(0)
    return b.raw[:g.value] if k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g)) else None

txt = read(B + 0xB8000, 4000)
attrs = {}
nonspace = []
for r in range(25):
    for c in range(80):
        ch, at = txt[r*160+c*2], txt[r*160+c*2+1]
        attrs[at] = attrs.get(at, 0) + 1
        if ch not in (0x20, 0):
            nonspace.append((r, c, hex(ch), hex(at)))
print('attrs:', {hex(k): v for k, v in sorted(attrs.items())})
print('non-space cells:', len(nonspace), nonspace[:40])
bda = read(B + 0x400, 0x10)
cx, cy = bda[0x50], bda[0x51]
print('cursor at row=%d col=%d' % (cy, cx))
# keyboard buffer head/tail
bda2 = read(B + 0x400, 0x40)
head = int.from_bytes(bda2[0x1A:0x1C], 'little')
tail = int.from_bytes(bda2[0x1C:0x1E], 'little')
print('kbd buf head=%04x tail=%04x (equal=empty)' % (head, tail))
k32.CloseHandle(h)
