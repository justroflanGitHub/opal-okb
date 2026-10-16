"""Чтение эмулируемой физической памяти DOSBox: BDA + текстовые страницы + A000."""
import ctypes, sys, subprocess

k32 = ctypes.windll.kernel32
PID = int(subprocess.run(['powershell','-NoProfile','(Get-Process DOSBox | Select-Object -First 1).Id'],
        capture_output=True, text=True).stdout.strip())
h = k32.OpenProcess(0x0410, False, PID)
sys.stdout.reconfigure(encoding='utf-8')
BASE = 0xbdb5000

def rd(a, n):
    buf = ctypes.create_string_buffer(n); got = ctypes.c_size_t(0)
    ok = k32.ReadProcessMemory(h, ctypes.c_void_p(a), buf, n, ctypes.byref(got))
    return buf.raw[:got.value] if ok else None

bios = rd(BASE+0x400, 0x30)
if bios:
    print("BDA: video mode=%02X cols=%d page=%d" % (
        bios[0x49], int.from_bytes(bios[0x4a:0x4c],'little'), bios[0x62]))
    print("     CRT base=%04X rows=%d" % (int.from_bytes(bios[0x63:0x65],'little'), bios[0x84]+1))

def dump_text(off, name, cols=80, rows=25):
    d = rd(BASE+off, cols*rows*2)
    if not d: print(name, "unreadable"); return
    pr = sum(1 for c in d[0::2] if 32 <= c < 127 or 0x80 <= c <= 0xFF)
    print(f"{name} (phys {off:#x}): printable={pr}/{cols*rows}")
    for r in range(rows):
        row = d[r*cols*2:(r+1)*cols*2:2]
        line = bytes(row).decode('cp866', errors='replace').rstrip()
        if line.strip(): print("  |" + line)

dump_text(0xB0000, "B000 mono")
dump_text(0xB8000, "B800 color")
a = rd(BASE+0xA0000, 0x8000)
if a is not None:
    nz = sum(1 for c in a if c)
    print(f"A000 first 32K: nonzero={nz} ({nz*100//0x8000}%)")
