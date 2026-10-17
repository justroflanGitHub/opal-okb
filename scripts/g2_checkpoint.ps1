$ErrorActionPreference = 'SilentlyContinue'
Set-Location C:\Users\mikhail\.openclaw\workspace\opal_okb
$git = 'C:\Program Files\Git\cmd\git.exe'
while ($true) {
    Start-Sleep -Seconds 1200
    & $git add -A 2>$null
    $staged = & $git diff --cached --name-only 2>$null
    if ($staged) {
        $ts = Get-Date -Format 'HH:mm'
        & $git commit -m "checkpoint: gfix auto $ts" 2>$null | Out-Null
        & $git push origin feature/native-core 2>$null | Out-Null
    }
}
