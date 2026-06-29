# -*- coding: utf-8 -*-
"""
Финальный тест: используем точные коэффициенты из анализа
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

# Точные коэффициенты из find_exact_coefficients.py (RAW mode)
# Для SV1 (каналы 0-7):
K_sv1 = {
    'Ia': -0.003045,
    'Ib': -0.010703,
    'Ic': -0.022974,
    'In': -0.040444,
    'Ua':  0.024455,
    'Ub':  0.124848,
    'Uc':  0.341676,
    'Un':  1.340672,
}

# Эталонные значения из Frame 1 (smpCnt=215)
expected_sv1 = {
    'Ia': 245576, 'Ib': 967379, 'Ic': 2121320, 'In': 3636156,
    'Ua': -270133, 'Ub': -1064118, 'Uc': -2333453, 'Un': -6927809,
}

sample_idx = 215
row = rows[sample_idx]

print("="*80)
print(f"ПРОВЕРКА с RAW коэффициентами (sample {sample_idx})")
print("="*80)

roles = ['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']

for i, role in enumerate(roles):
    raw = row[i]
    K = K_sv1[role]

    is_current = role in ['Ia', 'Ib', 'Ic', 'In']
    scale = 1000 if is_current else 100

    # Формула: SV_value = raw * K * scale
    sv_value = int(round(raw * K * scale))

    expected = expected_sv1[role]
    diff = sv_value - expected
    diff_pct = abs(diff / expected * 100) if expected != 0 else 0

    match = "[OK]" if abs(diff_pct) < 0.1 else "[DIFF]"

    print(f"{match} {role}: raw={raw:7d}, K={K:10.6f}, sv={sv_value:10d}, "
          f"exp={expected:10d}, diff={diff:6d} ({diff_pct:5.2f}%)")

print("\n" + "="*80)
print("ВЫВОД: Нужно использовать RAW значения напрямую, БЕЗ mult из CFG!")
print("       Формула: SV_value = raw * K_channel * scale")
print("="*80)
