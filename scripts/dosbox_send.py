"""Отправить клавишу в окно DOSBox.

PostMessage WM_KEYDOWN/WM_KEYUP со сканкодом в lParam — не требует foreground
(SDL DOSBox обрабатывает их в своём message loop). Фолбэк: keybd_event.
Использование: py dosbox_send.py ENTER | ESC | A | F1 | ...
"""
import ctypes, subprocess, sys, time

VK = {'ESC': 0x1B, 'ENTER': 0x0D, 'SPACE': 0x20, 'TAB': 0x09,
      'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,
      'F1': 0x70, 'F3': 0x72, 'F9': 0x78, 'F10': 0x79, 'BS': 0x08}

u32 = ctypes.windll.user32
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x0100, 0x0101, 0x0102

def hwnd():
    out = subprocess.run(['powershell', '-NoProfile',
                          '(Get-Process DOSBox | Select-Object -First 1).MainWindowHandle'],
                         capture_output=True, text=True).stdout.strip()
    return int(out)

def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: dosbox_send.py KEY [KEY...]  (список подряд; CTRL_F5=скриншот)')
    h = hwnd()
    if not h:
        raise SystemExit('no window')

    def tap(vk, extra_ctrl=False, char=True):
        sc = u32.MapVirtualKeyW(vk, 0)
        lp_down = 1 | (sc << 16)
        lp_up = lp_down | (1 << 30) | (1 << 31)
        if extra_ctrl:
            cs = u32.MapVirtualKeyW(0x11, 0)
            clp = 1 | (cs << 16)
            u32.PostMessageW(h, WM_KEYDOWN, 0x11, clp)
            time.sleep(0.03)
        u32.PostMessageW(h, WM_KEYDOWN, vk, lp_down)
        time.sleep(0.03)
        if char:
            u32.PostMessageW(h, WM_CHAR, vk, lp_down)
            time.sleep(0.03)
        u32.PostMessageW(h, WM_KEYUP, vk, lp_up)
        if extra_ctrl:
            time.sleep(0.02)
            u32.PostMessageW(h, WM_KEYUP, 0x11, clp | (1 << 30) | (1 << 31))
        time.sleep(0.12)

    for key in sys.argv[1:]:
        k = key.upper()
        if k == 'CTRL_F5':
            tap(0x74, extra_ctrl=True, char=False)   # скриншот DOSBox
            continue
        if k in ('UP', 'DOWN', 'LEFT', 'RIGHT', 'F1', 'F3', 'F9', 'F10'):
            tap(VK[k], char=False)
            continue
        vk = VK.get(k, ord(k[0]) if len(k) == 1 else 0x0D)
        tap(vk)

if __name__ == '__main__':
    main()
