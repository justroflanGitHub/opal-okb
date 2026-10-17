# -*- coding: utf-8 -*-
"""TASK_OPALDIS: скретч-дизассемблер OPALA_unp.bin (база 0, file_off = lin).

В отличие от _dbg_0746.py (MZ-зона OPALA.EXE, LOAD 0x10000), здесь образ уже
распакован (REVERSE_TSR §1 / REVERSE_UNP §1): все сегменты на линк-таймовых
абсолютах, linear == file offset. x87-обёртки INT 34..3D декодирует x87dis.

Использование: py analysis/_tools/_dis_opaldis.py <lin_start> <lin_end> [...]
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from x87dis import disas  # noqa: E402

BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "reverse_data", "OPALA_unp.bin")

# функции CODE_MAIN (по _funcs.txt проекта OPALA_UNP), для подписей
FUNCS = {}


def load():
    with open(BIN, "rb") as f:
        return f.read()


def run(lin1, lin2):
    data = load()
    code = data[lin1:lin2]
    for a, t, ln in disas(bytes(code), lin1):
        raw = " ".join("%02x" % b for b in code[a - lin1:a - lin1 + ln])
        note = FUNCS.get(a, "")
        print("%06x: %-24s %s" % (a, raw, t if not note else t + "   ; ==>" + note))


if __name__ == "__main__":
    args = [int(x, 0) for x in sys.argv[1:]]
    for i in range(0, len(args), 2):
        run(args[i], args[i + 1])
