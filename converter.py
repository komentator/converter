# -*- coding: utf-8 -*-
"""
Конвертер осциллограммы COMTRADE (.cfg/.dat) в поток Sampled Values
IEC 61850-9-2 LE, упакованный в файл .pcap.

Все вычисления выполняются по открытым данным:
 - структура Ethernet/SV ASDU кадра (UCA IEC 61850-9-2LE Implementation Guideline)
 - масштабирующие коэффициенты по умолчанию: ток x1000 (1 LSB = 1 мА),
   напряжение x100 (1 LSB = 10 мВ / 1 сантивольт)
"""

import re
import struct

ROLE_ORDER = ['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']
ROLE_IS_CURRENT = {
    'Ia': True, 'Ib': True, 'Ic': True, 'In': True,
    'Ua': False, 'Ub': False, 'Uc': False, 'Un': False,
}

SCALE_CURRENT = 1000   # 1 LSB = 1 mA  -> A * 1000
SCALE_VOLTAGE = 100    # 1 LSB = 10 mV -> V * 100

DEFAULT_SRC_MAC = '10:FF:E0:84:FE:34'


# --------------------------------------------------------------------------
# COMTRADE parsing
# --------------------------------------------------------------------------

def _split_csv(line):
    return [p.strip() for p in line.rstrip(',').split(',')]


def parse_cfg(text):
    """Парсит .cfg (COMTRADE). Возвращает словарь с каналами и параметрами записи."""
    lines = [l for l in text.splitlines() if l.strip() != '']
    idx = 0

    # line 0: station_name, rec_dev_id, rev_year
    idx += 1

    # line 1: total_channels, countA(A), countD(D)
    counts = _split_csv(lines[idx]); idx += 1
    total = int(counts[0])
    countA = int(re.sub(r'[^0-9\-]', '', counts[1])) if len(counts) > 1 else total
    countD = int(re.sub(r'[^0-9\-]', '', counts[2])) if len(counts) > 2 else (total - countA)

    channels = []
    for i in range(countA):
        f = _split_csv(lines[idx]); idx += 1
        ch = {
            'index': int(f[0]),
            'name': f[1] if len(f) > 1 else '',
            'phase': f[2] if len(f) > 2 else '',
            'ccbm': f[3] if len(f) > 3 else '',
            'unit': f[4] if len(f) > 4 else '',
            'mult': float(f[5]) if len(f) > 5 and f[5] != '' else 1.0,
            'offset': float(f[6]) if len(f) > 6 and f[6] != '' else 0.0,
        }
        channels.append(ch)

    for i in range(countD):
        idx += 1  # цифровые каналы конвертеру не нужны

    line_freq = float(_split_csv(lines[idx])[0]); idx += 1

    nrates_raw = _split_csv(lines[idx])[0]; idx += 1
    try:
        nrates = int(float(nrates_raw))
    except ValueError:
        nrates = 1
    nrates = max(nrates, 1)

    rates = []
    for i in range(nrates):
        rf = _split_csv(lines[idx]); idx += 1
        rates.append((float(rf[0]), int(float(rf[1]))))

    start_time = lines[idx] if idx < len(lines) else ''
    idx += 1
    trigger_time = lines[idx] if idx < len(lines) else ''
    idx += 1
    dat_type = lines[idx].strip().upper() if idx < len(lines) else 'ASCII'
    idx += 1

    sample_rate = rates[0][0] if rates else 4000.0

    return {
        'channels': channels,
        'line_freq': line_freq,
        'sample_rate': sample_rate,
        'dat_type': dat_type,
        'start_time': start_time,
        'trigger_time': trigger_time,
    }


def parse_dat_ascii(text, n_channels):
    """Парсит ASCII .dat. Возвращает список строк (списков int значений каналов)."""
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.rstrip(',').split(',')
        if len(parts) < 2 + n_channels:
            continue
        vals = [int(p) for p in parts[2:2 + n_channels]]
        rows.append(vals)
    return rows


