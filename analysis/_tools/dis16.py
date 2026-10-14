# -*- coding: utf-8 -*-
"""16-битный дизассемблер (capstone) для COM/EXE-образов реверса TSR."""
import sys
import capstone


def disasm(data, org, start, length, stop_ret=False, raw=False):
    """org — линейный адрес байта data[0]. Возвращает список строк."""
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)
    md.detail = False
    code = data[start:start + length]
    out = []
    count = 0
    for i in md.disasm(code, org + start):
        out.append("%06x  %-23s %s %s" % (i.address, i.bytes.hex(), i.mnemonic, i.op_str))
        count += 1
        if stop_ret and i.mnemonic in ("ret", "retf", "iret"):
            break
        if count > 4000:
            out.append("... STOP 4000 insns")
            break
    return out


if __name__ == "__main__":
    import tsr_lib as T
    name = sys.argv[1]
    start = int(sys.argv[2], 0)
    length = int(sys.argv[3], 0) if len(sys.argv) > 3 else 128
    org = int(sys.argv[4], 0) if len(sys.argv) > 4 else 0
    d = T.load(name)
    if d[:2] == b"MZ":
        inf = T.mz_info(d)
        org = 0x10000  # образ Ghidra-подобно: file 0x200 -> linear 0x10000
        start = start + 0x200 - 0x10000  # если дали linear
    print("\n".join(disasm(d, org, start, length)))
