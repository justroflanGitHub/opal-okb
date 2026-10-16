# -*- coding: utf-8 -*-
"""Прогон набора клавиш с контролем изменения экрана после каждой.
Использование: py _scratch_keyprobe.py F1 F2 F3 ... — шлёт по одной,
печатает md5 экрана; при изменении — дамп строк, отличных от предыдущих.
"""
import ctypes
import hashlib
import subprocess
import sys
import time

sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
from dosbox_rd import get_pid

k32 = ctypes.windll.kernel32
ADDR = int(sys.argv[1], 16) if len(sys.argv) > 1 and sys.argv[1].startswith('addr:') else None
KEYS = sys.argv[2:] if ADDR else sys.argv[1:]


def dump():
    pid = get_pid()
    h = k32.OpenProcess(0x410, False, pid)
    b = ctypes.create_string_buffer(4000)
    g = ctypes.c_size_t(0)
    k32.ReadProcessMemory(h, ctypes.c_void_p(ADDR or 0xCDBC0A0), b, 4000, ctypes.byref(g))
    k32.CloseHandle(h)
    return b.raw[:4000]


def rows(d):
    out = []
    for r in range(25):
        row = ''.join(d[r*160+i:r*160+i+1].decode('cp866') for i in range(0, 160, 2))
        out.append(row.rstrip())
    return out


def find_buf():
    """если адрес не задан — найти текстовый буфер сканом (как dos_text)."""
    from dosbox_rd import find_base  # noqa
    pid = get_pid()
    h = k32.OpenProcess(0x410, False, pid)
    mbi = ctypes.create_string_buffer(48)

    def read(a, n):
        b = ctypes.create_string_buffer(n)
        g = ctypes.c_size_t(0)
        r = k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g))
        return b.raw[:g.value] if r else None
    best = None
    addr = 0
    while addr < 0x7FFFFFFF:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000
            continue
        base = int.from_bytes(mbi[0:8], 'little')
        size = int.from_bytes(mbi[24:32], 'little')
        state = int.from_bytes(mbi[32:36], 'little')
        prot = int.from_bytes(mbi[36:40], 'little')
        if state == 0x1000 and (prot & 0x4) and size >= 4096:
            d = read(base, size)
            if d:
                for off in range(0, len(d) - 4000, 160):
                    w = d[off:off + 4000]
                    attrs = w[1::2]
                    cnt = {}
                    for x in attrs[::2]:
                        cnt[x] = cnt.get(x, 0) + 1
                    top, n = max(cnt.items(), key=lambda kv: kv[1])
                    if top == 0 or n < 120:
                        continue
                    chars = w[0::2]
                    pr = sum(1 for c in chars if 32 <= c < 127 or 0x80 <= c <= 0xEF)
                    if pr < 1800:
                        continue
                    if best is None or pr > best[0]:
                        best = (pr, base + off)
        addr = base + size if base + size > addr else addr + 0x1000
    k32.CloseHandle(h)
    return best[1] if best else 0xCDBC0A0


if not ADDR:
    ADDR = find_buf()
    print('# buffer @%X' % ADDR)

prev = rows(dump())
print('# start md5=%s' % hashlib.md5('\n'.join(prev).encode()).hexdigest()[:8])
for k in KEYS:
    subprocess.run(['py', '-X', 'utf8',
                    r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts\dosbox_scan.py', k])
    time.sleep(1.2)
    cur = rows(dump())
    h = hashlib.md5('\n'.join(cur).encode()).hexdigest()[:8]
    if cur != prev:
        print('KEY %-6s -> CHANGED md5=%s' % (k, h))
        for i, (a, b) in enumerate(zip(prev, cur)):
            if a != b:
                print('  %2d -%s' % (i, a[-60:]))
                print('  %2d +%s' % (i, b[-60:]))
    else:
        print('KEY %-6s -> same' % k)
    prev = cur
