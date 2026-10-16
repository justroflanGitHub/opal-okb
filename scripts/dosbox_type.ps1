# Поднять DOSBox в foreground, скормить жертву-клавишу (первая после
# активации съедается SDL), пауза, затем SendKeys с полезной нагрузкой.
# Использование: powershell -File dosbox_type.ps1 'D3{ENTER}'
param([string]$Keys = '{ENTER}')

$p = Get-Process DOSBox -ErrorAction Stop | Select-Object -First 1
$h = $p.MainWindowHandle
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class F2 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
'@
[F2]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 400
[System.Windows.Forms.SendKeys]::SendWait('{SCROLLLOCK}')   # жертва: безвредна в DOSBox
Start-Sleep -Milliseconds 250
[System.Windows.Forms.SendKeys]::SendWait($Keys)
Start-Sleep -Milliseconds 400
Write-Output "typed: $Keys"
