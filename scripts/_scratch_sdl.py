# -*- coding: utf-8 -*-
"""Надёжная работа с SDL-окном DOSBox: поиск по заголовку 'DOSBox 0.74',
фокус, отправка сканкодов (usescancodes=true), чтение заголовка,
родной скриншот Ctrl+F5 с копированием в workspace capture/."""
import ctypes
import ctypes.wintypes as wt
import glob
import os
import shutil
import subprocess
import sys
import time

u32 = ctypes.windll.user32
KEYUP, SCAN = 0x0002, 0x0008
SDL_MARK = 'DOSBox 0.74'
CAPDIRS = [r'C:\GOLDEN_DOS\capture', r'C:\tools\dosbox\capture',
           r'C:\Users\mikhail\AppData\Local\DOSBox\capture',
           r'C:\Users\mikhail\.openclaw\workspace\opal_okb\capture']
DST = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\capture'

SCANCODES = {
    'ESC': 0x01, 'ENTER': 0x1C, 'SPACE': 0x39, 'TAB': 0x0F, 'BS': 0x0E,
    'UP': 0x48, 'DOWN': 0x50, 'LEFT': 0x4B, 'RIGHT': 0x4D,
    'F1': 0x3B, 'F2': 0x3C, 'F3': 0x3D, 'F4': 0x3E, 'F5': 0x3F,
    'F6': 0x40, 'F7': 0x41, 'F8': 0x42, 'F9': 0x43, 'F10': 0x44,
    'F11': 0x57, 'F12': 0x58,
    'HOME': 0x47, 'END': 0x4F, 'PGUP': 0x49, 'PGDN': 0x51,
    'INS': 0x52, 'DEL': 0x53, 'DASH': 0x0C, 'POINT': 0x34,
    'LCTRL': 0x1D, 'ALT': 0x38, 'LSHIFT': 0x2A,
    '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
    '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B,
    'PAUSE': 0x45,
}
POS = {'Q': 0x10, 'W': 0x11, 'E': 0x12, 'R': 0x13, 'T': 0x14,
       'Y': 0x15, 'U': 0x16, 'I': 0x17, 'O': 0x18, 'P': 0x19,
       'A': 0x1E, 'S': 0x1F, 'D': 0x20, 'F': 0x21, 'G': 0x22,
       'H': 0x23, 'J': 0x24, 'K': 0x25, 'L': 0x26,
       'Z': 0x2C, 'X': 0x2D, 'C': 0x2E, 'V': 0x2F,
       'B': 0x30, 'N': 0x31, 'M': 0x32}
POS.update({c: SCANCODES[c] for c in '1234567890'})


def dosbox_pid():
    out = subprocess.run(
        ['powershell', '-NoProfile',
         '(Get-Process DOSBox -ErrorAction SilentlyContinue | Select-Object -First 1).Id'],
        capture_output=True, text=True).stdout.strip()
    return int(out) if out else 0


def sdl_hwnd():
    """Вернуть HWND SDL-окна (заголовок начинается с 'DOSBox 0.74')."""
    pid = dosbox_pid()
    if not pid:
        return 0
    found = []

    u32.EnumWindows.restype = ctypes.c_bool

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(h, l):
        p = wt.DWORD()
        u32.GetWindowThreadProcessId(h, ctypes.byref(p))
        if p.value == pid and u32.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(h, buf, 256)
            if buf.value.startswith(SDL_MARK):
                found.append((h, buf.value))
        return True

    u32.EnumWindows(cb, 0)
    return found[0][0] if found else 0


def title(h=None):
    h = h or sdl_hwnd()
    buf = ctypes.create_unicode_buffer(256)
    u32.GetWindowTextW(h, buf, 256)
    return buf.value


def focus(h=None):
    h = h or sdl_hwnd()
    if not h:
        raise SystemExit('no SDL window')
    for _ in range(5):
        u32.ShowWindow(h, 9)
        # ALT-трюк для перехвата foreground
        u32.keybd_event(0, 0x38, SCAN, 0)
        u32.SetForegroundWindow(h)
        u32.keybd_event(0, 0x38, SCAN | KEYUP, 0)
        time.sleep(0.3)
        if u32.GetForegroundWindow() == h:
            return h
    raise SystemExit('cannot focus SDL window: fg=%#x' % u32.GetForegroundWindow())


def raw(scan, up=False, hold=0.0):
    u32.keybd_event(0, scan, (KEYUP if up else 0) | SCAN, 0)
    if hold:
        time.sleep(hold)


def tap(scan, hold=0.08):
    if isinstance(scan, str):
        scan = SCANCODES.get(scan, POS.get(scan[0], 0))
    raw(scan)
    time.sleep(hold)
    raw(scan, up=True)
    time.sleep(0.08)


def combo(mods, key):
    """mods: список сканкодов-модификаторов, key: сканкод."""
    for m in mods:
        raw(m)
    time.sleep(0.06)
    raw(key)
    time.sleep(0.1)
    raw(key, up=True)
    for m in reversed(mods):
        raw(m, up=True)
    time.sleep(0.15)


def send(tokens, settle=0.4):
    """tokens: список строк — имя клавиши или слово из букв."""
    focus()
    time.sleep(settle)
    for tok in tokens:
        if '+' in tok:
            parts = tok.split('+')
            mods = [SCANCODES['LCTRL'] if p == 'CTRL' else
                    SCANCODES['ALT'] if p == 'ALT' else
                    SCANCODES['LSHIFT'] for p in parts[:-1]]
            k = SCANCODES.get(parts[-1], POS.get(parts[-1][0], 0))
            combo(mods, k)
        elif tok in SCANCODES:
            tap(SCANCODES[tok])
        elif tok.isalpha() and len(tok) > 1:
            for ch in tok:
                tap(POS[ch])
        else:
            for ch in tok:
                tap(SCANCODES.get(ch, POS.get(ch.upper(), 0)))
    time.sleep(0.5)


def shots(before):
    """Новые png во всех возможных capture-каталогах."""
    out = []
    for d in CAPDIRS:
        for f in glob.glob(os.path.join(d, '*.png')):
            if f not in before:
                out.append(f)
    return out


def snap_all():
    s = set()
    for d in CAPDIRS:
        s.update(glob.glob(os.path.join(d, '*.png')))
    return s


def screenshot(dst_prefix='shot'):
    """Ctrl+F5 сканкодами; вернуть путь нового png или None."""
    before = snap_all()
    focus()
    time.sleep(0.2)
    combo([SCANCODES['LCTRL']], SCANCODES['F5'])
    time.sleep(1.5)
    new = sorted(shots(before), key=os.path.getmtime)
    if not new:
        return None
    idx = len(glob.glob(os.path.join(DST, dst_prefix + '_*.png')))
    dst = os.path.join(DST, '%s_%03d.png' % (dst_prefix, idx))
    shutil.copy(new[-1], dst)
    return dst


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print('SDL hwnd:', hex(sdl_hwnd()), '|', title())
