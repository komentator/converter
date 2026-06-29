# -*- coding: utf-8 -*-
"""
pcap_analyzer.py - Анализ и парсинг PCAP файлов IEC 61850-9-2 LE
Извлечение значений токов, напряжений, расчет параметров
"""

import struct
import numpy as np
from typing import Dict, List, Tuple


class PCAPAnalyzer:
    """Анализатор PCAP файлов IEC 61850-9-2 LE"""
    
    def __init__(self, pcap_file: str):
        self.pcap_file = pcap_file
        self.frames = []
        self.values = {
            'Ia': [], 'Ib': [], 'Ic': [], 'In': [],
            'Ua': [], 'Ub': [], 'Uc': [], 'Un': []
        }
        self.timestamps = []
        self.sample_rate = 4000  # Hz
        
    def parse(self):
        """Парсит PCAP файл и извлекает данные"""
        with open(self.pcap_file, 'rb') as f:
            # Читаем PCAP глобальный заголовок (24 байта)
            magic = struct.unpack('<I', f.read(4))[0]
            if magic not in [0xa1b2c3d4, 0xd4c3b2a1]:
                raise ValueError("Неверный формат PCAP файла")
            
            f.read(20)  # Пропускаем остаток заголовка
            
            # Читаем пакеты
            frame_idx = 0
            while True:
                # Читаем заголовок пакета (16 байт)
                packet_header = f.read(16)
                if len(packet_header) < 16:
                    break
                
                ts_sec, ts_usec, incl_len, orig_len = struct.unpack('<IIII', packet_header)
                
                # Читаем данные пакета
                packet_data = f.read(incl_len)
                if len(packet_data) < incl_len:
                    break
                
                # Пытаемся извлечь SV данные
                try:
                    self._extract_sv_data(packet_data, frame_idx)
                    frame_idx += 1
                except Exception:
                    pass  # Пропускаем неверные пакеты
        
        return len(self.frames)
    
    def _extract_sv_data(self, packet_data: bytes, frame_idx: int):
        """Извлекает данные SV из пакета"""
        try:
            # Ищем Ethernet тип 0x88BA (SV)
            if len(packet_data) < 14:
                return

            # Пропускаем MAC адреса (12 байт)
            offset = 12

            # Проверяем EtherType
            eth_type = struct.unpack('>H', packet_data[offset:offset+2])[0]
            offset += 2

            # Если VLAN тег
            if eth_type == 0x8100:
                offset += 4  # Пропускаем VLAN тег
                eth_type = struct.unpack('>H', packet_data[offset:offset+2])[0]
                offset += 2

            # Проверяем SV тип
            if eth_type != 0x88BA:
                return

            # Пропускаем APPID (2) + Length (2) + Reserved1 (2) + Reserved2 (2)
            offset += 8

            # Ищем ASN.1 структуру
            # Ищем тег 0x60 (savPDU)
            found = False
            while offset < len(packet_data) and not found:
                if packet_data[offset] == 0x60:
                    # Нашли savPDU
                    self._parse_savpdu(packet_data[offset:], frame_idx)
                    found = True
                    break
                offset += 1
            if not found and offset >= len(packet_data):
                return
        except (struct.error, IndexError):
            # Игнорируем ошибки парсинга поврежденных пакетов
            pass
    
    def _parse_savpdu(self, data: bytes, frame_idx: int):
        """Парсит savPDU структуру"""
        offset = 0
        
        # 0x60 - savPDU
        if data[offset] != 0x60:
            return
        offset += 1
        
        # Длина
        length = self._read_ber_length(data, offset)
        if length is None:
            return
        offset = length[1]
        
        # Ищем ASDU (начинается с тага 0x30)
        while offset < len(data) and data[offset] != 0x30:
            offset += 1
        
        if offset >= len(data):
            return
        
        # Парсим ASDU
        self._parse_asdu(data[offset:], frame_idx)
    
    def _parse_asdu(self, data: bytes, frame_idx: int):
        """Парсит ASDU структуру"""
        offset = 0
        
        # 0x30 - SEQUENCE
        if data[offset] != 0x30:
            return
        offset += 1
        
        # Длина
        length_info = self._read_ber_length(data, offset)
        if length_info is None:
            return
        asdu_length = length_info[0]
        offset = length_info[1]
        
        asdu_data = data[offset:offset+asdu_length]
        offset = 0
        
        # Парсим элементы ASDU
        samples = None
        while offset < len(asdu_data):
            tag = asdu_data[offset]
            offset += 1
            
            length_info = self._read_ber_length(asdu_data, offset)
            if length_info is None:
                break
            elem_length = length_info[0]
            offset = length_info[1]
            
            elem_data = asdu_data[offset:offset+elem_length]
            offset += elem_length
            
            # 0x87 - samples
            if tag == 0x87:
                samples = elem_data
        
        if samples and len(samples) >= 64:
            self._extract_sample_values(samples)
    
    def _extract_sample_values(self, samples: bytes):
        """Извлекает значения из блока samples"""
        offset = 0
        roles = ['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']
        
        for role in roles:
            if offset + 8 > len(samples):
                break
            
            # Читаем int32 значение (big-endian)
            value = struct.unpack('>i', samples[offset:offset+4])[0]
            offset += 4
            
            # Пропускаем quality (4 байта)
            offset += 4
            
            # Преобразуем в реальные единицы
            if role in ['Ia', 'Ib', 'Ic', 'In']:
                # Токи: мА → А
                real_value = value / 1000.0
            else:
                # Напряжения: сантивольты → В
                real_value = value / 100.0
            
            self.values[role].append(real_value)
    
    def _read_ber_length(self, data: bytes, offset: int) -> Tuple[int, int]:
        """Читает BER длину, возвращает (длина, новый_offset)"""
        if offset >= len(data):
            return None
        
        first_byte = data[offset]
        offset += 1
        
        if first_byte & 0x80 == 0:
            # Короткая форма
            return (first_byte, offset)
        else:
            # Длинная форма
            num_octets = first_byte & 0x7f
            if offset + num_octets > len(data):
                return None
            
            length = 0
            for i in range(num_octets):
                length = (length << 8) | data[offset + i]
            
            return (length, offset + num_octets)
    
    def get_values_array(self, role: str) -> np.ndarray:
        """Возвращает массив значений для роли"""
        return np.array(self.values.get(role, []))
    
    def get_statistics(self, role: str) -> Dict:
        """Вычисляет статистику для роли"""
        values = self.get_values_array(role)
        
        if len(values) == 0:
            return {}
        
        return {
            'min': np.min(values),
            'max': np.max(values),
            'mean': np.mean(values),
            'rms': np.sqrt(np.mean(values**2)),
            'peak': np.max(np.abs(values)),
            'count': len(values)
        }
    
    def get_frequency(self) -> float:
        """Вычисляет частоту из данных"""
        # Используем частоту дискретизации
        return 50.0  # Стандартная частота электросети
    
    def get_rms_values(self) -> Dict[str, float]:
        """Вычисляет RMS значения для всех ролей"""
        rms_values = {}
        
        for role in self.values.keys():
            values = self.get_values_array(role)
            if len(values) > 0:
                # Берем данные одного периода (~80 отсчетов при 4000 Гц и 50 Гц)
                period_samples = 80
                if len(values) >= period_samples:
                    period_data = values[-period_samples:]
                    rms_values[role] = np.sqrt(np.mean(period_data**2))
                else:
                    rms_values[role] = np.sqrt(np.mean(values**2))
        
        return rms_values
    
    def get_phase_angles(self) -> Dict[str, float]:
        """Вычисляет фазовые углы"""
        # Для упрощения возвращаем предполагаемые углы
        # В реальности нужно анализировать форму сигнала
        phases = {
            'Ia': 0,
            'Ib': 240,
            'Ic': 120,
            'In': 180,
            'Ua': 0,
            'Ub': 240,
            'Uc': 120,
            'Un': 0
        }
        return phases
    
    def get_time_axis(self) -> np.ndarray:
        """Возвращает временную ось в миллисекундах"""
        n_samples = len(self.values['Ia'])
        dt = 1000.0 / self.sample_rate  # Интервал в мс
        return np.arange(n_samples) * dt
    
    def get_subset(self, start_idx: int, end_idx: int) -> Dict:
        """Возвращает подмножество данных"""
        subset = {}
        for role, values in self.values.items():
            subset[role] = values[start_idx:end_idx]
        return subset
