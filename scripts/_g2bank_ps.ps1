Get-CimInstance Win32_Process |
  Where-Object { $_.CommandLine -match 'g2bank|dosbox_send|_g2_shot|_g2_read' } |
  Select-Object ProcessId, Name, @{n = 'Cmd'; e = { $_.CommandLine.Substring(0, [Math]::Min(110, $_.CommandLine.Length)) } } |
  Format-Table -AutoSize | Out-String -Width 200
