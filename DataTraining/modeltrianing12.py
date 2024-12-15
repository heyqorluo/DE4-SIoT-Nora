import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error
from influxdb_client_3 import InfluxDBClient3, flight_client_options
import certifi

# Set up InfluxDB connection
fh = open(certifi.where(), "r")
cert = fh.read()
fh.close()

token = "zNCFBPPJzHGz4mTAXe0W9GPf-yjyJndooj0Tfg8AqX23Jz3SSf2lnuDEiC3WMboTYXtT-DEVR9_IfYAs6kp6ig=="
org = "IoTProject"
host = "https://eu-central-1-1.aws.cloud2.influxdata.com"

client = InfluxDBClient3(host=host, token=token, org=org, flight_client_options=flight_client_options(tls_root_certs=cert))

# Query data from InfluxDB
query = """SELECT *
FROM "sensor value"
WHERE
time >= timestamp '2024-12-02T00:00:00.000Z' AND time <= timestamp '2024-12-07T23:59:00.000Z'
AND
("Nora/DHT/Humidity" IS NOT NULL OR "Nora/DHT/Temp" IS NOT NULL OR "Nora/lightintensity" IS NOT NULL OR "Nora/moisture" IS NOT NULL)
"""

# Execute the query
table = client.query(query=query, database="node-red", language='sql')

# Convert to DataFrame and preprocess
df = table.to_pandas().sort_values(by="time")
df['time'] = pd.to_datetime(df['time'])
df.set_index('time', inplace=True)

# Group the time stamps in half-hour intervals and calculate the average for each group
df_resampled = df.resample('30 min').mean()
df_resampled.dropna(inplace=True)

# Fill missing values with 0
df_resampled.fillna(0, inplace=True)

# Print available columns to diagnose the issue
print("Available columns in the DataFrame:")
print(df_resampled.columns.tolist())

# Define features and target column
features = ['Nora/DHT/Humidity', 'Nora/DHT/Temp', 'Nora/lightintensity', 'Nora/moisture']
target = 'Nora/moisture'

# Check if target is in features
if target not in df_resampled.columns:
    print(f"Target '{target}' is not found in the DataFrame columns.")
else:
    # If the target exists, proceed
    # Normalize the data
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df_resampled[features])  # Normalize the features

    # Create sequences for LSTM model
    def create_sequences(data, seq_length, forecast_horizon, target_index):
        X, y = [], []
        for i in range(len(data) - seq_length - forecast_horizon + 1):
            X.append(data[i:i+seq_length, :])  # Input features
            y.append(data[i + seq_length:i + seq_length + forecast_horizon, target_index])  # Target
        return np.array(X), np.array(y)

    # Define the sequence length and forecast horizon
    seq_length = 60
    forecast_horizon = 5
    target_index = features.index(target)

    # Generate sequences
    X, y = create_sequences(scaled_data, seq_length, forecast_horizon, target_index)

    # Split the data into training and testing sets
    train_size = int(0.8 * len(X))  # 80% for training
    X_train, X_test = X[:train_size], X[train_size:]
    y_train, y_test = y[:train_size], y[train_size:]

    print(f"Training set: {len(X_train)} samples")
    print(f"Testing set: {len(X_test)} samples")

    # Construct the LSTM model
    model = Sequential()
    model.add(LSTM(64, input_shape=(seq_length, len(features)), return_sequences=False))
    model.add(Dense(forecast_horizon))
    model.compile(optimizer='adam', loss='mse')

    # Train the model
    model.fit(X_train, y_train, epochs=100, batch_size=8, validation_data=(X_test, y_test), verbose=1)

    # Save the model
    model.save('LSTMmodel_new.keras')
