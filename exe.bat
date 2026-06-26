@echo off
setlocal

REM Всегда работаем из папки, где лежит BAT
cd /d "%~dp0"

echo.
echo ============================================
echo      SV Converter - EXE Builder
echo ============================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не найден.
    pause
    exit /b 1
)

echo [OK] Python найден.

REM Проверка pip
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip не найден.
    pause
    exit /b 1
)

echo [*] Обновление PyInstaller...
python -m pip install --upgrade pyinstaller

if errorlevel 1 (
    echo [ERROR] Не удалось установить PyInstaller.
    pause
    exit /b 1
)

REM Удаляем старую сборку
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo [*] Сборка EXE...
echo.

python -m PyInstaller --clean sv_converter.spec

if errorlevel 1 (
    echo.
    echo ============================================
    echo            СБОРКА НЕ УДАЛАСЬ
    echo ============================================
    pause
    exit /b 1
)

echo.
echo ============================================
echo          СБОРКА ЗАВЕРШЕНА
echo ============================================

if exist "dist\SV_Converter\SV_Converter.exe" (
    echo.
    echo Готовый файл:
    echo %CD%\dist\SV_Converter\SV_Converter.exe
) else (
    echo.
    echo Проверьте папку dist
)

echo.
pause