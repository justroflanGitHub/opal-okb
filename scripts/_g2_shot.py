# -*- coding: utf-8 -*-
"""Скриншот главного окна DOSBox (не статусного)."""
import sys
import win32gui, win32ui, win32con


def main_hwnd():
    best = None
    def cb(w, _):
        nonlocal best
        t = win32gui.GetWindowText(w)
        if t.startswith('DOSBox 0.74') and win32gui.IsWindowVisible(w):
            best = w
    win32gui.EnumWindows(cb, None)
    return best


def shot(path):
    h = main_hwnd()
    if not h:
        raise SystemExit('no main DOSBox window')
    r = win32gui.GetWindowRect(h)
    w, ht = r[2] - r[0], r[3] - r[1]
    hdc = win32gui.GetWindowDC(h)
    mdc = win32ui.CreateDCFromHandle(hdc)
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mdc, w, ht)
    cdc = mdc.CreateCompatibleDC()
    cdc.SelectObject(bmp)
    cdc.BitBlt((0, 0), (w, ht), mdc, (0, 0), win32con.SRCCOPY)
    bmp.SaveBitmapFile(cdc, path)
    win32gui.ReleaseDC(h, hdc)
    import os
    print('saved', os.path.getsize(path))


if __name__ == '__main__':
    shot(sys.argv[1] if len(sys.argv) > 1 else r'C:\Users\mikhail\.openclaw\workspace\opal_okb\capture\g2_shot.png')
