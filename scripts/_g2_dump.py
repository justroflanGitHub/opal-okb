# G2 scratch: показать эталонный .PRN и hex OPAL.ARH / OPAL.PSP
import sys

base = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb'

def hexdump(d, start=0, end=None, step=16):
    end = len(d) if end is None else min(end, len(d))
    for b in range(start, end, step):
        chunk = d[b:b+step]
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
        print(f'{b:04x}: {chunk.hex(" "):47}  {asc}')

if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'prn'
    if what == 'prn':
        d = open(base + r'\RT__2236.PRN', 'rb').read()
        print(f'== RT__2236.PRN size={len(d)}')
        print(d.decode('cp866', errors='replace'))
        d2 = open(base + r'\RT__2250.PRN', 'rb').read()
        print(f'== RT__2250.PRN size={len(d2)}')
        print(d2.decode('cp866', errors='replace'))
    elif what == 'arh':
        d = open(base + r'\OPAL.ARH', 'rb').read()
        print(f'== OPAL.ARH size={len(d)} (0x{len(d):X})')
        hexdump(d, 0, 0x140)
        print('... tail:')
        hexdump(d, len(d)-0x40)
    elif what == 'psp':
        d = open(base + r'\OPAL.PSP', 'rb').read()
        print(f'== OPAL.PSP size={len(d)} (0x{len(d):X})')
        hexdump(d, 0, min(len(d), 0x200))
