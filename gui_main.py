# -*- coding: utf-8 -*-
"""
SV Converter v2.0 - GUI приложение (Tkinter)
Оконное приложение для конвертации COMTRADE → IEC 61850-9-2LE PCAP
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path
import threading
import base64
import struct
import math

try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[WARNING] matplotlib не установлен - функция просмотра будет ограничена")

# Добавляем текущую папку в путь
sys.path.insert(0, str(Path(__file__).parent))

from converter import convert, parse_cfg, guess_mapping, ROLE_ORDER, ROLE_IS_CURRENT


class SVConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SV Converter v2.0 - IEC 61850-9-2 LE")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)

        # Переменные
        self.cfg_file = None
        self.dat_file = None
        self.channels = []
        self.mapping = {role: None for role in ROLE_ORDER}
        self.pcap_data = None
        self.parsed_samples = None  # Данные для просмотра
        self.notebook = None  # Ссылка на Notebook для переключения вкладок

        # Создаем интерфейс
        self.create_widgets()
        
    def create_widgets(self):
        """Создает элементы интерфейса"""

        # Главное меню
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Открыть результат PCAP", command=self.open_pcap)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Помощь", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about)

        # Главный фрейм с вкладками
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Вкладка 1: Загрузка файлов
        frame1 = ttk.Frame(self.notebook)
        self.notebook.add(frame1, text="1. Загрузка файлов")
        self.create_file_tab(frame1)

        # Вкладка 2: Сопоставление каналов
        frame2 = ttk.Frame(self.notebook)
        self.notebook.add(frame2, text="2. Сопоставление каналов")
        self.create_mapping_tab(frame2)

        # Вкладка 3: Параметры
        frame3 = ttk.Frame(self.notebook)
        self.notebook.add(frame3, text="3. Параметры SV")
        self.create_params_tab(frame3)

        # Вкладка 4: Конвертация
        frame4 = ttk.Frame(self.notebook)
        self.notebook.add(frame4, text="4. Конвертация")
        self.create_convert_tab(frame4)

        # Вкладка 5: Просмотр (новая)
        frame5 = ttk.Frame(self.notebook)
        self.notebook.add(frame5, text="5. Просмотр данных")
        self.create_view_tab(frame5)
        
    def create_file_tab(self, parent):
        """Вкладка загрузки файлов"""
        
        mainframe = ttk.Frame(parent, padding="20")
        mainframe.pack(fill=tk.BOTH, expand=True)
        
        # .cfg файл
        ttk.Label(mainframe, text="Конфигурационный файл (.cfg):", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        cfg_frame = ttk.Frame(mainframe)
        cfg_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.cfg_label = ttk.Label(cfg_frame, text="Не выбран", foreground="red")
        self.cfg_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(cfg_frame, text="Выбрать .cfg", command=self.load_cfg).pack(side=tk.RIGHT)
        
        # .dat файл
        ttk.Label(mainframe, text="Файл данных осциллограммы (.dat):", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        dat_frame = ttk.Frame(mainframe)
        dat_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.dat_label = ttk.Label(dat_frame, text="Не выбран", foreground="red")
        self.dat_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Button(dat_frame, text="Выбрать .dat", command=self.load_dat).pack(side=tk.RIGHT)
        
        # Статус
        ttk.Separator(mainframe).pack(fill=tk.X, pady=20)
        
        self.status_label = ttk.Label(mainframe, text="Ожидание загрузки файлов...", foreground="orange")
        self.status_label.pack(anchor=tk.W)
        
    def create_mapping_tab(self, parent):
        """Вкладка сопоставления каналов"""
        
        mainframe = ttk.Frame(parent, padding="20")
        mainframe.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(mainframe, text="Сопоставление параметров SV с каналами:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 20))
        
        # Таблица
        columns = ("Параметр", "Канал", "Тип")
        self.mapping_tree = ttk.Treeview(mainframe, columns=columns, height=12, show="headings")
        
        self.mapping_tree.column("Параметр", width=150)
        self.mapping_tree.column("Канал", width=400)
        self.mapping_tree.column("Тип", width=200)
        
        self.mapping_tree.heading("Параметр", text="Параметр")
        self.mapping_tree.heading("Канал", text="Выбранный канал")
        self.mapping_tree.heading("Тип", text="Тип (ток/напряжение)")
        
        self.mapping_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Кнопки
        btn_frame = ttk.Frame(mainframe)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="🔍 Автоматическое определение", command=self.auto_detect).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="✎ Редактировать выбранный", command=self.edit_mapping).pack(side=tk.LEFT)
        
    def create_params_tab(self, parent):
        """Вкладка параметров SV"""
        
        mainframe = ttk.Frame(parent, padding="20")
        mainframe.pack(fill=tk.BOTH, expand=True)
        
        # Сетевые параметры
        ttk.Label(mainframe, text="Сетевые параметры:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        net_frame = ttk.Frame(mainframe)
        net_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.params = {}
        
        params_list = [
            ("MAC адрес", "mac", "01-0C-CD-04-00-01"),
            ("APPID (hex)", "appid", "4000"),
            ("VLANID (hex)", "vlanid", "0"),
            ("VLAN Priority", "vlan_pcp", "4"),
        ]
        
        for i, (label, key, default) in enumerate(params_list):
            ttk.Label(net_frame, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            self.params[key] = ttk.Entry(net_frame, width=30)
            self.params[key].insert(0, default)
            self.params[key].grid(row=i, column=1, sticky=tk.W, padx=(0, 20), pady=5)
        
        # ASDU параметры
        ttk.Label(mainframe, text="ASDU параметры:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(20, 10))
        
        asdu_frame = ttk.Frame(mainframe)
        asdu_frame.pack(fill=tk.X, pady=(0, 20))
        
        asdu_params = [
            ("svID", "svid", "RET61850_SV1"),
            ("confRev", "confrev", "1"),
        ]
        
        for i, (label, key, default) in enumerate(asdu_params):
            ttk.Label(asdu_frame, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            self.params[key] = ttk.Entry(asdu_frame, width=30)
            self.params[key].insert(0, default)
            self.params[key].grid(row=i, column=1, sticky=tk.W, padx=(0, 20), pady=5)
        
        # Флаг Simulation
        self.params["simulation"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(asdu_frame, text="Флаг Simulation/Test", variable=self.params["simulation"]).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Коэффициенты
        ttk.Label(mainframe, text="Коэффициенты трансформации:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(20, 10))
        
        coef_frame = ttk.Frame(mainframe)
        coef_frame.pack(fill=tk.X)
        
        coef_list = [
            ("Ктт (ток)", "ktt", "1000"),
            ("Ктн (напр)", "ktn", "1100"),
            ("K3i0 (нейтр ток)", "k3i0", "1000"),
            ("K3u0 (нейтр напр)", "k3u0", "1905.2"),
        ]
        
        for i, (label, key, default) in enumerate(coef_list):
            col = i % 2
            row = i // 2
            ttk.Label(coef_frame, text=label + ":").grid(row=row, column=col*2, sticky=tk.W, padx=(0, 10), pady=5)
            self.params[key] = ttk.Entry(coef_frame, width=20)
            self.params[key].insert(0, default)
            self.params[key].grid(row=row, column=col*2+1, sticky=tk.W, padx=(0, 20), pady=5)
        
    def create_convert_tab(self, parent):
        """Вкладка конвертации"""

        mainframe = ttk.Frame(parent, padding="20")
        mainframe.pack(fill=tk.BOTH, expand=True)

        # Прогресс
        ttk.Label(mainframe, text="Статус конвертации:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))

        self.progress = ttk.Progressbar(mainframe, mode='determinate', length=400)
        self.progress.pack(fill=tk.X, pady=(0, 20))

        self.progress_label = ttk.Label(mainframe, text="Готово к конвертации", foreground="blue")
        self.progress_label.pack(anchor=tk.W, pady=(0, 30))

        # Кнопки
        btn_frame = ttk.Frame(mainframe)
        btn_frame.pack(fill=tk.X, pady=(0, 30))

        self.convert_btn = ttk.Button(btn_frame, text="▶ Конвертировать в PCAP", command=self.start_convert)
        self.convert_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.download_btn = ttk.Button(btn_frame, text="⬇ Сохранить PCAP", command=self.save_pcap, state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.view_btn = ttk.Button(btn_frame, text="📊 Просмотр данных", command=self.goto_view_tab, state=tk.DISABLED)
        self.view_btn.pack(side=tk.LEFT)

        # Информация
        ttk.Separator(mainframe).pack(fill=tk.X, pady=20)

        ttk.Label(mainframe, text="Информация о результате:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))

        self.info_text = tk.Text(mainframe, height=10, width=80, state=tk.DISABLED)
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
    def load_cfg(self):
        """Загружает .cfg файл"""
        file = filedialog.askopenfilename(filetypes=[("CFG files", "*.cfg"), ("All files", "*.*")])
        if file:
            self.cfg_file = file
            self.cfg_label.config(text=os.path.basename(file), foreground="green")

            # Автоподтягивание .dat файла с тем же именем
            dat_file = Path(file).with_suffix('.dat')
            if dat_file.exists():
                self.dat_file = str(dat_file)
                self.dat_label.config(text=os.path.basename(self.dat_file), foreground="green")
                self.status_label.config(text="✓ CFG и DAT загружены автоматически", foreground="green")

            try:
                with open(file, 'r', encoding='utf-8') as f:
                    cfg = parse_cfg(f.read())
                self.channels = cfg['channels']
                self.update_mapping_table()
                self.auto_detect()
                if self.dat_file:
                    self.status_label.config(text=f"✓ CFG загружен ({len(self.channels)} каналов), DAT найден автоматически", foreground="green")
                else:
                    self.status_label.config(text=f"✓ CFG загружен ({len(self.channels)} каналов)", foreground="green")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при загрузке CFG:\n{str(e)}")
                self.status_label.config(text="✗ Ошибка загрузки CFG", foreground="red")

    def load_dat(self):
        """Загружает .dat файл"""
        file = filedialog.askopenfilename(filetypes=[("DAT files", "*.dat"), ("All files", "*.*")])
        if file:
            self.dat_file = file
            self.dat_label.config(text=os.path.basename(file), foreground="green")

            # Автоподтягивание .cfg файла с тем же именем
            cfg_file = Path(file).with_suffix('.cfg')
            if cfg_file.exists() and not self.cfg_file:
                self.cfg_file = str(cfg_file)
                self.cfg_label.config(text=os.path.basename(self.cfg_file), foreground="green")

                try:
                    with open(self.cfg_file, 'r', encoding='utf-8') as f:
                        cfg = parse_cfg(f.read())
                    self.channels = cfg['channels']
                    self.update_mapping_table()
                    self.auto_detect()
                    self.status_label.config(text=f"✓ DAT и CFG загружены автоматически ({len(self.channels)} каналов)", foreground="green")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Ошибка при загрузке CFG:\n{str(e)}")
                    self.status_label.config(text="✗ Ошибка загрузки CFG", foreground="red")
            else:
                self.status_label.config(text="✓ DAT загружен", foreground="green")
    
    def update_mapping_table(self):
        """Обновляет таблицу сопоставления"""
        # Очищаем таблицу
        for item in self.mapping_tree.get_children():
            self.mapping_tree.delete(item)
        
        # Добавляем строки
        for role in ROLE_ORDER:
            ch_idx = self.mapping.get(role)
            if ch_idx is not None and ch_idx < len(self.channels):
                ch = self.channels[ch_idx]
                channel_str = f"{ch_idx}: {ch['name']} ({ch['unit']})"
            else:
                channel_str = "-- не выбран --"
            
            role_type = "Ток (А)" if ROLE_IS_CURRENT[role] else "Напряжение (В)"
            self.mapping_tree.insert('', 'end', values=(role, channel_str, role_type))
    
    def auto_detect(self):
        """Автоматическое определение каналов"""
        if not self.channels:
            messagebox.showwarning("Предупреждение", "Сначала загрузите CFG файл")
            return
        
        self.mapping = guess_mapping(self.channels)
        self.update_mapping_table()
        messagebox.showinfo("Успех", "Каналы автоматически сопоставлены")
    
    def edit_mapping(self):
        """Редактирование сопоставления"""
        selection = self.mapping_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите параметр в таблице")
            return
        
        item = selection[0]
        role = self.mapping_tree.item(item)['values'][0]
        
        # Создаем диалоговое окно выбора
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Выберите канал для {role}")
        dialog.geometry("400x300")
        
        ttk.Label(dialog, text=f"Выберите канал для параметра '{role}':", font=("Arial", 11, "bold")).pack(padx=10, pady=10)
        
        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for i, ch in enumerate(self.channels):
            listbox.insert(tk.END, f"{i}: {ch['name']} ({ch['unit']}) - {ch['phase']}")
        
        def select_channel():
            selection = listbox.curselection()
            if selection:
                self.mapping[role] = selection[0]
                self.update_mapping_table()
                dialog.destroy()
        
        ttk.Button(dialog, text="Выбрать", command=select_channel).pack(pady=10)
    
    def start_convert(self):
        """Запускает конвертацию в отдельном потоке"""
        if not self.cfg_file or not self.dat_file:
            messagebox.showerror("Ошибка", "Загрузите оба файла (.cfg и .dat)")
            return
        
        if None in self.mapping.values():
            messagebox.showerror("Ошибка", "Все каналы должны быть сопоставлены")
            return
        
        # Проверяем параметры
        try:
            params = {}
            params['mac'] = self.params['mac'].get()
            params['appid'] = self.params['appid'].get()
            params['vlanid'] = self.params['vlanid'].get()
            params['vlan_pcp'] = int(self.params['vlan_pcp'].get())
            params['svid'] = self.params['svid'].get()
            params['confrev'] = int(self.params['confrev'].get())
            params['simulation'] = self.params['simulation'].get()
            params['ktt'] = float(self.params['ktt'].get())
            params['ktn'] = float(self.params['ktn'].get())
            params['k3i0'] = float(self.params['k3i0'].get())
            params['k3u0'] = float(self.params['k3u0'].get())
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Ошибка в параметрах:\n{str(e)}")
            return
        
        # Запускаем в отдельном потоке
        self.convert_btn.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.do_convert, args=(params,), daemon=True)
        thread.start()
    
    def do_convert(self, params):
        """Выполняет конвертацию"""
        try:
            self.progress_label.config(text="Загрузка файлов...", foreground="blue")
            self.progress['value'] = 20
            self.root.update()

            with open(self.cfg_file, 'r', encoding='utf-8') as f:
                cfg_text = f.read()

            with open(self.dat_file, 'r', encoding='utf-8') as f:
                dat_text = f.read()

            self.progress_label.config(text="Конвертация...", foreground="blue")
            self.progress['value'] = 50
            self.root.update()

            pcap_bytes, n_frames = convert(cfg_text, dat_text, self.mapping, params)

            self.progress_label.config(text=f"✓ Успешно! {n_frames} кадров", foreground="green")
            self.progress['value'] = 100
            self.download_btn.config(state=tk.NORMAL)
            self.view_btn.config(state=tk.NORMAL)

            self.pcap_data = pcap_bytes

            # Парсим данные для просмотра
            self.parse_samples_from_dat(cfg_text, dat_text, params)

            # Показываем информацию
            info = f"Параметры SV потока:\n"
            info += f"  MAC: {params['mac']}\n"
            info += f"  APPID: 0x{params['appid']}\n"
            info += f"  VLANID: {params['vlanid']}\n"
            info += f"  svID: {params['svid']}\n"
            info += f"  confRev: {params['confrev']}\n"
            info += f"  Simulation: {'Да' if params['simulation'] else 'Нет'}\n"
            info += f"\nКоэффициенты:\n"
            info += f"  Ктт: {params['ktt']}\n"
            info += f"  Ктн: {params['ktn']}\n"
            info += f"  K3i0: {params['k3i0']}\n"
            info += f"  K3u0: {params['k3u0']}\n"
            info += f"\nРезультат:\n"
            info += f"  Кадров: {n_frames}\n"
            info += f"  Размер PCAP: {len(pcap_bytes) / 1024:.1f} KB\n"

            self.info_text.config(state=tk.NORMAL)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, info)
            self.info_text.config(state=tk.DISABLED)

            messagebox.showinfo("Успех", f"Конвертация завершена!\n\n{n_frames} кадров SV потока\n{len(pcap_bytes) / 1024:.1f} KB")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при конвертации:\n{str(e)}")
            self.progress_label.config(text=f"✗ Ошибка: {str(e)}", foreground="red")
        finally:
            self.convert_btn.config(state=tk.NORMAL)
    
    def save_pcap(self):
        """Сохраняет PCAP файл"""
        if not self.pcap_data:
            messagebox.showerror("Ошибка", "Нет данных для сохранения")
            return
        
        file = filedialog.asksaveasfilename(
            defaultextension=".pcap",
            filetypes=[("PCAP files", "*.pcap"), ("All files", "*.*")],
            initialfile="sampled_values.pcap"
        )
        
        if file:
            try:
                with open(file, 'wb') as f:
                    f.write(self.pcap_data)
                messagebox.showinfo("Успех", f"Файл сохранён:\n{file}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка при сохранении:\n{str(e)}")
    
    def open_pcap(self):
        """Открывает папку с результатом"""
        file = filedialog.askopenfilename(filetypes=[("PCAP files", "*.pcap"), ("All files", "*.*")])
        if file:
            os.startfile(file) if sys.platform == "win32" else os.system(f"open '{file}'")

    def goto_view_tab(self):
        """Переход на вкладку просмотра"""
        self.notebook.select(4)  # Индекс 5-й вкладки (начиная с 0)
        self.update_view_tab()

    def parse_samples_from_dat(self, cfg_text, dat_text, params):
        """Парсит данные из DAT файла для просмотра"""
        try:
            from converter import parse_dat_ascii

            cfg = parse_cfg(cfg_text)
            n_channels = len(cfg['channels'])
            rows = parse_dat_ascii(dat_text, n_channels)

            # Извлекаем данные по каналам
            sample_rate = cfg['sample_rate']
            time = [i / sample_rate for i in range(len(rows))]

            # Создаем словарь данных
            self.parsed_samples = {
                'time': time,
                'sample_rate': sample_rate,
                'line_freq': cfg.get('line_freq', 50.0),
                'params': params,
            }

            # Извлекаем значения каждого канала
            for role in ROLE_ORDER:
                ch_idx = self.mapping.get(role)
                if ch_idx is not None and ch_idx < len(cfg['channels']):
                    ch = cfg['channels'][ch_idx]
                    values = []

                    for row in rows:
                        if ch_idx + 1 < len(row):  # +1 потому что первое значение - номер сэмпла
                            raw_val = row[ch_idx + 1]
                            # Применяем масштабирование из CFG
                            real_val = raw_val * ch['mult'] + ch['offset']

                            # Применяем коэффициенты трансформации
                            if ROLE_IS_CURRENT[role]:
                                if role == 'In':
                                    real_val *= params['k3i0']
                                else:
                                    real_val *= params['ktt']
                            else:
                                if role == 'Un':
                                    real_val *= params['k3u0']
                                else:
                                    real_val *= params['ktn']

                            values.append(real_val)

                    self.parsed_samples[role] = values

        except Exception as e:
            print(f"[ERROR] Ошибка при парсинге данных: {e}")
            self.parsed_samples = None

    def create_view_tab(self, parent):
        """Вкладка просмотра данных (5-я вкладка)"""

        if not MATPLOTLIB_AVAILABLE:
            ttk.Label(parent, text="⚠ Для просмотра данных требуется установить matplotlib:\npip install matplotlib numpy",
                     font=("Arial", 12), foreground="red").pack(pady=50)
            return

        mainframe = ttk.Frame(parent, padding="10")
        mainframe.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        ttk.Label(mainframe, text="Просмотр данных осциллограммы", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Панель управления
        control_frame = ttk.Frame(mainframe)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="Тип графика:").pack(side=tk.LEFT, padx=(0, 5))

        self.view_mode = tk.StringVar(value="oscillogram")
        view_modes = [
            ("Осциллограммы", "oscillogram"),
            ("Векторная диаграмма", "phasor"),
            ("Частота", "frequency"),
            ("Таблица значений", "table"),
        ]

        for text, mode in view_modes:
            ttk.Radiobutton(control_frame, text=text, variable=self.view_mode, value=mode,
                           command=self.update_view_tab).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="🔄 Обновить", command=self.update_view_tab).pack(side=tk.LEFT, padx=(20, 0))

        # Контейнер для графиков/таблиц
        self.view_container = ttk.Frame(mainframe)
        self.view_container.pack(fill=tk.BOTH, expand=True)

        # Начальное сообщение
        self.view_placeholder = ttk.Label(self.view_container,
                                          text="Выполните конвертацию, чтобы просмотреть данные",
                                          font=("Arial", 11), foreground="gray")
        self.view_placeholder.pack(expand=True)

    def update_view_tab(self):
        """Обновляет содержимое вкладки просмотра"""

        if not MATPLOTLIB_AVAILABLE:
            return

        # Очищаем контейнер
        for widget in self.view_container.winfo_children():
            widget.destroy()

        if not self.parsed_samples:
            self.view_placeholder = ttk.Label(self.view_container,
                                              text="Нет данных для отображения. Выполните конвертацию.",
                                              font=("Arial", 11), foreground="gray")
            self.view_placeholder.pack(expand=True)
            return

        mode = self.view_mode.get()

        if mode == "oscillogram":
            self.show_oscillogram()
        elif mode == "phasor":
            self.show_phasor_diagram()
        elif mode == "frequency":
            self.show_frequency()
        elif mode == "table":
            self.show_data_table()

    def show_oscillogram(self):
        """Отображает осциллограммы токов и напряжений"""

        fig = Figure(figsize=(12, 8), dpi=100)

        # Верхний график - токи
        ax1 = fig.add_subplot(211)
        time = self.parsed_samples['time']

        for role in ['Ia', 'Ib', 'Ic', 'In']:
            if role in self.parsed_samples:
                ax1.plot(time, self.parsed_samples[role], label=role, linewidth=1.5)

        ax1.set_xlabel('Время (с)')
        ax1.set_ylabel('Ток (А)')
        ax1.set_title('Токи')
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3)

        # Нижний график - напряжения
        ax2 = fig.add_subplot(212)

        for role in ['Ua', 'Ub', 'Uc', 'Un']:
            if role in self.parsed_samples:
                ax2.plot(time, self.parsed_samples[role], label=role, linewidth=1.5)

        ax2.set_xlabel('Время (с)')
        ax2.set_ylabel('Напряжение (В)')
        ax2.set_title('Напряжения')
        ax2.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)

        fig.tight_layout()

        # Встраиваем график
        canvas = FigureCanvasTkAgg(fig, master=self.view_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Добавляем панель инструментов для зума
        toolbar = NavigationToolbar2Tk(canvas, self.view_container)
        toolbar.update()

    def show_phasor_diagram(self):
        """Отображает векторную диаграмму"""

        # Вычисляем действующие значения и фазы
        sample_rate = self.parsed_samples['sample_rate']
        line_freq = self.parsed_samples['line_freq']

        # Берем один период (или часть данных)
        period_samples = int(sample_rate / line_freq)

        phasors = {}

        for role in ROLE_ORDER:
            if role in self.parsed_samples:
                data = self.parsed_samples[role][:period_samples * 3]  # 3 периода для точности

                if len(data) > 0:
                    # Вычисляем RMS
                    rms = math.sqrt(sum(x**2 for x in data) / len(data))

                    # Вычисляем фазу через FFT (упрощенно - находим первый пик)
                    if len(data) >= period_samples:
                        max_idx = data.index(max(data))
                        phase = (max_idx / period_samples) * 360
                    else:
                        phase = 0

                    phasors[role] = {'magnitude': rms, 'phase': phase}

        fig = Figure(figsize=(10, 10), dpi=100)
        ax = fig.add_subplot(111, projection='polar')

        # Отображаем векторы токов
        colors_i = {'Ia': 'red', 'Ib': 'green', 'Ic': 'blue', 'In': 'orange'}
        for role in ['Ia', 'Ib', 'Ic', 'In']:
            if role in phasors:
                mag = phasors[role]['magnitude']
                phase_rad = math.radians(phasors[role]['phase'])
                ax.arrow(0, 0, phase_rad, mag, head_width=0.1, head_length=mag*0.1,
                        fc=colors_i[role], ec=colors_i[role], linewidth=2, label=f"{role}: {mag:.1f}A")

        # Отображаем векторы напряжений (масштабируем для видимости)
        colors_u = {'Ua': 'darkred', 'Ub': 'darkgreen', 'Uc': 'darkblue', 'Un': 'darkorange'}
        scale_u = 0.1 if any(role in phasors for role in ['Ua', 'Ub', 'Uc']) else 1.0

        for role in ['Ua', 'Ub', 'Uc', 'Un']:
            if role in phasors:
                mag = phasors[role]['magnitude'] * scale_u
                phase_rad = math.radians(phasors[role]['phase'])
                ax.arrow(0, 0, phase_rad, mag, head_width=0.1, head_length=mag*0.1,
                        fc=colors_u[role], ec=colors_u[role], linewidth=2,
                        label=f"{role}: {phasors[role]['magnitude']:.1f}V", linestyle='--')

        ax.set_title('Векторная диаграмма\n(напряжения масштабированы для видимости)', fontsize=12)
        ax.legend(loc='upper left', bbox_to_anchor=(1.1, 1))

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.view_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def show_frequency(self):
        """Отображает частоту сигнала"""

        sample_rate = self.parsed_samples['sample_rate']
        line_freq = self.parsed_samples['line_freq']

        # Вычисляем частоту по нулевым переходам (для Ua)
        if 'Ua' not in self.parsed_samples:
            ttk.Label(self.view_container, text="Нет данных напряжения для расчета частоты",
                     font=("Arial", 11), foreground="red").pack(expand=True)
            return

        data = self.parsed_samples['Ua']
        time = self.parsed_samples['time']

        # Находим нулевые переходы
        zero_crossings = []
        for i in range(1, len(data)):
            if (data[i-1] < 0 and data[i] >= 0) or (data[i-1] > 0 and data[i] <= 0):
                zero_crossings.append(time[i])

        # Вычисляем частоту между переходами
        frequencies = []
        freq_time = []

        for i in range(2, len(zero_crossings)):
            period = (zero_crossings[i] - zero_crossings[i-2])
            if period > 0:
                freq = 1.0 / period
                frequencies.append(freq)
                freq_time.append(zero_crossings[i])

        fig = Figure(figsize=(12, 6), dpi=100)
        ax = fig.add_subplot(111)

        if frequencies:
            ax.plot(freq_time, frequencies, label='Частота (Ua)', linewidth=2, color='blue')
            ax.axhline(y=line_freq, color='red', linestyle='--', label=f'Номинальная ({line_freq} Гц)')

            avg_freq = sum(frequencies) / len(frequencies)
            ax.axhline(y=avg_freq, color='green', linestyle='--', label=f'Средняя ({avg_freq:.2f} Гц)')

        ax.set_xlabel('Время (с)')
        ax.set_ylabel('Частота (Гц)')
        ax.set_title('Частота сигнала (по нулевым переходам Ua)')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.view_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(canvas, self.view_container)
        toolbar.update()

    def show_data_table(self):
        """Отображает таблицу значений"""

        # Создаем таблицу с прокруткой
        table_frame = ttk.Frame(self.view_container)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # Скроллбары
        vsb = ttk.Scrollbar(table_frame, orient="vertical")
        hsb = ttk.Scrollbar(table_frame, orient="horizontal")

        # Таблица
        columns = ['Время (с)'] + ROLE_ORDER
        tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                           yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)

        # Заголовки
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100)

        # Данные (показываем каждый 10-й сэмпл для производительности)
        time = self.parsed_samples['time']
        step = max(1, len(time) // 1000)  # Не более 1000 строк

        for i in range(0, len(time), step):
            row = [f"{time[i]:.6f}"]
            for role in ROLE_ORDER:
                if role in self.parsed_samples and i < len(self.parsed_samples[role]):
                    row.append(f"{self.parsed_samples[role][i]:.3f}")
                else:
                    row.append("—")
            tree.insert('', 'end', values=row)

        # Размещение
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')

        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Статистика
        stats_frame = ttk.Frame(self.view_container)
        stats_frame.pack(fill=tk.X, pady=10)

        stats_text = f"Всего сэмплов: {len(time)} | Частота дискретизации: {self.parsed_samples['sample_rate']} Гц | "
        stats_text += f"Длительность: {time[-1]:.3f} с"

        ttk.Label(stats_frame, text=stats_text, font=("Arial", 10)).pack()

    def show_about(self):
        """Показывает информацию о программе"""
        messagebox.showinfo("О программе",
            "SV Converter v2.0\n\n"
            "Конвертер осциллограмм COMTRADE\n"
            "в поток Sampled Values\n"
            "по стандарту IEC 61850-9-2 LE\n\n"
            "Версия: 2.0 (GUI на Tkinter)\n"
            "Python: 3.7+\n"
            "Лицензия: Open Source")


if __name__ == "__main__":
    root = tk.Tk()
    app = SVConverterGUI(root)
    root.mainloop()
