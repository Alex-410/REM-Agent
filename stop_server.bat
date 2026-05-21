@echo off
title Big Agent Server Stopper
echo 正在停止 Big Agent 服务器...
cd /d "%~dp0"

:: 查找并终止 main.py 进程
for /f "tokens=2 delims=," %%a in ('wmic process where "commandline like '%%main.py%%' and commandline like '%%uvicorn%%'" get processid /format:csv 2^>nul') do (
    if not "%%a"=="" (
        taskkill /f /pid %%a 2>nul
        echo 已终止进程 PID: %%a
    )
)

:: 也终止 Python 中运行 uvicorn 的进程
for /f "tokens=2 delims=," %%a in ('wmic process where "name='python.exe' and commandline like '%%uvicorn%%'" get processid /format:csv 2^>nul') do (
    if not "%%a"=="" (
        taskkill /f /pid %%a 2>nul
    )
)

timeout /t 2 /nobreak >nul
echo.
echo 服务器已停止。
pause
