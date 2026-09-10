/*
 * ============================================================
 *  AI Smart Farming Assistant - Wokwi ESP32 Virtual Sensor
 * ============================================================
 *
 *  This sketch runs inside the Wokwi ESP32 simulator (https://wokwi.com).
 *  It simulates a field sensor node and pushes readings to the
 *  Flask backend over the internet using HTTP POST.
 *
 *  Simulated sensors:
 *    1. Soil moisture  - read from a potentiometer (knob) on GPIO 36
 *    2. Temperature    - read from a DHT22 sensor on GPIO 15
 *    3. Humidity       - read from the same DHT22 sensor on GPIO 15
 *    4. Rainfall       - read from a potentiometer (knob) on GPIO 39
 *                        (0 mm min ... 30 mm max, simulated)
 *
 *  Data flow:
 *    ESP32 reads sensors
 *        -> builds a JSON string
 *        -> HTTP POST to the Flask API (/api/sensor-data)
 *        -> server validates, stores in SQLite, runs decision logic
 *        -> returns analysis as JSON (printed in the Serial Monitor)
 *
 *  Open the Serial Monitor (9600 baud) to see live output.
 * ============================================================
 */

#include <WiFi.h>            // Wokwi provides a simulated WiFi network
#include <HTTPClient.h>      // Used to send HTTP POST requests
#include <WiFiClientSecure.h>// Used for HTTPS (Render's URL is HTTPS)
#include <DHT.h>             // DHT22 temperature / humidity sensor driver

// ============================================================
// >>> CONFIGURABLE SERVER URL <<<
// ------------------------------------------------------------
// Replace YOUR-RENDER-APP below with the real Render URL AFTER
// deployment. Example:
//   SERVER_URL = "https://my-farm-app.onrender.com/api/sensor-data"
//
// NOTE: An HTTPS URL is used because Render serves HTTPS only.
// ============================================================
#define SERVER_URL "https://YOUR-RENDER-APP.onrender.com/api/sensor-data"

// Wokwi simulator uses this WiFi network. On real hardware this
// would be the farmer's router / mobile hotspot.
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASS = "";

// Sensor pins (see diagram.json for the wiring)
const int SOIL_MOISTURE_PIN = 36;  // GPIO 36 (A0)  -> soil moisture potentiometer
const int RAINFALL_PIN      = 39;  // GPIO 39 (A1)  -> rainfall potentiometer
const int DHT_PIN           = 15;  // GPIO 15       -> DHT22 data pin
#define DHT_TYPE DHT22             // our sensor is a DHT22

// How often to send a reading to the server (milliseconds)
const unsigned long SEND_INTERVAL_MS = 10000;  // every 10 seconds

DHT dht(DHT_PIN, DHT_TYPE);

// Keep track of the last time we sent data
unsigned long lastSendTime = 0;

/* ------------------------------------------------------------
 * Read the soil moisture from the potentiometer.
 * The potentiometer gives 0..4095. We convert that to 0..100 (%).
 * ---------------------------------------------------------- */
float readSoilMoisture() {
  int raw = analogRead(SOIL_MOISTURE_PIN);   // 0..4095
  float moisture = raw / 4095.0 * 100.0;     // 0..100 %
  return moisture;
}

/* ------------------------------------------------------------
 * Read the simulated rainfall from the second potentiometer.
 * 0..4095 is converted to 0..30 mm.
 * ---------------------------------------------------------- */
float readRainfall() {
  int raw = analogRead(RAINFALL_PIN);        // 0..4095
  float rain = raw / 4095.0 * 30.0;          // 0..30 mm
  return rain;
}

/* ------------------------------------------------------------
 * Connect to WiFi and keep retrying until success.
 * ---------------------------------------------------------- */
void connectToWiFi() {
  Serial.println();
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.begin(WIFI_SSID, WIFI_PASS);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
    attempts++;
    // Keep trying forever but print every 10 tries so the user
    // can see what is happening in the Serial Monitor.
    if (attempts % 10 == 0) {
      Serial.println();
      Serial.println("Still trying to connect...");
    }
  }

  Serial.println();
  Serial.print("WiFi connected! IP address: ");
  Serial.println(WiFi.localIP());
}

