# -*- coding: utf-8 -*-
"""Вырезать диапазон адресов из dis_main.txt: py _dis_range.py <hex1> <hex2>"""
import sys

path = os_path = None
import os
path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', '..', 'dis_main.txt')
a1, a2 = int(sys.argv[1], 16), int(sys.argv[2], 16)
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    for line in f:
        col = line.find(':')
        if col < 0:
            continue
        try:
            a = int(line[:col], 16)
        except ValueError:
            continue
        if a1 <= a <= a2:
            sys.stdout.write(line)
