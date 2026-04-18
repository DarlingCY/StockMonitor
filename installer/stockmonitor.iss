; Inno Setup Script for StockMonitor
; Requires Inno Setup 6.x

#define AppName "StockMonitor"
#define AppVersion GetEnv('STOCKMONITOR_VERSION')
#if AppVersion == ""
  #define AppVersion "0.1.0"
#endif
#define AppPublisher "DarlingCY"
#define AppURL "https://github.com/DarlingCY/StockMonitor"
#define AppExeName "StockMonitor.exe"

[Setup]
AppId={{8A7C9D5E-1234-5678-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; 安装包输出路径和名称
OutputDir=dist
OutputBaseFilename=StockMonitor-Setup
SetupIconFile=
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; 权限设置
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; 卸载支持
Uninstallable=yes
CreateUninstallRegKey=yes
; 许可协议（可选）
; LicenseFile=LICENSE.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\StockMonitor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\卸载 {#AppName}"; Filename: "{uninstallexe}"
; 桌面快捷方式（可选）
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; 安装完成后运行
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; 卸载时删除所有文件
Type: filesandordirs; Name: "{app}"
