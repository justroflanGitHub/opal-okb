# -*- coding: utf-8 -*-
"""Скретч-дизассемблер FUN_1000_0746 (TASK_REV0746, §17).

Модель та же, что в волнах 3-5 (REVERSE_TRACE §0/§0.1/§17):
  - MZ-заголовок 0x20 параграфов, модуль грузится с линейного 0x10000;
    file_off = lin - 0x10000 + 0x200.
  - INT 34..3B (CD 34..3B) — эмуляция x87: опкод ESC синтезируется из
    байта прерывания (старшая часть D8..DF соответствует обёртке), фактический
    модификатор берётся из следующей инструкции (как в §0 — «обёртка»).
  - INT 3C/3D — x87wt / x87stat (маркеры записи/статуса).
  - 9A/EA — far call/jmp: цель = (seg<<4)+off по релокациям LOAD_SEG 0x1000.

Использование: py analysis/_tools/_dbg_0746.py <lin_start> <lin_end>
"""
import sys

import capstone

EXE = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\OPALA.EXE"
LOAD = 0x10000
HDR = 0x200

X87 = {0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B}


def off(lin):
    return lin - LOAD + HDR


def load():
    with open(EXE, "rb") as f:
        return f.read()


def disas(data, lin_start, lin_end, resolve=True):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)
    md.detail = False
    o0, o1 = off(lin_start), off(lin_end)
    code = data[o0:o1]
    out = []
    pos = 0
    while pos < len(code):
        lin = lin_start + pos
        b = code[pos]
        # INT-обёртки x87 (§0): CD 34..3B → синтез мнемоники-маркера
        if b == 0xCD and pos + 1 < len(code) and code[pos + 1] in X87:
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
            # разрешение far-call/jmp
            if resolve and i.mnemonic in ("call", "jmp") and i.op_str.startswith("0x"):
                try:
                    ops = i.op_str.split(" ")
                    val = int(ops[-1], 16)
                except ValueError:
                    val = None
            out.append((lin, raw, txt))
            pos += i.size
            break
        else:
            out.append((lin, code[pos:pos + 1], f"db {code[pos]:02x}"))
            pos += 1
    return out


def main():
    a = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x10746
    b = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x112D0
    data = load()
    for lin, raw, txt in disas(data, a, b):
        print(f"{lin:06x}  {raw.hex():<16} {txt}")


if __name__ == "__main__":
    main()
