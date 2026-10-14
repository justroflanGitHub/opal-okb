"""Найти текстовые страницы (25x80) со строками кириллицы CP866 в памяти DOSBox."""
import ctypes, sys, subprocess

k32 = ctypes.windll.kernel32
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

def get_pid():
    out = subprocess.run(['powershell', '-NoProfile', '(Get-Process DOSBox | Select-Object -First 1).Id'],
                         capture_output=True, text=True).stdout.strip()
    return int(out)

def has_cyr_line(win):
    """Хотя бы одна строка экрана с >=8 подряд кириллическими знакоместами."""
    for r in range(25):
        run = 0
        for c in range(0, 160, 2):
            ch = win[r * 160 + c]
            if 0xE0 <= ch <= 0xFF or 0x80 <= ch <= 0xAF:
                run += 1
                if run >= 8:
                    return True
            else:
                run = 0
    return False

def decode(win):
    lines = []
    for r in range(25):
        row = []
        for c in range(0, 160, 2):
            ch = win[r * 160 + c]
            try:
                row.append(bytes([ch]).decode('cp866'))
            except Exception:
                row.append('?')
        lines.append(''.join(row).rstrip())
    return '\n'.join(lines)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pid = get_pid()
    h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    mbi = ctypes.create_string_buffer(48)
    ReadProcessMemory = k32.ReadProcessMemory
    pages = []
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
                for off in range(0, got.value - 4000, 160):
                    if base + off > 0x2000000:
                        break
                    win = data[off:off + 4000]
                    if has_cyr_line(win):
                        # атрибутная регулярность слабая проверка — пропускаем
                        pages.append((base + off, win))
                        if len(pages) > 6:
                            break
        if len(pages) > 6:
            break
        addr = base + size if base + size > addr else addr + 0x1000
    k32.CloseHandle(h)
    if not pages:
        print('NO CYR PAGES')
        return
    for a, w in pages[:4]:
        print(f'=== CYR PAGE @ {a:#x} ===')
        print(decode(w))
        print()

if __name__ == '__main__':
    main()
