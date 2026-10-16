# -*- coding: utf-8 -*-
"""Скриншот нативным Ctrl+F5 DOSBox (foreground SendKeys) -> capture/last.png."""
import glob, os, shutil, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')
BASE = r'C:\Users\mikhail\.openclaw\workspace\opal_okb'
CAP = os.path.join(BASE, 'capture')
def shot(name='last'):
    before = set(glob.glob(os.path.join(CAP, '*.png')))
    r = subprocess.run(['powershell','-NoProfile','-File',
        os.path.join(BASE,'scripts','dosbox_fg_keys.ps1'), '^{F5}'],
        capture_output=True, text=True)
    dst = os.path.join(CAP, f'{name}.png')
    for _ in range(10):
        time.sleep(0.6)
        new = set(glob.glob(os.path.join(CAP, '*.png'))) - before
        if new:
            f = max(new, key=os.path.getmtime)
            shutil.copy(f, dst)
            print(f'shot -> {dst} ({os.path.getsize(dst)} b)')
            return dst
    print('NO SHOT:', r.stdout.strip(), r.stderr.strip())
    return None
if __name__ == '__main__':
    shot(sys.argv[1] if len(sys.argv) > 1 else 'last')
