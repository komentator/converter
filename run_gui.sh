#!/bin/bash
# SV Converter v2.0 - Запуск GUI приложения на Linux/macOS

cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "  SV Converter v2.0 - GUI приложение"
echo "========================================"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "[!] ОШИБКА: Python3 не найден!"
    echo "[*] Установите Python 3.7+ с https://www.python.org/"
    exit 1
fi

echo "[+] Python найден:"
python3 --version

echo "[*] Запуск SV Converter GUI..."
echo ""

python3 main.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[!] ОШИБКА при запуске приложения"
    exit 1
fi
