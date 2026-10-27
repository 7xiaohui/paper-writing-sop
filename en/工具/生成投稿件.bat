@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist output mkdir output

set PY=
where python >nul 2>nul && set PY=python
if not "%PY%"=="" goto GOTPY
where py >nul 2>nul && set PY=py -3
if not "%PY%"=="" goto GOTPY
echo [ERROR] Python not found.
goto END

:GOTPY
%PY% scripts\build_docx.py
echo.
echo 文件在 output\docx\ 目录
echo 请打开每一份确认能正常打开；打不开请把报错发我

:END
pause
