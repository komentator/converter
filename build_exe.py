# -*- coding: utf-8 -*-
"""
Скрипт для автоматической сборки SV Converter в EXE/приложение.
Использование: python build_exe.py
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description=""):
    """Выполняет команду и выводит результат"""
    if description:
        print(f"\n[*] {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[!] ОШИБКА: {result.stderr}")
            return False
        if result.stdout:
            print(result.stdout)
        return True
    except Exception as e:
        print(f"[!] Исключение: {e}")
        return False

def main():
    print("""
============================================
  SV Converter - Build Script
============================================
    """)
    
    # Проверка Python версии
    print(f"[+] Python версия: {sys.version}")
    if sys.version_info < (3, 7):
        print("[!] Требуется Python 3.7 или выше!")
        return False
    
    # Проверка, находимся ли мы в правильной директории
    if not Path("sv_converter.spec").exists():
        print("[!] ОШИБКА: sv_converter.spec не найден!")
        print("[*] Убедитесь, что вы находитесь в папке sv_converter/")
        return False
    
    print("[+] Все файлы на месте")
    
    # Установка PyInstaller
    print("\n[*] Проверка PyInstaller...")
    try:
        import PyInstaller
        print(f"[+] PyInstaller уже установлен: {PyInstaller.__version__}")
    except ImportError:
        print("[*] Установка PyInstaller...")
        if not run_command(f"{sys.executable} -m pip install pyinstaller --quiet", 
                          "Установка PyInstaller"):
            print("[!] Не удалось установить PyInstaller")
            print("[*] Попробуйте вручную: pip install pyinstaller")
            return False
    
    # Сборка
    print("\n[*] Сборка приложения...")
    print("[*] Это может занять 1-3 минуты...")
    
    cmd = f"{sys.executable} -m PyInstaller sv_converter.spec"
    if not run_command(cmd):
        print("[!] Ошибка при сборке!")
        return False
    
    # Результат
    print("""
============================================
  [+] СБОРКА УСПЕШНА!
============================================
    """)
    
    if sys.platform == "win32":
        print("[*] EXE файл находится в: dist\\SV_Converter\\SV_Converter.exe")
        print("[*] Запустите двойным кликом или из командной строки:")
        print("    dist\\SV_Converter\\SV_Converter.exe")
    else:
        print("[*] Исполняемый файл находится в: dist/SV_Converter/SV_Converter")
        print("[*] Запустите:")
        print("    ./dist/SV_Converter/SV_Converter")
    
    print("""
[*] Для создания одного файла (.exe):
    pyinstaller sv_converter.spec --onefile

[*] Размер однофайлового EXE: ~50-60 MB
    Это включает весь Python и все библиотеки
    """)
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
