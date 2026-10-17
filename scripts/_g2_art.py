# -*- coding: utf-8 -*-
"""G2: печать строк экрана ASCII-артом (по клеткам 8x16) для чтения глифов.
Использование: py _g2_art.py shot.png r0 r1 [c0 c1] [--dx N --dy N]
"""
import sys
from collections import Counter

import numpy as np
from PIL import Image

DX, DY = 3, 29
CW, CH = 8, 16


def cell_bitmap(a, y0, x0):
    cell = a[y0:y0 + CH, x0:x0 + CW]
    flat = cell.reshape(-1, 3)
    colors = Counter(map(tuple, flat))
    bg = np.array(colors.most_common(1)[0][0], dtype=np.int16)
    dist = np.abs(cell - bg).sum(axis=2)
    return (dist > 90).astype(np.uint8)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    path = args[0]
    r0, r1 = int(args[1]), int(args[2])
    c0, c1 = (int(args[3]), int(args[4])) if len(args) > 4 else (0, 80)
    dx, dy = DX, DY
    argv = sys.argv
    if '--dx' in argv:
        dx = int(argv[argv.index('--dx') + 1])
    if '--dy' in argv:
        dy = int(argv[argv.index('--dy') + 1])
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.int16)
    for r in range(r0, r1 + 1):
        rowcells = []
        for c in range(c0, c1):
            bm = cell_bitmap(a, dy + r * CH, dx + c * CW)
            rowcells.append(bm)
        # 16 строк арта
        print(f'== row {r} (cols {c0}..{c1 - 1}) ==')
        for y in range(CH):
            line = ''
            for bm in rowcells:
                line += ''.join('#' if v else '.' for v in bm[y])
            print(line)


if __name__ == '__main__':
    main()
