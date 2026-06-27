"""Use os_converter.exe to convert OPJ → ZMX, then parse ZMX (text format)."""
import sys, os, subprocess, tempfile, struct

lib_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_ utils\converter'
exe = os.path.join(lib_dir, 'os_converter.exe')

# We need an OPJ file to convert. Extract Индустар-23у from LBO.
sys.path.insert(0, r'C:\Users\mikhail\.openclaw\workspace\opal_okb')
from lbo_reader import load_lbo_fast

lens = load_lbo_fast(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\LENS.LBO')
s = lens[3]  # Индустар-23у

# Write OPJ data to temp file
tmpdir = tempfile.mkdtemp()
opj_path = os.path.join(tmpdir, 'ind23u.OPJ')
with open(opj_path, 'wb') as f:
    f.write(s['opj_data'])

print(f"Wrote OPJ: {opj_path} ({len(s['opj_data'])} bytes)")

# Also extract Окуляр f=10
ocul = load_lbo_fast(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\OCULAR.LBO')
s2 = ocul[1]
opj_path2 = os.path.join(tmpdir, 'ocular10.OPJ')
with open(opj_path2, 'wb') as f:
    f.write(s2['opj_data'])

# And BINOC-8X from USBINOCL
usbin = load_lbo_fast(r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\Lib\USBINOCL.LBO')
s3 = usbin[0]
opj_path3 = os.path.join(tmpdir, 'binoc8x.OPJ')
with open(opj_path3, 'wb') as f:
    f.write(s3['opj_data'])

print(f"Wrote {opj_path2} and {opj_path3}")

# Try to run os_converter.exe with command line args
# It's a Qt GUI app, but might accept args: input.opj output.zmx
zmx_path = os.path.join(tmpdir, 'ind23u.zmx')

# Try various command line patterns
for args_pattern in [
    [opj_path, zmx_path],
    ['-i', opj_path, '-o', zmx_path],
    [f'/i={opj_path}', f'/o={zmx_path}'],
]:
    try:
        result = subprocess.run(
            [exe] + args_pattern,
            capture_output=True, timeout=5,
            cwd=lib_dir
        )
        print(f"Args {args_pattern}: rc={result.returncode}")
        if result.stdout:
            print(f"  stdout: {result.stdout[:200]}")
        if result.stderr:
            print(f"  stderr: {result.stderr[:200]}")
        if os.path.exists(zmx_path):
            print(f"  OUTPUT CREATED!")
            break
    except subprocess.TimeoutExpired:
        print(f"Args {args_pattern}: TIMEOUT (GUI app?)")
    except Exception as e:
        print(f"Args {args_pattern}: ERROR {e}")

print(f"\nTemp dir: {tmpdir}")
