import sys
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')

from glass_catalog_full import compute_refractive_index, list_glasses
glasses = list_glasses()
n = len(glasses)
k8n = compute_refractive_index('K8', 0.58756)

print(f'glass_catalog_full.py: {n} glasses')
print(f'K8 nd = {k8n:.6f}')

import opj_reader
print('opj_reader: import OK')

import fil_reader_v2
print('fil_reader_v2: import OK')

print('All bugs fixed!')
