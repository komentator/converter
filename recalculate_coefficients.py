# -*- coding: utf-8 -*-
"""
Пересчёт всех коэффициентов с корректировкой
"""

# Исходные коэффициенты из calculate_coefficients.py
original_sv1 = {
    'ktt': -344.843,
    'ktn': 546.857,
    'k3i0': -668.864,
    'k3u0': 2650.716,
}

original_sv2 = {
    'ktt': -1113.158,
    'ktn': -4535.070,
    'k3i0': -1834.867,
    'k3u0': -8670.607,
}

# Корректирующий коэффициент (из анализа Ia)
correction_factor = 1.92

print("="*80)
print("ПЕРЕСЧЁТ КОЭФФИЦИЕНТОВ")
print("="*80)
print(f"Корректирующий фактор: {correction_factor}")

print("\nSV1 (исходные -> скорректированные):")
sv1_corrected = {}
for k, v in original_sv1.items():
    corrected = v / correction_factor
    sv1_corrected[k] = corrected
    print(f"  {k}: {v:10.3f} -> {corrected:10.3f}")

print("\nSV2 (исходные -> скорректированные):")
sv2_corrected = {}
for k, v in original_sv2.items():
    corrected = v / correction_factor
    sv2_corrected[k] = corrected
    print(f"  {k}: {v:10.3f} -> {corrected:10.3f}")

print("\n" + "="*80)
print("ОБНОВЛЁННЫЕ ЗНАЧЕНИЯ ДЛЯ test_dual_stream.py:")
print("="*80)

print(f"""
params1 = {{
    'mac': '01-0C-CD-04-00-01',
    'src_mac': '10-FF-E0-84-FE-34',
    'appid': '4000',
    'vlanid': '0',
    'vlan_pcp': 4,
    'svid': 'RET61850_SV1',
    'confrev': 1,
    'simulation': False,
    'ktt': {sv1_corrected['ktt']:.3f},
    'ktn': {sv1_corrected['ktn']:.3f},
    'k3i0': {sv1_corrected['k3i0']:.3f},
    'k3u0': {sv1_corrected['k3u0']:.3f},
}}

params2 = {{
    'mac': '01-0C-CD-04-00-02',
    'src_mac': '10-FF-E0-84-FE-34',
    'appid': '4001',
    'vlanid': '0',
    'vlan_pcp': 4,
    'svid': 'RET61850_SV2',
    'confrev': 1,
    'simulation': False,
    'ktt': {sv2_corrected['ktt']:.3f},
    'ktn': {sv2_corrected['ktn']:.3f},
    'k3i0': {sv2_corrected['k3i0']:.3f},
    'k3u0': {sv2_corrected['k3u0']:.3f},
}}
""")
