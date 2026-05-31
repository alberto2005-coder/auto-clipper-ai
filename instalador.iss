[Setup]
; Configuracion basica del instalador
AppName=Auto-Clipper AI
AppVersion=1.0
AppPublisher=Tu Nombre o Marca
DefaultDirName={autopf}\Auto-Clipper AI
DefaultGroupName=Auto-Clipper AI
OutputDir=.
OutputBaseFilename=Instalador_AutoClipperAI
Compression=lzma2/ultra64
SolidCompression=yes
; Icono opcional (usa uno por defecto del sistema si no tienes)
SetupIconFile=compiler:SetupClassicIcon.ico
UninstallDisplayIcon={app}\run_gui.exe

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
; Toma TODO el contenido de la carpeta que genero PyInstaller y lo empaqueta
Source: "dist\run_gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Auto-Clipper AI"; Filename: "{app}\run_gui.exe"
Name: "{autodesktop}\Auto-Clipper AI"; Filename: "{app}\run_gui.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\run_gui.exe"; Description: "Abrir Auto-Clipper AI ahora"; Flags: nowait postinstall skipifsilent