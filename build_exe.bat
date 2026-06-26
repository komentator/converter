@echo off
REM Скрипт для сборки SV Converter в EXE на Windows
REM Требует: Python 3.7+ и PyInstaller

echo.
echo ============================================
echo  SV Converter - Build EXE for Windows
echo ============================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] ОШИБКА: Python не найден!
    echo [*] Убедитесь, что Python установлен и добавлен в PATH
    echo [*] Скачайте Python с: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [+] Python найден
python --version

REM Установка PyInstaller
echo.
echo [*] Установка PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 (
    echo [!] ОШИБКА при установке PyInstaller
    echo [*] Попробуйте вручную: pip install pyinstaller
    pause
    exit /b 1
)

echo [+] PyInstaller установлен

REM Сборка EXE
echo.
echo [*] Сборка EXE файла...
echo [*] Это может занять 1-2 минуты...
echo.

pyinstaller sv_converter.spec

if errorlevel 1 (
    echo.
    echo [!] ОШИБКА при сборке!
    pause
    exit /b 1
)

echo.
echo ============================================
echo  [+] УСПЕШНО!
echo ============================================
echo.
echo [*] EXE файл находится в папке: dist\SV_Converter\
echo [*] Запустите: dist\SV_Converter\SV_Converter.exe
echo.
echo [*] Для однофайлового EXE запустите:
echo     pyinstaller sv_converter.spec --onefile
echo.

pause
