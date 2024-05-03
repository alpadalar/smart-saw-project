import json
import math
import sqlite3
import time
import os

# import paho.mqtt.client as mqtt
import yaml
from pymodbus.client import ModbusTcpClient

# Create sensor folder with suffix dd-mm-yyyy_00:00 in sensor_data folder
nowtime = time.strftime('%d-%m-%Y_%H-%M-%S')
os.makedirs(f"./sensor_data/{nowtime}", exist_ok=True)


# Config dosyasını okuma
def read_config(file_path):
    with open(file_path, 'r') as config_file:
        config_data = yaml.safe_load(config_file)
    return config_data


config = read_config("config.yaml")

# Modbus ve MQTT yapılandırma
MODBUS_IP = config["modbus"]["ip"]
MODBUS_PORT = config["modbus"]["port"]
START_ADDRESS = config["modbus"]["start_address"]
NUMBER_OF_BITS = config["modbus"]["number_of_bits"]

DATABASE_PATH = config["database"]["database_path"].format(time.strftime("%Y%m%d%H%M%S"))
TOTAL_DATABASE_PATH = config["database"]["total_database_path"]
RAW_DATABASE_PATH = config["database"]["raw_database_path"]
TEXT_FILE_PATH = config["database"]["text_file_path"]
columns = config["database"]["columns"]

broker_address = "185.87.252.58"
port = 1883
topic = "v1/devices/me/telemetry"
username = "3EvsGJhFyBGuZiJxbXOO"

#client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
#client.username_pw_set(username)
#client.connect(broker_address, port=port)

modbus_client = ModbusTcpClient(MODBUS_IP, port=MODBUS_PORT)
# modbus_client.connect()

last_speed_adjustment_time = 0
speed_adjustment_interval = 1


