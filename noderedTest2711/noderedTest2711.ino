#include <Arduino.h>
#include <WiFi.h>  
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include "DHT.h"

/* Digital pin connected to the DHT sensor */
#define DHT_PIN       4

/* I'm using DHT22, if you use DHT11 you can change DHT22 to DHT11 */
#define DHT_TYPE      DHT11

// Define LED pin
#define LedPin      23    

// Define Relay pin
#define RELAY_PIN  2


//define light intensity pin
const int lightsensor = 34;

const int sensor_pin = 35;  /* Soil moisture sensor O/P pin */

long lastMsg = 0;
char msg[50];
int value = 0;

DHT dht(DHT_PIN, DHT_TYPE);

const char* ssid = "Three_E17DD5";                        /* Your Wifi SSID */
const char* password = "4rEr45442x26376";                /* Your Wifi Password */
//const char* mqtt_server = "jroqth.stackhero-network.com";   /* Mosquitto Server URL */
// const char* mqtt_server = "broker.hivemq.com";   /* Mosquitto Server URL */
const char* mqtt_server = "beb8fb0b8c314776bf8d0bcc647382b5.s1.eu.hivemq.cloud";   /* Mosquitto Server URL */
const char* mqtt_username = "noraluo";
const char* mqtt_password = "Nora123456";
const int mqtt_port = 8883;

WiFiClientSecure espClient;  
// WiFiClient espClient;
PubSubClient client(espClient);

float humidity;
float temperature;
int lightintensity; 
int moisture, sensor_analog;



void setup_wifi()
{ 
    delay(10);
    Serial.println();
    Serial.print("Connecting to ");
    Serial.print(ssid);
    WiFi.begin(ssid, password);

    while(WiFi.status() != WL_CONNECTED) 
    { 
        delay(500);
        Serial.print(".");
    }

    Serial.println("");
    Serial.println("WiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
}


// void callback(char* topic, byte* payload, unsigned int length) 
// { 
//     char msg = 0;
//     Serial.print("Message arrived [");
//     Serial.print(topic);
//     Serial.print("]: ");

//     for(int i = 0 ; i < length; i++){ msg = (char)payload[i]; }
//     Serial.println(msg);
    
//     if (String(topic) == "/LEDControl") {//Check if the MQTT message matches the subscription
//     Serial.print("Changing output to ");
//     if('1' == msg){//if the message is "true", switch on
//       Serial.println("on");
//       digitalWrite(LedPin, HIGH);
//     }
//     else if('2' == msg){//if the message is "false", switch off
//       Serial.println("off");
//       digitalWrite(LedPin, LOW);
//     }
//   }  // You can add more "if" statements behind this to control more GPIOs with MQTT
// }

void callback(char* topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messageTemp;
  
  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    messageTemp += (char)message[i];
  }
  Serial.println();

  if (String(topic) == "/LEDControl") {//Check if the MQTT message matches the subscription, if add more ESP32 change topic esp32 to for instance esp33
    Serial.print("Changing output to ");
    if(messageTemp == "true"){//if the message is "true", switch on
      Serial.println("on");
      digitalWrite(LedPin, HIGH);
    }
    else if(messageTemp == "false"){//if the message is "false", switch off
      Serial.println("off");
      digitalWrite(LedPin, LOW);
    }
  }  // You can add more "if" statements behind this to control more GPIOs with MQTT
  if (String(topic)=="/PUMPControl"){
    Serial.print("Pump State Change to ");
    if(messageTemp == "true"){//if the message is "true", switch on
      Serial.println("on");
      digitalWrite(RELAY_PIN, HIGH);
      delay(3000);
      digitalWrite(RELAY_PIN, LOW);
    }
    else if(messageTemp == "false"){//if the message is "false", switch off
      Serial.println("off");
      digitalWrite(RELAY_PIN, LOW);
    }
  }
  //   if (String(topic) == "Nora/lightintensity") {//Check if the MQTT message matches the subscription, if add more ESP32 change topic esp32 to for instance esp33
  //   Serial.print("Light turn");
  //   if(messageTemp.toInt() >= 1000){//if the message is "true", switch on
  //     Serial.println("on");
  //     digitalWrite(LedPin, HIGH);
  //   }
  //   else if(messageTemp.toInt() <= 1000){//if the message is "false", switch off
  //     Serial.println("off");
  //     digitalWrite(LedPin, LOW);
  //   }
  // } 
}



void reconnect() 
{ 
    while(!client.connected()) 
    {
        Serial.println("Attempting MQTT connection...");
        

        if(client.connect("ESPClient", mqtt_username, mqtt_password)) 
        {
            Serial.println("Connected");
            client.subscribe("Nora/DHT/Humidity");
            client.subscribe("Nora/DHT/Temp");
            client.subscribe("Nora/lightintensity");
            client.subscribe("/LEDControl");
            client.subscribe("/PUMPControl");
        } 
        else 
        {
            Serial.print("Failed, rc=");
            Serial.print(client.state());
            Serial.println("try again in 5 seconds");
            delay(5000);
        }
    }
}

void setup()
{
    Serial.begin(115200);
    setup_wifi(); 
    espClient.setInsecure();
    client.setServer(mqtt_server, mqtt_port);
    dht.begin();
    client.setCallback(callback);
    pinMode(LedPin, OUTPUT);
    pinMode(RELAY_PIN, OUTPUT);

}

void loop()
{
    if(!client.connected()) { reconnect(); }
    client.loop();

    long now = millis();
    if (now - lastMsg > 300000) {
      lastMsg = now;
    humidity = dht.readHumidity();
    temperature = dht.readTemperature();
    lightintensity = analogRead(lightsensor);
    sensor_analog = analogRead(sensor_pin);
    moisture = ( 100 - ( (sensor_analog/4095.00) * 100 ) );
    
    char h[3] = {0};
    char t[3] = {0};
    char l[10] = {0};
    char m[3] ={0};

    h[0] = (uint8_t)humidity / 10 + '0';
    h[1] += (uint8_t)humidity % 10 + '0';
    t[0] += (uint8_t)temperature / 10 + '0';
    t[1] += (uint8_t)temperature % 10 + '0';

  snprintf(l, sizeof(l), "%d", lightintensity);
  snprintf(m, sizeof(l), "%d", moisture);

    /* Sending Data to Node-Red */
    client.publish("Nora/DHT/Humidity", h, false);
    client.publish("Nora/DHT/Temp", t, false); 
    client.publish("Nora/lightintensity", l, false); 
    client.publish("Nora/moisture", m, false); 

    Serial.print("Humidity: ");
    Serial.print(humidity);
    Serial.print("% - Temperature: ");
    Serial.print(temperature);
    Serial.print("°C");
    Serial.print("- Light Intensity: ");
    Serial.println(lightintensity);
    // Serial.println(h);
    Serial.print("Moisture = ");
    Serial.print(moisture);  /* Print Temperature on the serial window */
    Serial.println("%");

    delay(100);
    }
}