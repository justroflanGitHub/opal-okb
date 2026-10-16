# TASK_OPTIM: реализация optimization.py + починка fit_dialog (волна 9-код)

## Цель — ЗАКРЫТЬ TODO Михаила «Fix fit/подгонка dialog»
Реализовать analysis/optimization.py по реверс-досье волны 9 и подключить
к GUI (gui/dialogs/fit_dialog.py — сейчас сломан/заглушка).

## Материалы (досье готовы!)
- analysis/REVERSE_LAP.md (30KB) — ОПТИМИЗАТОР: Goal/Variable/Penalty-модель,
  центральные разности якобиана, нормальные уравнения (JᵀJ+λ·diag)ΔP=−Jᵀоф
  (Levenberg-степень демпфирования), лимитеры + штрафы вместо clamp,
  istop-коды, solve-режим (Ньютон-подобный)
- analysis/REVERSE_OPTDOC.md (50KB) — §5 ТЗ на optimization.py (!) — модель
  мерит-функции из OPALOPT.DOC: цели (аберрации по зонам/полям/λ), типы
  параметров (радиусы/толщины/стекла/асферика), связи, границы, веса
- analysis/REVERSE_OS.md — словарь 71 марки, парсер PAR/EQF/MF+pmin/pmax —
  формат файлов задания оптимизации (SYN-подобный)
- Существующее: domain/calculations.py (paraxial, мерит-сырьё), analysis/
  aberrations.py (compute_field_aberrations и т.д.), gui/dialogs/fit_dialog.py

## Реализация
### A) analysis/optimization.py (НОВЫЙ)
```python
@dataclass
class OptVariable: параметр (тип: radius/thickness/glass_index/...), surface,
    pmin/pmax, шаг d для разностей, связь (link на другую var + коэф)
@dataclass
class OptGoal: тип аберрации/величина, зона/поле/λ, target, weight
@dataclass
class Penalty: границы как штрафы

def build_jacobian(system, vars, goals, central=True) -> J
def merit_vector(system, goals) -> residuals
def optimize(system, vars, goals, penalties, max_iter, damping) -> OptResult:
    # ЛАП-метод: (JᵀJ+λ·diag)ΔP = −Jᵀr; лимитеры+штрафы; istop-коды OPAL
def parse_opt_file(path) -> (vars, goals)  # формат PAR/EQF/MF из REVERSE_OS
```
### B) Починка gui/dialogs/fit_dialog.py
- выбрать переменные (чекбоксы поверхностей/параметров), цели, границы
- вызов optimize(), прогресс, результат → обновление системы + протокол
- стиль существующих диалогов порта

## Тесты (tests/test_optimization.py)
1. Дублет: варьируя R2 и толщину, свести продольную сферическую к минимуму →
   мерит падает монотонно; istop корректен
2. Граница: pmin/pmax соблюдаются (штрафы/лимитеры)
3. Связь: две переменные связаны коэф — двигаются синхронно
4. Якобиан центральных разностей против аналитической оценки (порядок)
5. parse_opt_file на синтетическом файле формата OPAL
6. fit_dialog: QDialog создаётся, вызов optimize через mock
7. pytest -q зелёный (993+)

## Правила
- tables.py/vignetting/psf_mtf НЕ трогать; импортировать существующее
- Коммит: feat(analysis+gui): оптимизация ЛАП-метод + fit_dialog (волна 9)
- CHANGELOG + README
