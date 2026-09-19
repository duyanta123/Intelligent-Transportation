@echo off
chcp 65001 >nul
rem ============================================================
rem reset-db.bat —— 一键还原演示数据
rem 作用：重新导入 sql\init.sql + sql\seed.sql，把数据库恢复到种子状态
rem 用途：答辩演示前还原数据；数据库被测试弄脏后快速重置
rem 注意：连接参数从 backend\.env 读取，禁止在此硬编码密码
rem ============================================================
setlocal EnableDelayedExpansion

set "ROOT=%~dp0"
set "MYSQL_EXE=C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
set "ENV_FILE=%ROOT%backend\.env"
set "INIT_SQL=%ROOT%sql\init.sql"
set "SEED_SQL=%ROOT%sql\seed.sql"

rem ---- 前置检查 ----
if not exist "%MYSQL_EXE%" (
    echo [错误] 未找到 MySQL 客户端：%MYSQL_EXE%
    exit /b 1
)
if not exist "%INIT_SQL%" (
    echo [错误] 未找到 %INIT_SQL% —— 请先完成 Phase 1 生成 sql 文件
    exit /b 1
)
if not exist "%SEED_SQL%" (
    echo [错误] 未找到 %SEED_SQL% —— 请先完成 Phase 1 生成 sql 文件
    exit /b 1
)

rem ---- 从 backend\.env 读取连接参数（PowerShell 解析，规避 CR 残留）----
if exist "%ENV_FILE%" (
    for /f "usebackq delims=" %%a in (`powershell -NoProfile -Command "Get-Content -LiteralPath '%ENV_FILE%' ^| Where-Object { $_ -match '^[A-Za-z_]+=' } ^| ForEach-Object { $kv = $_ -split '=', 2; ($kv[0].Trim() + '=' + $kv[1].Trim()) }"`) do set "%%a"
)

rem 缺省值
if not defined DB_HOST set "DB_HOST=127.0.0.1"
if not defined DB_PORT set "DB_PORT=3306"
if not defined DB_USER set "DB_USER=root"
if not defined DB_NAME set "DB_NAME=smart_traffic"

if not defined DB_PASSWORD (
    set /p "DB_PASSWORD=未在 backend\.env 中找到 DB_PASSWORD，请输入 MySQL %DB_USER% 密码: "
)

rem ---- 二次确认：该操作会清空并重建整个数据库 ----
echo.
echo 即将清空并重建数据库 [%DB_NAME%]（%DB_HOST%:%DB_PORT%），所有业务数据将被重置为种子数据。
choice /c YN /n /m "确认继续？(Y=是 / N=否): "
if errorlevel 2 (
    echo 已取消。
    exit /b 0
)

rem ---- 执行导入（用 MYSQL_PWD 避免密码出现在命令行）----
set "MYSQL_PWD=%DB_PASSWORD%"

echo.
echo [1/2] 导入 init.sql（建库建表）...
"%MYSQL_EXE%" -h%DB_HOST% -P%DB_PORT% -u%DB_USER% -e "source %ROOT%sql/init.sql"
if errorlevel 1 (
    echo [错误] init.sql 导入失败，请检查数据库连接与密码。
    exit /b 1
)

echo [2/2] 导入 seed.sql（种子数据）...
"%MYSQL_EXE%" -h%DB_HOST% -P%DB_PORT% -u%DB_USER% %DB_NAME% -e "source %ROOT%sql/seed.sql"
if errorlevel 1 (
    echo [错误] seed.sql 导入失败。
    exit /b 1
)

echo.
echo [完成] 数据库 %DB_NAME% 已还原为种子状态。
endlocal
