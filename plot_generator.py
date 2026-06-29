# -*- coding: utf-8 -*-
"""
plot_generator.py - Генерация графиков осциллограмм и векторных диаграмм
Использует matplotlib для отрисовки
"""

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')  # Используем TkAgg для встраивания в Tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from typing import Dict, List


class PlotGenerator:
    """Генератор графиков для PCAP анализатора"""
    
    @staticmethod
    def create_oscillogram(parent, time_axis: np.ndarray, values_dict: Dict[str, List],
                          title: str = "Осциллограмма", roles: List[str] = None) -> FigureCanvasTkAgg:
        """Создает осциллограмму и встраивает в Tkinter окно"""
        
        if roles is None:
            roles = ['Ia', 'Ib', 'Ic', 'Ua', 'Ub', 'Uc']
        
        # Определяем количество подграфиков
        current_roles = [r for r in roles if r in values_dict and r[0] == 'I']
        voltage_roles = [r for r in roles if r in values_dict and r[0] == 'U']
        
        fig = Figure(figsize=(12, 8), dpi=100)
        
        # График токов
        if current_roles:
            ax1 = fig.add_subplot(2, 1, 1)
            for role in current_roles:
                if role in values_dict:
                    values = np.array(values_dict[role])
                    ax1.plot(time_axis, values, label=role, linewidth=2)
            
            ax1.set_xlabel('Время (мс)')
            ax1.set_ylabel('Ток (А)')
            ax1.set_title('Токи')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        # График напряжений
        if voltage_roles:
            ax2 = fig.add_subplot(2, 1, 2)
            for role in voltage_roles:
                if role in values_dict:
                    values = np.array(values_dict[role])
                    ax2.plot(time_axis, values, label=role, linewidth=2)
            
            ax2.set_xlabel('Время (мс)')
            ax2.set_ylabel('Напряжение (В)')
            ax2.set_title('Напряжения')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        fig.tight_layout()
        
        # Встраиваем в Tkinter
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        
        return canvas, fig
    
    @staticmethod
    def create_phasor_diagram(parent, rms_values: Dict[str, float], 
                             phases: Dict[str, float]) -> FigureCanvasTkAgg:
        """Создает векторную диаграмму"""
        
        fig = Figure(figsize=(10, 10), dpi=100)
        ax = fig.add_subplot(111, projection='polar')
        
        # Разделяем токи и напряжения
        current_roles = [r for r in rms_values.keys() if r[0] == 'I']
        voltage_roles = [r for r in rms_values.keys() if r[0] == 'U']
        
        colors_current = {'Ia': 'red', 'Ib': 'blue', 'Ic': 'green', 'In': 'black'}
        colors_voltage = {'Ua': 'red', 'Ub': 'blue', 'Uc': 'green', 'Un': 'gray'}
        
        # Рисуем токи
        for role in current_roles:
            if role in rms_values and role in phases:
                rms = rms_values[role]
                phase_rad = np.radians(phases[role])
                
                ax.arrow(0, 0, phase_rad, rms, head_width=0.1, 
                        head_length=50, fc=colors_current.get(role, 'black'),
                        ec=colors_current.get(role, 'black'), linewidth=2,
                        label=f"{role} ({rms:.1f}A)")
        
        # Добавляем напряжения с смещением для видимости
        for role in voltage_roles:
            if role in rms_values and role in phases:
                rms = rms_values[role] / 100  # Масштабируем для видимости
                phase_rad = np.radians(phases[role])
                
                ax.arrow(0, 0, phase_rad, rms, head_width=0.1,
                        head_length=5, fc=colors_voltage.get(role, 'gray'),
                        ec=colors_voltage.get(role, 'gray'), linewidth=1.5,
                        linestyle='--', label=f"{role} ({rms*100:.1f}V)")
        
        ax.set_ylim(0, 2000)
        ax.set_title('Векторная диаграмма токов и напряжений', pad=20)
        ax.legend(loc='upper left', bbox_to_anchor=(1.1, 1.0))
        
        fig.tight_layout()
        
        # Встраиваем в Tkinter
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        
        return canvas, fig
    
    @staticmethod
    def create_phasor_diagram_3d(parent, rms_values: Dict[str, float],
                                phases: Dict[str, float]) -> FigureCanvasTkAgg:
        """Создает 3D векторную диаграмму"""
        
        fig = Figure(figsize=(10, 8), dpi=100)
        
        # Две подграфика - для токов и напряжений
        ax1 = fig.add_subplot(1, 2, 1, projection='polar')
        ax2 = fig.add_subplot(1, 2, 2, projection='polar')
        
        # Только трехфазные токи
        current_roles = ['Ia', 'Ib', 'Ic']
        voltage_roles = ['Ua', 'Ub', 'Uc']
        
        colors = {'a': 'red', 'b': 'blue', 'c': 'green'}
        
        # Диаграмма токов
        for role in current_roles:
            if role in rms_values and role in phases:
                rms = rms_values[role]
                phase_rad = np.radians(phases[role])
                color = colors.get(role[-1], 'black')

                # Масштабируем head_length безопасно
                head_len = max(10, min(100, int(rms * 0.1))) if rms > 0 else 10
                ax1.arrow(0, 0, phase_rad, rms, head_width=0.15,
                         head_length=head_len, fc=color, ec=color,
                         linewidth=2.5, label=role)
        
        ax1.set_ylim(0, max([rms_values.get(r, 0) for r in current_roles]) * 1.3)
        ax1.set_title('Токи (А)', pad=10)
        ax1.legend(loc='upper left', bbox_to_anchor=(1.05, 1))
        
        # Диаграмма напряжений
        for role in voltage_roles:
            if role in rms_values and role in phases:
                rms = rms_values[role]
                phase_rad = np.radians(phases[role])
                color = colors.get(role[-1], 'black')

                # Масштабируем head_length безопасно
                head_len = max(50, min(500, int(rms * 0.1))) if rms > 0 else 50
                ax2.arrow(0, 0, phase_rad, rms, head_width=0.15,
                         head_length=head_len, fc=color, ec=color,
                         linewidth=2.5, label=role)
        
        ax2.set_ylim(0, max([rms_values.get(r, 0) for r in voltage_roles]) * 1.3)
        ax2.set_title('Напряжения (В)', pad=10)
        ax2.legend(loc='upper left', bbox_to_anchor=(1.05, 1))
        
        fig.tight_layout()
        
        # Встраиваем в Tkinter
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        
        return canvas, fig
    
    @staticmethod
    def create_single_phase_oscillogram(parent, time_axis: np.ndarray,
                                       values_dict: Dict[str, List],
                                       title: str = "Осциллограмма фазы") -> FigureCanvasTkAgg:
        """Создает осциллограмму одной фазы (I + U)"""
        
        fig = Figure(figsize=(12, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        # Берем первую доступную фазу (обычно фаза A)
        current_role = 'Ia'
        voltage_role = 'Ua'
        
        if current_role in values_dict:
            values = np.array(values_dict[current_role])
            ax.plot(time_axis, values, label=f'{current_role} (A)', 
                   color='red', linewidth=2)
        
        if voltage_role in values_dict:
            ax_twin = ax.twinx()
            values = np.array(values_dict[voltage_role])
            ax_twin.plot(time_axis, values, label=f'{voltage_role} (V)',
                        color='blue', linewidth=2)
            ax_twin.set_ylabel('Напряжение (В)', color='blue')
            ax_twin.tick_params(axis='y', labelcolor='blue')
        
        ax.set_xlabel('Время (мс)')
        ax.set_ylabel('Ток (А)', color='red')
        ax.tick_params(axis='y', labelcolor='red')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left')
        
        fig.tight_layout()
        
        # Встраиваем в Tkinter
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        
        return canvas, fig
    
    @staticmethod
    def create_harmonic_spectrum(parent, values_dict: Dict[str, List],
                                sample_rate: float = 4000) -> FigureCanvasTkAgg:
        """Создает спектр гармоник"""
        
        fig = Figure(figsize=(12, 6), dpi=100)
        ax = fig.add_subplot(111)
        
        for role in ['Ia', 'Ib', 'Ic']:
            if role in values_dict:
                values = np.array(values_dict[role])
                
                # FFT анализ
                fft = np.fft.fft(values)
                freqs = np.fft.fftfreq(len(values), 1/sample_rate)
                magnitude = np.abs(fft)
                
                # Берем только положительные частоты до 500 Гц
                idx = np.where((freqs >= 0) & (freqs <= 500))
                ax.plot(freqs[idx], magnitude[idx], label=role, linewidth=1.5)
        
        ax.set_xlabel('Частота (Гц)')
        ax.set_ylabel('Амплитуда')
        ax.set_title('Спектр гармоник')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        fig.tight_layout()
        
        # Встраиваем в Tkinter
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        
        return canvas, fig
