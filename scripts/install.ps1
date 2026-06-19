$ErrorActionPreference = "Stop"

$RepoUrl = if ($env:RECONKIT_REPO_URL) { $env:RECONKIT_REPO_URL } else { "https://github.com/icynetx/RconKIT.git" }
$InstallDir = if ($env:RECONKIT_HOME) { $env:RECONKIT_HOME } else { Join-Path $env:USERPROFILE ".reconkit\src" }
$InstallOptional = if ($env:RECONKIT_INSTALL_OPTIONAL) { $env:RECONKIT_INSTALL_OPTIONAL } else { "1" }
$SkipTools = if ($env:RECONKIT_SKIP_TOOLS) { $env:RECONKIT_SKIP_TOOLS } else { "0" }

function Write-Step($Message) { Write-Host $Message -ForegroundColor Cyan }
function Write-Ok($Message) { Write-Host $Message -ForegroundColor Green }
function Test-Command($Name) { return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }
function Invoke-PythonReconKit([string[]]$ReconArgs) {
    if (Test-Command py) {
        & py -3 .\recon.py @ReconArgs
    } else {
        & python .\recon.py @ReconArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "ReconKit command failed: $($ReconArgs -join ' ')" }
}

Write-Step "[*] ReconKit installer by Team CynetX"
Write-Step "[*] Website: https://cynetx.ir | Telegram: https://t.me/cynetx"

function Install-WinGetPackage($Id, $Name) {
    if (-not (Test-Command winget)) { throw "$Name is required and winget was not found. Install $Name manually, then rerun this command." }
    Write-Step "[*] $Name not found; trying winget install..."
    winget install --id $Id --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "winget failed to install $Name. Install it manually, then rerun this command." }
}

if (-not (Test-Command git)) {
    Install-WinGetPackage "Git.Git" "Git"
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
if (-not (Test-Command py) -and -not (Test-Command python)) {
    Install-WinGetPackage "Python.Python.3.12" "Python 3"
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

$Parent = Split-Path -Parent $InstallDir
New-Item -ItemType Directory -Force -Path $Parent | Out-Null
if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Step "[*] Updating existing ReconKit checkout: $InstallDir"
    git -C $InstallDir pull --ff-only
} elseif (Test-Path $InstallDir) {
    throw "Install path exists but is not a git checkout: $InstallDir. Set RECONKIT_HOME to another path or remove that directory."
} else {
    Write-Step "[*] Cloning ReconKit into $InstallDir"
    git clone $RepoUrl $InstallDir
}

Set-Location $InstallDir
Write-Step "[*] Installing reconkit command for current user"
Invoke-PythonReconKit @("--self-install", "--user")

if ($SkipTools -eq "1") {
    Write-Step "[*] Skipping external tool installation because RECONKIT_SKIP_TOOLS=1"
} elseif ($InstallOptional -eq "1") {
    Write-Step "[*] Installing required + optional tools best-effort"
    Invoke-PythonReconKit @("--install-deps", "--with-optional")
} else {
    Write-Step "[*] Installing required tools best-effort"
    Invoke-PythonReconKit @("--install-deps")
}

Write-Step "[*] Final dependency status"
try { Invoke-PythonReconKit @("--check-deps") } catch { Write-Host $_ -ForegroundColor Yellow }

Write-Ok "[+] Done. Try: reconkit"
Write-Host "    If this terminal cannot find reconkit yet, open a new PowerShell window." -ForegroundColor DarkGray
