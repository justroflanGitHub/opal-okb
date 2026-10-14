"""Чтение текстового экрана DOSBox (текстовый режим, VRAM B800) + отправка клавиш.

Использование:
  py dosbox_text.py          → напечатать экран 80x25
  py dosbox_text.py -k "5"   → отправить клавиши (Scan-коды не нужны: PostMessage WM_CHAR),
                               затем напечатать экран
"""
import ctypes, ctypes.wintypes as wt, sys, time

u32 = ctypes.windll.user32
k32 = ctypes.windll.kernel32

PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
WM_CHAR = 0x0102

CP437 = ('☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼' + ' ' * 15 +
         '!"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~⌂'
         'ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐'
         '└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■ ')

def find_dosbox():
    hwnd = u32.FindWindowW(None, None)
    best = None
    u32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)(
        lambda h, l: (best := h) if False else True), 0)  # placeholder
    # проще: по Process name
    import subprocess
    out = subprocess.run(['powershell', '-NoProfile', '(Get-Process DOSBox | Select-Object -First 1).Id'],
                         capture_output=True, text=True).stdout.strip()
    return int(out)

def read_screen(pid):
    h = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h:
        raise OSError('OpenProcess failed')
    # найти базу памяти DOSBox — эмулируемая VRAM лежит в куче хоста; для 0.74
    # сканируем на сигнатуру: адрес, где 25 строк по 160 байт выглядят как
    # текст (чередование char/attr). Сначала пробуем известные смещения malloc-кучи.
    # Надёжный путь: пройтись по всему адресному пространлению.
    mbi = ctypes.create_string_buffer(48)
    MEM_COMMIT = 0x1000
    PAGE_READABLE = (0x02, 0x04, 0x20, 0x40)  # R, RW etc.
    VirtualQueryEx = k32.VirtualQueryEx
    ReadProcessMemory = k32.ReadProcessMemory
    addr = 0
    results = []
    while addr < 0x7FFFFFFFFFFF:
        if VirtualQueryEx(h, ctypes.c_void_p(addr), mbi, 48) == 0:
            addr += 0x1000
            continue
        base = int.from_bytes(mbi[0:8], 'little')
        size = int.from_bytes(mbi[24:32], 'little')
        state = int.from_bytes(mbi[32:36], 'little')
        prot = int.from_bytes(mbi[36:40], 'little')
        if state == MEM_COMMIT and (prot & 0xEE) and size <= 0x10000000:
            CHUNK = 0x10000
            got_prev = b''
            for cbase in range(base, base + size, CHUNK):
                n = min(CHUNK, base + size - cbase)
                buf = ctypes.create_string_buffer(n)
                got = ctypes.c_size_t(0)
                if not ReadProcessMemory(h, ctypes.c_void_p(cbase), buf, n, ctypes.byref(got)) or got.value == 0:
                    got_prev = b''
                    continue
                data = got_prev + buf.raw[:got.value]  # швы между чанками
                got_prev = buf.raw[:got.value][-0x1000:]
                step = 0x800
                for off in range(0, max(1, len(data) - 4000), step):
                    win = data[off:off + 4000]
                    if len(win) < 4000:
                        break
                    printable = sum(1 for i in range(0, 4000, 2)
                                    if 0x20 <= win[i] <= 0x7E or 0x80 <= win[i] <= 0xFF or win[i] in (0x0E,))
                    if printable >= 60:
                        attrs_ok = sum(1 for i in range(1, 4000, 2) if win[i] == win[1])
                        if attrs_ok >= 2800:
                            results.append((base + off, win))
                        elif printable >= 1200 and attrs_ok >= 2000:
                            results.append((base + off, win))  # слабый кандидат (последний — посмотрим)
        addr = base + size
        if addr <= base:
            break
    k32.CloseHandle(h)
    return results

def decode(win):
    lines = []
    for r in range(25):
        line = ''.join(CP437[win[r * 160 + c]] if win[r * 160 + c] < len(CP437) else '?' for c in range(0, 160, 2))
        lines.append(line.rstrip())
    return '\n'.join(lines)

def send_keys(pid, text, delay=0.25):
    """PostMessage WM_CHAR в главное окно — не требует foreground!"""
    import subprocess
    hwnd = int(subprocess.run(['powershell', '-NoProfile',
        '(Get-Process -Id %d).MainWindowHandle' % pid], capture_output=True, text=True).stdout.strip())
    if not hwnd:
        raise OSError('no hwnd')
    u32.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    for ch in text:
        for need_alt in (False,):
            vk = u32.VkKeyScanW(ord(ch))
            if vk == -1:
                continue
            u32.PostMessageW(hwnd, WM_CHAR, ord(ch), 0)
            time.sleep(delay)
    time.sleep(0.3)

if __name__ == '__main__':
    pid = find_dosbox()
    args = [a for a in sys.argv[1:]]
    if '-k' in args:
        send_keys(pid, args[args.index('-k') + 1])
        time.sleep(1.0)
    screens = read_screen(pid)
    sys.stdout.reconfigure(encoding='utf-8')
    # печатаем ВСЕ уникальные кандидаты (по 4 строки превью)
    for i, (base, win) in enumerate(screens):
        print(f'=== screen[{i}] @ {base:#x} ===')
        print(decode(win))
        print()
    if not screens:
        print('NO SCREEN FOUND')
