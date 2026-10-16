# Поднять окно DOSBox в foreground и отправить Ctrl+F5 (скриншот эмулятора).
# Использование: powershell -File dosbox_fg_keys.ps1 [KEYS через SendKeys-синтаксис]
param([string]$Keys = '+{F5}')

$p = Get-Process DOSBox -ErrorAction Stop | Select-Object -First 1
$h = $p.MainWindowHandle
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class F {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
'@
[F]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 400
$fg = [F]::GetForegroundWindow()
Write-Output ("foreground==dosbox: " + ($fg -eq $h))
[System.Windows.Forms.SendKeys]::SendWait($Keys)
Start-Sleep -Milliseconds 500
Write-Output "sent: $Keys"
