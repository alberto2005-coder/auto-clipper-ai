$ws = New-Object -ComObject WScript.Shell
$escritorio = [System.Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $escritorio "Auto-Clipper AI.lnk"
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $args[0]
$s.WorkingDirectory = $args[1]
$ico = Join-Path $args[1] "assets\logo.ico"
if (-not (Test-Path $ico)) {
    $ico = Join-Path $args[1] "logo.ico"
}
if (Test-Path $ico) {
    $s.IconLocation = "$ico,0"
} else {
    $s.IconLocation = "shell32.dll,22"
}
$s.Save()
Write-Host "Acceso directo creado en $lnk"