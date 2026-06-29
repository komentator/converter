# -*- coding: utf-8 -*-
"""
Проверка: что если ktt=ktn=k3i0=k3u0=1 ?
Тогда SV_value = secondary * 1 * scale
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

# Эталонные значения
expected_sv1 = {
    'Ia': 245576, 'Ib': 967379, 'Ic': 2121320, 'In': 3636156,
    'Ua': -270133, 'Ub': -1064118, 'Uc': -2333453, 'Un': -6927809,
}

sample_idx = 215
row = rows[sample_idx]

print("="*80)
print("ТЕСТ: ktt=ktn=k3i0=k3u0=1 (используем secondary напрямую)")
print("="*80)

roles = ['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']

for i, role in enumerate(roles):
    ch = channels[i]
    raw = row[i]
    mult = ch.get('mult', 1.0)
    secondary = float(raw) * mult

    is_current = role in ['Ia', 'Ib', 'Ic', 'In']
    scale = 1000 if is_current else 100

    # SV_value = secondary * 1.0 * scale
    sv_value = int(round(secondary * scale))

    expected = expected_sv1[role]
    diff = sv_value - expected

    # Вычисляем нужный коэффициент
    if secondary != 0:
        needed_k = expected / (secondary * scale)
    else:
        needed_k = 0

    print(f"{role}: raw={raw:7d}, sec={secondary:10.3f}, sv={sv_value:10d}, "
          f"exp={expected:10d}, needed_k={needed_k:8.3f}")

print("\n" + "="*80)
print("Вывод: secondary слишком малы, нужен большой коэффициент K")
print("="*80)
