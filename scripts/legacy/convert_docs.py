import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

doc_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\extracted\opal_okb\DOC'
out_dir = r'C:\Users\mikhail\.openclaw\workspace\opal_okb\docs'
os.makedirs(out_dir, exist_ok=True)

for f in os.listdir(doc_dir):
    if f.endswith('.DOC'):
        with open(os.path.join(doc_dir, f), 'rb') as fh:
            text = fh.read().decode('cp866')
        out_name = f.replace('.DOC', '.txt')
        with open(os.path.join(out_dir, out_name), 'w', encoding='utf-8') as oh:
            oh.write(text)
        print(f'{f} -> {out_name} ({len(text)} chars)')
