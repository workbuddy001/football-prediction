@echo off
taskkill /F /IM python.exe 2>nul
timeout /t 3 /nobreak >nul
cd /d "d:\work\workbuddy\足球预测"
start /B python sporttery_web.py
start /B python football_web.py 8889
echo Services restarted
