@echo off
title Big Agent Server
cd /d "%~dp0"

:: 激活虚拟环境
call ..\venv\Scripts\activate.bat

:: 启动服务器
echo ========================================
echo   Big Agent — 自学型电脑控制智能体
echo ========================================
echo.
echo 正在启动服务器...
echo.

start /B python main.py

:: 等待服务器就绪
timeout /t 3 /nobreak >nul

:: 打开浏览器
start http://127.0.0.1:8000

cls
echo ========================================
echo   Big Agent 已启动！
echo ========================================
echo.
echo   http://127.0.0.1:8000
echo.
echo ========================================
echo 关闭此窗口不会停止服务器。
echo 要停止请运行 stop_server.bat
echo.
pause >nul
