@echo off
REM SV Converter v2.0 - Запуск GUI приложения на Windows

title SV Converter v2.0 - GUI Application
cd /d "%~dp0"

echo.
echo ===============================================
echo   SV Converter v2.0 - GUI приложение
echo ===============================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] ОШИБКА: Python не найден!
    echo [*] Установите Python с https://www.python.org/
    echo [*] При установке отметьте "Add Python to PATH"
    pause
    exit /b 1
)

echo [+] Python найден
python --version

echo [*] Запуск SV Converter GUI...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo [!] ОШИБКА при запуске приложения
    pause
    exit /b 1
)

pause
