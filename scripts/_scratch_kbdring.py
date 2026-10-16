# -*- coding: utf-8 -*-
"""BIOS kbd ring BDA: head 0x41A tail 0x41C buffer 0x41E..0x43D."""
import ctypes, sys
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
from dosbox_rd import get_pid, find_base
k32 = ctypes.windll.kernel32
pid = get_pid(); h = k32.OpenProcess(0x410, False, pid); B = find_base(h)
def rd(a, n):
    b = ctypes.create_string_buffer(n); g = ctypes.c_size_t(0)
    r = k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g))
    return b.raw[:g.value] if r else None
hdr = rd(B + 0x41A, 4)
head, tail = int.from_bytes(hdr[0:2], 'little'), int.from_bytes(hdr[2:4], 'little')
buf = rd(B + 0x41E, 32)
ents = [(hex(buf[i]), hex(buf[i+1])) for i in range(0, 32, 2)]
print('head=%03X tail=%03X' % (head, tail))
print('ring:', ' '.join('%s/%s' % e for e in ents))
ivt16 = rd(B + 0x16 * 4, 4)
ivt9 = rd(B + 9 * 4, 4)
print('int16=%04X:%04X int9=%04X:%04X' % (
    int.from_bytes(ivt16[2:4], 'little'), int.from_bytes(ivt16[0:2], 'little'),
    int.from_bytes(ivt9[2:4], 'little'), int.from_bytes(ivt9[0:2], 'little')))
k32.CloseHandle(h)