def guess_mapping(channels):
    """Эвристическое сопоставление роль -> индекс канала (0-based) по имени.
    
    Стратегия:
    1. Прямое совпадение имени канала
    2. По фазе (a/b/c/n) + unit (A/V)
    3. По позиции в списке (последовательный порядок)
    """
    mapping = {}
    used = set()
    
    for role in ROLE_ORDER:
        found = None
        is_current = ROLE_IS_CURRENT[role]
        unit_expected = 'A' if is_current else 'V'
        phase_letter = role[-1].lower()
        
        # Стратегия 1: прямое совпадение имени (точная проверка)
        for i, ch in enumerate(channels):
            if i in used:
                continue
            name = ch['name'].strip().lower()
            if name == role.lower():
                found = i
                break
        
        # Стратегия 2: по фазе + unit
        if found is None:
            for i, ch in enumerate(channels):
                if i in used:
                    continue
                unit = (ch['unit'] or '').strip().upper()
                phase = ch['phase'].strip().lower()
                
                # Проверяем совпадение unit и phase
                if unit == unit_expected and phase == phase_letter:
                    found = i
                    break
        
        # Стратегия 3: по unit + позиция в правильном порядке
        if found is None:
            current_idx = 0
            for i, ch in enumerate(channels):
                if i in used:
                    continue
                unit = (ch['unit'] or '').strip().upper()
                if unit == unit_expected:
                    if current_idx == len([r for r in ROLE_ORDER[:ROLE_ORDER.index(role)] 
                                          if ROLE_IS_CURRENT[r] == is_current and mapping[r] is not None]):
                        found = i
                        break
                    current_idx += 1
        
        if found is not None:
            used.add(found)
        
        mapping[role] = found
    
    return mapping


# --------------------------------------------------------------------------
# BER (ASN.1) helpers
# --------------------------------------------------------------------------

def ber_len(n):
    if n < 0x80:
        return bytes([n])
    b = []
    while n > 0:
        b.insert(0, n & 0xFF)
        n >>= 8
    return bytes([0x80 | len(b)]) + bytes(b)


def tlv(tag, value):
    return bytes([tag]) + ber_len(len(value)) + value


# --------------------------------------------------------------------------
# SV ASDU / frame building
# --------------------------------------------------------------------------

def build_sample_bytes(values_by_role, ktt, ktn, k3i0, k3u0):
    """values_by_role: секундные (вторичные) instantaneous значения по ролям.
    
    Вычисление:
    1. secondary (вторичное) * ratio → primary (первичное)
    2. primary * scale → int32 для SV потока
    
    Масштабирование IEC 61850-9-2LE:
    - Токи: 1 LSB = 1 мА (A × 1000)
    - Напряжения: 1 LSB = 10 мВ (V × 100)
    """
    ratio_map = {
        'Ia': ktt, 'Ib': ktt, 'Ic': ktt,
        'In': k3i0,
        'Ua': ktn, 'Ub': ktn, 'Uc': ktn,
        'Un': k3u0,
    }
    out = bytearray()
    for role in ROLE_ORDER:
        try:
            secondary = float(values_by_role[role])
            ratio = float(ratio_map[role])
            primary = secondary * ratio
            
            # Масштабирование для SV потока
            if ROLE_IS_CURRENT[role]:
                # Токи: A → мА (×1000)
                ival = int(round(primary * SCALE_CURRENT))
            else:
                # Напряжения: V → сантивольты (×100)
                ival = int(round(primary * SCALE_VOLTAGE))
            
            # Ограничиваем диапазон int32 (-2^31 до 2^31-1)
            if ival > 2147483647:
                ival = 2147483647
            elif ival < -2147483648:
                ival = -2147483648
            
            # Кодируем как signed int32 big-endian
            out += struct.pack('>i', ival)
            
            # Quality flags: 0 = good, хорошее качество
            # Состояние: 0 = normal, 1 = abnormal
            # Ошибка: 0 = no error
            out += b'\x00\x00\x00\x00'
            
        except (ValueError, TypeError, KeyError) as e:
            # На случай ошибок - добавляем нулевое значение
            out += struct.pack('>i', 0)
            out += b'\x00\x00\x00\x00'
    
    return bytes(out)


