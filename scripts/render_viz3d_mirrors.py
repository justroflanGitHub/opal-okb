"""Скриншоты 3D-визуализации зеркальных систем (TASK_3DMIRRORS).

Offscreen-платформа Qt не даёт GL-контекст (Windows), поэтому кадр
рендерится программно: настоящий ``_GLWidget.paintGL`` прогоняется через
записывающий GL-стаб (tests/_viz3d_glstub.py), поток примитивов
растеризуется с перспективой, depth-test и alpha-blend. Результат —
PNG, эквивалентный кадру QOpenGLWidget при том же коде отрисовки.

Использование:
    py scripts/render_viz3d_mirrors.py demo [метка]
    py scripts/render_viz3d_mirrors.py lbo  [метка]
PNG пишется во временную папку (аналог /tmp) и печатает путь.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt5.QtWidgets import QApplication

TAG = sys.argv[2] if len(sys.argv) > 2 else 'shot'
WHICH = sys.argv[1] if len(sys.argv) > 1 else 'demo'

app = QApplication([])

from visualization3d import Visualization3D
from tests._viz3d_glstub import render_framebuffer

if WHICH == 'lbo':
    from lbo_reader import load_lbo_fast
    from decode_lbo_opj import decode_lbo_opj
    ents = load_lbo_fast(r'Lib\LENS_SPC.LBO')
    system = decode_lbo_opj(ents[4]['opj_data'])  # «Инфракрасный … з-л»
else:
    from domain.models import create_demo_system_by_name
    system = create_demo_system_by_name('mirror')

viz = Visualization3D()
viz.set_system(system)
print('scene:', viz.get_scene_info())

img, stub = render_framebuffer(viz.gl_widget, 900, 600)
print('primitives:', len(stub.primitives))

out = os.path.join(tempfile.gettempdir(), f'viz3d_mirror_{WHICH}_{TAG}.png')
ok = img.save(out)
print('saved:', out, ok, img.width(), 'x', img.height())

# быстрый пиксельный отчёт: сколько золотых/подложечных пикселей
from PyQt5.QtGui import QImage
n_gold = n_sub = 0
for y in range(img.height()):
    for x in range(img.width()):
        c = img.pixel(x, y)
        r, g, b = (c >> 16) & 255, (c >> 8) & 255, c & 255
        if r > 140 and 100 < g < 210 and b < 110 and r > b + 60:
            n_gold += 1
        elif 55 < r < 140 and 40 < g < 110 and b < 70 and r > b + 25:
            n_sub += 1
print(f'gold px: {n_gold}, substrate px: {n_sub}')
