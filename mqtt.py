import json
import time
import paho.mqtt.client as mqtt
from config import config

broker_address = config["mqtt"]["broker_address"]
port = config["mqtt"]["port"]
topic = config["mqtt"]["topic"]
username = config["mqtt"]["username"]

client = mqtt.Client()
client.username_pw_set(username)
client.connect(broker_address, port=port)


def publish_message(data):
    json_data = json.dumps(data)
    client.publish(topic, json_data)


def mqtt_publisher():
    while True:
        # Bu kısımda MQTT için gerekli olan verileri alın ve publish_message fonksiyonu ile gönderin
        time.sleep(1)
