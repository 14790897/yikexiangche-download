@echo off
chcp 65001 >nul
echo ======================================
echo   百度一刻相册下载器 - GUI版本
echo ======================================
echo.

python gui_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo 错误: 程序运行失败
    echo 请确保已安装依赖: pip install -r requirements-gui.txt
    pause
)
