@echo off
echo 正在清除Python缓存...
del /s /q "__pycache__" 2>nul
rd /s /q "__pycache__" 2>nul

echo 启动 Flask 服务...
cd /d "d:\work\workbuddy\足球预测"
python sporttery_web.py
pause
