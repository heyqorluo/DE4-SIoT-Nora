from http import client
import os, time
from influxdb_client_3 import InfluxDBClient3, Point
from influxdb_client_3 import flight_client_options
import certifi
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import openpyxl

# Read data
fh = open(certifi.where(), "r")
cert = fh.read()
fh.close()

token = "zNCFBPPJzHGz4mTAXe0W9GPf-yjyJndooj0Tfg8AqX23Jz3SSf2lnuDEiC3WMboTYXtT-DEVR9_IfYAs6kp6ig=="
org = "IoTProject"
host = "https://eu-central-1-1.aws.cloud2.influxdata.com"

client = InfluxDBClient3(host=host, token=token, org=org,flight_client_options= flight_client_options(tls_root_certs=cert))

# Query data
query = """SELECT *
FROM 'sensor value'
WHERE time >= now() - interval '15 day'
AND
("Nora/DHT/Humidity" IS NOT NULL OR "Nora/DHT/Temp" IS NOT NULL OR "Nora/lightintensity" IS NOT NULL)"""

# Execute the query
table = client.query(query=query, database="node-red", language='sql')

# Convert to dataframe
df = table.to_pandas().sort_values(by="time")
# print(df)

# Create a cross-correlation scatter plot
# sns.pairplot(df, kind="scatter")
# Customize the appearance
sns.pairplot(df, kind="scatter", diag_kind="kde", markers="o", height=2.5,
             plot_kws={'s': 20, 'alpha': 0.3}, diag_kws={'fill': True})
# Show the plot
# plt.show()
# Calculate the correlation coefficients
correlation_matrix = df.corr()
print(correlation_matrix)
correlation_matrix.to_excel("scatterplot.xlsx")
