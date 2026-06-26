# 📁 Структура проекта SV Converter

```
sv_converter/
│
├── 📋 ДОКУМЕНТАЦИЯ
│   ├── README.md              - Основная документация, возможности, использование
│   ├── QUICKSTART.md          - Быстрый старт (5 минут)
│   ├── INSTALLATION.md        - Подробная установка на Windows/macOS/Linux
│   ├── EXAMPLES.md            - Примеры использования и сценарии
│   ├── TECHNICAL.md           - Технические детали IEC 61850-9-2 LE
│   └── PROJECT_STRUCTURE.md   - Этот файл
│
├── 🐍 ИСХОДНЫЙ КОД (Python)
│   ├── main.py                - Точка входа приложения (запуск сервера и браузера)
│   ├── converter.py           - Основная логика конвертации COMTRADE → PCAP
│   ├── server.py              - HTTP сервер (без внешних зависимостей)
│   │
│   └── sv_converter.spec      - Конфигурация PyInstaller для сборки EXE
│
├── 🌐 ВЕБ-ИНТЕРФЕЙС
│   └── static/
│       └── index.html         - Веб-страница (HTML/CSS/JavaScript)
│
├── ⚙️ КОНФИГУРАЦИЯ
│   ├── requirements-dev.txt   - Зависимости для разработки (PyInstaller)
│   └── .gitignore             - Git исключения
│
└── 🚀 БЫСТРЫЙ ЗАПУСК
    ├── run.bat                - Быстрый запуск на Windows
    └── run.sh                 - Быстрый запуск на Linux/macOS
```

## 📄 Описание каждого файла

### Документация

#### **README.md**
- Общее описание программы
- Основные возможности
- Инструкции по использованию
- Стандартные параметры
- Архитектура
- Известные ограничения

#### **QUICKSTART.md**
- Для нетерпеливых
- За 5 минут до первой конвертации
- Помощь при проблемах

#### **INSTALLATION.md**
- Установка на Windows, macOS, Linux
- Запуск из исходного кода
- Сборка EXE через PyInstaller
- Проблемы и решения
- Советы для разработчиков

#### **EXAMPLES.md**
- Пример 1: базовая конвертация
- Пример 2: специализированная конфигурация
- Пример 3: проверка в Wireshark
- Пример 4: интеграция с реальным оборудованием
- Пример 5: разные производители осциллограмм
- Пример 6: пакетная обработка
- Вычисление коэффициентов трансформации
- Отладка и трубка вопросов

#### **TECHNICAL.md**
- Структура кадра SV
- Кодирование данных (8 каналов)
- Масштабирование значений
- Quality (состояние качества)
- Примеры расчётов
- Формат PCAP (libpcap)
- BER/ASN.1 кодирование
- VLAN тег 802.1Q
- Совместимость
- Формулы для отладки

---

### Исходный код

#### **main.py** (120 строк)
```python
Функции:
  - open_browser()      # Открывает браузер с задержкой
  - main()              # Главная функция: запуск сервера и браузера
```
**Используется:** Threading для асинхронного запуска
**Порт:** 127.0.0.1:8000 (можно изменить)

#### **converter.py** (330 строк)
```python
Основные функции:
  - parse_cfg()               # Парсит COMTRADE .cfg файл
  - parse_dat_ascii()         # Парсит ASCII .dat файл
  - guess_mapping()           # Эвристическое определение каналов
  - ber_len(), tlv()         # Кодирование ASN.1
  - build_sample_bytes()      # Расчёт значений с масштабированием
  - build_asdu()              # Создание ASDU (Application Service Data Unit)
  - build_savpdu()            # Создание SV APDU
  - mac_to_bytes()            # Преобразование MAC адреса
  - build_frame()             # Построение Ethernet кадра
  - write_pcap_bytes()        # Запись PCAP файла
  - convert()                 # Главный конвейер конвертации
```
**Константы:**
  - ROLE_ORDER: ['Ia', 'Ib', 'Ic', 'In', 'Ua', 'Ub', 'Uc', 'Un']
  - SCALE_CURRENT: 1000 (1 LSB = 1 мА)
  - SCALE_VOLTAGE: 100 (1 LSB = 10 мВ)

**Зависимости:** только стандартная библиотека (re, struct)

#### **server.py** (220 строк)
```python
Классы:
  - SVConverterHandler(http.server.SimpleHTTPRequestHandler)
    Методы:
    - do_GET()           # Обработка GET запросов
    - do_POST()          # Обработка POST запросов
    - serve_file()       # Раздача статических файлов
    - api_get_roles()    # API: получить список ролей
    - api_convert()      # API: конвертировать

Функции:
  - run_server()        # Запуск HTTP сервера на (host:port)
```
**Порты:** 127.0.0.1:8000 (настраивается в main.py)
**Форматы:**
  - Входящий JSON (POST /api/convert)
  - Исходящий JSON (все API)

#### **sv_converter.spec** (50 строк)
PyInstaller конфигурация для сборки Windows EXE:
- Подключает static/ папку в дистрибутив
- Создаёт console application
- Поддерживает однофайловый режим (--onefile)

---

### Веб-интерфейс

