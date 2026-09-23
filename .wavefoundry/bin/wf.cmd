@echo off
REM Wavefoundry operator CLI -- .wavefoundry\bin\wf.cmd (wave 1p7tz)
setlocal
set "REPO_ROOT=%~dp0..\.."
cd /d "%REPO_ROOT%"
where.exe python3 >nul 2>nul
if errorlevel 1 goto python_missing
python3 "%REPO_ROOT%\.wavefoundry\framework\scripts\wf_cli.py" %*
set "WF_EXIT=%ERRORLEVEL%"
if not "%WF_EXIT%"=="0" (
  echo Wavefoundry command failed. If Python could not start, diagnose this workstation: 1>&2
  echo powershell -NoProfile -File "%REPO_ROOT%\.wavefoundry\framework\scripts\diagnose_python.ps1" 1>&2
)
exit /b %WF_EXIT%
:python_missing
echo Wavefoundry: required python3 command was not found on PATH. Setup was not started. 1>&2
echo Candidate python command paths below are discovery only, not verified interpreters: 1>&2
where.exe python 1>&2 2>nul
echo Run bounded diagnosis without Python or MCP: 1>&2
echo powershell -NoProfile -File "%REPO_ROOT%\.wavefoundry\framework\scripts\diagnose_python.ps1" 1>&2
echo If policy blocks diagnosis, give IT the command/path/error; do not bypass policy or reseed this checkout. 1>&2
exit /b 2
