# -*- coding: utf-8 -*-
"""Марш-конвейер печати OPAL — симуляция и сверка с банком (TASK_MARCH2).

Дизасм-карта конвейера (REVERSE_OPALDIS.md §M.1–M.5; полный вывод хвоста
cd62 — analysis/reverse_data/march_cd62_tail.txt):

* запуск 0x9d7a — два чертежа (A/B): семена [4bc6]=[3b88]/t,
  [4bce]=[3b90]/t; позиция [3bd0..3be0], направление [3be8..3bf8]
  (нормировка [3c00]=1−dx²−dy²=dz², отказ [0x39d0]=1 при dz²≤0);
  записи [3c58+0x18k]/[3d18+0x18k]←0 (k≤8); счётчик [0x39e4]=−зона;
* шаг 0x93f3 — точная сфера L_s=(cos−√(cos²−A·D))/A−r·d̂ (lcall ff9:19),
  каскад W₂=(W₂+L_s)·head (0x9435, head=qword[4d20] λ-слота), микс
  rec_k=(v_k+1)·rec_k·head+v_k·W₂ (0x9497, c₀=[2d6e]=1.0), рекуррентность
  записей (x,d)→(−(c·x+d), x) (0x94cc/0x95c8), экспорт f32=−[3be8]−acc
  (0x9627); зеркальная ветка (A,B)→(−cos·(B+c·A), cos·A) (0x968d);
* шаг-замыкание cd62 — adj-матрица N из локальной 2×2 [[3ca0,3ca8],
  [3cb8,3cc0]] c det=[4d9e] (0xcde9; вырождение → отказ печати);
  кромочные проверки f32(ap_x)·[3be8]≤0 И f32(ap_y)·[3bf0]≤0 →
  [4dca]=−1 (0xcd95–0xcdd3); тензор-solve (0xce76+); замыкание 0xd074:
  W₂[3c28] += head·(x²·T11+2xy·T12+y²·T22)/2, (x,y)=([3bd0],[3bd8]);
  M-трансформации 0xd147: (x,y), труба ([3c70],[3c78]) и пара
  ([3c88],[3c90]) ← M·v, M=[[3d30,3d38],[3d48,3d50]]; обратная ветка
  0xd28c (U ← M⁻¹U по строкам, det-деление); зеркальная ветка
  [0x39e2]<0 → 0xd6d4 (печать p=[4dca]·dy²/(A·(dz+1)));
* печать 0xd9c5+ — волна = ΔW₂ − S·sin(u), S — марш-прод трубы.

Статически НЕ извлекаемые семена (локализация в дизасме):
* head qword[4d20] — пишется рантайм-преломлением ff9:19 (sub
  0x138b7/0x147b3); физически n_пад/n_прел (телескоп Πhead=n_вх/n_вых,
  для систем, окончившихся воздухом, Πhead=1 → W₂=OPL+ΣQF/2 —
  подтверждено 307 GREEN строками банка);
* v_k наклонов qword[4c4a+8k] — заполняет живой драйвер 0xbe4f (arg3,
  после lcall ff9:294b/2ecc);
* блок запуска [3b78..3bc0]/[3a90..3ad0] — подготовка 0xb375/0xbce6/
  0xba3f (f32-таблицы OPJ: смещение [4c88]·строка + [4c7c]·4).
Поэтому λ-уровень точности печати (тензор T/труба S) статически
недостижим; модуль даёт: (а) точный геометрический конвейер и его
инварианты (телескоп W₂/OPL, Πhead), (б) кромочные/ЗЕРКАЛЬНЫЕ флаги
веток по декодированным условиям, (в) сверку с банком и точные причины
остатков (:func:`march_report`).

Запуск: ``py -X utf8 analysis/golden_march.py [СИСТЕМЫ…]``
(без аргументов — RED/YELLOW-носители волновых остатков).
"""
import math
import os
import sys

from analysis.golden_verify import (  # noqa: E402
    parse_golden_prn, parse_golden_opj, opj_to_system, _n_media,
    paraxial_of, _paraxial_ray, _GOLDEN_DOS,
)

BANK_DIR = os.path.join(os.path.dirname(__file__), 'reverse_data',
                        'golden', 'bank')

#: носители волновых остатков RED/YELLOW (TASK_MARCH2 §M.4)
DEFAULT_SYSTEMS = ['121', 'OKULAR', 'KURSOVIK', 'S_KOND1', 'OBEKTIV']


