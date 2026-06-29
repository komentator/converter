# -*- coding: utf-8 -*-
"""
Анализ целевых фреймов для понимания структуры
"""

frames_hex = [
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

def parse_frame(hex_str):
    """Парсит hex дамп фрейма"""
    data = bytes.fromhex(hex_str.replace('\n', ''))

    # Ethernet
    dst_mac = data[0:6]
    src_mac = data[6:12]
    ethertype = data[12:14]

    print(f"DST MAC: {dst_mac.hex(':')}")
    print(f"SRC MAC: {src_mac.hex(':')}")
    print(f"EtherType: {ethertype.hex()}")

    # APPID
    appid = int.from_bytes(data[14:16], 'big')
    print(f"APPID: 0x{appid:04x}")

    # Length
    length = int.from_bytes(data[16:18], 'big')
    print(f"Length: {length}")

    # Reserved fields
    res1 = data[18:20]
    res2 = data[20:22]
    print(f"Reserved1: {res1.hex()}")
    print(f"Reserved2: {res2.hex()}")

    # APDU (SavPdu)
    apdu_start = 22

    # SavPdu tag (0x60) + len
    savpdu_tag = data[apdu_start]
    savpdu_len = data[apdu_start+1]
    print(f"\nSavPdu: tag=0x{savpdu_tag:02x}, len={savpdu_len}")

    # noASDU tag (0x80) + len + val
    noasdu_start = apdu_start + 2
    noasdu_tag = data[noasdu_start]
    noasdu_len = data[noasdu_start+1]
    noasdu_val = data[noasdu_start+2]
    print(f"noASDU: tag=0x{noasdu_tag:02x}, len={noasdu_len}, val={noasdu_val}")

    # seqASDU tag (0xa2) + len
    seq_start = noasdu_start + 3
    seq_tag = data[seq_start]
    seq_len = data[seq_start+1]
    print(f"seqASDU: tag=0x{seq_tag:02x}, len={seq_len}")

    # ASDU (внутри seqASDU)
    asdu_start = seq_start + 2
    asdu_tag = data[asdu_start]
    asdu_len = data[asdu_start+1]
    print(f"ASDU: tag=0x{asdu_tag:02x}, len={asdu_len}")

    # svID
    svid_start = asdu_start + 2
    svid_tag = data[svid_start]
    svid_len = data[svid_start+1]
    svid_val = data[svid_start+2:svid_start+2+svid_len].decode('utf-8')
    print(f"svID: tag=0x{svid_tag:02x}, len={svid_len}, val='{svid_val}'")

    # smpCnt
    smpcnt_start = svid_start + 2 + svid_len
    smpcnt_tag = data[smpcnt_start]
    smpcnt_len = data[smpcnt_start+1]
    smpcnt_val = int.from_bytes(data[smpcnt_start+2:smpcnt_start+2+smpcnt_len], 'big')
    print(f"smpCnt: tag=0x{smpcnt_tag:02x}, len={smpcnt_len}, val=0x{smpcnt_val:04x} ({smpcnt_val})")

    # confRev
    confrev_start = smpcnt_start + 2 + smpcnt_len
    confrev_tag = data[confrev_start]
    confrev_len = data[confrev_start+1]
    confrev_val = int.from_bytes(data[confrev_start+2:confrev_start+2+confrev_len], 'big')
    print(f"confRev: tag=0x{confrev_tag:02x}, len={confrev_len}, val={confrev_val}")

    # smpSynch
    smpsynch_start = confrev_start + 2 + confrev_len
    smpsynch_tag = data[smpsynch_start]
    smpsynch_len = data[smpsynch_start+1]
    smpsynch_val = data[smpsynch_start+2]
    print(f"smpSynch: tag=0x{smpsynch_tag:02x}, len={smpsynch_len}, val={smpsynch_val}")

    # sample (sequence of data)
    sample_start = smpsynch_start + 2 + smpsynch_len
    sample_tag = data[sample_start]
    sample_len = data[sample_start+1]
    print(f"sample: tag=0x{sample_tag:02x}, len={sample_len}")

    # Извлекаем значения (8 каналов x 8 байт = 64 байта)
    values_start = sample_start + 2
    values = []
    for i in range(8):
        offset = values_start + i * 8
        val_bytes = data[offset:offset+8]
        # Первые 4 байта - значение (big-endian signed int32)
        val = int.from_bytes(val_bytes[0:4], 'big', signed=True)
        # Вторые 4 байта - quality (обычно 00 00 00 00)
        qual = val_bytes[4:8]
        values.append((val, qual.hex()))

    print(f"\nЗначения каналов (INT32):")
    roles = ['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']
    for i, (val, qual) in enumerate(values):
        print(f"  {roles[i]}: {val:10d} (0x{val & 0xffffffff:08x})  quality: {qual}")

    return data

print("=" * 80)
print("ФРЕЙМ 1 (SV1, smpCnt должен быть 0x00d7 = 215)")
print("=" * 80)
parse_frame(frames_hex[0])

print("\n" + "=" * 80)
print("ФРЕЙМ 2 (SV2, smpCnt должен быть 0x00d7 = 215)")
print("=" * 80)
parse_frame(frames_hex[1])

print("\n" + "=" * 80)
print("ФРЕЙМ 3 (SV1, smpCnt должен быть 0x00d8 = 216)")
print("=" * 80)
parse_frame(frames_hex[2])

print("\n" + "=" * 80)
print("ФРЕЙМ 4 (SV2, smpCnt должен быть 0x00d8 = 216)")
print("=" * 80)
parse_frame(frames_hex[3])
