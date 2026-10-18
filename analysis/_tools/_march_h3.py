# -*- coding: utf-8 -*-
"""TASK_MARCH2 зонд H3: структура требуемого замыкания E(z) марша.

E(z) = (банк − ΔOPL_vertex)·λ — что марш добавляет к OPL-до-вершины.
Сравниваем: точная сфера (гаусс-центр, вершина z_last и вых. зрачок),
S·sin(u), Σ n·T_s·X_s²/2 (тангенциальная труба диффтрассировки),
y⁴-члены. Цель — опознать замыкание как физическую величину.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from analysis._tools._march_h2 import _fan_zone_rows, _ray_of  # noqa: E402
from analysis.golden_verify import _n_media, paraxial_of, _paraxial_ray  # noqa: E402


def main():
    names = sys.argv[1:] or ['121', 'OKULAR', 'KURSOVIK', 'US00KI02',
                             'HELIOS8', 'S_KOND1', 'OBEKTIV']
    for name in names:
        try:
            prn, opj, system, wl, near, ax_semi, wave_rows = _fan_zone_rows(name)
        except Exception as e:               # noqa: BLE001
            print(f'== {name}: FAIL {e!r}')
            continue
        z_obj = opj.get('object_pos', 0.0)
        na = 0.0
        for (ws, nz), row in prn['gabarit'].items():
            if nz == 0 and row.get('Ax'):
                na = row['Ax']
        lam = wl * 1e-3
        media = _n_media(system, wl)
        z_last = sum(s.thickness for s in system.surfaces[:-1])
        if near:
            if z_obj < 0.0:
                y0, u0, z0p = 0.0, 0.05, z_obj
            else:
                z0p = -(abs(z_obj) + 100.0)
                u0 = -0.05
                y0 = (z_obj - z0p) * (-u0)
            yp, up = _paraxial_ray(system, wl, y0, u0, z0p)
            L_p = -yp / up if abs(up) > 1e-15 else None
        else:
            L_p = paraxial_of(system, wl)['bfd']
        sp = paraxial_of(system, wl)['sP_prime']
        chief = _ray_of(system, near, z_obj, na, ax_semi, 0.0, wl)

        def opl_vertex(res):
            """OPL до плоскости z_last (мм), по сегментам path."""
            o = 0.0
            for i in range(len(res.path) - 1):
                p0, p1 = res.path[i], res.path[i + 1]
                if p1[2] > z_last + 1e-9 and p0[2] <= z_last + 1e-9:
                    t = (z_last - p0[2]) / (p1[2] - p0[2])
                    pe = (p0[0] + t * (p1[0] - p0[0]),
                          p0[1] + t * (p1[1] - p0[1]), z_last)
                    o += math.dist(p0, pe) * media[min(i, len(media) - 1)]
                    break
                o += math.dist(p0, p1) * media[min(i, len(media) - 1)]
                if p1[2] > z_last - 1e-9:
                    break
            return o

        opl_cv = opl_vertex(chief)
        print(f'== {name}  λ={wl:.4f} L_p={L_p:.4f} sP\'={sp:.4f}'
              f' nsurf={len(system.surfaces)}')
        print(f"  {'zone':>5} {'банкλ':>10} {'E,мм':>10} {'t_sphere':>10}"
              f" {'t_vert.zp':>10} {'Ssin':>9} {'ΣnTX²/2':>10} {'y_last':>8}")
        for zone, bank in wave_rows:
            if zone == 0.0:
                continue
            res = _ray_of(system, near, z_obj, na, ax_semi, zone, wl)
            if not res.success:
                print(f'  {zone:>5.3f}: trace fail')
                continue
            dOPL = opl_vertex(res) - opl_cv
            E = bank * lam - dOPL            # требуемое замыкание, мм
            # выход
            pts = [p for p in res.path if p[2] <= z_last + 1e-9]
            y_last, z_exit = pts[-1][1], pts[-1][2]
            p0, p1 = res.path[-3], res.path[-2]
            dz = p1[2] - p0[2]
            slope = (p1[1] - p0[1]) / dz if abs(dz) > 1e-12 else 0.0
            sinu = slope / math.sqrt(1.0 + slope * slope)
            cosu = math.sqrt(max(0.0, 1.0 - sinu * sinu))
            Lz = z_exit - y_last / slope - z_last
            S = Lz - L_p
            # точное расширение до сферы центр=гаусс, вершина на оси z_last
            b = cosu * L_p - y_last * sinu
            disc = b * b - y_last * y_last
            t_sph = (b - math.sqrt(disc)) if disc > 0 else float('nan')
            # сфера с вершиной в плоскости выходного зрачка
            zp = z_last + sp
            R2 = (z_last + L_p) - zp
            b2 = cosu * R2 - (y_last + slope * 0.0) * sinu \
                if R2 != 0 else float('nan')
            # (упрощённо: тот же угол, точка на z_last) — точная форма ниже
            # Σ n·T_s·X_s²/2 — диффтрассировка (чистая)
            res_b = _ray_of(system, near, z_obj, na, ax_semi,
                            zone * 1.0005, wl)
            sumT = 0.0
            if res_b.success:
                n = min(len(res.path), len(res_b.path))
                for i in range(1, n):
                    a0, a1 = res.path[i - 1], res.path[i]
                    b0, b1 = res_b.path[i - 1], res_b.path[i]
                    dza = a1[2] - a0[2]
                    dzb = b1[2] - b0[2]
                    if abs(dza) < 1e-12 or abs(dzb) < 1e-12:
                        continue
                    slope_a = (a1[1] - a0[1]) / dza   # наклон входа в повер.i
                    slope_b = (b1[1] - b0[1]) / dzb
                    dy = a1[1] - b1[1]
                    if abs(dy) < 1e-15:
                        continue
                    T = (slope_b - slope_a) / dy
                    ym = 0.5 * (a1[1] + b1[1])
                    sumT += media[min(i, len(media) - 1)] * T * ym * ym / 2.0
            print(f'  {zone:>5.3f} {bank:>10.4f} {E:>10.5f} {t_sph:>10.5f}'
                  f' {"—":>10} {S * sinu:>9.4f} {sumT:>10.5f} {y_last:>8.3f}')


if __name__ == '__main__':
    main()
