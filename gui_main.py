# -*- coding: utf-8 -*-
"""
SV Converter v2.1 - Расширенный GUI с просмотром PCAP
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os, sys, threading
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from converter import convert, convert_dual_stream, parse_cfg, guess_mapping, ROLE_ORDER, ROLE_IS_CURRENT
from pcap_analyzer import PCAPAnalyzer
from plot_generator import PlotGenerator


class SVConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SV Converter v2.1 - IEC 61850-9-2 LE")
        self.root.geometry("1400x900")

        self.cfg_file = None
        self.dat_file = None
        self.cfg_file2 = None
        self.dat_file2 = None
        self.pcap_file = None
        self.channels = []
        self.channels2 = []
        self.mapping = {role: None for role in ROLE_ORDER}
        self.mapping2 = {role: None for role in ROLE_ORDER}
        self.pcap_data = None
        self.analyzer = None
        self.dual_mode = False

        self.create_widgets()
        
    def create_widgets(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Открыть PCAP", command=self.load_pcap_file)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.root.quit)
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладки 1-4 как раньше
        frame1 = ttk.Frame(self.notebook)
        self.notebook.add(frame1, text="1. Загрузка файлов")
        self.create_file_tab(frame1)
        
        frame2 = ttk.Frame(self.notebook)
        self.notebook.add(frame2, text="2. Сопоставление")
        self.create_mapping_tab(frame2)
        
        frame3 = ttk.Frame(self.notebook)
        self.notebook.add(frame3, text="3. Параметры")
        self.create_params_tab(frame3)
        
        frame4 = ttk.Frame(self.notebook)
        self.notebook.add(frame4, text="4. Конвертация")
        self.create_convert_tab(frame4)
        
        # Вкладка 5: Просмотр
        frame5 = ttk.Frame(self.notebook)
        self.notebook.add(frame5, text="5. Просмотр PCAP")
        self.create_viewer_tab(frame5)
    
    def create_file_tab(self, parent):
        mainframe = ttk.Frame(parent, padding="20")
        mainframe.pack(fill=tk.BOTH, expand=True)

        ttk.Label(mainframe, text="Поток 1 - Конфигурационный файл (.cfg):", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        cfg_frame = ttk.Frame(mainframe)
        cfg_frame.pack(fill=tk.X, pady=(0, 20))

        self.cfg_label = ttk.Label(cfg_frame, text="Не выбран", foreground="red")
        self.cfg_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(cfg_frame, text="Выбрать .cfg", command=self.load_cfg).pack(side=tk.RIGHT)

        ttk.Label(mainframe, text="Поток 1 - Файл данных (.dat):", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        dat_frame = ttk.Frame(mainframe)
        dat_frame.pack(fill=tk.X, pady=(0, 20))

        self.dat_label = ttk.Label(dat_frame, text="Не выбран", foreground="red")
        self.dat_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dat_frame, text="Выбрать .dat", command=self.load_dat).pack(side=tk.RIGHT)

        ttk.Separator(mainframe).pack(fill=tk.X, pady=20)

        ttk.Label(mainframe, text="Поток 2 (опционально) - Конфигурационный файл (.cfg):", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        cfg_frame2 = ttk.Frame(mainframe)
        cfg_frame2.pack(fill=tk.X, pady=(0, 20))

        self.cfg_label2 = ttk.Label(cfg_frame2, text="Не выбран", foreground="orange")
        self.cfg_label2.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(cfg_frame2, text="Выбрать .cfg", command=self.load_cfg2).pack(side=tk.RIGHT)

        ttk.Label(mainframe, text="Поток 2 (опционально) - Файл данных (.dat):", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        dat_frame2 = ttk.Frame(mainframe)
        dat_frame2.pack(fill=tk.X, pady=(0, 20))

        self.dat_label2 = ttk.Label(dat_frame2, text="Не выбран", foreground="orange")
        self.dat_label2.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dat_frame2, text="Выбрать .dat", command=self.load_dat2).pack(side=tk.RIGHT)

        ttk.Separator(mainframe).pack(fill=tk.X, pady=20)
        self.status_label = ttk.Label(mainframe, text="Ожидание загрузки...", foreground="orange")
        self.status_label.pack(anchor=tk.W)
    
    def create_mapping_tab(self, parent):
        mainframe = ttk.Frame(parent, padding="20")
        mainframe.pack(fill=tk.BOTH, expand=True)

        ttk.Label(mainframe, text="Поток 1 - Сопоставление каналов:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))

        columns = ("Параметр", "Канал", "Тип")
        self.mapping_tree = ttk.Treeview(mainframe, columns=columns, height=10, show="headings")
        self.mapping_tree.column("Параметр", width=150)
        self.mapping_tree.column("Канал", width=400)
        self.mapping_tree.column("Тип", width=200)

        for col in columns:
            self.mapping_tree.heading(col, text=col)

        self.mapping_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_frame = ttk.Frame(mainframe)
        btn_frame.pack(fill=tk.X, pady=(0, 20))
        ttk.Button(btn_frame, text="🔍 Автоматическое определение", command=self.auto_detect).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="✎ Редактировать", command=self.edit_mapping).pack(side=tk.LEFT)

        ttk.Separator(mainframe).pack(fill=tk.X, pady=15)

        ttk.Label(mainframe, text="Поток 2 (опционально) - Сопоставление каналов:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))

        self.mapping_tree2 = ttk.Treeview(mainframe, columns=columns, height=10, show="headings")
        self.mapping_tree2.column("Параметр", width=150)
        self.mapping_tree2.column("Канал", width=400)
        self.mapping_tree2.column("Тип", width=200)

        for col in columns:
            self.mapping_tree2.heading(col, text=col)

        self.mapping_tree2.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        btn_frame2 = ttk.Frame(mainframe)
        btn_frame2.pack(fill=tk.X)
        ttk.Button(btn_frame2, text="🔍 Автоматическое определение", command=self.auto_detect2).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame2, text="✎ Редактировать", command=self.edit_mapping2).pack(side=tk.LEFT)
    
    def create_params_tab(self, parent):
        mainframe = ttk.Frame(parent, padding="20")
        mainframe.pack(fill=tk.BOTH, expand=True)
        
        self.params = {}
        
        ttk.Label(mainframe, text="Сетевые параметры:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(0, 10))
        net_frame = ttk.Frame(mainframe)
        net_frame.pack(fill=tk.X, pady=(0, 20))
        
        params_list = [("MAC адрес", "mac", "01-0C-CD-04-00-01"), ("APPID (hex)", "appid", "4000")]
        for i, (label, key, default) in enumerate(params_list):
            ttk.Label(net_frame, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            self.params[key] = ttk.Entry(net_frame, width=30)
            self.params[key].insert(0, default)
            self.params[key].grid(row=i, column=1, sticky=tk.W, padx=(0, 20), pady=5)
        
        ttk.Label(mainframe, text="Коэффициенты:", font=("Arial", 11, "bold")).pack(anchor=tk.W, pady=(20, 10))
        coef_frame = ttk.Frame(mainframe)
        coef_frame.pack(fill=tk.X)
        
        coef_list = [("Ктт", "ktt", "1000"), ("Ктн", "ktn", "1100")]
        for i, (label, key, default) in enumerate(coef_list):
            ttk.Label(coef_frame, text=label + ":").grid(row=i, column=0, sticky=tk.W, padx=(0, 10), pady=5)
            self.params[key] = ttk.Entry(coef_frame, width=20)
            self.params[key].insert(0, default)
            self.params[key].grid(row=i, column=1, sticky=tk.W, padx=(0, 20), pady=5)
        
        self.params["simulation"] = tk.BooleanVar(value=True)
        ttk.Checkbutton(coef_frame, text="Simulation", variable=self.params["simulation"]).grid(row=2, column=0, sticky=tk.W, pady=10)
    
    def create_convert_tab(self, parent):
        mainframe = ttk.Frame(parent, padding="20")
        mainframe.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(mainframe, text="Статус:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        self.progress = ttk.Progressbar(mainframe, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0, 20))
        
        self.progress_label = ttk.Label(mainframe, text="Готово", foreground="blue")
        self.progress_label.pack(anchor=tk.W, pady=(0, 30))
        
        btn_frame = ttk.Frame(mainframe)
        btn_frame.pack(fill=tk.X, pady=(0, 30))
        
        self.convert_btn = ttk.Button(btn_frame, text="▶ Конвертировать", command=self.start_convert)
        self.convert_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.download_btn = ttk.Button(btn_frame, text="⬇ Сохранить", command=self.save_pcap, state=tk.DISABLED)
        self.download_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.viewer_btn = ttk.Button(btn_frame, text="👁 Просмотр", command=self.open_viewer, state=tk.DISABLED)
        self.viewer_btn.pack(side=tk.LEFT)
    
    def create_viewer_tab(self, parent):
        mainframe = ttk.Frame(parent, padding="20")
        mainframe.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(mainframe, text="Просмотр PCAP файла:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(0, 10))
        
        btn_frame = ttk.Frame(mainframe)
        btn_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Button(btn_frame, text="📂 Открыть PCAP", command=self.load_pcap_file).pack(side=tk.LEFT, padx=(0, 10))
        self.pcap_status = ttk.Label(btn_frame, text="Файл не загружен", foreground="red")
        self.pcap_status.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.viewer_notebook = ttk.Notebook(mainframe)
        self.viewer_notebook.pack(fill=tk.BOTH, expand=True)
        
        frame_params = ttk.Frame(self.viewer_notebook)
        self.viewer_notebook.add(frame_params, text="Параметры")
        self.params_text = tk.Text(frame_params, height=20, width=80, state=tk.DISABLED)
        self.params_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        frame_osc = ttk.Frame(self.viewer_notebook)
        self.viewer_notebook.add(frame_osc, text="Осциллограмма")
        self.osc_canvas_frame = frame_osc
        
        frame_vector = ttk.Frame(self.viewer_notebook)
        self.viewer_notebook.add(frame_vector, text="Векторная диаграмма")
        self.vector_canvas_frame = frame_vector
    
    def load_cfg(self):
        file = filedialog.askopenfilename(filetypes=[("CFG files", "*.cfg"), ("All files", "*.*")])
        if file:
            self.cfg_file = file
            self.cfg_label.config(text=os.path.basename(file), foreground="green")
            
            base_name = Path(file).stem
            dat_file = Path(file).parent / (base_name + ".dat")
            if dat_file.exists():
                self.dat_file = str(dat_file)
                self.dat_label.config(text=os.path.basename(str(dat_file)), foreground="green")
            
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    cfg = parse_cfg(f.read())
                self.channels = cfg['channels']
                self.update_mapping_table()
                self.auto_detect()
                self.status_label.config(text=f"✓ CFG загружен ({len(self.channels)} каналов)", foreground="green")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")
    
    def load_dat(self):
        file = filedialog.askopenfilename(filetypes=[("DAT files", "*.dat"), ("All files", "*.*")])
        if file:
            self.dat_file = file
            self.dat_label.config(text=os.path.basename(file), foreground="green")
            
            base_name = Path(file).stem
            cfg_file = Path(file).parent / (base_name + ".cfg")
            if cfg_file.exists():
                self.cfg_file = str(cfg_file)
                self.cfg_label.config(text=os.path.basename(str(cfg_file)), foreground="green")
                
                try:
                    with open(str(cfg_file), 'r', encoding='utf-8') as f:
                        cfg = parse_cfg(f.read())
                    self.channels = cfg['channels']
                    self.update_mapping_table()
                    self.auto_detect()
                    self.status_label.config(text=f"✓ Файлы загружены", foreground="green")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")
    
    def load_pcap_file(self):
        file = filedialog.askopenfilename(filetypes=[("PCAP files", "*.pcap"), ("All files", "*.*")])
        if file:
            self.pcap_file = file
            self.pcap_status.config(text=f"✓ {os.path.basename(file)}", foreground="green")
            
            try:
                self.analyzer = PCAPAnalyzer(file)
                n_frames = self.analyzer.parse()
                self.show_pcap_params()
                self.plot_oscillogram()
                self.plot_phasor()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка анализа: {str(e)}")
    
    def show_pcap_params(self):
        if not self.analyzer:
            return
        
        info = "Параметры сигнала:\n\n"
        rms_values = self.analyzer.get_rms_values()
        
        info += "RMS значения ТОКОВ:\n"
        for role in ['Ia', 'Ib', 'Ic', 'In']:
            if role in rms_values:
                info += f"  {role}: {rms_values[role]:.2f} A\n"
        
        info += "\nRMS значения НАПРЯЖЕНИЙ:\n"
        for role in ['Ua', 'Ub', 'Uc', 'Un']:
            if role in rms_values:
                info += f"  {role}: {rms_values[role]:.2f} V\n"

        info += f"\nЧастота: 50 Гц\n"
        if self.analyzer and 'Ia' in self.analyzer.values:
            info += f"Отсчетов: {len(self.analyzer.values['Ia'])}\n"
        else:
            info += "Отсчетов: нет данных\n"
        
        self.params_text.config(state=tk.NORMAL)
        self.params_text.delete(1.0, tk.END)
        self.params_text.insert(1.0, info)
        self.params_text.config(state=tk.DISABLED)
    
    def plot_oscillogram(self):
        if not self.analyzer:
            return
        
        for widget in self.osc_canvas_frame.winfo_children():
            widget.destroy()
        
        time_axis = self.analyzer.get_time_axis()
        canvas, fig = PlotGenerator.create_oscillogram(
            self.osc_canvas_frame, time_axis, self.analyzer.values,
            roles=['Ia', 'Ib', 'Ic', 'Ua', 'Ub', 'Uc']
        )
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def plot_phasor(self):
        if not self.analyzer:
            return
        
        for widget in self.vector_canvas_frame.winfo_children():
            widget.destroy()
        
        rms_values = self.analyzer.get_rms_values()
        phases = self.analyzer.get_phase_angles()
        
        canvas, fig = PlotGenerator.create_phasor_diagram_3d(
            self.vector_canvas_frame, rms_values, phases
        )
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def update_mapping_table(self):
        for item in self.mapping_tree.get_children():
            self.mapping_tree.delete(item)

        for role in ROLE_ORDER:
            ch_idx = self.mapping.get(role)
            if ch_idx is not None and ch_idx < len(self.channels):
                ch = self.channels[ch_idx]
                channel_str = f"{ch_idx}: {ch['name']} ({ch['unit']})"
            else:
                channel_str = "-- не выбран --"

            role_type = "Ток (А)" if ROLE_IS_CURRENT[role] else "Напряжение (В)"
            self.mapping_tree.insert('', 'end', values=(role, channel_str, role_type))

    def update_mapping_table2(self):
        for item in self.mapping_tree2.get_children():
            self.mapping_tree2.delete(item)

        for role in ROLE_ORDER:
            ch_idx = self.mapping2.get(role)
            if ch_idx is not None and ch_idx < len(self.channels2):
                ch = self.channels2[ch_idx]
                channel_str = f"{ch_idx}: {ch['name']} ({ch['unit']})"
            else:
                channel_str = "-- не выбран --"

            role_type = "Ток (А)" if ROLE_IS_CURRENT[role] else "Напряжение (В)"
            self.mapping_tree2.insert('', 'end', values=(role, channel_str, role_type))
    
    def auto_detect(self):
        if not self.channels:
            messagebox.showwarning("Предупреждение", "Загрузите CFG файл")
            return
        
        self.mapping = guess_mapping(self.channels)
        self.update_mapping_table()
    
    def edit_mapping(self):
        selection = self.mapping_tree.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите параметр")
            return

        item = selection[0]
        role = self.mapping_tree.item(item)['values'][0]

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Выберите канал для {role}")
        dialog.geometry("400x300")

        ttk.Label(dialog, text=f"Выберите канал для '{role}':", font=("Arial", 11, "bold")).pack(padx=10, pady=10)

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

    def edit_mapping2(self):
        selection = self.mapping_tree2.selection()
        if not selection:
            messagebox.showwarning("Предупреждение", "Выберите параметр")
            return

        item = selection[0]
        role = self.mapping_tree2.item(item)['values'][0]

        dialog = tk.Toplevel(self.root)
        dialog.title(f"Выберите канал для {role} (Поток 2)")
        dialog.geometry("400x300")

        ttk.Label(dialog, text=f"Выберите канал для '{role}':", font=("Arial", 11, "bold")).pack(padx=10, pady=10)

        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        for i, ch in enumerate(self.channels2):
            listbox.insert(tk.END, f"{i}: {ch['name']} ({ch['unit']}) - {ch['phase']}")

        def select_channel():
            selection = listbox.curselection()
            if selection:
                self.mapping2[role] = selection[0]
                self.update_mapping_table2()
                dialog.destroy()

        ttk.Button(dialog, text="Выбрать", command=select_channel).pack(pady=10)
    
    def start_convert(self):
        if not self.cfg_file or not self.dat_file:
            messagebox.showerror("Ошибка", "Загрузите хотя бы первый поток")
            return

        # Проверяем, есть ли второй поток
        has_second_stream = self.cfg_file2 and self.dat_file2

        if None in self.mapping.values():
            messagebox.showerror("Ошибка", "Сопоставьте все каналы первого потока")
            return

        if has_second_stream and None in self.mapping2.values():
            messagebox.showerror("Ошибка", "Сопоставьте все каналы второго потока")
            return

        try:
            params = {
                'mac': self.params['mac'].get(),
                'appid': self.params['appid'].get(),
                'vlanid': '0',
                'vlan_pcp': 4,
                'svid': 'RET61850_SV1',
                'confrev': 1,
                'simulation': self.params['simulation'].get(),
                'ktt': float(self.params['ktt'].get()),
                'ktn': float(self.params['ktn'].get()),
                'k3i0': 1000,
                'k3u0': 1905.2,
            }
        except ValueError as e:
            messagebox.showerror("Ошибка", f"Ошибка параметров: {str(e)}")
            return

        self.convert_btn.config(state=tk.DISABLED)
        self.dual_mode = has_second_stream
        thread = threading.Thread(target=self.do_convert, args=(params,), daemon=True)
        thread.start()

    def do_convert(self, params):
        try:
            self.progress_label.config(text="Загрузка файлов...", foreground="blue")
            self.progress['value'] = 20
            self.root.update()

            cfg_text = None
            dat_text = None
            cfg_text2 = None
            dat_text2 = None

            try:
                with open(self.cfg_file, 'r', encoding='utf-8') as f:
                    cfg_text = f.read()
                with open(self.dat_file, 'r', encoding='utf-8') as f:
                    dat_text = f.read()

                if self.dual_mode:
                    with open(self.cfg_file2, 'r', encoding='utf-8') as f:
                        cfg_text2 = f.read()
                    with open(self.dat_file2, 'r', encoding='utf-8') as f:
                        dat_text2 = f.read()
            except IOError as e:
                raise ValueError(f'Ошибка чтения файлов: {str(e)}')

            self.progress_label.config(text="Конвертация...", foreground="blue")
            self.progress['value'] = 50
            self.root.update()

            if self.dual_mode:
                # Конвертируем два потока одновременно
                params2 = params.copy()
                params2['svid'] = 'RET61850_SV2'
                pcap_bytes, n_frames = convert_dual_stream(
                    cfg_text, dat_text, self.mapping, params,
                    cfg_text2, dat_text2, self.mapping2, params2
                )
            else:
                # Конвертируем один поток
                pcap_bytes, n_frames = convert(cfg_text, dat_text, self.mapping, params)

            self.progress_label.config(text=f"✓ Готово! {n_frames} кадров", foreground="green")
            self.progress['value'] = 100
            self.download_btn.config(state=tk.NORMAL)
            self.viewer_btn.config(state=tk.NORMAL)
            self.pcap_data = pcap_bytes

            if self.dual_mode:
                messagebox.showinfo("Успех", f"Конвертация завершена!\nДва потока синхронизированы\n{n_frames} кадров")
            else:
                messagebox.showinfo("Успех", f"Конвертация завершена!\n{n_frames} кадров")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")
            self.progress_label.config(text=f"✗ Ошибка", foreground="red")
        finally:
            self.convert_btn.config(state=tk.NORMAL)
    
    def save_pcap(self):
        if not self.pcap_data:
            messagebox.showerror("Ошибка", "Нет данных")
            return
        
        file = filedialog.asksaveasfilename(defaultextension=".pcap", filetypes=[("PCAP files", "*.pcap")])
        if file:
            try:
                with open(file, 'wb') as f:
                    f.write(self.pcap_data)
                messagebox.showinfo("Успех", f"Файл сохранён:\n{file}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")
    
    def load_cfg2(self):
        file = filedialog.askopenfilename(filetypes=[("CFG files", "*.cfg"), ("All files", "*.*")])
        if file:
            self.cfg_file2 = file
            self.cfg_label2.config(text=os.path.basename(file), foreground="green")

            base_name = Path(file).stem
            dat_file = Path(file).parent / (base_name + ".dat")
            if dat_file.exists():
                self.dat_file2 = str(dat_file)
                self.dat_label2.config(text=os.path.basename(str(dat_file)), foreground="green")

            try:
                with open(file, 'r', encoding='utf-8') as f:
                    cfg = parse_cfg(f.read())
                self.channels2 = cfg['channels']
                self.auto_detect2()
                self.status_label.config(text=f"✓ Потоки загружены", foreground="green")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")

    def load_dat2(self):
        file = filedialog.askopenfilename(filetypes=[("DAT files", "*.dat"), ("All files", "*.*")])
        if file:
            self.dat_file2 = file
            self.dat_label2.config(text=os.path.basename(file), foreground="green")

            base_name = Path(file).stem
            cfg_file = Path(file).parent / (base_name + ".cfg")
            if cfg_file.exists():
                self.cfg_file2 = str(cfg_file)
                self.cfg_label2.config(text=os.path.basename(str(cfg_file)), foreground="green")

                try:
                    with open(str(cfg_file), 'r', encoding='utf-8') as f:
                        cfg = parse_cfg(f.read())
                    self.channels2 = cfg['channels']
                    self.auto_detect2()
                    self.status_label.config(text=f"✓ Потоки загружены", foreground="green")
                except Exception as e:
                    messagebox.showerror("Ошибка", f"Ошибка: {str(e)}")

    def auto_detect2(self):
        if not self.channels2:
            messagebox.showwarning("Предупреждение", "Загрузите CFG файл для потока 2")
            return

        self.mapping2 = guess_mapping(self.channels2)
        self.update_mapping_table2()

    def open_viewer(self):
        self.notebook.select(2)


if __name__ == "__main__":
    root = tk.Tk()
    app = SVConverterGUI(root)
    root.mainloop()
