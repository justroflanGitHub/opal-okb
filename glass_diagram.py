"""
OPAL-OKB — Диаграмма стёкол (n-V diagram)
Показывает nd vs vd для всех стёкол каталога
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from glass_catalog import GLASS_CATALOG

# Цвета по типу стекла
GLASS_TYPE_COLORS = {
    'К':  '#2ecc71',     # Кроны — зелёный
    'БК': '#3498db',     # Баритовые кроны — синий
    'ТК': '#2980b9',     # Тяжёлые кроны — тёмно-синий
    'ЛК': '#27ae60',     # Лёгкие кроны — светло-зелёный
    'ФК': '#1abc9c',     # Фосфатные кроны — бирюзовый
    'СТК': '#1a5276',    # Сверхтяжёлые кроны — тёмно-синий
    'Ф':  '#e74c3c',     # Флинты — красный
    'ТФ': '#c0392b',     # Тяжёлые флинты — тёмно-красный
    'БФ': '#e67e22',     # Баритовые флинты — оранжевый
    'ЛФ': '#f39c12',     # Лёгкие флинты — жёлто-оранжевый
    'ОФ': '#d35400',     # Особые флинты — коричневый
}

DEFAULT_COLOR = '#95a5a6'  # Серый для неизвестных


def get_glass_color(name: str) -> str:
    """Определить цвет стекла по названию."""
    # Проверяем от длинных префиксов к коротким
    for prefix in sorted(GLASS_TYPE_COLORS.keys(), key=len, reverse=True):
        if name.upper().startswith(prefix):
            return GLASS_TYPE_COLORS[prefix]
    return DEFAULT_COLOR


def get_glass_type_label(name: str) -> str:
    """Определить тип стекла по названию."""
    type_order = ['СТК', 'БК', 'ТК', 'ЛК', 'ФК', 'ТФ', 'БФ', 'ЛФ', 'ОФ', 'Ф', 'К']
    for prefix in type_order:
        if name.upper().startswith(prefix):
            return prefix
    return ''


def plot_glass_diagram(highlight_glasses=None):
    """
    Показать диаграмму nd vs vd для всех стёкол каталога.

    Args:
        highlight_glasses: список марок стёкол для подсветки (из текущей системы)
    """
    try:
        import matplotlib
        matplotlib.use('Qt5Agg')
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    except ImportError:
        print("matplotlib не установлен. Установите: pip install matplotlib")
        return None

    if highlight_glasses is None:
        highlight_glasses = []

    fig, ax = plt.subplots(1, 1, figsize=(10, 7))
    fig.canvas.manager.set_window_title('Диаграмма стёкол — OPAL-OKB')

    # Собираем данные
    plotted_types = {}
    for name, entry in GLASS_CATALOG.items():
        if name in ('ВОЗДУХ', 'AIR'):
            continue
        nd, vd = entry[0], entry[1]
        if vd <= 0:
            continue

        color = get_glass_color(name)
        gtype = get_glass_type_label(name)

        is_highlighted = name in highlight_glasses

        if gtype not in plotted_types:
            plotted_types[gtype] = {'x': [], 'y': [], 'color': color, 'names': []}

        plotted_types[gtype]['x'].append(vd)
        plotted_types[gtype]['y'].append(nd)
        plotted_types[gtype]['names'].append(name)

        if is_highlighted:
            ax.plot(vd, nd, 'o', color='gold', markersize=14, markeredgecolor='black',
                    markeredgewidth=2, zorder=10)
            ax.annotate(name, (vd, nd), fontsize=9, fontweight='bold',
                       ha='left', va='bottom', xytext=(5, 5),
                       textcoords='offset points',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.8))

    # Рисуем точки по типам
    for gtype, data in plotted_types.items():
        label = gtype if gtype else 'Другие'
        ax.scatter(data['x'], data['y'], c=data['color'], s=50, alpha=0.7,
                  label=label, edgecolors='gray', linewidths=0.5)

    ax.set_xlabel('Коэффициент дисперсии $v_d$ (Аббе)', fontsize=12)
    ax.set_ylabel('Показатель преломления $n_d$', fontsize=12)
    ax.set_title('Диаграмма стёкол (ГОСТ 13658-78)', fontsize=14)
    ax.legend(loc='upper right', fontsize=9, ncol=2)
    ax.grid(True, alpha=0.3)

    # Стандартная область для визуализации
    ax.set_xlim(20, 80)
    ax.set_ylim(1.45, 1.85)
    ax.invert_xaxis()  # Обычное соглашение: vd убывает вправо

    fig.tight_layout()
    return fig


class GlassDiagramWindow:
    """Окно диаграммы стёкол для интеграции с PyQt5."""

    def __init__(self, parent=None, highlight_glasses=None):
        try:
            from PyQt5.QtWidgets import QDialog, QVBoxLayout
            import matplotlib
            matplotlib.use('Qt5Agg')
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
        except ImportError:
            raise ImportError("matplotlib и PyQt5 необходимы для диаграммы стёкол")

        self.dialog = QDialog(parent)
        self.dialog.setWindowTitle('Диаграмма стёкол — OPAL-OKB')
        self.dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(self.dialog)

        fig = plot_glass_diagram(highlight_glasses)
        if fig is None:
            return

        self.canvas = FigureCanvas(fig)
        toolbar = NavigationToolbar(self.canvas, self.dialog)

        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)

    def show(self):
        self.dialog.show()
        self.dialog.exec_()


if __name__ == '__main__':
    import matplotlib
    matplotlib.use('Qt5Agg')
    fig = plot_glass_diagram(highlight_glasses=['К8', 'ТФ5'])
    import matplotlib.pyplot as plt
    plt.show()
