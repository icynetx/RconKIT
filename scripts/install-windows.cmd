@echo off
setlocal
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 recon.py --self-install --user
) else (
  python recon.py --self-install --user
)
if errorlevel 1 exit /b %errorlevel%

set "RK=%USERPROFILE%\.reconkit\bin\reconkit.cmd"
if exist "%RK%" goto run
set "RK=%LOCALAPPDATA%\Microsoft\WindowsApps\reconkit.cmd"
if exist "%RK%" goto run
set "RK=reconkit"

:run
"%RK%" --install-deps --with-optional
"%RK%" --check-deps
echo [+] Done. Try: reconkit
echo     If this terminal cannot see reconkit yet, open a new CMD/PowerShell window.
