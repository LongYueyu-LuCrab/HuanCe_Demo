Add-Type -AssemblyName System.Drawing
$path = Join-Path $PSScriptRoot '..\tmp\ui-test-sample.png'
$bitmap = New-Object System.Drawing.Bitmap 480, 300
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$font = New-Object System.Drawing.Font 'Arial', 22
try {
    $graphics.Clear([System.Drawing.Color]::White)
    $graphics.DrawRectangle([System.Drawing.Pens]::Blue, 50, 50, 380, 200)
    $graphics.DrawString('UI TEST SAMPLE', $font, [System.Drawing.Brushes]::Black, 95, 100)
    $graphics.DrawString('NOT REAL DATA', $font, [System.Drawing.Brushes]::Red, 90, 160)
    $bitmap.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
} finally {
    $font.Dispose()
    $graphics.Dispose()
    $bitmap.Dispose()
}
Write-Output ([System.IO.Path]::GetFullPath($path))
