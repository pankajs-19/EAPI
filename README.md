# EAPI
Early Disaster Warning System API &amp; Server
# Early Disaster Warning System

A low-cost, scalable, and efficient real-time early disaster detection and warning system designed using IoT technologies. This project monitors seismic activity and water levels using sensor nodes and provides real-time alerts via SMS and web dashboards to enable rapid disaster response and preparedness.

## Features

- Multi-sensor node architecture (IMU + Ultrasonic + GPS)
- Wi-Fi and GSM communication for data transfer and SMS alerts
- Machine learning flood prediction model
- FastAPI and Flask-based server hosted on Raspberry Pi
- Real-time data visualization dashboard
- SMS and buzzer alerts on threshold breach
- Remote access via port forwarding

## Hardware Components

- NodeMCU (ESP8266)
- MPU6050 (IMU Sensor)
- HC-SR04 (Ultrasonic Sensor)
- SIM800L GSM Module
- GPS Module (Neo-6M)
- Raspberry Pi (Server)
- Buzzer, 18650 Battery

## Software Stack

| Component       | Technology             |
|----------------|------------------------|
| Firmware       | Arduino C++ (ESP8266)  |
| Backend Server | Python, FastAPI        |
| Frontend       | HTML, CSS, JavaScript  |
| ML Model       | XGBoost (Flood Prediction) |

## How It Works

1. Sensor node collects:
   - Seismic data from MPU6050
   - Water level from Ultrasonic sensor
   - Location from GPS
2. Node processes data locally to:
   - Classify tremor severity using PGA/RMS
   - Detect flood risk
3. Sends data to the Raspberry Pi server via HTTP over Wi-Fi
4. Server:
   - Processes and stores incoming data
   - Predicts flood risk using a machine learning model
   - Displays data on a live dashboard
   - Sends SMS alerts if thresholds are breached

## Real-Time Dashboard

- Earthquake PGA and RMS values
- Water level in cm
- Temperature readings
- Location of the event
- Flood prediction probability

## Alert System

- SMS alerts sent to emergency contacts
- Buzzer triggered for local warning
- Visual and audio indicators on dashboard

## Directory Structure

