# -*- coding: utf-8 -*-
"""Патч exepack.py: REP-префикс, 8-битные mov, ljmp через [bx], inc/dec."""
import io

src = io.open('exepack.py', encoding='utf-8').read()

NEW_STR = '''            elif b0 in (0xA4, 0xA5, 0xAA, 0xAB, 0xAE, 0xAC, 0xAD):
                def _movsb():
                    s = ea_seg("ds"); e = ea_seg("es")
                    d = 1 if c.df == 0 else -1
                    c.w8(e, c.reg["di"], c.r8(s, c.reg["si"]))
                    c.reg["si"] = (c.reg["si"] + d) & 0xFFFF
                    c.reg["di"] = (c.reg["di"] + d) & 0xFFFF
                def _stosb():
                    e = ea_seg("es")
                    d = 1 if c.df == 0 else -1
                    c.w8(e, c.reg["di"], c.reg["ax"] & 0xFF)
                    c.reg["di"] = (c.reg["di"] + d) & 0xFFFF
                def _stosw():
                    e = ea_seg("es")
                    d = 2 if c.df == 0 else -2
                    c.w16(e, c.reg["di"], c.reg["ax"])
                    c.reg["di"] = (c.reg["di"] + d) & 0xFFFF
                def _scasb():
                    e = ea_seg("es")
                    d = 1 if c.df == 0 else -1
                    v = c.r8(e, c.reg["di"])
                    c.reg["di"] = (c.reg["di"] + d) & 0xFFFF
                    r = (c.reg["ax"] & 0xFF) - v
                    c.cf = r < 0
                    c.flags8(r)
                def _lodsb():
                    s = ea_seg("ds")
                    d = 1 if c.df == 0 else -1
                    al = c.r8(s, c.reg["si"])
                    set_r16("ax", (c.reg["ax"] & 0xFF00) | al)
                    c.reg["si"] = (c.reg["si"] + d) & 0xFFFF
                def _lodsw():
                    s = ea_seg("ds")
                    d = 2 if c.df == 0 else -2
                    set_r16("ax", c.r16(s, c.reg["si"]))
                    c.reg["si"] = (c.reg["si"] + d) & 0xFFFF
                fn = {0xA4: _movsb, 0xAA: _stosb, 0xAB: _stosw,
                      0xAE: _scasb, 0xAC: _lodsb, 0xAD: _lodsw}[b0]
                if rep:
                    while c.reg["cx"]:
                        fn()
                        c.reg["cx"] = (c.reg["cx"] - 1) & 0xFFFF
                        if rep == "rep" and b0 in (0xAE,) and not c.zf:
                            break
                        if rep == "repne" and b0 in (0xAE,) and c.zf:
                            break
                else:
                    fn()'''

OLD_STR = '''            elif b0 == 0xAC:  # lodsb
                s = ea_seg("ds")
                d = 1 if c.df == 0 else -1
                al = c.r8(s, c.reg["si"])
                set_r16("ax", (c.reg["ax"] & 0xFF00) | al)
                c.reg["si"] = (c.reg["si"] + d) & 0xFFFF
            elif b0 == 0xAD:  # lodsw
                s = ea_seg("ds")
                d = 2 if c.df == 0 else -2
                set_r16("ax", c.r16(s, c.reg["si"]))
                c.reg["si"] = (c.reg["si"] + d) & 0xFFFF
            elif b0 == 0xAA:  # stosb
                e = ea_seg("es")
                d = 1 if c.df == 0 else -1
                c.w8(e, c.reg["di"], c.reg["ax"] & 0xFF)
                c.reg["di"] = (c.reg["di"] + d) & 0xFFFF
            elif b0 == 0xAB:  # stosw
                e = ea_seg("es")
                d = 2 if c.df == 0 else -2
                c.w16(e, c.reg["di"], c.reg["ax"])
                c.reg["di"] = (c.reg["di"] + d) & 0xFFFF
            elif b0 == 0xA4:  # movsb
                s = ea_seg("ds")
                e = ea_seg("es")
                d = 1 if c.df == 0 else -1
                v = c.r8(s, c.reg["si"])
                c.w8(e, c.reg["di"], v)
                c.reg["si"] = (c.reg["si"] + d) & 0xFFFF
                c.reg["di"] = (c.reg["di"] + d) & 0xFFFF
            elif b0 == 0xAE:  # scasb
                e = ea_seg("es")
                d = 1 if c.df == 0 else -1
                v = c.r8(e, c.reg["di"])
                c.reg["di"] = (c.reg["di"] + d) & 0xFFFF
                r = (c.reg["ax"] & 0xFF) - v
                c.cf = r < 0
                c.flags8(r)'''

