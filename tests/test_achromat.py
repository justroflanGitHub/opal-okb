import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from achromat import design_achromat, achromat_report
s = design_achromat(100)
print(achromat_report(s))
