@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/4] 安装网页构建工具...
py -m pip install --upgrade pygbag==0.9.3 fonttools qrcode[pil]
if errorlevel 1 goto :error

echo [2/4] 准备中文字体子集...
py tools\prepare_web_fonts.py
if errorlevel 1 goto :error

echo [3/4] 构建 Pygbag 网页版...
py -m pygbag --build --archive --ume_block 1 --title "核境造物" .
if errorlevel 1 goto :error

echo [4/4] 构建完成。
echo 网页目录：build\web
echo itch.io 上传包：build\web.zip
pause
exit /b 0

:error
echo 构建失败，请保留窗口中的错误信息。
pause
exit /b 1
