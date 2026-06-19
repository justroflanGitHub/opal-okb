"""Decode Индустар-23у: f'=110, f/4.5, 7 surfaces, 5 wavelengths."""
import sys, io, struct, math
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from lbo_reader import load_lbo_fast

data = load_lbo_fast('extracted/opal_okb/Lib/LENS.LBO')[3]['opj_data']  # ST01FA04
# Verify it's Индустар-23у
name = data[0x0c:0x34].decode('cp866', errors='replace').replace('\x00','').strip()
print(f'System: {name}')
ns = struct.unpack_from('<H', data, 0x34)[0]
nw = struct.unpack_from('<H', data, 0x38)[0]
print(f'nsurf={ns}, nwl={nw}')

# Dump doubles from 0x60 to 0x120
print(f'\n=== Doubles 0x60-0x120 ===')
for off in range(0x60, 0x120, 8):
    val = struct.unpack_from('<d', data, off)[0]
    if not math.isnan(val) and not math.isinf(val):
        raw = struct.unpack_from('<Q', data, off)[0]
        print(f'  @{off:#x}: {val:>12.6f}  (0x{raw:016x})')

# The data at 0x60-0x80 looks like config
# @0x60: 1100.0? Check
val60 = struct.unpack_from('<d', data, 0x60)[0]
print(f'\n@0x60: {val60}')

# Check 0x5c as double
val5c = struct.unpack_from('<d', data, 0x5c)[0]
print(f'@0x5c: {val5c}')

# Try: 0x60 has f'=110 as double? 
# 9a 99 99 99 99 19 25 40 = ?
val = struct.unpack_from('<d', data, 0x5c)[0]
print(f'@0x5c as double: {val:.4f}')

val = struct.unpack_from('<d', data, 0x60)[0]  
print(f'@0x60 as double: {val:.4f}')

# From hex: @0x60: 9a 99 99 99 99 19 25 40
# 0x4025199999999999a → let's compute
import struct
print(f'0x402519999999999a = {struct.unpack("<d", bytes.fromhex("9a99999999192540"))[0]}')

# That's 10.1 — not 110
# Maybe it's at 0x5c: 9a 99 99 99 99 99 c9 3f
# No, @0x5c starts mid-double

# Actually check @0x58
val58 = struct.unpack_from('<d', data, 0x58)[0]
print(f'@0x58: {val58:.4f}')

# The key: @0xE0 has 4.5 (f/number from description "1:4.5")
# Then @0xE8-0x118: 7 values
# These could be: [semi_diam or thickness for each surface]
# @0xE8: 4.8, @0xF0: 1.9, @0xF8: 8.15, @0x100: 1.55, @0x108: 6.0
# @0x110: 38.4... (this is 0x4415af... = 1e20 marker!)

# Wait — check @0x110:
val110 = struct.unpack_from('<d', data, 0x110)[0]
print(f'\n@0x110: {val110:.4e} — marker?')

# So doubles from 0xE0 to 0x108 (6 values) + marker at 0x110
# But nsurf=7, so need 7 pairs = 14 doubles = 112 bytes
# Only 6 doubles = 48 bytes available → NOT R/d pairs

# INSIGHT: maybe each surface has ONE double (not pair)
# 7 surfaces → 7 doubles from 0xE0 to 0x118
print(f'\n7 doubles from 0xE0:')
for i in range(7):
    off = 0xE0 + i * 8
    val = struct.unpack_from('<d', data, off)[0]
    print(f'  S{i}: {val:.4f}')

# These are: 4.5, 4.8, 1.9, 8.15, 1.55, 6.0, 38.4e15
# Still doesn't look right

# NEW IDEA: Maybe surface data uses 10-byte extended float (Turbo C long double)!
# DOS programs often used 80-bit extended precision
# 10 bytes per value, so 7 surfaces × 2 values × 10 bytes = 140 bytes

print(f'\n=== Try 10-byte extended float (80-bit) ===')
# 80-bit extended: 1 sign + 15 exponent + 64 mantissa
# Stored in 10 bytes
for start in [0xE0, 0x60, 0x80]:
    print(f'\nFrom {start:#x} as 10-byte extended:')
    for i in range(7):
        off = start + i * 10
        if off + 10 > len(data):
            break
        # Read as 80-bit extended float
        raw = data[off:off+10]
        # x87 extended precision: little-endian
        # mantissa (8 bytes) + exponent+sign (2 bytes)
        exp_sign = struct.unpack_from('<H', data, off + 8)[0]
        sign = (exp_sign >> 15) & 1
        exp = exp_sign & 0x7FFF
        mantissa = struct.unpack_from('<Q', data, off)[0]
        if exp == 0 or exp == 0x7FFF:
            continue
        # value = (-1)^sign * mantissa / 2^63 * 2^(exp - 16383)
        val = (mantissa / (2**63)) * (2 ** (exp - 16383))
        if sign:
            val = -val
        if 0.1 < abs(val) < 10000:
            print(f'  S{i}: {val:.4f} (exp={exp}, raw={raw.hex()})')
