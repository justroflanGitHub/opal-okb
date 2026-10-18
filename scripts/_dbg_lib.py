import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from catalog.library import build_library, expand_lbo, _scan_lbo_files, _scan_opj_files

lib = build_library()
for cat, nodes in lib.items():
    print(f'[{cat}] {len(nodes)} узлов' if isinstance(nodes, list) else f'[{cat}] -> {type(nodes)}')
    if isinstance(nodes, list):
        for n in nodes[:4]:
            print('   ', {k: (str(v)[:60] if not isinstance(v, (list, dict)) else type(v).__name__) for k, v in n.items()})

print('--- scans ---')
lbos = _scan_lbo_files()
print('LBO files:', lbos[:3] if lbos else lbos, '... всего', len(lbos) if lbos else 0)
opjs = _scan_opj_files()
print('OPJ files:', opjs[:3] if opjs else opjs, '... всего', len(opjs) if opjs else 0)

print('--- expand ---')
if lbos:
    try:
        kids = expand_lbo(lbos[0] if isinstance(lbos[0], str) else lbos[0].get('path'))
        print('expand_lbo ok:', len(kids))
        for k in kids[:5]:
            print('   ', {kk: (str(vv)[:40] if not isinstance(vv,(list,dict)) else type(vv).__name__) for kk, vv in k.items()})
    except Exception as e:
        import traceback; traceback.print_exc()
