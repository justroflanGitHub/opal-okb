# -*- coding: utf-8 -*-
"""Поиск НАСТОЯЩЕГО текстового буфера VGA в процессе DOSBox (B800 живёт
в отдельной куче C++). Ищем окно 4000 байт: нечётные байты (attr) однородны,
чётные декодируются в CP866-печатаемые. --marker ZZQW7: поиск по маркеру.
"""
import ctypes
import re
import sys

sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
from dosbox_rd import get_pid

k32 = ctypes.windll.kernel32


def decode(buf):
    lines = []
    for r in range(25):
        chunk = buf[r * 160:(r + 1) * 160]
        out = []
        for i in range(0, 160, 2):
            c = chunk[i]
            if 32 <= c < 127:
                out.append(chr(c))
            elif 0x80 <= c <= 0xAF:
                out.append(chr(0x410 + c - 0x80))  # А-Я/а-п cp866
            elif 0xE0 <= c <= 0xEF:
                out.append(chr(0x440 + c - 0xE0))
            elif 0xF0 <= c <= 0xF9 and False:
                out.append('')
            else:
                out.append('·')
        lines.append('%2d|%s|' % (r, ''.join(out).rstrip()))
    return '\n'.join(lines)


def scan(marker=None):
    pid = get_pid()
    h = k32.OpenProcess(0x410, False, pid)
    mbi = ctypes.create_string_buffer(48)

    def read(a, n):
        b = ctypes.create_string_buffer(n)
        g = ctypes.c_size_t(0)
        r = k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g))
        return b.raw[:g.value] if r else None

    hits = []
    if marker:
        pat = re.compile(b''.join(bytes([ord(ch), 0x2E]) for ch in marker), re.S)
    addr = 0
    while addr < 0x7FFFFFFF:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000
            continue
        base = int.from_bytes(mbi[0:8], 'little')
        size = int.from_bytes(mbi[24:32], 'little')
        state = int.from_bytes(mbi[32:36], 'little')
        prot = int.from_bytes(mbi[36:40], 'little')
        if state == 0x1000 and (prot & 0x4) and size >= 4096:
            d = read(base, size)
            if d:
                if marker:
                    for m in pat.finditer(d):
                        a = base + m.start()
                        buf = read(a - (a % 160) if False else a, 0)  # noop
                        hits.append(base + m.start())
                        break
                else:
                    # ищем attr-однородные окна
                    for off in range(0, min(len(d), size) - 4000, 160):
                        w = d[off:off + 4000]
                        attrs = w[1::2]
                        # самый частый attr
                        cnt = {}
                        for x in attrs[::4]:
                            cnt[x] = cnt.get(x, 0) + 1
                        top, n = max(cnt.items(), key=lambda kv: kv[1])
                        if n < 120:
                            continue
                        chars = w[0::2]
                        pr = sum(1 for c in chars if 32 <= c < 127 or 0x80 <= c <= 0xEF)
                        if pr > 1800:
                            nz = sum(1 for c in chars if c != 0x20 and c != 0)
                            if 30 < nz < 1800:
                                hits.append((base + off, top, pr, nz))
        addr = base + size if base + size > addr else addr + 0x1000
    k32.CloseHandle(h)
    return hits


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--marker':
        print(scan(sys.argv[2]))
    else:
        hs = scan()
        print('candidate text buffers:', len(hs))
        pid = get_pid()
        h = k32.OpenProcess(0x410, False, pid)
        for a, top, pr, nz in hs[:4]:
            b = ctypes.create_string_buffer(4000)
            g = ctypes.c_size_t(0)
            k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, 4000, ctypes.byref(g))
            print('=== @%X attr=%02X printable=%d nz=%d' % (a, top, pr, nz))
            print(decode(b.raw))
        k32.CloseHandle(h)
