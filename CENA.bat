@echo off
chcp 65001 >nul
title Cena Checker - dong cua so nay de tat
cd /d "%~dp0"
python app.py
pause
