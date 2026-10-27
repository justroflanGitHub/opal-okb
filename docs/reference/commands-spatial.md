# Категория spatial

8 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`spatial.coord_breaks`](#spatialcoord_breaks) | Изломы СК по поверхностям: где есть наклон/децентрировка | `file`, `system`, `lbo_index`, `lbo_name` | {surfaces: [{index, has_break, tilts, decenters}]} |
| [`spatial.mat_tvec`](#spatialmat_tvec) | Умножить транспонированную матрицу 3×3 на вектор (Mᵀ·v) | `matrix`, `v` | {result: [x, y, z]} |
| [`spatial.mat_vec`](#spatialmat_vec) | Умножить матрицу 3×3 на вектор (M·v) | `matrix`, `v` | {result: [x, y, z]} |
| [`spatial.ray_rotate`](#spatialray_rotate) | Повернуть направление луча (k,l,m) наклонами поверхности (нормирует вектор) | `tilt_x`, `tilt_y`, `tilt_z`, `k`, `l`, `m`, `transpose` | {k, l, m} |
| [`spatial.rotate_vector`](#spatialrotate_vector) | Повернуть вектор матрицей наклонов (R или Rᵀ) | `tilt_x`, `tilt_y`, `tilt_z`, `v`, `transpose` | {v, result} |
| [`spatial.rotation_matrix`](#spatialrotation_matrix) | Матрица поворота R = Rz·Ry·Rx (наклоны поверхностей, порядок X→Y→Z) | `tilt_x`, `tilt_y`, `tilt_z` | {matrix: [9 чисел строкой за строкой], identity} |
| [`spatial.surface_frames`](#spatialsurface_frames) | Системы координат поверхностей: вершина + матрица поворота (CoordBreak) | `file`, `system`, `lbo_index`, `lbo_name` | {frames: [{index, vertex, matrix, identity}]} |
| [`spatial.vertices`](#spatialvertices) | Вершины поверхностей в глобальной СК (z по толщинам + децентрировки) | `file`, `system`, `lbo_index`, `lbo_name` | {vertices: [{index, x, y, z, semi_diameter}]} |

## Параметры и результаты

### spatial.coord_breaks

Изломы СК по поверхностям: где есть наклон/децентрировка

**Returns:** {surfaces: [{index, has_break, tilts, decenters}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### spatial.mat_tvec

Умножить транспонированную матрицу 3×3 на вектор (Mᵀ·v)

**Returns:** {result: [x, y, z]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `matrix` | `list` | да | `null` | — | матрица 3×3 строкой за строкой (9 чисел) |
| `v` | `list` | да | `null` | — | вектор [x, y, z] |

### spatial.mat_vec

Умножить матрицу 3×3 на вектор (M·v)

**Returns:** {result: [x, y, z]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `matrix` | `list` | да | `null` | — | матрица 3×3 строкой за строкой (9 чисел) |
| `v` | `list` | да | `null` | — | вектор [x, y, z] |

### spatial.ray_rotate

Повернуть направление луча (k,l,m) наклонами поверхности (нормирует вектор)

**Returns:** {k, l, m}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `tilt_x` | `float` | — | `0.0` | — | наклон X, град |
| `tilt_y` | `float` | — | `0.0` | — | наклон Y, град |
| `tilt_z` | `float` | — | `0.0` | — | наклон Z, град |
| `k` | `float` | да | `null` | — | компонента X направления |
| `l` | `float` | да | `null` | — | компонента Y направления |
| `m` | `float` | да | `null` | — | компонента Z направления |
| `transpose` | `bool` | — | `false` | — | применить Rᵀ (в локальную СК) |

### spatial.rotate_vector

Повернуть вектор матрицей наклонов (R или Rᵀ)

**Returns:** {v, result}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `tilt_x` | `float` | — | `0.0` | — | наклон X, град |
| `tilt_y` | `float` | — | `0.0` | — | наклон Y, град |
| `tilt_z` | `float` | — | `0.0` | — | наклон Z, град |
| `v` | `list` | да | `null` | — | вектор [x, y, z] |
| `transpose` | `bool` | — | `false` | — | применить Rᵀ (глобальная → локальная СК) |

### spatial.rotation_matrix

Матрица поворота R = Rz·Ry·Rx (наклоны поверхностей, порядок X→Y→Z)

**Returns:** {matrix: [9 чисел строкой за строкой], identity}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `tilt_x` | `float` | — | `0.0` | — | наклон вокруг X, град |
| `tilt_y` | `float` | — | `0.0` | — | наклон вокруг Y, град |
| `tilt_z` | `float` | — | `0.0` | — | наклон вокруг Z, град |

### spatial.surface_frames

Системы координат поверхностей: вершина + матрица поворота (CoordBreak)

**Returns:** {frames: [{index, vertex, matrix, identity}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

### spatial.vertices

Вершины поверхностей в глобальной СК (z по толщинам + децентрировки)

**Returns:** {vertices: [{index, x, y, z, semi_diameter}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |

