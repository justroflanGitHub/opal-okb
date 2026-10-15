# -*- coding: utf-8 -*-
"""TASK_LAP: пошаговый 16-бит дизассемблер OPALLAP_full.bin с расшифровкой
эмуляции x87 (INT 34..3D, схема REVERSE_OPALO.md: CD 3X = ESC D8+(X-0x34),
CD 3C = ESC сохранен, CD 3D = FISTP-макро). Идет по инструкциям, x87-пары
эмитит как псевдо-мнемоники, вызовы аннотирует именами функций.
Использование: py dis16s.py <lin_start> <lin_end>
"""
import sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_16

RD = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data"
BUF = open(RD + r"\OPALLAP_full.bin", "rb").read()

FUNCS = {}
for ln in open(r"C:\tools\rea-out\_lap_funcs.txt"):
    p = ln.split("|")
    if len(p) < 4:
        continue
    so = p[0].split(":")
    FUNCS.setdefault((int(so[0], 16) << 4) | int(so[1], 16), p[1])

# имена арифметики x87 по (esc, /reg) для mem-форм
ARITH = {0: "FADD", 1: "FMUL", 2: "FCOM", 3: "FCOMP", 4: "FSUB", 5: "FSUBR", 6: "FDIV", 7: "FDIVR"}
D9_MEM = {0: "FLD", 1: None, 2: "FST", 3: "FSTP", 4: "FLDENV", 5: "FLDCW", 6: "FSTENV", 7: "FSTCW"}
D9_REG = {0: "FLD st", 1: "FXCH", 2: "FNOP", 3: "FSTP st", 4: None, 5: None, 6: None, 7: None}
DC_REG = {0: "FADD", 1: "FMUL", 2: "FCOM", 3: "FCOMP", 4: "FSUB", 5: "FSUBR", 6: "FSUB", 7: "FSUBR"}
DD_MEM = {0: "FLD m64", 1: "FISTTP", 2: "FST m64", 3: "FSTP m64", 4: "FRSTOR", 5: None, 6: "FSAVE", 7: "FSTSW"}
DE_REG = {0: "FADDP", 1: "FMULP", 2: "FCOMP", 3: "FCOMPP", 4: "FSUBP", 5: "FSUBRP", 6: "FDIVP", 7: "FDIVRP"}
DF_REG = {0: "FFREE", 1: "FXCH", 2: "FST", 3: "FSTP", 4: "FSTP(?)", 5: "FUCOM", 6: "FUCOMP", 7: None}
INT_ONLY = {0xC0: "F2XM1", 0xC1: "FYL2X", 0xC2: "FPTAN", 0xC3: "FPATAN", 0xC4: "FXTRACT",
            0xC5: "FPREM1", 0xC6: "FDECSTP", 0xC7: "FINCSTP", 0xC8: "FPREM", 0xE0: "FCHS",
            0xE1: "FABS", 0xE4: "FTST", 0xE5: "FXAM", 0xE8: "FLD1", 0xE9: "FLDL2T", 0xEA: "FLDL2E",
            0xEB: "FLDPI", 0xEC: "FLDZ", 0xED: "FLDLG2", 0xEE: "FLDLN2", 0xF0: "F2XM1?",
            0xF1: "FYL2XP1", 0xF2: "FSQRT", 0xF3: "FSINCOS", 0xF4: "FRNDINT", 0xF5: "FSCALE",
            0xF6: "FSIN", 0xF7: "FCOS"}


def name_of(lin):
    return FUNCS.get(lin, "sub_%06x" % lin)


def modrm_info(m, i):
    mod, reg, rm = (m >> 6) & 3, (m >> 3) & 7, m & 7
    if mod == 3:
        return 1, reg, rm, "st,st(%d)" % reg
    disp = 0
    if mod == 0 and rm == 6:
        disp = int.from_bytes(BUF[i + 3:i + 5], "little")
        return 3, reg, rm, "[%04x]" % disp
    if mod == 1:
        d = int.from_bytes(BUF[i + 3:i + 4], "little", signed=True)
        return 2, reg, rm, "%+d" % d
    d = int.from_bytes(BUF[i + 3:i + 5], "little", signed=True)
    return 3, reg, rm, "%+d" % d


def x87_pseudo(i):
    op = BUF[i + 1]
    if op == 0x3D:
        return 2, "FISTP#"
    if op == 0x3C:
        return 2, "ESC#"
    esc = 0xD8 + (op - 0x34)
    m = BUF[i + 2]
    n, reg, rm, ea = modrm_info(m, i)
    total = 2 + n
    if (m >> 6) == 3:
        # регистровые формы
        if esc == 0xD9:
            name = D9_REG.get(reg) or ("D9 /%d" % reg)
        elif esc == 0xDC:
            name = "%s st,st(%d)" % (ARITH.get(reg, "?"), rm)
        elif esc == 0xDD:
            name = "DD /%d st(%d)" % (reg, rm)
        elif esc == 0xDE:
            name = DE_REG.get(rm, "DE /%d" % rm)
        elif esc == 0xDF:
            name = DF_REG.get(rm, "DF /%d" % rm)
        else:
            name = "%s st,st(%d)" % (ARITH.get(reg, "?"), rm)
        if m in INT_ONLY and esc == 0xD9:
            name = INT_ONLY[m]
        return total, "%s %s" % (name, ea)
    else:
        if esc == 0xD9:
            name = D9_MEM.get(reg) or ("D9 /%d" % reg)
        elif esc in (0xD8, 0xDC, 0xDE):
            name = ARITH.get(reg, "%X /%d" % (esc, reg))
            if esc == 0xDC:
                name += " m64"
            if esc == 0xDE:
                name += "P"
        elif esc == 0xDD:
            name = DD_MEM.get(reg) or ("DD /%d" % reg)
        elif esc == 0xDF:
            name = {0: "FILD m16", 1: "FILD m32", 2: "FBLD", 3: "FILDP?", 4: "FST m16?",
                    5: "FILD m64"}.get(reg, "DF /%d" % reg)
        else:
            name = "%X /%d" % (esc, reg)
        return total, "%-10s %s" % (name, ea)


def disasm(lo, hi):
    md = Cs(CS_ARCH_X86, CS_MODE_16)
    out = []
    i = lo
    while i < hi:
        b = BUF[i]
        if b == 0xCD and 0x34 <= BUF[i + 1] <= 0x3D:
            n, txt = x87_pseudo(i)
            out.append("%06x  %-20s %s" % (i, BUF[i:i + n].hex(), txt))
            i += n
            continue
        got = False
        for ins in md.disasm(BUF[i:hi], i, count=1):
            raw = BUF[ins.address:ins.address + ins.size]
            line = "%06x  %-20s %s %s" % (ins.address, raw.hex(), ins.mnemonic, ins.op_str)
            if raw[:1] == b"\x9a":
                off = int.from_bytes(raw[1:3], "little")
                seg = int.from_bytes(raw[3:5], "little")
                line += "   ; -> %s" % name_of((seg << 4) + off)
            if raw[:2] == b"\xcd\x3f":
                line += "   ; INT 3Fh sel=%02x off=%04x" % (
                    BUF[ins.address + 2], int.from_bytes(BUF[ins.address + 3:ins.address + 5], "little"))
            out.append(line)
            i += ins.size
            got = True
        if not got:
            out.append("%06x  %02x          db %02x" % (i, b, b))
            i += 1
    return "\n".join(out)


if __name__ == "__main__":
    lo, hi = int(sys.argv[1], 16), int(sys.argv[2], 16)
    print(disasm(lo, hi))
