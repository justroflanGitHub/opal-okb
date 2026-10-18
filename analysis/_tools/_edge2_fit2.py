# -*- coding: utf-8 -*-
"""TASK_EDGE2: финальная подгонка λ-таблицы — приоритет зоны 1.0.

Лемма: прод/попер з.1.0 обязаны GREEN (≤1e-3); остальные зоны — лучшие
возможные. Скан (q0,q1) с отрицательными q (OKULAR: λ>1) и лексико-
графической целевой: (max d на з.1.0 прод+попер, max d на всех).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..'))

from analysis._tools._edge2_fit import equations


def fit2(name):
    eqs, sp = equations(name)
    pp = [(z, kind, bank, port, power) for z, kind, bank, port, power in eqs
          if kind in ('прод', 'попер')]
    tg = [(z, kind, bank, port, power) for z, kind, bank, port, power in eqs
          if kind == 'Tg']
    best = None
    q0, q1 = -0.025, -0.006
    while q0 < 0.055:
        q1 = -0.006
        while q1 < 0.006:
            m1 = 0.0
            for z, kind, bank, port, power in pp:
                if z != 1.0:
                    continue
                lam = 1.0 - (q0 + q1 * z * z) * z * z
                m1 = max(m1, abs(port * lam ** power - bank) / abs(bank))
            if best is not None and m1 > best[0] * 1.5:
                q1 += 0.00005
                continue
            mx = m1
            for z, kind, bank, port, power in pp:
                lam = 1.0 - (q0 + q1 * z * z) * z * z
                mx = max(mx, abs(port * lam ** power - bank) / abs(bank))
            if best is None or (m1, mx) < (best[0], best[1]):
                best = (m1, mx, q0, q1)
            q1 += 0.00005
        q0 += 0.0002
    m1, mx, q0, q1 = best
    print('== %s: q0=%.5f q1=%.5f  max d(з.1.0)=%.2e  max d(все)=%.2e'
          % (name, q0, q1, m1, mx))
    q = q0 + q1
    print('   λ(1.0)=%.6f  λ(0.866)=%.6f  λ(0.707)=%.6f  λ(0.5)=%.6f'
          % (1 - q, 1 - (q0 + q1 * 0.75) * 0.75,
             1 - (q0 + q1 * 0.5) * 0.5, 1 - (q0 + q1 * 0.25) * 0.25))
    for z, kind, bank, port, power in sorted(pp + tg, key=lambda e: -e[0]):
        lam = 1.0 - (q0 + q1 * z * z) * z * z
        pred = port * lam ** power
        print('  %-4s z%.3f: банк=%12.5f предикт=%12.5f d=%.2e'
              % (kind, z, bank, pred, abs(pred - bank) / abs(bank)))
    return q0, q1


if __name__ == '__main__':
    for nm in (sys.argv[1:] or ['OBEKTIV', 'OKULAR']):
        fit2(nm)
