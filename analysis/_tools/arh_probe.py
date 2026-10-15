# TASK_OPCOM: разведка формата OPAL.ARH (заголовок/оглавление) и OPAL.PSP
import struct, sys

def arh_map(path):
    data = open(path, 'rb').read()
    print(f"== {path}: size={len(data)} (0x{len(data):X})")
    # ненулевые 16-байтовые строки первых 0x1010 байт
    for base in range(0, min(0x1010, len(data)), 16):
        chunk = data[base:base+16]
        if any(chunk):
            print(f"{base:04x}: {chunk.hex(' ', 4)}")
    # 6-байтовые слоты (off:dword, size:word) в диапазоне оглавления
    print("\n-- интерпретация: слоты 6 байт (off:dword,size:word), первый проход 0..0x1000")
    end = min(0x100, len(data))
    recs = []
    for off in range(0, end - 6, 6):
        o, s = struct.unpack_from('<IH', data, off)
        if o and s and o + s <= len(data):
            recs.append((off, o, s))
    for slot, o, s in recs:
        head = data[o:o + 12]
        print(f"slot@0x{slot:03X} #{slot//6:2d}: off=0x{o:04X} size=0x{s:04X} end=0x{o+s:04X} head={head.hex(' ')}")

if __name__ == '__main__':
    arh_map('extracted/opal_okb/OPAL.ARH')
