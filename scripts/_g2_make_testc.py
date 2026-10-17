# -*- coding: utf-8 -*-
"""TESTC.COM: печать 'a', int21/3C create C:\TESTFILE.XXX, печать K/F+AX hex, exit."""
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


def call(t):
    emit(0xE8)
    fixups.append((len(code), t, 'rel16'))
    emit(0, 0)


j_short(0xEB, 'init')

label('putc')
emit(0x88, 0xC2, 0x50, 0xB4, 0x02, 0xCD, 0x21, 0x58, 0xC3)

label('phex')
emit(0xB9, 0x04, 0x00)
label('ph1')
emit(0xC1, 0xC3, 0x04, 0x88, 0xD8, 0x24, 0x0F, 0x3C, 0x0A)
j_short(0x72, 'ph2')
emit(0x04, 0x07)
label('ph2')
emit(0x04, 0x30)
call('putc')
j_short(0xE2, 'ph1')
emit(0xC3)

label('oldax'); emit(0, 0)
label('fname')
for ch in b'C:\\TESTFILE.XXX\x00':
    emit(ch)

label('init')
emit(0xB0, 0x61)                    # 'a'
call('putc')
emit(0xB8, 0x3C, 0x00)              # mov ax,3C00h
emit(0x31, 0xC9)                    # xor cx,cx
emit(0xBA); w16('fname')            # mov dx,fname
emit(0xCD, 0x21)                    # int 21h
emit(0x89, 0x06); w16('oldax')      # mov [oldax],ax
emit(0xB0, 0x62)                    # 'b'
call('putc')
emit(0x8B, 0x1E); w16('oldax')      # mov bx,[oldax]
call('phex')
emit(0xCD, 0x20)                    # exit

labels['oldax'] = labels['oldax']
for pos, name, kind in fixups:
    if kind == 'rel8':
        rel = labels[name] - (pos + 1)
        assert -128 <= rel <= 127, (name, rel)
        code[pos] = rel & 0xFF
    elif kind == 'rel16':
        code[pos:pos+2] = struct.pack('<h', labels[name] - (pos + 2))
    else:
        code[pos:pos+2] = struct.pack('<H', 0x100 + labels[name])

open(r'C:\GOLDEN_DOS\TESTC.COM', 'wb').write(bytes(code))
print('TESTC.COM', len(code), 'bytes')
print(' '.join(f'{b:02X}' for b in code))
