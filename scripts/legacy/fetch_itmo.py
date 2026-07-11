import urllib.request, ssl, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = 'https://conf-bpo.itmo.ru/el_books/basics_optics/lab_app_opal/lab_app_opal.html'

try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, context=ctx, timeout=15)
    data = resp.read()
    print(f'Status: {resp.status}')
    print(f'Size: {len(data)} bytes')
    
    for enc in ['utf-8', 'cp1251', 'cp866', 'latin-1']:
        try:
            text = data.decode(enc)
            print(f'Decoded with: {enc} ({len(text)} chars)')
            break
        except:
            continue
    else:
        text = data.decode('latin-1')
    
    # Save full text
    out = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\docs\itmo_lab.html.txt'
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'Saved to {out}')
    
    # Print first 3000 chars
    print(text[:3000])
except Exception as e:
    print(f'Error: {type(e).__name__}: {e}')