def build_asdu(svid, smp_cnt, conf_rev, sample_bytes, smp_synch=0):
    svid_b = svid.encode('ascii', errors='replace')
    f_svid = tlv(0x80, svid_b)
    f_smpcnt = tlv(0x82, struct.pack('>H', smp_cnt & 0xFFFF))
    f_confrev = tlv(0x83, struct.pack('>I', conf_rev & 0xFFFFFFFF))
    f_synch = tlv(0x85, bytes([smp_synch & 0xFF]))
    f_sample = tlv(0x87, sample_bytes)
    body = f_svid + f_smpcnt + f_confrev + f_synch + f_sample
    return tlv(0x30, body)


def build_savpdu(asdu_list):
    seq = b''.join(asdu_list)
    f_seq = tlv(0xA2, seq)
    f_noasdu = tlv(0x80, bytes([len(asdu_list) & 0xFF]))
    body = f_noasdu + f_seq
    return tlv(0x60, body)


def mac_to_bytes(mac_str):
    parts = re.split(r'[:\-]', mac_str.strip())
    if len(parts) != 6:
        raise ValueError(f'Некорректный MAC-адрес: {mac_str}')
    return bytes(int(p, 16) for p in parts)


def build_frame(dst_mac, src_mac, appid, vlan_id, vlan_pcp, simulation, savpdu):
    reserved1 = 0x8000 if simulation else 0x0000
    reserved2 = 0x0000
    length_field = 8 + len(savpdu)  # APPID(2)+Length(2)+Res1(2)+Res2(2) + savPDU
    sv_header = struct.pack('>HHHH', appid & 0xFFFF, length_field & 0xFFFF,
                             reserved1, reserved2)
    eth = bytearray()
    eth += dst_mac
    eth += src_mac
    if vlan_id:
        tci = ((vlan_pcp & 0x7) << 13) | (vlan_id & 0x0FFF)
        eth += struct.pack('>HH', 0x8100, tci)
    eth += struct.pack('>H', 0x88BA)
    eth += sv_header
    eth += savpdu
    return bytes(eth)


# --------------------------------------------------------------------------
# pcap writing
# --------------------------------------------------------------------------

PCAP_GLOBAL_HEADER = struct.pack('<IHHiIII', 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)


def write_pcap_bytes(frames, sample_interval_us, timestamps=None):
    """
    Записывает фреймы в PCAP формат.

    Args:
        frames: список фреймов
        sample_interval_us: интервал между сэмплами в микросекундах
        timestamps: опциональный список временных меток для каждого фрейма (в микросекундах)
                   Если None, используется линейное увеличение с шагом sample_interval_us
    """
    out = bytearray(PCAP_GLOBAL_HEADER)

    if timestamps is None:
        # Стандартное поведение: линейное увеличение времени
        t_us = 0
        for fr in frames:
            ts_sec = t_us // 1_000_000
            ts_usec = t_us % 1_000_000
            out += struct.pack('<IIII', ts_sec, ts_usec, len(fr), len(fr))
            out += fr
            t_us += sample_interval_us
    else:
        # Используем предоставленные временные метки
        for fr, t_us in zip(frames, timestamps):
            ts_sec = t_us // 1_000_000
            ts_usec = t_us % 1_000_000
            out += struct.pack('<IIII', ts_sec, ts_usec, len(fr), len(fr))
            out += fr

    return bytes(out)


# --------------------------------------------------------------------------
# Полный конвейер
# --------------------------------------------------------------------------

