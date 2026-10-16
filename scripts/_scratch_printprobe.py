# -*- coding: utf-8 -*-
"""Автопроб клавиш в меню печати OPAL (RT/OPALA).
Путь: F7 -> Печать -> '2' -> Расчет. После каждой клавиши: скриншот
(Ctrl+F5), хэш, имя PSP (префикс файла скриншота), новые файлы.
Состояние меню может «залипнуть» — детектируем по хэшу.
"""
import ctypes
import glob
import hashlib
import os
import subprocess
import sys
import time

sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts')
import dosbox_scan as ds

u32 = ctypes.windll.user32
CAP = r'C:\GOLDEN_DOS\capture'


def shot():
    u32.keybd_event(0, 0x1D, 8, 0); time.sleep(0.06)
    u32.keybd_event(0, 0x3F, 8, 0); time.sleep(0.12)
    u32.keybd_event(0, 0x3F, 10, 0); time.sleep(0.04)
    u32.keybd_event(0, 0x1D, 10, 0); time.sleep(0.7)


def newest():
    fs = sorted(glob.glob(CAP + r'\*.png'), key=os.path.getmtime)
    return fs[-1] if fs else None


def state():
    f = newest()
    if not f:
        return None, None, None
    h = hashlib.md5(open(f, 'rb').read()).hexdigest()[:8]
    return f, h, os.path.basename(f).split('_')[0].strip()


def key(k, hold=0.12):
    scan = ds.SCAN.get(k)
    if scan is None:
        print('unknown key', k); return
    hw = ds.hwnd(); ds.focus(hw); time.sleep(0.2)
    u32.keybd_event(0, scan, 8, 0); time.sleep(hold)
    u32.keybd_event(0, scan, 10, 0)


def main():
    path = sys.argv[1:] or ['F7', '2']
    hw = ds.hwnd(); ds.focus(hw); time.sleep(0.4)
    f0, h0, m0 = state()
    print('start:', m0, h0)
    for k in path:
        key(k)
        time.sleep(2.0)
        f, h, m = state()
        print('after %-4s -> module=%-8s hash=%s %s' % (k, m, h, 'CHANGED' if h != h0 else 'same'))
        h0 = h
        for nf in sorted(glob.glob(r'C:\GOLDEN_DOS\*.PRN') + glob.glob(r'C:\GOLDEN_DOS\*.pcx')):
            if os.path.getmtime(nf) > time.time() - 300:
                print('  fresh file:', nf)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
