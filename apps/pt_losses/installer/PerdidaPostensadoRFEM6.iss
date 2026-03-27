[Setup]
AppId={{B1F6F6B6-6D0C-4C0D-8A8D-PTLOSS-RFEM6}}
AppName=Calculadora de pérdidas de postensado para RFEM6
AppVersion=1.3
AppPublisher=MIDEE
AppPublisherURL=https://dlubal.com.ar
DefaultDirName={autopf}\MIDEE\PerdidaPostensadoRFEM6
DefaultGroupName=MIDEE\Calculadora de pérdidas de postensado para RFEM6
DisableProgramGroupPage=yes
OutputDir=..\..\..\dist\installer
OutputBaseFilename=PerdidaPostensadoRFEM6-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\src\pt_losses\gui\assets\postensado.ico
UninstallDisplayIcon={app}\PerdidaPostensadoRFEM6.exe
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "..\..\..\dist\PerdidaPostensadoRFEM6\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Calculadora de pérdidas de postensado para RFEM6"; Filename: "{app}\PerdidaPostensadoRFEM6.exe"; IconFilename: "{app}\PerdidaPostensadoRFEM6.exe"
Name: "{autodesktop}\Calculadora de pérdidas de postensado para RFEM6"; Filename: "{app}\PerdidaPostensadoRFEM6.exe"; Tasks: desktopicon; IconFilename: "{app}\PerdidaPostensadoRFEM6.exe"

[Run]
Filename: "{app}\PerdidaPostensadoRFEM6.exe"; Description: "Abrir Calculadora de pérdidas de postensado para RFEM6"; Flags: nowait postinstall skipifsilent


