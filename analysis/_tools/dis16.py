# -*- coding: utf-8 -*-
"""TASK_LAP: 16-бит дизассемблер (capstone) для merged-образа OPALLAP_full.bin.
Аннотирует far-call цели именами функций из _lap_funcs.txt и RTL 1ECB/2AA3.
Использование: py dis16.py <lin_start> <lin_end> [> out.txt]
"""
import sys, bisect
from capstone import *

RD = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data"
BUF = open(RD + r"\OPALLAP_full.bin", "rb").read()

# карта функций: линейный адрес -> имя
FUNCS = {}
for ln in open(r"C:\tools\rea-out\_lap_funcs.txt"):
    p = ln.split("|")
    if len(p) < 4:
        continue
    so = p[0].split(":")
    funcls = (int(so[0], 16) << 4) | int(so[1], 16)
    FUNCS.setdefault(funcls, p[1])
STARTS = sorted(FUNCS)


def name_of(lin):
    if lin in FUNCS:
        return FUNCS[lin]
    return "sub_%06x" % lin


def disasm(lo, hi):
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    md.detail = False
    code = BUF[lo:hi]
    out = []
    for ins in md.disasm(code, lo):
        txt = "%06x  %-22s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str)
        # far call / far jmp: 9a/ea off seg
        if ins.mnemonic in ("callf", "lcall", "call") and ins.bytes[:1] == b"\x9a":
            off = int.from_bytes(ins.bytes[1:3], "little")
            seg = int.from_bytes(ins.bytes[3:5], "little")
            txt += "   ; -> %s" % name_of((seg << 4) + off)
        # int 3Fh остатки
        if ins.bytes[:2] == b"\xcd\x3f":
            txt += "   ; INT 3Fh sel=%02x off=%04x" % (BUF[ins.address + 2],
                                                       int.from_bytes(BUF[ins.address + 3:ins.address + 5], "little"))
        out.append(txt)
    return "\n".join(out)


if __name__ == "__main__":
    lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
    print(disasm(lo, hi))
