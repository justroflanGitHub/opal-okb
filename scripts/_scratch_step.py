"""Шаг: отправить клавиши в DOSBox (foreground+keybd_event), подождать, снять родной скриншот Ctrl+F5,
скопировать в capture/step_NNN.png. Использование: py _scratch_step.py [-w сек] KEY [KEY...]"""
import glob, os, shutil, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _scratch_sendkeys as sk

CAPDIR = r"C:\GOLDEN_DOS\capture"
DST = r"C:\Users\mikhail\.openclaw\workspace\opal_okb\capture"

def native_shots():
    return set(glob.glob(os.path.join(CAPDIR, "*.png")))

def latest(before):
    new = [f for f in glob.glob(os.path.join(CAPDIR, "*.png")) if f not in before]
    return sorted(new, key=os.path.getmtime)

def main():
    args = sys.argv[1:]
    wait = 1.5
    if args and args[0] == '-w':
        wait = float(args[1]); args = args[2:]
    idx = len(glob.glob(os.path.join(DST, "step_*.png")))
    before = native_shots()
    if args:
        sk.focus(); time.sleep(0.3)
        for tok in args:
            t = tok.upper()
            if t == 'WAIT':
                time.sleep(2); continue
            sk_mod = __import__('_scratch_sendkeys')
            # одиночные символы / имена
            if t in sk.NAMED:
                sk.tap(sk.NAMED[t])
            else:
                for ch in tok:
                    vk = sk.u32.VkKeyScanW(ord(ch))
                    sh = (vk >> 8) & 1
                    if sh: sk.key(0x10)
                    sk.tap(vk & 0xFF, 0.05)
                    if sh: sk.key(0x10, up=True)
    time.sleep(wait)
    sk.focus(); time.sleep(0.2)
    sk.combo([sk.CTRL], 0x74)
    time.sleep(1.0)
    newf = latest(before)
    if not newf:
        print("NO NEW SHOT"); return
    dst = os.path.join(DST, f"step_{idx+1:03d}.png")
    shutil.copy(newf[-1], dst)
    print("keys:", ' '.join(args) if args else "(shot only)", "->", os.path.basename(dst))

if __name__ == '__main__':
    main()