# Veri tabanı ve MQTT işlemleri
def create_table(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    create_table_query = "CREATE TABLE IF NOT EXISTS imas_testere ({})".format(
        ", ".join(["{} {}".format(col, dtype) for col, dtype in columns.items()])
    )
    cursor.execute(create_table_query)
    conn.commit()
    conn.close()


def insert_to_database(db_path, data):
    create_table(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    columns_str = ", ".join(columns.keys())
    placeholders = ", ".join(["?" for _ in columns])
    cursor.execute(f'INSERT INTO imas_testere ({columns_str}) VALUES ({placeholders})', data)
    conn.commit()
    conn.close()


def publish_message(data):
    json_data = json.dumps(data)
    client.publish(topic, json_data)


def write_to_text_file(data):
    TEXT_FILE_PATH = f"./sensor_data/{nowtime}/raw.txt"
    with open(TEXT_FILE_PATH, "a") as file:
        file.write(", ".join(map(str, data)) + "\n")


# Veri işleme ve hız ayarlama
def process_row(row_data):
    # Direkt dönüşüm işlemleri
    row_data['testere_durumu'] = int(row_data['testere_durumu'])
    row_data['alarm_status'] = int(row_data['alarm_status'])
    row_data['alarm_bilgisi'] = f"0x{int(row_data['alarm_bilgisi']):04x}"
    row_data['kafa_yuksekligi_mm'] = row_data['kafa_yuksekligi_mm'] / 10.0
    row_data['serit_motor_akim_a'] = row_data['serit_motor_akim_a'] / 10.0
    row_data['serit_motor_tork_percentage'] = row_data['serit_motor_tork_percentage'] / 10.0
    row_data['inme_motor_akim_a'] = row_data['inme_motor_akim_a'] / 100.0
    row_data['mengene_basinc_bar'] = row_data['mengene_basinc_bar'] / 10.0
    row_data['serit_gerginligi_bar'] = row_data['serit_gerginligi_bar'] / 10.0
    row_data['serit_sapmasi'] = row_data['serit_sapmasi'] / 100.0
    row_data['ortam_sicakligi_c'] = row_data['ortam_sicakligi_c'] / 10.0
    row_data['ortam_nem_percentage'] = row_data['ortam_nem_percentage'] / 10.0
    row_data['sogutma_sivi_sicakligi_c'] = row_data['sogutma_sivi_sicakligi_c'] / 10.0
    row_data['hidrolik_yag_sicakligi_c'] = row_data['hidrolik_yag_sicakligi_c'] / 10.0
    row_data['ivme_olcer_x'] = row_data['ivme_olcer_x'] / 10.0
    row_data['ivme_olcer_y'] = row_data['ivme_olcer_y'] / 10.0
    row_data['ivme_olcer_z'] = row_data['ivme_olcer_z'] / 10.0
    # Kesme ve inme hızı için özel dönüşüm
    row_data['serit_kesme_hizi'] = row_data['serit_kesme_hizi'] * 0.0754
    row_data['serit_inme_hizi'] = (row_data['serit_inme_hizi'] - 65535) * -0.06

    # Conditional transformations
    if row_data['inme_motor_akim_a'] > 15:
        row_data['inme_motor_akim_a'] = 655.35 - row_data['inme_motor_akim_a']

    if abs(row_data['serit_sapmasi']) > 1.5:
        row_data['serit_sapmasi'] = abs(row_data['serit_sapmasi']) - 655.35

    return row_data


def reverse_calculate_value(value, value_type):
    if value_type == 'serit_inme_hizi':
        # Serit inme hızı için hesaplanan Modbus değerini al
        return math.ceil((value / -0.06) + 65535)
    elif value_type == 'serit_kesme_hizi':
        # Serit kesme hızı için hesaplanan Modbus değerini al
        return math.ceil(value / 0.0754)
    else:
        # Diğer tipler için genel bir dönüşüm (gerekirse)
        return value


def write_to_modbus_for_speed_adjustment(kesme_hizi, inme_hizi):
    global modbus_client

    # Serit kesme hızı için Modbus'a yazma işlemi
    kesme_hizi_modbus_value = reverse_calculate_value(kesme_hizi, 'serit_kesme_hizi')
    kesme_hizi_register_address = 2066  # Örnek bir Modbus register adresi
    modbus_client.write_register(kesme_hizi_register_address, kesme_hizi_modbus_value)

    # Serit inme hızı için Modbus'a yazma işlemi (işaret biti ile)
    inme_hizi_is_negative = inme_hizi < 0  # İşaret kontrolü
    inme_hizi_modbus_value = reverse_calculate_value(math.ceil(abs(inme_hizi)), 'serit_inme_hizi')
    inme_hizi_register_address = 2041  # Örnek bir Modbus register adresi
    write_to_modbus(modbus_client, inme_hizi_register_address, inme_hizi_modbus_value, inme_hizi_is_negative)


def write_to_modbus(modbus_client, address, value, is_negative):
    # İşaret bitini ayarla (MSB - en anlamlı bit)
    if not is_negative:
        sign_bit = 1 << 15  # Negatif için 16. biti 1 yap
    else:
        sign_bit = 0

    # Gerçek değeri ve işaret bitini birleştir
    modbus_value = sign_bit | value & 0x7FFF  # Değerin son 15 bitini koru

    # Modbus'a yaz
    modbus_client.write_register(address, modbus_value)


def adjust_speeds_based_on_current(processed_speed_data, adjust_time):
    global last_speed_adjustment_time
    serit_motor_tork_percentage = processed_speed_data.get('serit_motor_tork_percentage')
    testere_durumu = processed_speed_data.get('testere_durumu')
    serit_motor_akim_a = processed_speed_data.get('serit_motor_akim_a')
    serit_sapmasi = processed_speed_data.get('serit_sapmasi')
    print(
        f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
        f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")

    if processed_speed_data['serit_kesme_hizi'] <= 5:
        return

    if processed_speed_data['serit_inme_hizi'] < 29 and testere_durumu == 3:
        processed_speed_data['serit_inme_hizi'] = 29
        return

    if serit_motor_tork_percentage > 7 and testere_durumu == 3:
        # Tork yüksekse hızı azalt
        processed_speed_data['serit_kesme_hizi'] *= 0.98
        processed_speed_data['serit_inme_hizi'] *= 0.98
        write_to_modbus_for_speed_adjustment(processed_speed_data['serit_kesme_hizi'],
                                             processed_speed_data['serit_inme_hizi'])
        print(
            f"Tork yüksek, hızlar azaltılıyor... İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
            f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")

    if serit_motor_akim_a > 34 and testere_durumu == 3:
        # Akım yüksek, hızı azalt
        processed_speed_data['serit_kesme_hizi'] *= 0.8
        processed_speed_data['serit_inme_hizi'] *= 0.8
        print(
            f"Akım çok yüksek, hızlar azaltılıyor... "
            f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
            f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")
        # Modbus'a hız ayarlamalarını yaz
        write_to_modbus_for_speed_adjustment(processed_speed_data['serit_kesme_hizi'],
                                             processed_speed_data['serit_inme_hizi'])

    # Belirtilen aralıkta bir kez çalıştır
    if adjust_time - last_speed_adjustment_time < speed_adjustment_interval:
        return
    last_speed_adjustment_time = adjust_time  # Son çalışma zamanını güncelle

    # Şerit sapması öncelikli kontrol
    if abs(serit_sapmasi) > 5:
        # Şerit sapması yüksekse hızı azalt
        processed_speed_data['serit_kesme_hizi'] *= 1
        processed_speed_data['serit_inme_hizi'] *= 0.98
        write_to_modbus_for_speed_adjustment(processed_speed_data['serit_kesme_hizi'],
                                             processed_speed_data['serit_inme_hizi'])
        print(
            f"Şerit sapması yüksek, hızlar azaltılıyor... "
            f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
            f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")
    elif testere_durumu == 3:
        # Şerit sapması kabul edilebilir seviyede ise akım kontrolü yap
        if serit_motor_akim_a < 24:
            # Akım düşük ve şerit sapması kabul edilebilir seviyede, hızı artır
            processed_speed_data['serit_kesme_hizi'] *= 1.02
            processed_speed_data['serit_inme_hizi'] *= 1.02
            print(
                f"Akım düşük ve şerit sapması kabul edilebilir, hızlar artırılıyor... "
                f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
                f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")
        elif serit_motor_akim_a > 28:
            # Akım yüksek, hızı azalt
            processed_speed_data['serit_kesme_hizi'] *= 1
            processed_speed_data['serit_inme_hizi'] *= 0.98
            print(
                f"Akım yüksek, hızlar azaltılıyor... "
                f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
                f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")
        # Modbus'a hız ayarlamalarını yaz
        write_to_modbus_for_speed_adjustment(processed_speed_data['serit_kesme_hizi'],
                                             processed_speed_data['serit_inme_hizi'])


# Ana döngü
while True:
    current_time = time.time()
    # Modbus'tan ham veri okuma
    response = modbus_client.read_holding_registers(START_ADDRESS, NUMBER_OF_BITS)
    if not response.isError():
        raw_data = response.registers
        data_dict = dict(zip(columns.keys(), raw_data))
        data_dict["timestamp"] = time.time()
        processed_data = process_row(data_dict)
        # adjust_speeds_based_on_current(processed_speed_data, adjust_time)
        TOTAL_DATABASE_PATH = f"./sensor_data/{nowtime}/total.db"
        insert_to_database(TOTAL_DATABASE_PATH, list(processed_data.values()))
        # publish_message(processed_speed_data)
        raw_data.append(time.time())
        RAW_DATABASE_PATH = f"./sensor_data/{nowtime}/raw.db"
        insert_to_database(RAW_DATABASE_PATH, raw_data)
        write_to_text_file(raw_data)
        print(json.dumps(processed_data,indent=4))
    time.sleep(0.1)
