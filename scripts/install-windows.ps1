$ErrorActionPreference = "Stop"

function Invoke-ReconKit {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ReconArgs)
    $UserLauncher = Join-Path $env:USERPROFILE ".reconkit\bin\reconkit.cmd"
    if (Test-Path $UserLauncher) {
        & $UserLauncher @ReconArgs
        return $LASTEXITCODE
    }
    $WindowsAppsLauncher = Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\reconkit.cmd"
    if (Test-Path $WindowsAppsLauncher) {
        & $WindowsAppsLauncher @ReconArgs
        return $LASTEXITCODE
    }
    if (Get-Command reconkit -ErrorAction SilentlyContinue) {
        & reconkit @ReconArgs
        return $LASTEXITCODE
    }
    & py -3 .\recon.py @ReconArgs
    if ($LASTEXITCODE -eq 9009) { & python .\recon.py @ReconArgs }
    return $LASTEXITCODE
}

Write-Host "[*] Installing ReconKit command for current Windows user..." -ForegroundColor Cyan
& py -3 .\recon.py --self-install --user
if ($LASTEXITCODE -eq 9009) { & python .\recon.py --self-install --user }
if ($LASTEXITCODE -ne 0) { throw "ReconKit self-install failed." }

Write-Host "[*] Installing ReconKit dependencies best-effort..." -ForegroundColor Cyan
Invoke-ReconKit --install-deps --with-optional

Write-Host "[*] Final dependency status:" -ForegroundColor Cyan
Invoke-ReconKit --check-deps

Write-Host "[+] Done. Try: reconkit" -ForegroundColor Green
Write-Host "    If this terminal cannot see reconkit yet, open a new PowerShell window." -ForegroundColor DarkGray
