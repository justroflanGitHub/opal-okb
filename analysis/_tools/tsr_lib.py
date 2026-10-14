# -*- coding: utf-8 -*-
"""TSR-реверс (§18): общие утилиты — чтение EXE, MZ-заголовок, строки, поиск."""
import re, struct, sys

EXTRACT = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb"

def load(name):
    return open(EXTRACT + "\\" + name, "rb").read()

def mz_info(data):
    if data[:2] != b"MZ":
        return None
    (cblp, cp, crlc, cparhdr, minalloc, maxalloc, ss, sp, csum, ip, cs,
     lfarlc) = struct.unpack("<12H", data[2:26])
    return dict(pages=cp, bytes_last=cblp, nreloc=crlc, hdr_para=cparhdr,
                minalloc=minalloc, maxalloc=maxalloc, ss=ss, sp=sp,
                ip=ip, cs=cs, reloc_off=lfarlc)

def relocations(data):
    inf = mz_info(data)
    if not inf or inf["nreloc"] == 0:
        return []
    off = inf["reloc_off"]
    out = []
    for i in range(inf["nreloc"]):
        o, s = struct.unpack("<HH", data[off + 4*i: off + 4*i + 4])
        out.append((s, o))
    return out

def strings(data, minlen=5, enc="cp866"):
    """ASCII + CP866-строки; возвращает [(off, tag, text)]"""
    out = []
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, data):
        out.append((m.start(), "a", m.group().decode("ascii", "replace")))
    for m in re.finditer(rb"(?:[\x80-\xAF\xE0-\xFF][\x20-\x7e\x80-\xAF\xE0-\xFF]{%d,})" % minlen, data):
        try:
            out.append((m.start(), "r", m.group().decode("cp866"))
            )
        except Exception:
            pass
    return out

def hexdump(data, base=0, start=0, length=256, width=16):
    lines = []
    for i in range(start, min(start + length, len(data)), width):
        chunk = data[i:i+width]
        hx = " ".join("%02x" % b for b in chunk)
        asc = "".join(chr(b) if 0x20 <= b < 0x7f else "." for b in chunk)
        lines.append("%06x  %-*s |%s|" % (base + i, width * 3 - 1, hx, asc))
    return "\n".join(lines)
