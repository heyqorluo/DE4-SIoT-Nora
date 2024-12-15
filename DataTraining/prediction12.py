import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import load_model
from sklearn.metrics import mean_squared_error
from influxdb_client_3 import InfluxDBClient3, flight_client_options
import certifi
import matplotlib.pyplot as plt

# Set up InfluxDB connection
fh = open(certifi.where(), "r")
cert = fh.read()
fh.close()

token = "zNCFBPPJzHGz4mTAXe0W9GPf-yjyJndooj0Tfg8AqX23Jz3SSf2lnuDEiC3WMboTYXtT-DEVR9_IfYAs6kp6ig=="
org = "IoTProject"
host = "https://eu-central-1-1.aws.cloud2.influxdata.com"

client = InfluxDBClient3(host=host, token=token, org=org, flight_client_options=flight_client_options(tls_root_certs=cert))

# Query data from InfluxDB
query_test = """SELECT *
FROM "sensor value"
WHERE
time >= now() - interval '7 days'
AND
("Nora/DHT/Humidity" IS NOT NULL OR "Nora/DHT/Temp" IS NOT NULL OR "Nora/lightintensity" IS NOT NULL OR "Nora/moisture" IS NOT NULL)
"""

# Execute the query for the test data
table_test = client.query(query=query_test, database="node-red", language='sql')

# Convert to DataFrame and preprocess
df_test = table_test.to_pandas().sort_values(by="time")
df_test['time'] = pd.to_datetime(df_test['time'])
df_test.set_index('time', inplace=True)

# Resample and preprocess the test data
df_test_resampled = df_test.resample('2H').mean()  # Resample to 2-hour intervals
df_test_resampled.dropna(inplace=True)

# Define the same features and target as before
features = ['Nora/DHT/Humidity', 'Nora/DHT/Temp', 'Nora/lightintensity', 'Nora/moisture']
target = 'Nora/moisture'

# Load the trained model
model = load_model('LSTMmodel_new.keras')

# Define the sequence length and forecast horizon
seq_length = 24
forecast_horizon = 5

# Initialize the scaler
scaler = MinMaxScaler()
scaler.fit(df_test_resampled[features])  # Fit the scaler on the test data

# Normalize the test data
scaled_test_data = scaler.transform(df_test_resampled[features])

# Create sequences for prediction
def create_sequences(data, seq_length, forecast_horizon):
    X, y = [], []
    for i in range(len(data) - seq_length - forecast_horizon + 1):
        X.append(data[i:i + seq_length, :])
        y.append(data[i + seq_length:i + seq_length + forecast_horizon, features.index(target)])
    return np.array(X), np.array(y)

X_test, y_test = create_sequences(scaled_test_data, seq_length, forecast_horizon)

# Make predictions
y_pred = model.predict(X_test)

# Inverse transform predictions and actual values
def inverse_transform(data, scaler, n_features, target_index):
    # Create an array to hold the unscaled values
    y_unscaled = []
    
    for row in data:
        full_dim_data = np.zeros((len(row), n_features))
        full_dim_data[:, target_index] = row
        y_unscaled.append(scaler.inverse_transform(full_dim_data)[:, target_index])
    
    return np.array(y_unscaled)

n_features = len(features)
y_pred_unscaled = inverse_transform(y_pred, scaler, n_features, features.index(target))
y_test_unscaled = inverse_transform(y_test, scaler, n_features, features.index(target))

# Evaluate the model
mse = mean_squared_error(y_test_unscaled.flatten(), y_pred_unscaled.flatten())
print(f"Mean Squared Error (MSE) on Test Data: {mse:.2f}")

# Visualize the results
plt.figure(figsize=(12, 6))
plt.plot(range(len(y_test_unscaled.flatten())), y_test_unscaled.flatten(), label='Actual Values', marker='o')
plt.plot(range(len(y_pred_unscaled.flatten())), y_pred_unscaled.flatten(), label='Predicted Values', marker='x')
plt.title('Test Data: Actual vs Predicted Values')
plt.xlabel('Time Steps')
plt.ylabel('Moisture')
plt.legend()
plt.grid()
plt.show()
