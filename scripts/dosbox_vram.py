# -*- coding: utf-8 -*-
"""Headless-чтение ЭКРАНА DOSBox через хост-копию VRAM (vga.mem.linear).
Текстовый буфер B800 ищется по сигнатуре «серия пар (символ,атрибут) с одинаковым атрибутом».
Использование: py dosbox_vram.py [--raw]  — печатает 80x25 текст текущего экрана (cp866).
Также: py dosbox_vram.py --a000 [N] — дамп A000-окна (графика) как ASCII-арт (плоскости)."""
import ctypes, re, subprocess, sys

k32 = ctypes.windll.kernel32
_RUN = None  # (pid, vram_text_addr) кэш

def get_pid():
    out = subprocess.run(['powershell','-NoProfile',
                          '(Get-Process DOSBox | Select-Object -First 1).Id'],
                         capture_output=True, text=True).stdout.strip()
    return int(out)

def _regions(h):
    mbi = ctypes.create_string_buffer(48)
    def read(a, n):
        b = ctypes.create_string_buffer(n); g = ctypes.c_size_t(0)
        return b.raw[:g.value] if k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g)) else None
    addr = 0
    while addr < 0x7FFFFFFF:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000; continue
        base = int.from_bytes(mbi[0:8], 'little'); size = int.from_bytes(mbi[24:32], 'little')
        st = int.from_bytes(mbi[32:36], 'little'); pr = int.from_bytes(mbi[36:40], 'little')
        if st == 0x1000 and (pr & 0xEE) and size >= 4096:
            yield base, size, read
        addr = base + size if base + size > addr else addr + 0x1000

def find_text_vram(h):
    """Адрес начала парного (char,attr) текстового экрана внутри хост-VRAM (не выровнен)."""
    best = None  # (runlen, addr)
    pat = re.compile(rb'([\x20-\xFF].)\1{23,}')
    for base, size, read in _regions(h):
        d = read(base, min(size, 64*1024*1024))
        if not d: continue
        for m in pat.finditer(d):
            L = len(m.group(0))
            if best is None or L > best[0]:
                best = (L, base + m.start())
    return best

def screen_text(h, probe_addr):
    """Читаем 25x80 вокруг probe; выравниваем на сетку 160 байт."""
    def read(a, n):
        b = ctypes.create_string_buffer(n); g = ctypes.c_size_t(0)
        return b.raw[:g.value] if k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g)) else None
    row0 = (probe_addr // 160) * 160
    d = read(row0, 160*40) or b''
    lines = []
    for r in range(40):
        row = d[r*160:(r+1)*160]
        t = ''.join(bytes([row[c]]).decode('cp866', 'replace') for c in range(0, 160, 2))
        lines.append(t.rstrip())
    return lines

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pid = get_pid()
    h = k32.OpenProcess(0x410, False, pid)
    best = find_text_vram(h)
    if not best:
        print('TEXT VRAM NOT FOUND'); return
    L, a = best
    print(f'# text-vram run={L} at {a:#x} pid={pid}')
    for i, t in enumerate(screen_text(h, a)):
        if t: print(f'{i:2}|{t}')
    k32.CloseHandle(h)

if __name__ == '__main__':
    main()
