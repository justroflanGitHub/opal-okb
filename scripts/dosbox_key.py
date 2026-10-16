# -*- coding: utf-8 -*-
"""Инъекция клавиш в BIOS-буфер клавиатуры DOSBox (BDA 0x41E ring, head/tail 0x41A/0x41C).
Работает без окна/foreground. Каждая клавиша: слово (scancode<<8 | ascii).
Использование: py dosbox_key.py ENTER ENTER DOWN ..."""
import ctypes, subprocess, sys, time

k32 = ctypes.windll.kernel32
SCAN = {'ENTER': 0x1C, 'ESC': 0x01, 'SPACE': 0x39, 'TAB': 0x0F, 'BS': 0x0E,
        'UP': 0x48, 'DOWN': 0x50, 'LEFT': 0x4B, 'RIGHT': 0x4D,
        'F1': 0x3B, 'F2': 0x3C, 'F3': 0x3D, 'F4': 0x3E, 'F5': 0x3F, 'F6': 0x40,
        'F7': 0x41, 'F8': 0x42, 'F9': 0x43, 'F10': 0x44,
        'HOME': 0x47, 'END': 0x4F, 'PGUP': 0x49, 'PGDN': 0x51}
ASCII = {'ENTER': 0x0D, 'ESC': 0x1B, 'SPACE': 0x20, 'TAB': 0x09, 'BS': 0x08}

def get_pid():
    out = subprocess.run(['powershell', '-NoProfile',
                          '(Get-Process DOSBox | Select-Object -First 1).Id'],
                         capture_output=True, text=True).stdout.strip()
    return int(out)

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pid = get_pid()
    h = k32.OpenProcess(0x410 | 0x20, False, pid)   # VM_READ|VM_WRITE|QUERY
    sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
    from dosbox_rd import find_base
    B = find_base(h)
    if not B:
        print('BASE NOT FOUND'); return

    def read(a, n):
        b = ctypes.create_string_buffer(n); g = ctypes.c_size_t(0)
        return b.raw[:g.value] if k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g)) else None

    def write(a, data):
        return k32.WriteProcessMemory(h, ctypes.c_void_p(a), data, len(data), None)

    for key in sys.argv[1:]:
        k = key.upper()
        if k in SCAN:
            sc, ch = SCAN[k], ASCII.get(k, 0)
        else:
            ch = ord(k.lower())
            sc = 0x02 + (ord(k.lower()) - ord('a')) if 'a' <= k.lower() <= 'z' else 0x1C
            if k.isdigit(): sc = {  # цифровой ряд
                '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
                '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B}[k]
        word = bytes([ch, sc])
        bda = read(B + 0x400, 0x30)
        head = int.from_bytes(bda[0x1A:0x1C], 'little')
        tail = int.from_bytes(bda[0x1C:0x1E], 'little')
        # ждать освобождения слота (эмулятор должен забрать)
        for _ in range(50):
            nxt = tail + 2
            if nxt > 0x3D: nxt = 0x1E
            if nxt == head:
                time.sleep(0.05)
                bda = read(B + 0x400, 0x30)
                head = int.from_bytes(bda[0x1A:0x1C], 'little')
                tail = int.from_bytes(bda[0x1C:0x1E], 'little')
            else:
                break
        write(B + 0x400 + tail, word)
        nxt = tail + 2
        if nxt > 0x3D: nxt = 0x1E
        write(B + 0x400 + 0x1C, nxt.to_bytes(2, 'little'))
        print(f'{key}: kbuf <- {word.hex()} tail {tail:04X}->{nxt:04X}')
        time.sleep(0.15)
    k32.CloseHandle(h)

if __name__ == '__main__':
    main()
