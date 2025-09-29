@echo off
chcp 65001 >nul
title AI 客服管理工具

:menu
echo.
echo ========================================
echo      🤖 AI 客服統一管理工具
echo ========================================
echo.
echo 請選擇操作：
echo.
echo [1] 完整安裝設定 (推薦新用戶)
echo [2] 檢查環境依賴
echo [3] 匯入 Excel 資料
echo [4] 重建向量資料庫
echo [5] 測試 AI 客服
echo [6] 檢查服務狀態
echo [0] 退出
echo.
set /p choice=請輸入選項 (0-6):

if "%choice%"=="1" goto setup
if "%choice%"=="2" goto check
if "%choice%"=="3" goto import
if "%choice%"=="4" goto rebuild
if "%choice%"=="5" goto test
if "%choice%"=="6" goto status
if "%choice%"=="0" goto exit
goto menu

:setup
echo.
echo 執行完整安裝設定...
python ai_service_manager.py setup
echo.
echo 完成後請重新啟動 Django 服務：
echo python manage.py runserver 0.0.0.0:8000
pause
goto menu

:check
echo.
echo 檢查環境依賴...
python ai_service_manager.py check
pause
goto menu

:import
echo.
echo 匯入 Excel 資料...
python ai_service_manager.py import
pause
goto menu

:rebuild
echo.
echo 重建向量資料庫...
python ai_service_manager.py rebuild
pause
goto menu

:test
echo.
echo 測試 AI 客服 (需要 Django 服務運行)...
python ai_service_manager.py test
pause
goto menu

:status
echo.
echo 檢查服務狀態...
python ai_service_manager.py status
pause
goto menu

:exit
echo.
echo 再見！
exit