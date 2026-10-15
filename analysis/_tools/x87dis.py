# -*- coding: utf-8 -*-
"""TASK_OPALO: дизассемблер x87-эмуляции Microsoft (FORTRAN 5.0).

Схема эмуляции: ESC-байт D8..DF заменён парой «CD 34+n», следом — ОСТАТОК
инструкции (modrm и т.д.). FWAIT-варианты: 3C..3F. Декодер восстанавливает
x87-мнемонику и печатает позади capstone-8086 для остального кода.
"""
import struct
import sys

import capstone

# 34..3B: INT замещает ESC-байт (D8..DF), следом — modrm(+disp) инструкции.
# 3C: ESC-байт СОХРАНЁН после INT (проверено статистически: 97% след. байт D8-DF).
# 3D: макрос FNSTSW AX (2 байта), далее обычный код (топ-байты после: 8b/les/83).
ESC = {0x34: (0xD8, 0), 0x35: (0xD9, 0), 0x36: (0xDA, 0), 0x37: (0xDB, 0),
       0x38: (0xDC, 0), 0x39: (0xDD, 0), 0x3A: (0xDE, 0), 0x3B: (0xDF, 0)}

# D8: /0 FADD /1 FMUL /2 FCOM /3 FCOMP /4 FSUB /5 FSUBR /6 FDIV /7 FDIVR
D8_ARITH = ["fadd", "fmul", "fcom", "fcomp", "fsub", "fsubr", "fdiv", "fdivr"]
DC_ARITH = D8_ARITH  # те же /reg-коды, память m64
DE_ARITH = ["faddp", "fmulp", "fcomp", "fcompp", "fsubp", "fsubrp", "fdivp", "fdivrp"]

REGS = ["st0", "st1", "st2", "st3", "st4", "st5", "st6", "st7"]
R16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
RM16 = ["bx+si", "bx+di", "bp+si", "bp+di", "si", "di", "bp", "bx"]


def modrm(b, pos):
    """Разбор modrm по 16-битной адресации; возвращает (reg, rm, disp, длина_хвоста)."""
    mod = b >> 6
    reg = (b >> 3) & 7
    rm = b & 7
    tail = 0
    disp = 0
    if mod == 0 and rm == 6:
        disp = None  # direct16 — читаем 2 байта
        return reg, rm, None, 2
    if mod == 1:
        tail = 1
    elif mod == 2:
        tail = 2
    return reg, rm, disp, tail


def mem_str(rm, disp, seg=None):
    base = RM16[rm]
    if disp is None:
        s = "[%x]" % disp if False else ""
    if disp:
        s = "[%s%+x]" % (base, disp) if isinstance(disp, int) else base
    else:
        s = "[%s]" % base
    return ("%s:" % seg + s) if seg else s


