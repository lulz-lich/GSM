@echo off
title GSM Uninstaller

echo ============================
echo GSM Uninstaller
echo ============================

echo.
echo Removing GSM config...
if exist "%APPDATA%\GSM" (
    rmdir /s /q "%APPDATA%\GSM"
    echo GSM config removed.
) else (
    echo GSM config folder not found.
)

echo.
echo Removing local backup library...
if exist "%USERPROFILE%\Documents\GSM" (
    rmdir /s /q "%USERPROFILE%\Documents\GSM"
    echo Local backup library removed.
) else (
    echo Local backup library not found.
)

echo.
echo NOTE:
echo rclone global config in AppData\Roaming\rclone was not removed.
echo Remove it manually if you want to fully disconnect cloud accounts.

pause
