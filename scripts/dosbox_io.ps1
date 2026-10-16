param([string]$Keys = '', [int]$WaitMs = 1500)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
if ($Keys -ne '') {
  $p = Get-Process -Name DOSBox -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($p) {
    $sig = '[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);'
    Add-Type -MemberDefinition $sig -Name U32 -Namespace W
    [W.U32]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
    Start-Sleep -Milliseconds 300
  }
  foreach ($ch in $Keys.ToCharArray()) {
    [System.Windows.Forms.SendKeys]::SendWait($ch)
    Start-Sleep -Milliseconds 120
  }
}
Start-Sleep -Milliseconds $WaitMs
$b = New-Object System.Drawing.Bitmap([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
$g = [System.Drawing.Graphics]::FromImage($b)
$g.CopyFromScreen(0,0,0,0,$b.Size)
$b.Save("$env:TEMP\dosbox_shot.png",[System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $b.Dispose()
Write-Output "shot saved"
