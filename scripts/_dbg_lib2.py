import sys
sys.path.insert(0, '.')
sys.stdout.reconfigure(encoding='utf-8')
from catalog.library import expand_lbo, build_library, create_system_from_entry

lib = build_library()
lbo_nodes = lib['LBO библиотеки']
opj_nodes = lib['OPAL системы (.OPJ)']

print('--- expand LBO (как GUI: entry.lbo_path) ---')
n = lbo_nodes[0]
print('узел:', n['name'])
try:
    kids = expand_lbo(n['lbo_path'])
    print('ok:', len(kids), 'детей; первый:', {k: str(v)[:40] for k, v in kids[0].items()})
except Exception:
    import traceback; traceback.print_exc()

print('--- create OPAL-система (как GUI: entry) ---')
e = opj_nodes[1]  # 121
try:
    s = create_system_from_entry(e)
    print('ok:', s.name, 'поверхностей:', len(s.surfaces))
except Exception:
    import traceback; traceback.print_exc()
