# -*- coding: utf-8 -*-
"""Чтение видимой текстовой страницы DOSBox (80x25) из памяти процесса.
Ищем строку-якорь с шагом 2 (char,attr) по всей памяти; печатаем страницу."""
import ctypes as C
import subprocess
import sys

k32 = C.windll.kernel32


def find_page(anchor=b'LPTCAP'):
    # сначала ищем с attr=0x07 (настоящая текстовая страница), потом любой attr
    pat07 = b''.join(bytes([c, 0x07]) for c in anchor)
    n = len(anchor)
    pid = int(subprocess.run(['powershell', '-NoProfile',
                              '(Get-Process DOSBox | Select-Object -First 1).Id'],
                             capture_output=True, text=True).stdout.strip())
    h = k32.OpenProcess(0x0410, False, pid)
    if not h:
        raise SystemExit('no dosbox')
    mbi = C.create_string_buffer(48)
    addr = 0
    fallback = None
    while addr < 0x7FFFFFFF:
        if k32.VirtualQueryEx(h, C.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000
            continue
        base = int.from_bytes(mbi[0:8], 'little')
        size = int.from_bytes(mbi[24:32], 'little')
        st = int.from_bytes(mbi[32:36], 'little')
        pr = int.from_bytes(mbi[36:40], 'little')
        if st == 0x1000 and (pr & 0xEE) and 0x1000 < size <= 0x8000000:
            buf = C.create_string_buffer(size)
            got = C.c_size_t(0)
            if k32.ReadProcessMemory(h, C.c_void_p(base), buf, size, C.byref(got)) and got.value > 0x1000:
                d = buf.raw[:got.value]
                i = d.find(pat07)
                if i >= 0:
                    pg = i - (i % 4000)
                    if 0 <= pg and pg + 4000 <= len(d):
                        k32.CloseHandle(h)
                        return d[pg:pg + 4000]
                start = 0
                while fallback is None:
                    j = d.find(bytes([anchor[0]]), start)
                    if j < 0 or j + 2 * (n - 1) >= len(d):
                        break
                    if all(d[j + 2 * k] == anchor[k] for k in range(1, n)):
                        pg = j - (j % 4000)
                        if 0 <= pg and pg + 4000 <= len(d):
                            fallback = d[pg:pg + 4000]
                    start = j + 1
        addr = base + size if size else addr + 0x1000
        if addr <= base:
            break
    k32.CloseHandle(h)
    return fallback


def decode(win):
    rows = []
    for r in range(25):
        chars = bytes(win[r * 160:(r + 1) * 160][0::2])
        rows.append(chars.decode('cp437', errors='replace').rstrip())
    return rows


if __name__ == '__main__':
    anchor = sys.argv[1].encode() if len(sys.argv) > 1 else b'LPTCAP'
    win = find_page(anchor)
    if not win:
        print('PAGE NOT FOUND for', anchor)
        raise SystemExit(1)
    for i, row in enumerate(decode(win)):
        print(f'{i:2}|{row}')
