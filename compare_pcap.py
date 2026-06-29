# -*- coding: utf-8 -*-
"""
Сравнение сгенерированного PCAP с эталонным
"""

def read_pcap_frames(filename, count=4):
    """Читает первые N фреймов из PCAP файла"""
    with open(filename, 'rb') as f:
        # Пропускаем PCAP заголовок (24 байта)
        pcap_header = f.read(24)

        frames = []
        for i in range(count):
            # Читаем заголовок пакета (16 байт)
            pkt_header = f.read(16)
            if len(pkt_header) < 16:
                break

            # Извлекаем длину пакета (2 значения - captured и original)
            import struct
            ts_sec, ts_usec, incl_len, orig_len = struct.unpack('<IIII', pkt_header)

            # Читаем данные пакета
            pkt_data = f.read(incl_len)
            frames.append(pkt_data)

        return frames

def compare_frames(frame1, frame2, label1="Frame1", label2="Frame2"):
    """Сравнивает два фрейма побайтно"""
    print(f"\n{'='*80}")
    print(f"Сравнение: {label1} vs {label2}")
    print(f"{'='*80}")

    if len(frame1) != len(frame2):
        print(f"ДЛИНА ОТЛИЧАЕТСЯ: {len(frame1)} vs {len(frame2)}")

    min_len = min(len(frame1), len(frame2))
    differences = []

    for i in range(min_len):
        if frame1[i] != frame2[i]:
            differences.append(i)

    if not differences:
        print("[OK] Фреймы ИДЕНТИЧНЫ")
        return True

    print(f"[DIFF] Найдено {len(differences)} отличий:")

    # Группируем отличия по диапазонам
    for offset in differences[:20]:  # Показываем первые 20 отличий
        print(f"  Offset {offset:04d} (0x{offset:04x}): "
              f"generated={frame1[offset]:02x} expected={frame2[offset]:02x}")

    if len(differences) > 20:
        print(f"  ... и ещё {len(differences) - 20} отличий")

    return False

# Эталонные фреймы из вашего сообщения
expected_frames_hex = [
    # Фрейм 1 (SV1, smpCnt=0x00d7)
    "01 0c cd 04 00 01 10 ff e0 84 fe 34 88 ba 40 00 "
    "00 6e 80 00 00 00 60 64 80 01 01 a2 5f 30 5d 80 "
    "0c 52 45 54 36 31 38 35 30 5f 53 56 31 82 02 00 "
    "d7 83 04 00 00 00 01 85 01 00 87 40 00 03 bf 48 "
    "00 00 00 00 00 0e c2 d3 00 00 00 00 00 20 5e 68 "
    "00 00 00 00 00 37 7b bc 00 00 00 00 ff fb e0 cb "
    "00 00 00 00 ff ef c3 4a 00 00 00 00 ff dc 64 f3 "
    "00 00 00 00 ff 96 4a 3f 00 00 00 00",

    # Фрейм 2 (SV2, smpCnt=0x00d7)
    "01 0c cd 04 00 02 10 ff e0 84 fe 34 88 ba 40 01 "
    "00 6e 80 00 00 00 60 64 80 01 01 a2 5f 30 5d 80 "
    "0c 52 45 54 36 31 38 35 30 5f 53 56 32 82 02 00 "
    "d7 83 04 00 00 00 01 85 01 00 87 40 00 52 a7 30 "
    "00 00 00 00 00 70 20 f5 00 00 00 00 00 8d f1 d2 "
    "00 00 00 00 00 aa 02 c4 00 00 00 00 ff a5 14 e4 "
    "00 00 00 00 ff 84 a8 8b 00 00 00 00 ff 63 dc 65 "
    "00 00 00 00 fe bc 15 fc 00 00 00 00",

    # Фрейм 3 (SV1, smpCnt=0x00d8)
    "01 0c cd 04 00 01 10 ff e0 84 fe 34 88 ba 40 00 "
    "00 6e 80 00 00 00 60 64 80 01 01 a2 5f 30 5d 80 "
    "0c 52 45 54 36 31 38 35 30 5f 53 56 31 82 02 00 "
    "d8 83 04 00 00 00 01 85 01 00 87 40 00 05 67 2b "
    "00 00 00 00 00 11 e5 c2 00 00 00 00 00 24 aa f2 "
    "00 00 00 00 00 3c 80 0d 00 00 00 00 ff fd b9 93 "
    "00 00 00 00 ff f3 50 25 00 00 00 00 ff e1 57 bd "
    "00 00 00 00 ff a0 80 0c 00 00 00 00",

    # Фрейм 4 (SV2, smpCnt=0x00d8)
    "01 0c cd 04 00 02 10 ff e0 84 fe 34 88 ba 40 01 "
    "00 6e 80 00 00 00 60 64 80 01 01 a2 5f 30 5d 80 "
    "0c 52 45 54 36 31 38 35 30 5f 53 56 32 82 02 00 "
    "d8 83 04 00 00 00 01 85 01 00 87 40 00 57 d6 fa "
    "00 00 00 00 00 74 dc c2 00 00 00 00 00 91 8f 7f "
    "00 00 00 00 00 ab d6 b6 00 00 00 00 ff ab 58 f5 "
    "00 00 00 00 ff 8a a0 33 00 00 00 00 ff 68 cd 13 "
    "00 00 00 00 fe c1 90 ca 00 00 00 00",
]

expected_frames = [bytes.fromhex(h.replace('\n', '')) for h in expected_frames_hex]

# Читаем сгенерированный файл
generated_file = r"D:\Projects\add\generated_dual_stream.pcap"
generated_frames = read_pcap_frames(generated_file, 4)

print(f"Прочитано {len(generated_frames)} фреймов из {generated_file}")
print(f"Эталонных фреймов: {len(expected_frames)}")

# Сравниваем каждый фрейм
all_match = True
for i in range(min(len(generated_frames), len(expected_frames))):
    match = compare_frames(
        generated_frames[i],
        expected_frames[i],
        f"Generated Frame {i+1}",
        f"Expected Frame {i+1}"
    )
    all_match = all_match and match

if all_match:
    print(f"\n{'='*80}")
    print("[SUCCESS] ВСЕ ФРЕЙМЫ ИДЕНТИЧНЫ! КОНВЕРТЕР РАБОТАЕТ ПРАВИЛЬНО!")
    print(f"{'='*80}")
else:
    print(f"\n{'='*80}")
    print("[ERROR] Есть отличия, требуется доработка")
    print(f"{'='*80}")
