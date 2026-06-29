# -*- coding: utf-8 -*-
"""
Анализ значений из эталонного фрейма для определения коэффициентов
"""

# Эталонные значения из Frame 1 (INT32)
expected_values = {
    'Ia': 245576,
    'Ib': 967379,
    'Ic': 2121320,
    'In': 3636156,
    'Ua': -270133,
    'Ub': -1064118,
    'Uc': -2333453,
    'Un': -6927809,
}

# Исходные значения из DAT файла (первая строка после 215 сэмпла)
# Нужно найти сэмпл 215 (0xd7)
import sys
sys.path.insert(0, r'D:\Projects\sv_converter')
from converter import parse_cfg, parse_dat_ascii

# Читаем CFG и DAT
with open(r'D:\Projects\add\Осциллограмма того, что подаем.cfg', 'r', encoding='utf-8') as f:
    cfg_text = f.read()

with open(r'D:\Projects\add\Осциллограмма того, что подаем.dat', 'r', encoding='utf-8') as f:
    dat_text = f.read()

cfg = parse_cfg(cfg_text)
channels = cfg['channels']
rows = parse_dat_ascii(dat_text, len(channels))

sample_rate = cfg['sample_rate']
print(f"Sample rate: {sample_rate} Hz")
print(f"Total samples: {len(rows)}")
print(f"smpCnt period: {int(sample_rate)}")

# Находим сэмпл с индексом 215 (0xd7)
sample_idx = 215
if sample_idx < len(rows):
    row = rows[sample_idx]
    print(f"\nСэмпл {sample_idx} (0x{sample_idx:04x}):")

    # Для SV1: каналы 0-7
    print("\n--- SV1 (каналы 0-7) ---")
    for i, role in enumerate(['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']):
        ch = channels[i]
        raw_value = row[i]
        mult = ch.get('mult', 1.0)
        offset = ch.get('offset', 0.0)
        secondary = float(raw_value) * mult + offset

        expected = expected_values[role]

        # Попытка найти коэффициент
        if secondary != 0:
            # Для токов: scale = 1000 (мА)
            # Для напряжений: scale = 100 (сантивольты)
            is_current = role in ['Ia', 'Ib', 'Ic', 'In']
            scale = 1000 if is_current else 100

            # Вычисляем что получится с разными ktt/ktn
            primary = secondary  # Уже применён mult из cfg

            # Попробуем найти ktt/ktn, который даст нужный результат
            # expected = primary * ktt * scale
            # ktt = expected / (primary * scale)
            if primary != 0:
                needed_k = expected / (primary * scale)
            else:
                needed_k = 0

            print(f"{role}: raw={raw_value:6d}, mult={mult:.6f}, secondary={secondary:10.3f}, "
                  f"expected={expected:10d}, needed_k={needed_k:10.3f}")
        else:
            print(f"{role}: raw={raw_value:6d}, mult={mult:.6f}, secondary={secondary:10.3f}, expected={expected:10d}")

    # Для SV2: каналы 8-15
    print("\n--- SV2 (каналы 8-15) ---")
    expected_sv2 = {
        'Ia': 5416752,
        'Ib': 7348469,
        'Ic': 9302482,
        'In': 11141828,
        'Ua': -5958428,
        'Ub': -8083317,
        'Uc': -10232731,
        'Un': -21228036,
    }

    for i, role in enumerate(['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']):
        ch_idx = 8 + i
        ch = channels[ch_idx]
        raw_value = row[ch_idx]
        mult = ch.get('mult', 1.0)
        offset = ch.get('offset', 0.0)
        secondary = float(raw_value) * mult + offset

        expected = expected_sv2[role]

        is_current = role in ['Ia', 'Ib', 'Ic', 'In']
        scale = 1000 if is_current else 100

        if secondary != 0:
            needed_k = expected / (secondary * scale)
        else:
            needed_k = 0

        print(f"{role}: raw={raw_value:6d}, mult={mult:.6f}, secondary={secondary:10.3f}, "
              f"expected={expected:10d}, needed_k={needed_k:10.3f}")
