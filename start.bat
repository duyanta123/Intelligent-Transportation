@echo off
chcp 65001 >nul
rem ============================================================
rem start.bat —— 一键拉起后端(8000)与前端(5173)
rem 依赖：backend\venv 已创建、backend\.env 已配置、MySQL/Redis 服务运行中
rem ============================================================
setlocal EnableDelayedExpansion
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "VENV_PY=%BACKEND%\venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo [错误] 未找到后端虚拟环境：%VENV_PY%
    echo 请先执行: cd backend ^&^& python -m venv venv ^&^& venv\Scripts\pip install -r requirements.txt
    pause & exit /b 1
)
if not exist "%FRONTEND%\node_modules" (
    echo [提示] 前端依赖未安装，正在执行 npm install ...
    pushd "%FRONTEND%" && call npm install && popd
)

echo [1/2] 启动后端 http://127.0.0.1:8000  (接口文档 /docs)
start "smart-traffic-backend" cmd /k "cd /d %BACKEND% && venv\Scripts\python.exe -m uvicorn app.main:app --port 8000"

echo [2/2] 启动前端 http://localhost:5173
start "smart-traffic-frontend" cmd /k "cd /d %FRONTEND% && npm run dev"

rem 等待服务就绪后自动打开浏览器
timeout /t 8 /nobreak >nul
start http://localhost:5173

echo.
echo [完成] 两个服务已在独立窗口运行，关闭对应窗口或运行 stop.bat 可停止。
echo 默认浏览器已打开登录页。测试账号：admin / officer / user，密码均为 123456
pause
endlocal
