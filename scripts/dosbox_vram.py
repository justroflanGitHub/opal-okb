"""Найти и декодировать реальный текстовый VRAM (B800-зона DOS) в памяти DOSBox.
Маркер: строка вида C:\\> / Z:\\> / A:\\> или любой '...> ' с путём."""
import ctypes, sys, subprocess

k32 = ctypes.windll.kernel32
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

def get_pid():
    out = subprocess.run(['powershell', '-NoProfile', '(Get-Process DOSBox | Select-Object -First 1).Id'],
                         capture_output=True, text=True).stdout.strip()
    return int(out)

def decode(win):
    lines = []
    for r in range(25):
        row = ''.join(chr(win[r*160+c]) if 32 <= win[r*160+c] < 127 else
                      (bytes([win[r*160+c]]).decode('cp866') if win[r*160+c] >= 0x80 else
                       ('·' if win[r*160+c] else ' ')) for c in range(0, 160, 2))
        lines.append(row.rstrip())
    return '\n'.join(lines)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pid = get_pid()
    h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    mbi = ctypes.create_string_buffer(48)
    ReadProcessMemory = k32.ReadProcessMemory
    found = []
    addr = 0
    while addr < 0x7FFFFFFF:
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
            if ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(got)) and got.value >= 4000:
                data = buf.raw[:got.value]
                # маркер промпта: X:\ c чередованием attr
                for off in range(0, got.value - 40, 2):
                    d = data[off:off+8]
                    if (len(d) == 8 and d[0] in b'CZA' and d[2:4] == b':\\' and d[4] != 0 and
                            abs(base + off) < 0x2000000):
                        # выровнять на строку: назад до кратного 160 в пределах окна
                        start = off
                        win = data[max(0, off - 160*24):off - 160*24 + 4000]
                        if len(win) == 4000:
                            found.append((base + off, win))
                        break  # один на регион
        addr = base + size if base + size > addr else addr + 0x1000
    k32.CloseHandle(h)
    for a, w in found[:3]:
        print(f'=== PROMPT SCREEN @ {a:#x} ===')
        print(decode(w))
        print()

if __name__ == '__main__':
    main()
