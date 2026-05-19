@echo off
REM Canonical upgrade-wavefoundry launcher — .wavefoundry\bin\upgrade-wavefoundry.bat
REM Resolves repo root from this script's location and delegates to upgrade_wavefoundry.py.
setlocal
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%..\.."
cd /d "%REPO_ROOT%"
python ".wavefoundry\framework\scripts\upgrade_wavefoundry.py" %*
