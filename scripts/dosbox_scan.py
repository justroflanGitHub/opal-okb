# -*- coding: utf-8 -*-
"""Отправка клавиш в DOSBox ЯВНЫМИ СКАНКОДАМИ (KEYEVENTF_SCANCODE) —
обходит раскладку Windows (русская даёт MapVirtualKey=0 → клавиши терялись).
Сканкоды XT: ENTER=1C ESC=01 SPACE=39 буквы/цифры по рядам, F1..F10=3B..44.
Использование: py dosbox_scan.py ENTER | py dosbox_scan.py F5 ENTER | py dosbox_scan.py D3
(D3 = три буквы подряд)
"""
import ctypes
import subprocess
import sys
import time

u32 = ctypes.windll.user32
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

SCAN = {
    'ESC': 0x01, 'ENTER': 0x1C, 'SPACE': 0x39, 'TAB': 0x0F, 'BS': 0x0E,
    'UP': 0x48, 'DOWN': 0x50, 'LEFT': 0x4B, 'RIGHT': 0x4D,
    'F1': 0x3B, 'F2': 0x3C, 'F3': 0x3D, 'F4': 0x3E, 'F5': 0x3F,
    'F6': 0x40, 'F7': 0x41, 'F8': 0x42, 'F9': 0x43, 'F10': 0x44,
    'HOME': 0x47, 'END': 0x4F, 'PGUP': 0x49, 'PGDN': 0x51,
    'INS': 0x52, 'DEL': 0x53, 'DASH': 0x0C, 'POINT': 0x34,
    'LSHIFT': 0x2A, 'RSHIFT': 0x36, 'LCTRL': 0x1D, 'ALT': 0x38,
    '1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
    '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B,
}
ROWS = ['1234567890', 'QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM']
POS = {'1': 0x02, '2': 0x03, '3': 0x04, '4': 0x05, '5': 0x06,
       '6': 0x07, '7': 0x08, '8': 0x09, '9': 0x0A, '0': 0x0B,
       'Q': 0x10, 'W': 0x11, 'E': 0x12, 'R': 0x13, 'T': 0x14,
       'Y': 0x15, 'U': 0x16, 'I': 0x17, 'O': 0x18, 'P': 0x19,
       'A': 0x1E, 'S': 0x1F, 'D': 0x20, 'F': 0x21, 'G': 0x22,
       'H': 0x23, 'J': 0x24, 'K': 0x25, 'L': 0x26,
       'Z': 0x2C, 'X': 0x2D, 'C': 0x2E, 'V': 0x2F,
       'B': 0x30, 'N': 0x31, 'M': 0x32}


def hwnd():
    out = subprocess.run(
        ['powershell', '-NoProfile',
         '(Get-Process DOSBox | Select-Object -First 1).MainWindowHandle'],
        capture_output=True, text=True).stdout.strip()
    return int(out)


def focus(h):
    u32.SetForegroundWindow(h)
    time.sleep(0.45)
    return u32.GetForegroundWindow() == h


def tap(scan, hold=0.05):
    u32.keybd_event(0, scan, KEYEVENTF_SCANCODE, 0)
    time.sleep(hold)
    u32.keybd_event(0, scan, KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP, 0)
    time.sleep(0.07)


def press_scan(tok):
    if tok in SCAN:
        tap(SCAN[tok])
    else:
        for ch in tok:
            tap(POS[ch])


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: dosbox_scan.py TOKEN... (D3 = буквы подряд)')
    h = hwnd()
    if not h:
        raise SystemExit('no window')
    if not focus(h):
        print('warn: foreground check failed', file=sys.stderr)
    for tok in sys.argv[1:]:
        press_scan(tok)
    print('sent(scan):', ' '.join(sys.argv[1:]))


if __name__ == '__main__':
    main()
