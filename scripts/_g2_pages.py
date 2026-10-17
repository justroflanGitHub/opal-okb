# -*- coding: utf-8 -*-
"""Поиск всех текстовых 80x25 страниц в памяти DOSBox (по плотности attr=0x07)."""
import ctypes as C
import subprocess
import sys

k32 = C.windll.kernel32


def pages():
    pid = int(subprocess.run(['powershell', '-NoProfile',
                              '(Get-Process DOSBox | Select-Object -First 1).Id'],
                             capture_output=True, text=True).stdout.strip())
    h = k32.OpenProcess(0x0410, False, pid)
    if not h:
        raise SystemExit('no dosbox')
    mbi = C.create_string_buffer(48)
    addr = 0
    out = []
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
                step = 4000
                for off in range(0, len(d) - step, 2):
                    w = d[off:off + step]
                    n07 = sum(1 for k in range(1, step, 2) if w[k] == 0x07)
                    if n07 > 3600:
                        nz = sum(1 for k in range(0, step, 2) if w[k] >= 32)
                        if nz > 400:
                            out.append((base + off, w))
                            if len(out) > 200:
                                break
        addr = base + size if size else addr + 0x1000
        if addr <= base:
            break
    k32.CloseHandle(h)
    return out


if __name__ == '__main__':
    seen = set()
    for a, w in pages():
        key = w[:400]
        if key in seen:
            continue
        seen.add(key)
        rows = []
        for r in range(25):
            ch = bytes(w[r * 160:(r + 1) * 160][0::2])
            rows.append(ch.decode('cp437', errors='replace').rstrip())
        print(f'=== page @ {a:#x} ===')
        for i in (0, 1, 2, 12, 22, 23, 24):
            print(f'{i:2}|{rows[i][:78]}')
        print()
