@echo off
chcp 65001 >nul
echo ======================================
echo   打包程序为EXE文件
echo ======================================
echo.
echo 正在打包，请稍候...
echo.

pyinstaller build.spec --clean

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ 打包完成！
    echo.
    echo 生成的exe文件位于: dist\百度一刻相册下载器.exe
    echo.
    explorer dist
) else (
    echo.
    echo ✗ 打包失败
    echo.
)

pause
