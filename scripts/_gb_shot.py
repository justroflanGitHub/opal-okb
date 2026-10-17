# -*- coding: utf-8 -*-
"""Скрин окна DOSBox через PrintWindow (работает для фонового окна) -> PNG.

Использование: py scripts/_gb_shot.py capture/gb_xxx.png
"""
import ctypes
import os
import sys

import win32con
import win32gui
import win32ui
from PIL import Image

from _gb_win import find_hwnd


def shot(path):
    h = find_hwnd()
    if not h:
        raise SystemExit('no DOSBox window')
    r = win32gui.GetWindowRect(h)
    w, ht = r[2] - r[0], r[3] - r[1]
    hdc = win32gui.GetWindowDC(h)
    mdc = win32ui.CreateDCFromHandle(hdc)
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mdc, w, ht)
    cdc = mdc.CreateCompatibleDC()
    cdc.SelectObject(bmp)
    # PW_RENDERFULLCONTENT (2) — захват клиентской области даже без фокуса
    ctypes.windll.user32.PrintWindow(h, cdc.GetSafeHdc(), 2)
    bmp.SaveBitmapFile(cdc, path.replace('.png', '.bmp'))
    win32gui.ReleaseDC(h, hdc)
    Image.open(path.replace('.png', '.bmp')).save(path)
    os.remove(path.replace('.png', '.bmp'))
    print('png', os.path.getsize(path))


if __name__ == '__main__':
    shot(sys.argv[1] if len(sys.argv) > 1 else r'capture\gb_shot.png')
