import json
import time
import paho.mqtt.client as mqtt
import yaml
from queue import Empty
from datetime import datetime


def read_config(file_path):
    with open(file_path, 'r') as config_file:
        config_data = yaml.safe_load(config_file)
    return config_data


config = read_config("config.yaml")

broker_address = config["mqtt"]["broker_address"]
port = config["mqtt"]["port"]
topic = config["mqtt"]["topic"]
username = config["mqtt"]["username"]

client = mqtt.Client()
client.username_pw_set(username, password=None)
client.connect(broker_address, port=port)


# Tüm timestamp formatlarını işleyebilmek için bir yardımcı fonksiyon
def parse_timestamp(timestamp):
    formats = [
        '%Y-%m-%d %H:%M:%S.%f',  # Örnek format: 2024-09-20 12:34:56.123
        '%Y-%m-%d %H:%M:%S',  # Örnek format: 2024-09-20 12:34:56
        '%d/%m/%Y %H:%M',  # Örnek format: 20/09/2024 12:34
        '%m-%d-%Y %H:%M:%S',  # Örnek format: 09-20-2024 12:34:56
        '%Y-%m-%d',  # Örnek format: 2024-09-20
        '%d/%m/%Y',  # Örnek format: 20/09/2024
    ]

    # Eğer Unix Time ise:
    try:
        # Unix time milisaniye cinsinden olabilir, bunu kontrol ediyoruz
        if len(str(timestamp)) == 13:  # Milisaniye cinsinden Unix time
            return int(timestamp)
        elif len(str(timestamp)) == 10:  # Saniye cinsinden Unix time
            return int(timestamp) * 1000
    except ValueError:
        pass

    # Eğer timestamp standart tarih formatlarında ise:
    for fmt in formats:
        try:
            return int(datetime.strptime(timestamp, fmt).timestamp() * 1000)  # Milisaniye cinsinden timestamp
        except ValueError:
            continue

    # ISO 8601 formatlarını kontrol et (UTC Zaman damgalarını)
    try:
        return int(datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp() * 1000)
    except ValueError:
        raise ValueError(f"Unsupported timestamp format: {timestamp}")


def publish_message(data):
    json_data = json.dumps(data)
    client.publish(topic, json_data)


def mqtt_publisher(data_queue):
    while True:
        try:
            data = data_queue.get(timeout=1)  # Kuyruktan veri al, 1 saniye içinde veri gelmezse exception fırlat

            # Eğer data'da timestamp varsa onu işle, yoksa anlık timestamp ekle
            if 'ts' in data:
                try:
                    timestamp = parse_timestamp(data['ts'])
                except ValueError as e:
                    # print(f"Error parsing timestamp: {e}")
                    continue
            else:
                # Milisaniye hassasiyetinde timestamp ekle
                timestamp = int(datetime.now().timestamp() * 1000)

            data['ts'] = timestamp  # Timestamp'i milisaniye cinsinden ekle
            telemetry_data = {
                'ts': timestamp,
                'values': data
            }

            publish_message(telemetry_data)
            data_queue.task_done()  # Kuyruktan alınan verinin işlendiğini belirt
        except Empty:
            pass
        time.sleep(0.1)  # Saniyede 10 veri göndermek için 0.1 saniye bekle
