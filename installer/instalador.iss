; Script de Inno Setup 7 para Auto-Clipper AI
; Requiere haber generado previamente el ejecutable con scripts\crear_exe.bat (carpeta dist\run_gui)

#define MyAppName "Auto-Clipper AI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Alberto"
#define MyAppURL "https://github.com/alberto2005-coder/auto-clipper-ai"
#define MyAppExeName "run_gui.exe"

[Setup]
; Identificador unico de la aplicacion (GUID)
AppId={{B7F3A2C1-4D8E-4F19-9B2A-DA3E56781230}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=Instalador_AutoClipperAI
SetupIconFile=..\assets\logo.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=yes

; Requisitos de sistema: Windows 10+ 64-bit (Compatible con Inno Setup 7)
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog commandline

; Configuracion del desinstalador
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Archivos generados por PyInstaller en dist\run_gui
Source: "..\dist\run_gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Icono de la aplicacion
Source: "..\assets\logo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\logo.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\logo.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent