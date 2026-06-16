# Архитектура OPAL-OKB

## Модули

```
┌──────────────────────────────────────────────────────────────┐
│                        main.py (GUI)                         │
│  PyQt5 MainWindow: меню, таблица, параметры, статус         │
├──────────┬───────────┬──────────────┬────────────────────────┤
│          │           │              │                        │
│ visualization.py    │  analysis_gui.py                      │
│ (ход лучей,         │  (13 вкладок графиков)                │
│  зум, пан)          │              │                        │
├──────────┴───────────┴──────────────┴────────────────────────┤
│                                                              │
│ system_utils.py   optimizer.py    achromat.py    io_utils.py │
│ (reverse, scale,  (DLS,           (ахромат        (JSON)     │
│  ГОСТ радиусы)    Nelder-Mead)     дублет)                    │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│                     optics_engine.py                         │
│  OpticalSystem, Surface, Wavelength, FieldPoint             │
│  paraxial_trace(), seidel_aberrations()                      │
├──────────────────────┬───────────────────────────────────────┤
│  glass_catalog.py    │  glass_catalog_full.py                │
│  (14 ГОСТ)           │  (889 марок из .FIL)                  │
├──────────────────────┴───────────────────────────────────────┤
│                      ray_tracing.py                          │
│  Ray, TraceResult, trace_ray_through_system()                │
│  (Снеллиус, TIR, OPL, асферика)                              │
├──────────────────────────────────────────────────────────────┤
│  aberrations.py         │  diffraction_mtf.py                │
│  (spot, Δy', Δs', W,   │  (ЧКХ FFT,                        │
│   геом. MTF, поле)      │   волновой фронт)                  │
├─────────────────────────┴────────────────────────────────────┤
│  advanced_analysis.py  │  glass_diagram.py                    │
│  (PSF, LSF, ENC, PTF)  │  (диаграмма nd–νd)                 │
├─────────────────────────┴────────────────────────────────────┤
│  opj_reader.py     │  fil_reader_v2.py                       │
│  (парсинг .OPJ)    │  (парсинг .FIL каталогов)               │
└────────────────────┴─────────────────────────────────────────┘
```

---

## Поток данных

```
OpticalSystem (данные)
       │
       ▼
  Surface.surfaces[] ──── glass_name ──── glass_catalog.py / _full.py
       │                                     │
       │                               compute_refractive_index()
       │                                     │
       ▼                                     ▼
  paraxial_trace()                     n(λ) для каждой среды
       │
       ├──► f', BFD, FFD
       │
       ▼
  seidel_aberrations()
       │
       ├──► SI … SV
       │
       ▼
  ray_tracing.py: trace_ray_through_system()
       │
       │  Векторный Снеллиус + OPL
       │  Для асферик: Newton solver
       │
       ├──► Точка пересечения
       ├──► Направление после преломления
       └──► OPL (оптическая длина пути)
       
       ▼
  aberrations.py
       ├──► trace_aberration_fan()  ──► Δy', Δs', W(OPL)
       ├──► compute_spot_diagram()  ──► RMS
       ├──► compute_geometric_mtf() ──► геом. ЧКХ
       └──► compute_field_aberrations() ──► дисторсия, астигматизм
       
       ▼
  diffraction_mtf.py
       ├──► compute_wavefront_map()  ──► W(x,y)
       └──► compute_diffraction_mtf() ──► дифр. ЧКХ (FFT)
       
       ▼
  advanced_analysis.py
       ├──► compute_psf()  ──► PSF (2D интенсивность)
       ├──► compute_lsf()  ──► LSF (интеграл PSF)
       ├──► compute_enc()  ──► Encircled Energy
       └──► compute_ptf()  ──► Phase Transfer Function
       
       ▼
  Полихроматический режим:
       Для каждой λ: расчёт с весом → взвешенная сумма
```

---

## Классы модели данных

### OpticalSystem

```python
@dataclass
class OpticalSystem:
    name: str = ""
    object_type: ObjectType = INFINITE
    object_height: float = 0.0
    surfaces: List[Surface] = []
    aperture_type: ApertureType = ENTRANCE_PUPIL
    aperture_value: float = 0.0
    wavelengths: List[Wavelength] = []       # до 5
    field_points: List[FieldPoint] = []      # до 5
    stop_surface: int = 1                    # номер стоп-поверхности
    comment: str = ""
```

### Surface

```python
@dataclass
class Surface:
    radius: float = 0.0
    thickness: float = 0.0
    glass: str = ""
    semi_diameter: float = 0.0
    surface_type: SurfaceType = SPHERE
    conic_constant: float = 0.0             # k
    aspheric_coeffs: List[float] = []       # A4–A10
    is_reflective: bool = False
```

### FieldPoint

```python
@dataclass
class FieldPoint:
    y: float = 0.0              # координата поля
    weight: float = 1.0         # вес
    vuy: float = 1.0            # верхнее виньетирование
    vly: float = -1.0           # нижнее виньетирование
```

---

## Параксиальный расчёт (y-nu)

**Перенос:** `y[i+1] = y[i] + ν[i] · d[i] / n[i]`

**Преломление:** `ν'[i] = ν[i] − y[i] · (n' − n) / R`

