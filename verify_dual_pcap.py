# -*- coding: utf-8 -*-
"""
Верификация dual-stream PCAP файла
"""

import struct

PCAP_FILE = r"D:\Projects\add\generated_dual_stream.pcap"

def read_pcap_headers(filename):
    """Читает заголовки PCAP и проверяет структуру фреймов"""
    with open(filename, 'rb') as f:
        # Читаем глобальный заголовок PCAP (24 байта)
        global_header = f.read(24)

        frames = []
        prev_time = None

        while True:
            # Читаем заголовок пакета (16 байт)
            packet_header = f.read(16)
            if len(packet_header) < 16:
                break

            ts_sec, ts_usec, incl_len, orig_len = struct.unpack('<IIII', packet_header)
            timestamp_us = ts_sec * 1_000_000 + ts_usec

            # Читаем данные пакета
            packet_data = f.read(incl_len)

            # Парсим Ethernet заголовок
            dst_mac = ':'.join(f'{b:02x}' for b in packet_data[0:6])
            src_mac = ':'.join(f'{b:02x}' for b in packet_data[6:12])

            # Пропускаем VLAN если есть (0x8100)
            offset = 12
            if len(packet_data) > offset + 2:
                etype = struct.unpack('>H', packet_data[offset:offset+2])[0]
                if etype == 0x8100:
                    offset += 4  # Пропускаем VLAN tag

            # Читаем EtherType (должен быть 0x88BA для SV)
            if len(packet_data) > offset + 2:
                etype = struct.unpack('>H', packet_data[offset:offset+2])[0]
                offset += 2

                if etype == 0x88BA:
                    # Читаем SV заголовок
                    if len(packet_data) >= offset + 8:
                        appid, length, res1, res2 = struct.unpack('>HHHH', packet_data[offset:offset+8])
                        offset += 8

                        # Ищем smpCnt в ASDU (tag 0x82)
                        smp_cnt = None
                        svid = None

                        # Простой поиск тега 0x82 (smpCnt)
                        for i in range(offset, min(len(packet_data) - 3, offset + 100)):
                            if packet_data[i] == 0x82 and packet_data[i+1] == 0x02:
                                smp_cnt = struct.unpack('>H', packet_data[i+2:i+4])[0]
                                break

                        time_delta = timestamp_us - prev_time if prev_time is not None else 0

                        frames.append({
                            'time_us': timestamp_us,
                            'time_delta': time_delta,
                            'dst_mac': dst_mac,
                            'src_mac': src_mac,
                            'appid': f'0x{appid:04x}',
                            'smp_cnt': smp_cnt,
                            'size': incl_len
                        })

                        prev_time = timestamp_us

        return frames

print("[INFO] Анализ PCAP файла...")
print(f"[INFO] Файл: {PCAP_FILE}\n")

frames = read_pcap_headers(PCAP_FILE)

print(f"[INFO] Всего фреймов: {len(frames)}\n")

# Группируем по MAC адресу
sv1_frames = [f for f in frames if f['dst_mac'] == '01:0c:cd:04:00:01']
sv2_frames = [f for f in frames if f['dst_mac'] == '01:0c:cd:04:00:02']

print(f"[INFO] SV1 (MAC 01:0c:cd:04:00:01): {len(sv1_frames)} фреймов")
print(f"[INFO] SV2 (MAC 01:0c:cd:04:00:02): {len(sv2_frames)} фреймов\n")

# Показываем первые 10 фреймов
print("[INFO] Первые 10 фреймов (паттерн чередования):")
print("№   | Время (мкс) | Дельта  | MAC адрес         | APPID  | smpCnt")
print("----|-------------|---------|-------------------|--------|-------")

for i, frame in enumerate(frames[:10]):
    print(f"{i+1:3d} | {frame['time_us']:11d} | {frame['time_delta']:7d} | {frame['dst_mac']} | {frame['appid']} | {frame['smp_cnt']:5d}")

# Проверяем паттерн чередования
print("\n[INFO] Проверка паттерна чередования:")
pattern_ok = True
for i in range(0, min(20, len(frames) - 1), 2):
    f1 = frames[i]
    f2 = frames[i + 1]

    if f1['dst_mac'] != '01:0c:cd:04:00:01' or f2['dst_mac'] != '01:0c:cd:04:00:02':
        print(f"[ERROR] Фрейм {i+1}: неправильный порядок MAC адресов")
        pattern_ok = False

    if f1['smp_cnt'] != f2['smp_cnt']:
        print(f"[ERROR] Фрейм {i+1}: smpCnt не совпадает ({f1['smp_cnt']} != {f2['smp_cnt']})")
        pattern_ok = False

    if f2['time_delta'] > 10:
        print(f"[WARNING] Фрейм {i+2}: большая задержка между SV1 и SV2 ({f2['time_delta']} мкс)")

if pattern_ok:
    print("[SUCCESS] Паттерн чередования корректен!")
else:
    print("[ERROR] Обнаружены ошибки в паттерне!")

# Проверяем временные интервалы
print("\n[INFO] Анализ временных интервалов:")
sv1_deltas = [sv1_frames[i+1]['time_us'] - sv1_frames[i]['time_us'] for i in range(len(sv1_frames)-1)]
sv2_deltas = [sv2_frames[i+1]['time_us'] - sv2_frames[i]['time_us'] for i in range(len(sv2_frames)-1)]

if sv1_deltas:
    print(f"  SV1: мин={min(sv1_deltas)} мкс, макс={max(sv1_deltas)} мкс, среднее={sum(sv1_deltas)//len(sv1_deltas)} мкс")
if sv2_deltas:
    print(f"  SV2: мин={min(sv2_deltas)} мкс, макс={max(sv2_deltas)} мкс, среднее={sum(sv2_deltas)//len(sv2_deltas)} мкс")

print("\n[INFO] Проверка завершена!")
