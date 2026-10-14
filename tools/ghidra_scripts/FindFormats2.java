import java.io.File;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.symbol.Reference;

public class FindFormats2 extends GhidraScript {
    static final String OUT = "C:\\tools\\rea-out\\decomp_opala\\_format_xrefs.txt";
    static final String[] PATTERNS = {"TABRAY", "TABOC1", "TABOC2", "TABAX3", "TABSAG",
        "TABGL", "TABPR2", "TABBEA", "TABESB", "TABEAP", "AVTO", "F11.5", "f9.3"};

    @Override
    public void run() throws Exception {
        PrintWriter w = new PrintWriter(new File(OUT));
        for (String pat : PATTERNS) {
            byte[] bytes = pat.getBytes("US-ASCII");
            Address start = currentProgram.getAddressFactory().getAddress("1000:0000");
            Address end = currentProgram.getAddressFactory().getAddress("5000:463f");
            while (true) {
                Address found = currentProgram.getMemory().findBytes(
                    start, end, bytes, null, true, monitor);
                if (found == null) break;
                int off = (int) found.getOffset(); // linear offset
                // offset within segment 5000 = off - 0x50000
                int segOff = off - 0x50000;
                String around = "";
                try {
                    byte[] buf = new byte[110];
                    currentProgram.getMemory().getBytes(found, buf);
                    int z = 0; while (z < buf.length && buf[z] != 0) z++;
                    around = new String(buf, 0, z, "US-ASCII").replaceAll("[^\\x20-\\x7e]", ".");
                } catch (Exception e) {}
                // 1) real references if any
                StringBuilder refs = new StringBuilder();
                for (Reference r : currentProgram.getReferenceManager().getReferencesTo(found)) {
                    Function fn = currentProgram.getFunctionManager().getFunctionContaining(r.getFromAddress());
                    refs.append(fn == null ? r.getFromAddress().toString() : fn.getName() + "@" + r.getFromAddress());
                    refs.append(" ");
                }
                // 2) immediate scan: PUSH segOff / MOV reg, segOff in code
                StringBuilder imms = new StringBuilder();
                if (segOff > 0 && segOff < 0x10000) {
                    InstructionIterator it = currentProgram.getListing().getInstructions(true);
                    while (it.hasNext()) {
                        Instruction ins = it.next();
                        if (ins.getAddress().getOffset() >= 0x50000) break; // strings area
                        for (Object o : ins.getOpObjects(new int[]{0, 1}[0] == 0 ? 0 : 0)) {}
                        Object[] ops = ins.getOpObjects(0);
                        if (ops.length == 0) ops = ins.getOpObjects(1);
                        for (Object o : ops) {
                            if (o instanceof Scalar) {
                                Scalar s = (Scalar) o;
                                if (s.getUnsignedValue() == (segOff & 0xffffL)) {
                                    Function fn = currentProgram.getFunctionManager().getFunctionContaining(ins.getAddress());
                                    imms.append(fn == null ? ins.getAddress().toString() : fn.getName() + "@" + ins.getAddress());
                                    imms.append(" ");
                                    break;
                                }
                            }
                        }
                    }
                }
                w.println(pat + " | at " + found + " (segOff=0x" + Integer.toHexString(segOff)
                    + ") | refs: [" + refs.toString().trim() + "] | imm-push: [" + imms.toString().trim()
                    + "] | text: " + around);
                println("FOUND " + pat + " at " + found + " segOff=0x" + Integer.toHexString(segOff));
                start = found.add(1);
            }
        }
        w.close();
        println("FIND_FORMATS2_DONE");
    }
}
