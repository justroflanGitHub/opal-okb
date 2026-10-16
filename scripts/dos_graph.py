# -*- coding: utf-8 -*-
"""Рендер графического экрана DOSBox из памяти.
Раскладка vga.mem.linear (DOSBox 0.74): плоскости interleaved по байтам,
linear[a*4 + plane]. Текст B8000 -> linear + 0x18000*4 (якорь для поиска базы).
Режим 0x10: 640x350, 80 байт/ряд на плоскость.
"""
import ctypes
import sys

sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
from dosbox_rd import get_pid, find_base

k32 = ctypes.windll.kernel32

EGA_LUM = [0x00, 0xAA, 0x55, 0xFF, 0xAA, 0xFF, 0x55, 0xFF,
           0x55, 0xFF, 0xAA, 0xFF, 0xAA, 0xFF, 0xAA, 0xFF]


def find_text_buf(h):
    mbi = ctypes.create_string_buffer(48)

    def read(a, n):
        b = ctypes.create_string_buffer(n)
        g = ctypes.c_size_t(0)
        r = k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g))
        return b.raw[:g.value] if r else None
    best = None
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
                    cnt = {}
                    for x in w[1::2]:
                        cnt[x] = cnt.get(x, 0) + 1
                    top, n = max(cnt.items(), key=lambda kv: kv[1])
                    if top == 0 or n < 120:
                        continue
                    chars = w[0::2]
                    pr = sum(1 for c in chars if 32 <= c < 127 or 0x80 <= c <= 0xEF)
                    if pr < 1500:
                        continue
                    if best is None or pr > best[0]:
                        best = (pr, base + off)
        addr = base + size if base + size > addr else addr + 0x1000
    return best


def main():
    pid = get_pid()
    h = k32.OpenProcess(0x410, False, pid)
    B = find_base(h)

    def rd(a, n):
        b = ctypes.create_string_buffer(n)
        g = ctypes.c_size_t(0)
        r = k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g))
        return b.raw[:g.value] if r else None

    mode = rd(B + 0x449, 1)[0] if B else -1
    print('# mode=%s' % mode)
    bt = find_text_buf(h)
    if not bt:
        print('# no anchor')
        return
    linear = bt[1] - 0x18000 * 4
    print('# textbuf @%X -> linear=%X' % (bt[1], linear))
    W, H = 640, 350
    need = (80 * H) * 4
    buf = rd(linear, need) or b''
    print('# read %d/%d bytes' % (len(buf), need))
    from PIL import Image
    im = Image.new('L', (W, H), 0)
    px = im.load()
    nz = 0
    for y in range(H):
        row = y * 80 * 4
        for xb in range(80):
            b0 = buf[row + xb*4 + 0]
            b1 = buf[row + xb*4 + 1]
            b2 = buf[row + xb*4 + 2]
            b3 = buf[row + xb*4 + 3]
            nz += (b0 | b1 | b2 | b3) != 0
            for bit in range(8):
                idx = (((b3 >> (7 - bit)) & 1) << 3) | (((b2 >> (7 - bit)) & 1) << 2) | \
                      (((b1 >> (7 - bit)) & 1) << 1) | ((b0 >> (7 - bit)) & 1)
                px[xb * 8 + bit, y] = EGA_LUM[idx]
    print('# nonblank bytes: %d/%d' % (nz, 80*H))
    k32.CloseHandle(h)
    out = sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\mikhail\AppData\Local\Temp\dos_graph.png'
    im2 = im.resize((W * 2, H * 2), Image.NEAREST)
    im2.save(out)
    print('saved', out, im2.size)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
