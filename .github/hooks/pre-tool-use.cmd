@echo off
        setlocal
        set "SCRIPT_DIR=%~dp0"
        where py >nul 2>nul
        if not errorlevel 1 (
          py -3 "%SCRIPT_DIR%pre-tool-use.py" %*
          exit /b %ERRORLEVEL%
        )
        where python >nul 2>nul
        if not errorlevel 1 (
          python "%SCRIPT_DIR%pre-tool-use.py" %*
          exit /b %ERRORLEVEL%
        )
        python3 "%SCRIPT_DIR%pre-tool-use.py" %*
        exit /b %ERRORLEVEL%
