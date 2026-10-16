# -*- coding: utf-8 -*-
"""Найти текстовые страницы DOSBox по произвольному (в т.ч. CP866-кириллица)
якорю и напечатать их. Использование: py dosbox_find.py 'Работа' [--dump 0xADDR]
"""
import ctypes
import re
import subprocess
import sys

k32 = ctypes.windll.kernel32


def pid_of():
    out = subprocess.run(
        ['powershell', '-NoProfile',
         '(Get-Process DOSBox | Select-Object -First 1).Id'],
        capture_output=True, text=True).stdout.strip()
    return int(out)


def row_text(h, got, addr):
    row = ctypes.create_string_buffer(160)
    if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), row, 160,
                                 ctypes.byref(got)) or got.value < 160:
        return None
    cells = row.raw[::2]
    return ''.join(
        chr(c) if 32 <= c < 127 else
        bytes([c]).decode('cp866') if c >= 0x80 else ' '
        for c in cells)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    anchor = sys.argv[1].encode('cp866')
    inter = re.compile(rb''.join(
        re.escape(bytes([c])) + b'(.)' for c in anchor[:-1]
    ) + re.escape(bytes([anchor[-1]])), re.S)
    h = k32.OpenProcess(0x10 | 0x400, False, pid_of())
    mbi = ctypes.create_string_buffer(48)
    addr = 0
    hits = []
    while addr < 0x7FFFFFFF and len(hits) < 128:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000
            continue
        base = int.from_bytes(mbi[0:8], 'little')
        size = int.from_bytes(mbi[24:32], 'little')
        state = int.from_bytes(mbi[32:36], 'little')
        prot = int.from_bytes(mbi[36:40], 'little')
        if state == 0x1000 and (prot & 0xEE) and size >= 4096:
            buf = ctypes.create_string_buffer(size)
            got = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size,
                                     ctypes.byref(got)) and got.value:
                hits.extend(base + m.start()
                            for m in inter.finditer(buf.raw[:got.value]))
        addr = base + size if base + size > addr else addr + 0x1000
    if not hits:
        print('NO ANCHOR PAGE')
        return
    pages = {}
    for a in hits:
        # якорь может быть в любой строке: пробуем выравнивания 0..24
        top = a - (a % 160)
        for r in range(25):
            cand = top - r * 160
            pages.setdefault(cand, 0)
        pages[top] += 1
    got = ctypes.c_size_t(0)
    if len(sys.argv) > 3 and sys.argv[2] == '--dump':
        sel = int(sys.argv[3], 16)
    else:
        sel = None
    tops = sorted(t for t in pages if pages[t] > 0)
    if sel is None:
        for top in tops:
            print(f'== page {top:#x}')
        sel = max(tops)
        print(f'-- dumping {sel:#x}')
    for r in range(25):
        txt = row_text(h, got, sel + r * 160)
        print(f'{r:2d}|{(txt or "?").rstrip()}')


if __name__ == '__main__':
    main()
