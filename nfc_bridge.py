#!/usr/bin/env python3
"""
nfc_bridge.py — Мост Arduino/ESP32 Serial → Flask сервер
=========================================================
Запускать на том же компьютере, что и магазин.

Использование:
    python nfc_bridge.py                     # авто-поиск порта
    python nfc_bridge.py COM3                # Windows
    python nfc_bridge.py /dev/ttyUSB0        # Linux
    python nfc_bridge.py /dev/tty.usbserial  # macOS

Зависимости:
    pip install pyserial requests

Что делает:
1. Подключается к Arduino/ESP32 по Serial (9600 бод).
2. Каждый раз, когда Arduino присылает строку вида "UID:A3F2B1CC",
   скрипт отправляет POST на http://localhost:5000/api/nfc/push
   с телом {"uid": "A3F2B1CC"}.
3. Flask-сервер кладёт UID в буфер, браузер магазина забирает его polling'ом.
"""

import sys
import time
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('nfc_bridge')

SERVER_URL = 'http://localhost:5000/api/nfc/push'
BAUD_RATE  = 9600

# ── Попытка импортировать зависимости ──────────────────────────
try:
    import serial
    import serial.tools.list_ports
except ImportError:
    log.error("pyserial не установлен. Выполните: pip install pyserial")
    sys.exit(1)

try:
    import requests
except ImportError:
    log.error("requests не установлен. Выполните: pip install requests")
    sys.exit(1)

# ── Найти порт ─────────────────────────────────────────────────
def find_arduino_port():
    """Автоматически ищет Arduino/ESP32 среди доступных Serial-портов."""
    ports = list(serial.tools.list_ports.comports())
    keywords = ['arduino', 'esp', 'ch340', 'cp210', 'ftdi', 'usb serial', 'uart']
    for p in ports:
        desc = (p.description or '').lower()
        mfg  = (p.manufacturer or '').lower()
        if any(k in desc or k in mfg for k in keywords):
            return p.device
    # Если не нашли по описанию — берём первый доступный
    if ports:
        return ports[0].device
    return None

def get_port():
    if len(sys.argv) > 1:
        return sys.argv[1]
    port = find_arduino_port()
    if port:
        log.info(f"Авто-обнаружен порт: {port}")
        return port
    log.error("Arduino не найдена. Укажите порт вручную: python nfc_bridge.py COM3")
    sys.exit(1)

# ── Отправить UID на сервер ────────────────────────────────────
def push_uid(uid: str):
    try:
        resp = requests.post(SERVER_URL, json={'uid': uid}, timeout=3)
        if resp.status_code == 200 and resp.json().get('ok'):
            log.info(f"✓ UID отправлен на сервер: {uid}")
        else:
            log.warning(f"Сервер вернул ошибку: {resp.text}")
    except requests.exceptions.ConnectionError:
        log.error("Не удалось подключиться к Flask-серверу. Убедитесь, что app.py запущен.")
    except Exception as e:
        log.error(f"Ошибка отправки: {e}")

# ── Основной цикл ──────────────────────────────────────────────
def main():
    port = get_port()
    log.info(f"Подключение к {port} @ {BAUD_RATE} бод...")

    last_uid = None
    last_uid_time = 0
    DEBOUNCE = 2.0  # секунды — игнорировать повторное считывание той же карты

    while True:
        try:
            with serial.Serial(port, BAUD_RATE, timeout=1) as ser:
                log.info(f"✓ Подключено к {port}. Ожидаем данные от Arduino...")
                while True:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                    log.debug(f"Serial: {line!r}")

                    # Ожидаем формат "UID:AABBCCDD" или просто "AABBCCDD"
                    # Arduino-скетч посылает именно "UID:AABBCCDD\n"
                    match = re.search(r'(?:UID:)?([0-9A-Fa-f]{6,16})', line)
                    if match:
                        uid = match.group(1).upper()
                        now = time.time()
                        # Дебаунс: не отправлять одну и ту же карту дважды подряд
                        if uid == last_uid and (now - last_uid_time) < DEBOUNCE:
                            continue
                        last_uid = uid
                        last_uid_time = now
                        push_uid(uid)

        except serial.SerialException as e:
            log.error(f"Ошибка Serial: {e}. Переподключение через 3 сек...")
            time.sleep(3)
        except KeyboardInterrupt:
            log.info("Мост остановлен.")
            break

if __name__ == '__main__':
    main()
