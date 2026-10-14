import java.io.File;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;

public class FindSegOffTable extends GhidraScript {
    static final String OUT = "C:\\tools\\rea-out\\decomp_opala\\_format_table.txt";
    static final int[] SEGOFFS = {0x4d9, 0x5fa, 0x6b3, 0x7af, 0x8a2, 0x9ea, 0xb3e,
        0xc56, 0xdb9, 0xece, 0x19f8, 0x4e8};
    static final String[] NAMES = {"TABRAY", "TABOC1", "TABOC2", "TABAX3", "TABSAG",
        "TABGL", "TABPR2", "TABBEA", "TABESB", "TABEAP", "AVTO", "f9.3"};

    @Override
    public void run() throws Exception {
        PrintWriter w = new PrintWriter(new File(OUT));
        // scan all initialized memory for word == segOff (skip the string area itself 5000:0000+)
        Address start = currentProgram.getAddressFactory().getAddress("1000:0000");
        Address end = currentProgram.getAddressFactory().getAddress("6000:ffff");
        java.util.List<MemoryBlockLite> blocks = new java.util.ArrayList<>();
        for (ghidra.program.model.mem.MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            if (b.isInitialized() && b.getStart().getOffset() < end.getOffset()
                && b.getEnd().getOffset() > start.getOffset()) {
                blocks.add(new MemoryBlockLite(b));
            }
        }
        for (int k = 0; k < SEGOFFS.length; k++) {
            int seg = SEGOFFS[k];
            StringBuilder sb = new StringBuilder();
            for (MemoryBlockLite b : blocks) {
                for (int i = 0; i + 1 < b.bytes.length; i += 1) {
                    if ((b.bytes[i] & 0xff) == (seg & 0xff)
                        && (b.bytes[i+1] & 0xff) == ((seg >> 8) & 0xff)) {
                        long lin = b.startOff + i;
                        if (lin >= 0x50000 && lin < 0x53000) continue; // strings zone
                        Address a = currentProgram.getAddressFactory().getAddress(Long.toHexString(lin));
                        ghidra.program.model.listing.Function fn =
                            currentProgram.getFunctionManager().getFunctionContaining(a);
                        sb.append(String.format("[%s@%s] ", fn == null ? "DATA" : fn.getName(), a));
                    }
                }
            }
            w.println(NAMES[k] + " (0x" + Integer.toHexString(seg) + ") words at: " + sb.toString().trim());
            println("TBL " + NAMES[k] + " -> " + sb.toString().trim());
        }
        // dump 4000:5b90..5c10 (descriptor area used by e920)
        w.println();
        w.println("--- dump 4000:5b90..5c10 ---");
        try {
            Address d = currentProgram.getAddressFactory().getAddress("4000:5b90");
            byte[] buf = new byte[0x80];
            currentProgram.getMemory().getBytes(d, buf);
            for (int r = 0; r < buf.length; r += 16) {
                StringBuilder hex = new StringBuilder();
                for (int c = 0; c < 16 && r + c < buf.length; c++)
                    hex.append(String.format("%02x ", buf[r + c]));
                w.println(String.format("4000:%04x  %s", 0x5b90 + r, hex));
            }
        } catch (Exception e) { w.println("dump err " + e); }
        w.close();
        println("FIND_TABLE_DONE");
    }

    static class MemoryBlockLite {
        long startOff; byte[] bytes;
        MemoryBlockLite(ghidra.program.model.mem.MemoryBlock b) throws Exception {
            this.startOff = b.getStart().getOffset();
            this.bytes = new byte[(int) b.getSize()];
            b.getBytes(b.getStart(), bytes);
        }
    }
}
