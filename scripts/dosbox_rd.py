# -*- coding: utf-8 -*-
"""Headless-ридер экрана/состояния DOSBox: B800 (текст), A000 (графика), MCB, kbuf.
База эмулируемого RAM ищется по IVT (серия F000-векторов) + BDA(80x24)."""
import ctypes, re, subprocess, sys

k32 = ctypes.windll.kernel32

def get_pid():
    out = subprocess.run(['powershell', '-NoProfile',
                          '(Get-Process DOSBox | Select-Object -First 1).Id'],
                         capture_output=True, text=True).stdout.strip()
    return int(out)

def find_base(h):
    mbi = ctypes.create_string_buffer(48)
    def read(a, n):
        b = ctypes.create_string_buffer(n); g = ctypes.c_size_t(0)
        return b.raw[:g.value] if k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g)) else None
    pat = re.compile(rb'(?:.{2}\x00\xf0){12,}', re.S)
    addr = 0; done = 0
    while addr < 0x7FFFFFFF and not done:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000; continue
        base = int.from_bytes(mbi[0:8], 'little'); size = int.from_bytes(mbi[24:32], 'little')
        state = int.from_bytes(mbi[32:36], 'little'); prot = int.from_bytes(mbi[36:40], 'little')
        if state == 0x1000 and (prot & 0xEE) and size >= 4096:
            d = read(base, size)
            if d:
                for m in pat.finditer(d):
                    s = m.start()
                    for k in range(128):
                        p0 = s - k * 4
                        if p0 < 0 or p0 + 0x490 > len(d): continue
                        if int.from_bytes(d[p0+0x44A:p0+0x44C], 'little') == 80 and d[p0+0x484] == 24 \
                           and int.from_bytes(d[p0+0x463:p0+0x465], 'little') in (0x3D4, 0x3B4):
                            return base + p0
        addr = base + size if base + size > addr else addr + 0x1000
    return None

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pid = get_pid()
    h = k32.OpenProcess(0x410, False, pid)
    B = find_base(h)
    if not B:
        print('BASE NOT FOUND'); return
    def read(a, n):
        b = ctypes.create_string_buffer(n); g = ctypes.c_size_t(0)
        return b.raw[:g.value] if k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g)) else None
    bda = read(B + 0x400, 0x90)
    mode = bda[0x49]; page = bda[0x62]
    v90 = int.from_bytes(read(B + 0x240, 4), 'little')
    print(f'RAM base={B:#x} pid={pid} mode={mode:02X} page={page} int90={v90>>16:04X}:{v90&0xFFFF:04X}')
    if mode in (0, 1, 2, 3, 7):
        txt = read(B + 0xB8000 + page * 0x1000, 4000) or b''
        lines = []
        for r in range(25):
            row = []
            for c in range(0, 160, 2):
                ch = txt[r*160+c]
                try: row.append(bytes([ch]).decode('cp866'))
                except Exception: row.append('.')
            # attr-подсветка курсора не нужна
            lines.append(''.join(row).rstrip())
        print('\n'.join(lines))
    else:
        g = read(B + 0xA0000, 0x8000) or b''
        nz = sum(1 for b in g if b)
        print(f'(графика mode={mode:02X}, A000 ненулевых байт в первых 32K: {nz})')
    k32.CloseHandle(h)

if __name__ == '__main__':
    main()
