import java.io.File;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import ghidra.program.model.mem.MemoryBlock;

public class MemInfo extends GhidraScript {
    @Override
    public void run() throws Exception {
        PrintWriter w = new PrintWriter(new File("C:\\tools\\rea-out\\decomp_opala\\_meminfo.txt"));
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            w.println(b.getName() + " | " + b.getStart() + " .. " + b.getEnd()
                + " | size=0x" + Long.toHexString(b.getSize())
                + " | type=" + b.getType() + " | init=" + b.isInitialized());
        }
        byte[] pat = "TABRAY".getBytes("US-ASCII");
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            if (!b.isInitialized()) continue;
            try {
                AddressSet set = new AddressSet(b.getStart(), b.getEnd());
                Address a = currentProgram.getMemory().findBytes(
                    b.getStart(), b.getEnd(), pat, null, true, monitor);
                if (a != null) w.println("TABRAY found in " + b.getName() + " at " + a);
            } catch (Exception e) {
                w.println(b.getName() + " scan err " + e);
            }
        }
        w.close();
        println("MEMINFO_DONE");
    }
}
