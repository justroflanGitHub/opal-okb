# -*- coding: utf-8 -*-
"""Итеративный OCR экрана OPAL: алфавит строится из known-plaintext и растёт вручную.

Алфавит хранится в scripts/_g2_alphabet.json: {"C": [[row bits]...], ...}.
Каждый глиф — 16 строк x 8 колонок bool (вырезка band[y0:y0+16] вокруг строки).
Использование:
  py scripts/_g2_font.py learn shot.png 0 0 'Cистема-'   # y-строка 0, cell 0.., текст
  py scripts/_g2_font.py ocr shot.png [row]               # печать декода всех строк
"""
import json
import os
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
ALPHA = os.path.join(os.path.dirname(__file__), '_g2_alphabet.json')
PITCH = 14
GH = 16          # высота вырезки глифа (строка + хвосты)


def load_alpha():
    if os.path.exists(ALPHA):
        return {k: np.array(v, dtype=bool) for k, v in json.load(open(ALPHA)).items()}
    return {}


def save_alpha(a):
    json.dump({k: v.tolist() for k, v in a.items()}, open(ALPHA, 'w'))


def bands(img):
    a = np.asarray(Image.open(img).convert('L')) > 150
    out = []
    for y in range(0, a.shape[0] - 3, PITCH):
        if a[y:y + 11].any():
            out.append(y)
    return a, out


def cell_of(a, y, x):
    """Глиф с центром строки y: вырезка [y-2 : y+14) — верх/низ для выносных."""
    return a[max(0, y - 2):y - 2 + GH, x:x + 8]


def learn(img, row, col0, text):
    a, bs = bands(img)
    y = bs[row]
    alpha = load_alpha()
    for i, ch in enumerate(text):
        if ch == ' ':
            continue
        g = cell_of(a, y, (col0 + i) * 8)
        alpha[ch] = g
        print(f'{ch!r} learned ({g.sum()} ink)')
    save_alpha(alpha)


def match(g, alpha):
    best, bd = None, 10 ** 9
    for ch, t in alpha.items():
        h = min(g.shape[0], t.shape[0])
        d = int((g[:h] != t[:h]).sum())
        if d < bd:
            best, bd = ch, d
    return best, bd


def ocr(img, row=None):
    a, bs = bands(img)
    alpha = load_alpha()
    print('alphabet:', ''.join(sorted(alpha.keys())), f'({len(alpha)})')
    rows = bs if row is None else [bs[row]]
    for y in rows:
        line, raw = [], []
        for x in range(0, a.shape[1] - 7, 8):
            g = cell_of(a, y, x)
            if not g.any():
                line.append(' ')
                continue
            ch, d = match(g, alpha)
            if d <= 10:
                line.append(ch)
            else:
                line.append('□')
                raw.append((x // 8, d))
        print(f'{y:3}|' + ''.join(line).rstrip())
        if raw:
            print(f'    unknown cells: {raw[:20]}')


def dump(img, row, c0, c1):
    """Печать глифов [c0,c1) строки row для ручного декода."""
    a, bs = bands(img)
    y = bs[row]
    for c in range(c0, c1):
        g = cell_of(a, y, c * 8)
        if not g.any():
            continue
        print(f'--- cell {c} (x={c*8})')
        for r in g:
            print('   ' + ''.join('#' if v else '.' for v in r))


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'learn':
        learn(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    elif cmd == 'ocr':
        ocr(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else None)
    elif cmd == 'dump':
        dump(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))
