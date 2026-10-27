@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Installing python-docx (only needed for build_docx)...
python -m pip install python-docx
echo.
echo Done. If you see "Successfully installed", you can close this window.
pause
