# -*- coding: utf-8 -*-
"""
Подбор коэффициентов ktt, ktn, k3i0, k3u0 по эталонным значениям
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

# Эталонные значения из Frame 1 (smpCnt=215)
expected_sv1 = {
    'Ia': 245576,
    'Ib': 967379,
    'Ic': 2121320,
    'In': 3636156,
    'Ua': -270133,
    'Ub': -1064118,
    'Uc': -2333453,
    'Un': -6927809,
}

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

sample_idx = 215
row = rows[sample_idx]

print("="*80)
print("ПОДБОР КОЭФФИЦИЕНТОВ ДЛЯ SV1 (каналы 0-7)")
print("="*80)

# Для SV1
roles = ['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']
ktt_values = []
ktn_values = []
k3i0_value = None
k3u0_value = None

for i, role in enumerate(roles):
    ch = channels[i]
    raw = row[i]
    mult = ch.get('mult', 1.0)
    offset = ch.get('offset', 0.0)
    secondary = float(raw) * mult + offset

    expected = expected_sv1[role]
    is_current = role in ['Ia', 'Ib', 'Ic', 'In']
    scale = 1000 if is_current else 100

    # expected = secondary * K * scale
    # K = expected / (secondary * scale)
    if secondary != 0:
        K = expected / (secondary * scale)
    else:
        K = 0

    print(f"{role}: raw={raw:7d}, secondary={secondary:10.6f}, expected={expected:10d}, K={K:10.3f}")

    if role in ['Ia', 'Ib', 'Ic']:
        ktt_values.append(K)
    elif role == 'In':
        k3i0_value = K
    elif role in ['Ua', 'Ub', 'Uc']:
        ktn_values.append(K)
    elif role == 'Un':
        k3u0_value = K

ktt_avg = sum(ktt_values) / len(ktt_values) if ktt_values else 0
ktn_avg = sum(ktn_values) / len(ktn_values) if ktn_values else 0

print(f"\nРекомендуемые коэффициенты для SV1:")
print(f"  ktt  = {ktt_avg:.3f} (среднее от Ia, Ib, Ic)")
print(f"  ktn  = {ktn_avg:.3f} (среднее от Ua, Ub, Uc)")
print(f"  k3i0 = {k3i0_value:.3f} (из In)")
print(f"  k3u0 = {k3u0_value:.3f} (из Un)")

print("\n" + "="*80)
print("ПОДБОР КОЭФФИЦИЕНТОВ ДЛЯ SV2 (каналы 8-15)")
print("="*80)

ktt_values2 = []
ktn_values2 = []
k3i0_value2 = None
k3u0_value2 = None

for i, role in enumerate(roles):
    ch_idx = 8 + i
    ch = channels[ch_idx]
    raw = row[ch_idx]
    mult = ch.get('mult', 1.0)
    offset = ch.get('offset', 0.0)
    secondary = float(raw) * mult + offset

    expected = expected_sv2[role]
    is_current = role in ['Ia', 'Ib', 'Ic', 'In']
    scale = 1000 if is_current else 100

    if secondary != 0:
        K = expected / (secondary * scale)
    else:
        K = 0

    print(f"{role}: raw={raw:7d}, secondary={secondary:10.6f}, expected={expected:10d}, K={K:10.3f}")

    if role in ['Ia', 'Ib', 'Ic']:
        ktt_values2.append(K)
    elif role == 'In':
        k3i0_value2 = K
    elif role in ['Ua', 'Ub', 'Uc']:
        ktn_values2.append(K)
    elif role == 'Un':
        k3u0_value2 = K

ktt_avg2 = sum(ktt_values2) / len(ktt_values2) if ktt_values2 else 0
ktn_avg2 = sum(ktn_values2) / len(ktn_values2) if ktn_values2 else 0

print(f"\nРекомендуемые коэффициенты для SV2:")
print(f"  ktt  = {ktt_avg2:.3f} (среднее от Ia, Ib, Ic)")
print(f"  ktn  = {ktn_avg2:.3f} (среднее от Ua, Ub, Uc)")
print(f"  k3i0 = {k3i0_value2:.3f} (из In)")
print(f"  k3u0 = {k3u0_value2:.3f} (из Un)")
