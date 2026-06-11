[Setup]
; Configuracion basica del instalador
AppName=Auto-Clipper AI
AppVersion=2.0
AppPublisher=Alberto
; AppId unico (GUID): permite detectar versiones instaladas y gestionar actualizaciones
AppId={{B7F3A2C1-4D8E-4F19-9B2A-DA3E56781230}}
; Solo Windows 10+ de 64 bits
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DefaultDirName={autopf}\Auto-Clipper AI
DefaultGroupName=Auto-Clipper AI
OutputDir=.
OutputBaseFilename=Instalador_AutoClipperAI
Compression=lzma2/ultra64
SolidCompression=yes
; Icono del instalador personalizado
SetupIconFile=logo.ico
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