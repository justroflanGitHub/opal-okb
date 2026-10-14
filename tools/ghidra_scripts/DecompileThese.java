import java.io.File;
import java.io.PrintWriter;

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class DecompileThese extends GhidraScript {
    static final String OUTDIR = "C:\\tools\\rea-out\\decomp_opala\\";
    static final String[] ADDRS = {
        "1000:7df9", "1000:6a4b", "1000:1bfd", "1000:db6f", "1000:babf", "1000:d3bd",
        "2000:e05a", "2000:e12b", "2000:f782", "2000:3590", "2000:3e4c", "2000:4617",
        "2000:6191", "2000:8b89", "2000:c816",
        "3000:11c4", "3000:3a3c", "3000:3ce0", "3000:c975", "3000:e310",
        "4000:5136", "4000:52d8", "4000:6fac", "4000:89a4", "4000:92a4", "4000:92c4",
        "4000:9a2a"
    };

    @Override
    public void run() throws Exception {
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        for (String s : ADDRS) {
            Address a = currentProgram.getAddressFactory().getAddress(s);
            Function fn = currentProgram.getFunctionManager().getFunctionAt(a);
            if (fn == null) {
                fn = createFunction(a, "FUN_" + s.replace(':', '_'));
                println("created function at " + s + " -> " + (fn == null ? "FAIL" : fn.getName()));
            }
            if (fn == null) continue;
            DecompileResults res = di.decompileFunction(fn, 120, monitor);
            String code = res.getDecompiledFunction() == null ? null
                : res.getDecompiledFunction().getC();
            if (code == null) {
                println(s + " decompile FAILED: " + res.getErrorMessage());
                continue;
            }
            String fname = OUTDIR + s.replace(':', '_') + "_" + fn.getName() + ".c";
            PrintWriter w = new PrintWriter(new File(fname), "UTF-8");
            w.print(code);
            w.close();
            println("WROTE " + fname + " (" + code.length() + " chars)");
        }
        di.dispose();
        println("DECOMPILE_THESE_DONE");
    }
}
