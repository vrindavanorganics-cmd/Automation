# One-time setup: creates a Desktop shortcut that launches ORBIT's real
# window directly (python main.py --gui via pythonw.exe, so no console
# window flashes up). After running this once, just double-click the
# "ORBIT" icon on your Desktop -- no PowerShell needed for normal use.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\create_desktop_shortcut.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = (Get-Item $PSScriptRoot).Parent.FullName

if (-not (Test-Path "$RepoRoot\.venv")) {
    Write-Host "Virtual environment not found. Run scripts\setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}

$PythonwExe = "$RepoRoot\.venv\Scripts\pythonw.exe"
if (-not (Test-Path $PythonwExe)) {
    Write-Host "pythonw.exe not found in .venv\Scripts -- is this a standard Windows Python install?" -ForegroundColor Red
    exit 1
}

# Best-effort icon (skipped silently if Pillow isn't installed) -- the
# shortcut still works fine without it, just with the default icon.
$IconPath = "$RepoRoot\assets\orbit.ico"
if (-not (Test-Path $IconPath)) {
    & "$RepoRoot\.venv\Scripts\python.exe" "$RepoRoot\scripts\generate_icon.py" 2>$null
}

$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\ORBIT.lnk")
$Shortcut.TargetPath = $PythonwExe
$Shortcut.Arguments = "main.py --gui"
$Shortcut.WorkingDirectory = $RepoRoot
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = $IconPath
}
$Shortcut.Description = "ORBIT -- your voice AI desktop agent"
$Shortcut.Save()

Write-Host "Desktop shortcut created: $DesktopPath\ORBIT.lnk" -ForegroundColor Green
Write-Host "Double-click it any time to open ORBIT -- no PowerShell needed." -ForegroundColor Green
