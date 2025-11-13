; PRISMA Inno Setup Installer Script
; ====================================
; Creates PRISMA-Installer.exe for Windows distribution
;
; Requirements:
;   - Inno Setup 6.2+ (download from https://jrsoftware.org/isinfo.php)
;   - PRISMA.exe already built (run build_exe.py first)
;
; Usage:
;   iscc prisma_installer.iss
;
; Output:
;   Output\PRISMA-Installer-v0.3.0-beta.exe
;
; Author: William Gonzalez
; Date: November 2025
; Version: Beta 0.3

#define MyAppName "PRISMA"
#define MyAppVersion "0.3.0-beta"
#define MyAppPublisher "William Gonzalez, Adrian Guzman, Luke Davenport"
#define MyAppURL "https://github.com/wdgonzo/PRISMA"
#define MyAppExeName "PRISMA.exe"

[Setup]
; Application information
AppId={{8A5D3F2B-4C1E-4D9A-B8F2-9E7A6C5D4B3A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
; Uncomment the following line when LICENSE file is created
; If LICENSE doesn't exist yet, comment out the line above

; Output configuration
OutputDir=Output
OutputBaseFilename=PRISMA-Installer-v{#MyAppVersion}
SetupIconFile=prisma_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; Installation requirements
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0.17763
; Windows 10 version 1809 or later
PrivilegesRequired=admin
; Admin required for Program Files installation

; Uninstaller
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main executable
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Setup scripts
Source: "setup_gsas.py"; DestDir: "{app}\setup"; Flags: ignoreversion
Source: "bundle_python.py"; DestDir: "{app}\setup"; Flags: ignoreversion

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion

; Documentation directory
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

; Example recipes (if they exist)
Source: "..\recipes\*.json"; DestDir: "{app}\examples"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

; Quick Launch shortcut
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Option to launch PRISMA after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  GSASSetupPage: TInputOptionWizardPage;
  GSASPathPage: TInputDirWizardPage;
  GSASSetupChoice: Integer;
  GitAvailable: Boolean;

{ Check if Git is installed }
function CheckGitInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('git', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if Result then
    Result := (ResultCode = 0);
end;

{ Initialize Git check }
procedure InitializeWizard;
begin
  GitAvailable := CheckGitInstalled();

  { Create GSAS-II setup options page }
  GSASSetupPage := CreateInputOptionPage(wpSelectDir,
    'GSAS-II Setup', 'Configure GSAS-II installation',
    'PRISMA requires GSAS-II for peak fitting. Choose how to set up GSAS-II:',
    True, False);

  GSASSetupPage.Add('Download and install GSAS-II automatically (requires Git and ~500MB)');
  GSASSetupPage.Add('I have GSAS-II installed already (specify path)');
  GSASSetupPage.Add('Skip GSAS-II setup (configure manually later)');

  { Default to automatic if Git available }
  if GitAvailable then
    GSASSetupPage.Values[0] := True
  else
    GSASSetupPage.Values[2] := True;

  { Create GSAS-II path selection page }
  GSASPathPage := CreateInputDirPage(GSASSetupPage.ID,
    'GSAS-II Installation Path', 'Specify existing GSAS-II location',
    'Select the directory where GSAS-II is installed:',
    False, 'GSAS-II');
  GSASPathPage.Add('');
end;

{ Control page visibility based on GSAS setup choice }
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  { Skip GSAS path page if not using existing installation }
  if PageID = GSASPathPage.ID then
  begin
    Result := not GSASSetupPage.Values[1];
  end
  else
    Result := False;
end;

{ Validate GSAS-II path if using existing installation }
function NextButtonClick(CurPageID: Integer): Boolean;
var
  GSASPath: String;
  ScriptPath: String;
begin
  Result := True;

  { Validate GSAS path page }
  if CurPageID = GSASPathPage.ID then
  begin
    GSASPath := GSASPathPage.Values[0];

    if GSASPath = '' then
    begin
      MsgBox('Please select a GSAS-II installation directory.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if not DirExists(GSASPath) then
    begin
      MsgBox('The specified directory does not exist.' + #13#10 + GSASPath, mbError, MB_OK);
      Result := False;
      Exit;
    end;

    { Check for GSASII subdirectory }
    if not DirExists(GSASPath + '\GSASII') then
    begin
      MsgBox('Invalid GSAS-II installation.' + #13#10 + 'GSASII subdirectory not found.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    { Check for GSASIIscriptable.py }
    ScriptPath := GSASPath + '\GSASII\GSASIIscriptable.py';
    if not FileExists(ScriptPath) then
    begin
      MsgBox('Invalid GSAS-II installation.' + #13#10 + 'GSASIIscriptable.py not found.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

{ Post-installation GSAS-II setup }
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  GSASPath: String;
  SetupScript: String;
  CommandLine: String;
  ErrorMsg: String;
begin
  if CurStep = ssPostInstall then
  begin
    SetupScript := ExpandConstant('{app}\setup\setup_gsas.py');

    { Option 0: Download and install automatically }
    if GSASSetupPage.Values[0] then
    begin
      if not GitAvailable then
      begin
        MsgBox('Git is not installed. Cannot download GSAS-II automatically.' + #13#10 + #13#10 +
               'Please install Git from https://git-scm.com/download/win' + #13#10 +
               'Then run PRISMA and configure GSAS-II manually.', mbError, MB_OK);
        Exit;
      end;

      { Run setup script to download GSAS-II }
      CommandLine := ExpandConstant('"{app}\{#MyAppExeName}" --gsas-setup');

      { Note: This would need PRISMA.exe to have a --gsas-setup flag }
      { Alternative: Could extract Python and run setup_gsas.py directly }
      { For now, show message to user }
      MsgBox('GSAS-II will be configured on first launch.' + #13#10 + #13#10 +
             'PRISMA will guide you through the setup process.', mbInformation, MB_OK);
    end

    { Option 1: Use existing installation }
    else if GSASSetupPage.Values[1] then
    begin
      GSASPath := GSASPathPage.Values[0];

      { Create environment activation script }
      SaveStringToFile(ExpandConstant('{app}\activate_prisma.bat'),
        '@echo off' + #13#10 +
        'REM PRISMA Environment Activation Script' + #13#10 +
        'SET "GSAS2DIR=' + GSASPath + '"' + #13#10 +
        'SET "PYTHONPATH=' + GSASPath + ';%PYTHONPATH%"' + #13#10 +
        'SET "PATH=' + ExpandConstant('{app}') + ';%PATH%"' + #13#10 +
        'echo PRISMA environment activated' + #13#10 +
        'echo   GSAS-II: %GSAS2DIR%' + #13#10,
        False);

      MsgBox('GSAS-II configured successfully.' + #13#10 + #13#10 +
             'GSAS-II path: ' + GSASPath, mbInformation, MB_OK);
    end

    { Option 2: Skip - user will configure later }
    else if GSASSetupPage.Values[2] then
    begin
      MsgBox('GSAS-II setup skipped.' + #13#10 + #13#10 +
             'You can configure GSAS-II later in PRISMA settings.', mbInformation, MB_OK);
    end;
  end;
end;

[Registry]
; Add to PATH (optional - user can choose during install)
; Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Code]
{ Check if directory is already in PATH }
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE,
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
    'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

[UninstallDelete]
; Clean up created files
Type: files; Name: "{app}\activate_prisma.bat"
Type: filesandordirs; Name: "{userappdata}\.prisma"