**Результат:** f' = −1/ν_last, BFD = −y_last / ν_last · n_last

---

## Суммы Зейделя

```python
for каждой поверхности:
    A = n₁·u + y·Δn/R
    B = n̄·ū + ȳ·Δn/R
    SI  += h² · A² · (1/n₂ − 1/n₁)
    SII += h · A · B · (1/n₂ − 1/n₁)
    SIII += B² · (1/n₂ − 1/n₁)
    SIV += Δn / (R·n₁·n₂)
    SV  += h·B²·(1/n₂ − 1/n₁) / A
```

---

## Реальная трассировка

### Сфера

Стандартное пересечение луча со сферой: квадратное уравнение, выбор ближайшего корня.

### Асферические поверхности

Уравнение асферической поверхности:

```
z = c·r² / (1 + √(1 − (1+k)·c²·r²)) + A4·r⁴ + A6·r⁶ + A8·r⁸ + A10·r¹⁰
```

где `c = 1/R`, `r² = x² + y²`.

**Пересечение:** итеративный метод Ньютона. Начальное приближение — пересечение со сферой (k=0, A=0). Каждая итерация уточняет z и r по асферическому уравнению.

**Нормаль:** вычисляется аналитически из производной dz/dr.

### Преломление (векторный Снеллиус)

```
N = внешняя нормаль
cos_i = −(K·N)
sin²_t = (n₁/n₂)² · (1 − cos²_i)
Если sin²_t > 1 → TIR
K' = (n₁/n₂)·K + (n₁/n₂·cos_i − cos_t)·N
```

### OPL (оптическая длина пути)

Накапливается вдоль луча: `OPL += n · |Δs|` для каждого сегмента.

---

## Дифракционный анализ (advanced_analysis.py)

### PSF
`PSF = |FFT(W)|²` — квадрат модуля FFT от волнового фронта ( комплексная экспонента 2πiW/λ).

### LSF
Интеграл PSF по одному направлению (обычно X).

### ENC
Cumulative sum по радиальным кольцам PSF. ENC(r) = энергия внутри круга радиуса r.

### PTF
Фаза OTF: `PTF = arg(OTF)` где `OTF = FFT(PSF)`.

---

## Диаграмма стёкол (glass_diagram.py)

Отдельный виджет: график nd (ось X) vs νd (ось Y) для всех 889 марок. Стёкла текущей системы выделены. Используется для подбора замен.

---

## Подгонка характеристик

Три функции (binary search по радиусу):

- `fit_focal_length(system, surface_idx, target_f)` — подобрать R для заданного f'
- `fit_bfd(system, surface_idx, target_bfd)` — подобрать R для заданного BFD
- `fit_magnification(system, surface_idx, target_mag)` — подобрать R для заданного увеличения

Алгоритм: бисекция по R с пересчётом параксиальных характеристик на каждой итерации.

---

## Полихроматический расчёт

Для каждой длины волны из `system.wavelengths`:
1. Вычислить n(λ) для всех сред
2. Выполнить трассировку и анализ
3. Взвесить результат по `wl.weight`

Итоговое значение = Σ(result_i × weight_i) / Σ(weight_i).

Позволяет оценить хроматическую коррекцию и получить реальную картину для белого света.

---

## Каталоги стёкол

### glass_catalog.py — 14 ГОСТ (встроенный)

```python
GLASS_CATALOG = {
    "К8": (1.51630, 64.1, [C0..C5], λ_min, λ_max), ...
}
```

Формула Герцбергера: `n(λ) = C₀ + C₁λ² + C₂λ⁴ + C₃L + C₄L² + C₅L³`, L = 1/(λ² − 0.167²).

### glass_catalog_full.py — 889 марок

Загружается из .FIL файлов при первом обращении.

| Файл | Запись | Источник |
|------|--------|----------|
| GCTG.FIL | 96 б | ГОСТ |
| FCTG.FIL | 96 б | Schott |
| GCNG.FIL | 80 б | Новый формат |
| HCTG.FIL | 48 б | HOYA |

---

## Оптимизация

### DLS
Градиентный метод: ∂M/∂x через конечные разности, обновление с демпфированием.

### Nelder-Mead
Безградиентный. Надёжнее для многоэкстремальных задач.

### Целевая функция
RMS пятна рассеяния, взвешенное по полю и λ.

---

## Форматы файлов

### .OPJ (opj_reader.py)
Бинарный формат OPAL-PC. Заголовок → поверхности → стёкла (cp866) → λ и поля. 83 файла парсятся, 63 с именами стёкол.

### .FIL (fil_reader_v2.py)
Массивы записей фиксированной длины без заголовка. Валидация: C₀ ∈ (1.0, 3.0).

### .opal.json (io_utils.py)
Полный дамп OpticalSystem в JSON. Включает поверхности, λ, поля, стоп, комментарии.

---

## Зависимости

| Пакет | Назначение |
|-------|-----------|
| Python 3.10+ | Основной язык |
| PyQt5 ≥5.15 | GUI |
| numpy ≥1.20 | FFT, массивы |

Стандартная библиотека: math, struct, json, dataclasses, copy, bisect, os, sys.
