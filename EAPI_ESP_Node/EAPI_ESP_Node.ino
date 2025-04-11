#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <SoftwareSerial.h>
#include <TinyGPS++.h>

// MPU6050 instance
Adafruit_MPU6050 mpu;  // D1-SCL D2-SDA on NodeMCU

// Define the RX and TX pins for Software Serial 2
#define RX 2 //D4
#define TX 0 //D3

#define GPS_BAUD 9600

// The TinyGPS++ object
TinyGPSPlus gps;

// Create an instance of Software Serial
SoftwareSerial gpsSerial(RX, TX);

// Earthquake magnitude thresholds
const float MILD_THRESHOLD = 0.2;
const float EARTHQUAKE_THRESHOLD = 0.5;
const float SEVERE_THRESHOLD = 1.5;

// Ultrasonic sensor pins
const int trigPin = 14;  // D5 on NodeMCU 
const int echoPin = 12;  // D6 on NodeMCU 

// FastAPI server URL
const char* serverUrl = "http://henrycapron735.ddns.net:8000/imu-data";  //RPI server URL

// Buzzer pin
const int buzzerPin = 13; // D7

// WiFi credentials
const char* ssid = "REPLACE_WITH_YOUR_SSID";
const char* pass = "REPLACE_WITH_YOUR_PASSWORD";

// Global variables
long duration;
float distanceCm;

void setup() {
  Serial.begin(115200);

  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(buzzerPin, OUTPUT);
  digitalWrite(buzzerPin, LOW);

  Serial.println("Initializing MPU6050...");
  if (!mpu.begin()) {
    Serial.println("MPU6050 not found! Check connections.");
    while (1) delay(10);
  }
  Serial.println("MPU6050 Initialized!");

  // Start Serial 2 with the defined RX and TX pins and a baud rate of 9600
  gpsSerial.begin(GPS_BAUD);
  Serial.println("Software Serial started at 9600 baud rate");

  WiFi.begin(ssid, pass);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print("Connecting to WiFi...\n");
    delay(1000);
  }
  Serial.println("\nWiFi Connected!");

  // Initialize SIM800L
  Serial.println("AT"); // Check module
  delay(100);
    
  Serial.println("AT+CMGF=1"); // Set SMS mode to TEXT
  delay(100);
    
  Serial.println("AT+CSMP=17,167,0,0"); // Set Class 1 (Phone Storage)
  delay(100);
    
  Serial.println("AT+CREG?"); // Check network registration
  delay(100);
}

void loop() {
  // ---------- Ultrasonic Sensor Measurement ----------
  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  duration = pulseIn(echoPin, HIGH);
  distanceCm = duration * 0.034 / 2;        // Convert to cm

  Serial.print("Water Level: ");
  Serial.print(distanceCm);
  Serial.println(" cm");

  // ---------- MPU6050 Data Acquisition ----------
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // Convert acceleration data to g (1g = 9.81 m/s²)
  float accel_x = (a.acceleration.x - 10.40) / 9.81;  // Correcting the offset by subtracting 10.40
  float accel_y = (a.acceleration.y - 0.11) / 9.81;   // Correcting the offset by subtracting 0.11
  float accel_z = a.acceleration.z / 9.81;

  // Calculate Peak Ground Acceleration (PGA)
  float pga = sqrt(accel_x * accel_x + accel_y * accel_y + accel_z * accel_z);

  // Calculate Root Mean Square (RMS) Acceleration
  float rms = sqrt((accel_x * accel_x + accel_y * accel_y + accel_z * accel_z) / 3);

  // Continuously read GPS data
  while (gpsSerial.available() > 0) {
      gps.encode(gpsSerial.read());
  }

  // ---------- Earthquake Detection ----------
  String message;
  if (pga >= SEVERE_THRESHOLD) {
    message = "Severe Earthquake! Take Cover!";
    digitalWrite(buzzerPin, HIGH);
    sendSMS(message);
  } else if (pga >= EARTHQUAKE_THRESHOLD) {
    message = "Earthquake Alert!";
    sendSMS(message);
    digitalWrite(buzzerPin, HIGH);
  } else if (pga >= MILD_THRESHOLD) {
    message = "Mild Tremor Detected";
    sendSMS(message);
    digitalWrite(buzzerPin, HIGH);
  } else {
    // message = "No Significant Movement.";
    digitalWrite(buzzerPin, LOW);
  }

  // ---------- Send Data to FastAPI ----------
  if (WiFi.status() == WL_CONNECTED) {
    WiFiClient client;
    HTTPClient http;

    http.begin(client, serverUrl);
    http.addHeader("Content-Type", "application/json");

  String payload = "{\"x\":" + String(accel_x, 4) + 
                 ",\"y\":" + String(accel_y, 4) + 
                 ",\"z\":" + String(accel_z, 4) + 
                 ",\"magnitude\":" + String(pga, 2) + 
                 ",\"warning\":\"" + message + "\"" + 
                 ",\"distance_cm\":" + String(distanceCm, 2) + 
                 ",\"temperature\":" + String(temp.temperature, 2) + "}";

    int httpResponseCode = http.POST(payload);
    if (httpResponseCode > 0) {
      Serial.println("Data Sent Successfully!");
      Serial.println("Response: " + http.getString());
    } else {
      Serial.println("Error Sending Data! Code: " + String(httpResponseCode));
    }
    http.end();
  } else {
    Serial.println("WiFi Disconnected! Attempting Reconnection...");
    WiFi.begin(ssid, pass);
    while (WiFi.status() != WL_CONNECTED) {
      delay(1000);
      Serial.print(".");
    }
    Serial.println("\nReconnected!");
  }

  // ---------- Print data in Serial Monitor ----------

  Serial.println("PGA: " + String(pga));
  Serial.print("Temperature: ");
  Serial.print(temp.temperature);
  Serial.println("°C");
  Serial.println(message);
  Serial.println();

  delay(2000);
} 


void sendSMS(String message) {
    if (gps.location.isUpdated()) {
        message += " at ";
        message += String(gps.location.lat(), 6);
        message += ", ";
        message += String(gps.location.lng(), 6);
    } else {
        message += " Location: Unavailable";
    }

    // List of phone numbers
    String phoneNumbers[] = {"+ZZxxxxxxxxxx", "+ZZxxxxxxxxxx"}; //change ZZ with country code and xxxxxxxxxxx with phone number to sms
    int numCount = sizeof(phoneNumbers) / sizeof(phoneNumbers[0]);

    for (int i = 0; i < numCount; i++) {
        Serial.print("AT+CMGS=\"");
        Serial.print(phoneNumbers[i]);
        Serial.println("\"");
        delay(100);

        Serial.print(message);
        delay(100);

        Serial.write(26); // End message (Ctrl+Z)
        delay(5000); // Allow time for sending
    }
}

