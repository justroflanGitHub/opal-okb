import urllib.request, ssl, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

base = 'https://conf-bpo.itmo.ru/el_books/basics_optics/lab_app_opal/'
pages = [
    ('lab_app_opal_2.html', 'Л1.2 Формирование'),
    ('lab_app_opal_3.html', 'Л1.3 Общие принципы'),
    ('lab_app_opal_4.html', 'Л1.4 Анализ габаритов и аберраций'),
    ('lab_app_opal_5.html', 'Л1.5 Анализ волнового фронта'),
    ('lab_app_opal_6.html', 'Л1.6 Анализ геометрического изображения'),
    ('lab_app_opal_7.html', 'Л1.7 Анализ дифракционного ЧКХ'),
    ('lab_app_opal_8.html', 'Л1.8 Анализ функции рассеяния точки'),
]

for page, title in pages:
    url = base + page
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        html = resp.read().decode('utf-8', errors='replace')
        
        # Find all images and their surrounding context
        # Pattern: text before <img> + src
        pattern = r'(?:<p[^>]*>|<div[^>]*>|<h[234][^>]*>)([^<]{0,200})?<img[^>]+src=["\x27]([^"\x27>]+)["\x27]'
        matches = re.findall(pattern, html, re.I)
        
        # Also find images with alt text
        alt_pattern = r'<img[^>]+src=["\x27]([^"\x27>]+)["\x27][^>]*alt=["\x27]([^"\x27>]*)["\x27]'
        alt_matches = re.findall(alt_pattern, html, re.I)
        
        print(f'\n{"="*70}')
        print(f'{title} ({page})')
        print(f'{"="*70}')
        
        for src in re.findall(r'image_app_opal_\d+\.gif', html):
            # Find surrounding text context
            idx = html.find(src)
            context_before = html[max(0,idx-500):idx]
            # Clean HTML tags
            context = re.sub(r'<[^>]+>', ' ', context_before)
            context = re.sub(r'\s+', ' ', context).strip()
            # Last 200 chars
            context = context[-200:] if len(context) > 200 else context
            print(f'  {src}: ...{context}')
        
    except Exception as e:
        print(f'{page}: ERROR {e}')
