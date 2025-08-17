@echo off
REM MetaCLI Uninstall Tool
REM This batch file launches the MetaCLI installer in uninstall mode

echo MetaCLI Uninstall Tool
echo =====================
echo.
echo This will completely remove MetaCLI from your system.
echo WARNING: This action cannot be undone!
echo.
echo Press any key to continue or close this window to cancel.
pause >nul

echo.
echo Starting uninstall process...
python "%~dp0metacli_installer.py" --uninstall

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Uninstall process encountered an error.
    echo Please check the installation log for details.
    pause
)