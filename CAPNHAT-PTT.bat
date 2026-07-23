@echo off
REM Cap nhat gia PTT Global (chay hang thang qua Task Scheduler).
REM Neu cookie PHPSESSID het han, script se BAO LOI va KHONG ghi de du lieu cu.
cd /d "%~dp0"
set PYTHONUTF8=1
"C:\Users\charl\AppData\Local\Python\pythoncore-3.14-64\python.exe" thu_gia_pttglobal.py >> "%~dp0ptt_update.log" 2>&1
echo [%date% %time%] exit=%errorlevel% >> "%~dp0ptt_update.log"
