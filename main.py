# -*- coding: utf-8 -*-
"""
SV Converter v2.0 - Точка входа (GUI версия)
"""

import sys
from pathlib import Path

# Добавляем текущую папку в путь
sys.path.insert(0, str(Path(__file__).parent))

# Запускаем GUI
if __name__ == '__main__':
    try:
        from gui_main import SVConverterGUI
        import tkinter as tk
        
        print("[SV Converter] Запуск GUI приложения...")
        root = tk.Tk()
        app = SVConverterGUI(root)
        root.mainloop()
    except ImportError as e:
        print(f"[ERROR] Ошибка импорта: {e}")
        print("[INFO] Убедитесь, что все файлы на месте (converter.py, gui_main.py и т.д.)")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Ошибка при запуске: {e}")
        sys.exit(1)