# --------------------------------------------------------------------------
# запуск луча (ветки A/B рутины 0x9d7a; геометрия — порт-трейсер,
# дающий ту же точную сферу L_s=(cos−√(cos²−A·D))/A−r·d̂)
# --------------------------------------------------------------------------
def ray_of(system, near, z_obj, na, ax_semi, zone, wl):
    """Осевой веерный луч зоны ``zone`` (дальняя/ближняя ветка запуска)."""
    if not near:
        from analysis.aberrations import _compute_ray_start
        from domain.calculations import paraxial_trace
        from optics_utils import make_field_ray
        from ray_tracing import trace_ray_through_system
        parax = paraxial_trace(system, wl=wl)
        z_start, z_pupil = _compute_ray_start(system, parax)
        return trace_ray_through_system(
            system, make_field_ray(system, 0.0, zone * ax_semi, 0.0,
                                   z_start, z_pupil), wl)
    from ray_tracing import Ray, trace_ray_through_system
    su = na * zone
    if z_obj < 0.0:
        ray = Ray(0.0, 0.0, z_obj, 0.0, su, math.sqrt(1.0 - su * su))
    else:
        tu = su / math.sqrt(1.0 - su * su)
        z0 = -(abs(z_obj) + 100.0)
        ray = Ray(0.0, (z_obj - z0) * tu, z0, 0.0, -su,
                  math.sqrt(1.0 - su * su))
    return trace_ray_through_system(system, ray, wl)


def fan_context(name, bank_dir=BANK_DIR, opj_dir=_GOLDEN_DOS):
    """Сшивка зон волновых строк банка (как compare_system)."""
    prn = parse_golden_prn(os.path.join(bank_dir, name + '.PRN'))
    opj = parse_golden_opj(os.path.join(opj_dir, name + '.OPJ'))
    system = opj_to_system(opj)
    wl = opj['wls'][0]
    near = (opj['obj_type'] == 1)
    hzr_vals = [r['h_zr'] for r in prn['axial2'].get('rows', {}).values()
                if r.get('h_zr') is not None]
    ax_semi = max(hzr_vals) if hzr_vals else opj['aperture_semi']
    zones_sorted = sorted(prn['axial1'].get('rows', {}).keys(), reverse=True)
    na = 0.0
    for (ws, nz), row in prn['gabarit'].items():
        if nz == 0 and row.get('Ax'):
            na = row['Ax']
    scale = ax_semi if not near else 100.0 * (na or opj['aperture_semi'])
    used, wave_rows = set(), []
    for tg, et in sorted(prn['axial2'].get('rows', {}).items(),
                         key=lambda kv: -kv[1]['tg100']):
        if not et.get('wave') or et['wave'][0] is None:
            continue
        hzr = et.get('h_zr')
        z = None
        if hzr is not None and scale:
            z = min(zones_sorted, key=lambda zz: abs(zz - hzr / scale))
        if z is None or z in used:
            z = next((zz for zz in zones_sorted if zz not in used), None)
        if z is None:
            break
        used.add(z)
        wave_rows.append((z, et['wave'][0]))
    return prn, opj, system, wl, near, ax_semi, na, wave_rows


def surface_semis(prn, wl):
    """Пер-поверхностные y-полудиаметры габарита (столбец Ay)."""
    out = {}
    for (ws, n), row in prn['gabarit'].items():
        if ws == wl or wl is None:
            out[n] = max(abs(row.get('Ay', 0.0)), abs(row.get('Ax', 0.0)))
    return out


# --------------------------------------------------------------------------
# шаг конвейера: сегмент → L_s, head, TIR-диагностика, кромка
# --------------------------------------------------------------------------
def march_ray(system, wl, media, res, semis):
    """Конвейер геометрии марша по трассе ``res``.

    Возвращает словарь состояния: OPL-часть W₂ (телескоп каскада
    W₂=(W₂+L_s)·head при head=n_пад/n_прел — для воздушного окончания
    Πhead=1, W₂=Σn_s·L_s), произведение head, кромочные отношения
    |y_s|/Ay_s и поверхность TIR (ветка [0x39e2]/0xd6d4, если есть).
    """
    z_last = sum(s.thickness for s in system.surfaces[:-1])
    w2, head_prod = 0.0, 1.0
    opl_direct = 0.0
    rim_max, rim_surf = 0.0, None
    tir_surf = None
    segments = 0
    for i in range(len(res.path) - 1):
        p0, p1 = res.path[i], res.path[i + 1]
        if p1[2] > z_last + 1e-9 and p0[2] <= z_last + 1e-9:
            t = (z_last - p0[2]) / (p1[2] - p0[2])
            pe = (p0[0] + t * (p1[0] - p0[0]),
                  p0[1] + t * (p1[1] - p0[1]), z_last)
            seg, hit = math.dist(p0, pe), pe
            partial = True
        else:
            seg, hit, partial = math.dist(p0, p1), p1, False
        n_inc = media[min(i, len(media) - 1)]
        n_ref = media[min(i + 1, len(media) - 1)]
        # head = n_пад/n_прел (ff9:19); reflекция → n_ref=−n_inc, head=−1
        surf = system.surfaces[i] if i < len(system.surfaces) else None
        is_mirror = bool(getattr(surf, 'is_reflective', False)
                         ) if surf is not None else False
        head = (-1.0 if is_mirror or n_ref == -n_inc
                else n_inc / n_ref if n_ref else 1.0)
        # каскад 0x9435: W₂=(W₂+L_s)·head
        w2 = (w2 + seg) * head
        head_prod *= head
        opl_direct += n_inc * seg
        segments += 1
        # кромка: |y| на поверхности против габаритного полудиаметра
        sidx = i + 1                     # точка p1 лежит на поверхности i+1
        ay = semis.get(sidx)
        if ay and abs(hit[1]) / ay > rim_max:
            rim_max, rim_surf = abs(hit[1]) / ay, sidx
        # TIR: n_пад·sinθ > n_прел на преломляющей границе
        if (tir_surf is None and surf is not None and not is_mirror
                and n_ref != n_inc and n_ref > 0):
            rad = surf.radius or 0.0
            zc = (sum(s.thickness for s in system.surfaces[:i])
                  + (rad if rad else 0.0))
            ry = hit[1]
            rn = math.sqrt(ry * ry + (hit[2] - zc) ** 2) or 1.0
            cos_i = abs((hit[2] - zc) * (p1[2] - p0[2])
                        + ry * (p1[1] - p0[1])) / (
                seg * rn) if seg > 1e-12 else 1.0
            cos_i = min(1.0, max(0.0, cos_i))
            if n_inc * n_inc * (1.0 - cos_i * cos_i) > n_ref * n_ref:
                tir_surf = sidx
        if partial:
            break
    return {'w2_opl': w2, 'head_prod': head_prod,
            'opl_direct': opl_direct, 'rim_max': rim_max,
            'rim_surf': rim_surf, 'tir_surf': tir_surf,
            'segments': segments}


