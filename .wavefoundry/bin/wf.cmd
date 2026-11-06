@echo off
REM Wavefoundry operator CLI -- .wavefoundry\bin\wf.cmd (wave 1p7tz)
setlocal
set "REPO_ROOT=%~dp0..\.."
cd /d "%REPO_ROOT%"
where.exe python3 >nul 2>nul
if errorlevel 1 goto python_missing
set "WF_PYTHON3="
for /f "delims=" %%I in ('where.exe python3 2^>nul') do if not defined WF_PYTHON3 set "WF_PYTHON3=%%I"
if /i "%WF_PYTHON3%"=="%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" goto python_alias_probe
goto python_launch
:python_alias_probe
python3 -c "import sys" >nul 2>nul
if "%ERRORLEVEL%"=="0" goto python_launch
echo Wavefoundry: the WindowsApps python3 App execution alias cannot run Python. Disable the Python/Python3 App execution aliases in Settings and put a real Python 3.11 or newer python3 on PATH, then retry. 1>&2
exit /b 2
:python_launch
python3 "%REPO_ROOT%\.wavefoundry\framework\scripts\wf_cli.py" %*
set "WF_EXIT=%ERRORLEVEL%"
if "%WF_EXIT%"=="0" exit /b 0
python3 -c "import sys" >nul 2>nul
if "%ERRORLEVEL%"=="0" exit /b %WF_EXIT%
echo Wavefoundry: python3 could not start. Diagnose this workstation: 1>&2
echo powershell -NoProfile -File "%REPO_ROOT%\.wavefoundry\framework\scripts\diagnose_python.ps1" 1>&2
exit /b %WF_EXIT%
:python_missing
echo Wavefoundry: required python3 command was not found on PATH. Setup was not started. 1>&2
echo Candidate python command paths below are discovery only, not verified interpreters: 1>&2
where.exe python 1>&2 2>nul
echo Run bounded diagnosis without Python or MCP: 1>&2
echo powershell -NoProfile -File "%REPO_ROOT%\.wavefoundry\framework\scripts\diagnose_python.ps1" 1>&2
echo If policy blocks diagnosis, give IT the command/path/error; do not bypass policy or reseed this checkout. 1>&2
exit /b 2
