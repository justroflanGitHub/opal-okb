Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Drawing;
using System.Drawing.Imaging;
public class Cap {
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public struct RECT { public int L, T, R, B; }
  public static void Shot(IntPtr h, string path) {
    RECT r; GetWindowRect(h, out r);
    int w = r.R - r.L, ht = r.B - r.T;
    if (w <= 0 || ht <= 0) throw new Exception("bad rect");
    Bitmap b = new Bitmap(w, ht);
    Graphics g = Graphics.FromImage(b);
    IntPtr hd = g.GetHdc();
    PrintWindow(h, hd, 2);
    g.ReleaseHdc(hd);
    b.Save(path, ImageFormat.Png);
    g.Dispose(); b.Dispose();
  }
}
'@
$p = Get-Process DOSBox -ErrorAction Stop | Select-Object -First 1
[Cap]::Shot($p.MainWindowHandle, "$env:TEMP\dosbox_win.png")
Get-Item "$env:TEMP\dosbox_win.png" | Select-Object Length
