# -*- coding: utf-8 -*-
"""
OPAL-OKB — система единиц OPAL-PC «ближний/дальний тип» (реверс §19.2).

Тип предмета/изображения (OPAL.DOC §3.4.1: ближний — «на конечном
расстоянии», дальний — «на бесконечности») переключает единицы ПЕЧАТИ
величин анализа. Правила ANALIZE.DOC:659–680 (= REVERSE_NZR.md §19.2.2),
пул юнитов OPALA.EXE 0x44500–0x445B8:

==================  ==================  ========================
величина            ближний тип         дальний тип
==================  ==================  ========================
поперечные аберр.   мм                  гр.мнсек
продольные аберр.   мм                  дптр
Z'm/Z's             мм                  дптр (от вых. зрачка)
зрачковые корд.     tg*100 / tg'*100    H ЗР / H' ЗР (мм)
сдвиг DS', ЧКХ      мм, лин/мм          дптр, лин/мин
предмет/изображ.    мм                  гр.мнсек (½ углового поля)
==================  ==================  ========================

Порт считает в родных мм/градусах; функции здесь восстанавливают
печать OPAL (эталоны extracted/opal_okb/RT__2236.PRN — осевой пучок
в дптр/гр.мнсек, RT__2250.PRN — колонки «(гр.мнсек)» TABGL).
Переключатель GUI мм/дптр — отдельный слой (utils/optics_utils.py,
``DIOPTRE_PER_M``); этот модуль — конверсии табличной печати.
"""
import decimal
import math

#: 1 дптр = 1/м → 1000 мм на диоптрию (мм → дптр: ``1000/мм``).
MM_PER_DIOPTRE = 1000.0

#: Колонка «(гр.мнсек)» OPAL — f12.6 (эталоны RT__2250 TABGL,
#: RT__2236 TABOC1-дальний).
GMS_WIDTH, GMS_DECIMALS = 12, 6


def mm_to_dioptres(mm) -> float | None:
    """мм → дптр: ``D = 1000/мм`` (продольные/Z'm дальнего типа).

    Табличная печать OPAL оставляет ячейку пустой вместо ∞, поэтому
    ``0`` → ``None`` (в отличие от ``utils.mm_to_dioptre`` с 0 → ±∞ —
    то конверсия положений зрачков для GUI). NaN/±∞ → ValueError.
    """
    mm = float(mm)
    if not math.isfinite(mm):
        raise ValueError(f"ожидалось конечное значение, получено {mm!r}")
    if abs(mm) < 1e-12:
        return None
    return MM_PER_DIOPTRE / mm


def grminsec(angle_deg: float) -> float:
    """Градусы в печатную меру «гр.мнсек»: градусы + минуты/100.

    Тот же закон, что ``tables._grminsec`` (волна 5, побайтовая сверка
    по RT__2250); здесь — каноническое место системы единиц, а ``tables``
    импортирует этот модуль, поэтому закон продублирован, не импортирован.
    Проверка конкурирующих гипотез ТЗ (TASK_UNITS, «−36.000000 при
    2W=72»):

    * «град×3600»: −36° дало бы «-129600.000000» — эталон печатает
      «-36.000000» (RT__2250, предмет зоны 1.000) — ОПРОВЕРГНУТО;
    * «десятичные градусы»: целое −36° согласовано, но ω' = 9.09104°
      эталона напечатано «9.054624», а не «9.091040» — ОПРОВЕРГНУТО
      (RT__2250, изображение зоны 1.000);
    * ВЕРДИКТ: ``целые_градусы + угл_минуты/100`` — 9.09104° =
      9°05.4624' → 9.054624 (точно); −36° → −36.000000 (точно).

    Обратно: :func:`from_grminsec`.
    """
    sign = -1.0 if angle_deg < 0 else 1.0
    a = abs(angle_deg)
    deg = math.floor(a)
    return sign * (deg + (a - deg) * 0.6)


def from_grminsec(value: float) -> float:
    """«гр.мнсек» в градусы (обратное к :func:`grminsec`)."""
    sign = -1.0 if value < 0 else 1.0
    a = abs(value)
    deg = math.floor(a + 1e-9)
    return sign * (deg + (a - deg) / 0.6)


def _fwo(value, width: int, decimals: int) -> str:
    """Поле FORTRAN ``Fw.d`` без ведущего нуля — двойник ``tables._fwo``
    (модули не связаны импортом: ``tables`` → ``units``, не наоборот).

    OPAL печатает «   .816», «   -.535640» (ведущий нуль мантиссы не
    печатается; «-.0000» → «.0000»); ``None`` — пробелы; переполнение
    поля — звёздочки, как FORTRAN. Округление — HALF_UP по десятичному
    разложению, как RTL 0x2E73 (REVERSE_FMT.md §4), а не half-even
    f-строки: 0.0625 при d=3 → «.063».
    """
    if value is None:
        return ' ' * width
    try:
        with decimal.localcontext() as ctx:
            ctx.prec = 60
            q = decimal.Decimal(value).quantize(
                decimal.Decimal(1).scaleb(-decimals),
                rounding=decimal.ROUND_HALF_UP)
        text = f'{q:f}'
    except (decimal.InvalidOperation, ValueError, OverflowError):
        text = f'{value:.{decimals}f}'
    if text.startswith('-') and set(text[1:]) <= {'0', '.'}:
        text = text[1:]
    if text.startswith('0.'):
        text = text[1:]
    elif text.startswith('-0.'):
        text = '-' + text[2:]
    if len(text) > width:
        return '*' * width
    return text.rjust(width)


def deg_to_gms(angle_deg: float, width: int = GMS_WIDTH,
               decimals: int = GMS_DECIMALS) -> str:
    """Угол (град) → строка «гр.мнсек» стилем OPAL f12.6.

    Мера — :func:`grminsec` (град + мин/100), печать — :func:`_fwo`
    без ведущего нуля: ``deg_to_gms(-36.0) == '  -36.000000'``
    (RT__2250), ``deg_to_gms(9.09104) == '    9.054624'``.
    """
    return _fwo(grminsec(angle_deg), width, decimals)


def tg100(angle_deg: float) -> float:
    """Тангенс ×100 — угловая зрачковая координата (ближний тип).

    Пул юнитов OPALA.EXE «(tg*100)»/«(tg'*100)» (§19.1.1): входная/
    выходная координаты луча — 100·тангенсы углов с координатными
    плоскостями зональной СК. Для метки-строки TABOC2 (выходной
    наклон зонального луча) — то же самое от тангенса: ``100·tg u'``.
    """
    return math.tan(math.radians(angle_deg)) * 100.0


def pupil_h_mm(rel: float, ax_mm: float) -> float:
    """H ЗР (мм) — входная зрачковая координата луча: ``отн.зр × Ax``.

    Реверс §19.1: «Н ЗР» шапки TABOC2 = «H ЗР» пула юнитов; эталон
    RT__2236 — зона × 5.0000 при D = 10 точно до 4-го знака
    (номинальная ВХОДНАЯ координата, а не результат трассировки).
    """
    return rel * ax_mm


def pupil_h_out_mm(rel: float, ax_out_mm: float) -> float:
    """H' ЗР (мм) — выходная зрачковая координата: ``отн.зр × Ax'``.

    Штрих — пространство изображений (пул юнитов «(H' ЗР(мм))» 0x4456B;
    «(H ЗР(мм))» без штриха — предметов). Дальнему типу изображения
    отвечают мм на выходной сфере (ANALIZE.DOC:674–680), ближнему —
    угловая tg'*100 (:func:`tg100`).
    """
    return rel * ax_out_mm