# --------------------------------------------------------------------------
# сверка с банком: строка → причина остатка
# --------------------------------------------------------------------------
def march_report(name, verbose=True):
    """Таблица зон: банк, порт-ОPL-часть марша, кромка/TIR, причина."""
    prn, opj, system, wl, near, ax_semi, na, wave_rows = fan_context(name)
    media = _n_media(system, wl)
    semis = surface_semis(prn, wl)
    z_obj = opj.get('object_pos', 0.0)
    chief = ray_of(system, near, z_obj, na, ax_semi, 0.0, wl)
    chief_state = march_ray(system, wl, media, chief, semis)
    rows = []
    for zone, bank in wave_rows:
        res = ray_of(system, near, z_obj, na, ax_semi, zone, wl)
        if not res.success:
            rows.append({'zone': zone, 'bank': bank, 'trace': 'fail'})
            continue
        st = march_ray(system, wl, media, res, semis)
        d_w2 = st['w2_opl'] - chief_state['w2_opl']       # ΔW₂ (OPL-часть)
        # причина остатка против банка
        causes = []
        if st['tir_surf'] is not None:
            causes.append(f'TIR@пов{st["tir_surf"]} — зеркальная ветка '
                          'марша (0xd6d4), порт не имеет зеркальной трубы')
        if st['rim_max'] > 0.97:
            causes.append(f'кромка пов{st["rim_surf"]} '
                          f'({st["rim_max"]:.3f}·габарит) — приповерхностная'
                          ' ветка [4dca]')
        if zone == 1.0 and abs(st['head_prod'] - 1.0) < 1e-12 and not causes:
            causes.append('зона 1.0: идентификация луча (см. пин-тест '
                          'test_kursovik_march_tube_limit_ray)')
        rows.append({'zone': zone, 'bank': bank, 'dw2_lambda':
                     d_w2 / (wl * 1e-3), **st, 'causes': causes})
    if verbose:
        print(f'== {name}  λ={wl:.4f}  Πhead={chief_state["head_prod"]:.6f}'
              f'  сегментов={chief_state["segments"]}')
        print(f"  {'зона':>6} {'банкλ':>10} {'ΔW₂ opl λ':>11}"
              f" {'разность':>10} {'кромка':>7} {'пов':>4} {'TIR':>4}  причины")
        for r in rows:
            if 'trace' in r:
                print(f"  {r['zone']:>6.3f}  trace fail")
                continue
            diff = r['bank'] - r['dw2_lambda']
            print(f"  {r['zone']:>6.3f} {r['bank']:>10.4f}"
                  f" {r['dw2_lambda']:>11.4f} {diff:>10.4f}"
                  f" {r['rim_max']:>7.3f} {r['rim_surf'] or '—':>4}"
                  f" {r['tir_surf'] or '—':>4}  {'; '.join(r['causes'])}")
    return rows


def main(argv=None):
    names = (argv if argv is not None else sys.argv[1:]) or DEFAULT_SYSTEMS
    for name in names:
        try:
            march_report(name)
        except Exception as e:                    # noqa: BLE001
            print(f'== {name}: FAIL {e!r}')


if __name__ == '__main__':
    main()
