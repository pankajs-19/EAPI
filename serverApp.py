from fastapi import FastAPI, Request
import requests
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from pydantic import BaseModel
import numpy as np
import pandas as pd
from datetime import datetime
import joblib
from apscheduler.schedulers.background import BackgroundScheduler
import os

app = FastAPI()

# Mount static files (for CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load historical weather data
weatherHistory = pd.read_csv(r"Datasets\Mumbai_1990_Absolute_Santacruz.csv")

# Ensure the 'time' column is in the correct format and set it as the index
weatherHistory['time'] = pd.to_datetime(weatherHistory['time'], format='%d-%m-%Y')
weatherHistory.set_index('time', inplace=True)

# Calculate monthly and day-of-year averages using expanding mean
weatherHistory["monthly_average"] = weatherHistory.groupby(weatherHistory.index.month)["prcp"].transform(lambda x: x.expanding(1).mean())
weatherHistory["day_of_year_average"] = weatherHistory.groupby(weatherHistory.index.day_of_year)["prcp"].transform(lambda x: x.expanding(1).mean())

# Reset the index for easier manipulation
weatherHistory.reset_index(inplace=True)

IMU_CSV_PATH = "imu_data.csv"

# Ensure the CSV file exists with headers
if not os.path.exists(IMU_CSV_PATH):
    pd.DataFrame(columns=["timestamp", "x", "y", "z", "magnitude", "distance_cm", "temperature"]).to_csv(IMU_CSV_PATH, index=False)

IMU_CSV_PATH2 = "imu_data2.csv"

# Ensure the CSV file exists with headers
if not os.path.exists(IMU_CSV_PATH2):
    pd.DataFrame(columns=["timestamp", "x", "y", "z", "magnitude", "distance_cm", "temperature"]).to_csv(IMU_CSV_PATH2, index=False)

# Load the trained model
classifier = open('Model/flood_prediction_model.pkl', "rb")
model = joblib.load(classifier)

# Define the input data model for weather prediction
class WeatherData(BaseModel):
    tempAvg: float
    tempMin: float
    tempMax: float
    prcp: float
    predictDate: str  # Date in 'YYYY-MM-DD' format

# Define the input data model for IMU and ultrasonic sensor data
class IMUData(BaseModel):
    x: float
    y: float
    z: float
    magnitude: float
    warning: str
    distance_cm: float
    temperature: float

# Global variable to store the latest weather data
latest_weather_data = {}

# Global variable to store the latest IMU data from the forst Node
latest_imu_data = {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "magnitude": 0.0,
    "warning": "",
    "distance_cm": 0.0,
    "temperature": 0.0
}

# Global variable to store the latest IMU data from the second Node
latest_imu_data2 = {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "magnitude": 0.0,
    "warning": "",
    "distance_cm": 0.0,
    "temperature": 0.0
}

# Function to fetch weather data from Open-Meteo API
def fetch_weather_data():
    global latest_weather_data
    url = f'https://api.open-meteo.com/v1/forecast?latitude=12.9194&longitude=79.6717&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto&forecast_days=1'
    response = requests.get(url).json()

    latest_weather_data = {
        'date': response['daily']['time'][0],
        'temp_max': response['daily']['temperature_2m_max'][0],
        'temp_min': response['daily']['temperature_2m_min'][0],
        'temp_avg': (response['daily']['temperature_2m_max'][0] + response['daily']['temperature_2m_min'][0]) / 2,
        'precipitation': response['daily']['precipitation_sum'][0]
    }
    print("Fetched latest weather data:", latest_weather_data)

# Schedule the weather data fetch job
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_weather_data, 'interval', hours=1)  # Fetch data every hour
scheduler.start()

# Fetch initial weather data
fetch_weather_data()

@app.get('/')
def root():
    return FileResponse("static/index.html")

@app.get('/weather')
def get_weather():
    return JSONResponse(content=latest_weather_data)

@app.post('/imu-data')
async def receive_imu_data(data: IMUData):
    global latest_imu_data
    latest_imu_data = data.dict()

    # Add a timestamp to the data
    latest_imu_data["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Convert to DataFrame and append to CSV
    df = pd.DataFrame([latest_imu_data])
    df.to_csv(IMU_CSV_PATH, mode='a', header=False, index=False)

    return {"Ack": "IMU data received successfully", "data": latest_imu_data}

@app.get('/imu-data')
def get_imu_data():
    return JSONResponse(content=latest_imu_data)

@app.post('/imu-data2')
async def receive_imu_data2(data: IMUData):
    global latest_imu_data2
    latest_imu_data2 = data.dict()

    # Add a timestamp to the data
    latest_imu_data2["timestamp"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Convert to DataFrame and append to CSV
    df = pd.DataFrame([latest_imu_data2])
    df.to_csv(IMU_CSV_PATH2, mode='a', header=False, index=False)

    return {"Ack": "IMU data 2 received successfully", "data": latest_imu_data2}

@app.get('/imu-data2')
def get_imu_data2():
    return JSONResponse(content=latest_imu_data2)

@app.post('/predict')
async def predictFlood(data: WeatherData):
    # Convert input data to dictionary
    data = data.dict()

    # Extract input values
    tempAvg = data['tempAvg']
    tempMin = data['tempMin']
    tempMax = data['tempMax']
    prcp = data['prcp']
    predictDate = datetime.strptime(data['predictDate'], '%Y-%m-%d')

    # Step 1: Calculate average of that month till that day
    month = predictDate.month
    day = predictDate.day

    # Filter historical data for the same month and days <= current day
    monthly_data = weatherHistory[(weatherHistory['time'].dt.month == month) & 
                                  (weatherHistory['time'].dt.day <= day)]

    # Get the monthly average precipitation for the given day
    monthly_avg_precipitation = monthly_data[monthly_data['time'] == predictDate]['monthly_average'].values[0]

    # Step 2: Calculate day of the year average
    day_of_year = predictDate.timetuple().tm_yday

    # Filter historical data for the same day of the year
    day_of_year_data = weatherHistory[weatherHistory['time'].dt.dayofyear == day_of_year]

    # Get the day-of-year average precipitation for the given day
    day_of_year_avg_precipitation = day_of_year_data[day_of_year_data['time'] == predictDate]['day_of_year_average'].values[0]

    # Step 3: Prepare the feature vector for prediction
    feature_vector = np.array([
        tempAvg,
        tempMin,
        tempMax,
        prcp,
        monthly_avg_precipitation,
        day_of_year_avg_precipitation
    ]).reshape(1, -1)

    # Step 4: Predict flood level using the XGBoost model
    prediction = model.predict(feature_vector)[0]

    # Step 5: Return the prediction
    message = f"Predicted Level: {prediction}"
    return {'prediction': message}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
