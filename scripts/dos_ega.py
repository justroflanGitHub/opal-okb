# -*- coding: utf-8 -*-
"""Рендер EGA/VGA-графики (режим 0x10/0x12) из кучи DOSBox.
Раскладка vga.mem.linear в DOSBox 0.74 (unchained): плоскости КОНТИГУАЛЬНЫЕ,
плоскость p занимает linear[p*0x10000 .. +0x10000]; CPU-адрес A0000+x ->
плоскость x&3, байт внутри плоскости x>>2.
Ищем 4 подряд идущих 64KB-окна с доминирующим фоном (0xFF или 0x00).
Выход: PNG. --addr HEX — база вручную (тогда скан пропускаем).
"""
import ctypes
import sys

sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
from dosbox_rd import get_pid

k32 = ctypes.windll.kernel32

EGA_LUM = [0x00, 0xAA, 0x55, 0xFF, 0xAA, 0xFF, 0x55, 0xFF,
           0x55, 0xFF, 0xAA, 0xFF, 0xAA, 0xFF, 0xAA, 0xFF]


def regions(h):
    mbi = ctypes.create_string_buffer(48)
    addr = 0
    while addr < 0x7FFFFFFF:
        if k32.VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000
            continue
        base = int.from_bytes(mbi[0:8], 'little')
        size = int.from_bytes(mbi[24:32], 'little')
        state = int.from_bytes(mbi[32:36], 'little')
        prot = int.from_bytes(mbi[36:40], 'little')
        if state == 0x1000 and (prot & 0x4) and size >= 65536:
            yield base, size
        addr = base + size if base + size > addr else addr + 0x1000


def main():
    W, H = 640, 350
    P = 0x10000
    pid = get_pid()
    h = k32.OpenProcess(0x410, False, pid)

    def read(a, n):
        b = ctypes.create_string_buffer(n)
        g = ctypes.c_size_t(0)
        r = k32.ReadProcessMemory(h, ctypes.c_void_p(a), b, n, ctypes.byref(g))
        return b.raw[:g.value] if r else None

    fixed = len(sys.argv) > 2 and sys.argv[1] == '--addr'
    base_fb = None
    if fixed:
        base_fb = int(sys.argv[2], 16)
    else:
        # скан: страница 256KB, все 4 подвинга с одинаковым доминирующим байтом
        best = None
        for base, size in regions(h):
            if size < 4 * P:
                continue
            d = read(base, size)
            if not d:
                continue
            vis = 80 * H               # видимая область плоскости
            for off in range(0, len(d) - 4 * P, 0x1000):
                q = d[off:off + 4 * P]
                nz = 4 * P - q.count(0)
                if nz < 1500 or nz > 60000:   # текст ~1-3% от окна
                    continue
                # структура: ненулевые байты в каждой четверти (обе раскладки)
                quarters = [q[i * P:(i + 1) * P].count(b'\x00'[-1:]) if False
                            else (P - q[i * P:(i + 1) * P].count(0)) for i in range(4)]
                if min(quarters) < 150:
                    continue
                score = sum(abs(quarters[i] - quarters[i + 1]) for i in range(3))
                if best is None or score < best[0]:
                    best = (score, base + off)
        if not best:
            print('# no framebuffer found')
            k32.CloseHandle(h)
            return
        base_fb = best[1]
        print('# framebuffer @%X score=%d (равномерность ненулевых)' % (base_fb, best[0]))

    need = 80 * H  # байт на плоскость
    planes = [read(base_fb + p * P, need) for p in range(4)]
    from PIL import Image
    im = Image.new('L', (W, H), 255)
    px = im.load()
    for y in range(H):
        for xb in range(80):
            b0, b1, b2, b3 = planes[0][y*80+xb], planes[1][y*80+xb], planes[2][y*80+xb], planes[3][y*80+xb]
            for bit in range(8):
                idx = (((b3 >> (7 - bit)) & 1) << 3) | (((b2 >> (7 - bit)) & 1) << 2) | \
                      (((b1 >> (7 - bit)) & 1) << 1) | ((b0 >> (7 - bit)) & 1)
                px[xb * 8 + bit, y] = 255 - EGA_LUM[idx]  # палитра: 0=белый фон
    k32.CloseHandle(h)
    out = sys.argv[-1] if sys.argv[-1].endswith('.png') else r'C:\Users\mikhail\AppData\Local\Temp\dos_ega.png'
    im2 = im.resize((W * 2, H * 2), Image.NEAREST)
    im2.save(out)
    print('saved', out, im2.size)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
