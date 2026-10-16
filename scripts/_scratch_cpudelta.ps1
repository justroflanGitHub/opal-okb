$p = Get-Process DOSBox
$c1 = $p.CPU
Start-Sleep 2
$p.Refresh()
Write-Host ("cpu_delta={0:n2}s over 2s (pid {1})" -f ($p.CPU - $c1), $p.Id)
