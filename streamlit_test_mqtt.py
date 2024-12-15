import time
import paho.mqtt.client as paho
from paho import mqtt
import json

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
    try:
        # Attempt to decode JSON payload
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"Received message on topic {msg.topic}: {payload}")
    except json.JSONDecodeError:
        # Handle raw boolean or string payloads
        payload = msg.payload.decode("utf-8")
        if payload.lower() == "true":
            print(f"Received message on topic {msg.topic}: True")
        elif payload.lower() == "false":
            print(f"Received message on topic {msg.topic}: False")
        else:
            print(f"Error decoding message: {msg.payload}")

# Client setup
client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
client.on_connect = on_connect
client.on_subscribe = on_subscribe
client.on_message = on_message
client.on_publish = on_publish

client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLSv1_2)
client.username_pw_set("noraluo", "Nora123456")
client.connect("beb8fb0b8c314776bf8d0bcc647382b5.s1.eu.hivemq.cloud", 8883)

# Subscribe to the topic
client.subscribe("/LEDControl", qos=2)

# Start the MQTT loop in a separate thread
client.loop_start()

try:
    # Toggle LED on and off every 5 seconds
    while True:
        client.publish("/LEDControl", payload="true", qos=2, retain=True)  # LED ON
        print("LED is ON")
        time.sleep(5)  # Wait for 5 seconds
        client.publish("/LEDControl", payload="false", qos=2, retain=True)  # LED OFF
        print("LED is OFF")
        time.sleep(5)  # Wait for 5 seconds
except KeyboardInterrupt:
    print("Disconnecting from broker...")
    client.loop_stop()
    client.disconnect()
    print("Exiting program.")
