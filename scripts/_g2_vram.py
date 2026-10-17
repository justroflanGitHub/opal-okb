# -*- coding: utf-8 -*-
"""Целевое чтение текстовой VRAM DOSBox: ищем char/attr-чередование известной строки."""
import ctypes, subprocess, sys

k32 = ctypes.windll.kernel32
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400

CP437 = {}
for i in range(256):
    try:
        CP437[i] = bytes([i]).decode('cp437')
    except Exception:
        CP437[i] = '?'


def pid_of():
    out = subprocess.run(['powershell', '-NoProfile',
                          '(Get-Process DOSBox | Select-Object -First 1).Id'],
                         capture_output=True, text=True).stdout.strip()
    return int(out)


def find_screen(pid, anchors):
    h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h:
        raise OSError('open failed')
    mbi = ctypes.create_string_buffer(48)
    addr = 0
    hits = {}
    while addr < 0x7FFFFFFF:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000
            continue
        base = int.from_bytes(mbi[0:8], 'little')
        size = int.from_bytes(mbi[24:32], 'little')
        state = int.from_bytes(mbi[32:36], 'little')
        prot = int.from_bytes(mbi[36:40], 'little')
        if state == 0x1000 and (prot & 0xEE):
            buf = ctypes.create_string_buffer(size)
            got = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(got)) and got.value > 0x1000:
                data = buf.raw[:got.value]
                for name, pat in anchors.items():
                    start = 0
                    while True:
                        i = data.find(pat, start)
                        if i < 0:
                            break
                        hits.setdefault(name, []).append(base + i)
                        start = i + 2
        addr = base + size if size else addr + 0x1000
        if addr <= base:
            break
    k32.CloseHandle(h)
    return hits


def spaced(s, attr=None):
    out = b''
    for ch in s.encode('ascii'):
        out += bytes([ch])
        out += bytes([attr]) if attr is not None else b'.'
    # attr неизвестен: вернём все 256 вариантов при attr=None
    if attr is not None:
        return [out]
    return [bytes([ord(c)]) + bytes([a]) for c in s for a in ()] or None  # unused


def spaced_all(s):
    """Генерируем паттерн с маской: строим вручную поиск с шагом 2 и любой attr."""
    return s.encode('ascii')


def find_spaced(data_holder, s):
    """Ищем строку s, стоящую с шагом 2 (char,attr,char,attr...)."""
    res = []
    b = s.encode('ascii')
    n = len(b)
    d = data_holder
    i = d.find(bytes([b[0]]))
    # наивно: ищем первую букву, проверяем шаг 2
    start = 0
    while True:
        i = d.find(bytes([b[0]]), start)
        if i < 0 or i + 2 * (n - 1) >= len(d):
            break
        ok = True
        for k in range(1, n):
            if d[i + 2 * k] != b[k]:
                ok = False
                break
        if ok:
            res.append(i)
        start = i + 1
    return res


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pid = pid_of()
    h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    mbi = ctypes.create_string_buffer(48)
    addr = 0
    found = []   # (base, offset)
    while addr < 0x7FFFFFFF:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000
            continue
        base = int.from_bytes(mbi[0:8], 'little')
        size = int.from_bytes(mbi[24:32], 'little')
        state = int.from_bytes(mbi[32:36], 'little')
        prot = int.from_bytes(mbi[36:40], 'little')
        if state == 0x1000 and (prot & 0xEE) and size <= 0x8000000:
            buf = ctypes.create_string_buffer(size)
            got = ctypes.c_size_t(0)
            if k32.ReadProcessMemory(h, ctypes.c_void_p(base), buf, size, ctypes.byref(got)) and got.value > 0x1000:
                d = buf.raw[:got.value]
                for off in find_spaced(d, 'LPTCAP'):
                    found.append((base, off, d))
        addr = base + size if size else addr + 0x1000
        if addr <= base:
            break
    k32.CloseHandle(h)
    print('hits:', len(found))
    # декодируем экран вокруг каждого хита: выравниваем на 160-байтные строки
    seen = set()
    for base, off, d in found:
        row_start = off - (off % 160)
        page = off - (off % 4000) if len(d) >= (off % 4000) + 4000 else max(0, row_start - 10 * 160)
        if page < 0:
            page = 0
        win = d[page:page + 4000]
        if len(win) < 4000:
            continue
        key = win[:800]
        if key in seen:
            continue
        seen.add(key)
        print(f'=== @ {base + page:#x} (hit off {off - page}) ===')
        for r in range(25):
            line = ''.join(CP437.get(win[r * 160 + c], '?') for c in range(0, 160, 2))
            print(f'{r:2}|{line.rstrip()}')
        print()


if __name__ == '__main__':
    main()
