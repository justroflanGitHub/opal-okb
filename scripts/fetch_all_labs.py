"""Fetch all OPAL lab pages from ITMO"""
import urllib.request, ssl, sys, io, os, re, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = 'https://conf-bpo.itmo.ru/el_books/basics_optics/'
out_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\docs\itmo_labs'
os.makedirs(out_dir, exist_ok=True)

pages = [
    'lab_app_opal/lab_app_opal.html',
    'lab_app_opal/lab_app_opal_1.html',
    'lab_app_opal/lab_app_opal_2.html',
    'lab_app_opal/lab_app_opal_3.html',
    'lab_app_opal/lab_app_opal_4.html',
    'lab_app_opal/lab_app_opal_5.html',
    'lab_app_opal/lab_app_opal_6.html',
    'lab_app_opal/lab_app_opal_7.html',
    'lab_app_opal/lab_app_opal_8.html',
]

all_text = []

for page in pages:
    url = base + page
    fname = page.split('/')[-1]
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        data = resp.read()
        
        for enc in ['utf-8', 'cp1251', 'latin-1']:
            try:
                text = data.decode(enc)
                break
            except:
                continue
        else:
            text = data.decode('latin-1')
        
        # Strip HTML tags
        clean = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
        clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        out_path = os.path.join(out_dir, fname.replace('.html', '.txt'))
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(clean)
        
        all_text.append(f"===== {fname} =====\n{clean[:2000]}")
        print(f"OK: {fname} ({len(clean)} chars)")
    except Exception as e:
        print(f"FAIL: {fname} - {e}")
    
    time.sleep(0.5)

# Save combined
with open(os.path.join(out_dir, '_all_labs.txt'), 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(all_text))
print(f"\nTotal pages saved")
