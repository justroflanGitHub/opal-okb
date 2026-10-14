# TASK_3D: Strehl ratio + spot diagram 3D

## Цель
Дополнить 3D-блок (visualization3d.py уже есть: лучи, поверхности, wireframe):
1. **Strehl ratio** — расчёт + отображение в GUI
2. **Spot diagram 3D** — переключаемый 2D/3D вид пятна рассеяния

## Часть 1: Strehl ratio

### Расчёт (analysis/diffraction.py или отдельный модуль analysis/strehl.py)
```python
def compute_strehl(system, wl=None, field_y=0.0) -> dict:
    """Strehl ratio двумя способами.

    Returns:
      strehl_marechal: exp(-(2*pi*sigma_w)^2)  — аппроксимация Марешаля
      strehl_exact:    I_peak(аберр.) / I_peak(идеал) — через FFT PSF
      sigma_w:         RMS волновой аберрации (длины волн)
      validity:        'good' (S>0.1) | 'marechal_limit' (0.05<S<0.1) | 'invalid' (S<0.05,
                       Марешаль неприменим)
    """
```
- σ_w брать из wavefront RMS: `compute_wavefront_rms_vs_field` / `trace_wavefront_hexapolar`
  (analysis/aberrations.py, hexapolar сетка) на field_y
- точный Strehl: через PSF из analysis/diffraction.py (FFT) — если там есть FFT PSF
  (проверить; _fft2d есть в aberrations.py) — пик с аберрациями / пик дифракционно-
  ограниченного пятна той же апертуры
- polychromatic: strehl на каждой длине волны + взвешенное среднее

### GUI
- В панель результатов (ResultsPanel, main.py ~стр. 290) или рядом со spot diagram:
  строка «Strehl: 0.847 (σ=0.052λ, Марешаль)» + tooltip с расшифровкой
- Обновлять при _refresh_ui вместе с остальными результатами

## Часть 2: Spot diagram 3D

- gui/widgets/spot_diagram.py: SpotDiagramWidget — сейчас чистый QPainter 2D (paintEvent)
- Добавить кнопку-переключатель «2D/3D» (по образцу btn_wf_3d в main.py:957 —
  wavefront toggle) или в сам виджет
- 3D-режим: matplotlib 3D scatter (проекция '3d', MplCanvasWidget уже используется
  в FocusDiagramWidget — см. gui/widgets/spot_diagram.py:288) точек пятна:
  X, Y — координаты пятна, цвет — по плотности/длине волны (polychromatic)
- Переключение мгновенное, состояние сохраняется в виджете
- Данные: compute_spot_diagram / compute_spot_diagram_polychromatic (analysis/aberrations.py)

## Тесты (tests/test_strehl.py + доп. в test_spot если есть)
1. Marechal: аберрации→0 ⇒ S→1 (монотонность по σ)
2. Точный vs Марешаль: расхождение <10% при S>0.3
3. Идеальная система (плоская волна): S=1.0±eps
4. Спот 3D: сет данных не пуста, виджет создаётся (smoke, offscreen: QApplication
   с QT_QPA_PLATFORM=offscreen — проверить как сделано в существующих GUI-тестах)

## Правила
- Существующее поведение 2D не ломать; pytest -q tests/ зелёный
- type hints, docstrings
- CHANGELOG + README (раздел анализа)
- Коммит: `feat(analysis): Strehl ratio (Марешаль+FFT) + spot diagram 3D toggle`
