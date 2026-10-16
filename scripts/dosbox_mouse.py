# -*- coding: utf-8 -*-
"""Реальный клик мышью в клиентскую область DOSBox (после foreground).
DOSBox 0.74 захватывает мышь по клику — далее события идут в int 33h.
Использование: py dosbox_mouse.py [click|move|double|right]  (по умолчанию click)
"""
import ctypes
import subprocess
import sys
import time

u32 = ctypes.windll.user32
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MOVE = 0x0001


def hwnd():
    out = subprocess.run(
        ['powershell', '-NoProfile',
         '(Get-Process DOSBox | Select-Object -First 1).MainWindowHandle'],
        capture_output=True, text=True).stdout.strip()
    return int(out)


class RECT(ctypes.Structure):
    _fields_ = [('l', ctypes.c_long), ('t', ctypes.c_long),
                ('r', ctypes.c_long), ('b', ctypes.c_long)]


def main():
    args = sys.argv[1:]
    mode = args[0] if args else 'click'
    at = None
    if len(args) >= 3 and args[-2].lstrip('-').isdigit() and args[-1].lstrip('-').isdigit():
        at = (int(args[-2]), int(args[-1]))
    h = hwnd()
    if not h:
        raise SystemExit('no window')
    u32.SetForegroundWindow(h)
    time.sleep(0.5)
    rc = RECT()
    u32.GetClientRect(h, ctypes.byref(rc))
    pt = ctypes.wintypes.POINT() if False else None
    # screen coords of client center
    class P(ctypes.Structure):
        _fields_ = [('x', ctypes.c_long), ('y', ctypes.c_long)]
    p = P(at[0] if at else rc.r // 2, at[1] if at else rc.b // 2)
    u32.ClientToScreen(h, ctypes.byref(p))
    ctypes.windll.user32.SetCursorPos(p.x, p.y)
    time.sleep(0.3)
    if mode == 'move':
        for dx in range(-60, 61, 10):
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_MOVE, dx, 5, 0, 0)
            time.sleep(0.08)
        print('moved')
        return
    if mode == 'double':
        for _ in range(2):
            u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05)
            u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.15)
    elif mode == 'right':
        u32.mouse_event(MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        u32.mouse_event(MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    else:
        u32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        u32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    print('clicked', mode, 'at', p.x, p.y)


if __name__ == '__main__':
    import ctypes.wintypes  # noqa
    main()
