# -*- coding: utf-8 -*-
"""Карта слепого меню MENUOPAL: по клеткам (группа×позиция) жмём ENTER,
читаем заголовок окна (кто запустился), ESC — назад. Выход: карта модулей.
"""
import subprocess
import sys
import time

S = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\scripts'


def title():
    r = subprocess.run(['powershell', '-NoProfile', '-Command',
                        '(Get-Process DOSBox).MainWindowTitle'],
                       capture_output=True, text=True).stdout
    return r.strip().split(',')[-1].strip() if r.strip() else '?'


def key(k, n=1):
    for _ in range(n):
        subprocess.run(['py', '-X', 'utf8', S + r'\dosbox_scan.py', k],
                       capture_output=True)
        time.sleep(0.55)


def cursor():
    sys.path.insert(0, S)
    import ctypes
    from dosbox_rd import get_pid, find_base
    k32 = ctypes.windll.kernel32
    pid = get_pid()
    h = k32.OpenProcess(0x410, False, pid)
    B = find_base(h)
    b = ctypes.create_string_buffer(8)
    g = ctypes.c_size_t(0)
    k32.ReadProcessMemory(h, ctypes.c_void_p(B + 0x450), b, 8, ctypes.byref(g))
    k32.CloseHandle(h)
    d = b.raw[:8]
    return (d[0], d[1])


def main():
    groups = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    print('start title=%s cur=%s' % (title(), cursor()))
    for g in range(groups):
        for c in range(cols):
            key('HOME')
            key('RIGHT', g)
            key('DOWN', c)
            cur = cursor()
            key('ENTER')
            time.sleep(0.8)
            t = title()
            print('g%d c%d cur=%s -> %s' % (g, c, cur, t))
            if t == 'MENUOPAL':
                continue
            key('ESC')
            time.sleep(0.8)
            t2 = title()
            if t2 != 'MENUOPAL':
                print('!! ESC failed, title=%s — stop' % t2)
                return
    print('done')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
