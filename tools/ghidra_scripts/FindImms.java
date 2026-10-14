import java.io.File;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class FindImms extends GhidraScript {
    static final String OUT = "C:\\tools\\rea-out\\decomp_opala\\_format_imms.txt";
    // offsets of format strings in segment 5000
    static final int[] SEGOFFS = {0x4d9, 0x5fa, 0x6b3, 0x7af, 0x8a2, 0x9ea, 0xb3e,
        0xc56, 0xdb9, 0xece, 0x19f8, 0x3ec, 0x455, 0x4e8, 0x260c, 0x2788};
    static final String[] NAMES = {"TABRAY", "TABOC1", "TABOC2", "TABAX3", "TABSAG",
        "TABGL", "TABPR2", "TABBEA", "TABESB", "TABEAP", "AVTO", "F11.5-a", "F11.5-b", "f9.3",
        "TABRAY2", "TABAX3-2"};
    // x86 16-bit opcodes loading imm16 (little-endian operand follows)
    static final int[] OPCODES = {0x68 /*push imm16*/, 0xB8, 0xB9, 0xBA, 0xBB, 0xBE, 0xBF,
        0x05 /*add ax*/, 0x0D /*or ax*/, 0x15 /*adc ax*/, 0x25 /*and ax*/, 0x2D /*sub ax*/,
        0x35 /*xor ax*/, 0x3D /*cmp ax*/};

    @Override
    public void run() throws Exception {
        PrintWriter w = new PrintWriter(new File(OUT));
        Address codeStart = currentProgram.getAddressFactory().getAddress("1000:0000");
        Address codeEnd = currentProgram.getAddressFactory().getAddress("5000:0000");
        byte[] code = new byte[(int)(codeEnd.getOffset() - codeStart.getOffset())];
        currentProgram.getMemory().getBytes(codeStart, code);
        for (int k = 0; k < SEGOFFS.length; k++) {
            int seg = SEGOFFS[k];
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < code.length - 3; i++) {
                int op = code[i] & 0xff;
                if (op == 0x68 || (op >= 0xB8 && op <= 0xBF) || op == 0x05 || op == 0x0D
                    || op == 0x15 || op == 0x25 || op == 0x2D || op == 0x35 || op == 0x3D) {
                    if ((code[i+1] & 0xff) == (seg & 0xff) && (code[i+2] & 0xff) == ((seg >> 8) & 0xff)) {
                        long lin = codeStart.getOffset() + i;
                        // containing function via listing (may be null)
                        Address a = currentProgram.getAddressFactory().getAddress(Long.toHexString(lin));
                        ghidra.program.model.listing.Function fn =
                            currentProgram.getFunctionManager().getFunctionContaining(a);
                        sb.append(String.format("%s:%s ", (fn == null ? "?" : fn.getName()),
                            a));
                    }
                }
            }
            w.println(NAMES[k] + " (segOff=0x" + Integer.toHexString(seg) + ") hits: " + sb.toString().trim());
            println("IMM " + NAMES[k] + " -> " + sb.toString().trim());
        }
        w.close();
        println("FIND_IMMS_DONE");
    }
}
