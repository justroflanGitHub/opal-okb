# -*- coding: utf-8 -*-
"""EXEPACK-распаковщик OPALA.EXE (и соседних EXE поставки).

Исполняет стаб-распаковщик (вход MZ CS:IP) на мини-интерпретаторе 8086.
Трюк: PSP кладём в сегмент 0xFFF0, чтобы load-сегмент получился 0 —
тогда релокации добавляют 0 и образ остаётся ПРЕ-релокационным
(сегменты как в иммедиатах кода: 0x2e73, 0x506e, 0x52d4...).
"""
import struct
import capstone
import tsr_lib as T


class CPU:
    def __init__(self, mem, cs, ip, psp=0xFFF0):
        self.m = mem                    # bytearray(1MB), линейная адресация
        self.reg = {"ax": 0, "bx": 0, "cx": 0, "dx": 0, "si": 0, "di": 0,
                    "bp": 0, "sp": 0x100, "es": psp, "cs": cs, "ss": 0, "ds": psp}
        self.ip = ip
        self.df = 0
        self.zf = self.cf = self.sf = self.of = self.pf = False
        self.trace = False
        self.done = False
        self.steps = 0

    # ---------- память ----------
    def lin(self, seg, off):
        return ((seg << 4) + (off & 0xFFFF)) & 0xFFFFF

    def r8(self, seg, off):
        return self.m[self.lin(seg, off)]

    def w8(self, seg, off, v):
        self.m[self.lin(seg, off)] = v & 0xFF

    def r16(self, seg, off):
        return self.r8(seg, off) | (self.r8(seg, off + 1) << 8)

    def w16(self, seg, off, v):
        self.w8(seg, off, v)
        self.w8(seg, off + 1, v >> 8)

    # ---------- флаги ----------
    def _szp(self, r):
        self.zf = (r == 0)
        self.sf = bool(r & 0x8000 if r & 0x10000 == 0 else r & 0x80)
        return r

    def flags16(self, r):
        r &= 0xFFFF
        self.zf = r == 0
        self.sf = bool(r & 0x8000)
        self.pf = bin(r & 0xFF).count("1") % 2 == 0

    def flags8(self, r):
        r &= 0xFF
        self.zf = r == 0
        self.sf = bool(r & 0x80)
        self.pf = bin(r).count("1") % 2 == 0

    # ---------- основные ----------
    def push(self, v):
        self.reg["sp"] = (self.reg["sp"] - 2) & 0xFFFF
        self.w16(self.reg["ss"], self.reg["sp"], v)

    def pop(self):
        v = self.r16(self.reg["ss"], self.reg["sp"])
        self.reg["sp"] = (self.reg["sp"] + 2) & 0xFFFF
        return v

    def sub(self, a, b, w=16):
        r = a - b
        if w == 16:
            self.cf = r < 0
            self.flags16(r)
        else:
            self.cf = r < 0
            self.flags8(r)
        return r & ((1 << (8 * w)) - 1)

    def add(self, a, b, w=16, carry=0):
        r = a + b + carry
        mask = (1 << (8 * w)) - 1
        self.cf = r > mask
        if w == 16:
            self.flags16(r & 0xFFFF)
            self.of = ((a ^ r) & (b ^ r) & 0x8000) != 0
        else:
            self.flags8(r & 0xFF)
            self.of = ((a ^ r) & (b ^ r) & 0x80) != 0
        return r & mask

    def logic_flags(self, r, w=16):
        self.cf = self.of = False
        (self.flags16 if w == 16 else self.flags8)(r)


RM16 = ["bxsi", "bxdi", "bpsi", "bpsi", "si", "di", "bp", "bx"]
RM8 = ["al", "cl", "dl", "bl", "ah", "ch", "dh", "bh"]


