# Технические детали реализации IEC 61850-9-2 LE

## Структура Sampled Values кадра

Программа генерирует кадры Sampled Values согласно UCA Implementation Guideline for IEC 61850-9-2LE:

```
┌─────────────────────────────────────────────────────────┐
│ Ethernet Frame                                          │
├─────────────────────────────────────────────────────────┤
│ Destination MAC (6 байт)       │ 01:0C:CD:04:00:01     │
│ Source MAC (6 байт)            │ 10:FF:E0:84:FE:34     │
│ 802.1Q VLAN Tag (4 байта)      │ 0x8100 + TCI         │ (если VLANID ≠ 0)
│ EtherType (2 байта)            │ 0x88BA (SV)          │
├─────────────────────────────────────────────────────────┤
│ Sampled Value APDU                                      │
├─────────────────────────────────────────────────────────┤
│ APPID (2 байта)                │ 0x4000 (default)     │
│ Length (2 байта)               │ 8 + len(ASDU)        │
│ Reserved1 (2 байта)            │ 0x8000 или 0x0000    │
│   ├─ бит 15 = Simulation flag  │ 1 = тест, 0 = реал   │
│   └─ биты 14-0 = 0             │                      │
│ Reserved2 (2 байта)            │ всегда 0x0000        │
│                                                         │
│ ASDU (Application Service Data Unit)                   │
│ ├─ Tag: 0x60                   │ Sequence            │
│ ├─ noASDU: 0x80 01             │ количество ASDU (1) │
│ └─ seqOfASDU: 0xA2             │ список ASDU         │
│    └─ ASDU: 0x30               │ одна ASDU           │
│       ├─ svID: 0x80            │ "RET61850_SV1"     │
│       ├─ smpCnt: 0x82          │ sample counter      │
│       ├─ confRev: 0x83         │ config revision     │
│       ├─ smpSynch: 0x85        │ синхронизация       │
│       └─ Data: 0x87            │ 8 каналов × 8 байт │
└─────────────────────────────────────────────────────────┘
```

## Кодирование данных (8 каналов)

Каждый канал в Data кодируется как:
```
[4 байта значения int32 big-endian][4 байта quality]
```

### Порядок каналов (всегда):
```
1. Ia (ток фазы A)       [4B значение][4B quality]
2. Ib (ток фазы B)       [4B значение][4B quality]
3. Ic (ток фазы C)       [4B значение][4B quality]
4. In (ток нейтрали)     [4B значение][4B quality]
5. Ua (напр фазы A)      [4B значение][4B quality]
6. Ub (напр фазы B)      [4B значение][4B quality]
7. Uc (напр фазы C)      [4B значение][4B quality]
8. Un (напр нейтрали)    [4B значение][4B quality]
```

### Масштабирование значений:

```python
# Для токов (Ia, Ib, Ic, In):
primary_A = secondary_A × Ктт    # преобразование через ТТ
int32_value = primary_A × 1000   # 1 LSB = 1 мА
Результат: int32(big-endian)

# Для напряжений (Ua, Ub, Uc, Un):
primary_V = secondary_V × Ктн    # преобразование через ТН
int32_value = primary_V × 100    # 1 LSB = 10 мВ (0.01 V)
Результат: int32(big-endian)

# Для нейтральных:
# In: int32(primary_In × 1000) где primary_In = secondary_In × K3i0
# Un: int32(primary_Un × 100)  где primary_Un = secondary_Un × K3u0
```

### Quality (состояние качества):

```
┌──────────────────────────────────────┐
│ Quality Byte (4 байта = 32 бита)    │
├──────────────────────────────────────┤
│ 0x00000000 = Good (хорошее качество)│
│ (остальные биты = флаги ошибок)     │
└──────────────────────────────────────┘
```

Программа всегда устанавливает quality = 0x00000000 (хорошее качество).

## Пример расчёта для реальных значений

### Дано:
```
Исходная осциллограмма (вторичные значения):
  Ia = 1 A, фаза 0°
  Un = 100 V, фаза 190°

Коэффициенты:
  Ктт = 1000 (ТТ 1000/1)
  K3u0 = 1905.2

Нужно найти: значения в PCAP файле
```

### Расчёт:

```
1. Преобразование через ТТ/ТН:
   Ia_primary = 1 A × 1000 = 1000 A
   Un_primary = 100 V × 1905.2 = 190520 V

2. Масштабирование для SV:
   Ia_int32 = 1000 × 1000 = 1,000,000 = 0x000F4240 (big-endian)
   Un_int32 = 190520 × 100 = 19,052,000 = 0x012316F0 (big-endian)

3. В PCAP файле (hex):
   ... [остальные каналы] ...
   Ia: 00 0F 42 40 00 00 00 00  (значение + quality)
   ... [остальные каналы] ...
   Un: 01 23 16 F0 00 00 00 00  (значение + quality)
```

## Формат PCAP (libpcap)

Программа создаёт стандартный PCAP файл, совместимый с Wireshark:

```
┌──────────────────────────────┐
│ Global Header (24 байта)     │
├──────────────────────────────┤
│ Magic Number: 0xa1b2c3d4     │
│ Major Version: 2             │
│ Minor Version: 4             │
│ Timezone: 0 (UTC)            │
│ Timestamp Accuracy: 0        │
│ Snaplen: 65535               │
│ Data Link Type: 1 (Ethernet) │
├──────────────────────────────┤
│ Packet Record 1              │
│ ├─ Timestamp (seconds)       │
│ ├─ Timestamp (microseconds)  │
│ ├─ Packet Length (original)  │
│ ├─ Packet Length (captured)  │
│ └─ Packet Data (variable)    │
├──────────────────────────────┤
│ Packet Record 2              │
│ ... (аналогично)             │
├──────────────────────────────┤
│ ... (все остальные пакеты)   │
└──────────────────────────────┘
```

### Расчёт временных меток:

```python
# Частота дискретизации из .cfg файла (обычно 4000 Гц)
sample_rate = 4000  # Hz

# Интервал между отсчётами
interval_us = 1_000_000 / sample_rate = 250 микросекунд

# Для каждого пакета i:
timestamp_us = i × interval_us
timestamp_sec = timestamp_us // 1_000_000
timestamp_usec = timestamp_us % 1_000_000
```

## BER/ASN.1 кодирование

ASDU кодируется в ASN.1 DER (Distinguished Encoding Rules):

```
TLV структура (Tag-Length-Value):

Tag:    1 байт (0x30 для SEQUENCE, 0x80 для context-specific)
Length: переменное (1 или больше байт)
        < 128:   1 байт
        ≥ 128:   первый байт = 0x80 | количество байт длины
                 следующие байты = саморазмер (big-endian)
Value:  N байт данных
```

### Пример кодирования svID:

```
svID value: "RET61850_SV1" (12 символов)

Encoded:
80                 # Tag: context-specific[0]
0C                 # Length: 12 байт
52 45 54 36 31 38 35 30 5F 53 56 31  # "RET61850_SV1" (ASCII)

Result: 80 0C 52 45 54 36 31 38 35 30 5F 53 56 31
```

## VLAN тег (802.1Q)

Когда VLANID ≠ 0, программа вставляет VLAN тег между MAC адресом и EtherType:

```
┌────────────────────────────────┐
│ Destination MAC: 6 bytes       │
│ Source MAC: 6 bytes            │
│ 802.1Q Tag: 4 bytes            │  ← ВСТАВЛЯЕТСЯ, если VLANID ≠ 0
│ ├─ TPID: 0x8100 (2 bytes)      │
│ └─ TCI: 2 bytes                │
│    ├─ Priority (PCP): 3 бита   │ (обычно 4)
│    ├─ CFI: 1 бит               │ (всегда 0)
│    └─ VLAN ID: 12 бит          │ (0-4095)
│ EtherType SV: 0x88BA (2 bytes) │
│ SV APDU: ... (variable)        │
└────────────────────────────────┘

Формула TCI:
TCI = (PCP << 13) | (CFI << 12) | VLANID
    = (4 << 13) | (0 << 12) | 100
    = 0x8064  (для VLANID=100, PCP=4)
```

## Статистика кадра

Для пример из задания:

```
Входные параметры:
  - 80 отсчётов за период (стандарт 9-2 LE)
  - Частота 50 Гц
  - Интервал дискретизации: 4000 Гц (250 µs)
  - Число периодов: 1 секунда = 50 периодов
  - Всего отсчётов в .dat: 4000 (1 сек × 4000 Гц)

Выход:
  - Кадров в PCAP: 4000
  - Размер одного кадра: ~110 байт (зависит от svID)
  - Размер PCAP: примерно 440-450 KB
  - Файл содержит: 1 секунду записи SV потока
```

## Совместимость

Сгенерированные PCAP файлы совместимы с:

✅ **Анализаторы:**
- Wireshark (версия 3.0+)
- tcpdump
- Любые libpcap-совместимые инструменты

✅ **IEC 61850 приложения:**
- SEL Logic Tester
- OMICRON CMC
- ABB NetBiter
- Schweitzer SEL RDB

✅ **Операционные системы:**
- Windows (используя WinPcap/Npcap)
- Linux
- macOS

## Формулы восстановления первичных значений из PCAP

Если нужно вернуть первичные значения из PCAP:

```python
# Восстановление из int32 значения:
def decode_sv_value(int32_value, is_current, ktt, ktn, k3i0, k3u0):
    if is_current:
        # Расшифровка тока
        if channel_is_neutral:
            primary_A = int32_value / 1000 / k3i0
        else:
            primary_A = int32_value / 1000 / ktt
    else:
        # Расшифровка напряжения
        if channel_is_neutral:
            primary_V = int32_value / 100 / k3u0
        else:
            primary_V = int32_value / 100 / ktn
    return primary_A or primary_V
```

## Отладка

Для отладки SV кадров в Wireshark:

1. Откройте PCAP файл
2. В фильтре введите: `sv`
3. Выберите пакет
4. Разверните дерево: Frame → Ethernet → Sampled Values
5. Посмотрите:
   - APPID в hex-формате
   - Флаги Reserved1 (бит 15 = Simulation)
   - Значения каналов в int32 big-endian
   - Quality флаги для каждого канала

## Стандартные ссылки

- **IEC 61850-9-2**: Procedures for real-time communication between intelligent electronic devices
- **IEC 61850-9-2 LE Implementation Guideline**: UCA International
- **IEEE 1588**: Precision Time Protocol (для PTP синхронизации)
- **ISO 8859-1**: Latin-1 кодировка (для svID строк)

---

Версия документа: 1.0  
Дата: 2026-06-23
