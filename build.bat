@echo off
REM StockMonitor 本地构建脚本
REM 用法: build.bat [version]
REM   version: 可选版本号，如 0.1.0

setlocal enabledelayedexpansion

REM 设置版本号
if "%~1"=="" (
    set VERSION=0.1.0
) else (
    set VERSION=%~1
)

echo ========================================
echo StockMonitor Build Script
echo Version: %VERSION%
echo ========================================

REM 检查 uv 是否安装
where uv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] uv not found. Please install uv first.
    echo Run: pip install uv
    exit /b 1
)

REM 检查 ISCC 是否安装
where ISCC >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [WARN] Inno Setup (ISCC) not found. Skipping installer build.
    echo To build installer, install Inno Setup 6 from https://jrsoftware.org/isinfo.php
    set BUILD_INSTALLER=0
) else (
    set BUILD_INSTALLER=1
)

echo.
echo [1/3] Installing dependencies...
uv sync --group dev

echo.
echo [2/3] Building with PyInstaller...
uv run pyinstaller stockmonitor.spec --noconfirm
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller build failed.
    exit /b 1
)

if %BUILD_INSTALLER%==1 (
    echo.
    echo [3/3] Building installer with Inno Setup...
    set STOCKMONITOR_VERSION=%VERSION%
    ISCC installer/stockmonitor.iss
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Inno Setup build failed.
        exit /b 1
    )
    echo.
    echo ========================================
    echo Build completed successfully!
    echo PyInstaller output: dist\StockMonitor\
    echo Installer: dist\StockMonitor-Setup.exe
    echo ========================================
) else (
    echo.
    echo ========================================
    echo Build completed successfully!
    echo PyInstaller output: dist\StockMonitor\
    echo Installer: skipped (Inno Setup not installed)
    echo ========================================
)

endlocal
