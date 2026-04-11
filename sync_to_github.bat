@echo off
chcp 65001 >nul
echo ============================================
echo   足球预测项目 - 一键同步到 GitHub
echo ============================================

cd /d "d:\work\workbuddy\足球预测"

:: 检查是否有变更
git diff --quiet --exit-code
if %errorlevel%==0 (
    echo [✓] 没有新的变更，无需推送
    pause
    exit /b 0
)

echo.
echo 正在提交所有变更...

:: 添加所有文件（排除.gitignore中的）
git add -A

:: 生成带时间的commit message
for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set DATE=%%c-%%a-%%b
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set TIME=%%a:%%b

set COMMIT_MSG=每日更新: %DATE% %TIME%

:: 提交
git commit -m "%COMMIT_MSG%"

if %errorlevel% neq 0 (
    echo [✗] commit 失败！
    pause
    exit /b 1
)

echo.
echo 正在推送到 GitHub...

:: 推送
git push origin main

if %errorlevel% equ 0 (
    echo.
    echo [✓] 推送成功！
) else (
    echo.
    echo [✗] 推送失败，请检查网络或仓库地址
)

pause
