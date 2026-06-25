@echo off
REM Wavefoundry operator CLI -- .wavefoundry\bin\wf.cmd (wave 1p7tz)
setlocal
set "REPO_ROOT=%~dp0..\.."
cd /d "%REPO_ROOT%"
python "%REPO_ROOT%\.wavefoundry\framework\scripts\wf_cli.py" %*
exit /b %ERRORLEVEL%
