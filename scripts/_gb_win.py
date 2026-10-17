# -*- coding: utf-8 -*-
"""Поиск окна DOSBox: сперва MainWindowHandle процесса (устойчив к «пропажам»
из EnumWindows), потом EnumWindows по заголовку. Ретраи + разворот без фокуса."""
import ctypes
import subprocess
import time

u32 = ctypes.windll.user32


def _title(h):
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(h, buf, 256)
    return buf.value


def _from_ps():
    out = subprocess.run(
        ['powershell', '-NoProfile',
         '(Get-Process DOSBox | Select-Object -First 1).MainWindowHandle'],
        capture_output=True, text=True).stdout.strip()
    return int(out) if out.isdigit() else 0


def _enum():
    best = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(w, _):
        if _title(w).startswith('DOSBox 0.74'):
            best.append(w)
        return True

    u32.EnumWindows(cb, None)
    return best[0] if best else 0


def find_hwnd(tries=6):
    for _ in range(tries):
        h = _from_ps()
        if h and _title(h).startswith('DOSBox'):
            break
        h = _enum()
        if h:
            break
        time.sleep(0.5)
    else:
        return 0
    if u32.IsIconic(h):
        u32.ShowWindow(h, 4)   # SW_SHOWNOACTIVATE — не крадём фокус
        time.sleep(0.3)
    return h
