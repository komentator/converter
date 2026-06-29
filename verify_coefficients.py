# -*- coding: utf-8 -*-
"""
Проверка коэффициентов на втором сэмпле (216)
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

# Эталонные значения из Frame 3 (smpCnt=216)
expected_sv1_216 = {
    'Ia': 354091,
    'Ib': 1172930,
    'Ic': 2403058,
    'In': 3964941,
    'Ua': -149101,
    'Ub': -831451,
    'Uc': -2009155,
    'Un': -6258676,
}

# Предложенные коэффициенты из предыдущего анализа (берём абсолютные значения)
ktt1 = 344.843
ktn1 = 546.857
k3i0_1 = 668.864
k3u0_1 = 2650.716

sample_idx = 216
row = rows[sample_idx]

print("="*80)
print(f"ПРОВЕРКА на сэмпле {sample_idx} (SV1)")
print("="*80)

roles = ['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']

for i, role in enumerate(roles):
    ch = channels[i]
    raw = row[i]
    mult = ch.get('mult', 1.0)
    offset = ch.get('offset', 0.0)
    secondary = float(raw) * mult + offset

    # Выбираем коэффициент
    if role in ['Ia', 'Ib', 'Ic']:
        K = ktt1
    elif role == 'In':
        K = k3i0_1
    elif role in ['Ua', 'Ub', 'Uc']:
        K = ktn1
    else:  # Un
        K = k3u0_1

    is_current = role in ['Ia', 'Ib', 'Ic', 'In']
    scale = 1000 if is_current else 100

    # Попробуем с инверсией знака secondary
    primary = -secondary * K  # ИНВЕРСИЯ!
    sv_value = int(round(primary * scale))

    expected = expected_sv1_216[role]
    diff = sv_value - expected
    diff_pct = (diff / expected * 100) if expected != 0 else 0

    print(f"{role}: raw={raw:7d}, sec={secondary:9.3f}, K={K:8.3f}, "
          f"sv={sv_value:10d}, exp={expected:10d}, diff={diff:8d} ({diff_pct:6.2f}%)")

print(f"\nВывод: нужна инверсия знака secondary!")
