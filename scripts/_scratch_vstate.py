"""Поиск по всей памяти DOSBox: строки OPALA / ГАБАРИТЫ / This is a setup work."""
import ctypes, sys, subprocess

k32 = ctypes.windll.kernel32
PID = int(subprocess.run(['powershell','-NoProfile','(Get-Process DOSBox | Select-Object -First 1).Id'],
        capture_output=True, text=True).stdout.strip())
h = k32.OpenProcess(0x0410, False, PID)
sys.stdout.reconfigure(encoding='utf-8')

mbi = ctypes.create_string_buffer(48)
addr = 0
hits = 0
def rd(a, n):
    buf = ctypes.create_string_buffer(n); got = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(a), buf, n, ctypes.byref(got))
    return buf.raw[:got.value] if ok else None

needles = [b'OPALA', 'ГАБАРИТЫ'.encode('cp866'), b'setup work', b'PODDED', b'OPAL.ARH', b'MENUOPAL']
while addr < 0x7FFFFFFF and hits < 200:
    if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
        addr += 0x1000; continue
    base = int.from_bytes(mbi[0:8],'little'); size = int.from_bytes(mbi[24:32],'little')
    state = int.from_bytes(mbi[32:36],'little'); prot = int.from_bytes(mbi[36:40],'little')
    addr = base + size if size else addr + 0x1000
    if state != 0x1000 or not (prot & 0x2 or prot & 0x4): continue
    if size > 0x8000000: continue
    d = rd(base, size)
    if not d: continue
    for nd in needles:
        off = 0
        while True:
            i = d.find(nd, off)
            if i < 0: break
            off = i + 1; hits += 1
            ctx = d[max(0,i-16):i+80]
            print(f"{nd!r:30s} @ {base:#x}+{i:#x}: {ctx!r}")
            if hits >= 200: break
        if hits >= 200: break
print("done, hits:", hits)
