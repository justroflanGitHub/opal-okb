# TASK_ZERN: B3 — Цернике 28 членов (n≤12) + МНК-разложение (по реверс-досье)

## Цель
REVERSE_OPAVA.md: OPAL использует Цернике-базис **28 членов до n=12** (порт:
15 до 4-го порядка). Реализовать полный OPAL-базис + разложение волновой
аберрации МНК (Noll-подобное, как в OPAVA) + сверка с разложением OPAL.

## Материалы
- analysis/REVERSE_OPAVA.md (базис 28 членов — состав/нумерация!),
  analysis/REVERSE_OPALO.md (генерация базиса)
- Существующее: analysis/strehl.py, psf_mtf.py (pupil W-грид),
  aberrations.py::trace_wavefront_hexapolar
- Эталон: RT__2236.PRN (W по зонам)

## Реализация — analysis/zernike.py (НОВЫЙ)
```python
ZERNIKE_TERMS_28 = [...]  # (n, m) список из REVERSE_OPAVA (28 шт., n≤12)
def zernike_basis(grid) -> array (28, Ny, Nx)  # нормировка OPAL/Noll
def fit_zernike(W, mask, terms=ZERNIKE_TERMS_28) -> coeffs, residual RMS
def zernike_reconstruct(coeffs, grid) -> W_fit
def strehl_from_zernike(coeffs) -> float  # 1 - (2π)²Σc²... сверка со strehl.py
```
Интеграция: psf_mtf.py — опция разложения + печать коэффициентов (как OPAVA).

## Тесты (tests/test_zernike.py)
1. Ортогональность базиса на единичном круге (в пределах числ. точности)
2. W=полином k-й степени → coeffs[k]≈1, остальные≈0
3. 28 членов на безаберрационной системе: все ≈0
4. Сферическая аберрация дублета: c[сфера] доминирует
5. strehl_from_zernike vs strehl.py — согласие (допуск 2%)
6. pytest -q зелёный (1009+)

## Правила
- psf_mtf/strehl импортировать; таблицы/оптимизацию не трогать
- Коммит: feat(analysis): Цернике 28 членов n≤12 + МНК (zernike.py)
