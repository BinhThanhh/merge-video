@echo off
chcp 65001 >nul
title MergeVideoTool - Tool Ghep Video & Chen Chu Nen Trang
 
echo ======================================================================
echo           🎬 MERGEVIDEOTOOL - NATIVE WINDOW (ENCRYPTED)
echo ======================================================================
echo  Dang khoi dong ung dung Native Window (khong can mo trinh duyet)...
echo.

if exist "MergeVideoTool.exe" (
    start "" "MergeVideoTool.exe"
) else if exist "dist\MergeVideoTool.exe" (
    start "" "dist\MergeVideoTool.exe"
) else if exist "CapCutStudio.exe" (
    start "" "CapCutStudio.exe"
) else (
    if exist "C:\Users\binhm\AppData\Local\Programs\Python\Python310\python.exe" (
        "C:\Users\binhm\AppData\Local\Programs\Python\Python310\python.exe" app.py
    ) else (
        python app.py
    )
)
