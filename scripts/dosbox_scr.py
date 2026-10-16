# -*- coding: utf-8 -*-
"""Дамп активной текстовой страницы DOSBox (25x80, CP866) в stdout.

Ищет в памяти процесса interleaved-строку-якорь (по умолчанию 'F1-Help'),
берёт последний (самый свежий) hit, выравнивает по 160-байтным строкам,
якорь попадает на строку 24 (нижняя строка статуса).
Использование: py dosbox_scr.py [anchor_ascii]
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


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    anchor = sys.argv[1] if len(sys.argv) > 1 else 'F1-Help'
    # чередование байт/атрибут: между буквами ровно один любой байт
    inter = re.compile(rb''.join(
        re.escape(bytes([c])) + b'(.)' for c in anchor.encode('ascii')[:-1]
    ) + re.escape(bytes([anchor.encode('ascii')[-1]])), re.S)
    h = k32.OpenProcess(0x10 | 0x400, False, pid_of())
    mbi = ctypes.create_string_buffer(48)
    addr = 0
    hits = []
    while addr < 0x7FFFFFFF and len(hits) < 64:
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
    # группировка hit'ов по страницам (якорь на строке 24)
    pages = {}
    for a in hits:
        top = a - (a % 160) - 24 * 160
        pages.setdefault(top, 0)
        pages[top] += 1
    got = ctypes.c_size_t(0)

    def row_text(addr):
        row = ctypes.create_string_buffer(160)
        if not k32.ReadProcessMemory(h, ctypes.c_void_p(addr), row, 160,
                                     ctypes.byref(got)) or got.value < 160:
            return None
        cells = row.raw[::2]
        return ''.join(
            chr(c) if 32 <= c < 127 else
            bytes([c]).decode('cp866') if c >= 0x80 else ' '
            for c in cells)

    sel = None
    if len(sys.argv) > 2 and sys.argv[2].startswith('0x'):
        sel = int(sys.argv[2], 16)
        for r in range(25):
            txt = row_text(sel + r * 160)
            print(f'{r:2d}|{(txt or "?").rstrip()}')
        return
    if len(sys.argv) > 2 and sys.argv[2] == 'all':
        for top in sorted(pages):
            t2 = row_text(top + 2 * 160)
            t24 = row_text(top + 24 * 160)
            print(f'== page {top:#x} hits={pages[top]}')
            print(f'  r2 |{(t2 or "").rstrip()[:78]}')
            print(f'  r24|{(t24 or "").rstrip()[:78]}')
        return
    # по умолчанию: страница, где в r2 есть меню «Оптимиз/Выход», иначе последняя
    for top in sorted(pages, reverse=True):
        t2 = row_text(top + 2 * 160) or ''
        if 'Оптимиз' in t2 or 'Выход' in t2:
            sel = top
            break
    if sel is None:
        sel = max(pages)
    for r in range(25):
        addr = sel + r * 160
        txt = row_text(addr)
        print(f'{r:2d}|{(txt or f"<unreadable {addr:#x}>").rstrip()}')


if __name__ == '__main__':
    main()
