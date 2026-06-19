$ErrorActionPreference = "Stop"

$RepoUrl = if ($env:RECONKIT_REPO_URL) { $env:RECONKIT_REPO_URL } else { "https://github.com/icynetx/RconKIT.git" }
$ZipUrl = if ($env:RECONKIT_ZIP_URL) { $env:RECONKIT_ZIP_URL } else { "https://github.com/icynetx/RconKIT/archive/refs/heads/main.zip" }
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
    try {
        Install-WinGetPackage "Git.Git" "Git"
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    } catch {
        Write-Host "[!] Git install failed; ZIP fallback will be used if needed." -ForegroundColor Yellow
    }
}
if (-not (Test-Command py) -and -not (Test-Command python)) {
    Install-WinGetPackage "Python.Python.3.12" "Python 3"
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}


function Install-FromZipFallback {
    Write-Step "[*] Downloading ReconKit ZIP fallback"
    $TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("reconkit-" + [System.Guid]::NewGuid().ToString("N"))
    $ZipPath = Join-Path $TempRoot "reconkit.zip"
    $ExtractPath = Join-Path $TempRoot "extract"
    New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null
    Invoke-WebRequest -Uri $ZipUrl -OutFile $ZipPath -UseBasicParsing
    Expand-Archive -Path $ZipPath -DestinationPath $ExtractPath -Force
    $Root = Get-ChildItem -Path $ExtractPath -Directory | Select-Object -First 1
    if (-not $Root) { throw "ZIP archive did not contain a project directory" }
    if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
    Move-Item -Path $Root.FullName -Destination $InstallDir
}

$Parent = Split-Path -Parent $InstallDir
New-Item -ItemType Directory -Force -Path $Parent | Out-Null
if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Step "[*] Updating existing ReconKit checkout: $InstallDir"
    git -C $InstallDir pull --ff-only
    if ($LASTEXITCODE -ne 0) { Write-Host "[!] git pull failed; keeping existing checkout and continuing." -ForegroundColor Yellow }
} elseif (Test-Path $InstallDir) {
    throw "Install path exists but is not a git checkout: $InstallDir. Set RECONKIT_HOME to another path or remove that directory."
} else {
    Write-Step "[*] Cloning ReconKit into $InstallDir"
    if (Test-Command git) {
        git clone --depth 1 --single-branch $RepoUrl $InstallDir
    } else {
        $global:LASTEXITCODE = 1
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] git clone failed or timed out; trying ZIP fallback." -ForegroundColor Yellow
        Install-FromZipFallback
    }
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
