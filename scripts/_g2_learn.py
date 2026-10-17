# -*- coding: utf-8 -*-
"""G2: обучение карты глифов по таблице п.6 на скрине (значения = RT__2236).
Находит 5 строк данных, выравнивает прогоны клеток на известные группы чисел,
печатает карту (hex-битмап -> символ) и проверяет согласованность.
"""
import json
import sys
from collections import Counter, defaultdict

import numpy as np
from PIL import Image

DX, DY = 3, 29
CW, CH = 8, 16
COLS, ROWS = 80, 25

# 5 строк первой таблицы на экране: koop | продольные | поперечные
GOLDEN = [
    ('1.000', '-.09008', '.062432'),
    ('.866', '-.05594', '.032631'),
    ('.707', '-.03000', '.013023'),
    ('.500', '-.01158', '.002462'),
    ('.000', '.00000', '.000000'),
]
# 5 строк второй таблицы (волновые): Tg'*100 | W | Неизопл | Н ЗР
GOLDEN2 = [
    ('-20.684', '.7532', '-.3546', '5.0000'),
    ('-17.880', '.3620', '-.1628', '4.3301'),
    ('-14.582', '.1354', '-.0465', '3.5355'),
    ('-10.306', '.0279', '.0050', '2.5000'),
    ('.000', '.0000', '.0000', '.0000'),
]


def cell_bitmap(a, y0, x0):
    cell = a[y0:y0 + CH, x0:x0 + CW]
    flat = cell.reshape(-1, 3)
    colors = Counter(map(tuple, flat))
    bg = np.array(colors.most_common(1)[0][0], dtype=np.int16)
    dist = np.abs(cell - bg).sum(axis=2)
    return (dist > 90).astype(np.uint8)


def row_cells(a, r, dx, dy):
    out = {}
    for c in range(COLS):
        bm = cell_bitmap(a, dy + r * CH, dx + c * CW)
        if bm.sum() >= 2:
            out[c] = bm
    return out


def runs(cells):
    """Непустые клетки -> прогоны [(c0,c1,...)]."""
    cs = sorted(cells)
    out = []
    cur = []
    for c in cs:
        if cur and c == cur[-1] + 1:
            cur.append(c)
        else:
            if cur:
                out.append(cur)
            cur = [c]
    if cur:
        out.append(cur)
    return out


def try_align(cells, groups):
    """Прогоны строки -> группы известного текста. None если нет матча."""
    rr = runs(cells)
    if len(rr) != len(groups):
        return None
    mapping = {}
    for run, txt in zip(rr, groups):
        if len(run) != len(txt):
            return None
        for c, ch in zip(run, txt):
            mapping[cells[c].tobytes()] = ch
    return mapping


def frame_cols(allrows):
    """Колонки-кандидаты на рамку: один и тот же битмап в >=15 строках."""
    bycol = defaultdict(list)
    for r, cells in allrows.items():
        for c, bm in cells.items():
            bycol[(c, bm.tobytes())].append(r)
    bad = set()
    for (c, key), rs in bycol.items():
        if len(rs) >= 15:
            bad.add((c, key))
    return bad


def main():
    path = sys.argv[1]
    dx, dy = DX, DY
    if '--dx' in sys.argv:
        dx = int(sys.argv[sys.argv.index('--dx') + 1])
    if '--dy' in sys.argv:
        dy = int(sys.argv[sys.argv.index('--dy') + 1])
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.int16)
    # все строки: клетки
    allrows = {r: row_cells(a, r, dx, dy) for r in range(ROWS)}
    bad = frame_cols(allrows)
    for r, cells in allrows.items():
        for c in list(cells):
            if (c, cells[c].tobytes()) in bad:
                del cells[c]
    fontmap = {}
    conflicts = 0
    used_rows = []
    for base in range(ROWS - 4):
        five = range(base, base + 5)
        # все 5 строк должны иметь прогоны как в GOLDEN (3 группы)
        ok = True
        maps = []
        for r, gold in zip(five, GOLDEN):
            m = try_align(allrows[r], gold)
            if m is None:
                ok = False
                break
            maps.append(m)
        if ok:
            used_rows.append(('T1', base))
            for m in maps:
                for k, v in m.items():
                    if k in fontmap and fontmap[k] != v:
                        conflicts += 1
                    fontmap[k] = v
        ok = True
        maps = []
        for r, gold in zip(five, GOLDEN2):
            m = try_align(allrows[r], gold)
            if m is None:
                ok = False
                break
            maps.append(m)
        if ok:
            used_rows.append(('T2', base))
            for m in maps:
                for k, v in m.items():
                    if k in fontmap and fontmap[k] != v:
                        conflicts += 1
                    fontmap[k] = v
    print('aligned row-blocks:', used_rows, 'conflicts:', conflicts)
    print('learned glyphs:', len(fontmap))
    hexmap = {k.hex(): v for k, v in fontmap.items()}
    out = path + '.fontmap.json'
    json.dump(hexmap, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
    print('saved', out)


if __name__ == '__main__':
    main()
