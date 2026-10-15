# TASK_PSF: B2 — реализация ФРТ/ФРЛ/MTF/ФКЭ (analysis/psf_mtf.py)

## Цель
Уровень-2 анализ из ANALIZE.DOC — в порте ОТСУТСТВУЕТ. Реализовать по
стандартной физике (сверка с OPAL-алгоритмами отложена на реверс-волну 10 —
сейчас каркас + тесты физкорректности):

- **ФРТ** (PSF): |FFT(W-зрачок)|², амплитуда=чистая апертура (экранирование
  зеркал учитывать), длина волны основной, дефокус-параметр
- **ФРЛ** (LSF): интеграл ФРТ по одной оси
- **MTF** (ОПФ): |FFT(ФРТ)| нормированная; tan/sag-сечения (поле!)
- **ФКЭ**: энергия в кружке (encircled energy) по ФРТ
- **Штрель**: уже есть (strehl.py) — ИСПОЛЬЗОВАТЬ, не дублировать

## Материалы
- Существующее: analysis/strehl.py, analysis/aberrations.py
  (trace_wavefront_hexapolar — поле W по зрачку!), domain.models (OpticalSystem,
  obscuration_ratio), analysis/ray_tracing.py (trace_ray_through_system)
- ANALIZE.DOC: «ФРТ и ФРЛ, ОПФ, ФКЭ, точечные и фокусировочные диаграммы,
  изображения шпальных мир» — определения/единицы читать!
- numpy есть в зависимостях (FFT через numpy.fft)

## Реализация — analysis/psf_mtf.py (НОВЫЙ)
```python
GRID = 128  # или иное — задокументировать выбор

def psf_grid(system, field_y=0.0, wl=None, defocus=0.0, grid=GRID) -> dict:
    """ФРТ на сетке: pupil(W+defocus) → |FFT|² → psf[i,j], координаты мкм."""
def lsf_from_psf(psf) -> ...        # интеграл по оси
def mtf_from_psf(psf, pitch_um) -> ...  # норм. |FFT(псф)|; tan/sag кривые
def encircled_energy(psf, pitch_um) -> ...  # радиальная кумулятивная
def strel_from_psf(psf) -> float    # сверка со strehl.py (допуск 1e-3)
def render_test_target(...)-> ...   # шпальная мира (синус-миры): свёртка ФРТ
```
Интеграция: gui-диалог НЕ трогать (волна GUI позже); экспорт в protocol.py
добавить секцию «ФРТ/ОПФ» (краткую).

## Тесты (tests/test_psf_mtf.py)
1. Безаберрационная линза (W=0): Штрель из psf == strehl.py (≈1)
2. Дефокус 0.25λ: MTF ноль на 0.5/Nyq? (физика: дефокус-нуль MTF ~ известные
   нули Талбота — проверить порядок)
3. Экранирование 0.3: ФРТ «провал» центра → энергия в кольцах ↑, ФКЭ(0) ниже
4. MTF(0)=1.0 монотонность убывания; tan/sag различаются на поле≠0
5. Энергия сохраняется: Σpsf нормирована
6. pytest -q зелёный (953+)

## Правила
- strehl.py импортировать; aberrations.py не переписывать
- Коммит: feat(analysis): ФРТ/ФРЛ/MTF/ФКЭ — уровень-2 анализа (psf_mtf.py)
- CHANGELOG + README
