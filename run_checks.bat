@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY="
where python >nul 2>nul && set "PY=python"
if defined PY goto RUN
where py >nul 2>nul && set "PY=py -3"
if defined PY goto RUN
echo [错误] 没有找到 Python。请到 python.org 安装 3.x，安装时勾选 "Add Python to PATH"。
echo.
pause
exit /b 1

:RUN
echo ============================================
echo  论文写作 SOP · 本地检查
echo ============================================
echo.
%PY% tests\verify.py
set "RC1=%ERRORLEVEL%"
echo.
%PY% tests\scan_private.py
set "RC2=%ERRORLEVEL%"
echo.
echo ============================================
if "%RC1%%RC2%"=="00" (
  echo 全部通过。按任意键关闭窗口。
) else (
  echo 有检查未通过（verify=%RC1%  scan=%RC2%）。请把上面的内容截图或复制发给我。
)
pause >nul
