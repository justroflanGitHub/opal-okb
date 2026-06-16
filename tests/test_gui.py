import sys
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from PyQt5.QtWidgets import QApplication
app = QApplication([])
from main import MainWindow
w = MainWindow()
print(f'Title: {w.windowTitle()}')
print(f'viz: {hasattr(w, "viz")}')
print(f'analysis: {hasattr(w, "analysis")}')
print(f'surfaces: {len(w.current_system.surfaces)}')
w._load_demo()
print(f'demo loaded: {w.current_system.name}')
w._calculate()
print(f'efl: {w.results.lbl_efl.text()}')
w.close()
print('ALL OK')
