# -*- coding: utf-8 -*-
"""
Точный подбор коэффициентов методом наименьших квадратов
"""

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

# Эталонные значения из двух фреймов
samples_data = [
    # smpCnt=215
    (215, {
        'Ia': 245576, 'Ib': 967379, 'Ic': 2121320, 'In': 3636156,
        'Ua': -270133, 'Ub': -1064118, 'Uc': -2333453, 'Un': -6927809,
    }),
    # smpCnt=216
    (216, {
        'Ia': 354091, 'Ib': 1172930, 'Ic': 2403058, 'In': 3964941,
        'Ua': -149101, 'Ub': -831451, 'Uc': -2009155, 'Un': -6258676,
    }),
]

roles = ['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']

print("="*80)
print("ТОЧНЫЙ ПОДБОР КОЭФФИЦИЕНТОВ (SV1, каналы 0-7)")
print("="*80)

# Для каждого канала найдём коэффициент K
for i, role in enumerate(roles):
    ch = channels[i]
    mult = ch.get('mult', 1.0)

    # Собираем данные для этого канала
    K_values = []

    for sample_idx, expected_dict in samples_data:
        row = rows[sample_idx]
        raw = row[i]
        secondary = float(raw) * mult
        expected = expected_dict[role]

        is_current = role in ['Ia', 'Ib', 'Ic', 'In']
        scale = 1000 if is_current else 100

        # expected = secondary * K * scale
        # K = expected / (secondary * scale)
        if secondary != 0:
            K = expected / (secondary * scale)
            K_values.append(K)

    # Среднее значение K
    if K_values:
        K_avg = sum(K_values) / len(K_values)
        K_std = (sum((k - K_avg)**2 for k in K_values) / len(K_values)) ** 0.5

        # Проверяем стабильность
        print(f"{role}: K={K_avg:10.3f} ± {K_std:8.3f}  (значения: {[f'{k:.1f}' for k in K_values]})")

print("\n" + "="*80)
print("ВЫВОД:")
print("="*80)
print("Коэффициенты НЕПОСТОЯННЫ между сэмплами!")
print("Это означает, что либо:")
print("1. В DAT файле уже применён какой-то коэффициент")
print("2. Нужно использовать RAW значения БЕЗ mult из CFG")
print("3. Mult в CFG уже включает коэффициент трансформации")

print("\n" + "="*80)
print("ПОПЫТКА 2: Используем RAW значения напрямую (игнорируем mult)")
print("="*80)

for i, role in enumerate(roles):
    K_values = []

    for sample_idx, expected_dict in samples_data:
        row = rows[sample_idx]
        raw = row[i]
        expected = expected_dict[role]

        is_current = role in ['Ia', 'Ib', 'Ic', 'In']
        scale = 1000 if is_current else 100

        # expected = raw * K * scale (без mult!)
        if raw != 0:
            K = expected / (raw * scale)
            K_values.append(K)

    if K_values:
        K_avg = sum(K_values) / len(K_values)
        K_std = (sum((k - K_avg)**2 for k in K_values) / len(K_values)) ** 0.5

        print(f"{role}: K={K_avg:10.6f} ± {K_std:10.6f}")
