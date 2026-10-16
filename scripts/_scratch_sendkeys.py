"""Отправка реальных клавиш в DOSBox: foreground + SendInput (keybd_event)."""
import ctypes, subprocess, sys, time

u32 = ctypes.windll.user32

def hwnd():
    out = subprocess.run(['powershell','-NoProfile',
        '(Get-Process DOSBox | Select-Object -First 1).MainWindowHandle'],
        capture_output=True, text=True).stdout.strip()
    return int(out)

def key(vk, up=False):
    sc = u32.MapVirtualKeyW(vk, 0)
    flags = 0x8 if up else 0  # KEYEVENTF_KEYUP
    ctypes.windll.user32.keybd_event(vk, sc, flags, 0)

def focus(tries=6):
    h = hwnd()
    for _ in range(tries):
        u32.ShowWindow(h, 9)
        # классический трюк: ALT вниз позволяет перехватить foreground
        key(0x12); u32.SetForegroundWindow(h); key(0x12, up=True)
        time.sleep(0.25)
        fg = u32.GetForegroundWindow()
        if fg == h:
            return h
        # минимизировать/восстановить как запасной вариант
        u32.ShowWindow(h, 6); time.sleep(0.15); u32.ShowWindow(h, 9); time.sleep(0.3)
    raise SystemExit(f"cannot get foreground (fg={u32.GetForegroundWindow():#x}, want={h:#x})")

def tap(vk, hold=0.06):
    key(vk); time.sleep(hold); key(vk, up=True); time.sleep(0.1)

def combo(mods, vk):
    for m in mods: key(m)
    time.sleep(0.05)
    key(vk); time.sleep(0.08); key(vk, up=True)
    for m in reversed(mods): key(m, up=True)
    time.sleep(0.2)

CTRL, ALT, SHIFT = 0x11, 0x12, 0x10
NAMED = {'ENTER':0x0D,'ESC':0x1B,'SPACE':0x20,'TAB':0x09,'BS':0x08,
         'UP':0x26,'DOWN':0x28,'LEFT':0x25,'RIGHT':0x27,
         'F1':0x70,'F2':0x71,'F3':0x72,'F4':0x73,'F5':0x74,'F6':0x75,'F7':0x76,
         'F8':0x77,'F9':0x78,'F10':0x79,'HOME':0x24,'END':0x23,'PGUP':0x21,'PGDN':0x22,
         'INS':0x2D,'DEL':0x2E}

if __name__ == '__main__':
    focus()
    for tok in sys.argv[1:]:
        t = tok.upper()
        parts = t.split('+')
        if len(parts) > 1:
            mods = [{'CTRL':CTRL,'ALT':ALT,'SHIFT':SHIFT}[p] for p in parts[:-1]]
            vk = NAMED.get(parts[-1], ord(parts[-1][0]))
            combo(mods, vk)
        elif t in NAMED:
            tap(NAMED[t])
        elif t == 'CTRL_F5':
            combo([CTRL], 0x74)
        else:
            for ch in tok:
                vk = u32.VkKeyScanW(ord(ch))
                tap(vk & 0xFF, 0.05)
                if (vk >> 8) & 1: pass
