# -*- coding: utf-8 -*-
"""OCR экрана OPALTRAN (EGA 640x400, текст KEYRUS 8x16/11 активных строк, питч 14px).

Шрифт: KEYRUS.COM таблица @0x45d0 (256 глифов x 16 байт, активные ~11 строк).
Экранная строка: глиф занимает верхние ~11 пикселей 14-пиксельного питча.
Использование:
  py scripts/_g2_ocr.py shot.png [x0 x1]       — авто: все строки с текстом
"""
import sys
import numpy as np
from PIL import Image

FONT_OFF = 0x45D0


def load_font():
    d = open(r'C:\GOLDEN_DOS\KEYRUS.COM', 'rb').read()
    glyphs = []
    for c in range(256):
        rows = []
        for r in range(11):                      # активные строки глифа
            bits = d[FONT_OFF + c * 16 + r]
            rows.append(np.array([(bits >> (7 - k)) & 1 for k in range(8)], dtype=np.uint8))
        glyphs.append(np.stack(rows))
    return glyphs


def ocr_line(patch, glyphs):
    """patch: HxW uint8 (1=текст). Возвращает строку и среднюю ошибку."""
    h, w = patch.shape
    # лучший x-фазовый сдвиг: максимум текстовых пикселей на сетке 8px
    best = None
    for phase in range(8):
        cols_ok = 0
        for x in range(phase, w - 7, 8):
            cols_ok += patch[:, x:x + 8].sum()
        # штраф: пиксели вне клеток (x%8 в хвосте фазы)
        if best is None or cols_ok > best[0]:
            best = (cols_ok, phase)
    phase = best[1]
    out = []
    for x in range(phase, w - 7, 8):
        cell = patch[:, x:x + 8]
        if cell.sum() == 0:
            out.append(' ')
            continue
        bestd, bestc = 1e9, 0
        for c, g in enumerate(glyphs):
            gh, gw = g.shape
            # глиф в верхних строках клетки
            gg = np.zeros_like(cell)
            gg[:gh, :gw] = g
            n = cell.size
            dist = int((gg != cell).sum())
            if dist < bestd:
                bestd, bestc = dist, c
        ch = chr(bestc)
        try:
            ch = bytes([bestc]).decode('cp866')
        except Exception:
            ch = '?'
        out.append(ch if bestd <= 12 else '□')
        if bestd > 12:
            out.append(f'[{bestd}]')
    return ''.join(out)


def main():
    path = sys.argv[1]
    x0, x1 = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 640)
    im = np.asarray(Image.open(path).convert('L')) > 150
    glyphs = load_font()
    # гасим сплошные линии (рамки/разделители): строки и столбцы с >70% чернил
    rowink = im[:, x0:x1].mean(axis=1)
    colink = im[:, :].mean(axis=0)
    im = im.copy()
    im[rowink > 0.7, :] = False
    im[:, colink > 0.7] = False
    prof = im[:, x0:x1].sum(axis=1)
    y = 0
    lines = []
    while y < im.shape[0] - 10:
        if prof[y:y + 11].sum() > 8:
            y1 = y
            while y1 < im.shape[0] and prof[max(0, y1 - 2):y1 + 3].sum() > 0:
                y1 += 1
            patch = im[y:max(min(y1, y + 13), y + 11), x0:x1]
            txt = ocr_line(patch.astype(np.uint8), glyphs)
            lines.append((y, min(y1, y + 13), txt))
            y = y1 + 3
        else:
            y += 1
    for y, y1, t in lines:
        print(f'{y:3}|{t.rstrip()}')


if __name__ == '__main__':
    main()
