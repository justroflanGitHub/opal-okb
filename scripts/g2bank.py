# -*- coding: utf-8 -*-
"""G2BANK: батч-генерация эталонных .PRN (рецепт TASK_G2BANK).

Цикл на систему (рецепт откалиброван, см. analysis/REVERSE_G2BANK.md):
boot → F10 → ENTER(METAPRN) → F2 ENTER(Чтение) → BS×12 <ИМЯ> (2с) ENTER
→ F5(Меню работ) → RIGHT ENTER(Анализ) ENTER(Работа-RT; оракул: PROTOCOL 0 б)
→ '4' → '6' → ENTER(закрыть вид) → '6' → F4 F9 ENTER → RT__HHMM.PRN
→ bank/<ИМЯ>.PRN. F6 НЕ жать (toggle текст/график; RT.REG=TX).

Оракулы: title окна DOSBox, PROTOCOL.PRN (0 б = свежесть), контент .PRN.
Использование: py scripts/g2bank.py ИМЯ [ИМЯ...]   (каждое имя = полный ребут)
"""
import glob
import os
import shutil
import subprocess
import sys
import time

ROOT = r'C:\Users\mikhail\.openclaw\workspace\opal_okb'
PY = sys.executable
SEND = os.path.join(ROOT, 'scripts', 'dosbox_send.py')
SHOT = os.path.join(ROOT, 'scripts', '_g2_shot.py')
CAP = os.path.join(ROOT, 'capture')
BANK = os.path.join(ROOT, 'analysis', 'reverse_data', 'golden', 'bank')
MANIFEST = os.path.join(ROOT, 'analysis', 'REVERSE_G2BANK.md')
GD = r'C:\GOLDEN_DOS'
DOSBOX = r'C:\Program Files (x86)\DOSBox-0.74-3\DOSBox.exe'
CONF = os.path.join(os.environ['TEMP'], 'dosbox_golden.conf')


def log(msg):
    print(f'[{time.strftime("%H:%M:%S")}] {msg}', flush=True)


def send(*keys):
    subprocess.run([PY, SEND] + list(keys), check=False)


def ps(cmd):
    return subprocess.run(['powershell', '-NoProfile', '-Command', cmd],
                          capture_output=True, text=True).stdout.strip()


def title():
    return ps("(Get-Process DOSBox -ErrorAction SilentlyContinue | Select-Object -First 1).MainWindowTitle")


def n_dosbox():
    try:
        return int(ps("@(Get-Process DOSBox -ErrorAction SilentlyContinue).Count") or 0)
    except ValueError:
        return 0


def wait_title(sub, timeout, poll=0.9):
    t0 = time.time()
    while time.time() - t0 < timeout:
        t = title()
        if sub.lower() in t.lower():
            return t
        time.sleep(poll)
    return None


def shot(path):
    subprocess.run([PY, SHOT, path], check=False)


def diff_frac(a, b):
    from PIL import Image
    import numpy as np
    A = np.asarray(Image.open(a).convert('L'), dtype=np.int16)
    B = np.asarray(Image.open(b).convert('L'), dtype=np.int16)
    if A.shape != B.shape:
        return 1.0
    return float((np.abs(A - B) > 12).mean())


def wait_title_stable(timeout=90, need=3):
    """Ждём стабильный title с 'Program:'."""
    t0 = time.time()
    last, same = '', 0
    while time.time() - t0 < timeout:
        t = title()
        if 'Program:' in t and t == last:
            same += 1
            if same >= need:
                return t
        else:
            same = 0
        last = t
        time.sleep(1.0)
    return last if 'Program:' in last else None


def boot():
    for attempt in (1, 2):
        subprocess.run(['taskkill', '/IM', 'DOSBox.exe', '/F'], capture_output=True)
        time.sleep(1.5)
        subprocess.Popen(['powershell', '-NoProfile', '-Command',
                          f"Start-Process '{DOSBOX}' -ArgumentList '-conf','{CONF}'"])
        t0 = time.time()
        cand = ''
        while time.time() - t0 < 120:
            t = title()
            prog = t.split('Program:')[-1].strip().upper() if 'Program:' in t else ''
            if prog and prog != 'DOSBOX':      # «DOSBox 0.74-3» в любом title — сравниваем только модуль
                if t == cand:
                    time.sleep(2.0)
                    if title() == t:
                        return t
                else:
                    cand = t
            time.sleep(1.0)
        log(f'boot попытка {attempt}: только DOSBOX/пусто')
    return None


