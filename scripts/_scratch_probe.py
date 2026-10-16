# -*- coding: utf-8 -*-
"""Зонд памяти DOSBox v2: база эмулируемого RAM (крупнейший регион) -> IVT/MCB/B800."""
import ctypes, sys, subprocess
from collections import Counter

k32 = ctypes.windll.kernel32
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

def get_pid():
    out = subprocess.run(['powershell', '-NoProfile',
                          '(Get-Process DOSBox | Select-Object -First 1).Id'],
                         capture_output=True, text=True).stdout.strip()
    return int(out)

def regions(h):
    mbi = ctypes.create_string_buffer(48)
    addr = 0
    out = []
    while addr < 0x7FFFFFFF:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000
            continue
        base = int.from_bytes(mbi[0:8], 'little')
        size = int.from_bytes(mbi[24:32], 'little')
        state = int.from_bytes(mbi[32:36], 'little')
        prot = int.from_bytes(mbi[36:40], 'little')
        if state == 0x1000 and (prot & 0xEE):
            out.append((base, size))
        addr = base + size if base + size > addr else addr + 0x1000
    return out

def read(h, addr, n):
    buf = ctypes.create_string_buffer(n)
    got = ctypes.c_size_t(0)
    if k32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, n, ctypes.byref(got)):
        return buf.raw[:got.value]
    return None

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pid = get_pid()
    h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    regs = regions(h)
    regs.sort(key=lambda r: -r[1])
    print('топ-регионы:', [(hex(b), hex(s)) for b, s in regs[:5]])
    # эмулируемый RAM: крупнейший регион >= 4MB
    cand = [(b, s) for b, s in regs if s >= 0x400000]
    B = cand[0][0]
    print(f'база RAM: {B:#x}')

    # --- IVT ---
    ivt = read(h, B, 0x400)
    for v in (0x21, 0x28, 0x2F, 0x90):
        off = int.from_bytes(ivt[v * 4:v * 4 + 2], 'little')
        seg = int.from_bytes(ivt[v * 4 + 2:v * 4 + 4], 'little')
        print(f'int {v:02X}h -> {seg:04X}:{off:04X}')
    off = int.from_bytes(ivt[0x240:0x242], 'little')
    seg = int.from_bytes(ivt[0x242:0x244], 'little')
    lin = seg * 16 + off
    sig = read(h, B + lin, 16)
    print(f'int90 handler @ lin {lin:#x}: {sig.hex(" ") if sig else None}')

    # --- поиск резидента OPAL.COM ---
    ram = read(h, B, 0x110000)
    hits = []
    i = ram.find(b'OPAL5x5.EXE')
    while i != -1:
        hits.append(i)
        i = ram.find(b'OPAL5x5.EXE', i + 1)
    print(f'"OPAL5x5.EXE" в lin: {[hex(x) for x in hits]}')

    # --- MCB-цепь ---
    print('\n=== MCB chain ===')
    for start in range(0x40, 0x120):
        s = start
        chain = []
        ok = True
        for _ in range(300):
            hdr = read(h, B + s * 16, 16)
            if not hdr or hdr[0:1] not in (b'M', b'Z'):
                ok = False
                break
            typ = hdr[0:1].decode()
            owner = int.from_bytes(hdr[1:3], 'little')
            size = int.from_bytes(hdr[3:5], 'little')
            name = hdr[8:16].split(b'\0')[0].decode('cp437', 'replace')
            chain.append((s, typ, owner, size, name))
            if typ == 'Z':
                break
            s += size + 1
        if ok and len(chain) >= 5 and chain[-1][1] == 'Z':
            for s, t, o, sz, nm in chain:
                mark = ''
                if o == 8:
                    mark = ' (ядро DOS)'
                elif o == 0 and nm == '':
                    mark = ' (свободно)'
                print(f'MCB {s:04X} {t} owner={o:04X} size={sz * 16:6d}B  {nm!r}{mark}')
            break

    # --- B8000 текст ---
    print('\n=== B8000 (25x80) ===')
    txt = read(h, B + 0xB8000, 4000)
    if txt:
        lines = []
        for r in range(25):
            row = []
            for c in range(0, 160, 2):
                ch = txt[r * 160 + c]
                try:
                    row.append(bytes([ch]).decode('cp866'))
                except Exception:
                    row.append('.')
            lines.append(''.join(row).rstrip())
        screen = '\n'.join(lines)
        if screen.strip('\x00 .'):
            print(screen)
        else:
            print('(пусто)')
    g = read(h, B + 0xA0000, 0x10000)
    if g:
        cc = Counter(g)
        print(f'\nA000 (64K): {len(cc)} уник., топ: {[(hex(b), n) for b, n in cc.most_common(4)]}')
    k32.CloseHandle(h)

if __name__ == '__main__':
    main()
