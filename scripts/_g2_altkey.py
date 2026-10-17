# -*- coding: utf-8 -*-
"""G2: Alt+<клавиша> в DOSBox (keybd_event сканкодами, foreground).
Использование: py _g2_altkey.py 0     -> Alt+0 (активное окно 0)
               py _g2_altkey.py X     -> Alt+X (выход из OPAL)
"""
import sys
import time

sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
import dosbox_scan as ds

u32 = ds.u32
UP = ds.KEYEVENTF_KEYUP | ds.KEYEVENTF_SCANCODE
DOWN = ds.KEYEVENTF_SCANCODE


def alt_combo(tok):
    scan = ds.SCAN.get(tok) or ds.POS.get(tok)
    if not scan:
        raise SystemExit('no scan for ' + tok)
    h = ds.hwnd()
    ds.focus(h)
    time.sleep(0.2)
    u32.keybd_event(0, ds.SCAN['ALT'], DOWN, 0)      # Alt вниз
    time.sleep(0.08)
    u32.keybd_event(0, scan, DOWN, 0)                # клавиша вниз
    time.sleep(0.10)
    u32.keybd_event(0, scan, UP, 0)                  # клавиша вверх
    time.sleep(0.06)
    u32.keybd_event(0, ds.SCAN['ALT'], UP, 0)        # Alt вверх
    time.sleep(0.15)


if __name__ == '__main__':
    for tok in sys.argv[1:]:
        alt_combo(tok)
    print('sent alt+:', ' '.join(sys.argv[1:]))
