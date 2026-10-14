# -*- coding: utf-8 -*-
"""Скретч-дизассемблер RTL FORTRAN 5.0 из OPALA_unp.bin (TASK_FMT, волна 7/A2).

Отличия от _dbg_0746.py (волны 3-5): читаем РАСПАКОВАННЫЙ образ
``analysis/reverse_data/OPALA_unp.bin`` — там линейный адрес = смещение
в файле (пре-релокационные сегменты, REVERSE_TSR §1: стаб исполнен при
load-сегмент 0, релокации добавили 0). Сегмент:офсет → лин =
``(seg << 4) + off``.

Модель INT-обёрток x87 та же (REVERSE_TRACE §0/§0.1):
  - CD 34..3B — эмуляция x87 (маркер «x87em NN»);
  - CD 3C/3D — x87wt / x87stat;
  - 9A/EA — far call/jmp, цель = (seg<<4)+off (пре-релок образ).

Использование: py analysis/_tools/_dbg_fmt.py <lin_start> <lin_end> [max]
"""
import sys

import capstone

BIN = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\OPALA_unp.bin"

X87 = {0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B}


def seg_off(lin):
    """Линейный адрес → «сегмент:офсет» (канонический для RTL 0x2E73)."""
    return f"{lin >> 4:04x}:{lin & 0xF:04x}"


def load():
    with open(BIN, "rb") as f:
        return f.read()


def disas(data, lin_start, lin_end):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)
    md.detail = False
    code = data[lin_start:lin_end]
    out = []
    pos = 0
    while pos < len(code):
        lin = lin_start + pos
        b = code[pos]
        if b == 0xCD and pos + 1 < len(code) and code[pos + 1] in X87:
            # обёртка: INT 34..3B ЗАМЕЩАЕТ первый байт ESC D8..DF,
            # modrm/смещение следуют сразу (REVERSE_TRACE §0.1)
            esc = bytes([0xD8 + code[pos + 1] - 0x34]) + code[pos + 2:pos + 8]
            txt = None
            for i in md.disasm(esc, 0):
                txt = f"{i.mnemonic} {i.op_str}".strip()
                raw = code[pos:pos + 1 + i.size]
                out.append((lin, raw, txt))
                pos += 1 + i.size
                break
            if txt is None:
                out.append((lin, code[pos:pos + 2], f"x87em {code[pos+1]:02x}h"))
                pos += 2
            continue
        if b == 0xCD and pos + 1 < len(code) and code[pos + 1] in (0x3C, 0x3D):
            tag = "x87wt" if code[pos + 1] == 0x3C else "x87stat"
            out.append((lin, code[pos:pos + 2], tag))
            pos += 2
            continue
        for i in md.disasm(code[pos:], lin):
            txt = f"{i.mnemonic} {i.op_str}".strip()
            raw = code[pos:pos + i.size]
            # far call/jmp: 9A/EA off16,seg16 → цель лин = seg*16+off
            if i.mnemonic in ("call", "jmp") and raw[0] in (0x9A, 0xEA) \
                    and len(raw) == 5:
                off, seg = raw[1] | raw[2] << 8, raw[3] | raw[4] << 8
                txt += f"   ; {seg_off((seg << 4) + off)} (lin {(seg << 4) + off:06x})"
            out.append((lin, raw, txt))
            pos += i.size
            break
        else:
            out.append((lin, code[pos:pos + 1], f"db {code[pos]:02x}"))
            pos += 1
    return out


def main():
    a = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x30772
    b = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x30800
    data = load()
    for lin, raw, txt in disas(data, a, b):
        print(f"{lin:06x} {seg_off(lin)}  {raw.hex():<16} {txt}")


if __name__ == "__main__":
    main()