def run_stub(data, verbose=False, max_steps=2_000_000):
    """data: полный EXE-файл. Возвращает (mem, info) с распакованным образом."""
    inf = T.mz_info(data)
    img_bytes = (inf["pages"] - 1) * 512 + (inf["bytes_last"] or 512)
    mem = bytearray(1 << 20)
    # load image: файл 0x200.. -> линейно load*16; PSP=0xFFF0 → load=0x10000-0x10?? НЕТ:
    # хотим load=0 ⇒ PSP = 0xFFFF-... : PSP+0x10 = 0 ⇒ PSP = 0xFFF0 (линейно 0xFFF00),
    # образ с файла 0x200 пишем в линейный 0.
    psp = 0xFFF0
    load = ((psp + 0x10) & 0xFFFF)
    assert load == 0, load
    mem[0: img_bytes - inf["hdr_para"] * 16] = data[inf["hdr_para"] * 16: img_bytes]
    cpu = CPU(mem, (inf["cs"] + load) & 0xFFFF, inf["ip"], psp=psp)
    # SS:SP инициализируем (стаб сам поставит свои, но push до того — нет)
    cpu.reg["ss"] = (inf["ss"] + load) & 0xFFFF
    cpu.reg["sp"] = inf["sp"]
    info = {"entry_cs": inf["cs"], "entry_ip": inf["ip"], "load": load,
            "img_bytes": img_bytes, "ljmp": None, "insns": 0, "records": 0}

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)

    def fetch():
        c = cpu
        seg = c.reg["cs"]
        # читаем до 8 байт инструкции
        raw = bytes(c.m[c.lin(seg, c.ip): c.lin(seg, c.ip) + 16])
        insns = list(md.disasm(raw, 0))
        if not insns:
            raise RuntimeError("undecodable at cs:%04x ip=%04x" % (seg, c.ip))
        return insns[0]

    c = cpu
    while not c.done and c.steps < max_steps:
        i = fetch()
        c.steps += 1
        info["insns"] = c.steps
        m = i.mnemonic
        op = i.op_str
        seg_pre = None
        raw = i.bytes
        # префиксы: capstone склеивает их в insn; разберём по байтам
        pos = [0]

        def eat_prefix():
            p = None
            while pos[0] < len(raw):
                b = raw[pos[0]]
                if b in (0x26, 0x2E, 0x36, 0x3E):
                    p = {0x26: "es", 0x2E: "cs", 0x36: "ss", 0x3E: "ds"}[b]
                    pos[0] += 1
                elif b == 0xF3:
                    p = ("rep", p)
                    pos[0] += 1
                elif b == 0xF2:
                    p = ("repne", p)
                    pos[0] += 1
                elif b == 0xFD:
                    c.df = 1
                    pos[0] += 1
                elif b == 0xFC:
                    c.df = 0
                    pos[0] += 1
                elif b in (0xFA, 0xFB):  # cli/sti
                    pos[0] += 1
                elif b == 0x90:
                    pos[0] += 1
                else:
                    break
            return p

        pre = eat_prefix()
        rep = None
        seg = None
        if isinstance(pre, tuple):
            rep, seg = pre
        elif pre in ("es", "cs", "ss", "ds"):
            seg = pre
        if pos[0] >= len(raw):
            c.ip = (c.ip + len(raw)) & 0xFFFF
            continue
        opb = raw[pos[0]:]

        def modrm(bs):
            """разбор modrm; bs — срез байт начиная с modrm-байта"""
            bs = bytes(bs)
            b = bs[0]
            mod = b >> 6
            reg = (b >> 3) & 7
            rm = b & 7
            ea = None
            extra = 0
            if mod == 3:
                return mod, reg, rm, None, 0
            if mod == 0 and rm == 6:
                ea = struct.unpack("<H", bs[1:3])[0]
                return mod, reg, rm, ea, 2
            base = {0: ("bx", "si"), 1: ("bx", "di"), 2: ("bp", "si"),
                    3: ("bp", "di"), 4: ("si", None), 5: ("di", None),
                    6: ("bp", None), 7: ("bx", None)}[rm]
            off = 0
            if mod == 1:
                off = struct.unpack("<b", bs[1:2])[0]
                extra = 1
            elif mod == 2:
                off = struct.unpack("<h", bs[1:3])[0]
                extra = 2
            ea = off
            return mod, reg, rm, (base, off), extra

        def ea_seg(default=None):
            return c.reg[seg] if seg else (c.reg[default] if default else c.reg["ds"])

        def get_r16(name):
            return c.reg[name]

        def set_r16(name, v):
            c.reg[name] = v & 0xFFFF

        nxt = (c.ip + len(raw)) & 0xFFFF

        try:
            b0 = opb[0]
            if b0 == 0xEA:
                o, s = struct.unpack("<HH", opb[1:5])
                c.reg["cs"], c.ip = s, o
                continue
            if b0 == 0xFF:
                mod, regf, rmv, ea2, ex = modrm(opb[1:])
                if regf in (3, 5):  # jmp far m16:16 (2e ff 2f = jmp [bx])
                    segv = c.reg[seg] if seg else c.reg["cs"]
                    if mod == 3:
                        raise RuntimeError("ff far reg")
                    if mod == 0 and rmv == 6:
                        ptr = ea2
                    else:
                        base, offv = ea2
                        ptr = (c.reg[base[0]] + (c.reg[base[1]] if base[1] else 0) + offv) & 0xFFFF
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
            elif m == "retf" or b0 == 0xCB:
                c.ip = c.pop()
                c.reg["cs"] = c.pop()
            elif m == "int":
                raise RuntimeError("INT %#x при распаковке (данные повреждены?)" % opb[1])
            elif m == "hlt":
                raise RuntimeError("HLT")
            elif b0 in (0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77,
                        0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F, 0xE3):
                rel = struct.unpack("<b", opb[1:2])[0]
                take = False
                t = b0 & 0xF
                base = (b0 & 0xF0)
                if b0 == 0xE3:
                    take = c.reg["cx"] == 0
                elif base == 0x70:
                    cond = [c.of, c.of, c.cf, c.cf, c.zf, c.zf,
                            c.cf or c.zf, c.cf or c.zf,
                            c.sf, c.sf, c.pf, c.pf,
                            c.sf != c.of, c.sf != c.of,
                            c.cf or (c.sf != c.of), c.cf or (c.sf != c.of)][t]
                    take = cond if (t % 2 == 0) else not cond
                c.ip = (nxt + (rel if take else 0)) & 0xFFFF
                continue
            elif b0 == 0xEB or b0 == 0xE9:
                if b0 == 0xEB:
                    rel = struct.unpack("<b", opb[1:2])[0]
                else:
                    rel = struct.unpack("<h", opb[1:3])[0]
                c.ip = (nxt + rel) & 0xFFFF
                continue
            elif b0 == 0xE2:  # loop
                rel = struct.unpack("<b", opb[1:2])[0]
                c.reg["cx"] = (c.reg["cx"] - 1) & 0xFFFF
                if c.reg["cx"]:
                    c.ip = (nxt + rel) & 0xFFFF
                else:
                    c.ip = nxt
                continue
            elif b0 in (0xA4, 0xA5, 0xAA, 0xAB, 0xAE, 0xAC, 0xAD):
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
                    fn()
            elif b0 in (0x50, 0x51, 0x52, 0x53, 0x55, 0x56, 0x57):
                c.push(c.reg[["ax", "cx", "dx", "bx", "bp", "si", "di"][b0 - 0x50]])
            elif b0 in (0x58, 0x59, 0x5A, 0x5B, 0x5D, 0x5E, 0x5F):
                set_r16(["ax", "cx", "dx", "bx", "bp", "si", "di"][b0 - 0x58], c.pop())
            elif b0 in (0x06, 0x0E, 0x16, 0x1E):  # push sreg
                c.push(c.reg[["es", "cs", "ss", "ds"][(b0 >> 3) & 3]])
            elif b0 in (0x07, 0x17, 0x1F):  # pop sreg (кроме cs)
                set_r16(["es", "ss", "ds"][[0x07, 0x17, 0x1F].index(b0)], c.pop())
            elif b0 == 0x8C:  # mov r16/m16, sreg
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                val = c.reg[["es", "cs", "ss", "ds"][regf]]
                if mod == 3:
                    set_r16(["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"][rmv], val)
                else:
                    s = ea_seg()
                    off = ea if not isinstance(ea, tuple) else \
                        ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] if ea[0][1] else 0)) + ea[1]) & 0xFFFF
                    c.w16(s, off, val)
            elif b0 == 0x8E:  # mov sreg, r16/m16
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                if mod == 3:
                    val = c.reg[["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"][rmv]]
                else:
                    s = ea_seg()
                    off = ea if not isinstance(ea, tuple) else \
                        ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] if ea[0][1] else 0)) + ea[1]) & 0xFFFF
                    val = c.r16(s, off)
                set_r16(["es", "cs", "ss", "ds"][regf], val)
            elif b0 in (0x88, 0x8A):  # mov r8, r/m8 (только reg,reg)
                mod, regf, rmv, ea, ex = modrm(opb[1:])
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
            elif b0 in (0x89, 0x8B):  # mov r/m16,r16 / r16,r/m16 (16)
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                regs16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
                if mod == 3:
                    if b0 == 0x89:
                        set_r16(regs16[rmv], c.reg[regs16[regf]])
                    else:
                        set_r16(regs16[regf], c.reg[regs16[rmv]])
                else:
                    s = ea_seg()
                    off = ea if not isinstance(ea, tuple) else \
                        ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] if ea[0][1] else 0)) + ea[1]) & 0xFFFF
                    if b0 == 0x89:
                        c.w16(s, off, c.reg[regs16[regf]])
                    else:
                        set_r16(regs16[regf], c.r16(s, off))
            elif b0 == 0x8D:  # lea r16, m
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                off = ea if not isinstance(ea, tuple) else \
                    ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] if ea[0][1] else 0)) + ea[1]) & 0xFFFF
                set_r16(["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"][regf], off)
            elif b0 == 0xA0:  # mov al, [imm16]
                s = ea_seg("ds")
                set_r16("ax", (c.reg["ax"] & 0xFF00) | c.r8(s, struct.unpack("<H", opb[1:3])[0]))
            elif b0 == 0xA1:
                s = ea_seg("ds")
                set_r16("ax", c.r16(s, struct.unpack("<H", opb[1:3])[0]))
            elif b0 == 0xA2:
                s = ea_seg("ds")
                c.w8(s, struct.unpack("<H", opb[1:3])[0], c.reg["ax"] & 0xFF)
            elif b0 == 0xA3:
                s = ea_seg("ds")
                c.w16(s, struct.unpack("<H", opb[1:3])[0], c.reg["ax"])
            elif b0 in (0xB8, 0xB9, 0xBA, 0xBB, 0xBE, 0xBF):
                set_r16(["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"][b0 - 0xB8],
                        struct.unpack("<H", opb[1:3])[0])
            elif b0 in (0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7):
                hi = b0 >= 0xB4
                v = opb[1]
                if hi:
                    set_r16(["ah", "ch", "dh", "bh"][b0 - 0xB4].replace("ah", "ax"), v)
                    # проще: установим старший байт соотв. регистра
                    r = ["ax", "cx", "dx", "bx"][b0 - 0xB4]
                    set_r16(r, (v << 8) | (c.reg[r] & 0xFF))
                else:
                    r = ["ax", "cx", "dx", "bx"][b0 - 0xB0]
                    set_r16(r, (c.reg[r] & 0xFF00) | v)
            elif b0 == 0x01 or b0 == 0x03:  # add r/m16,r16 / r16,r/m16
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                regs16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
                if mod == 3:
                    a, bq = (c.reg[regs16[rmv]], c.reg[regs16[regf]]) if b0 == 1 \
                        else (c.reg[regs16[regf]], c.reg[regs16[rmv]])
                    set_r16(regs16[rmv] if b0 == 1 else regs16[regf], c.add(a, bq))
                else:
                    s = ea_seg()
                    off = ea if not isinstance(ea, tuple) else \
                        ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] if ea[0][1] else 0)) + ea[1]) & 0xFFFF
                    if b0 == 1:
                        c.w16(s, off, c.add(c.r16(s, off), c.reg[regs16[regf]]))
                    else:
                        set_r16(regs16[regf], c.add(c.r16(s, off), c.reg[regs16[rmv]]))
            elif b0 == 0x29 or b0 == 0x2B:  # sub
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                regs16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
                if mod == 3:
                    if b0 == 0x29:
                        set_r16(regs16[rmv], c.sub(c.reg[regs16[rmv]], c.reg[regs16[regf]]))
                    else:
                        set_r16(regs16[regf], c.sub(c.reg[regs16[regf]], c.reg[regs16[rmv]]))
                else:
                    s = ea_seg()
                    off = ea if not isinstance(ea, tuple) else \
                        ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] if ea[0][1] else 0)) + ea[1]) & 0xFFFF
                    if b0 == 0x29:
                        c.w16(s, off, c.sub(c.r16(s, off), c.reg[regs16[regf]]))
                    else:
                        set_r16(regs16[regf], c.sub(c.r16(s, off), c.reg[regs16[rmv]]))
            elif b0 == 0x05:  # add ax, imm16
                set_r16("ax", c.add(c.reg["ax"], struct.unpack("<H", opb[1:3])[0]))
            elif b0 == 0x2D:
                set_r16("ax", c.sub(c.reg["ax"], struct.unpack("<H", opb[1:3])[0]))
            elif 0x40 <= b0 <= 0x47:
                r = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"][b0 - 0x40]
                set_r16(r, c.add(c.reg[r], 1))
            elif 0x48 <= b0 <= 0x4F:
                r = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"][b0 - 0x48]
                set_r16(r, c.sub(c.reg[r], 1))
            elif b0 == 0xF7 and (opb[1] & 0xF8) == 0xD0:  # not r/m16
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                if mod == 3:
                    r = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"][rmv]
                    set_r16(r, ~c.reg[r] & 0xFFFF)
            elif b0 == 0xD3:  # shl/shr r/m16, cl
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                if mod == 3:
                    r = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"][rmv]
                    v = c.reg[r]
                    cl = c.reg["cx"] & 0x1F
                    if regf == 5:  # shr
                        c.cf = bool(v & (1 << (cl - 1))) if cl else c.cf
                        v >>= cl
                    elif regf in (4, 6, 7):  # shl/sal
                        c.cf = bool(v & (1 << (16 - cl))) if cl else c.cf
                        v = (v << cl) & 0xFFFF
                    set_r16(r, v)
                    c.logic_flags(v)
            elif b0 == 0xC6:  # mov m8, imm8
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                if mod == 3:
                    raise RuntimeError("mov r8,imm8 не нужен?")
                s = ea_seg()
                off = ea if not isinstance(ea, tuple) else \
                    ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] if ea[0][1] else 0)) + ea[1]) & 0xFFFF
                c.w8(s, off, opb[2 + ex])
            elif b0 == 0xC7:  # mov m16, imm16
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                if mod == 3:
                    set_r16(["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"][rmv],
                            struct.unpack("<H", opb[2 + ex:4 + ex])[0])
                else:
                    s = ea_seg()
                    off = ea if not isinstance(ea, tuple) else \
                        ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] if ea[0][1] else 0)) + ea[1]) & 0xFFFF
                    c.w16(s, off, struct.unpack("<H", opb[2 + ex:4 + ex])[0])
            elif b0 == 0x83:  # grp1 r/m16, imm8 sg
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                imm = struct.unpack("<b", opb[2 + ex:3 + ex])[0]
                regs16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
                if mod == 3:
                    v = c.reg[regs16[rmv]]
                    if regf == 7:  # cmp
                        c.sub(v, imm)
                    elif regf == 5:  # sub
                        set_r16(regs16[rmv], c.sub(v, imm))
                    elif regf == 0:  # add
                        set_r16(regs16[rmv], c.add(v, imm))
                    else:
                        raise RuntimeError("83 /%d" % regf)
                else:
                    raise RuntimeError("83 с памятью")
            elif b0 == 0x81:  # grp1 r/m16, imm16
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                imm = struct.unpack("<H", opb[2 + ex:4 + ex])[0]
                regs16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
                if mod == 3:
                    v = c.reg[regs16[rmv]]
                    if regf == 7:
                        c.sub(v, imm)
                    elif regf == 5:
                        set_r16(regs16[rmv], c.sub(v, imm))
                    elif regf == 0:
                        set_r16(regs16[rmv], c.add(v, imm))
                    else:
                        raise RuntimeError("81 /%d" % regf)
                else:
                    s = ea_seg()
                    off = ea if not isinstance(ea, tuple) else \
                        ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] if ea[0][1] else 0)) + ea[1]) & 0xFFFF
                    v = c.r16(s, off)
                    if regf == 0:
                        c.w16(s, off, c.add(v, imm))
                    elif regf == 5:
                        c.w16(s, off, c.sub(v, imm))
                    else:
                        raise RuntimeError("81 mem /%d" % regf)
            elif b0 == 0x3C:  # cmp al, imm8
                c.sub(c.reg["ax"] & 0xFF, opb[1], w=8)
            elif b0 == 0x3D:
                c.sub(c.reg["ax"], struct.unpack("<H", opb[1:3])[0])
            elif b0 == 0xA8:  # test al, imm8
                c.logic_flags((c.reg["ax"] & 0xFF) & opb[1], w=8)
            elif b0 == 0xA9:
                c.logic_flags(c.reg["ax"] & struct.unpack("<H", opb[1:3])[0])
            elif b0 == 0x24:  # and al, imm8
                v = (c.reg["ax"] & 0xFF) & opb[1]
                set_r16("ax", (c.reg["ax"] & 0xFF00) | v)
                c.logic_flags(v, w=8)
            elif b0 == 0x25:
                v = c.reg["ax"] & struct.unpack("<H", opb[1:3])[0]
                set_r16("ax", v)
                c.logic_flags(v)
            elif b0 == 0x0C:  # or al, imm8
                v = (c.reg["ax"] & 0xFF) | opb[1]
                set_r16("ax", (c.reg["ax"] & 0xFF00) | v)
                c.logic_flags(v, w=8)
            elif b0 == 0x0D:
                v = c.reg["ax"] | struct.unpack("<H", opb[1:3])[0]
                set_r16("ax", v)
                c.logic_flags(v)
            elif b0 in (0x30, 0x31, 0x32, 0x33):  # xor r/m,r / r,r/m
                mod, regf, rmv, ea, ex = modrm(opb[1:])
                regs16 = ["ax", "cx", "dx", "bx", "sp", "bp", "si", "di"]
                if b0 in (0x31, 0x33):
                    if mod == 3:
                        v = c.reg[regs16[rmv]] ^ c.reg[regs16[regf]]
                        set_r16(regs16[rmv] if b0 == 0x31 else regs16[regf], v)
                        c.logic_flags(v)
                    else:
                        s = ea_seg()
                        off = ea if not isinstance(ea, tuple) else \
                            ((c.reg[ea[0][0]] + (c.reg[ea[0][1]] if ea[0][1] else 0)) + ea[1]) & 0xFFFF
                        v = c.r16(s, off) ^ c.reg[regs16[regf]]
                        c.w16(s, off, v)
                        c.logic_flags(v)
                else:
                    raise RuntimeError("xor8 @ cs:%04x ip=%04x" % (c.reg["cs"], c.ip))
            else:
                raise RuntimeError("unsupported op %s (%s %s) at cs:%04x ip=%04x" %
                                   (i.bytes.hex(), m, op, c.reg["cs"], c.ip))
        except RuntimeError:
            raise
        c.ip = nxt

    info["regs"] = dict(cpu.reg)
    return bytes(mem), info


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "OPALA.EXE"
    d = T.load(name)
    mem, info = run_stub(d, verbose=True)
    print("steps:", info["insns"], "ljmp:", tuple(hex(x) for x in info["ljmp"]) if info["ljmp"] else None)
    # образ: линейный 0..img
    out = name.replace(".EXE", "").replace(".exe", "") + "_unp.bin"
    open(r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data" + "\\" + out, "wb").write(
        mem[:0x5C000])
    print("saved", out)
