# 3D_VIZ_NOTES — инвентаризация (пакет A)

**Дата:** 2026-10-26
**Ветка:** `feature/3d-viz` (база `de883be`)
**ТЗ:** `docs/tasks/TASK_3D_VIZ.md`
**Статус:** только инвентаризация, код не менялся.

> Важно: часть тезисов ТЗ **устарела** — Strehl в панели результатов уже есть
> (коммит `4dbc71c`), встроенный 2D/3D-тоггл вьюера тоже (коммит `bbb1ddfa`,
> 2026-07-02). Точки интеграции ниже сняты с кода, не с ТЗ.

---

## 1. Статус тестов

```
QT_QPA_PLATFORM=offscreen py -m pytest tests/test_viz3d_mirrors.py tests/test_spot_3d.py tests/test_psf_3d.py tests/test_wavefront_3d.py
→ 51 passed (44.09s)
```

- PyOpenGL **локально установлен** → `HAS_PYOPENGL=True` (`tests/conftest.py:75`).
- CI обязан быть зелёным без PyOpenGL: маркер `requires_pyopengl`
  (`tests/conftest.py:111`) + GL-стаб `tests/_viz3d_glstub.py`
  (`render_framebuffer(gl_widget, W, H)`, context manager `gl_stubbed`).
  Прецедент: `tests/test_viz3d_mirrors.py`.

## 2. API `visualization3d.py` (корень репо)

- Модульный флаг `HAS_OPENGL` (try-import `OpenGL.GL`/`OpenGL.GLU`)
  (`visualization3d.py:35-37`).
- **Без PyOpenGL:** конструктор `Visualization3D` ставит fallback-QLabel
  «PyOpenGL not available.\nInstall: pip install PyOpenGL»
  (`visualization3d.py:70-74`), `gl_widget=None`.
- **`Visualization3D(QWidget)`** (`:44`):
  - `set_system(sys)` (`:131`) — сохраняет систему и автотрассирует
    `_trace_rays()`;
  - `_trace_rays()` (`:154`): поля `[0, max|fp.y|]`, длины волн — до первых 3
    из `sys.wavelengths`, трассировка
    `ray_native.trace_grid_3d_native(sys, num_rings=3, num_azimuths=8, wl, field_y)`
    (`:178-179`) → `ray_data_3d`: список `(wl, field_y, grid_results)`;
  - `get_scene_info()` (`:189`) → строка вида «Rays: ok/total passed».
- **Внутренний тулбар виджета** (англ.): Reset View / «Rays: ON|OFF»
  (checkable) / Wireframe / Trace 3D Rays.
- **`_GLWidget(QOpenGLWidget)`** (`:204`): камера `rot_x/rot_y/zoom/pan`
  мышью, `reset_view()` (`:228`); `paintGL` рисует ось, поверхности
  (стеклянные объёмы, зеркала золотом), кольцо апертурной диафрагмы, лучи.
- **Цвет луча** — `parent3d._wl_color(wl)` (`:537`) из захардкоженного dict
  `WL_COLORS` (`:51`) {0.65627: red, 0.58756: yellow, 0.54607: green,
  0.48613: blue, 0.43405: violet} + fallback к ближайшему ключу (`:59-65`).

## 3. Точки интеграции в `main.py`

### Встроенный 3D-вьюер — УЖЕ ЕСТЬ (ТЗ устарело)

- `main.py:28` — `from visualization3d import Visualization3D`;
- `main.py:961` — `self.viz_3d` встроен в `viz_stack` (index 1, `:1018`);
- `main.py:997-1001` — тумблер `btn_3d_toggle` «3D» (checkable);
- `main.py:1793-1807` — `_toggle_viz_3d`: при переключении подаёт
  `viz_3d.set_system(self.current_system)`.

⇒ Тезис ТЗ «вьюер не интегрирован» устарел: встроенный 2D/3D-тоггл есть
(коммит `bbb1ddfa`, 2026-07-02).

### Strehl в панели результатов — УЖЕ ЕСТЬ (ТЗ устарело)

- Коммит `4dbc71c`. `ResultsPanel` (`main.py:286`):
  - `self.strehl_label` (`main.py:385-387`, «Strehl: —» + tooltip
    `strehl_tooltip({})`);
  - `update_strehl()` (`main.py:478-490`): `format_strehl` +
    `strehl_tooltip`.
- Проводка: `_refresh_ui` (`main.py:1252-1264`) вызывает
  `bridge.execute("strehl.calc")` → `update_strehl`; также
  `gui/controllers/calculation_controller.py:519-520` вызывает
  `update_strehl` после расчёта.
- Импорт (`main.py:30`) — из шима `strehl.py` → `analysis/strehl.py`.
- **Движок `analysis/strehl.py` ПОЛЕН** (`compute_strehl` `:169`): моно +
  полихром со взвешенным средним по λ, `format_strehl`, `strehl_tooltip`,
  validity: `good` / `marechal_limit` / `invalid` / `no_data`
  (`:140-145`, `:248-252`). Дополнять не нужно.

