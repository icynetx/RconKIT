@echo off
setlocal
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 recon.py --self-install --user --no-color
) else (
  python recon.py --self-install --user --no-color
)
if errorlevel 1 exit /b %errorlevel%

set "RK=%USERPROFILE%\.reconkit\bin\reconkit.cmd"
if exist "%RK%" goto run
set "RK=%LOCALAPPDATA%\Microsoft\WindowsApps\reconkit.cmd"
if exist "%RK%" goto run
set "RK=reconkit"

:run
"%RK%" --install-deps --with-optional --no-color
"%RK%" --check-deps --no-color
echo [+] Done. Try: reconkit
echo     If this terminal cannot see reconkit yet, open a new CMD/PowerShell window.