#### **static/index.html** (600+ строк)
Одностраничное приложение (SPA):
```
Структура:
├── HTML (450 строк)
│   ├── Заголовок (header)
│   ├── Раздел загрузки файлов
│   ├── Раздел сопоставления каналов (таблица)
│   ├── Раздел параметров SV (сетевые, ASDU, трансформация)
│   ├── Раздел конвертации (кнопки и статус)
│   └── Сообщения статуса
│
├── CSS (200+ строк)
│   ├── Адаптивный дизайн (mobile-friendly)
│   ├── Светлая / тёмная темы
│   ├── Grid и Flex layout
│   └── Анимации (spinner, transitions)
│
└── JavaScript (350+ строк)
    ├── Обработка загрузки файлов
    ├── Парсинг .cfg (базовый)
    ├── Построение таблицы сопоставления
    ├── Автоматическое определение каналов
    ├── Отправка данных на сервер (/api/convert)
    ├── Скачивание PCAP файла (base64 decode)
    └── Управление статусом и ошибками
```

**Требования:** JavaScript ES6+, работает во всех современных браузерах

---

### Конфигурация

#### **requirements-dev.txt**
```
pyinstaller>=5.0   # Для сборки EXE
pytest>=6.0        # Для тестирования (опционально)
```

#### **.gitignore**
Исключает:
- __pycache__, *.pyc, *.egg-info
- build/, dist/ (артефакты сборки)
- .venv/, env/ (виртуальные окружения)
- .vscode/, .idea/ (IDE файлы)
- *.pcap (сгенерированные файлы)

---

### Скрипты запуска

#### **run.bat** (Windows)
```batch
@echo off
cd /d "%~dp0"
python main.py
pause
```
Используется: 
- Для быстрого запуска из проводника
- Окно консоли остаётся после закрытия приложения

#### **run.sh** (Linux/macOS)
```bash
#!/bin/bash
cd "$(dirname "$0")"
python3 main.py
```
Используется:
- Для запуска из терминала или файл-менеджера
- На macOS можно создать приложение через `chmod +x run.sh`

---

## 🔄 Процесс конвертации

```
USER INPUT (WEB INTERFACE)
         ↓
    [HTML Form]
    ├─ .cfg file
    ├─ .dat file
    ├─ Mapping (8 roles)
    └─ Parameters (10 fields)
         ↓
  [POST /api/convert]
         ↓
  server.py:api_convert()
         ↓
  converter.py:convert()
    ├─ parse_cfg()           → channels data
    ├─ parse_dat_ascii()     → sample values
    ├─ build_asdu()          → ASN.1 encoding
    │   └─ build_sample_bytes() → int32 scaling
    ├─ build_frame()         → Ethernet frame
    │   └─ mac_to_bytes()    → MAC parsing
    └─ write_pcap_bytes()    → PCAP file
         ↓
  [JSON Response + base64 PCAP]
         ↓
  index.html:doConvert()
    └─ displayPcapData()
         ↓
  USER: [Download Button]
    └─ downloadPcap()
         ↓
  FILE: sampled_values.pcap
```

---

## 📊 Размеры и производительность

| Параметр | Значение |
|----------|----------|
| Размер main.py | ~4 KB |
| Размер converter.py | ~12 KB |
| Размер server.py | ~8 KB |
| Размер index.html | ~20 KB |
| **Итого исходный код** | **44 KB** |
| **Готовый exe (с Python)** | ~50-60 MB |
| PCAP файл (1 сек @ 4000 Hz) | ~440 KB |
| Время конвертации | <1 сек |

---

## 🔐 Безопасность

- **Входные данные:** парсятся локально (на вашем ПК)
- **Сервер:** работает только на localhost (127.0.0.1)
- **Сетевые данные:** не отправляются на внешние серверы
- **Файлы:** сохраняются только на вашем ПК
- **Зависимости:** только стандартная библиотека Python

---

## 🧪 Тестирование

### Для самопроверки:

1. **Загрузите ваши тестовые файлы** (.cfg и .dat)
2. **Сопоставьте каналы** (Ia, Ib, Ic, In, Ua, Ub, Uc, Un)
3. **Введите параметры** из вашего примера:
   ```
   MAC: 01-0C-CD-04-00-01
   APPID: 4000
   VLANID: 0
   svID: RET61850_SV1
   confRev: 1
   Simulation: ✓
   Ктт: 1000
   Ктн: 1100
   K3i0: 1000
   K3u0: 1905.2
   ```
4. **Конвертируйте** и скачайте PCAP
5. **Откройте в Wireshark** и сравните с эталонным дампом

### Проверка результата:

```python
# Должны совпадать с эталоном:
- MAC: 01 0c cd 04 00 01 ✓
- APPID: 0x4000 ✓
- svID: "RET61850_SV1" ✓
- Simulation flag (bit 15): 1 ✓
- First sample values (в hex) ✓
```

---

## 📚 Дополнительные ресурсы

- **IEC 61850**: https://webstore.iec.ch/publication/7427
- **UCA Implementation Guidelines**: https://www.uc-ca.org/
- **Wireshark**: https://www.wireshark.org/
- **Python docs**: https://docs.python.org/3/

---

**Версия:** 1.0  
**Последнее обновление:** 2026-06-23  
**Лицензия:** Open Source для технических работ
