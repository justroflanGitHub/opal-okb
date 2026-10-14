"""Точный поиск текстового экрана OPALA (CP866-кириллица) в памяти DOSBox."""
import ctypes, ctypes.wintypes as wt, sys, subprocess, time

k32 = ctypes.windll.kernel32
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

def get_pid():
    out = subprocess.run(['powershell', '-NoProfile', '(Get-Process DOSBox | Select-Object -First 1).Id'],
                         capture_output=True, text=True).stdout.strip()
    return int(out)

CP437 = (open(0, encoding='cp437', errors='replace').read() if False else None)

def decode_cp437(win):
    # быстрая таблица: только печатаемые
    tbl = {}
    for i in range(256):
        try:
            tbl[i] = bytes([i]).decode('cp437')
        except Exception:
            tbl[i] = '?'
    lines = []
    for r in range(25):
        lines.append(''.join(tbl.get(win[r*160+c], '?') for c in range(0, 160, 2)).rstrip())
    return '\n'.join(lines)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pid = get_pid()
    h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    mbi = ctypes.create_string_buffer(48)
    VirtualQueryEx = k32.VirtualQueryEx
    ReadProcessMemory = k32.ReadProcessMemory
    addr = 0
    best = None  # (score, addr, win)
    while addr < 0x7FFFFFFF:
        if VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000
            continue
        base = int.from_bytes(mbi[0:8], 'little')
        size = int.from_bytes(mbi[24:32], 'little')
        state = int.from_bytes(mbi[32:36], 'little')
        prot = int.from_bytes(mbi[36:40], 'little')
        if state == 0x1000 and (prot & 0xEE):
            buf = ctypes.create_string_buffer(size)
            got = ctypes.c_size_t(0)
            if ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(got)) and got.value >= 4000:
                data = buf.raw[:got.value]
                # ищем окна, выровненные на 2, шаг 0x40, только низкая память (<32MB)
                step = 0x40
                for off in range(0, got.value - 4000, step):
                    if (base + off) > 0x2000000:
                        break
                    win = data[off:off + 4000]
                    cyr = sum(1 for i in range(0, 4000, 2) if 0xE0 <= win[i] <= 0xFF or 0x80 <= win[i] <= 0xAF)
                    lat = sum(1 for i in range(0, 4000, 2) if 0x20 <= win[i] <= 0x7E)
                    score = cyr * 3 + lat
                    if cyr >= 100 and (best is None or score > best[0]):
                        attrs_ok = sum(1 for i in range(1, 4000, 2) if win[i] == win[1])
                        if attrs_ok >= 1500:
                            best = (score, base + off, win)
        addr = base + size if base + size > addr else addr + 0x1000
    k32.CloseHandle(h)
    if best:
        print(f'BEST @ {best[1]:#x} score={best[0]}')
        print(decode_cp437(best[2]))
    else:
        print('NO CYR SCREEN')

if __name__ == '__main__':
    main()
