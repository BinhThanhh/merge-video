@echo off
cd /d "%~dp0"
title Build MergeVideoTool.exe

echo ======================================================================
echo           BUILDING MERGEVIDEOTOOL.EXE (PYARMOR + PYINSTALLER)
echo ======================================================================
echo.

REM 0. Select Python 3.10
set "PYTHON_EXE=C:\Users\binhm\AppData\Local\Programs\Python\Python310\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

REM 1. Stop running instance if any
echo [1/4] Stopping running MergeVideoTool.exe processes...
taskkill /f /im MergeVideoTool.exe >nul 2>&1

REM 2. Obfuscate app.py with PyArmor
echo [2/4] Obfuscating app.py with PyArmor (Python 3.10)...
"%PYTHON_EXE%" -m pyarmor.cli gen -O obf_build app.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyArmor obfuscation failed!
    pause
    exit /b %ERRORLEVEL%
)

REM 3. Bundle single-file executable with PyInstaller
echo [3/4] Packaging MergeVideoTool.exe with PyInstaller (Python 3.10)...
"%PYTHON_EXE%" -m PyInstaller --noconfirm MergeVideoTool.spec
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] PyInstaller build failed!
    pause
    exit /b %ERRORLEVEL%
)

REM 4. Copy executable to project root
echo [4/4] Copying MergeVideoTool.exe to project root...
copy /y "dist\MergeVideoTool.exe" "MergeVideoTool.exe" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to copy MergeVideoTool.exe!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ======================================================================
echo  DONE! MergeVideoTool.exe is ready in the project root folder.
echo ======================================================================
echo.
pause
