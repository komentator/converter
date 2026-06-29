# -*- coding: utf-8 -*-
"""
Детальная проверка одного канала
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

sample_idx = 215
row = rows[sample_idx]

# Канал Ia (индекс 0)
role = 'Ia'
i = 0
ch = channels[i]
raw = row[i]
mult = ch.get('mult', 1.0)
secondary = float(raw) * mult

print("="*80)
print(f"Детальный анализ канала {role} (индекс {i})")
print("="*80)
print(f"raw = {raw}")
print(f"mult = {mult}")
print(f"secondary = raw * mult = {secondary}")

# Текущий подход
ktt = -344.843
scale = 1000
primary = secondary * ktt
sv_value = int(round(primary * scale))

print(f"\nТекущий подход:")
print(f"  ktt = {ktt}")
print(f"  primary = secondary * ktt = {primary}")
print(f"  sv_value = round(primary * {scale}) = {sv_value}")
print(f"  в hex: {sv_value & 0xffffffff:08x}")
print(f"  ожидается: 245576 (0x0003bf48)")

# Что если нужен положительный ktt?
ktt_pos = 344.843
primary_pos = secondary * ktt_pos
sv_value_pos = int(round(primary_pos * scale))

print(f"\nЕсли ktt положительный:")
print(f"  ktt = {ktt_pos}")
print(f"  primary = secondary * ktt = {primary_pos}")
print(f"  sv_value = round(primary * {scale}) = {sv_value_pos}")
print(f"  в hex: {sv_value_pos & 0xffffffff:08x}")

# Что если инвертировать secondary?
secondary_inv = -secondary
primary_inv = secondary_inv * ktt_pos
sv_value_inv = int(round(primary_inv * scale))

print(f"\nЕсли инвертировать secondary:")
print(f"  secondary = -{secondary} = {secondary_inv}")
print(f"  primary = secondary * ktt = {primary_inv}")
print(f"  sv_value = round(primary * {scale}) = {sv_value_inv}")
print(f"  в hex: {sv_value_inv & 0xffffffff:08x}")
print(f"  РАЗНИЦА: {sv_value_inv - 245576}")
