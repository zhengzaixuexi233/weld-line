#define MyAppName "焊缝识别系统"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Takobox"
#define MyAppExeName "焊缝识别系统.exe"

[Setup]
AppId={{A8C0D6F4-0E6C-4D4A-9F2C-123456789ABC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=output
OutputBaseFilename=焊缝识别系统_Setup_{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: unchecked

[Files]
; 应用核心文件 - 每次升级覆盖
Source: "..\dist\焊缝识别系统\焊缝识别系统.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\焊缝识别系统\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

; 应用配置（default.yaml）- 每次升级覆盖
Source: "..\dist\焊缝识别系统\config\default.yaml"; DestDir: "{app}\config"; Flags: ignoreversion

; 用户数据（模板记录、检测日志）- 首次安装才写入，升级不覆盖
Source: "..\dist\焊缝识别系统\config\user_data\*"; DestDir: "{app}\config\user_data"; Flags: onlyifdoesntexist recursesubdirs createallsubdirs

; 检测结果保存目录 - 首次安装才写入，升级不覆盖，源目录为空时跳过
Source: "..\dist\焊缝识别系统\data\saved\*"; DestDir: "{app}\data\saved"; Flags: onlyifdoesntexist skipifsourcedoesntexist recursesubdirs createallsubdirs

; 示例数据 - 每次升级覆盖
Source: "..\dist\焊缝识别系统\data\images\*"; DestDir: "{app}\data\images"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\焊缝识别系统\data\videos\*"; DestDir: "{app}\data\videos"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
