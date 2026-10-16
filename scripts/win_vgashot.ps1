param([string]$OutPath = "C:\Users\mikhail\AppData\Local\Temp\dosbox_vga.png")
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class W2 {
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc cb, IntPtr l);
  public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder sb, int n);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
  public struct RECT { public int L, T, R, B; }
  public struct POINT { public int X, Y; }
}
"@
$p = Get-Process DOSBox | Select-Object -First 1
if (-not $p) { Write-Host "no DOSBox"; exit 1 }
$wins = New-Object System.Collections.ArrayList
$cb = {
  param($h, $l)
  $wpid = 0
  [W2]::GetWindowThreadProcessId($h, [ref]$wpid) | Out-Null
  if ($wpid -eq $p.Id) {
    $sb = New-Object System.Text.StringBuilder 256
    [W2]::GetWindowText($h, $sb, 256) | Out-Null
    [void]$wins.Add(@{H=$h; T=$sb.ToString()})
  }
  return $true
}
[W2]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
foreach ($w in $wins) { Write-Host ("win: " + $w.T) }
# скрыть статус-окно
foreach ($w in $wins) {
  if ($w.T -like "*Status*") { [W2]::ShowWindow($w.H, 0) | Out-Null; Write-Host ("hidden: " + $w.T) }
}
Start-Sleep -Milliseconds 300
$main = ($wins | Where-Object { $_.T -like "*cycles*" } | Select-Object -First 1).H
if (-not $main) { $main = $p.MainWindowHandle }
[W2]::SetForegroundWindow($main) | Out-Null
Start-Sleep -Milliseconds 500
$r = New-Object W2+RECT
[W2]::GetClientRect($main, [ref]$r) | Out-Null
$pt = New-Object W2+POINT
$pt.X = 0; $pt.Y = 0
[W2]::ClientToScreen($main, [ref]$pt) | Out-Null
$w = $r.R - $r.L; $ht = $r.B - $r.T
Write-Host ("client ${w}x${ht} at ($($pt.X),$($pt.Y))")
$bmp = New-Object System.Drawing.Bitmap($w, $ht)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($pt.X, $pt.Y, 0, 0, (New-Object System.Drawing.Size($w, $ht)))
$g.Dispose()
$bmp.Save($OutPath, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Host "saved -> $OutPath"
