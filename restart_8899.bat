@echo off
chcp 65001 > nul
title 重启 sporttery_web (端口 8899)

echo 正在关闭 8899 端口的进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8899" ^| findstr "LISTENING"') do (
    echo 关闭进程 PID: %%a
    taskkill /F /PID %%a > nul 2>&1
)

echo 等待 2 秒...
timeout /t 2 /nobreak > nul

echo 正在启动 sporttery_web.py...
cd /d "d:\work\workbuddy\足球预测"
start "" python sporttery_web.py

echo 等待服务启动...
timeout /t 5 /nobreak > nul

echo 检查端口状态...
netstat -ano | findstr ":8899" | findstr "LISTENING"
if %errorlevel%==0 (
    echo.
    echo ✅ sporttery_web 已成功启动！
    echo 访问地址: http://127.0.0.1:8899
) else (
    echo.
    echo ❌ 启动可能失败，请检查 sporttery_web.py 是否有错误
)

echo.
pause
