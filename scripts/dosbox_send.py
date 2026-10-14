"""Отправить клавишу в окно DOSBox (foreground + vk)."""
import ctypes, subprocess, sys, time

VK = {'ESC': 0x1B, 'ENTER': 0x0D, 'SPACE': 0x20, 'TAB': 0x09, 'UP': 0x26, 'DOWN': 0x28,
      'LEFT': 0x25, 'RIGHT': 0x27, 'F1': 0x70, 'F10': 0x79}

def main():
    key = sys.argv[1] if len(sys.argv) > 1 else 'ENTER'
    vk = VK.get(key.upper(), ord(key[0].upper()) if key else 0x0D)
    u32 = ctypes.windll.user32
    out = subprocess.run(['powershell', '-NoProfile',
                          '(Get-Process DOSBox | Select-Object -First 1).MainWindowHandle'],
                         capture_output=True, text=True).stdout.strip()
    h = int(out)
    if not h:
        raise SystemExit('no window')
    u32.SetForegroundWindow(h)
    time.sleep(0.4)
    for _ in range(2):
        u32.keybd_event(vk, 0, 0, 0)
        time.sleep(0.05)
        u32.keybd_event(vk, 0, 2, 0)
        time.sleep(0.15)

if __name__ == '__main__':
    main()
