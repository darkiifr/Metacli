@echo off
REM MetaCLI Modify Tool
REM This batch file launches the MetaCLI installer in modify mode

echo MetaCLI Modify Tool
echo ==================
echo.
echo This will allow you to modify your existing MetaCLI installation.
echo You can add or remove components like shortcuts and PATH entries.
echo Press any key to continue or close this window to cancel.
pause >nul

echo.
echo Starting modify process...
python "%~dp0metacli_installer.py" --modify

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Modify process encountered an error.
    echo Please check the installation log for details.
    pause
)