"""Отправить клавишу в окно DOSBox.

PostMessage WM_KEYDOWN/WM_KEYUP со сканкодом в lParam — не требует foreground
(SDL DOSBox обрабатывает их в своём message loop). Фолбэк: keybd_event.
Использование: py dosbox_send.py ENTER | ESC | A | F1 | ...
"""
import ctypes, subprocess, sys, time

from _gb_win import find_hwnd

VK = {'ESC': 0x1B, 'ENTER': 0x0D, 'SPACE': 0x20, 'TAB': 0x09,
      'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,
      'F1': 0x70, 'F2': 0x71, 'F3': 0x72, 'F4': 0x73, 'F5': 0x74,
      'F6': 0x75, 'F7': 0x76, 'F8': 0x77, 'F9': 0x78, 'F10': 0x79,
      'F11': 0x7A, 'F12': 0x7B, 'BS': 0x08, 'INS': 0x2D, 'DEL': 0x2E,
      'HOME': 0x24, 'END': 0x23, 'PGUP': 0x21, 'PGDN': 0x22}

u32 = ctypes.windll.user32
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x0100, 0x0101, 0x0102

def hwnd():
    return find_hwnd()

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
        if k in ('UP', 'DOWN', 'LEFT', 'RIGHT', 'INS', 'DEL', 'HOME', 'END', 'PGUP', 'PGDN') or k.startswith('F') and k[1:].isdigit():
            tap(VK[k], char=False)
            continue
        if k in ('_', '#'):
            # шифтованные символы: WM_CHAR их не доставляет — слать Shift+база (US)
            sc_s = u32.MapVirtualKeyW(0x10, 0)
            lp_s = 1 | (sc_s << 16)
            u32.PostMessageW(h, WM_KEYDOWN, 0x10, lp_s)
            time.sleep(0.03)
            tap(0xBD if k == '_' else 0x33, char=False)
            u32.PostMessageW(h, WM_KEYUP, 0x10, lp_s | (1 << 30) | (1 << 31))
            time.sleep(0.05)
            continue
        vk = VK.get(k, ord(k[0]) if len(k) == 1 else 0x0D)
        tap(vk)

if __name__ == '__main__':
    main()
