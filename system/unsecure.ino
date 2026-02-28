// Claude Opus 4.5 am 17.01.2026

#include <WiFi.h>
#include "esp_camera.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "esp_task_wdt.h"
#include "time.h"  

const char* ssid = "TP-Link_4E56";
const char* password = "48772280";
const char* serverIP = "192.168.0.100";
const int serverPort = 9000;
String camName = "Garten_Cam_01"; // bzw. Cam 02 und Cam03

const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 3600;      
const int daylightOffset_sec = 3600;  

WiFiClient client;
unsigned long frameCount = 0;

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

unsigned long long getEpochMillis() {
  struct timeval tv;
  gettimeofday(&tv, NULL);
  return (unsigned long long)(tv.tv_sec) * 1000ULL + (unsigned long long)(tv.tv_usec / 1000);
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  Serial.begin(115200);
  delay(500);
  esp_task_wdt_init(30, false);
  
  WiFi.begin(ssid, password);
  WiFi.setSleep(false);
  while (WiFi.status() != WL_CONNECTED) delay(100);
  Serial.println("WLAN OK: " + WiFi.localIP().toString());

  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
  Serial.print("NTP Sync");
  while (time(nullptr) < 1000000000) {
    Serial.print(".");
    delay(100);
  }
  Serial.println(" OK");
  
  struct tm timeinfo;
  getLocalTime(&timeinfo);
  Serial.println(&timeinfo, "Zeit: %H:%M:%S %d.%m.%Y");

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
  config.frame_size = FRAMESIZE_HVGA;
  config.jpeg_quality = 10;
  config.fb_count = 2;

  if (esp_camera_init(&config) != ESP_OK) {
    Serial.println("Kamera FEHLER");
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
  Serial.println("Kamera OK - HVGA 480x320 mit NTP");
}

void loop() {
    yield();
    if (!client.connected()) {
        client.stop();
        Serial.print("TCP...");
        if (!client.connect(serverIP, serverPort, 5000)) {
            Serial.println("FEHLER");
            delay(2000);
            return;
        }
        Serial.println("OK");
        client.setNoDelay(true);
        delay(50);
    }
    
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
        delay(10);
        return;
    }
    
    unsigned long long timestamp = getEpochMillis();
    String header = "CAM:" + camName + ":" + String(fb->len) + ":" + String(timestamp) + "\n";
    
    uint8_t* dataToSend = (uint8_t*)malloc(fb->len);
    if (!dataToSend) {
        esp_camera_fb_return(fb);
        return;
    }
    memcpy(dataToSend, fb->buf, fb->len);
    
    if (client.print(header) == 0) {
        client.stop();
        free(dataToSend);
        esp_camera_fb_return(fb);
        return;
    }
    
    size_t sent = 0;
    while (sent < fb->len) {
        size_t toSend = min((size_t)4096, fb->len - sent);
        size_t result = client.write(dataToSend + sent, toSend); 
        if (result == 0) {
            client.stop();
            break;
        }
        sent += result;
        yield();
    }
    
    free(dataToSend);  
    esp_camera_fb_return(fb);
    frameCount++;
    delay(10);
    if (frameCount % 50 == 0) {
        Serial.printf("Frames: %lu\n", frameCount);
    }
}
