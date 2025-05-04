#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 5    // SDA
#define RST_PIN 22

MFRC522 rfid(SS_PIN, RST_PIN);  

MFRC522::MIFARE_Key key;

byte blockNum = 1;  // Block to write to (don't use block 0)
byte dataBlock[] = {
  'H', 'e', 'l', 'l', 'o', ' ', 'R', 'F', 'I', 'D', '!', '!', '!', '!', '!', '!'  // 16 bytes
};
byte buffer[18];
byte size = sizeof(buffer);

void setup() {
  Serial.begin(115200);
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("Scan RFID card to write/read...");

  // Set key (default is all 0xFF)
  for (byte i = 0; i < 6; i++) {
    key.keyByte[i] = 0xFF;
  }
}

void loop() {
  // Wait for card
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) {
    return;
  }

  Serial.print("Card UID: ");
  for (byte i = 0; i < rfid.uid.size; i++) {
    Serial.print(rfid.uid.uidByte[i], HEX);
    Serial.print(" ");
  }
  Serial.println();

  // Authenticate before read/write
  MFRC522::StatusCode status;
  status = rfid.PCD_Authenticate(
    MFRC522::PICC_CMD_MF_AUTH_KEY_A,
    blockNum, &key, &(rfid.uid));
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Auth failed: ");
    Serial.println(rfid.GetStatusCodeName(status));
    return;
  }

  // === Write Data ===
  status = rfid.MIFARE_Write(blockNum, dataBlock, 16);
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Write failed: ");
    Serial.println(rfid.GetStatusCodeName(status));
  } else {
    Serial.println("Write successful.");
  }

  // === Read Data ===
  status = rfid.MIFARE_Read(blockNum, buffer, &size);
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Read failed: ");
    Serial.println(rfid.GetStatusCodeName(status));
  } else {
    Serial.print("Data read from block ");
    Serial.print(blockNum);
    Serial.print(": ");
    for (int i = 0; i < 16; i++) {
      Serial.write(buffer[i]); // Print as characters
    }
    Serial.println();
  }

  rfid.PICC_HaltA();        // Halt PICC
  rfid.PCD_StopCrypto1();   // Stop encryption
  delay(3000);
}