def convert(cfg_text, dat_text, mapping, params, mapping2=None, params2=None):
    """
    Конвертер осциллограммы COMTRADE в SV поток(и).

    Поддерживает два режима:
    - Single stream: mapping2=None, params2=None → один SV поток
    - Dual stream: mapping2 и params2 заполнены → два независимых SV потока

    Args:
        cfg_text: Содержимое .cfg файла
        dat_text: Содержимое .dat файла
        mapping: { 'Ia': ch_index, 'Ib': ..., ... } для потока 1
        params: Параметры потока 1 (mac, appid, svid, ktt, ktn, k3i0, k3u0, ...)
        mapping2: Сопоставление каналов для потока 2 (опционально)
        params2: Параметры потока 2 (опционально)

    Returns:
        (pcap_bytes, frames_count) - бинарный PCAP с фреймами, количество фреймов
    """
    cfg = parse_cfg(cfg_text)
    channels = cfg['channels']
    n_channels = len(channels)
    rows = parse_dat_ascii(dat_text, n_channels)
    sample_rate = cfg['sample_rate']
    interval_us = int(round(1_000_000 / sample_rate))

    # Валидация Stream 1
    for role in ROLE_ORDER:
        if mapping.get(role) is None:
            raise ValueError(f'Не назначен канал для роли {role}')

    # Валидация Stream 2 (если включен)
    if mapping2 is not None or params2 is not None:
        if mapping2 is None or params2 is None:
            raise ValueError('Если включен режим двух потоков, нужны оба: mapping2 и params2')
        for role in ROLE_ORDER:
            if mapping2.get(role) is None:
                raise ValueError(f'Не назначен канал для роли {role} в Stream 2')

    dual_mode = mapping2 is not None and params2 is not None

    # Stream 1 параметры
    dst_mac = mac_to_bytes(params['mac'])
    src_mac = mac_to_bytes(params.get('src_mac') or DEFAULT_SRC_MAC)

    appid_raw = params['appid']
    appid = int(appid_raw, 16) if isinstance(appid_raw, str) else int(appid_raw)

    vlanid_raw = params.get('vlanid', 0)
    vlan_id = int(vlanid_raw, 16) if isinstance(vlanid_raw, str) and vlanid_raw != '' else int(vlanid_raw or 0)
    vlan_pcp = int(params.get('vlan_pcp', 4))

    svid = params['svid']
    conf_rev = int(params['confrev'])
    simulation = bool(params['simulation'])

    ktt = float(params['ktt'])
    ktn = float(params['ktn'])
    k3i0 = float(params['k3i0'])
    k3u0 = float(params['k3u0'])

    # Stream 2 параметры (если включен)
    if dual_mode:
        dst_mac2 = mac_to_bytes(params2['mac'])
        src_mac2 = mac_to_bytes(params2.get('src_mac') or DEFAULT_SRC_MAC)

        appid_raw2 = params2['appid']
        appid2 = int(appid_raw2, 16) if isinstance(appid_raw2, str) else int(appid_raw2)

        vlanid_raw2 = params2.get('vlanid', 0)
        vlan_id2 = int(vlanid_raw2, 16) if isinstance(vlanid_raw2, str) and vlanid_raw2 != '' else int(vlanid_raw2 or 0)
        vlan_pcp2 = int(params2.get('vlan_pcp', 4))

        svid2 = params2['svid']
        conf_rev2 = int(params2['confrev'])
        simulation2 = bool(params2['simulation'])

        ktt2 = float(params2['ktt'])
        ktn2 = float(params2['ktn'])
        k3i0_2 = float(params2['k3i0'])
        k3u0_2 = float(params2['k3u0'])

    smp_cnt_period = max(int(round(sample_rate)), 1)

    frames = []
    debug_count = 0
    for i, row in enumerate(rows):
        smp_cnt = i % smp_cnt_period

        # Stream 1 - всегда генерируется
        values_by_role = {}
        for role in ROLE_ORDER:
            ch_idx = mapping[role]
            if ch_idx is None:
                raise ValueError(f"Канал для {role} не определён!")
            ch = channels[ch_idx]
            raw = row[ch_idx]
            secondary = float(raw) * float(ch.get('mult', 1.0)) + float(ch.get('offset', 0.0))
            values_by_role[role] = secondary

            if i < 2 and debug_count < 16:
                ratio = ktt if ROLE_IS_CURRENT[role] else (ktn if role[0].upper() in 'U' else ktn)
                if role in ['In', 'Un']:
                    ratio = k3i0 if ROLE_IS_CURRENT[role] else k3u0
                primary = secondary * ratio
                scale = SCALE_CURRENT if ROLE_IS_CURRENT[role] else SCALE_VOLTAGE
                ival = int(round(primary * scale))
                debug_count += 1

        sample_bytes = build_sample_bytes(values_by_role, ktt, ktn, k3i0, k3u0)
        asdu = build_asdu(svid, smp_cnt, conf_rev, sample_bytes, smp_synch=0)
        savpdu = build_savpdu([asdu])
        frame = build_frame(dst_mac, src_mac, appid, vlan_id, vlan_pcp, simulation, savpdu)
        frames.append(frame)

        # Stream 2 - если включен dual mode
        if dual_mode:
            values_by_role2 = {}
            for role in ROLE_ORDER:
                ch_idx2 = mapping2[role]
                if ch_idx2 is None:
                    raise ValueError(f"Канал для {role} не определён в Stream 2!")
                ch = channels[ch_idx2]
                raw = row[ch_idx2]
                secondary2 = float(raw) * float(ch.get('mult', 1.0)) + float(ch.get('offset', 0.0))
                values_by_role2[role] = secondary2

            sample_bytes2 = build_sample_bytes(values_by_role2, ktt2, ktn2, k3i0_2, k3u0_2)
            # Используем ТОТЖЕ smp_cnt для обоих потоков одного момента времени
            asdu2 = build_asdu(svid2, smp_cnt, conf_rev2, sample_bytes2, smp_synch=0)
            savpdu2 = build_savpdu([asdu2])
            frame2 = build_frame(dst_mac2, src_mac2, appid2, vlan_id2, vlan_pcp2, simulation2, savpdu2)
            frames.append(frame2)

    pcap_bytes = write_pcap_bytes(frames, interval_us)
    return pcap_bytes, len(frames)


