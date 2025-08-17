@echo off
REM MetaCLI Repair Tool
REM This batch file launches the MetaCLI installer in repair mode

echo MetaCLI Repair Tool
echo ==================
echo.
echo This will repair your existing MetaCLI installation.
echo Press any key to continue or close this window to cancel.
pause >nul

echo.
echo Starting repair process...
python "%~dp0metacli_installer.py" --repair

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Repair process encountered an error.
    echo Please check the installation log for details.
    pause
)