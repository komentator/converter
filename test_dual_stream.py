# -*- coding: utf-8 -*-
"""
Тестовый скрипт для генерации двух SV потоков из одной осциллограммы
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from converter import convert_dual, ROLE_ORDER

# Пути к файлам
CFG_FILE = r"D:\Projects\add\Осциллограмма того, что подаем.cfg"
DAT_FILE = r"D:\Projects\add\Осциллограмма того, что подаем.dat"
OUTPUT_PCAP = r"D:\Projects\add\generated_dual_stream.pcap"

# Читаем файлы
with open(CFG_FILE, 'r', encoding='utf-8') as f:
    cfg_text = f.read()

with open(DAT_FILE, 'r', encoding='utf-8') as f:
    dat_text = f.read()

# Маппинг каналов
# Поток 1 (SV1): каналы 1-8 (индексы 0-7)
mapping1 = {
    'Ia': 0,  # Канал 1: Ia (индекс 0)
    'Ib': 1,  # Канал 2: Ib
    'Ic': 2,  # Канал 3: Ic
    'In': 3,  # Канал 4: In
    'Ua': 4,  # Канал 5: Ua
    'Ub': 5,  # Канал 6: Ub
    'Uc': 6,  # Канал 7: Uc
    'Un': 7,  # Канал 8: Un
}

# Поток 2 (SV2): каналы 9-16 (индексы 8-15)
mapping2 = {
    'Ia': 8,   # Канал 9: Ia (индекс 8)
    'Ib': 9,   # Канал 10: Ib
    'Ic': 10,  # Канал 11: Ic
    'In': 11,  # Канал 12: In
    'Ua': 12,  # Канал 13: Ua
    'Ub': 13,  # Канал 14: Ub
    'Uc': 14,  # Канал 15: Uc
    'Un': 15,  # Канал 16: 3U0 (используем как Un)
}

# Параметры потока 1 (SV1)
params1 = {
    'mac': '01-0C-CD-04-00-01',
    'src_mac': '10-FF-E0-84-FE-34',
    'appid': '4000',
    'vlanid': '0',
    'vlan_pcp': 4,
    'svid': 'RET61850_SV1',
    'confrev': 1,
    'simulation': False,
    'ktt': 1010.0,
    'ktn': 1600.0,
    'k3i0': 1960.0,
    'k3u0': 7760.0,
}

# Параметры потока 2 (SV2)
params2 = {
    'mac': '01-0C-CD-04-00-02',
    'src_mac': '10-FF-E0-84-FE-34',
    'appid': '4001',
    'vlanid': '0',
    'vlan_pcp': 4,
    'svid': 'RET61850_SV2',
    'confrev': 1,
    'simulation': False,
    'ktt': 3260.0,
    'ktn': 13280.0,
    'k3i0': 5370.0,
    'k3u0': 25390.0,
}

# Начальный smpCnt (из эталонного фрейма)
SMP_CNT_START = 215

print("[INFO] Запуск конвертации...")
print(f"[INFO] CFG: {CFG_FILE}")
print(f"[INFO] DAT: {DAT_FILE}")
print(f"[INFO] Поток 1: {params1['svid']} (MAC: {params1['mac']}, APPID: {params1['appid']})")
print(f"[INFO] Поток 2: {params2['svid']} (MAC: {params2['mac']}, APPID: {params2['appid']})")

try:
    pcap_bytes, frame_count = convert_dual(
        cfg_text, dat_text,
        mapping1, mapping2,
        params1, params2,
        smp_cnt_start=SMP_CNT_START
    )

    # Сохраняем результат
    with open(OUTPUT_PCAP, 'wb') as f:
        f.write(pcap_bytes)

    print(f"\n[SUCCESS] Конвертация завершена!")
    print(f"[INFO] Сгенерировано фреймов: {frame_count}")
    print(f"[INFO] Из них SV1: {frame_count // 2}, SV2: {frame_count // 2}")
    print(f"[INFO] Размер файла: {len(pcap_bytes) / 1024:.2f} KB")
    print(f"[INFO] Результат сохранён: {OUTPUT_PCAP}")
    print(f"\n[INFO] Откройте файл в Wireshark и примените фильтры:")
    print(f"       SV1: eth.dst == 01:0c:cd:04:00:01")
    print(f"       SV2: eth.dst == 01:0c:cd:04:00:02")

except Exception as e:
    print(f"\n[ERROR] Ошибка при конвертации:")
    print(f"        {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
