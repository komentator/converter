# -*- coding: utf-8 -*-
"""
Точный расчёт коэффициентов из эталонного PCAP
"""

import sys
import struct
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

# Эталонные значения Frame 1 (smpCnt=215)
expected_sv1_215 = [245576, 967379, 2121320, 3636156, -270133, -1064118, -2333453, -6927809]
expected_sv2_215 = [5416752, 7348469, 9302482, 11141828, -5958428, -8083317, -10232731, -21228036]

# Эталонные значения Frame 3 (smpCnt=216)
expected_sv1_216 = [354091, 1172930, 2403058, 3964941, -149101, -831451, -2009155, -6258676]
expected_sv2_216 = [5756666, 7658690, 9539455, 11261622, -5547787, -7692237, -9908973, -20868918]

sample_idx_1 = 215
sample_idx_2 = 216

roles = ['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']

print("="*80)
print("ТОЧНЫЙ РАСЧЁТ КОЭФФИЦИЕНТОВ ИЗ ЭТАЛОННОГО PCAP")
print("="*80)

# SV1
print("\n--- SV1 (каналы 0-7) ---")
coeffs_sv1 = {}

for i, role in enumerate(roles):
    ch = channels[i]
    mult = ch.get('mult', 1.0)

    # Два сэмпла
    row1 = rows[sample_idx_1]
    row2 = rows[sample_idx_2]

    sec1 = float(row1[i]) * mult
    sec2 = float(row2[i]) * mult

    exp1 = expected_sv1_215[i]
    exp2 = expected_sv1_216[i]

    is_current = role in ['Ia', 'Ib', 'Ic', 'In']
    scale = 1000 if is_current else 100

    # K = expected / (secondary * scale)
    if sec1 != 0 and sec2 != 0:
        k1 = exp1 / (sec1 * scale)
        k2 = exp2 / (sec2 * scale)
        k_avg = (k1 + k2) / 2
        coeffs_sv1[role] = k_avg
        print(f"{role}: K1={k1:10.3f}, K2={k2:10.3f}, avg={k_avg:10.3f}")

# SV2
print("\n--- SV2 (каналы 8-15) ---")
coeffs_sv2 = {}

for i, role in enumerate(roles):
    ch_idx = 8 + i
    ch = channels[ch_idx]
    mult = ch.get('mult', 1.0)

    row1 = rows[sample_idx_1]
    row2 = rows[sample_idx_2]

    sec1 = float(row1[ch_idx]) * mult
    sec2 = float(row2[ch_idx]) * mult

    exp1 = expected_sv2_215[i]
    exp2 = expected_sv2_216[i]

    is_current = role in ['Ia', 'Ib', 'Ic', 'In']
    scale = 1000 if is_current else 100

    if sec1 != 0 and sec2 != 0:
        k1 = exp1 / (sec1 * scale)
        k2 = exp2 / (sec2 * scale)
        k_avg = (k1 + k2) / 2
        coeffs_sv2[role] = k_avg
        print(f"{role}: K1={k1:10.3f}, K2={k2:10.3f}, avg={k_avg:10.3f}")

print("\n" + "="*80)
print("ФИНАЛЬНЫЕ КОЭФФИЦИЕНТЫ:")
print("="*80)

print(f"""
params1 = {{
    'ktt': {coeffs_sv1['Ia']:.3f},    # Ia
    'ktn': {coeffs_sv1['Ua']:.3f},    # Ua
    'k3i0': {coeffs_sv1['In']:.3f},   # In
    'k3u0': {coeffs_sv1['Un']:.3f},   # Un
}}

params2 = {{
    'ktt': {coeffs_sv2['Ia']:.3f},    # Ia
    'ktn': {coeffs_sv2['Ua']:.3f},    # Ua
    'k3i0': {coeffs_sv2['In']:.3f},   # In
    'k3u0': {coeffs_sv2['Un']:.3f},   # Un
}}

ВАЖНО: Для каждого канала свой коэффициент!
SV1: Ia={coeffs_sv1['Ia']:.1f}, Ib={coeffs_sv1['Ib']:.1f}, Ic={coeffs_sv1['Ic']:.1f}, In={coeffs_sv1['In']:.1f}
     Ua={coeffs_sv1['Ua']:.1f}, Ub={coeffs_sv1['Ub']:.1f}, Uc={coeffs_sv1['Uc']:.1f}, Un={coeffs_sv1['Un']:.1f}

SV2: Ia={coeffs_sv2['Ia']:.1f}, Ib={coeffs_sv2['Ib']:.1f}, Ic={coeffs_sv2['Ic']:.1f}, In={coeffs_sv2['In']:.1f}
     Ua={coeffs_sv2['Ua']:.1f}, Ub={coeffs_sv2['Ub']:.1f}, Uc={coeffs_sv2['Uc']:.1f}, Un={coeffs_sv2['Un']:.1f}
""")
