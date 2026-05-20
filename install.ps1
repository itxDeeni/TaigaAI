# Premium Terminal Coloring helper
function Write-ColorTeal ($text) { Write-Host $text -ForegroundColor Cyan }
function Write-ColorGreen ($text) { Write-Host $text -ForegroundColor Green }
function Write-ColorAmber ($text) { Write-Host $text -ForegroundColor Yellow }
function Write-ColorRed ($text) { Write-Host $text -ForegroundColor Red }

Clear-Host
Write-ColorTeal "=========================================================="
Write-ColorTeal "          TAIGAAI WORKSTATION ENGINE INSTALLER            "
Write-ColorTeal "                     (WINDOWS SETUP)                      "
Write-ColorTeal "=========================================================="
Write-Host ""

$WorkspaceDir = $PSScriptRoot
$BinDir = Join-Path $WorkspaceDir "bin"

# 1. Self-Diagnosis
Write-Host -NoNewline "Checking Python... "
$PythonPath = Get-Command python -ErrorAction SilentlyContinue
if ($PythonPath) {
    $PythonVer = (python --version).Split(" ")[1]
    Write-ColorGreen "OK ($PythonVer)"
} else {
    Write-ColorRed "Missing! Please install Python from Python.org or the Microsoft Store."
    exit 1
}

Write-Host -NoNewline "Checking Git... "
$GitPath = Get-Command git -ErrorAction SilentlyContinue
if ($GitPath) {
    $GitVer = ((git --version).Split(" ")[2])
    Write-ColorGreen "OK ($GitVer)"
} else {
    Write-ColorRed "Missing! Please install Git for Windows."
    exit 1
}

# Run setup configuration and diagnostics wizard
python "$WorkspaceDir\core\setup_config.py"

# 2. Add bin folder to user persistent Path
Write-Host ""
Write-Host "Configuring User PATH Environment Variables..."

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -like "*$BinDir*") {
    Write-ColorGreen "✔ Workstation bin directory is already registered in your PATH."
} else {
    try {
        $NewUserPath = "$UserPath;$BinDir"
        [Environment]::SetEnvironmentVariable("Path", $NewUserPath, "User")
        $env:Path += ";$BinDir"
        Write-ColorGreen "✔ Successfully added workstation bin folder to your USER PATH environment variable!"
        Write-ColorAmber "Note: Please RESTART your PowerShell or Command Prompt terminal for this change to take effect."
    } catch {
        Write-ColorRed "Failed to write user PATH environment variable: $_"
    }
}

Write-ColorGreen "`n🎉 Setup complete! All tools are now accessible system-wide."
Write-ColorTeal "`nTry running (in a NEW terminal window):"
Write-Host "  taiga -h"
Write-Host "  taiga-git help"
Write-Host "  taiga-review"
Write-Host "  taiga-sec"
Write-Host "  taiga-manage"
Write-Host ""
