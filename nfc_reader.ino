/*
 * nfc_reader.ino — Скетч Arduino для RFID RC522
 * ================================================
 * Подключение RC522 к Arduino Uno:
 *   RC522 SDA  → D10 (SS)
 *   RC522 SCK  → D13
 *   RC522 MOSI → D11
 *   RC522 MISO → D12
 *   RC522 IRQ  → не подключать
 *   RC522 GND  → GND
 *   RC522 RST  → D9
 *   RC522 3.3V → 3.3V (важно! не 5V)
 *
 * Для ESP32/ESP8266 пины другие — уточните по документации.
 *
 * Библиотека: MFRC522 от Miguel Balboa
 * Установить через Arduino IDE: Sketch → Include Library → MFRC522
 *
 * Что делает скетч:
 * При поднесении карты считывает её UID и отправляет по Serial
 * в формате "UID:AABBCCDD\n" — ровно то, что ожидает nfc_bridge.py
 */

#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN  10   // SDA
#define RST_PIN  9   // RST

MFRC522 rfid(SS_PIN, RST_PIN);

String lastUID = "";
unsigned long lastReadTime = 0;
const unsigned long DEBOUNCE_MS = 2000; // мс — пауза между считываниями

void setup() {
  Serial.begin(9600);
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("READY");  // сигнал для nfc_bridge.py что Arduino готова
}

void loop() {
  // Проверяем наличие карты
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  // Читаем UID
  String uid = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    if (rfid.uid.uidByte[i] < 0x10) uid += "0";
    uid += String(rfid.uid.uidByte[i], HEX);
  }
  uid.toUpperCase();

  unsigned long now = millis();
  // Дебаунс: не отправлять ту же карту снова в течение DEBOUNCE_MS
  if (uid != lastUID || (now - lastReadTime) > DEBOUNCE_MS) {
    Serial.println("UID:" + uid);  // <-- это читает nfc_bridge.py
    lastUID = uid;
    lastReadTime = now;
  }

  rfid.PICC_HaltA();       // остановить текущую карту
  rfid.PCD_StopCrypto1();  // остановить шифрование
}
