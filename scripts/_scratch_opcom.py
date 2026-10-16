# -*- coding: utf-8 -*-
"""Decode OPAL.PSP directory + OPAL.ARH allocation table (TASK_OPCOM)."""
import os

BASE = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'
psp = open(os.path.join(BASE, 'OPAL.PSP'), 'rb').read()
arh = open(os.path.join(BASE, 'OPAL.ARH'), 'rb').read()

def ror8(v, n):
    n &= 7
    return ((v >> n) | (v << (8 - n))) & 0xFF

def decode_entry(e):
    """In-place decode per 0x19F3: key=e[0] plain; for i in 1..0x5f:
    c^=key; ror(c, key&0xF); c^=0x5A; c-=(key^0x53); c^=0xC5; key-=7"""
    out = bytearray(e[:1])
    key = e[0]
    for i in range(1, 0x60):
        c = e[i]
        c ^= key
        c = ror8(c, key & 0x0F)
        c ^= 0x5A
        c = (c - ((key ^ 0x53) & 0xFF)) & 0xFF
        c ^= 0xC5
        out.append(c)
        key = (key - 7) & 0xFF
    return bytes(out)

n = int.from_bytes(psp[0:2], 'little')
print('OPAL.PSP size=%d, N=%d, dir bytes=%d, remainder=%d' %
      (len(psp), n, n * 0x60, len(psp) - 2 - n * 0x60))
assert len(psp) >= 2 + n * 0x60

def cp866(b):
    s = []
    for ch in b:
        if ch == 0:
            continue
        if 0xA0 <= ch <= 0xAF:
            s.append(chr(0x0410 + (ch - 0xA0)))  # А-П
        elif 0xE0 <= ch <= 0xEF:
            s.append(chr(0x0420 + (ch - 0xE0)))  # Р-Я
        elif ch == 0xF0:
            s.append('Ё')
        elif ch == 0xF1:
            s.append('ё')
        elif 32 <= ch < 127:
            s.append(chr(ch))
        else:
            s.append('.')
    return ''.join(s)

for k in range(n):
    raw = psp[2 + k * 0x60: 2 + (k + 1) * 0x60]
    dec = decode_entry(raw)
    name5 = dec[0:5].decode('latin1')
    exe8 = dec[4:12].decode('latin1')
    rest = dec[12:]
    print('#%02d key=%02X name=%r exe=%r tail=%r' % (k, raw[0], name5, exe8, cp866(rest[:40])))
    if k < 3:
        hx = ' '.join('%02x' % b for b in dec[:64])
        print('    dec[0:64] = %s' % hx)
        asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in dec[:96])
        print('    ascii     = %s' % asc)

print()
print('=== OPAL.ARH allocation table (128 x {u32 off, u16 size} at offset 0) ===')
used = 0
for i in range(128):
    off = int.from_bytes(arh[i * 6:i * 6 + 4], 'little')
    size = int.from_bytes(arh[i * 6 + 4:i * 6 + 6], 'little', signed=False)
    if off or size:
        used += 1
        end = off + size
        head = arh[off:off + 24]
        print('slot %3d: off=0x%06x (%6d) size=0x%04x (%5d) end=0x%06x  head=%r' %
              (i, off, off, size, size, end, head))
print('used slots: %d / 128; file size=%d (0x%x), table ends at 0x300' % (used, len(arh), len(arh)))
