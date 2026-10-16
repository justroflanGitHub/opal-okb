Get-CimInstance Win32_Process -Filter "Name LIKE 'py%.exe' OR Name LIKE 'python%.exe'" |
  Select-Object ProcessId, Name, CreationDate, CommandLine | Format-List
"--- key states ---"
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class K {
  [DllImport("user32.dll")] public static extern short GetAsyncKeyState(int vk);
}
"@
foreach ($n in @('SHIFT','CTRL','ALT')) {
  $vk = @{SHIFT=0x10; CTRL=0x11; ALT=0x12}[$n]
  $st = [K]::GetAsyncKeyState($vk)
  "$n : 0x{0:X4} $($(if ($st -band 0x8000) {'DOWN'} else {'up'}))" -f $st
}
