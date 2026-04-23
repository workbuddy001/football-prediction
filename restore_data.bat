@echo off
chcp 65001 >nul
echo ========================================
echo   足球预测项目 - 数据恢复脚本
echo ========================================
echo.

set BACKUP_DIR=%~dp0backups

if not exist "%BACKUP_DIR%" (
    echo [错误] 备份目录不存在: %BACKUP_DIR%
    echo 请先运行 backup_data.bat 创建备份！
    pause
    exit /b 1
)

echo 找到以下备份文件:
echo.
powershell -Command "Get-ChildItem '%BACKUP_DIR%\*.zip' | Select-Object Name,@{N='大小(MB)';E={[math]::Round($_.Length/1MB,2)}} | Format-Table -AutoSize"

echo.
echo ========================================
echo   请选择恢复选项：
echo ========================================
echo.
echo  [1] 恢复竞彩数据 (sporttery_data/)
echo  [2] 恢复分析模板 (分析模板/)
echo  [3] 恢复核心数据 (_scores.json, data/)
echo  [4] 全部恢复
echo  [0] 退出
echo.
set /p choice=请输入选项 (0-4): 

if "%choice%"=="1" goto restore_sporttery
if "%choice%"=="2" goto restore_templates
if "%choice%"=="3" goto restore_core
if "%choice%"=="4" goto restore_all
if "%choice%"=="0" exit /b

:restore_sporttery
echo.
echo 正在恢复竞彩数据...
for /f "tokens=*" %%f in ('dir /b /o-d "%BACKUP_DIR%\sporttery_data_*.zip"') do (
    echo 解压: %%f
    powershell -Command "Expand-Archive -Path '%BACKUP_DIR%\%%f' -DestinationPath 'sporttery_data' -Force"
    goto done_sporttery
)
:done_sporttery
echo 竞彩数据恢复完成！
goto end

:restore_templates
echo.
echo 正在恢复分析模板...
for /f "tokens=*" %%f in ('dir /b /o-d "%BACKUP_DIR%\analysis_templates_*.zip"') do (
    echo 解压: %%f
    powershell -Command "Expand-Archive -Path '%BACKUP_DIR%\%%f' -DestinationPath '分析模板' -Force"
    goto done_templates
)
:done_templates
echo 分析模板恢复完成！
goto end

:restore_core
echo.
echo 正在恢复核心数据...
for /f "tokens=*" %%f in ('dir /b /o-d "%BACKUP_DIR%\data_all_*.zip"') do (
    echo 解压: %%f
    powershell -Command "Expand-Archive -Path '%BACKUP_DIR%\%%f' -DestinationPath '.' -Force"
    goto done_core
)
:done_core
echo 核心数据恢复完成！
goto end

:restore_all
echo.
echo 正在恢复所有数据...
call :restore_sporttery
call :restore_templates
call :restore_core
echo.
echo ========================================
echo   全部恢复完成！
echo ========================================
goto end

:end
echo.
pause
