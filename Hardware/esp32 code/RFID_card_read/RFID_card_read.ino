#include <SPI.h>
#include <MFRC522.h>

// Pin configuration for ESP32
#define SS_PIN 5      // SDA on MFRC522
#define RST_PIN 22    // RST on MFRC522

// Create MFRC522 instance
MFRC522 mfrc522(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(115200);
  
  // Initialize SPI with ESP32 pins
  SPI.begin(18, 19, 23, 5); // SCK, MISO, MOSI, SS

  // Set lower SPI clock speed (1 MHz) for compatibility
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
  mfrc522.PCD_Init(); 
  SPI.endTransaction();

  // Optional: increase antenna gain
  mfrc522.PCD_SetAntennaGain(mfrc522.RxGain_max);

  // Read and show firmware version
  byte version = mfrc522.PCD_ReadRegister(mfrc522.VersionReg);
  Serial.print("MFRC522 Version: 0x");
  Serial.println(version, HEX);

  if (version == 0x00 || version == 0xFF) {
    Serial.println("ERROR: Communication with MFRC522 failed.");
  } else {
    Serial.println("RFID Scanner Initialized.");
    Serial.println("Place your RFID tag near the scanner...");
  }
}

void loop() {
  // Check if a new card is present
  if (!mfrc522.PICC_IsNewCardPresent()) {
    delay(100);
    return;
  }

  // Check if we can read the card
  if (!mfrc522.PICC_ReadCardSerial()) {
    Serial.println("Card detected but reading failed.");
    return;
  }

  Serial.print("Card UID:");
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    Serial.print(" ");
    Serial.print(mfrc522.uid.uidByte[i], HEX);
  }
  Serial.println();

  // Halt the card to stop communication
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}