def x87_decode(code, i):
    """code[i] == 0xCD, code[i+1] in ESC. Возвращает (текст, длина)."""
    n = code[i + 1]
    if n == 0x3D:
        return "fistp dx:ax (emu)", 2
    if n == 0x3C:
        esc, j = code[i + 2], i + 3
    else:
        esc, j = ESC[n][0], i + 2
    fwait = ""
    b2 = code[j]
    mod = b2 >> 6
    reg = (b2 >> 3) & 7
    rm = b2 & 7
    ln = (j - i) + 1  # CD [xx [esc]] modrm
    if mod == 0 and rm == 6:
        ln += 2  # +disp16
    elif mod == 1:
        ln += 1
    elif mod == 2:
        ln += 2
    if mod != 3:
        disp = None
        if mod == 0 and rm == 6:
            disp = struct.unpack("<H", code[j + 1:j + 3])[0]
        elif mod == 1:
            disp = struct.unpack("<b", code[j + 1:j + 2])[0]
        elif mod == 2:
            disp = struct.unpack("<H", code[j + 1:j + 3])[0]
        m = "[%s]%s" % (RM16[rm] if not (mod == 0 and rm == 6) else "",
                        ("%+x" % disp) if isinstance(disp, int) and not (mod == 0 and rm == 6) else
                        ("%x" % disp if disp is not None else ""))
        if mod == 0 and rm == 6:
            m = "[%x]" % disp
        opnd = m
        # группы: D8/DC — арифметика
        if esc == 0xD8:
            txt = "%s %s" % (D8_ARITH[reg], "dword " + opnd)
        elif esc == 0xDC:
            txt = "%s qword %s" % (DC_ARITH[reg], opnd)
        elif esc == 0xD9:
            g = {0: "fld dword", 2: "fst dword", 3: "fstp dword", 4: "fldenv", 5: "fldcw",
                 6: "fnstenv", 7: "fnstcw"}
            txt = "%s %s" % (g.get(reg, "d9/%d" % reg), opnd)
        elif esc == 0xDD:
            g = {0: "fld qword", 2: "fst qword", 3: "fstp qword", 4: "frstor", 6: "fnsave", 7: "fnstsw"}
            txt = "%s %s" % (g.get(reg, "dd/%d" % reg), opnd)
        elif esc == 0xDB:
            g = {0: "fild dword", 1: "fisttp", 2: "fist dword", 3: "fistp dword",
                 5: "fld tbyte", 7: "fstp tbyte"}
            txt = "%s %s" % (g.get(reg, "db/%d" % reg), opnd)
        elif esc == 0xDA:
            g = {0: "fiadd dword", 1: "fimul dword", 2: "ficom dword", 3: "ficomp dword",
                 4: "fisub dword", 5: "fisubr dword", 6: "fidiv dword", 7: "fidivr dword"}
            txt = "%s %s" % (g.get(reg, "da/%d" % reg), opnd)
        elif esc == 0xDF:
            g = {0: "fild word", 2: "fist word", 3: "fistp word", 5: "fld qword(78?)", 7: "fstp qword"}
            txt = "%s %s" % (g.get(reg, "df/%d" % reg), opnd)
        else:
            txt = "esc?"
    else:
        # регистровая форма
        if esc == 0xD8:
            txt = "%s %s, %s" % (D8_ARITH[reg], REGS[0], REGS[rm])
        elif esc == 0xDC:
            txt = "%s %s, %s" % (["fadd", "fmul", "fcom", "fcomp", "fsubr", "fsub", "fdivr", "fdiv"][reg],
                                 REGS[rm], REGS[0])
        elif esc == 0xD9:
            g = {0: "fld", 1: "fxch", 2: "fnop", 3: "fstp st0"}
            if reg == 0:
                txt = "fld %s" % REGS[rm]
            elif reg == 1:
                txt = "fxch %s" % REGS[rm]
            elif reg == 3 and rm == 1:
                txt = "fstp st0"
            elif reg == 4:  # D9 E0-E7
                ch = {0: "fchs", 1: "fabs", 4: "ftst", 5: "fxam"}.get(rm, "d9e%d" % rm)
                txt = ch
            elif reg == 5:  # D9 F8+ — нет; D9 F0 = f2xm1? нет: D9 F0=f2xm1? да (f2xm1=D9F0)
                ch = {0: "f2xm1", 1: "fyl2x", 2: "fptan", 3: "fpatan", 4: "fxtract", 5: "fprem1",
                      6: "fdecstp", 7: "fincstp"}.get(rm, "d9f%d" % rm)
                txt = ch
            elif reg == 6:
                ch = {0: "fprem", 1: "fyl2xp1", 2: "fsqrt", 3: "fsincos", 4: "frndint",
                      5: "fscale", 6: "fsin", 7: "fcos"}.get(rm, "?")
                txt = ch
            elif reg == 7:
                ch = {0: "fchs?", 1: "fabs?"}.get(rm, "d9ff%d" % rm)
                txt = ch
            else:
                txt = "d9/%d %s" % (reg, REGS[rm])
        elif esc == 0xDD:
            txt = "dd/%d %s" % (reg, REGS[rm]) if reg not in (0, 2, 3) else \
                ("%s %s" % (["ffree", "?", "fst", "fstp"][reg], REGS[rm]))
        elif esc == 0xDE:
            if reg in (0, 1, 4, 5, 6, 7):
                txt = "%s %s, %s" % (DE_ARITH[reg], REGS[rm], REGS[0])
            elif reg == 3 and rm == 1:
                txt = "fcompp"
            else:
                txt = "de/%d %s" % (reg, REGS[rm])
        elif esc == 0xDB:
            txt = "db c/%d %s" % (reg, REGS[rm])
        elif esc == 0xDA:
            txt = "da c/%d %s" % (reg, REGS[rm])
        elif esc == 0xDF:
            txt = "df c/%d %s" % (reg, REGS[rm])
        else:
            txt = "esc?"
    return txt, ln


def disas(code, base, size=None, stop_rets=True):
    """Смешанный дизассемблер: capstone-16 + x87-эмуляция. Возвращает список строк."""
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)
    out = []
    i = 0
    n = len(code) if size is None else min(len(code), size)
    while i < n:
        if code[i] == 0xCD and i + 1 < len(code) and (code[i + 1] in ESC or code[i + 1] in (0x3C, 0x3D)):
            try:
                txt, ln = x87_decode(code, i)
                out.append((base + i, txt.strip(), ln))
                i += ln
                continue
            except Exception:
                pass
        ins = next(md.disasm(bytes(code[i:i + 16]), base + i), None)
        if ins is None:
            out.append((base + i, "db %02x" % code[i], 1))
            i += 1
            continue
        out.append((base + i, "%s %s" % (ins.mnemonic, ins.op_str), ins.size))
        if stop_rets and ins.mnemonic in ("retf",) and ins.mnemonic == "retf":
            break
        i += ins.size
    return out


if __name__ == "__main__":
    # самопроверка: fadd [si], fmul st0,st1, fsqrt
    demo = bytes([0xCD, 0x34, 0x04,          # FADD [si]
                  0xCD, 0x3A, 0xC9,          # FMULP st1, st0
                  0xCD, 0x35, 0xFA])         # FSQRT
    for a, t, l in disas(demo, 0):
        print("%04x: %s" % (a, t))