assert OLD_STR in src, "old str op не найден"
src = src.replace(OLD_STR, NEW_STR)

# убрать мусорную ветку inc/dec
src = src.replace('''            elif b0 == 0x40 + 0 or b0 == 0x48:  # inc/ax dec — общий сет ниже
                pass
''', "")

# 8-битные mov
src = src.replace(
    '''            elif b0 in (0x88, 0x89, 0x8A, 0x8B):  # mov r/m,r / r,r/m (16)''',
    '''            elif b0 in (0x88, 0x8A):  # mov r8, r/m8 (только reg,reg)
                mod, regf, rmv, ea, ex = modrm(opb[1:2])
                if mod == 3:
                    def rd8(n):
                        r = ["ax", "cx", "dx", "bx"][n & 3]
                        return (c.reg[r] >> 8) & 0xFF if n > 3 else c.reg[r] & 0xFF
                    def wr8(n, v):
                        r = ["ax", "cx", "dx", "bx"][n & 3]
                        if n > 3:
                            set_r16(r, (c.reg[r] & 0x00FF) | ((v & 0xFF) << 8))
                        else:
                            set_r16(r, (c.reg[r] & 0xFF00) | (v & 0xFF))
                    if b0 == 0x88:
                        wr8(rmv, rd8(regf))
                    else:
                        wr8(regf, rd8(rmv))
                else:
                    raise RuntimeError("mov r8,mem не нужен")
            elif b0 in (0x89, 0x8B):  # mov r/m16,r16 / r16,r/m16 (16)''')

# 16-битный mov: старая ветка обрабатывала 0x88/0x8A как 16 — поправить заголовок внутренностей
src = src.replace('''                regs16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
                if mod == 3:
                    if b0 in (0x88, 0x89):
                        set_r16(regs16[rmv], c.reg[regs16[regf]])
                    else:
                        set_r16(regs16[regf], c.reg[regs16[rmv]])
                else:
                    s = ea_seg()
                    off = ea if not isinstance(ea, tuple) else \\
                        ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] or 0)) + ea[1]) & 0xFFFF
                    if b0 in (0x88, 0x89):
                        c.w16(s, off, c.reg[regs16[regf]])
                    else:
                        set_r16(regs16[regf], c.r16(s, off))''',
'''                regs16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
                if mod == 3:
                    if b0 == 0x89:
                        set_r16(regs16[rmv], c.reg[regs16[regf]])
                    else:
                        set_r16(regs16[regf], c.reg[regs16[rmv]])
                else:
                    s = ea_seg()
                    off = ea if not isinstance(ea, tuple) else \\
                        ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] or 0)) + ea[1]) & 0xFFFF
                    if b0 == 0x89:
                        c.w16(s, off, c.reg[regs16[regf]])
                    else:
                        set_r16(regs16[regf], c.r16(s, off))''')

# ljmp
OLD_LJMP_BEGIN = src.index('            if m == "ljmp"')
OLD_LJMP_END = src.index('            elif m == "retf"')
NEW_LJMP = '''            if b0 == 0xEA:
                o, s = struct.unpack("<HH", opb[1:5])
                c.reg["cs"], c.ip = s, o
                continue
            if b0 == 0xFF:
                mod, regf, rmv, ea2, ex = modrm(opb[1:2])
                if regf in (3, 5):  # jmp far m16:16 (2e ff 2f = jmp [bx])
                    segv = c.reg[seg] if seg else c.reg["cs"]
                    if mod == 3:
                        raise RuntimeError("ff far reg")
                    if mod == 0 and rmv == 6:
                        ptr = ea2
                    else:
                        base, offv = ea2
                        ptr = (c.reg[base[0]] + (c.reg[base[1]] or 0) + offv) & 0xFFFF
                    o1 = c.r16(segv, ptr)
                    o2 = c.r16(segv, ptr + 2)
                    info["ljmp"] = (o2, o1)
                    if verbose:
                        print("LJMP -> %04x:%04x" % (o2, o1))
                    c.reg["cs"] = o2
                    c.ip = o1
                    c.done = True
                    continue
                raise RuntimeError("ff /%d" % regf)
'''
src = src[:OLD_LJMP_BEGIN] + NEW_LJMP + src[OLD_LJMP_END:]

io.open('exepack.py', 'w', encoding='utf-8').write(src)
print("patched OK")
