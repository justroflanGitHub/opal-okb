# -*- coding: utf-8 -*-
"""Отправить реальные клавиши в DOSBox: foreground + keybd_event по VK-кодам.

SendKeys неприменим при русской раскладке Windows (VkKeyScan('d') = -1,
буквы молча теряются), PostMessage SDL 0.74 не обрабатывает. keybd_event
генерирует настоящий ввод: VK -> сканкод -> BIOS -> DOS, регистр в DOS
по умолчанию верхний, Shift не нужен.
Использование: py dosbox_real.py D3 ENTER | py dosbox_real.py UP UP ENTER
"""
import ctypes
import subprocess
import sys
import time

u32 = ctypes.windll.user32
KEYEVENTF_KEYUP = 0x0002

NAMED = {
    'ESC': 0x1B, 'ENTER': 0x0D, 'SPACE': 0x20, 'TAB': 0x09, 'BS': 0x08,
    'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,
    'F1': 0x70, 'F2': 0x71, 'F3': 0x72, 'F4': 0x73, 'F5': 0x74,
    'F6': 0x75, 'F7': 0x76, 'F8': 0x77, 'F9': 0x78, 'F10': 0x79,
    'F12': 0x7B, 'HOME': 0x24, 'END': 0x23, 'PGUP': 0x21, 'PGDN': 0x22,
    'INS': 0x2D, 'DEL': 0x2E, 'DASH': 0xBD, 'POINT': 0xBE,
}


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


def tap(vk, hold=0.05):
    sc = u32.MapVirtualKeyW(vk, 0)
    u32.keybd_event(vk, sc, 0, 0)
    time.sleep(hold)
    u32.keybd_event(vk, sc, KEYEVENTF_KEYUP, 0)
    time.sleep(0.06)


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: dosbox_real.py TOKEN...  (D3 = буквы подряд)')
    h = hwnd()
    if not h:
        raise SystemExit('no window')
    if not focus(h):
        print('warn: foreground check failed', file=sys.stderr)
    for tok in sys.argv[1:]:
        if tok in NAMED:
            tap(NAMED[tok])
        else:
            for ch in tok:
                tap(ord(ch.upper()))
    print('sent:', ' '.join(sys.argv[1:]))


if __name__ == '__main__':
    main()
