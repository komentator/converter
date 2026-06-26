#!/bin/bash
# Скрипт для сборки SV Converter на Linux/macOS
# Требует: Python 3.7+ и PyInstaller

echo ""
echo "============================================"
echo "  SV Converter - Build for Linux/macOS"
echo "============================================"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "[!] ОШИБКА: Python3 не найден!"
    echo "[*] Установите Python 3.7+ с https://www.python.org/"
    exit 1
fi

echo "[+] Python найден:"
python3 --version

# Установка PyInstaller
echo ""
echo "[*] Установка PyInstaller..."
pip3 install pyinstaller --quiet

if [ $? -ne 0 ]; then
    echo "[!] ОШИБКА при установке PyInstaller"
    echo "[*] Попробуйте вручную: pip3 install pyinstaller"
    exit 1
fi

echo "[+] PyInstaller установлен"

# Сборка (для Linux/macOS не создаётся .exe, но можно собрать исполняемый файл)
echo ""
echo "[*] Сборка исполняемого файла..."
echo "[*] Это может занять 1-2 минуты..."
echo ""

# Для Linux/macOS собираем как приложение (не .exe)
pyinstaller sv_converter.spec --onefile

if [ $? -ne 0 ]; then
    echo ""
    echo "[!] ОШИБКА при сборке!"
    exit 1
fi

echo ""
echo "============================================"
echo "  [+] УСПЕШНО!"
echo "============================================"
echo ""
echo "[*] Исполняемый файл находится в: dist/SV_Converter"
echo "[*] Запустите: ./dist/SV_Converter/SV_Converter"
echo ""
echo "[*] Для создания одного файла:"
echo "    pyinstaller sv_converter.spec --onefile"
echo ""
