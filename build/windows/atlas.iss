#define AppName "Atlas"
#define AppVersion "0.1.0"
#define AppPublisher "Atlas"
#define AppExeName "Atlas.Desktop.exe"

[Setup]
AppId={{D49B9C7A-20A9-4D8A-8E13-7A36D9B47E51}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Atlas
DefaultGroupName=Atlas
DisableProgramGroupPage=yes
OutputDir=..\..\artifacts\installer
OutputBaseFilename=Atlas-Setup-{#AppVersion}-win-x64
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "..\..\artifacts\publish\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Atlas"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\Atlas"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Iniciar Atlas"; Flags: postinstall nowait skipifsilent
