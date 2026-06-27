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
        self.mapping2 = {role: None for role in ROLE_ORDER}  # Для второго потока
        self.dual_stream_mode = tk.BooleanVar(value=False)  # Флаг режима двух потоков
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

        # Переключатель между потоками (видно только в режиме двух потоков)
        self.stream_selector_frame = ttk.Frame(mainframe)
        self.stream_selector_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(self.stream_selector_frame, text="Выбрать поток:").pack(side=tk.LEFT, padx=(0, 10))
        self.stream_var = tk.StringVar(value="stream1")
        ttk.Radiobutton(self.stream_selector_frame, text="SV Stream 1", variable=self.stream_var,
                        value="stream1", command=self.on_stream_selection_changed).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(self.stream_selector_frame, text="SV Stream 2", variable=self.stream_var,
                        value="stream2", command=self.on_stream_selection_changed).pack(side=tk.LEFT)

        self.stream_selector_frame.pack_forget()  # Скрываем до включения режима двух потоков

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

    def on_stream_selection_changed(self):
        """Переключение между потоками в Tab 2"""
        self.update_mapping_table()
        
    def auto_fill_stream2_params(self):
        """Автоматически заполняет параметры Stream 2 на основе Stream 1"""
        try:
            # MAC: последний октет +1
            mac = self.params['mac'].get()
            mac_parts = mac.split('-')
            if len(mac_parts) == 6:
                last_octet = int(mac_parts[-1], 16)
                mac_parts[-1] = f"{last_octet + 1:02X}"
                new_mac = '-'.join(mac_parts)
            else:
                new_mac = mac

            # APPID: текущее значение +1
            appid_str = self.params['appid'].get()
            appid = int(appid_str, 16)
            new_appid = f"{appid + 1:04X}"

            # SVID: _SV1 → _SV2
            svid = self.params['svid'].get()
            new_svid = svid.replace('_SV1', '_SV2').replace('SV1', 'SV2')

            # Заполняем поля Stream 2
            self.params2['mac'].delete(0, tk.END)
            self.params2['mac'].insert(0, new_mac)

            self.params2['appid'].delete(0, tk.END)
            self.params2['appid'].insert(0, new_appid)

            self.params2['svid'].delete(0, tk.END)
            self.params2['svid'].insert(0, new_svid)

            messagebox.showinfo("Успех", "Параметры Stream 2 автоматически заполнены")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при заполнении:\n{str(e)}")

    def copy_coefficients_to_stream2(self):
        """Копирует коэффициенты из Stream 1 в Stream 2"""
        try:
            for key in ['ktt', 'ktn', 'k3i0', 'k3u0']:
                value = self.params[key].get()
                self.params2[key].delete(0, tk.END)
                self.params2[key].insert(0, value)
            messagebox.showinfo("Успех", "Коэффициенты скопированы в Stream 2")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка при копировании:\n{str(e)}")
    def create_params_tab(self, parent):
        """Вкладка параметров SV"""

        mainframe = ttk.Frame(parent, padding="20")
        mainframe.pack(fill=tk.BOTH, expand=True)

        # Checkbox для режима двух потоков
        self.dual_stream_check = ttk.Checkbutton(mainframe, text="🔀 Режим двух SV потоков (Dual Stream Mode)",
                                                   variable=self.dual_stream_mode, command=self.on_dual_stream_toggled)
        self.dual_stream_check.pack(anchor=tk.W, pady=(0, 20))

        # Основной Canvas + Scrollbar для прокрутки
        canvas = tk.Canvas(mainframe, highlightthickness=0)
        scrollbar = ttk.Scrollbar(mainframe, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ===== STREAM 1 =====
        self.stream1_frame = ttk.LabelFrame(scrollable_frame, text="Stream 1 - Параметры", padding="15")
        self.stream1_frame.pack(fill=tk.X, pady=(0, 20), padx=5)

        # Сетевые параметры Stream 1
        ttk.Label(self.stream1_frame, text="Сетевые параметры:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))

        net_frame1 = ttk.Frame(self.stream1_frame)
        net_frame1.pack(fill=tk.X, pady=(0, 15))

        self.params = {}

        params_list = [
            ("MAC адрес", "mac", "01-0C-CD-04-00-01"),
            ("APPID (hex)", "appid", "4000"),
            ("VLANID (hex)", "vlanid", "0"),
            ("VLAN Priority", "vlan_pcp", "4"),
        ]

        for i, (label, key, default) in enumerate(params_list):
            ttk.Label(net_frame1, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            self.params[key] = ttk.Entry(net_frame1, width=30)
            self.params[key].insert(0, default)
            self.params[key].grid(row=i, column=1, sticky=tk.W, padx=(0, 20), pady=5)

        # ASDU параметры Stream 1
        ttk.Label(self.stream1_frame, text="ASDU параметры:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 10))

        asdu_frame1 = ttk.Frame(self.stream1_frame)
        asdu_frame1.pack(fill=tk.X, pady=(0, 15))

        asdu_params = [
            ("svID", "svid", "RET61850_SV1"),
            ("confRev", "confrev", "1"),
        ]

        for i, (label, key, default) in enumerate(asdu_params):
            ttk.Label(asdu_frame1, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            self.params[key] = ttk.Entry(asdu_frame1, width=30)
            self.params[key].insert(0, default)
            self.params[key].grid(row=i, column=1, sticky=tk.W, padx=(0, 20), pady=5)

        # Флаг Simulation Stream 1
        self.params["simulation"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(asdu_frame1, text="Флаг Simulation/Test", variable=self.params["simulation"]).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)

        # Коэффициенты Stream 1
        ttk.Label(self.stream1_frame, text="Коэффициенты трансформации:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 10))

        coef_frame1 = ttk.Frame(self.stream1_frame)
        coef_frame1.pack(fill=tk.X)

        coef_list = [
            ("Ктт (ток)", "ktt", "1000"),
            ("Ктн (напр)", "ktn", "1100"),
            ("K3i0 (нейтр ток)", "k3i0", "1000"),
            ("K3u0 (нейтр напр)", "k3u0", "1905.2"),
        ]

        for i, (label, key, default) in enumerate(coef_list):
            col = i % 2
            row = i // 2
            ttk.Label(coef_frame1, text=label + ":").grid(row=row, column=col*2, sticky=tk.W, padx=(0, 10), pady=5)
            self.params[key] = ttk.Entry(coef_frame1, width=20)
            self.params[key].insert(0, default)
            self.params[key].grid(row=row, column=col*2+1, sticky=tk.W, padx=(0, 20), pady=5)

        # ===== STREAM 2 (скрыт по умолчанию) =====
        self.stream2_frame = ttk.LabelFrame(scrollable_frame, text="Stream 2 - Параметры", padding="15")
        self.stream2_frame.pack(fill=tk.X, pady=(0, 20), padx=5)
        self.stream2_frame.pack_forget()  # Скрываем до включения режима двух потоков

        # Сетевые параметры Stream 2
        ttk.Label(self.stream2_frame, text="Сетевые параметры:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))

        net_frame2 = ttk.Frame(self.stream2_frame)
        net_frame2.pack(fill=tk.X, pady=(0, 15))

        self.params2 = {}

        for i, (label, key, default) in enumerate(params_list):
            ttk.Label(net_frame2, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            self.params2[key] = ttk.Entry(net_frame2, width=30)
            self.params2[key].insert(0, default)
            self.params2[key].grid(row=i, column=1, sticky=tk.W, padx=(0, 20), pady=5)

        # ASDU параметры Stream 2
        ttk.Label(self.stream2_frame, text="ASDU параметры:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 10))

        asdu_frame2 = ttk.Frame(self.stream2_frame)
        asdu_frame2.pack(fill=tk.X, pady=(0, 15))

        for i, (label, key, default) in enumerate(asdu_params):
            if key == "svid":
                default = "RET61850_SV2"
            ttk.Label(asdu_frame2, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            self.params2[key] = ttk.Entry(asdu_frame2, width=30)
            self.params2[key].insert(0, default)
            self.params2[key].grid(row=i, column=1, sticky=tk.W, padx=(0, 20), pady=5)

        # Флаг Simulation Stream 2
        self.params2["simulation"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(asdu_frame2, text="Флаг Simulation/Test", variable=self.params2["simulation"]).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=10)

        # Коэффициенты Stream 2
        ttk.Label(self.stream2_frame, text="Коэффициенты трансформации:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 10))

        coef_frame2 = ttk.Frame(self.stream2_frame)
        coef_frame2.pack(fill=tk.X, pady=(0, 15))

        for i, (label, key, default) in enumerate(coef_list):
            col = i % 2
            row = i // 2
            ttk.Label(coef_frame2, text=label + ":").grid(row=row, column=col*2, sticky=tk.W, padx=(0, 10), pady=5)
            self.params2[key] = ttk.Entry(coef_frame2, width=20)
            self.params2[key].insert(0, default)
            self.params2[key].grid(row=row, column=col*2+1, sticky=tk.W, padx=(0, 20), pady=5)

        # Кнопки для Stream 2
        buttons_frame2 = ttk.Frame(self.stream2_frame)
        buttons_frame2.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(buttons_frame2, text="🔧 Автоматически заполнить", command=self.auto_fill_stream2_params).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame2, text="📋 Копировать коэффициенты", command=self.copy_coefficients_to_stream2).pack(side=tk.LEFT)

    def on_dual_stream_toggled(self):
        """Включение/отключение режима двух потоков"""
        if self.dual_stream_mode.get():
            # Включаем режим двух потоков
            self.stream2_frame.pack(fill=tk.X, pady=(0, 20), padx=5, after=self.stream1_frame)
            self.stream_selector_frame.pack(fill=tk.X, pady=(0, 10))
            # Автоматически заполняем параметры Stream 2
            self.auto_fill_stream2_params()
        else:
            # Отключаем режим двух потоков
            self.stream2_frame.pack_forget()
            self.stream_selector_frame.pack_forget()
            self.stream_var.set("stream1")
        
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
        # Выбираем активный mapping в зависимости от режима
        if self.dual_stream_mode.get() and self.stream_var.get() == "stream2":
            active_mapping = self.mapping2
        else:
            active_mapping = self.mapping

        # Очищаем таблицу
        for item in self.mapping_tree.get_children():
            self.mapping_tree.delete(item)

        # Добавляем строки
        for role in ROLE_ORDER:
            ch_idx = active_mapping.get(role)
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

        # Выбираем активный mapping в зависимости от режима
        if self.dual_stream_mode.get() and self.stream_var.get() == "stream2":
            self.mapping2 = guess_mapping(self.channels)
        else:
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

        # Выбираем активный mapping в зависимости от режима
        if self.dual_stream_mode.get() and self.stream_var.get() == "stream2":
            active_mapping = self.mapping2
        else:
            active_mapping = self.mapping

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
                active_mapping[role] = selection[0]
                self.update_mapping_table()
                dialog.destroy()

        ttk.Button(dialog, text="Выбрать", command=select_channel).pack(pady=10)
    
    def start_convert(self):
        """Запускает конвертацию в отдельном потоке"""
        if not self.cfg_file or not self.dat_file:
            messagebox.showerror("Ошибка", "Загрузите оба файла (.cfg и .dat)")
            return

        # Проверяем основной mapping
        if None in self.mapping.values():
            messagebox.showerror("Ошибка", "Все каналы Stream 1 должны быть сопоставлены")
            return

        # Если включен режим двух потоков, проверяем второй mapping
        if self.dual_stream_mode.get():
            if None in self.mapping2.values():
                messagebox.showerror("Ошибка", "Все каналы Stream 2 должны быть сопоставлены")
                return

        # Проверяем параметры Stream 1
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
            messagebox.showerror("Ошибка", f"Ошибка в параметрах Stream 1:\n{str(e)}")
            return

        # Проверяем параметры Stream 2 (если включен режим двух потоков)
        params2 = None
        if self.dual_stream_mode.get():
            try:
                params2 = {}
                params2['mac'] = self.params2['mac'].get()
                params2['appid'] = self.params2['appid'].get()
                params2['vlanid'] = self.params2['vlanid'].get()
                params2['vlan_pcp'] = int(self.params2['vlan_pcp'].get())
                params2['svid'] = self.params2['svid'].get()
                params2['confrev'] = int(self.params2['confrev'].get())
                params2['simulation'] = self.params2['simulation'].get()
                params2['ktt'] = float(self.params2['ktt'].get())
                params2['ktn'] = float(self.params2['ktn'].get())
                params2['k3i0'] = float(self.params2['k3i0'].get())
                params2['k3u0'] = float(self.params2['k3u0'].get())
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Ошибка в параметрах Stream 2:\n{str(e)}")
                return

        # Запускаем в отдельном потоке
        self.convert_btn.config(state=tk.DISABLED)
        thread = threading.Thread(target=self.do_convert, args=(params, params2), daemon=True)
        thread.start()
    
    def do_convert(self, params, params2=None):
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

            # Вызываем convert с поддержкой двух потоков
            if params2 is not None:
                pcap_bytes, n_frames = convert(cfg_text, dat_text, self.mapping, params,
                                               self.mapping2, params2)
            else:
                pcap_bytes, n_frames = convert(cfg_text, dat_text, self.mapping, params)

            self.progress_label.config(text=f"✓ Успешно! {n_frames} кадров", foreground="green")
            self.progress['value'] = 100
            self.download_btn.config(state=tk.NORMAL)
            self.view_btn.config(state=tk.NORMAL)

            self.pcap_data = pcap_bytes

            # Парсим данные для просмотра
            self.parse_samples_from_dat(cfg_text, dat_text, params)

            # Показываем информацию
            if params2 is not None:
                info = f"Конфигурация: DUAL STREAM MODE\n\n"
                info += f"═════ Stream 1 ═════\n"
                info += f"  MAC: {params['mac']}\n"
                info += f"  APPID: 0x{params['appid']}\n"
                info += f"  VLANID: {params['vlanid']}\n"
                info += f"  svID: {params['svid']}\n"
                info += f"  Ктт: {params['ktt']}, Ктн: {params['ktn']}\n"
                info += f"\n═════ Stream 2 ═════\n"
                info += f"  MAC: {params2['mac']}\n"
                info += f"  APPID: 0x{params2['appid']}\n"
                info += f"  VLANID: {params2['vlanid']}\n"
                info += f"  svID: {params2['svid']}\n"
                info += f"  Ктт: {params2['ktt']}, Ктн: {params2['ktn']}\n"
                info += f"\n═════ Результат ═════\n"
                info += f"  Кадров: {n_frames} (каждый сэмпл = 2 фрейма)\n"
                info += f"  Размер PCAP: {len(pcap_bytes) / 1024:.1f} KB\n"
            else:
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

            messagebox.showinfo("Успех", f"Конвертация завершена!\n\n{n_frames} кадров\n{len(pcap_bytes) / 1024:.1f} KB")

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
                        if ch_idx < len(row):
                            raw_val = row[ch_idx]
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
            import traceback
            traceback.print_exc()
            self.parsed_samples = None

    def create_view_tab(self, parent):
        """Вкладка просмотра данных (5-я вкладка) - интерфейс как сетевой анализатор"""

        if not MATPLOTLIB_AVAILABLE:
            ttk.Label(parent, text="⚠ Для просмотра данных требуется установить matplotlib:\npip install matplotlib numpy",
                     font=("Arial", 12), foreground="red").pack(pady=50)
            return

        mainframe = ttk.Frame(parent)
        mainframe.pack(fill=tk.BOTH, expand=True)

        # ===== ЛЕВАЯ ПАНЕЛЬ - Список потоков =====
        left_panel = ttk.Frame(mainframe, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, padx=5, pady=5)
        left_panel.pack_propagate(False)

        ttk.Label(left_panel, text="Список потоков", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 10))

        # Listbox для потоков
        self.streams_listbox = tk.Listbox(left_panel, height=10, width=35)
        self.streams_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.streams_listbox.bind('<<ListboxSelect>>', self.on_stream_selected)

        # Режимы просмотра
        ttk.Label(left_panel, text="Режим просмотра", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))

        self.view_mode = tk.StringVar(value="oscillogram")
        view_modes = [
            ("Осциллограмма", "oscillogram"),
            ("Векторная диаграмма", "phasor"),
            ("Частота", "frequency"),
            ("Таблица значений", "table"),
        ]

        for text, mode in view_modes:
            ttk.Radiobutton(left_panel, text=text, variable=self.view_mode, value=mode,
                           command=self.on_view_mode_changed).pack(anchor=tk.W, padx=10)

        # Кнопки управления
        btn_frame = ttk.Frame(left_panel)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="🔄 Обновить", command=self.update_view_tab).pack(fill=tk.X, pady=5)

        # ===== ЦЕНТРАЛЬНАЯ/ПРАВАЯ ЧАСТЬ =====
        right_panel = ttk.Frame(mainframe)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Верхняя часть - Информация о потоке и значения
        top_frame = ttk.Frame(right_panel)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        # Левая часть верхней панели - описание
        info_frame = ttk.LabelFrame(top_frame, text="Информация о потоке", padding="10")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.info_label = ttk.Label(info_frame, text="Выберите поток для просмотра", font=("Arial", 9))
        self.info_label.pack(anchor=tk.W)

        # Правая часть верхней панели - таблица значений и диаграмма
        values_frame = ttk.Frame(top_frame)
        values_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Таблица аналоговых значений
        table_frame = ttk.LabelFrame(values_frame, text="Аналоговые значения", padding="10")
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        columns = ("Параметр", "Значение", "Единица")
        self.values_tree = ttk.Treeview(table_frame, columns=columns, height=8, show="headings")
        self.values_tree.column("Параметр", width=80)
        self.values_tree.column("Значение", width=80)
        self.values_tree.column("Единица", width=60)
        self.values_tree.heading("Параметр", text="Параметр")
        self.values_tree.heading("Значение", text="Значение")
        self.values_tree.heading("Единица", text="Единица")
        self.values_tree.pack(fill=tk.BOTH, expand=True)

        # Диаграмма (пока пустой фрейм)
        diagram_frame = ttk.LabelFrame(values_frame, text="Диаграмма", padding="5")
        diagram_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.diagram_canvas_frame = diagram_frame

        # Нижняя часть - Осциллограмма
        bottom_frame = ttk.LabelFrame(right_panel, text="Осциллограмма", padding="5")
        bottom_frame.pack(fill=tk.BOTH, expand=True)

        self.oscillogram_frame = ttk.Frame(bottom_frame)
        self.oscillogram_frame.pack(fill=tk.BOTH, expand=True)

        # Начальное сообщение
        self.view_placeholder = ttk.Label(self.oscillogram_frame,
                                          text="Выполните конвертацию, чтобы просмотреть данные",
                                          font=("Arial", 11), foreground="gray")
        self.view_placeholder.pack(expand=True)

    def on_stream_selected(self, event):
        """Обработчик выбора потока из списка"""
        selection = self.streams_listbox.curselection()
        if selection:
            self.selected_stream_idx = selection[0]
            self.update_view_tab()

    def on_view_mode_changed(self):
        """Обработчик переключения режима просмотра"""
        self.update_view_tab()

    def update_view_tab(self):
        """Обновляет содержимое вкладки просмотра"""

        if not MATPLOTLIB_AVAILABLE:
            return

        if not self.parsed_samples:
            # Очищаем осциллограмму
            for widget in self.oscillogram_frame.winfo_children():
                widget.destroy()

            self.view_placeholder = ttk.Label(self.oscillogram_frame,
                                              text="Нет данных для отображения. Выполните конвертацию.",
                                              font=("Arial", 11), foreground="gray")
            self.view_placeholder.pack(expand=True)
            return

        # Обновляем список потоков
        self.streams_listbox.delete(0, tk.END)

        # Если режим двух потоков, показываем оба потока
        if self.dual_stream_mode.get():
            self.streams_listbox.insert(tk.END, "SV Stream 1")
            self.streams_listbox.insert(tk.END, "SV Stream 2")
        else:
            self.streams_listbox.insert(tk.END, "SV Stream 1")

        # Выбираем первый поток по умолчанию
        if not hasattr(self, 'selected_stream_idx'):
            self.selected_stream_idx = 0
        self.streams_listbox.selection_set(min(self.selected_stream_idx, self.streams_listbox.size() - 1))

        # Обновляем информацию о выбранном потоке
        stream_name = self.streams_listbox.get(self.selected_stream_idx)
        self.update_stream_info(stream_name)

        # Очищаем осциллограмму
        for widget in self.oscillogram_frame.winfo_children():
            widget.destroy()

        # Показываем нужный режим просмотра
        mode = self.view_mode.get()

        if mode == "oscillogram":
            self.show_oscillogram()
        elif mode == "phasor":
            self.show_phasor_diagram()
        elif mode == "frequency":
            self.show_frequency()
        elif mode == "table":
            self.show_data_table()

    def update_stream_info(self, stream_name):
        """Обновляет информацию о потоке и таблицу значений"""

        # Определяем индекс потока
        stream_idx = 0 if "Stream 1" in stream_name else 1

        # Информация о потоке
        if stream_idx == 0:
            params = self.params
            mac = params['mac'].get()
            appid = params['appid'].get()
            svid = params['svid'].get()
        else:
            params = self.params2
            mac = params['mac'].get()
            appid = params['appid'].get()
            svid = params['svid'].get()

        info_text = f"SVID: {svid}\nСтандарт: IEC 61850-9-2 LE\n"
        info_text += f"MAC: {mac}\nAPPID: 0x{appid}\n"
        info_text += f"Сэмплов: {len(self.parsed_samples.get('Ia', []))}\n"
        info_text += f"Частота: {self.parsed_samples.get('sample_rate', 4000)} Гц"

        self.info_label.config(text=info_text)

        # Таблица аналоговых значений (первый сэмпл)
        for item in self.values_tree.get_children():
            self.values_tree.delete(item)

        # Получаем первый сэмпл для каждого канала
        for role in ROLE_ORDER:
            if role in self.parsed_samples and len(self.parsed_samples[role]) > 0:
                value = self.parsed_samples[role][0]
                unit = "А" if ROLE_IS_CURRENT[role] else "В"
                self.values_tree.insert('', 'end', values=(role, f"{value:.2f}", unit))

    def show_oscillogram(self):
        """Отображает осциллограммы токов и напряжений"""

        fig = Figure(figsize=(12, 3), dpi=100)

        # Один график со всеми каналами
        ax = fig.add_subplot(111)
        time = self.parsed_samples['time']

        colors = {'Ia': 'red', 'Ib': 'green', 'Ic': 'blue', 'In': 'orange',
                  'Ua': 'darkred', 'Ub': 'darkgreen', 'Uc': 'darkblue', 'Un': 'darkorange'}
        linestyles = {role: '-' if ROLE_IS_CURRENT[role] else '--' for role in ROLE_ORDER}

        for role in ROLE_ORDER:
            if role in self.parsed_samples:
                ax.plot(time, self.parsed_samples[role], label=f"{role} (мВ/мА)",
                       color=colors.get(role, 'black'), linestyle=linestyles.get(role, '-'), linewidth=1)

        ax.set_xlabel('Время (с)')
        ax.set_ylabel('Значение')
        ax.set_title('Осциллограмма')
        ax.legend(loc='upper right', fontsize=8, ncol=4)
        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        # Встраиваем график
        canvas = FigureCanvasTkAgg(fig, master=self.oscillogram_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Добавляем панель инструментов для зума
        toolbar = NavigationToolbar2Tk(canvas, self.oscillogram_frame)
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

        canvas = FigureCanvasTkAgg(fig, master=self.oscillogram_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def show_frequency(self):
        """Отображает частоту сигнала"""

        sample_rate = self.parsed_samples['sample_rate']
        line_freq = self.parsed_samples['line_freq']

        # Вычисляем частоту по нулевым переходам (для Ua)
        if 'Ua' not in self.parsed_samples:
            ttk.Label(self.oscillogram_frame, text="Нет данных напряжения для расчета частоты",
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

        canvas = FigureCanvasTkAgg(fig, master=self.oscillogram_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(canvas, self.oscillogram_frame)
        toolbar.update()

    def show_data_table(self):
        """Отображает таблицу значений"""

        # Создаем таблицу с прокруткой
        table_frame = ttk.Frame(self.oscillogram_frame)
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
        stats_frame = ttk.Frame(self.oscillogram_frame)
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
