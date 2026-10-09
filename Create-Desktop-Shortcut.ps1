# Creates convenient Windows Shortcuts in D:\LithoLog Studio and on the Desktop
$TargetDir = "D:\LithoLog Studio"
$ExePath = Join-Path $TargetDir "portable\LithoLogStudio\LithoLogStudio.exe"
$WshShell = New-Object -ComObject WScript.Shell

# 1. Shortcut in D:\LithoLog Studio
$LocalShortcutPath = Join-Path $TargetDir "LithoLog Studio (Desktop Shortcut).lnk"
$Shortcut = $WshShell.CreateShortcut($LocalShortcutPath)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = (Join-Path $TargetDir "portable\LithoLogStudio")
$Shortcut.Description = "LithoLog Studio - Native Windows Desktop Application"
$Shortcut.Save()
Write-Host "Created local shortcut: $LocalShortcutPath" -ForegroundColor Green

# 2. Desktop Shortcut
$DesktopFolder = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
if (Test-Path $DesktopFolder) {
    $DesktopShortcutPath = Join-Path $DesktopFolder "LithoLog Studio.lnk"
    $DesktopShortcut = $WshShell.CreateShortcut($DesktopShortcutPath)
    $DesktopShortcut.TargetPath = $ExePath
    $DesktopShortcut.WorkingDirectory = (Join-Path $TargetDir "portable\LithoLogStudio")
    $DesktopShortcut.Description = "LithoLog Studio - Open-Source RockWorks, GMS & Surpac Alternative"
    $DesktopShortcut.Save()
    Write-Host "Created Desktop shortcut: $DesktopShortcutPath" -ForegroundColor Green
}
