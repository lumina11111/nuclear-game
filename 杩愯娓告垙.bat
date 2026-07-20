@echo off
chcp 65001 >nul
cd /d %~dp0
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python 启动游戏.py
pause
