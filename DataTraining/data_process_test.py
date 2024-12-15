from http import client
import os, time
from influxdb_client_3 import InfluxDBClient3, Point
from influxdb_client_3 import flight_client_options
import certifi
import pandas as pd

fh = open(certifi.where(), "r")
cert = fh.read()
fh.close()

token = "zNCFBPPJzHGz4mTAXe0W9GPf-yjyJndooj0Tfg8AqX23Jz3SSf2lnuDEiC3WMboTYXtT-DEVR9_IfYAs6kp6ig=="
org = "IoTProject"
host = "https://eu-central-1-1.aws.cloud2.influxdata.com"

client = InfluxDBClient3(host=host, token=token, org=org,flight_client_options= flight_client_options(tls_root_certs=cert))

# Query data
query = """SELECT *
FROM "sensor value"
WHERE
time >= now() - interval '2 days' 
AND
("Nora/DHT/Humidity" IS NOT NULL OR "Nora/DHT/Temp" IS NOT NULL OR "Nora/lightintensity" IS NOT NULL OR "Nora/moisture" IS NOT NULL)
"""

# Execute the query
table = client.query(query=query, database="node-red", language='sql')

# Convert to dataframe
df = table.to_pandas().sort_values(by="time")
# print(df)

# Make sure the time column is parsed correctly
df['time'] = pd.to_datetime(df['time'])
# Set time as the index of the DataFrame
df.set_index('time', inplace=True)

# Group the time stamps in half-hour intervals and calculate the average for each group
df_resampled = df.resample('30 min').mean()
df_resampled.reset_index(inplace=True)

# Drop rows with NaN values
df_resampled.dropna(inplace=True)

# print(df_resampled)

# Save the processed data to a new CSV file
# df_resampled.to_csv("data_raw 2024_12_07_1919group_processed_file_30min.csv", index=False)