# -*- coding: utf-8 -*-
"""Чтение региона скриншота как пиксельного артa по 8px-колонкам (глиф = 8x11).

Использование: py scripts/_g2_read.py shot.png [x0 x1 y0 y1 [step]]
Без региона — все строки с чернилами. Вывод: одна строка на текстовую строку,
каждый глиф сжат до 2 символов (верх/низ), чтобы было читаемо в терминале.
"""
import sys
import numpy as np
from PIL import Image


def render(path, x0=0, x1=640, y0=0, y1=400, pitch=14):
    a = np.asarray(Image.open(path).convert('L')) > 150
    y1 = min(y1, a.shape[0]); x1 = min(x1, a.shape[1])
    for y in range(y0, y1, pitch):
        band = a[y:min(y + 11, y1)]
        if not band.any():
            continue
        top = band[:5]; bot = band[5:]
        line = []
        for x in range(x0, x1 - 7, 8):
            c1 = top[:, x:x + 8]; c2 = bot[:, x:x + 8]
            n1, n2 = c1.sum(), c2.sum()
            if n1 + n2 == 0:
                line.append('  ')
            elif n1 > 14 and n2 > 10:
                line.append('██')
            elif n1 > 12 and n2 <= 3:
                line.append('▀ ')
            elif n1 <= 3 and n2 > 10:
                line.append(' ▄')
            else:
                line.append(' ▪')
        print(f'{y:3}|' + ''.join(line))


if __name__ == '__main__':
    p = sys.argv[1]
    args = [int(v) for v in sys.argv[2:]]
    render(p, *args) if len(args) >= 4 else render(p)
