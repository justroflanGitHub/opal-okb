# -*- coding: utf-8 -*-
"""EXEPACK-распаковка OPALO.EXE / OPALOW.EXE (обёртка над exepack.run_stub).

Дополнительно к exepack.py: находит трейлер 'RB' в файле (кандидаты сверяются
с LJMP-целью стаба) и пишет образ размером до конца STACK (SS0*16+0x7E0).
"""
import struct
import sys

sys.path.insert(0, r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\_tools")
import tsr_lib as T
import exepack as E


def trailer_at(data, inf):
    """16-байтовый трейлер перед entry стаба: IP0,CS0,pad,stub_para,SP0,SS0,mend,'RB'."""
    t = inf["hdr_para"] * 16 + (inf["cs"] << 4) + inf["ip"] - 16
    ip0, cs0, pad, stub, sp0, ss0, mend = struct.unpack("<7H", data[t:t + 14])
    assert data[t + 14:t + 16] == b"RB", data[t + 14:t + 16]
    return dict(off=t, ip0=ip0, cs0=cs0, stub_para=stub, sp0=sp0, ss0=ss0,
                mem_end_para=mend)


def unpack(name, size=None):
    data = T.load(name)
    mem, info = E.run_stub(data, verbose=False)
    ljmp = info["ljmp"]
    t = trailer_at(data, T.mz_info(data))
    assert (t["cs0"], t["ip0"]) == ljmp, (t, ljmp)
    print("%s: steps=%d ljmp=%04x:%04x img_bytes=%#x" %
          (name, info["insns"], ljmp[0], ljmp[1], info["img_bytes"]))
    print("  trailer @ %#x: %s" % (t["off"],
          " ".join("%s=%#x" % kv for kv in t.items())))
    if size is None:
        # (SS<<4 + SP0) с округлением вверх до параграфа: код+данные+стек стаба
        size = ((t["ss0"] << 4) + t["sp0"] + 0xF) & ~0xF
    out = name.replace(".EXE", "").replace(".exe", "") + "_unp.bin"
    p = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data\\" + out
    open(p, "wb").write(mem[:size])
    print("  saved %s (%#x bytes)" % (p, size))
    return mem, info, t


if __name__ == "__main__":
    for nm in (sys.argv[1:] or ["OPALO.EXE", "OPALOW.EXE"]):
        unpack(nm)
