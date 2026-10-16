param([string]$PngPath)
Add-Type -AssemblyName System.Drawing
$png = [System.Drawing.Image]::FromFile($PngPath)
$bmp = New-Object System.Drawing.Bitmap($png)
$nonblack = 0
$colors = @{}
for ($y=0; $y -lt $bmp.Height; $y+=2) {
  for ($x=0; $x -lt $bmp.Width; $x+=2) {
    $c = $bmp.GetPixel($x,$y)
    if ($c.R -gt 20 -or $c.G -gt 20 -or $c.B -gt 20) { $nonblack++ }
    $colors["$($c.R),$($c.G),$($c.B)"] = 1
  }
}
Write-Host ("size={0}x{1} nonblack={2} distinct={3}" -f $bmp.Width,$bmp.Height,$nonblack,$colors.Count)
$bmp.Dispose(); $png.Dispose()
