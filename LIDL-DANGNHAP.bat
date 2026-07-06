@echo off
chcp 65001 >nul
title Dang nhap Lidl Plus (1 lan duy nhat)
cd /d "%~dp0"
python lidl_login.py
echo.
pause
