# -*- coding: utf-8 -*-
"""Читалка текстового экрана DOSBox: настоящий VGA-буфер живёт в куче
процесса (не в эмулируемом 1MB). Сканируем RW-память, ищем окно 4000 байт
с однородным attr!=0 и печатаемыми символами. BDA (find_base) даёт video mode.
Выход: 25 строк экрана. Выход с ключом --addr ADDR — дамп конкретного адреса.
"""
import ctypes
import sys

sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
from dosbox_rd import get_pid, find_base

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
                out.append(chr(0x410 + c - 0x80))
            elif 0xE0 <= c <= 0xEF:
                out.append(chr(0x440 + c - 0xE0))
            elif c == 0xF0 or c == 0xF1:
                out.append('Ё' if c == 0xF0 else 'ё')
            else:
                out.append('·')
        lines.append('%2d|%s|' % (r, ''.join(out).rstrip()))
    return '\n'.join(lines)


def main():
    pid = get_pid()
    h = k32.OpenProcess(0x410, False, pid)
    mbi = ctypes.create_string_buffer(48)

    def read(a, n):
        b = ctypes.create_string_buffer(n)
        g = ctypes.c_size_t(0)
        r = k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g))
        return b.raw[:g.value] if r else None

    if len(sys.argv) > 2 and sys.argv[1] == '--addr':
        a = int(sys.argv[2], 16)
        d = read(a, 4000) or b''
        print('@%X' % a)
        print(decode(d))
        k32.CloseHandle(h)
        return

    # BDA / mode
    B = find_base(h)
    mode = -1
    if B:
        d = read(B + 0x449, 1)
        if d:
            mode = d[0]
    print('# video_mode=%s' % mode)

    best = None  # (score, addr, buf)
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
                for off in range(0, len(d) - 4000, 160):
                    w = d[off:off + 4000]
                    attrs = w[1::2]
                    cnt = {}
                    for x in attrs[::2]:
                        cnt[x] = cnt.get(x, 0) + 1
                    top, n = max(cnt.items(), key=lambda kv: kv[1])
                    if top == 0 or n < 120:
                        continue
                    chars = w[0::2]
                    pr = sum(1 for c in chars if 32 <= c < 127 or 0x80 <= c <= 0xEF)
                    if pr < 1800:
                        continue
                    txt = bytes(chars)
                    score = pr + (500 if b':\\>' in txt else 0)
                    if best is None or score > best[0]:
                        best = (score, base + off, w)
        addr = base + size if base + size > addr else addr + 0x1000
    k32.CloseHandle(h)
    if best:
        print('# text buffer @%X score=%d' % (best[1], best[0]))
        print(decode(best[2]))
    else:
        print('# no text buffer found')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
