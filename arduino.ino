#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN    10
#define RST_PIN   9

MFRC522 rfid(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(9600); 
  SPI.begin();           
  rfid.PCD_Init();       
}

void loop() {
  if (!rfid.PICC_IsNewCardPresent()) return;
  if (!rfid.PICC_ReadCardSerial()) return;

  String uidStr = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    uidStr += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    uidStr += String(rfid.uid.uidByte[i], HEX);
  }
  
  uidStr.toUpperCase();
  Serial.println(uidStr); // Envia apenas o UID e pula linha

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  delay(1000); // Evita múltiplas leituras rápidas
}