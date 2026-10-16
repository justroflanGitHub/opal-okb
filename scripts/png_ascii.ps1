param([string]$PngPath, [int]$Cols = 110)
Add-Type -AssemblyName System.Drawing
$png = [System.Drawing.Image]::FromFile($PngPath)
$bmp = New-Object System.Drawing.Bitmap($png)
$rows = [int]($Cols * $bmp.Height / $bmp.Width / 2.1)
$chars = " .:-=+*#%@"
$out = New-Object System.Text.StringBuilder
for ($y=0; $y -lt $rows; $y++) {
  $line = New-Object System.Text.StringBuilder
  for ($x=0; $x -lt $Cols; $x++) {
    $sx = [int]($x * $bmp.Width / $Cols); $sy = [int]($y * $bmp.Height / $rows)
    $c = $bmp.GetPixel($sx, $sy)
    $b = [int](($c.R + $c.G + $c.B) / 3)
    $idx = [int]($b * ($chars.Length - 1) / 255)
    [void]$line.Append($chars[$idx])
  }
  [void]$out.AppendLine($line.ToString())
}
$bmp.Dispose(); $png.Dispose()
Write-Output $out.ToString()