/* ------------------------------------------------------------
 * Send one JSON reading to the Flask API and print the response.
 * This function never crashes the program: if anything fails it
 * prints the error and returns.
 * ---------------------------------------------------------- */
void sendSensorData(float moisture, float temperature, float humidity, float rainfall) {

  // Build the JSON body as a simple string (beginner friendly)
  String jsonBody = "{";
  jsonBody += "\"soil_moisture\":" + String(moisture, 1) + ",";
  jsonBody += "\"temperature\":" + String(temperature, 1) + ",";
  jsonBody += "\"humidity\":" + String(humidity, 1) + ",";
  jsonBody += "\"rainfall\":" + String(rainfall, 1);
  jsonBody += "}";

  Serial.println();
  Serial.println("========== Sending sensor data ==========");
  Serial.println(jsonBody);

  // Tell the server we are sending JSON
  HTTPClient http;
  http.addHeader("Content-Type", "application/json");

  // The server URL is HTTPS, so a secure client is used.
  WiFiClientSecure client;
  client.setInsecure();   // no certificate check (fine for a demo)

  // Begin the request
  if (!http.begin(client, SERVER_URL)) {
    Serial.println("ERROR: Could not reach the server URL. Check SERVER_URL in the code.");
    http.end();
    return;
  }

  // Perform the POST request
  int httpCode = http.POST(jsonBody);

  if (httpCode > 0) {
    Serial.print("Server responded with HTTP code: ");
    Serial.println(httpCode);

    // Print the analysis returned by the server
    String response = http.getString();
    Serial.println("Server response:");
    Serial.println(response);
  } else {
    // Connection failed - print the error and try again next round
    Serial.print("ERROR: HTTP request failed, error: ");
    Serial.println(http.errorToString(httpCode));
    Serial.println("The server may be offline or the URL may be wrong. Will retry...");
  }

  http.end();  // free the resources
}

/* ------------------------------------------------------------
 * Arduino setup - runs once at startup.
 * ---------------------------------------------------------- */
void setup() {
  Serial.begin(9600);
  delay(500);

  Serial.println();
  Serial.println("============================================");
  Serial.println("  AI Smart Farming Assistant - ESP32 Node");
  Serial.println("============================================");

  dht.begin();          // start the DHT22 sensor
  connectToWiFi();      // wait for a WiFi connection
  lastSendTime = millis();
}

/* ------------------------------------------------------------
 * Arduino loop - runs forever.
 * ---------------------------------------------------------- */
void loop() {
  // Make sure WiFi is still connected on real hardware
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected. Reconnecting...");
    connectToWiFi();
  }

  // Only send when enough time has passed
  unsigned long nowMillis = millis();
  if (nowMillis - lastSendTime >= SEND_INTERVAL_MS) {
    lastSendTime = nowMillis;

    // ----- Read the sensors -----
    float moisture   = readSoilMoisture();          // 0..100 %
    float rainfall   = readRainfall();              // 0..30 mm
    float temperature = dht.readTemperature(false); // degrees Celsius
    float humidity   = dht.readHumidity();          // 0..100 %

    // DHT22 returns "NaN" (Not a Number) if the reading failed
    if (isnan(temperature) || isnan(humidity)) {
      Serial.println("ERROR: Could not read the DHT22 sensor.");
      // Use fallback values so the demo continues to work
      temperature = 30.0;
      humidity = 55.0;
    }

    // ----- Print the current readings -----
    Serial.println();
    Serial.println("---- Current sensor readings ----");
    Serial.print("Soil moisture: ");
    Serial.print(moisture);
    Serial.println(" %");
    Serial.print("Temperature:   ");
    Serial.print(temperature);
    Serial.println(" C");
    Serial.print("Humidity:      ");
    Serial.print(humidity);
    Serial.println(" %");
    Serial.print("Rainfall:      ");
    Serial.print(rainfall);
    Serial.println(" mm");

    // ----- Send the readings to the server -----
    sendSensorData(moisture, temperature, humidity, rainfall);

    Serial.println("============================================");
  }
}