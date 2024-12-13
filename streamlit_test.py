import streamlit as st
import pandas as pd
from http import client
import os
from influxdb_client_3 import InfluxDBClient3, Point
from influxdb_client_3 import flight_client_options
import certifi
import seaborn as sns
import matplotlib.pyplot as plt

import paho.mqtt.client as paho
from paho import mqtt
import plotly.express as px  # interactive charts
import time  # to simulate a real time data, time loop
from PIL import Image
import io
import json
import base64
import numpy as np


# --- Global Variable for Binary Data ---
binary_image_data_global = None  # Initialize the global variable

# --- MQTT Configuration ---
MQTT_BROKER = "beb8fb0b8c314776bf8d0bcc647382b5.s1.eu.hivemq.cloud"  # Replace with your MQTT broker address
mqtt_username = "noraluo"
mqtt_password = "Nora123456"

MQTT_PORT = 8883
MQTT_TOPIC_LED = "/LEDControl"
MQTT_TOPIC_PUMP = "/PUMPControl"
MQTT_TOPIC_CAMERA1 = "TAKE"
MQTT_TOPIC_CAMERA2 = "FLASH"
MQTT_TOPIC_PICTURE = "PICTURE"

# Local storage directory
IMAGE_DIR = "captured_images"
os.makedirs(IMAGE_DIR, exist_ok=True)  # Create the directory if it doesn't exist

# Callback functions
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print("Connected successfully")
    else:
        print(f"Connection failed with code {rc}")

def on_publish(client, userdata, mid, properties=None):
    print("Message published with mid: " + str(mid))

def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    print("Subscribed successfully: " + str(mid) + ", QoS: " + str(granted_qos))


def on_message(client, userdata, msg):
    global binary_image_data_global
    try:
        if msg.topic == MQTT_TOPIC_PICTURE:
            binary_image_data_global = msg.payload
            print("Image received successfully.")
            print(binary_image_data_global)
        else:
            # Handle other topics
            payload = msg.payload.decode("utf-8")
            print(f"Received message on topic {msg.topic}: {payload}")
    except Exception as e:
        print(f"Error during message processing: {e}")

       
# Client setup
client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
client.on_connect = on_connect
client.on_subscribe = on_subscribe
client.on_message = on_message
client.on_publish = on_publish

client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLSv1_2)
client.username_pw_set(mqtt_username, mqtt_password)
client.connect(MQTT_BROKER, MQTT_PORT)

# Subscribe to the topic
client.subscribe(MQTT_TOPIC_LED, qos=2)
client.subscribe(MQTT_TOPIC_PUMP, qos=2)
# Subscribe to the camera topics
client.subscribe(MQTT_TOPIC_CAMERA1, qos=2)
client.subscribe(MQTT_TOPIC_CAMERA2, qos=2)
client.subscribe(MQTT_TOPIC_PICTURE, qos=2)


# Start the MQTT loop in a separate thread
client.loop_start()


# Refresh data every 1 minute
st.write("Last updated: ", time.ctime())

if st.button("Refresh Data"):
    st.rerun()

# --- Time Range Dropdown ---
time_range_options = [
    "Past 30 mins",
    "Past 1 hour",
    "Past 3 hours",
    "Past 12 hours",
    "Past 24 hours",
    "Past 2 days",
    "Past 7 days",
    "Past 15 days",
]

default_time_range = "Past 2 days" # set default time range
selected_time_range = st.selectbox("Select time range", time_range_options, index=time_range_options.index(default_time_range))

# --- Map time range to InfluxDB interval ---
time_range_mapping = {
    "Past 30 mins": "30 minutes",
    "Past 1 hour": "1 hour",
    "Past 3 hours": "3 hours",
    "Past 12 hours": "12 hours",
    "Past 24 hours": "1 day",
    "Past 2 days": "2 days",
    "Past 7 days": "7 days",
    "Past 15 days": "15 days",
}
influx_interval = time_range_mapping[selected_time_range]



# Read data
fh = open(certifi.where(), "r")
cert = fh.read()
fh.close()

token = "zNCFBPPJzHGz4mTAXe0W9GPf-yjyJndooj0Tfg8AqX23Jz3SSf2lnuDEiC3WMboTYXtT-DEVR9_IfYAs6kp6ig=="
org = "IoTProject"
host = "https://eu-central-1-1.aws.cloud2.influxdata.com"

