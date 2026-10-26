# Категория adv

29 команд.

| Команда | Описание | Параметры | Returns |
| --- | --- | --- | --- |
| [`adv.airy.encircled`](#advairyencircled) | Эталон Эйри: аналитическая ФКЭ идеального пятна 1 − J0²(x) − J1²(x) (ряды Бесселя), радиусы тёмных колец и сравнение фактической ФРТ (r₅₀/r₈₀) с диском Эйри | `file`, `system`, `lbo_index`, `lbo_name`, `r_fractions`, `field_y`, `wl` | {f_number, wl, airy_radius_um, dark_rings_um, rows: [{r_um, r_over_r1, ee}], psf_r50_um, psf_r80_um, r50_over_r1, r80_over_r1} |
| [`adv.bar_image`](#advbar_image) | Симуляция изображения штриховой миры: свёртка идеального профиля с ФРЛ | `file`, `system`, `lbo_index`, `lbo_name`, `bar_freq_lp_mm`, `num_bars`, `field_y`, `wl` | ось (мкм) + идеальный и размытый профили |
| [`adv.bar_mtf`](#advbar_mtf) | Таблица MTF по штриховой мире: контраст размытого изображения на заданных частотах | `file`, `system`, `lbo_index`, `lbo_name`, `freq_list`, `num_bars`, `field_y`, `wl` | строки {freq, contrast_ideal, contrast_real, mtf} |
| [`adv.convolve.profile`](#advconvolveprofile) | Отклик системы на произвольный одномерный профиль объекта: линейная свёртка с ФРЛ выбранного сечения (моделирование отклика на произвольный объект) | `file`, `system`, `lbo_index`, `lbo_name`, `profile`, `pitch_um`, `section`, `field_y`, `wl` | {coord_um, object, image, contrast} |
| [`adv.dof.compare`](#advdofcompare) | Глубина фокуса по полям: дифракционная ±2λF#² vs геометрическая (RMS пятна / NA′ — дефокус, при котором размытие от дефокуса равно аберрационному), доминирующий режим | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl`, `num_rays` | {rows: [{field, rms_spot_mm, na_image, dof_geo_half_mm, dof_diff_half_mm, ratio, regime}]} |
| [`adv.dof.diffraction`](#advdofdiffraction) | Дифракционная глубина фокуса (критерий Рэлея λ/4 OPD): ±2·λ·F#² по каждой λ системы + диск Эйри | `file`, `system`, `lbo_index`, `lbo_name`, `wl_list` | {f_number, rows: [{wl, dof_half_mm, dof_full_mm, airy_radius_um}]} |
| [`adv.enc`](#advenc) | ФКЭ (Encircled Energy): доля энергии пятна внутри радиуса r (геометрически, по точечной диаграмме) | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `field_y`, `wl` | радиусы (мкм) + доли энергии [0..1] |
| [`adv.energy.ring`](#advenergyring) | Энергия в кольце фотоприёмника: ФКЭ(r₂) − ФКЭ(r₁) от энергетического центра ФРТ (доля полной энергии) | `file`, `system`, `lbo_index`, `lbo_name`, `r_inner_um`, `r_outer_um`, `field_y`, `wl`, `defocus` | {r_inner_um, r_outer_um, ee_inner, ee_outer, fraction} |
| [`adv.esf`](#advesf) | ФКР (ESF): отклик на резкий край — интеграл ФРЛ (тангенциальной) | `file`, `system`, `lbo_index`, `lbo_name`, `num_points`, `field_y`, `wl` | ось (мкм) + ESF от 0 до 1 |
| [`adv.lsf`](#advlsf) | ФРЛ (LSF): интеграл ФРТ по одному направлению — отклик на щель | `file`, `system`, `lbo_index`, `lbo_name`, `direction`, `num_rays`, `field_y`, `wl` | профиль lsf (нормирован на 1) + ось (мкм) |
| [`adv.lsf.poly`](#advlsfpoly) | Полихроматическая ФРЛ: взвешенная сумма профилей ФРЛ по λ на общей оси (меридиональное и сагиттальное сечения) | `file`, `system`, `lbo_index`, `lbo_name`, `wl_list`, `weights`, `field_y` | {coord_um, meridional, sagittal, spectral} |
| [`adv.noise.spot`](#advnoisespot) | Наложение шума детектора на пятно: пиксельная матрица ФРТ × электроны + пуассоновский дробовой шум + гауссов шум чтения; генератор random.Random(seed) — результат воспроизводим | `file`, `system`, `lbo_index`, `lbo_name`, `pixel_um`, `size`, `peak_e`, `read_noise_e`, `dark_e`, `seed`, `field_y`, `wl` | {seed, matrix: [[e-]], peak_e, background_std_e, snr, meta} |
| [`adv.object_image`](#advobject_image) | Симуляция изображения тест-объекта (мира/край/точка/синус) — свёртка с дифракционной ФРТ | `file`, `system`, `lbo_index`, `lbo_name`, `kind`, `num_rays`, `field_y`, `defocus_mm`, `freq_lp_mm`, `num_bars`, `wl`, `include_grid` | метаданные + производные (+x/y/ideal/image/psf при include_grid) |
| [`adv.otf.complex`](#advotfcomplex) | Комплексная ОТФ из FFT ФРТ (psf_grid-маршрут, с полем и экранированием): сечения Re/Im/фаза тангенциальное и сагиттальное (фазовая ЧКХ) | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl`, `defocus` | {freq_lpmm, re_tan, im_tan, phase_tan, re_sag, im_sag, phase_sag, mtf_tan, mtf_sag, cutoff_lpmm} |
| [`adv.pixel.energy`](#advpixelenergy) | Энергия фотоприёмника в пикселе: доля ФРТ в пикселе с заданным смещением от центра пятна и в блоке N×N вокруг него (сумма блока ≤ 1) | `file`, `system`, `lbo_index`, `lbo_name`, `pixel_um`, `offset_x_um`, `offset_y_um`, `block`, `field_y`, `wl` | {pixel_um, offset_x_um, offset_y_um, block, pixel_fraction, block_fraction} |
| [`adv.pixel.matrix`](#advpixelmatrix) | Пиксельная матрица пятна: интегрирование ФРТ по пикселям заданного шага с подпиксельной передискретизацией — доли энергии в пикселях окна | `file`, `system`, `lbo_index`, `lbo_name`, `pixel_um`, `size`, `subsample`, `field_y`, `wl`, `defocus` | {pixel_um, size, subsample, matrix [[fraction]], central_fraction, max_fraction, sum_in_window, psf_pitch_um} |
| [`adv.psf`](#advpsf) | Дифракционная ФРТ через FFT зрачковой функции (с параксиальным дефокусом) | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `field_y`, `defocus_mm`, `wl`, `include_grid` | масштаб изображения (+решётки psf/x/y при include_grid) |
| [`adv.psf.centroid`](#advpsfcentroid) | Энергетический центр (центроид) ФРТ по полям: смещение от опорной оси поля (искажение-like метрика дифракционного пятна) | `file`, `system`, `lbo_index`, `lbo_name`, `fields`, `wl` | {rows: [{field, centroid_x_um, centroid_y_um, shift_um}]} |
| [`adv.psf.focus_stack`](#advpsffocus_stack) | Объёмная ФРТ через фокус: сетка дефокуса ±range, в каждой плоскости — пик, Штрель, FWHM сечений x/y и r₈₀ (опция — центральные срезы профилей) | `file`, `system`, `lbo_index`, `lbo_name`, `defocus_range_mm`, `num_points`, `field_y`, `wl`, `include_slices` | {rows: [{defocus_mm, defocus_waves, peak, strehl, fwhm_x_um, fwhm_y_um, r80_um}], meta} |
| [`adv.psf.fwhm`](#advpsffwhm) | FWHM центральных сечений ФРТ (по x — сагиттальное, по y — меридиональное) с сравнением с диском Эйри | `file`, `system`, `lbo_index`, `lbo_name`, `field_y`, `wl`, `defocus` | {fwhm_x_um, fwhm_y_um, airy_diameter_um, ratio_x, ratio_y} |
| [`adv.psf.poly`](#advpsfpoly) | Полихроматическая ФРТ: некогерентная взвешенная сумма монохромных ФРТ по λ системы (или явному спектру) на общей координатной сетке | `file`, `system`, `lbo_index`, `lbo_name`, `wl_list`, `weights`, `field_y`, `include_grid` | {spectral: [{wl, weight, pitch_um}], peak, fwhm_x_um, fwhm_y_um, r50_um, r80_um (+psf при include_grid)} |
| [`adv.psf.waist`](#advpsfwaist) | Перетяжка ФРТ вдоль оси: положение плоскости максимального пика (параболическое уточнение), осевой FWHM кривой пика и асимметрия полуширин | `file`, `system`, `lbo_index`, `lbo_name`, `defocus_range_mm`, `num_points`, `field_y`, `wl` | {z_waist_mm, defocus_waves_at_waist, peak_max, peak_refined, axial_fwhm_mm, half_left_mm, half_right_mm, strehl_at_waist} |
| [`adv.ptf`](#advptf) | ФКП (PTF): фазовая ЧКХ = arg(OTF), тангенциальная и сагиттальная | `file`, `system`, `lbo_index`, `lbo_name`, `num_rays`, `field_y`, `wl` | {freqs, ptf_tangential, ptf_sagittal, cutoff_freq} |
| [`adv.resolve.thornber`](#advresolvethornber) | Критерий Торнбера — разрешение по сечениям ЧКХ: частота, где ХУДШЕЕ из тангенциального/сагиттального сечений пересекает порог; дополнительно частота пересечения ветвей (астигматический баланс) | `file`, `system`, `lbo_index`, `lbo_name`, `threshold`, `fields`, `wl` | {threshold, rows: [{field, freq_tan_lpmm, freq_sag_lpmm, freq_resolved_lpmm, limiting, crossover_lpmm, astig_gap}]} |
| [`adv.slit_image`](#advslit_image) | Изображение щели конечной ширины: 2D-свёртка идеальной щели с дифракционной ФРТ (линия/край/точка — adv.object_image; здесь — конечная щель) | `file`, `system`, `lbo_index`, `lbo_name`, `width_um`, `along`, `field_y`, `wl`, `defocus`, `include_grid` | {width_um, along, contrast, edge_10_90_um, min/max профиля (+x/y/ideal/image при include_grid)} |
| [`adv.snr.bars`](#advsnrbars) | SNR измерения контраста штрихов через ЧКХ: SNR = 2C·N̄/√(2(N̄+σ_r²)), C = MTF(ν) сечения (танг./саг.), N̄ — средний сигнал на пиксель | `file`, `system`, `lbo_index`, `lbo_name`, `freq_lpmm`, `signal_e`, `read_noise_e`, `snr_min`, `field_y`, `wl` | {freq_lpmm, mtf_tan, mtf_sag, contrast, snr_tan, snr_sag, snr_min, verdict_tan, verdict_sag} |
| [`adv.usaf.object`](#advusafobject) | Ширина штриха элемента миры СШАФ-1951 на плоскости предмета: частота/ширина в изображении → через увеличение (для INFINITE — угловой масштаб ν·f′) | `file`, `system`, `lbo_index`, `lbo_name`, `group`, `element` | {group, element, freq_image_lpmm, bar_width_image_um, magnification, freq_object_lpmm, bar_width_object_um, angular_lp_per_mrad} |
| [`adv.usaf.resolve`](#advusafresolve) | Разрешимый элемент миры СШАФ-1951 по сечениям ЧКХ: наиболее мелкий элемент с ЧКХ (танг. и саг.) не ниже порога, с учётом предела Найквиста | `file`, `system`, `lbo_index`, `lbo_name`, `threshold`, `group_from`, `group_to`, `field_y`, `wl` | {group, element, freq_lpmm, bar_width_um, mtf_tan, mtf_sag, limiting, nyquist_lpmm, cutoff_lpmm, limited_by} |
| [`adv.usaf.table`](#advusaftable) | Таблица миры СШАФ-1951: частота элемента ν = 2^(G+(E−1)/6) лин/мм, период и ширина штриха (справочник, без системы) | `group_from`, `group_to`, `freq_max_lpmm` | {rows: [{group, element, freq_lpmm, period_um, bar_width_um}], base_freq_lpmm} |

## Параметры и результаты

### adv.airy.encircled

Эталон Эйри: аналитическая ФКЭ идеального пятна 1 − J0²(x) − J1²(x) (ряды Бесселя), радиусы тёмных колец и сравнение фактической ФРТ (r₅₀/r₈₀) с диском Эйри

**Returns:** {f_number, wl, airy_radius_um, dark_rings_um, rows: [{r_um, r_over_r1, ee}], psf_r50_um, psf_r80_um, r50_over_r1, r80_over_r1}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `r_fractions` | `list` | — | `null` | — | радиусы в долях r₁ (по умолчанию [0.25, 0.5, 1.0, 1.5, 2.0]) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.bar_image

Симуляция изображения штриховой миры: свёртка идеального профиля с ФРЛ

**Returns:** ось (мкм) + идеальный и размытый профили

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `bar_freq_lp_mm` | `float` | — | `10.0` | — | частота миры (лин/мм) |
| `num_bars` | `int` | — | `5` | — | число штрихов (параметр сигнатуры) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.bar_mtf

Таблица MTF по штриховой мире: контраст размытого изображения на заданных частотах

**Returns:** строки {freq, contrast_ideal, contrast_real, mtf}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `freq_list` | `list` | — | `null` | — | частоты (лин/мм); по умолчанию — [5, 10, 20, 30, 50, 80, 100] |
| `num_bars` | `int` | — | `5` | — | число штрихов (параметр сигнатуры) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.convolve.profile

Отклик системы на произвольный одномерный профиль объекта: линейная свёртка с ФРЛ выбранного сечения (моделирование отклика на произвольный объект)

**Returns:** {coord_um, object, image, contrast}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `profile` | `list` | да | `null` | — | профиль объекта [I0, I1, ...], ≥2 значений |
| `pitch_um` | `float` | да | `null` | — | шаг профиля, мкм (> 0) |
| `section` | `str` | — | `"tangential"` | `["tangential", "sagittal"]` | сечения ФРЛ: tangential — LSF(x), sagittal — LSF(y) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.dof.compare

Глубина фокуса по полям: дифракционная ±2λF#² vs геометрическая (RMS пятна / NA′ — дефокус, при котором размытие от дефокуса равно аберрационному), доминирующий режим

**Returns:** {rows: [{field, rms_spot_mm, na_image, dof_geo_half_mm, dof_diff_half_mm, ratio, regime}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | поля (град); по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `num_rays` | `int` | — | `30` | — | лучей сетки зрачка точечной диаграммы |

### adv.dof.diffraction

Дифракционная глубина фокуса (критерий Рэлея λ/4 OPD): ±2·λ·F#² по каждой λ системы + диск Эйри

**Returns:** {f_number, rows: [{wl, dof_half_mm, dof_full_mm, airy_radius_um}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl_list` | `list` | — | `null` | — | явный список λ, мкм (по умолчанию — λ системы) |

### adv.enc

ФКЭ (Encircled Energy): доля энергии пятна внутри радиуса r (геометрически, по точечной диаграмме)

**Returns:** радиусы (мкм) + доли энергии [0..1]

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `200` | — | лучей точечной диаграммы |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.energy.ring

Энергия в кольце фотоприёмника: ФКЭ(r₂) − ФКЭ(r₁) от энергетического центра ФРТ (доля полной энергии)

**Returns:** {r_inner_um, r_outer_um, ee_inner, ee_outer, fraction}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `r_inner_um` | `float` | да | `null` | — | внутренний радиус кольца, мкм (≥ 0) |
| `r_outer_um` | `float` | да | `null` | — | внешний радиус кольца, мкм (> внутреннего) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `defocus` | `float` | — | `0.0` | — | дефокусировка в длинах волн на краю зрачка |

### adv.esf

ФКР (ESF): отклик на резкий край — интеграл ФРЛ (тангенциальной)

**Returns:** ось (мкм) + ESF от 0 до 1

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_points` | `int` | — | `100` | — | параметр сигнатуры (сетка задаётся ФРЛ) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.lsf

ФРЛ (LSF): интеграл ФРТ по одному направлению — отклик на щель

**Returns:** профиль lsf (нормирован на 1) + ось (мкм)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `direction` | `str` | — | `"tangential"` | `["tangential", "sagittal"]` | tangential — LSF(x) (вертикальная щель), sagittal — LSF(y) |
| `num_rays` | `int` | — | `128` | — | размер сетки зрачка |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.lsf.poly

Полихроматическая ФРЛ: взвешенная сумма профилей ФРЛ по λ на общей оси (меридиональное и сагиттальное сечения)

**Returns:** {coord_um, meridional, sagittal, spectral}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl_list` | `list` | — | `null` | — | явный спектр λ, мкм (по умолчанию — λ системы) |
| `weights` | `list` | — | `null` | — | веса λ (по умолчанию — веса λ системы или 1) |
| `field_y` | `float` | — | `0.0` | — | поле |

### adv.noise.spot

Наложение шума детектора на пятно: пиксельная матрица ФРТ × электроны + пуассоновский дробовой шум + гауссов шум чтения; генератор random.Random(seed) — результат воспроизводим

**Returns:** {seed, matrix: [[e-]], peak_e, background_std_e, snr, meta}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `pixel_um` | `float` | да | `null` | — | шаг пиксельной решётки, мкм (> 0) |
| `size` | `int` | — | `7` | — | окно матрицы (нечётное число пикселей) |
| `peak_e` | `float` | — | `10000.0` | — | электроны в центральном пикселе пятна (> 0) |
| `read_noise_e` | `float` | — | `5.0` | — | шум чтения, электроны RMS (≥ 0) |
| `dark_e` | `float` | — | `0.0` | — | темновой сигнал на пиксель, электроны (≥ 0) |
| `seed` | `int` | — | `0` | — | seed генератора (детерминизм) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.object_image

Симуляция изображения тест-объекта (мира/край/точка/синус) — свёртка с дифракционной ФРТ

**Returns:** метаданные + производные (+x/y/ideal/image/psf при include_grid)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `kind` | `str` | — | `"mira"` | `["mira", "edge", "point", "sine"]` | вид тест-объекта |
| `num_rays` | `int` | — | `128` | — | размер сетки ФРТ |
| `field_y` | `float` | — | `0.0` | — | поле |
| `defocus_mm` | `float` | — | `0.0` | — | смещение плоскости установки (мм) |
| `freq_lp_mm` | `float` | — | `10.0` | — | частота первой группы миры / синусоиды (лин/мм) |
| `num_bars` | `int` | — | `6` | — | число групп штрихов миры |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `include_grid` | `bool` | — | `false` | — | включить решётки x/y/ideal/image/psf |

### adv.otf.complex

Комплексная ОТФ из FFT ФРТ (psf_grid-маршрут, с полем и экранированием): сечения Re/Im/фаза тангенциальное и сагиттальное (фазовая ЧКХ)

**Returns:** {freq_lpmm, re_tan, im_tan, phase_tan, re_sag, im_sag, phase_sag, mtf_tan, mtf_sag, cutoff_lpmm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `defocus` | `float` | — | `0.0` | — | дефокусировка в длинах волн на краю зрачка |

### adv.pixel.energy

Энергия фотоприёмника в пикселе: доля ФРТ в пикселе с заданным смещением от центра пятна и в блоке N×N вокруг него (сумма блока ≤ 1)

**Returns:** {pixel_um, offset_x_um, offset_y_um, block, pixel_fraction, block_fraction}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `pixel_um` | `float` | да | `null` | — | шаг пикселя, мкм (> 0) |
| `offset_x_um` | `float` | — | `0.0` | — | смещение центра пикселя по x, мкм |
| `offset_y_um` | `float` | — | `0.0` | — | смещение центра пикселя по y, мкм |
| `block` | `int` | — | `1` | — | блок block×block пикселей вокруг точки (неч.) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.pixel.matrix

Пиксельная матрица пятна: интегрирование ФРТ по пикселям заданного шага с подпиксельной передискретизацией — доли энергии в пикселях окна

**Returns:** {pixel_um, size, subsample, matrix [[fraction]], central_fraction, max_fraction, sum_in_window, psf_pitch_um}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `pixel_um` | `float` | да | `null` | — | шаг пикселя, мкм (> 0) |
| `size` | `int` | — | `7` | — | окно матрицы, пикселей (нечётное) |
| `subsample` | `int` | — | `4` | — | подпиксельная кратность передискретизации ФРТ |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `defocus` | `float` | — | `0.0` | — | дефокусировка в длинах волн на краю зрачка |

### adv.psf

Дифракционная ФРТ через FFT зрачковой функции (с параксиальным дефокусом)

**Returns:** масштаб изображения (+решётки psf/x/y при include_grid)

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `128` | — | размер сетки зрачка |
| `field_y` | `float` | — | `0.0` | — | поле |
| `defocus_mm` | `float` | — | `0.0` | — | смещение плоскости установки (мм) |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `include_grid` | `bool` | — | `false` | — | включить решётки psf/x_um/y_um (большой объём) |

### adv.psf.centroid

Энергетический центр (центроид) ФРТ по полям: смещение от опорной оси поля (искажение-like метрика дифракционного пятна)

**Returns:** {rows: [{field, centroid_x_um, centroid_y_um, shift_um}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `fields` | `list` | — | `null` | — | поля (град); по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.psf.focus_stack

Объёмная ФРТ через фокус: сетка дефокуса ±range, в каждой плоскости — пик, Штрель, FWHM сечений x/y и r₈₀ (опция — центральные срезы профилей)

**Returns:** {rows: [{defocus_mm, defocus_waves, peak, strehl, fwhm_x_um, fwhm_y_um, r80_um}], meta}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `defocus_range_mm` | `float` | — | `0.05` | — | ±мм развёртки дефокуса вокруг плоскости Гаусса |
| `num_points` | `int` | — | `9` | — | точек сетки (нечётное, ≥3; чётное округляется +1) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `include_slices` | `bool` | — | `false` | — | включить центральные срезы ФРТ по x для каждой плоскости |

### adv.psf.fwhm

FWHM центральных сечений ФРТ (по x — сагиттальное, по y — меридиональное) с сравнением с диском Эйри

**Returns:** {fwhm_x_um, fwhm_y_um, airy_diameter_um, ratio_x, ratio_y}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `defocus` | `float` | — | `0.0` | — | дефокусировка в длинах волн на краю зрачка |

### adv.psf.poly

Полихроматическая ФРТ: некогерентная взвешенная сумма монохромных ФРТ по λ системы (или явному спектру) на общей координатной сетке

**Returns:** {spectral: [{wl, weight, pitch_um}], peak, fwhm_x_um, fwhm_y_um, r50_um, r80_um (+psf при include_grid)}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `wl_list` | `list` | — | `null` | — | явный спектр λ, мкм (по умолчанию — λ системы) |
| `weights` | `list` | — | `null` | — | веса λ (по умолчанию — веса λ системы или 1) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `include_grid` | `bool` | — | `false` | — | включить решётку psf (Σ=1) и оси |

### adv.psf.waist

Перетяжка ФРТ вдоль оси: положение плоскости максимального пика (параболическое уточнение), осевой FWHM кривой пика и асимметрия полуширин

**Returns:** {z_waist_mm, defocus_waves_at_waist, peak_max, peak_refined, axial_fwhm_mm, half_left_mm, half_right_mm, strehl_at_waist}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `defocus_range_mm` | `float` | — | `0.05` | — | ±мм развёртки дефокуса |
| `num_points` | `int` | — | `21` | — | точек сетки (нечётное, ≥3) |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.ptf

ФКП (PTF): фазовая ЧКХ = arg(OTF), тангенциальная и сагиттальная

**Returns:** {freqs, ptf_tangential, ptf_sagittal, cutoff_freq}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `num_rays` | `int` | — | `128` | — | размер сетки зрачка |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.resolve.thornber

Критерий Торнбера — разрешение по сечениям ЧКХ: частота, где ХУДШЕЕ из тангенциального/сагиттального сечений пересекает порог; дополнительно частота пересечения ветвей (астигматический баланс)

**Returns:** {threshold, rows: [{field, freq_tan_lpmm, freq_sag_lpmm, freq_resolved_lpmm, limiting, crossover_lpmm, astig_gap}]}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `threshold` | `float` | — | `0.1` | — | порог ЧКХ (доли единицы, > 0) |
| `fields` | `list` | — | `null` | — | поля (град); по умолчанию — поля системы |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.slit_image

Изображение щели конечной ширины: 2D-свёртка идеальной щели с дифракционной ФРТ (линия/край/точка — adv.object_image; здесь — конечная щель)

**Returns:** {width_um, along, contrast, edge_10_90_um, min/max профиля (+x/y/ideal/image при include_grid)}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `width_um` | `float` | да | `null` | — | ширина щели, мкм (> 0) |
| `along` | `str` | — | `"x"` | `["x", "y"]` | ось, вдоль которой вытянута щель |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |
| `defocus` | `float` | — | `0.0` | — | дефокусировка в длинах волн на краю зрачка |
| `include_grid` | `bool` | — | `false` | — | включить решётки x/y/ideal/image |

### adv.snr.bars

SNR измерения контраста штрихов через ЧКХ: SNR = 2C·N̄/√(2(N̄+σ_r²)), C = MTF(ν) сечения (танг./саг.), N̄ — средний сигнал на пиксель

**Returns:** {freq_lpmm, mtf_tan, mtf_sag, contrast, snr_tan, snr_sag, snr_min, verdict_tan, verdict_sag}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `freq_lpmm` | `float` | да | `null` | — | частота штрихов, лин/мм (> 0) |
| `signal_e` | `float` | — | `10000.0` | — | средний сигнал, электроны на пиксель (> 0) |
| `read_noise_e` | `float` | — | `5.0` | — | шум чтения, электроны RMS (≥ 0) |
| `snr_min` | `float` | — | `3.0` | — | порог пригодности SNR |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.usaf.object

Ширина штриха элемента миры СШАФ-1951 на плоскости предмета: частота/ширина в изображении → через увеличение (для INFINITE — угловой масштаб ν·f′)

**Returns:** {group, element, freq_image_lpmm, bar_width_image_um, magnification, freq_object_lpmm, bar_width_object_um, angular_lp_per_mrad}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `group` | `int` | да | `null` | — | номер группы миры |
| `element` | `int` | да | `null` | — | номер элемента в группе (1..6) |

### adv.usaf.resolve

Разрешимый элемент миры СШАФ-1951 по сечениям ЧКХ: наиболее мелкий элемент с ЧКХ (танг. и саг.) не ниже порога, с учётом предела Найквиста

**Returns:** {group, element, freq_lpmm, bar_width_um, mtf_tan, mtf_sag, limiting, nyquist_lpmm, cutoff_lpmm, limited_by}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `file` | `str` | — | `null` | — | путь к файлу системы (.opj/.lbo/.json) |
| `system` | `str` | — | `null` | — | имя системы в контексте REPL |
| `lbo_index` | `int` | — | `0` | — | индекс записи в .lbo (если file указывает на библиотеку) |
| `lbo_name` | `str` | — | `null` | — | имя .OPJ-записи в .lbo (приоритетнее lbo_index) |
| `threshold` | `float` | — | `0.1` | — | порог ЧКХ (доли единицы, > 0) |
| `group_from` | `int` | — | `0` | — | начальная группа поиска |
| `group_to` | `int` | — | `7` | — | конечная группа поиска |
| `field_y` | `float` | — | `0.0` | — | поле |
| `wl` | `float` | — | `null` | — | длина волны, мкм (по умолчанию — основная λ) |

### adv.usaf.table

Таблица миры СШАФ-1951: частота элемента ν = 2^(G+(E−1)/6) лин/мм, период и ширина штриха (справочник, без системы)

**Returns:** {rows: [{group, element, freq_lpmm, period_um, bar_width_um}], base_freq_lpmm}

| Имя | Тип | Обяз. | Умолчание | Choices | Описание |
| --- | --- | --- | --- | --- | --- |
| `group_from` | `int` | — | `0` | — | начальная группа (номер группы миры) |
| `group_to` | `int` | — | `5` | — | конечная группа включительно |
| `freq_max_lpmm` | `float` | — | `null` | — | обрезать таблицу по частоте, лин/мм |

