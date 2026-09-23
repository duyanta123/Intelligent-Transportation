@echo off
chcp 65001 >nul
rem ============================================================
rem stop.bat - 停止本项目占用 8000 和 5173 端口的服务进程
rem 原理: 按端口找到 PID 后 taskkill, 仅影响这两个端口的监听进程
rem ============================================================
setlocal EnableDelayedExpansion
echo 正在停止后端 8000 与前端 5173 ...
for %%P in (8000 5173) do (
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%%P " ^| findstr "LISTENING"') do (
        echo   端口 %%P -^> PID %%a
        taskkill /PID %%a /T /F >nul 2>&1
    )
)
echo [完成] 已停止。
pause
endlocal
