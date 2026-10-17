# -*- coding: utf-8 -*-
"""G2: печать отдельных клеток экрана с метками (для ручного декода глифов).
Использование: py _g2_cells.py shot.png r0 r1 c0 c1 [--dx N --dy N]
"""
import sys
from collections import Counter

import numpy as np
from PIL import Image

DX, DY = 3, 29


def main():
    argv = sys.argv
    dx, dy = DX, DY
    if '--dx' in argv:
        dx = int(argv[argv.index('--dx') + 1])
    if '--dy' in argv:
        dy = int(argv[argv.index('--dy') + 1])
    args = [a for a in argv[1:] if not a.startswith('--')]
    path = args[0]
    r0, r1, c0, c1 = map(int, args[1:5])
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.int16)

    def cell(r, c):
        cc = a[dy + r * 16:dy + r * 16 + 16, dx + c * 8:dx + c * 8 + 8]
        cols = Counter(map(tuple, cc.reshape(-1, 3)))
        bg = np.array(cols.most_common(1)[0][0], dtype=np.int16)
        return (np.abs(cc - bg).sum(axis=2) > 90).astype(np.uint8), cols.most_common(2)

    for r in range(r0, r1 + 1):
        for c in range(c0, c1 + 1):
            bm, top2 = cell(r, c)
            if bm.sum() < 2:
                continue
            bg = top2[0][0]
            inv = ' INV' if sum(v for k, v in top2) > 0 and top2[0][1] < 60 else ''
            print(f'--- r{r} c{c} ink={bm.sum()} bg={bg}{inv}')
            for y in range(12):
                print('   ' + ''.join('#' if v else '.' for v in bm[y]))


if __name__ == '__main__':
    main()
