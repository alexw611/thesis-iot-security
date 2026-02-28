// Erstellt von Claude Opus 4.5 am 04.02.2026

#include <WiFi.h>
#include "esp_camera.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_task_wdt.h"
#include "time.h"
#include "mbedtls/aes.h"
#include "mbedtls/md.h"
#include "esp_random.h"

const char* ssid = "TP-Link_4E56";
const char* password = "48772280";
const char* serverIP = "192.168.0.100";
const int serverPort = 9000;
String camName = "Garten_Cam_03"; // bzw. Cam 02 und Cam 01

const uint8_t CAMERA_PSK[32] = {'T','h','i','s','I','s','3','2','B','y','t','e','S','e','c','r','e','t','K','e','y','F','o','r','C','a','m','!','!',0,0,0};
const uint8_t AES_KEY[16] = {'A','E','S','1','2','8','S','e','c','r','e','t','K','e','y','!'};

const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 3600;
const int daylightOffset_sec = 3600;

WiFiClient client;
unsigned long frameCount = 0;

unsigned long encryptionTime = 0;
unsigned long hmacTime = 0;

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void generateIV(uint8_t* iv) {
    for (int i = 0; i < 16; i++) {
        iv[i] = esp_random() & 0xFF;
    }
}

void bytesToHex(const uint8_t* bytes, size_t len, char* hexStr) {
    const char hexChars[] = "0123456789abcdef";
    for (size_t i = 0; i < len; i++) {
        hexStr[i * 2] = hexChars[(bytes[i] >> 4) & 0x0F];
        hexStr[i * 2 + 1] = hexChars[bytes[i] & 0x0F];
    }
    hexStr[len * 2] = '\0';
}

bool encryptAES_CTR(uint8_t* data, size_t dataLen, const uint8_t* iv) {
    mbedtls_aes_context aes;
    mbedtls_aes_init(&aes);
    
    if (mbedtls_aes_setkey_enc(&aes, AES_KEY, 128) != 0) {
        mbedtls_aes_free(&aes);
        return false;
    }
    
    uint8_t nonce_counter[16];
    uint8_t stream_block[16];
    size_t nc_off = 0;
    
    memcpy(nonce_counter, iv, 16);
    memset(stream_block, 0, 16);
    
    int ret = mbedtls_aes_crypt_ctr(&aes, dataLen, &nc_off, 
                                     nonce_counter, stream_block, 
                                     data, data);
    
    mbedtls_aes_free(&aes);
    return (ret == 0);
}

void calculateHMAC(const char* message, char* hmacOut) {
    uint8_t hmacResult[32];
    
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
    mbedtls_md_hmac_starts(&ctx, CAMERA_PSK, 32);
    mbedtls_md_hmac_update(&ctx, (const unsigned char*)message, strlen(message));
    mbedtls_md_hmac_finish(&ctx, hmacResult);
    mbedtls_md_free(&ctx);
    bytesToHex(hmacResult, 8, hmacOut);
}

unsigned long long getEpochMillis() {
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (unsigned long long)(tv.tv_sec) * 1000ULL + 
           (unsigned long long)(tv.tv_usec / 1000);
}

