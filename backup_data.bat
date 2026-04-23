@echo off
chcp 65001 >nul
echo ========================================
echo   足球预测项目 - 数据备份脚本
echo ========================================
echo.

set BACKUP_DIR=%~dp0backups
set DATE_STR=%date:~0,4%%date:~5,2%%date:~8,2%

:: 创建备份目录
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

:: 备份文件名
set SPORTTERY_BACKUP=sporttery_data_%DATE_STR%.zip
set TEMPLATE_BACKUP=analysis_templates_%DATE_STR%.zip
set DATA_BACKUP=data_all_%DATE_STR%.zip

echo [1/3] 正在压缩竞彩数据 (sporttery_data/)...
powershell -Command "Compress-Archive -Path 'sporttery_data\*.json' -DestinationPath '%BACKUP_DIR%\%SPORTTERY_BACKUP%' -Force"
echo       完成: %BACKUP_DIR%\%SPORTTERY_BACKUP%

echo.
echo [2/3] 正在压缩分析模板 (分析模板/)...
powershell -Command "Compress-Archive -Path '分析模板\*' -DestinationPath '%BACKUP_DIR%\%TEMPLATE_BACKUP%' -Force"
echo       完成: %BACKUP_DIR%\%TEMPLATE_BACKUP%

echo.
echo [3/3] 正在压缩核心数据文件...
powershell -Command "Compress-Archive -Path '_scores.json','data\*.json' -DestinationPath '%BACKUP_DIR%\%DATA_BACKUP%' -Force"
echo       完成: %BACKUP_DIR%\%DATA_BACKUP%

echo.
echo ========================================
echo   备份完成！
echo ========================================
echo.
echo 备份目录: %BACKUP_DIR%
echo.
powershell -Command "Get-ChildItem '%BACKUP_DIR%' | Select-Object Name,@{N='大小(MB)';E={[math]::Round($_.Length/1MB,2)}} | Format-Table -AutoSize"

echo.
echo ========================================
echo   恢复数据方法：
echo ========================================
echo.
echo 竞彩数据:  解压 %SPORTTERY_BACKUP% 到 sporttery_data/
echo 分析模板: 解压 %TEMPLATE_BACKUP% 到 分析模板/
echo 核心数据: 解压 %DATA_BACKUP% 到项目根目录
echo.
echo 示例命令:
echo   powershell Expand-Archive %SPORTTERY_BACKUP% -DestinationPath sporttery_data
echo.
pause