client_influx = InfluxDBClient3(host=host, token=token, org=org,flight_client_options= flight_client_options(tls_root_certs=cert))

# Query data
query = f"""SELECT *
FROM 'sensor value'
WHERE time >= now() - interval '{influx_interval}'
AND
("Nora/DHT/Humidity" IS NOT NULL OR "Nora/DHT/Temp" IS NOT NULL OR "Nora/lightintensity" IS NOT NULL OR "Nora/moisture" IS NOT NULL)"""

# Execute the query
table = client_influx.query(query=query, database="node-red", language='sql')

# Convert to dataframe
df = table.to_pandas().sort_values(by="time")

# print(df)


st.title('IoT Plant Watering System :seedling:')
st.info("This is a dashboard for monitoring the real-time data from the IoT plant watering system. You can also control the LED, pump, and camera using the buttons below.")
st.subheader("Real-time Data Monitor :computer:", divider=True)
# --- Layout for the charts ---
col1, col2 = st.columns(2)
col3, col4 = st.columns(2)
with col1:
    fig1 = px.line(df, x="time", y="Nora/DHT/Humidity", title="Humidity")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    fig2 = px.line(df, x="time", y="Nora/DHT/Temp", title="Temperature")
    fig2.update_layout(yaxis=dict(range=[15, 30]))  # Set initial y-axis range
    st.plotly_chart(fig2, use_container_width=True)

with col3:
     fig3 = px.line(df, x="time", y="Nora/lightintensity", title="Photoresistor Reading (Light Intensity)")
     fig3.update_layout(yaxis=dict(range=[0, 5000]))  # Set initial y-axis range
     st.plotly_chart(fig3, use_container_width=True)

with col4:
    fig4 = px.line(df, x="time", y="Nora/moisture", title="Soil Moisture")
    fig4.update_layout(yaxis=dict(range=[30, 60]))  # Set initial y-axis range
    st.plotly_chart(fig4, use_container_width=True)
    
    
st.subheader("Control Panel :control_knobs:", divider="green")
# --- Button for LED ---
led_on = st.toggle("LED On/Off", value=False)
if led_on:
    client.publish("/LEDControl", payload="true", qos=2, retain=True)  # LED ON
    print("LED is ON")
else:
    client.publish("/LEDControl", payload="false", qos=2, retain=True)  # LED OFF
    print("LED is OFF")

# --- Button for Pump ---
pump_on, pump_off = st.columns(2)
with pump_on:
    if st.button("Pump ON"):
        client.publish("/PUMPControl", payload="true", qos=2, retain=True)  # Pump ON
        print("Pump is ON")
with pump_off:
    if st.button("Pump OFF"):
        client.publish("/PUMPControl", payload="false", qos=2, retain=True)  # Pump OFF
        print("Pump is OFF")

    
# --- Camera Control Buttons ---
col5, col6 = st.columns(2)
with col5:
    if st.button("Take Photo (No Flash)"):
        client.publish(MQTT_TOPIC_CAMERA1, payload="TAKE", qos=2)
        print("take photo no flash request")
        
with col6:
    if st.button("Take Photo (Flash)"):
      client.publish(MQTT_TOPIC_CAMERA2, payload="FLASH", qos=2)
      print("take photo with flash request")
      



# st.image("https://static.streamlit.io/examples/cat.jpg", width=300)

# --- Display Image ---
if binary_image_data_global is not None:
    st.image(binary_image_data_global, width=300)  # Display the image
else:
    st.write("No image available.")


footer_html = """
<div style="
    bottom: 0;
    width: 100%;
    background-color: #f9f9f9;
    text-align: center;
    padding: 10px 0;
    color: #333;
    font-size: 14px;
    box-shadow: 0px -1px 5px rgba(0, 0, 0, 0.1);
">
    <p style="margin: 0;">Developed by Nora Luo © 2024 ❤ </p>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)

# Custom CSS to change selectbox cursor
st.markdown("""
    <style>
        div[class="stSelectbox"] > div > div > div {
            cursor: pointer;
        }
    </style>
""", unsafe_allow_html=True)