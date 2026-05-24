@echo off
        setlocal
        set "SCRIPT_DIR=%~dp0"
        if defined WAVEFOUNDRY_TOOL_VENV (
          set "PYTHON=%WAVEFOUNDRY_TOOL_VENV%\Scripts\python.exe"
        ) else (
          set "PYTHON=%USERPROFILE%\.wavefoundry\venv\Scripts\python.exe"
        )
        if not exist "%PYTHON%" set "PYTHON=python3"
        "%PYTHON%" "%SCRIPT_DIR%pre-edit.py" %*
        exit /b %ERRORLEVEL%
