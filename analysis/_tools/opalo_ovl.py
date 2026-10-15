# -*- coding: utf-8 -*-
"""TASK_OPALO §2b: извлечение оверлейных юнитов OPALO/OPALOW из хвоста EXE.

Модель (подтверждена дизассемблом диспетчера OPALO 0x1E197/ридера 0x1DF84,
аналог у OPALOW — 0x2389F, теми же байтами):
- хвост файла = цепочка мини-MZ (ovno 1..4), шаг = pages*512;
- юнит N грузится ЦЕЛИКОМ на OV_BASE:0000 (хардкод `mov di,imm` в ридере):
  OPALO → 0x442D (пул рута 0x442D0..0x51740), OPALOW → 0x48B7 (0x48B70..0x5CC1E);
- релокации: записи (off,seg) хранят УЖЕ ФИНАЛЬНЫЙ сегмент (OV_BASE...),
  рантайм-прибавка = 0 → для реальной базы патчи не нужны;
- селектор → byte=№ юнита, word=сегмент входа внутри загруженного юнита.

Выход: <name>_ovl<N>.bin (юнит как в рантайме на OV_BASE:0) и merged
<name>_full.bin для Ghidra: root + юнит1 на реальной базе, юниты 2-4
перелинкованы на фиктивные базы ЗА пределами рута (сегменты юнита +delta).
"""
import struct
import sys

sys.path.insert(0, r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\_tools")
import tsr_lib as T

RD = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\analysis\reverse_data"
# база загрузки (runtime) и фиктивные базы юнитов 2..4 для мержа
CFG = {
    "OPALO":  dict(ov_base=0x442D, fake={2: 0x6800, 3: 0x9000, 4: 0x9800}),
    "OPALOW": dict(ov_base=0x48B7, fake={2: 0x7200, 3: 0x8000, 4: 0x8600}),
}


def parse_chain(exe, img_bytes):
    units = []
    off = (img_bytes + 0x1FF) & ~0x1FF
    while True:
        while off < len(exe) and exe[off:off + 2] != b"MZ":
            off += 0x200
        if off >= len(exe):
            break
        (last, pages, nrel, hdrp, minal, maxa, ss_, sp_,
         csum, ip_, cs_, roff, ovno) = struct.unpack("<13H", exe[off + 2:off + 28])
        size = ((pages - 1) << 9) + (last or 512)
        units.append(dict(mz=off, ovno=ovno, size=size, nrel=nrel, hdr=hdrp,
                          img_para=pages * 32 - hdrp, reloc_off=roff))
        off += pages * 512
    return units


def rebase(unit_img, unit, exe, delta, ov_base):
    """Сдвиг юнита на delta параграфов: по релоцируемым словам — +delta.

    Релок-таблица указывает слова-сегменты; в файле они уже = ov_base...
    (финальные). Для переноса юнита на фиктивную базу прибавляем delta
    только к словам из таблицы (адреса слов — относительно базы юнита,
    записи (off, seg) с финальным seg: лин. адрес = (seg-ov_base)*16+off).
    """
    p = unit["mz"] + (unit["reloc_off"] or 0x20)
    buf = bytearray(unit_img)
    n = 0
    for i in range(unit["nrel"]):
        off, seg = struct.unpack("<HH", exe[p + 4 * i:p + 4 * i + 4])
        lin = ((seg - ov_base) << 4) + off
        if 0 <= lin < len(buf) - 1:
            old = buf[lin] | (buf[lin + 1] << 8)
            buf[lin] = (old + delta) & 0xFF
            buf[lin + 1] = ((old + delta) >> 8) & 0xFF
            n += 1
    return bytes(buf), n


def build(name, merged_bases=None):
    cfg = CFG[name]
    ov_base = cfg["ov_base"]
    exe = T.load(name + ".EXE")
    inf = T.mz_info(exe)
    img_bytes = (inf["pages"] - 1) * 512 + (inf["bytes_last"] or 512)
    root = open(RD + "\\%s_unp.bin" % name, "rb").read()
    units = parse_chain(exe, img_bytes)
    print("%s: юнитов %d, ov_base=%04x" % (name, len(units), ov_base))
    imgs = {}
    for u in units:
        start = u["mz"] + u["hdr"] * 16
        size = min(u["img_para"] * 16, len(exe) - start, u["size"] - u["hdr"] * 16)
        imgs[u["ovno"]] = exe[start:start + size]
        open(RD + "\\%s_ovl%d.bin" % (name, u["ovno"]), "wb").write(imgs[u["ovno"]])
        print("  юнит %d: MZ@%#x size=%#x hdr=%#x nrel=%d img=%#x" %
              (u["ovno"], u["mz"], u["size"], u["hdr"] * 16, u["nrel"], size))
    if merged_bases is None:
        merged_bases = dict(cfg["fake"])
        merged_bases[1] = ov_base
    total = max(len(root), (max(merged_bases.values()) << 4))
    for k, b in merged_bases.items():
        total = max(total, (b << 4) + len(imgs[k]))
    full = bytearray(total)
    full[:len(root)] = root
    for k, b in sorted(merged_bases.items()):
        u = [x for x in units if x["ovno"] == k][0]
        img, n = rebase(imgs[k], u, exe, b - ov_base, ov_base)
        # контроль: юнит не должен затирать ненулевые байты рута
        clob = sum(1 for i in range(len(img)) if b * 16 + i < len(root)
                   and root[b * 16 + i] != 0 and img[i] != 0)
        if clob:
            print("  !! юнит %d затирает %d ненулевых байт рута" % (k, clob))
        full[(b << 4):(b << 4) + len(img)] = img
        print("  юнит %d -> база %04x (перелинковано %d слов)" % (k, b, n))
    open(RD + "\\%s_full.bin" % name, "wb").write(bytes(full))
    print("  merged -> %s_full.bin (%#x байт)" % (name, total))
    return units, imgs


if __name__ == "__main__":
    for nm in (sys.argv[1:] or ["OPALO", "OPALOW"]):
        build(nm)
