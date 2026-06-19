"""Compare real Индустар-23у data with LBO parsed data."""
import sys, io, struct, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from lbo_reader import load_lbo_fast

# Real data from OPAL-PC
real_surfaces = [
    # (R, d, D/2, glass, n0, n1)
    (30.48,    4.5,  12.35, 'ТК16',  1.612596, 1.625977),
    (0.0,      4.9,  12.10, 'ВОЗДУХ', 1.0,      1.0),
    (-68.23,   1.9,  11.00, 'ЛФ5',   1.574899, 1.593150),
    (28.05,    8.4,  10.50, 'ВОЗДУХ', 1.0,      1.0),
    (-214.8,   1.6,  10.75, 'ОФ1',   1.529401, 1.542489),
    (28.58,    6.0,  11.00, 'ТК20',  1.621995, 1.636002),
    (-44.06,   11.1, 11.10, 'ВОЗДУХ', 1.0,      1.0),  # d= расстояние до изображения
]

# LBO data
data = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')[3]['opj_data']
print('=== LBO hex dump 0x5C-0x120 ===')
for off in range(0x5C, 0x120, 8):
    val = struct.unpack_from('<d', data, off)[0]
    if not math.isnan(val) and not math.isinf(val):
        print(f'  @{off:#x}: {val:.6f}')

# Real R values: 30.48, 0, -68.23, 28.05, -214.8, 28.58, -44.06
# Real d values: 4.5, 4.9, 1.9, 8.4, 1.6, 6.0, 11.1
# Real D/2:      12.35, 12.10, 11.00, 10.50, 10.75, 11.00, 11.10

# Search for 30.48 in LBO data
import struct
target = struct.pack('<d', 30.48)
pos = data.find(target)
print(f'\n30.48 found at: {pos:#x}' if pos >= 0 else '30.48 NOT found')

# Search for -68.23
target2 = struct.pack('<d', -68.23)
pos2 = data.find(target2)
print(f'-68.23 found at: {pos2:#x}' if pos2 >= 0 else '-68.23 NOT found')

# Search for 28.05
target3 = struct.pack('<d', 28.05)
pos3 = data.find(target3)
print(f'28.05 found at: {pos3:#x}' if pos3 >= 0 else '28.05 NOT found')

# Search for -214.8
target4 = struct.pack('<d', -214.8)
pos4 = data.find(target4)
print(f'-214.8 found at: {pos4:#x}' if pos4 >= 0 else '-214.8 NOT found')

# Search for -44.06
target5 = struct.pack('<d', -44.06)
pos5 = data.find(target5)
print(f'-44.06 found at: {pos5:#x}' if pos5 >= 0 else '-44.06 NOT found')

# Search for d=4.5 (already found at 0xE0)
print(f'\n4.5 at 0xE0 confirmed: {struct.unpack_from("<d", data, 0xE0)[0]}')

# Search for D/2=12.35
target_sd = struct.pack('<d', 12.35)
pos_sd = data.find(target_sd)
print(f'12.35 found at: {pos_sd:#x}' if pos_sd >= 0 else '12.35 NOT found')

# Search for 10.55 (Высота по Y from OPAL-PC)
target_y = struct.pack('<d', 10.55)
pos_y = data.find(target_y)
print(f'10.55 found at: {pos_y:#x}' if pos_y >= 0 else '10.55 NOT found')

# So where are the R values stored?
# Maybe R is stored as R×k where k is some scale factor
# Or maybe R is NOT in the LBO at all — it's computed by OPAL-PC from .OPJ

# Let's also check: maybe R values are stored in the .OPJ files inside
# OPALARCH folder, not in LBO
import os, glob
for path in glob.glob('extracted/opal_okb/OPALARCH/**/*.OPJ', recursive=True):
    with open(path, 'rb') as f:
        opj = f.read()
    for r_val in [30.48, -68.23, 28.05]:
        target = struct.pack('<d', r_val)
        if target in opj:
            print(f'{os.path.basename(path)}: contains R={r_val}!')
