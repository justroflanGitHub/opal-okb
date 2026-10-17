# -*- coding: utf-8 -*-
"""G2: LPTCAP.COM v11 — TSR INT17 «принтер всегда готов», вывод в файл.

Особенности ЭТОЙ DOSBox (0.74-3 билд стенда, доказано тестами TESTQ/R/V):
  * int21 25h/35h для вектора INT17 НЕ работают -> пишем/читаем IVT напрямую;
  * int21 3Ch/5Bh/3Dh молча убивают программу -> файл создаёт шелл-редирект;
  * int21 50h (set PSP) убивает при вызове из обработчика -> НЕ используем;
  * int21 62h (get PSP), 40h (write), 02h (putc) — работают.

Схема: LPTCAP.COM > C:\\LPTSPOOL.PRN  (файл создаёт шелл; хендл унаследован
в слоте JFT[1]). Перед int27h PSP:0x34 указывает на ПУСТУЮ JFT — терминиро-
вание ничего не закроет; копия настоящей JFT хранится в теле TSR.

Печать (INT17 AH=00): берём PSP вызывающего (62h), находим ЕГО JFT, подменяем
его JFT[1] на наш файловый хендл (из копии), пишем байт (40h BX=1), возвра-
щаем слот. AH=01/02 -> статус 90h «готов». Прочее -> старый обработчик.
"""

import struct

code = bytearray()
labels = {}
fixups = []


def emit(*bs):
    code.extend(bs)


def label(n):
    labels[n] = len(code)


def j_short(op, t):
    fixups.append((len(code) + 1, t, 'rel8'))
    emit(op, 0)


def w16(t):
    fixups.append((len(code), t, 'w16'))
    emit(0, 0)


def putc(ch):
    """Консольный зонд: mov dl,ch; push ax; ah=02; int21; pop ax."""
    emit(0xB2, ord(ch))                        # mov dl,ch
    emit(0x50, 0xB4, 0x02, 0xCD, 0x21, 0x58)   # push ax; ah=02; int21; pop ax


emit(0xE9)
fixups.append((len(code), 'init', 'rel16'))
emit(0, 0)

label('old17'); emit(0, 0, 0, 0)
label('mypsp'); emit(0, 0)
label('jftofs'); emit(0, 0)
label('jftseg'); emit(0, 0)
label('buff'); emit(0)
label('savedj1'); emit(0)
label('jftreal')
for _ in range(20):
    emit(0)
label('jftempty')
for _ in range(20):
    emit(0xFF)


def set_jft(tbl):
    """ES=[mypsp]; ES:0x34 ← cs:tbl (tbl — имя метки)."""
    emit(0x8E, 0x06); w16('mypsp')           # mov es,[mypsp]
    emit(0xB8); w16(tbl)                     # mov ax,offset tbl
    emit(0x26, 0xA3, 0x34, 0x00)             # mov es:[0034],ax
    emit(0x8C, 0xC8)                         # mov ax,cs
    emit(0x26, 0xA3, 0x36, 0x00)             # mov es:[0036],ax


# ---------------- обработчик INT17 ----------------
label('int17')
emit(0x80, 0xFC, 0x00)                       # cmp ah,0
emit(0x0F, 0x85)                             # jne near chk
fixups.append((len(code), 'chk', 'rel16n'))
emit(0, 0)
emit(0x50, 0x53, 0x51, 0x52)                 # push ax,bx,cx,dx
emit(0x56, 0x57, 0x55)                       # push si,di,bp
emit(0x06, 0x1E)                             # push es,ds
emit(0x0E, 0x1F)                             # push cs; pop ds
emit(0xA2); w16('buff')                      # mov [buff],al
emit(0xB4, 0x62); emit(0xCD, 0x21)           # mov ah,62h; int21 -> bx=PSP звонящего
emit(0x8E, 0xC3)                             # mov es,bx (PSP звонящего)
emit(0x26, 0x8B, 0x3E, 0x34, 0x00)           # mov di,es:[0034] (JFT ofs)
emit(0x26, 0xA1, 0x36, 0x00)                 # mov ax,es:[0036] (JFT seg)
emit(0x8E, 0xC0)                             # mov es,ax -> es:di = JFT звонящего
emit(0x26, 0x8A, 0x45, 0x01)                 # mov al,es:[di+1] (его JFT[1])
emit(0xA2); w16('savedj1')                   # mov [savedj1],al
emit(0xA0); w16('jftreal1')                  # mov al,[jftreal1] (наш хендл)
emit(0x26, 0x88, 0x45, 0x01)                 # mov es:[di+1],al (JFT[1] = спул)
# сам вывод: 02h пишет через слот 1 -> сейчас это файл спула
emit(0x8A, 0x16); w16('buff')                # mov dl,[buff]
emit(0xB4, 0x02); emit(0xCD, 0x21)           # mov ah,02; int21 (байт -> спул)
# ВНИМАНИЕ: flush не делаем (68h/40h убивают) — буфер stdio сбрасывается
# сам при заполнении и при выходе из DOSBox (CRT atexit). После печати:
# выйти из OPAL и набрать exit.
# восстановить JFT[1] звонящего (es:di сохранены)
emit(0xA0); w16('savedj1')                   # mov al,[savedj1]
emit(0x26, 0x88, 0x45, 0x01)                 # mov es:[di+1],al
emit(0x1F, 0x07)                             # pop ds,es
emit(0x5D, 0x5F, 0x5E)                       # pop bp,di,si
emit(0x5A, 0x59, 0x5B, 0x58)                 # pop dx,cx,bx,ax
emit(0xB4, 0x90)                             # mov ah,90h
emit(0xCF)                                   # iret
label('chk')
emit(0x80, 0xFC, 0x01)                       # cmp ah,1
j_short(0x74, 'fake')                        # je fake
emit(0x80, 0xFC, 0x02)                       # cmp ah,2
j_short(0x74, 'fake')                        # je fake
emit(0x2E, 0xFF, 0x2E); w16('old17')         # jmp far cs:[old17]
label('fake')
emit(0xB4, 0x90)                             # mov ah,90h
emit(0xCF)                                   # iret

