@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if not exist output mkdir output
set LOG=output\run_log.txt

echo ============================================ > "%LOG%"
echo  SSCI SOP checker   %DATE% %TIME% >> "%LOG%"
echo ============================================ >> "%LOG%"

set PY=
where python >nul 2>nul && set PY=python
if not "%PY%"=="" goto GOTPY
where py >nul 2>nul && set PY=py -3
if not "%PY%"=="" goto GOTPY
echo [ERROR] Python not found.
echo         Install Python 3 from python.org and tick "Add Python to PATH".
echo [ERROR] Python not found. >> "%LOG%"
goto END

:GOTPY
echo [Python] %PY%
%PY% --version >> "%LOG%" 2>&1

echo. >> "%LOG%"
echo ==== 1/5 counts ==== >> "%LOG%"
%PY% scripts\check_counts.py >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo ==== 2/5 terms ==== >> "%LOG%"
%PY% scripts\check_terms.py >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo ==== 3/5 refs ==== >> "%LOG%"
%PY% scripts\check_refs.py >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo ==== 4/5 consistency ==== >> "%LOG%"
%PY% scripts\check_consistency.py >> "%LOG%" 2>&1
echo. >> "%LOG%"
echo ==== 5/5 clean ==== >> "%LOG%"
%PY% scripts\check_clean.py >> "%LOG%" 2>&1

type "%LOG%"

:END
echo.
echo Done. Reports are in output\
echo If something looks wrong, send output\run_log.txt
pause
