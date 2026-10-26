# Категория strehl

2 команды.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`strehl.calc`](#strehlcalc) | Число Штреля двумя способами: Марешаль + точный FFT-PSF (полихроматически при wl не задана) | `file`, `system`, `lbo_index`, `lbo_name`, `wl`, `field_y`, `include_text` | strehl_marechal/strehl_exact/sigma_w/validity + per_wl |
| [`strehl.marechal`](#strehlmarechal) | Аппроксимация Марешаля S = exp(−(2π·σ)²) из СКВ волновой аберрации | `sigma_w` | число Штреля (0, 1] |

## Параметры и результаты

### strehl.calc

Число Штреля двумя способами: Марешаль + точный FFT-PSF (полихроматически при wl не задана)

**Returns:** strehl_marechal/strehl_exact/sigma_w/validity + per_wl

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — все λ системы) |
| `field_y` | `float` | — | `0.0` | — | поле (град для INFINITE / мм для FINITE) |
| `include_text` | `bool` | — | `false` | — | добавить строку и tooltip GUI (strehl_tooltip) |

### strehl.marechal

Аппроксимация Марешаля S = exp(−(2π·σ)²) из СКВ волновой аберрации

**Returns:** число Штреля (0, 1]

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `sigma_w` | `float` | да | `null` | — | СКВ волновой аберрации, длины волн |