# ---------------- init ----------------
label('init')
emit(0x0E, 0x1F)                             # push cs; pop ds
emit(0xB4, 0x62); emit(0xCD, 0x21)           # mov ah,62h; int21 -> bx=PSP
emit(0x89, 0x1E); w16('mypsp')               # mov [mypsp],bx
emit(0x8E, 0xC3)                             # mov es,bx
emit(0x26, 0x8B, 0x1E, 0x34, 0x00)           # mov bx,es:[0034]
emit(0x89, 0x1E); w16('jftofs')              # mov [jftofs],bx
emit(0x26, 0x8B, 0x0E, 0x36, 0x00)           # mov cx,es:[0036]
emit(0x89, 0x0E); w16('jftseg')              # mov [jftseg],cx
# копия JFT (20 байт) -> jftreal: ds=src,si=ofs; es=cs,di=jftreal
emit(0x89, 0xDE)                             # mov si,bx (srcofs)
emit(0x8E, 0xD9)                             # mov ds,cx (srcseg)
emit(0x0E, 0x1F)                             # push cs; pop es
emit(0xBF); w16('jftreal')                   # mov di,jftreal
emit(0xB9, 0x14, 0x00)                       # mov cx,20
emit(0xFC)                                   # cld
emit(0xF3, 0xA4)                             # rep movsb
emit(0x0E, 0x1F)                             # push cs; pop ds (ds=cs)
# PSP:0x34 ← cs:jftempty (при int27h терминирование ничего не закроет)
set_jft('jftempty')
# hook INT17 — ПРЯМАЯ запись в IVT (25h/35h в этой DOSBox не работают!)
emit(0x31, 0xC0); emit(0x8E, 0xC0)           # xor ax,ax; mov es,ax
emit(0x26, 0xA1, 0x5C, 0x00)                 # mov ax,es:[005C] (старый ofs)
emit(0xA3); w16('old17')                     # mov [old17],ax
emit(0x26, 0xA1, 0x5E, 0x00)                 # mov ax,es:[005E] (старый seg)
emit(0xA3); w16('old17+2')                   # mov [old17+2],ax
emit(0x31, 0xC0); emit(0x8E, 0xC0)           # xor ax,ax; mov es,ax
emit(0xB8); w16('int17')                     # mov ax,int17
emit(0x26, 0xA3, 0x5C, 0x00)                 # mov es:[005C],ax
emit(0x8C, 0xC8)                             # mov ax,cs
emit(0x26, 0xA3, 0x5E, 0x00)                 # mov es:[005E],ax
emit(0xBA); w16('initend')                   # mov dx,initend
emit(0xCD, 0x27)                             # int 27h
label('initend')

labels['old17+2'] = labels['old17'] + 2
labels['jftreal1'] = labels['jftreal'] + 1
for pos, name, kind in fixups:
    if kind == 'rel8':
        rel = labels[name] - (pos + 1)
        assert -128 <= rel <= 127, (name, rel)
        code[pos] = rel & 0xFF
    elif kind == 'rel16':                    # E8/E9 rel16: rel от конца (pos+2)
        code[pos:pos+2] = struct.pack('<h', labels[name] - (pos + 2))
    elif kind == 'rel16n':                   # 0F 8x rel16: rel от конца (pos+2)
        code[pos:pos+2] = struct.pack('<h', labels[name] - (pos + 2))
    elif kind == 'w16':                      # COM: смещение = 0x100 + позиция
        code[pos:pos+2] = struct.pack('<H', 0x100 + labels[name])

out = bytes(code)
open(r'C:\GOLDEN_DOS\LPTCAP.COM', 'wb').write(out)
print('LPTCAP.COM', len(out), 'bytes')