### 2D-хроматический тумблер — УЖЕ ЕСТЬ

- `main.py:990-994` — `btn_zernike_chrom` «Хром.Ц» (checkable) →
  `_toggle_chromatic_rays` (`main.py:1784-1791`):
  `viz.chromatic_rays` + `_trace_all_rays`.
- `visualization.py` (2D): флаг `chromatic_rays` (`:63`), ветка отрисовки
  (`:107`, `:664`). 2D-файл **не в рабочей зоне задачи** — ничего дописывать,
  решение зафиксировано (см. gaps D).

### Меню/тулбар (здесь gap C)

- Меню «Вид» (`main.py:1156-1162`): только «Диаграмма стёкол».
- Тулбар (`main.py:1180-1188`): 📄 Новый / 🔧 Демо / ▶ Рассчитать.
- Кнопки/окна «3D-ход лучей» **нет** (это и есть gap C).

## 4. Палитры цветов и единый источник

Сейчас три несогласованных источника:

| Где | Что |
|---|---|
| `visualization.py::_wl_color` (`:52`) | 2D, диапазоны λ |
| `visualization3d.py::WL_COLORS` (`:51`) | 3D, захардкоженный dict + fallback к ближайшему |
| `gui/widgets/base.py::wl_to_plot_color` (`:133`) | **санкционированный единый источник**: якоря `_wl_plot_anchors` (`:122`) из `utils/spectral_lines.py`, RGB для h/g/F/e/d/C/r |

`utils/spectral_lines.py` — справочник линий (i/h/g/G'/F'/F/e/d/C/C'/A'…,
элементы Hg/H/Cd/Na/…, `SPECTRAL_LINES:49`), декларирует себя якорем палитры
(`:9`). Gap D: перевести 3D-палитру на единый источник.

## 5. Gaps по пакетам B/C/D/E (решения)

### B — Strehl в GUI: остались только тесты

Движок и проводка готовы. **Нет GUI-тестов** — файлы `tests/test_gui_*`
отсутствуют (движок покрыт `tests/test_strehl.py`). Нужны offscreen-тесты:
- на демо-ахромате (`domain.models.create_demo_system_by_name('achromat')`,
  `domain/models.py:182`): `0 < S ≤ 1`;
- Марешаль ≈ точный в допуске;
- полихром ≥ моно-минимума;
- проводка `ResultsPanel.update_strehl` + текст/tooltip.
Возможны мелкие полировки строки, но ядро — тесты.

### C — отдельное окно «3D-ход лучей»

Встроенный тоггл есть, **отдельного окна нет**:
- пункт меню «Вид» → «3D-ход лучей» + кнопка тулбара;
- подача текущей системы (данные — только вызовами, `commands/` не трогать);
- `HAS_OPENGL=False` → действие/кнопка disabled + tooltip
  «pip install PyOpenGL»;
- тесты offscreen через GL-стаб (прецедент `test_viz3d_mirrors`):
  окно открывается/закрывается, сцена не пуста.

### D — тумблер «Лучи по λ» в 3D

- В 3D **нет** тумблера: моно (основная λ) ↔ полихром (все λ с весами);
- `_wl_color`/`WL_COLORS` заменить на палитру от единого источника
  (`wl_to_plot_color` / якоря `utils/spectral_lines.py`);
- тесты: число цветов = числу λ, toggle переключает набор отрисованных лучей;
- 2D-тумблер «Хром.Ц» уже есть — дописывать нечего, зафиксировать решение;
- мелочь: тулбар `Visualization3D` на английском («Rays: ON», «Reset View»)
  — можно русифицировать в рамках D.

### E — финал

Полный `py -m pytest -q` зелёный; CHANGELOG `[1.32.0]`; строка в README;
отчёт `docs/tasks/3D_VIZ_REPORT.md` (что вошло, что отложено и почему).

## 6. Окружение

- Запуск: `py` (не `python`); GUI-тесты — `QT_QPA_PLATFORM=offscreen`
  (прецедент в существующих 3D-тестах).
- PyOpenGL может отсутствовать — все GL-тесты через stub/маркер
  (`tests/_viz3d_glstub.py`, `requires_pyopengl` в `tests/conftest.py:111`);
  CI без PyOpenGL обязан быть зелёным.
- Демо-системы: `domain.models.create_demo_system_by_name('achromat')` и
  `('mirror')` (`domain/models.py:182`); прецедент фикстуры —
  `tests/test_spot_3d.py::build_doublet` (`:17`).
- PyQt5/pytestqt/mplotlib установлены.
- Запреты пакета A соблюдены: код не менялся, создан только этот файл;
  `scripts/`, `commands/`, `tests/test_corpus*`, `docs/reports/`,
  `docs/tasks/CORPUS*`, `analysis/`, `visualization.py` не тронуты.
