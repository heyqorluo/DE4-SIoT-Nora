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
import paho.mqtt.client as mqtt
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
        
test_image = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00\x00\x00\x00\x00\x00\xff\xdb\x00C\x00\n\x07\x08\t\x08\x06\n\t\x08\t\x0b\x0b\n\x0c\x0f\x19\x10\x0f\x0e\x0e\x0f\x1f\x16\x17\x12\x19$ &&$ #"(-:1(+6+"#2D36;=@A@\'0GLF?K:?@>\xff\xdb\x00C\x01\x0b\x0b\x0b\x0f\r\x0f\x1d\x10\x10\x1d>)#)>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xc4\x00\x1f\x01\x00\x03\x01\x01\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x11\x00\x02\x01\x02\x04\x04\x03\x04\x07\x05\x04\x04\x00\x01\x02w\x00\x01\x02\x03\x11\x04\x05!1\x06\x12AQ\x07aq\x13"2\x81\x08\x14B\x91\xa1\xb1\xc1\t#3R\xf0\x15br\xd1\n\x16$4\xe1%\xf1\x17\x18\x19\x1a&\'()*56789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xc0\x00\x11\x08\x00\xf0\x01@\x03\x01!\x00\x02\x11\x01\x03\x11\x01\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\xf3\xb9\x141\xfb\xa2\xa3\xda\xbe\x9dhhc\xb6.x\x03\x14l\x07\xb6{\xd1+nQ&\xc4\xc60\x054 \xe9\x8a:\x00\xf0\x88\x13\x1bA\xf7\xefI\xb1\x07j\x9b\x086/\xa5\x1b\x13<-TF\xfc\x85(1\xd2\x8d\xab\x8cm\xa3\x956+\t\xb0\x7ftS\xc0\x1d\xd4Q("\xb9Cj\x7ftQ\xb1=\x05\rh+\t\xf8\x0f\xca\x97j\x9e\xd4\x9a[\x05\x84\xd8\xbe\x82\x8f-=(\xb4l;\x89\xb1@\x1cQ\xb5\x7f\xba)\x88\x8c\xc6\xbe\x94\xc2\x91\xf6^iX\x01"\xe2\x9d\xb1i\xd8\xae\xa2\xedQ\xfc4\x85FsG,Icv\x81AU\xfe\xed=\x045\x80\xf4\x14\x9b\x07\xa5-\x04\x01W\x1d\x054\xa8\xf4\xa6\x01\xb4zQ\x81G*\x016\x8d\xdc\nB\xa3\xae*P\x84\xda\xb4l\x06\x9d\xad\xa8\x17\t\xe7\xda\x9b\xfc\xa9\xeb\xd4{\x86sO?\x86(z\x0cg8\xa7\x03D{\x8cv(\xfa\xd3\xba\x15\x85\xc5-+\x8f\xd4\x1b\x8f\xad/ZW\x1f\x98w\xc0\r\xf9R\x91\xe9H\xd0\x93\xcb\xe2\x9b\xb4\xd0\xb5!\x89\xd4\xf3F1ORD\xa4\xce\x0fZ\x12\xb9b\xf5\xf44c\x8a\x13hCv\xd31N\xe2\xb0\x01K\xc5\x02HN\xd4\x874\xc0ozkT\xb0\xb7Q\x9di\xddh$Lz\xd3EU\xf4\x0b\x0e\xebI\xd3\xb5!\x85!\x1c\xd4\xf9\x0cJN\xf4\xf5D\xb2\xd3\x0c\xbeE0\xd5\xb7p\x18\xb9\xa92q\xd2\xa1j$;\x1c\xd0\xa8h\xd8\xa5\xb8\xf0\x86\x9e\x12\x9e\x85\x0e\xd9\xf9\xd2\x88\x9b4\xae\x16\r\x9e\xb4\xe0\x94\xd0Z\xe3\xd8\x00\xb4\x01\xc5$V\xc1\x9fZ\r\x1a #\xa6\xb8"\x99\x9fR/\xba03B\xab\x13MhR\x91ac\xf9z\xd1\xb3\x8aI\xdc`Wu3e\x16\x06!Ni\xa4qE\xc9\x1azSpqG0n3\xbd\x07\x9aW\x15\x84\x0bG4\xf4`\xc4\xc5\x18\xe2\x8d\x86\'j(\x13Li\xa4\xa5&\x02QOph\xb1\xf7[\x9a~}\xea\x89R\x13\x00\xb7o\xc6\x9e1Q\x18\xfb\xa5\xec;nz\xd2\x8e\xb4\x08v)\xc0\x1a\xa5\x15\xb1K\xc8_\xc4S\xb3E\x85\xa8\xbdi\xc3\xa5I\xa2\xd8^\xd8\xc6(\xdbH\x90\xdb\xc5.=\xa9\x95b\t\x17\x14\xe1\x10nMH\x92\xd4\x04\x0b\x9a\x93\xcbT^{SW\x0e]J\xc6\xe8g\x81H\xb7\x04\xfd\xef\xd2\xafd.\xa4\xbb\x83Tm\x8a\x9d\xc2\xe3\x0e)3R\xe2C\xd4\r7\xb5ZC\x10\xf4\xa6}(\xb8\nzRv\xa5\xd0k\xb8\x94\x94\xdcD%\'\x14\x00\x83\xde\x90\xd4\xda\xda\x89\x89M\xebM\x12\\\xdah\xe9\xd8f\xb4o\x9aC\x11P\x9fl{T\xb8*\xb4\xba\xe8\x08w$t\xe9N\xdaz\xe7\x15,\xbb\x0b\x8e\xd4\xf5\xc6(`\xb4$\xc2\xfaQ\x81\x9e\x94\xb5*\xe3\x85HzT\xc9\xea\x00\x06z\xd2\x93\x83T1;\xd0\xc7\x8aL\x06;/Zf\xf59\xa5p\x15O\xe5Une>f?\x86\x9c;\x85\xf4*g\'4\x8c\xdc\xd6\xd2d\x0f\x89\xaasY\xb0HkP;f\x90\xee8\xe2\x9b\xf5\xa2\xecHJnh\xb0\x86\xf5\xa6\xd0=\xb4\nJ\xae\x84\xd8L\xd3I4\xb5\x06%4\x9e\xf4\xb7\x18\x9e\xf4\x80\x9aV \xd0^i&\x1b\\/\xf1V\xa9\x8fa\xe83\x03\x93\xcd07\x15\x1b\xea)y\x0eV?\x85J\xa7\xd6\x8b\x02$\x18\xa5\x1bij]\xc1Kc\xad85;\x8c~{\xd2\xd01\xc0\x83K\xd4\xd4\xf5\x1e\xe1Ms\xc7\n*\xadvQ\x03\xa94,x\xe6\x9f\xc2C\x12V\xda>\xb5J^M.\x84\xbd\xc8\x93\xef\xd2\xcd\xc54\xc5q\x89\xd7\xda\xad\xe74\xad\xa9W\xee.9\xa6\xe2\x973\x0b\x87z)\xde\xe04\x9a)\x06\x83\x0fZm;\x08J(\r\xc6\x91IKQ\x06)1@n\x18\xa6\xe2\x82Y\xa2\x91\x1d\xfb\x80\xa5\x9dI\x97\xfaU\xdc\xa1\xf7\x03\xcb\xb5E\xc7\xe3T\xc6?:b\xbd\x89c\xe7\x8aG\x97h+\x8a\x8eQ\xb5\xd4H\xe5\xda\xdc\xf4\xabq\xb2\xc9\xca\x9c\xe6\x9d\xb5\x0b\x92\x81K\xb7m.\xb64\xbfQjP=\xbf*N\xc5h\x84\\\x1e\x875&8\xe9A1cv\xd1\xb6\x94\xa6h\x0c\x80.\xe3F\xde>^~\x94\xaf\xa0imL\xab\xa7\xff\x00I?\xec\xf1PLr\xa7\xd2\xb4H\xc1\xb1`\xc3)\xf5\xa6\xcc\xac\xc4\x0fJk\xe2\x021\xc3U\x84jl\x0b;>\\\xd4dV`\x1d\xa9(-\x89M4\x12&2)\x08\xe2\x95\xfa\x03\x12\x93\x8av\x10\x94\x94\n\xc2\x1aJ.\x03{\xd1H,k\xc2\x0eO\xf7jFQ\xe6oo\xe1\xabw\xb9ZlQ\xbem\xef\xeb\xfd*\x15\xfci\xb6\xd9\x99\'*=\xea\x17R\xc7#4\xd3\xd0\x18\xe2\x01\xeb\xfa\xd2`.0M-w\x02\xccw=7\x1e\xb5r3\xb8eh\xdfR\xd4\xc1\xa4\x08\xdc\x9ej\xb4\xb31\x1bT\x9c}j6cl\x823\xf3U\x88/\x1a9B\xb1fOJ\xbe[\xa1E\x9b)\x12\x14\x07\xd4T\x9eZc\xa0\xa8\xf25\xe6\xb8w\xa8o&\xf2m\x99\xf8\xcfc\xefIG]\x05\xa1\xcd\xb1\xeaz\x93Q\xe7"\xb42%\xb58\x93\x1e\xb5,\xb8\x02\xa7q\xdfB\x99\xeb\x9ax5kBK\xb06c\xdbN+\xc5OR\xf4\x18i\xa4sS\xd4\xae\x82RPH\x9fJi4u\x01)\xb4\x12\x84\xa6\x93@1\t\xa6\xd3\x15\xc4\xa4&\x90\xcd\xebY\x15\xd3`\xe3\x15jH\xc0\xb2\xdfM\xf6.\xc6$\x9f<\x87\xb7j\x96\xda5\xdcY\xfe\xe8\xf4\xa7\xa9\x95\xec@\xcc\xc5\xfaV\x95\xac1\xb6\x9e\xf22\xfc\xd94K\xb1I-\xca\x0e\x99\x035\x0b\x0c\x1aN\xe4\xb5\xad\x86\x0e*x\xe6e<U\xf4\x0b\x0e,Y\xea\x7f\x97\xca\xc8\xedY\x94B\xb1\x1f/\xde\xa0\' \xf3N\r\xb4\'\xa34\xb4\x9b\xff\x00-\xfc\x99?\xd5\xb1\xfb\xd9\xe9[\xc7\x9f\xa7\xad\x1b2\xe21\x87\xa5ckRfe\x8b\xd0n\xa1h\xc7-\x8c\xbcTG \xd5st3$N\x18\x11K<\x99\xe9J\xcd\x8f\xa1\x08\xce3GZ5\x06O\x1bc\xa5Y\xe0\xaehlhL\xd2g\x9aZ\x95k\x8c8\xa0\xd0\xae\x0cfi\x0fZ:\x93q\xb9\xa4\'\x8e)\t\x8d\xcd6\x81[Q8\xa6\x9e\xb5C\xb0w\xa6\x9aN\xe4\x9a\x16\xeeb\x9c6zV\xdd\xf4\xe8-#\x8f\xfb\xc7uT\xd6\xb7/\xd4\xc8\x91\x90\xbe\xe5\x14\x9b\xca\xc7\xb3\xf5\xa4\x88#\xab)rE\xb7\x90\xa7\x14i\xd0h\x8b\x9d\xdc\xd2\xf9y\xa9\xb8\xb7\x18\xf1\xd3#M\x86\xa96U\xc7\x87]\xc0~\xb5f=\x9b\x1b\x12\xaa\xfb\x1a\x87p\xdc\xae.w#\x0e\xe2\xab\xd6\xb1\xd0\x96\x81>\xf2\x9fz\xe84\x8b\xdd\xff\x00\xe8\xd2\x1f\xf7\rD\x87\x13E\xab\x9d\xd7\xbeMB#\xfd\xe8\xbf\xad;\xeak.\xc5.\xb5\x19\xe6\x84d\x03\xadM\xb0qM\x82C_\x81P\x1a\x94\xc3q\xe9WW\xfdU6;\x0c\xcd4\x93Qr\xc44\x87\x9a\xb4K\x1b\xda\x9b\xce:\xd2b\xb0\x94\x9bq@\x08G\xbd4\xd1\xb8=\xc4\xc5%\x00\'jN\xb4\x08\xd8x\x07<~U\x0c\x92n\x035Nz\x89"<q\xc5!q\xd2\x90XN\xa6\xa5U\xf5\xa6\xde\x83\xb1(O\x97\xad8/\xfbb\xa3\x9bA\xebaO\x97\xfd\xec\xd2\xfd\x9c\xb8\xc8\xa7\x114F\xd6;\xbbsU\x9e\x07\x8f\x8e\x7f*\\\xcf\x9a\xc2!\xefR\x15\x1e^i\xc7b\xba\x11\x8e\x95<\x13y\x12\xc5\'\xf7\x1c\x1e*\xdd\x86\xb4:\xd9W\xf8\x87B2>\x95\xcc\xebM\x9d@\x8ctQP\xb5)\x94Q\xbbS\xc8\xa7k\x104|\xaf\xcdX\xedL\n\x93>\xe6\xe2\xa3\xa4\x04\x8b\xd6\xb4m\xc00>jo`\x1aEG\xcf\xb5\x05\x89I\xd6\xab\xa0\x84=*\xaa\x9c\x9a\x9dDM\x9ae4!)\xb4u\x01)\r\x004\xd2R\xeb\xa9,\xdd\xdf\x80U\xbb\xd4\x12.\xe6\xc2\x03\x9a\x13ccZ2\xa8FN\xea\xaa\xdd\xf7\n\x13\xb9;\x8a\x0f4\x19\t\xe4\x1a\xb6\xc6\xf4,Cr\xbbv\xb7\x07\xb5;\x1b\x86s\x9aK@$\x8e!\xebZ1aWo\x15;\x9a\x13\r\x8c0\xbbI\xa8\xe4\x81\x1dM-\x85k\x99wVE\x03<|\xf7\xc5R\x1f9\x02\xaa\xfa\n\xce\xc2>\x01\xc5\x00o\xaa%\xdc\xe9t)D\x9ar\xc0_\xe6\x8c\xed\xdb\xedX\x17\xecZ\xfe\xe3?\xf3\xd0\x8aW/VT\xe752\xf2)\xa2^\xc2\xe3\xbd6G\xda0(\xb8-\n\xf4\xecP\x83TH*\xe4LD\x04s\xcd\x1d\x06\x90\xda\x19\x80\x19\xa8l\xad\x8a\xed/\xa5G\xbd\x8fJ,H\x85\x9b\x18\xcdE\xc09&\xa8[\x8e\xf3\xfbT\x99\xe2\x98\xc4&\x9b\x9a\x96\x02\x13M\xefA;\x01\xa34\x01\xae\x81\x9cU\xcb8\x0b\x16\xcf\x1cu\xa1\xadB\xe2O\x02F\xff\x003\x13Y\xac\xa1\xfeo\xe1\xa0\x15\xde\x84~_\xc9\xf3\x0e\x0fj\x8c\xf3\xf5\xa7\xcbpCrA\xabQ\xcb\x81R\xf4\x02U\x94v5c\xce\x19\xe2\xac\xb4(\xba\x0b\xf7q\xf9SZ\xf9\xf0@\x1f\x8dg`\x12\x0b\x87\xfbB\xe4\xf1\x9a\xb3=\x98\x92A S\xba\x96\xccH\xc8\x9e7\x8eC\xbdH\xf4\xe2\x84\xab\xdc\x0b\x96m\xf6y\x04\xab\xc1\x15WQ\xff\x00\x90\x94\xc4c\x07\x07\x8f\xa5>P+R\xa1\xc3`\x9a<\x82\xe4\xc6\x8d\x99\xedC\x8e\x805\xa3\x1dj\x02\xde\x94DM\x8b\x17-Z/\xf2B\xab\xd6\x87\xa9h\xae\xec\x00\xa8\x8c\x99Z\x92Y\x1e@\xa6\x19\xbd\x05\x0b\xb8\xaeD[4\xcc\xd5n!\xcaj\\\xd2\x18\x99\xa2\x80\x12\x92\x95\xc4\xc4\xcd!\xa7\xd4gI\x01F\x15:0I\xbd\xc8\xa1\xab\x8e\xf6)\xde\xcaL\x9bV\xab\x0e\x9c\xe7\x14\xd2ar\x07}\xd4\x83\xa1\xa3Rc\xb8\xa4\x02\x057\x18\xa2CcO#\x8e\xb4\x80\xba\xd2\xd5\xe8!|\xf6\xa7\xa4\xb4\xf9m\xb9E\x98H\xc8\xad\x18f\xd9\xcb1\xa9~C\xb8\xe6\x02\xe3\x97\xce\xca\xa5-\xae\xcc\x95\xe4f\x92\xbac\xb6\xa5\x19_\x1cS&\x94\xcc\xfea\xe34\xec\xeeg\xb0\xde);\x03\xd2\xb4\xb8\xcb\x03\xe6\\\xd0d\xc0\xa4V\xe5w\x90\x93L\xa4A$y\xdd\x90*\xe3H\r\x99\xf5\x06\x85\x1b\x8dlPix\xa8\x8b\xfaS\x16\xe2\x12Z\x9b\x8a\x940\xa4\xa7\xe6!\x01\xa9\xc1\xe2\x86=\xc2\x8a\x00F\xa6\xf4\xa0aI\xd2\x95\x895b\x90\xa3\n\xba\xed\xbba^\xbc\xd6\x96\xb0\xeeC\x8ey\xaa\xd3\xb7l\xf1U\xe84W\x14\x8b\xf3\x1a\x8b\x82%c\xcd\'\xde\xa6\xc9\xdc\x97`\xa8G\xcc\xe4Qb\xb6\x06JS\x11\xc7\x14\xde\xa3\xd5\x8c\xcb\xaeq\x9a\x90\\\x11\xd75\x9d\x84N\xb7\xc5V\x93\xfbE\xb6\xe3\xbd;\x0e\xe5ga%F=(\'q\x07Z\x90S\xdc\x07\xc6qJV\x90\xc6\x15\x1dj*"K\'\x80\x8c\xf3O\x96=\xd1\x1f,f\x97\x99]\x0c\xef\xe2\xa5\xa6\xde\xb7&\xc3\xc4Y\xebRm\xe2\xa6\xe8\x19[\xbd\x06\xa8\x04\xa7\x8aC\n}\x00%\x15=A\x8d\xa44\x07\x91\xaf$|\xf1O\x8f\xe5\xdb\x9c\xe2\xb5r\xe6\x05\xe4,\xac*\x84\x874\x83f3>\xd4\xff\x00\xba\xb5Z\x14\x1c\xff\x00\xf5\xe9\xa1\xb9\xe2\x8e\xba\t\xdba\xf9\xe6\x9d\x17\x0eqI\xea\x04\xa5i\xed\xf7joq\x90\x9e9\xa8\xc2\xee5q\xd0Do\xf2\xd4U,\x96\x02\x9f\x91RRz\x08}\xe9\xf1\xb78\xaaC\xeaIJ[h\xcd\x02!2qQ\xe6\xa4C\x91\xaa\xdc\x13\x94\xa0\ns\x7f\xad5\x18\xa4;\x96S\xa6(\x98\xed\x18\xa5q\x15\xb1Hz\xd3\xdcB\x8aL\x9c\xd5\xad\x86\'5*&\xe3HC\xe6M\xa3\x8e\x95\x0141\x8d\xddFh\x11\xb2\xa7\x1cQ\xe9J(\xb5\xb9\x14\xef\xf2\xe2\xaa\xf7\xabh\x99!\xd4\xea\x86;\\e7\xa1\xa6\x99,\x94d\xaf\xbdI\x06K\n\xad\xc6\x91h\xaf\x14\xd7\xf9GZE\x15\xb6\x92}\xaaH\xc56\t\x15\xe4\xfb\xd9\xa8x=*7\x15\x872\xf1\x9ah\xe6\x89+jKC\xbbsM\x14G\xb0\xf5D\xd9\xcfJa_SN\xc3#\xd9\x8fZ*w$*D\xa646_\xbdM\x8f\xa5J\x18\xa8\xc5\r1\x8e\xf6\xcdP\xc6\x9aP)\xd8\x96\x05\xb8\xa8\xe9t\x01\xdd)\xeb&\x16\xa4Lc\xcc\xed\xc1n=)\xb8\xa7\xe60\xc5%\'\xaa\x0eShR\xe6\xa9\xbb\x14U*\xccri\xa16\x9eE]\xee-\xc0\x9ex\xa4\xe7\xd6\xa0HCB\x8c\xff\x00\r\x17\xb8\x96\xe5\x88\xc6EI\x08\xc4\xb8=)\xea=\x8bO\xd6\xa0\xf2\xd9\x9b\xe6\xa5}K\xb8\xd9@N)m\xb6\xa9\xcf\xad\x0fRw)\xcep\xe5j\x1fz4@\x89S\x91\x8aC\x90x\xa3}\x01\x8c4\x0cz\xd1k\x05\xae?\xa0\xa5\xdd\xc50c\x1b\x9a\x8c\xd4\x88)\xc8\xd8j{\xa0\tz\xd4`\xd2\x01\r.8\xa60\x14\xc3L\x90\x1c\xd2\x8a\x90C^\x81\xcd\x03\x17n(\xa4\xb7\x00\xa3\x14[\xa0\x8b\xf11\x1c\x1a\x9c\xfc\xc9\xe9[2\xfe\xc89\xe3;\xb7{\xe3\x15\x031=:T\x88c\xf1H\xbc\x8e\x94\x87\xa0P3\x9e(!\x96\xa3\xa9;\xd3\x198\xf5\xa3q\xc1\x15>E\x15\xa7?6\x0fZ\x8c\x1ah\x92\xb4\xff\x004\x9c\xd3\x14\xf64\n\xc3\xd4\x95\x7fj\x90\x9a\n#\xc7\xe0*59\xa4!wq@5+`\x13u6\xa8\x02\x8ahB7"\x92\xa7\xa9B\x8eM\x06\x9ab\xb0R\x1a\xa6\xc4\'\xdd\x14\xd2\xf56\xb8\x02\r\xc7\x15k`QR\x04\x07\xad6\xa8\x18f\x92\x98\x17O\xca7b\xa7G;0\xc3\x9a\xa2\xba\x0f\xc8 g\x8a\xad#\xf3\xc5M\x82\xe3;Rg\xd2\x92B\xe6C\x85(\xe1\x85;\x0e\xc5\xc1\xd4T\xbc\x1a\x8dGaI\x0bP\xb4\xfe\x95j=F\xfb\x90\x13\x9a^\xdc\x8aFw\xd4\xaa\xc7-Q\xf7\xa0.L9\x14\x9f\xc5\x81C*\xe28\xc0\xc9\xa6RA\xd0O\xe1\xa2\x91"Rf\xae\xc3\x14\xfd\xeaz\xe2\xa4\x067^))\\C\xbaS7z\xd5\x0c\x0bRg\x9a\x00kRv\xa6$M\x07\x075,\x8d\x93I\x0c\x80\xb74\xdaB\x12\x8aa\xd4\xd4\xf2\x1b \xd3B\x1d\xb8#\x9a#"\xb6\x15\x8e"\xaa\xa7\x9eh\xb7\xbdrF\xb0\xd8I\xefN?.}\xa8\x02D\x1c\xf4\xa9\r\x03\xb9a9QNg\xc0\xcd%k\x8c\x84\x97sI\xe5\x9c\xf1L.\x05v\x1e\xb5:\xae\xe8\xe9\xd8:\x19\xd2\x82\x1c\xf1Q\xf7\xa5\x12v\x1d\xf4\xa1heXN3M\x02\x90\x87\x01\xcd4\x8f\x9a\x80\x12\x9b\xde\x98\x0e\xa5\xce\x05 \xbe\x83i\xdd\xe9\x8d\x0bL\xc5\x17\x10\x94\xee\x05!!\x94\xd3T\x04\x89\xf7iX\xd2\x1d\xc6SjD\x1d)j\x81\x1b\x1eg&\x81\xfb\xcf\xc2\x9e\xda\x94B\xe8MG\xb7\x14GT+\x91\x9fz\t\xa2\xc1}\x07\xc5\xd6\xaccp\xc5=\x90\xb9\xba\x8eF\xe2\xa5\xedJ\xc5n7!zS\x1e^8\xa4"\xbe\xe3\x9ey\xab\t6\x17\x15Z\x0c\xab?\xcf#\xe3\xd6\xa2\t\xcdO(\x12\xc3!\xb7\xdd\xb1\xd5\x87C\x8e\xf4\x9f#r\xbf\xbb\xf6\xa5k\x01\x10\\\x9aF4\x85q7b\x9cy\\\xd5XDf\x9b@\xfa\x0bGU\xa0B\xafNi\xf4\x00\xdcR\xf45<\xa3cY\xb1\xd2\xa2\'u;\n\xe2\x8a1\x93T\xf6\x0b\x93\x0e*7\xebR\x17\x1bIN\xc8\x05\xcd(\xa9\x19\xa4O\xcf\xc8\xa7\xa3b\xb6b\xd4\x95\x9b\x1f\x8dA!^\xdf\xa5Dt,\xae\xc9\xc6EGJ:\xe8M\x87\x8e\x99\xc5YC\xde\xaf\x94:\n9j\x18\x9c\xfbT\xfa\x00g\xd6\xa3%{R\x18\x94\x87\xa7\x14\x95\x84F\x1b\x06\x9d\xe6`\xe4U\x0e\xe2\xf9\x88\xddc\x0b\xf4\xa7<\x7f6\xd0F\x05H\xc8\x18\x15\xfaSi1\x11\xd3\xf7b\xa9\x12\x869\xe6\x9a)\xb6\x0cRi3H\x07R\xe6\x92W\x00\xcd6\x80\x1bM\xa6 \xcd>.Z\x98\x139\xe2\xa1nil\xc66\x8a@\xf5\x14S\x96\x80\xb9\xa5/\x06\xa1\xe8\xc4\x85\xc7\xaf\xbdT\xb7(]\xd9\x14\xdei\xeeH\nk/9\xa5\xe6\x86/QNSHH~\xfct\xa6\x99*\x8a\x18\\\xb5 \xa5\xe4\x03\xb3\x9e\xf4\x13\x9c\xd1a\x11S\xd7\xad&!\xa6\x93u\x16C\xea7\x93\xc6i*X\xafq\x84\xe2\x9d\xda\xa9X\x06\x9e\xb4\x94\x80\r\x03\xadP\x0f\xa2\x95\xfa\x00\x8c1L\xa0\x04\xa0\xd1\xd0\x06\xe2\xa5\x83\xefQp\x1d)\xf9\xaa*W\xd4\x04\xe9I\xf5\xaa\x1ac\xc7Z~*@\xd0\x9b\xeff\x98\x06\xee}\xaa\xbdD\n)\x18R\x1bBs\xb6\x85\xe7\xb5=\x84F\xdf+QLc\xf7b\x8d\xd5zt\r\x84\xa6\xd6m\xdf@\x1c\x94\xe0\x06h\xd4\x18\xccPh\xea!\x07CG\x96M\x17\x00\x10?R(0\xd4\xf3\x0cO.\x98R\x95\xc4\x1e]5\x86\r4\x04t)\xe6\x98\x13\nL\x8a\x90#c\x9ae;\x80Q\x9a\x18\x05\x08\xdbM1\nNM\x02\x81\x88\xd4\x86\x95\xc0uI\xd6\x8d\xc0\xd0\x9f%\xf1O\x8d02j\x9e\x9a\x03z\x8d\x8f\x8d\xf5\x19\xe0\xd1p\xd8\t\xf9zP\x87\xb6i\x14,\x98d\xc5V\xefGBA\x8f\xbd&M\x08,.h\xedU\xa0\x12\'JvsSq\xdbA1E;\x80\xe5\xc5L*\x06I\xde\x9a\xcbHEy\x0539\xf5\xaa[\x00\x86\xa2\x97\xa54-H)TR\x00\xcd%&\xb5\x18PE=\xc01I\x8av\x10b\x92\x93\x01h\xa4\x16\nC@\n)\xd4\xf4\x03[nd\xa9[\x85\'\xda\xab[\x81\n\xf4\xa8\\\xfe\xf0\xe2\x97P\x1b\xd6\x93\x9c\xd5\\\x034\xc9=h\xb8\x0c\xc7z)\x00\x94\xb9\xc5!\x92\xc6r\xb4\xee\x94\xee \xa2\x81\x8fU\xf5\xa9\xc6\x00\xa1\x80\xea$\x1d\xc5H2\xb99\x1c\xd4t\xd8\r\xa8\xe4\xe9HD&\x8a\x18\x82\x90\n\x07a\xe1M\x18\xaa\xd8cZ\x9bLW\x10\xd2T\xb0\xe8 \xa5\xa0\x10QE\x82\xc2\xd2\xe6\x90\x1bKD\x8d\xfa\xd6\xa5=\xc6\xafO\xa5V\x7f\xbfY\xb2n\'\xf0\xd2c\x8ahbQG\xa8\x11g\x9a\r\x16\x13\xee6\x974\xb9D86*U}\xc6\x90\xd3\x1c\xddh\x1d*\xfa\x00\xb94\xf4\x1b\x8d\'.\x81b\xc51\x9b\x1cR\xd8d.9\xa8\x8f\xa51\\J\x85\xcei\x00\xd3M\xaa@-/\x15 .\xee)\x87\xad1\xb1\t\xa4\xa0I\r\xebEK`6\x96\x98u\n(\x0b\x8bKI\x01\xb3\x9f\x9b\xa9\xa3\xadS\xd0\x18tJ\xa8NjF\x89\x1dv\xd3X\xd2\x11\x1fnh\xad\x8bB2\xe0\xd4mY\x926\x90}i\xdc\x91\xd4\xee\x9d)\x0c\x90=H\r>\x9a\x8d\x89OS\x81S\xd4c\xe3b\xc6\xa5nE>\xa0Wn)\x95Z2H\xd8\xd4T\x00\x86\x92\x8d\xb4\x18\xa74\xda\x8e\xa2\x1c)\rP\xc6RR`\x82\x93\x14\x98\x98\xda(\x10\xb4\x94\x0c\\\xd2\x8a,\x176\xb8\xedM\x04U=\x06$\xa7\xe4\xa8\x80\xa9z\x89\xb1\xc7\x9a\x8d\xcf\xcdT\x80\x8e\x8a\xab\x83\xd0Bri\x8dQ\xa8\x86\xd2\x9av\xd4aIM\x85\x80T\xaa\xdc\xd2\xf2\x04\x89\xb23F\xde\xd4\xb6\xd0{\x0f\x8f\x83J\xcdT+\x91\x13M\xcf\xad.Q\x91\x13M\xa4\xb4\x10\xda*\x98\x0b\x9aJ\x92\x85\xa44\x127\xbd.*\xac\x02RR\x042\x8a@6\x8aB\x16\x94P3\xff\xd9\x00\x00\x00\x00\x00\x15\xf7{Q\x16\x16\x1d\xde\x94Sa\xa0\xb94\xf8\xf71\xa42\xc6\xdc/\x14\xd2\xdcsL\x1a\xb9^D\x18\xe2\xa1\xa5\xe4$\x80\xd4\r\xd6\x8dF!\x14\xda\x04\x02\x9d\xf4\xa0\x05\xdd\xc57\x9am\x8d\x8d\xa6\xd2\xb9!M\xa3q\xb04T\xb1\x05-P\x05;5-\xd8h\xda\xce\x0fZ\rU\xb5\x06&v\xa5T \xb1\xa7$\x17\x1e\xcb\xb0\x01\xebH\xc7\x03\x0b\x8av\xd0w\x19\xba\x93\xebP\x17#a\x8aBx\xab\x13#\x14\xb8\xa4\xc4-8\x1c\x1a@H\x1e\xa4\xedC\xd4hn\xda\x99$\xda:\xd5\x14=\\\x96\xc5H\xc3rT\x81X\xf0pi\x86\x81\\k\x1cT\x07\xefR\xf3\x01))\x80Rv\xc5\x00?\x8aL\xd3\xb5\xc6Fi)2XRR\x01\r%!1i)\x8e\xc2\xd1I\xcb\xa8\x1b\x84d\xf1I\x90*\xdb\xe81$\x7f\x96\xab\xa04\xee\xafa!\xff\x00x\xd3\x1f\xad&\x1eDTQpB\x1e\xd4\xc69=\xa9\xde\xe0\xc6\xf7\xa5\xa9\x12\xd4Ze(\xb1\xd8Q\xd2\xa5F\xa6\x83\xa90\xf6\xa5\xe6\x80$\x8c\xe0\xd2\xe7\x93\x8a"2&\xe4\xe6\xa3\xfa\xd2\x0e\xb7!c\x93M\xaa\x10\x98\xa5\xedF\xe0\xc2\x92\xa4\x05\xa4\xaa\x01\xb4\xb8\xa2\xc3\x13\xd6\x90\xd2hV\x19\x8aJ\x00(\xa0\x05\xa2\xa4\x0f\xff\xd9\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x14\xc0\xde\xf5\xa6w\xc5k\xa1lI\x9f\t\xedP \xefRH\xe6\xfb\xd5\x13\xf2i\xd9\xd8.G\xfc\xe8\xcd!0c\xc75\x1bT\xc4\x1e\xc39\xf4\xa5\x1c\xd51t\x1dI\x9a\xce\xc3\xb0g&\xa5\x8d\xb6\xf1W\xa5\xac>\x84\xd9\xa7S\x04>"\x14\xf3N2zS\x1d\xc8Y\xb9\xa8\xf3KBR!bM%.\xa3\x12\x92\x81\x05%P\n)\r\x007\x04\xd2\xed\xa4\x01M4\x00\xd3M\xa8\x10QL\x10w\xa7f\x9a\x19\xff\xd9'
with col6:
    if st.button("Take Photo (Flash)"):
      client.publish(MQTT_TOPIC_CAMERA2, payload="FLASH", qos=2)
      st.image(test_image)
      print("take photo with flash request")
      



# st.image("https://static.streamlit.io/examples/cat.jpg", width=300)

# --- Display Image ---
# if binary_image_data_global is not None:
#     st.image(binary_image_data_global, width=300)  # Display the image
# else:
#     st.write("No image available.")


footer_html = """<div style='text-align: center;'>
  <p>Developed by Nora Luo @2024 </p>
</div>"""
st.markdown(footer_html, unsafe_allow_html=True)

# Custom CSS to change selectbox cursor
st.markdown("""
    <style>
        div[class="stSelectbox"] > div > div > div {
            cursor: pointer;
        }
    </style>
""", unsafe_allow_html=True)