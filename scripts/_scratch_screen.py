# -*- coding: utf-8 -*-
"""Состояние экрана DOSBox: хеш тёмных пикселей по полосам строк + ASCII."""
import subprocess, sys, hashlib

def capture(path=r'C:\Users\mikhail\AppData\Local\Temp\dosbox_vga.png'):
    r = subprocess.run(['powershell','-NoProfile','-File',
        r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts\win_vgashot.ps1',
        '-OutPath', path], capture_output=True, text=True)
    if 'saved' not in r.stdout:
        print(r.stdout, r.stderr); raise SystemExit('capture failed')
    return path

def profile(path=None):
    from PIL import Image
    p = path or capture()
    im = Image.open(p).convert('L')
    w, h = im.size; px = im.load()
    bands = []
    for y0 in range(0, h, 10):
        n = sum(1 for y in range(y0, min(y0+10, h)) for x in range(0, w, 2) if px[x, y] < 200)
        bands.append(n)
    sig = hashlib.md5(bytes(min(255, b) for b in bands)).hexdigest()[:8]
    return sig, bands

if __name__ == '__main__':
    sig, bands = profile()
    print('sig=%s bands=%s' % (sig, bands))
