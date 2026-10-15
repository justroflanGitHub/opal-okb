# TASK_OPCOM: рекурсивный 16-битный дизассемблер (capstone) для COM-образов.
# Следует jmp/call (в т.ч. условным) от точки входа; таблицы int-диспетчера
# обрабатываются вручную отдельными сидами.
import sys
import capstone

JMP_MN = ('jmp',)
JCC_MN = ('je','jne','jb','jae','jbe','ja','js','jns','jo','jno','jp','jnp',
          'jl','jge','jle','jg','jcxz','loop','loope','loopne')
CALL_MN = ('call',)
RET_MN = ('ret','retf','iret','hlt')

def rec_disasm(data, org, entry, extra_seeds=()):
    """entry/extra_seeds — линейные адреса (org + file_offset)."""
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_16)
    md.detail = True
    todo = [entry] + list(extra_seeds)
    done = {}          # addr -> (bytes, text)
    while todo:
        a = todo.pop()
        off = a - org
        if off < 0 or off >= len(data) or a in done:
            continue
        code = data[off:]
        for ins in md.disasm(code, a):
            if ins.address in done:
                break
            done[ins.address] = (ins.bytes.hex(), f"{ins.mnemonic} {ins.op_str}")
            m = ins.mnemonic
            if m in RET_MN:
                break
            if m in JMP_MN or m in JCC_MN or m in CALL_MN:
                if ins.operands and ins.operands[0].type == capstone.x86.X86_OP_IMM:
                    todo.append(ins.operands[0].imm)
                if m in JMP_MN:
                    break          # безусловный jmp — дальше поток не идёт
            # call/jcc — поток продолжается дальше
    return dict(sorted(done.items()))

if __name__ == '__main__':
    import tsr_lib as T
    name = sys.argv[1]
    entry = int(sys.argv[2], 0)
    seeds = [int(x, 0) for x in sys.argv[3:]]
    d = T.load(name)
    org = 0x100
    out = rec_disasm(d, org, entry, seeds)
    for a, (b, t) in out.items():
        print(f"{a:06x}  {b:<16} {t}")
    print(f"; total {len(out)} instructions", file=sys.stderr)