def convert_dual(cfg_text, dat_text, mapping1, mapping2, params1, params2, smp_cnt_start=0):
    """
    Конвертирует осциллограмму в ДВА чередующихся SV потока в одном PCAP файле.

    Паттерн чередования:
    - Фрейм 1: SV1, smpCnt=N, время=T
    - Фрейм 2: SV2, smpCnt=N, время=T+1µs
    - Фрейм 3: SV1, smpCnt=N+1, время=T+interval
    - Фрейм 4: SV2, smpCnt=N+1, время=T+interval+1µs

    Args:
        cfg_text: текст .cfg файла
        dat_text: текст .dat файла
        mapping1: маппинг каналов для первого потока { 'Ia': ch_idx, ... }
        mapping2: маппинг каналов для второго потока { 'Ia': ch_idx, ... }
        params1: параметры первого потока (mac, appid, svid, ktt, ktn, k3i0, k3u0 и т.д.)
        params2: параметры второго потока (mac, appid, svid, ktt, ktn, k3i0, k3u0 и т.д.)
        smp_cnt_start: начальное значение smpCnt (по умолчанию 0)

    Returns:
        (pcap_bytes, frames_count)
    """
    cfg = parse_cfg(cfg_text)
    channels = cfg['channels']
    n_channels = len(channels)
    rows = parse_dat_ascii(dat_text, n_channels)
    sample_rate = cfg['sample_rate']
    interval_us = int(round(1_000_000 / sample_rate))

    # Валидация маппингов
    for role in ROLE_ORDER:
        if mapping1.get(role) is None:
            raise ValueError(f'Поток 1: не назначен канал для роли {role}')
        if mapping2.get(role) is None:
            raise ValueError(f'Поток 2: не назначен канал для роли {role}')

    # Парсим параметры потока 1
    dst_mac1 = mac_to_bytes(params1['mac'])
    src_mac1 = mac_to_bytes(params1.get('src_mac') or DEFAULT_SRC_MAC)
    appid1 = int(params1['appid'], 16) if isinstance(params1['appid'], str) else int(params1['appid'])
    vlanid_raw1 = params1.get('vlanid', 0)
    vlan_id1 = int(vlanid_raw1, 16) if isinstance(vlanid_raw1, str) and vlanid_raw1 != '' else int(vlanid_raw1 or 0)
    vlan_pcp1 = int(params1.get('vlan_pcp', 4))
    svid1 = params1['svid']
    conf_rev1 = int(params1['confrev'])
    simulation1 = bool(params1['simulation'])
    ktt1 = float(params1['ktt'])
    ktn1 = float(params1['ktn'])
    k3i0_1 = float(params1['k3i0'])
    k3u0_1 = float(params1['k3u0'])

    # Парсим параметры потока 2
    dst_mac2 = mac_to_bytes(params2['mac'])
    src_mac2 = mac_to_bytes(params2.get('src_mac') or DEFAULT_SRC_MAC)
    appid2 = int(params2['appid'], 16) if isinstance(params2['appid'], str) else int(params2['appid'])
    vlanid_raw2 = params2.get('vlanid', 0)
    vlan_id2 = int(vlanid_raw2, 16) if isinstance(vlanid_raw2, str) and vlanid_raw2 != '' else int(vlanid_raw2 or 0)
    vlan_pcp2 = int(params2.get('vlan_pcp', 4))
    svid2 = params2['svid']
    conf_rev2 = int(params2['confrev'])
    simulation2 = bool(params2['simulation'])
    ktt2 = float(params2['ktt'])
    ktn2 = float(params2['ktn'])
    k3i0_2 = float(params2['k3i0'])
    k3u0_2 = float(params2['k3u0'])

    smp_cnt_period = max(int(round(sample_rate)), 1)

    frames = []

    for i, row in enumerate(rows):
        smp_cnt = (smp_cnt_start + i) % smp_cnt_period

        # Фрейм 1: SV1
        values1 = {}
        for role in ROLE_ORDER:
            ch_idx = mapping1[role]
            ch = channels[ch_idx]
            raw = row[ch_idx]
            secondary = float(raw) * float(ch.get('mult', 1.0)) + float(ch.get('offset', 0.0))
            values1[role] = secondary

        sample_bytes1 = build_sample_bytes(values1, ktt1, ktn1, k3i0_1, k3u0_1)
        asdu1 = build_asdu(svid1, smp_cnt, conf_rev1, sample_bytes1, smp_synch=0)
        savpdu1 = build_savpdu([asdu1])
        frame1 = build_frame(dst_mac1, src_mac1, appid1, vlan_id1, vlan_pcp1, simulation1, savpdu1)
        frames.append(frame1)

        # Фрейм 2: SV2 (с тем же smp_cnt!)
        values2 = {}
        for role in ROLE_ORDER:
            ch_idx = mapping2[role]
            ch = channels[ch_idx]
            raw = row[ch_idx]
            secondary = float(raw) * float(ch.get('mult', 1.0)) + float(ch.get('offset', 0.0))
            values2[role] = secondary

        sample_bytes2 = build_sample_bytes(values2, ktt2, ktn2, k3i0_2, k3u0_2)
        asdu2 = build_asdu(svid2, smp_cnt, conf_rev2, sample_bytes2, smp_synch=0)
        savpdu2 = build_savpdu([asdu2])
        frame2 = build_frame(dst_mac2, src_mac2, appid2, vlan_id2, vlan_pcp2, simulation2, savpdu2)
        frames.append(frame2)

    # Генерируем временные метки: оба фрейма в паре имеют почти одинаковое время
    timestamps = []
    for i in range(len(rows)):
        t_us = i * interval_us
        timestamps.append(t_us)        # SV1 в момент T
        timestamps.append(t_us + 1)    # SV2 через 1 микросекунду

    pcap_bytes = write_pcap_bytes(frames, interval_us, timestamps)
    return pcap_bytes, len(frames)
