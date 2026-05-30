$ws = New-Object -ComObject WScript.Shell
$escritorio = [System.Environment]::GetFolderPath('Desktop')
$lnk = Join-Path $escritorio "Auto-Clipper AI.lnk"
$s = $ws.CreateShortcut($lnk)
$s.TargetPath = $args[0]
$s.WorkingDirectory = $args[1]
$s.IconLocation = "shell32.dll,22"
$s.Save()
Write-Host "Acceso directo creado en $lnk"