def prt_size():
    p = os.path.join(GD, 'PROTOCOL.PRN')
    return os.path.getsize(p) if os.path.exists(p) else -1


def rt_snapshot():
    return set(glob.glob(os.path.join(GD, 'RT__*.P*')))


def analyze_prn(path, name):
    raw = open(path, 'rb').read()
    txt = raw.decode('cp866', 'replace')
    lines = [ln.rstrip() for ln in txt.replace('\r\n', '\n').split('\n')]
    head1 = next((ln for ln in lines if ln.strip()), '')
    return {
        'size': len(raw),
        'head': head1[:70],
        'axial': 'Аберрации осевого пучка' in txt,
        'gabar': 'абарит' in txt,
        'seps': sum(1 for ln in lines if ln.count('─') > 10),
    }


def append_manifest(row, detail):
    with open(MANIFEST, 'a', encoding='utf-8') as f:
        f.write(row + '\n')
        f.write(f'- `{detail}`\n')


def run_one(name, sanity=False):
    t_start = time.time()
    res = {'name': name, 'rt': '', 'status': 'FAIL', 'note': ''}
    log(f'=== {name}: boot')
    bt = boot()
    if not bt:
        res.update(status='BOOTFAIL', note='нет окна после старта')
        append_manifest(f'| {name} | - | - | BOOTFAIL | окно не появилось |',
                        f'{name} BOOTFAIL')
        return res
    log(f'boot ok: {bt!r}')

    # 1) при загрузке авто-восстановлен OPALA: F10 → MENUOPAL, бар уже активен
    send('F10')
    t = wait_title('MENUOPAL', 12)
    time.sleep(1.5)
    send('ENTER')
    t_ed = wait_title('MENUOPAL', 4)   # должно уйти с MENUOPAL
    ed_title = title()
    log(f'редактор: {ed_title!r}')
    time.sleep(2.0)

    # 3) Чтение: F2 → ENTER → BS×12 → имя → ENTER (с задержкой ~2с)
    pre = os.path.join(CAP, 'gb_tmp_pre.bmp')
    post = os.path.join(CAP, 'gb_tmp_post.bmp')
    send('F2')
    time.sleep(1.0)
    send('ENTER')
    time.sleep(1.5)
    shot(pre)
    send(*(['BS'] * 12))
    send(*list(name.upper()))
    time.sleep(2.0)
    send('ENTER')
    time.sleep(2.5)
    shot(post)
    d = diff_frac(pre, post)
    log(f'после ENTER(имя): diff={d:.4f}')
    if d < 0.003:                       # ENTER не сработал — переключить раскладку и повторить
        log('диалог не отреагировал → INS + повтор ввода')
        send('INS')
        time.sleep(0.8)
        send(*(['BS'] * 12))
        send(*list(name.upper()))
        time.sleep(2.0)
        send('ENTER')
        time.sleep(2.5)
        shot(post)
        d = diff_frac(pre, post)
        log(f'повтор: diff={d:.4f}')
        if d < 0.003:
            res.update(status='LOADFAIL', note='диалог Чтения замерз')
            append_manifest(f'| {name} | - | - | LOADFAIL | диалог Чтения не реагирует |',
                            f'{name} LOADFAIL diff={d:.4f}')
            return res

    # 4) выход из редактора: F5 = Меню работ (бар, курсор на Формиров.)
    #    → RIGHT (Анализ) → ENTER (pulldown) → ENTER (п.1 Работа-RT)
    send('F5')
    t = wait_title('MENUOPAL', 12)
    time.sleep(1.5)
    send('RIGHT')
    time.sleep(0.7)
    send('ENTER')
    time.sleep(1.2)
    send('ENTER')
    t = wait_title('OPALA', 20)
    if not t:
        res.update(status='NOOPALA2', note='Анализ→Работа-RT не запустилась')
        append_manifest(f'| {name} | - | - | NOOPALA2 | Анализ не запустил RT |',
                        f'{name} NOOPALA2')
        return res
    time.sleep(2.5)
    # устаревший PROTOCOL.PRN от прошлой системы даёт ложную «несвежесть» — стираем
    _pr = os.path.join(GD, 'PROTOCOL.PRN')
    if os.path.exists(_pr):
        try:
            os.remove(_pr)
        except OSError:
            pass
    p0 = prt_size()
    log(f'RT свежая: PROTOCOL.PRN={p0} б')

    # 5) расчёт: '4' габариты → '6' осевой пучок → скрин → F4 F9 ENTER
    base = rt_snapshot()
    send('4')                     # RT.REG=TX: текст по умолчанию, F6 НЕ жать (toggle!)
    time.sleep(6.0)
    send('6')
    time.sleep(6.0)
    send('ENTER')                   # закрыть вид п.6 → секция уходит в протокол
    time.sleep(2.0)
    send('6')                       # снова открыть вид п.6 (F4/F9 работают из вида)
    time.sleep(6.0)
    shot(os.path.join(CAP, f'gb_{name}.bmp'))
    p_mid = prt_size()
    send('F4')
    time.sleep(1.3)
    send('F9')
    time.sleep(1.3)
    send('ENTER')
    time.sleep(3.0)

    new = [f for f in rt_snapshot() - base if f.upper().endswith('.PRN')]
    if not new:
        time.sleep(5.0)
        new = [f for f in rt_snapshot() - base if f.upper().endswith('.PRN')]
    if not new:
        pcx = [f for f in rt_snapshot() - base if f.upper().endswith('.PCX')]
        if pcx:                      # F9 сохранил ГРАФИКУ → текст и повтор
            log(f'F9 дал .PCX ({len(pcx)}) → F6 + повтор сохранения')
            for f in pcx:
                try:
                    os.remove(f)
                except OSError:
                    pass
            send('F6')           # граф → текст (toggle)
            time.sleep(1.0)
            send('6')
            time.sleep(6.0)
            send('ENTER')
            time.sleep(2.0)
            send('6')
            time.sleep(6.0)
            send('F4')
            time.sleep(1.3)
            send('F9')
            time.sleep(1.3)
            send('ENTER')
            time.sleep(3.0)
            new = [f for f in rt_snapshot() - base if f.upper().endswith('.PRN')]
    p1 = prt_size()
    log(f'после F9: новых .PRN={len(new)}, PROTOCOL.PRN={p1} б')
    if not new:
        shot(os.path.join(CAP, f'gb_{name}_anom.bmp'))
        res.update(status='SAVEFAIL', note=f'нет RT__*.PRN; PROTOCOL={p1}')
        append_manifest(f'| {name} | - | - | SAVEFAIL | F9 не создал файл; PROTOCOL={p1} б |',
                        f'{name} SAVEFAIL PROTOCOL={p1}')
        return res
    src = max(new, key=os.path.getmtime)
    dst = os.path.join(BANK, f'{name}.PRN')
    shutil.copyfile(src, dst)
    os.remove(src)
    info = analyze_prn(dst, name)
    ok = info['axial'] and info['size'] > 400
    if sanity and ok:
        txt = open(dst, 'rb').read().decode('cp866', 'replace')
        ok = '-.09008' in txt and '.062432' in txt
        res['note'] = 'эталонные значения осевого пучка ' + ('СОВПАЛИ' if ok else 'НЕ совпали')
    res.update(rt=os.path.basename(src), status='OK' if ok else 'OK-NOAXIAL',
               note=res['note'] or f"секций~{info['seps']}, габариты={'да' if info['gabar'] else 'нет'}")
    append_manifest(
        f"| {name} | {os.path.basename(src)} | {info['size']} | {res['status']} | {res['note']}; {info['head'][:48]} |",
        f"{name}: {os.path.basename(src)} {info['size']}б axial={info['axial']} "
        f"seps~{info['seps']} PROTOCOL {p0}->{p1}; head={info['head']!r}")
    log(f'{name}: {res["status"]} {info}')
    return res


def main():
    names = sys.argv[1:]
    if not names:
        raise SystemExit('usage: py scripts/g2bank.py ИМЯ [ИМЯ...]')
    stats = {}
    for i, nm in enumerate(names):
        try:
            r = run_one(nm, sanity=(nm.upper() == 'US00KI02'))
        except Exception as e:
            r = {'name': nm, 'status': 'CRASH', 'note': repr(e)}
            log(f'{nm}: EXC {e!r}')
        if r['status'] not in ('OK', 'OK-NOAXIAL'):
            log(f'{nm}: {r["status"]} → автоповтор')
            try:
                r = run_one(nm, sanity=(nm.upper() == 'US00KI02'))
            except Exception as e:
                r = {'name': nm, 'status': 'CRASH', 'note': repr(e)}
                log(f'{nm}: EXC(повтор) {e!r}')
        stats[r['name']] = r['status']
    log('ИТОГ: ' + ', '.join(f'{k}={v}' for k, v in stats.items()))


if __name__ == '__main__':
    main()
