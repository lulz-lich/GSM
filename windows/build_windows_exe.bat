@echo off
title GSM Builder

echo ==============================
echo GSM Windows Build Script
echo ==============================

echo.
echo [1/5] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo Python not found. Install Python and add it to PATH.
    pause
    exit /b
)

echo.
echo [2/5] Installing PyInstaller...
python -m pip install --upgrade pip
python -m pip install pyinstaller

echo.
echo [3/5] Checking required files...

if not exist gsm_windows.py (
    echo gsm_windows.py not found!
    pause
    exit /b
)

if not exist rclone.exe (
    echo rclone.exe not found!
    pause
    exit /b
)

if not exist ludusavi.exe (
    echo ludusavi.exe not found!
    pause
    exit /b
)

echo.
echo [4/5] Building EXE...

python -m PyInstaller ^
--noconfirm ^
--onefile ^
--windowed ^
--name GSM ^
--add-binary "rclone.exe;." ^
--add-binary "ludusavi.exe;." ^
gsm_windows.py

if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b
)

echo.
echo [5/5] Build completed!
echo Your executable is here:
echo dist\GSM.exe

pause