void setup() {
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
    Serial.begin(115200);
    delay(500);
    
    Serial.println("\n========================================");
    Serial.println("  SECURE ESP32-CAM");
    Serial.println("  AES-128-CTR + HMAC-SHA256");
    Serial.println("========================================\n");
    
    esp_task_wdt_init(30, false);
    
    WiFi.begin(ssid, password);
    WiFi.setSleep(false);
    Serial.print("WiFi verbinden");
    while (WiFi.status() != WL_CONNECTED) {
        delay(100);
        Serial.print(".");
    }
    Serial.println("\n✅ WLAN OK: " + WiFi.localIP().toString());

    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    Serial.print("NTP Sync");
    int ntpRetry = 0;
    while (time(nullptr) < 1000000000 && ntpRetry < 100) {
        Serial.print(".");
        delay(100);
        ntpRetry++;
    }
    
    if (time(nullptr) > 1000000000) {
        Serial.println(" ✅ OK");
        struct tm timeinfo;
        getLocalTime(&timeinfo);
        Serial.println(&timeinfo, "Zeit: %H:%M:%S %d.%m.%Y");
    } else {
        Serial.println(" ⚠️ NTP fehlgeschlagen - verwende Fallback");
    }

    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 16000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_HVGA;  // 480x320
    config.jpeg_quality = 10;
    config.fb_count = 2;
    
    if (esp_camera_init(&config) != ESP_OK) {
        Serial.println("❌ Kamera FEHLER");
        ESP.restart();
    }
    
    sensor_t *s = esp_camera_sensor_get();
    s->set_brightness(s, 0);
    s->set_contrast(s, 0);
    s->set_saturation(s, 0);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_exposure_ctrl(s, 1);
    s->set_aec2(s, 0);
    s->set_gain_ctrl(s, 1);
    
    Serial.println("✅ Kamera OK - HVGA 480x320");
    Serial.println("\n🔐 Sicherheitsfeatures aktiv:");
    Serial.println("   • AES-128-CTR Verschlüsselung");
    Serial.println("   • HMAC-SHA256 Authentifizierung");
    Serial.println("   • Replay-Schutz via Timestamp\n");
}


void loop() {
    yield();
    
    if (!client.connected()) {
        client.stop();
        Serial.print("🔌 TCP Verbindung...");
        if (!client.connect(serverIP, serverPort, 5000)) {
            Serial.println(" ❌ FEHLER");
            delay(2000);
            return;
        }
        Serial.println(" ✅ OK");
        client.setNoDelay(true);
        delay(50);
    }

    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        delay(10);
        return;
    }
    
    unsigned long long timestamp = getEpochMillis();
    String timestampStr = String(timestamp);

    unsigned long hmacStart = micros();
    
    String hmacMessage = camName + ":" + timestampStr;
    char hmacHex[17];  
    calculateHMAC(hmacMessage.c_str(), hmacHex);
    hmacTime = micros() - hmacStart;
    uint8_t iv[16];
    generateIV(iv);
    char ivHex[33];
    bytesToHex(iv, 16, ivHex);
    unsigned long encStart = micros();
    uint8_t* encryptedData = (uint8_t*)malloc(fb->len);
    if (!encryptedData) {
        Serial.println("❌ Speicherfehler");
        esp_camera_fb_return(fb);
        return;
    }
    memcpy(encryptedData, fb->buf, fb->len);
    
    if (!encryptAES_CTR(encryptedData, fb->len, iv)) {
        Serial.println("❌ Verschlüsselung fehlgeschlagen");
        free(encryptedData);
        esp_camera_fb_return(fb);
        return;
    }
    
    encryptionTime = micros() - encStart;
    String header = "CAM:" + camName + ":" + 
                    String(fb->len) + ":" + 
                    timestampStr + ":" + 
                    String(hmacHex) + ":" + 
                    String(ivHex) + "\n";
    
    if (client.print(header) == 0) {
        Serial.println("❌ Header-Senden fehlgeschlagen");
        client.stop();
        free(encryptedData);
        esp_camera_fb_return(fb);
        return;
    }
    
    size_t sent = 0;
    while (sent < fb->len) {
        size_t toSend = min((size_t)4096, fb->len - sent);
        size_t result = client.write(encryptedData + sent, toSend);
        if (result == 0) {
            Serial.println("❌ Daten-Senden fehlgeschlagen");
            client.stop();
            break;
        }
        sent += result;
        yield();
    }
    
    free(encryptedData);
    esp_camera_fb_return(fb);
    frameCount++;
    delay(10);
    
    if (frameCount % 50 == 0) {
        Serial.printf("📊 Frames: %lu | Encrypt: %lu µs | HMAC: %lu µs\n", 
                      frameCount, encryptionTime, hmacTime);
    }
}
