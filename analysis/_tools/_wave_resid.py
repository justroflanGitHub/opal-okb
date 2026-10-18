# -*- coding: utf-8 -*-
"""Остатки волновых строк банка vs порт (TASK_MARCH): структура D(z)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis.golden_verify import compare_system  # noqa: E402


def main():
    names = sys.argv[1:] or ['121', 'OKULAR', 'OBEKTIV', 'S_KOND1',
                             'KURSOVIK', 'OPTICS#1', 'GTIE00', 'US00KI02']
    for name in names:
        try:
            res = compare_system(name)
        except Exception as e:               # noqa: BLE001
            print(f'== {name}: FAIL {e!r}')
            continue
        rows = [r for r in res['rows'] if r[1] == 'волновые']
        if not rows:
            print(f'== {name}: нет волновых строк')
            continue
        print(f'== {name}')
        print(f"  {'zone':>6} {'bank':>12} {'port':>12} {'D=bank-port':>12}"
              f" {'D/z^2':>12} {'D/z^4':>12} {'verd':>6}")
        for r in rows:
            _, _, zone, bank, port, d, tol, verd = r
            if port is None or bank is None:
                print(f'  {zone:>6} {bank} {port}')
                continue
            D = bank - port
            z2 = D / zone ** 2 if zone else 0.0
            z4 = D / zone ** 4 if zone else 0.0
            print(f'  {zone:>6.3f} {bank:>12.4f} {port:>12.4f} {D:>12.4f}'
                  f' {z2:>12.4f} {z4:>12.4f} {verd:>6}')


if __name__ == '__main__':
    main()
