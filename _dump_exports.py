"""Call opal_api.dll (32-bit) to read an OPJ file and dump all parameters."""
import sys, struct

dll_path = r'C:\Users\mikhail\.openclaw\workspace\opal_ utils\converter\opal_api.dll'
# Looking at exports: ?OPAL_Read... or similar
# From export list we saw: no explicit read_opj in first 50
# Let's check ALL exports
# Read the DLL exports from the PE export table directly
data = open(dll_path, 'rb').read()
pe_off = struct.unpack_from('<I', data, 0x3C)[0]
num_sections = struct.unpack_from('<H', data, pe_off + 6)[0]
opt_size = struct.unpack_from('<H', data, pe_off + 20)[0]
sections_offset = pe_off + 24 + opt_size

def rva_to_offset(rva):
    for i in range(num_sections):
        off = sections_offset + i * 40
        v_addr = struct.unpack_from('<I', data, off + 12)[0]
        v_size = struct.unpack_from('<I', data, off + 8)[0]
        raw_off = struct.unpack_from('<I', data, off + 20)[0]
        if v_addr <= rva < v_addr + v_size:
            return rva - v_addr + raw_off
    return None

export_rva = struct.unpack_from('<I', data, pe_off + 24 + 96)[0]
exp_off = rva_to_offset(export_rva)
num_names = struct.unpack_from('<I', data, exp_off + 24)[0]
names_rva = struct.unpack_from('<I', data, exp_off + 32)[0]
names_off = rva_to_offset(names_rva)

all_names = []
for i in range(num_names):
    name_rva = struct.unpack_from('<I', data, names_off + i * 4)[0]
    name_off = rva_to_offset(name_rva)
    end = data.find(b'\x00', name_off)
    name = data[name_off:end].decode('ascii')
    all_names.append(name)

# Print ALL exports
print(f"Total exports: {len(all_names)}")
for n in all_names:
    print(f"  {n}")
