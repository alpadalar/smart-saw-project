import json
import math
import sqlite3
import time
import os
from threading import Thread
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from pymodbus.client import ModbusTcpClient
import paho.mqtt.client as mqtt
import yaml
import matplotlib.pyplot as plt

# Create sensor folder with suffix dd-mm-yyyy_00:00 in sensor_data folder
nowtime = time.strftime('%d-%m-%Y_%H-%M-%S')
base_path = os.path.join(os.getcwd(), "sensor_data", nowtime)
os.makedirs(base_path, exist_ok=True)

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

DATABASE_PATH = os.path.join(base_path, config["database"]["database_path"].format(time.strftime("%Y%m%d%H%M%S")))
TOTAL_DATABASE_PATH = os.path.join(base_path, config["database"]["total_database_path"])
RAW_DATABASE_PATH = os.path.join(base_path, config["database"]["raw_database_path"])
TEXT_FILE_PATH = os.path.join(base_path, config["database"]["text_file_path"])
columns = config["database"]["columns"]

# Create all database and txt files
for path in [DATABASE_PATH, TOTAL_DATABASE_PATH, RAW_DATABASE_PATH, TEXT_FILE_PATH]:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        open(path, 'w').close()  # Create empty file

broker_address = config["mqtt"]["broker_address"]
port = config["mqtt"]["port"]
topic = config["mqtt"]["topic"]
username = config["mqtt"]["username"]

#client = mqtt.Client()
#client.username_pw_set(username, password)
#client.connect(broker_address, port=port)

modbus_client = ModbusTcpClient(MODBUS_IP, port=MODBUS_PORT)
modbus_client.connect()

last_speed_adjustment_time = 0
speed_adjustment_interval = 1

# Fuzzy logic için girişlerin tanımlanması
akim = ctrl.Antecedent(np.arange(10, 29, 1), 'akim')
akim_degisim = ctrl.Antecedent(np.arange(-3, 4, 1), 'akim_degisim')

# Çıkışın tanımlanması
cikis_degisim = ctrl.Consequent(np.arange(-3, 4, 1), 'cikis_degisim')

# Üyelik fonksiyonlarının tanımlanması
akim['NB'] = fuzz.trimf(akim.universe, [10, 10, 18])
akim['NK'] = fuzz.trimf(akim.universe, [10, 18, 22])
akim['ideal'] = fuzz.trimf(akim.universe, [18, 20, 22])
akim['PK'] = fuzz.trimf(akim.universe, [18, 22, 28])
akim['PB'] = fuzz.trimf(akim.universe, [22, 28, 28])

akim_degisim['NB'] = fuzz.trimf(akim_degisim.universe, [-3, -3, -1])
akim_degisim['NK'] = fuzz.trimf(akim_degisim.universe, [-3, -1, 1])
akim_degisim['Z'] = fuzz.trimf(akim_degisim.universe, [-1, 0, 1])
akim_degisim['PK'] = fuzz.trimf(akim_degisim.universe, [-1, 1, 3])
akim_degisim['PB'] = fuzz.trimf(akim_degisim.universe, [1, 3, 3])

cikis_degisim['NB'] = fuzz.trimf(cikis_degisim.universe, [-3, -3, -2])
cikis_degisim['NO'] = fuzz.trimf(cikis_degisim.universe, [-3, -2, -1])
cikis_degisim['NK'] = fuzz.trimf(cikis_degisim.universe, [-2, -1, 0])
cikis_degisim['Z'] = fuzz.trimf(cikis_degisim.universe, [-1, 0, 1])
cikis_degisim['PK'] = fuzz.trimf(cikis_degisim.universe, [0, 1, 2])
cikis_degisim['PO'] = fuzz.trimf(cikis_degisim.universe, [1, 2, 3])
cikis_degisim['PB'] = fuzz.trimf(cikis_degisim.universe, [2, 3, 3])

# Kuralların tanımlanması
rules = [
    ctrl.Rule(akim['NB'] & akim_degisim['NB'], cikis_degisim['PB']),
    ctrl.Rule(akim['NB'] & akim_degisim['NK'], cikis_degisim['PB']),
    ctrl.Rule(akim['NB'] & akim_degisim['Z'], cikis_degisim['PB']),
    ctrl.Rule(akim['NB'] & akim_degisim['PK'], cikis_degisim['PO']),
    ctrl.Rule(akim['NB'] & akim_degisim['PB'], cikis_degisim['PK']),
    ctrl.Rule(akim['NK'] & akim_degisim['NB'], cikis_degisim['PO']),
    ctrl.Rule(akim['NK'] & akim_degisim['NK'], cikis_degisim['PK']),
    ctrl.Rule(akim['NK'] & akim_degisim['Z'], cikis_degisim['PK']),
    ctrl.Rule(akim['NK'] & akim_degisim['PK'], cikis_degisim['PK']),
    ctrl.Rule(akim['NK'] & akim_degisim['PB'], cikis_degisim['Z']),
    ctrl.Rule(akim['ideal'] & akim_degisim['NB'], cikis_degisim['PK']),
    ctrl.Rule(akim['ideal'] & akim_degisim['NK'], cikis_degisim['Z']),
    ctrl.Rule(akim['ideal'] & akim_degisim['Z'], cikis_degisim['Z']),
    ctrl.Rule(akim['ideal'] & akim_degisim['PK'], cikis_degisim['Z']),
    ctrl.Rule(akim['ideal'] & akim_degisim['PB'], cikis_degisim['NK']),
    ctrl.Rule(akim['PK'] & akim_degisim['NB'], cikis_degisim['Z']),
    ctrl.Rule(akim['PK'] & akim_degisim['NK'], cikis_degisim['NK']),
    ctrl.Rule(akim['PK'] & akim_degisim['Z'], cikis_degisim['NK']),
    ctrl.Rule(akim['PK'] & akim_degisim['PK'], cikis_degisim['NK']),
    ctrl.Rule(akim['PK'] & akim_degisim['PB'], cikis_degisim['NO']),
    ctrl.Rule(akim['PB'] & akim_degisim['NB'], cikis_degisim['NK']),
    ctrl.Rule(akim['PB'] & akim_degisim['NK'], cikis_degisim['NO']),
    ctrl.Rule(akim['PB'] & akim_degisim['Z'], cikis_degisim['NB']),
    ctrl.Rule(akim['PB'] & akim_degisim['PK'], cikis_degisim['NB']),
    ctrl.Rule(akim['PB'] & akim_degisim['PB'], cikis_degisim['NB']),
]

# Kuralların sisteme eklenmesi
cikis_ctrl = ctrl.ControlSystem(rules)
cikis_sim = ctrl.ControlSystemSimulation(cikis_ctrl)

def fuzzy_output(input_akim, input_akim_degisim):
    cikis_sim.input['akim'] = input_akim
    cikis_sim.input['akim_degisim'] = input_akim_degisim
    cikis_sim.compute()
    return cikis_sim.output['cikis_degisim']

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
    with open(TEXT_FILE_PATH, "a") as file:
        file.write(", ".join(map(str, data)) + "\n")

def process_row(row_data):
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
    row_data['serit_kesme_hizi'] = row_data['serit_kesme_hizi'] * 0.0754
    row_data['serit_inme_hizi'] = (row_data['serit_inme_hizi'] - 65535) * -0.06

    if row_data['inme_motor_akim_a'] > 15:
        row_data['inme_motor_akim_a'] = 655.35 - row_data['inme_motor_akim_a']

    if abs(row_data['serit_sapmasi']) > 1.5:
        row_data['serit_sapmasi'] = abs(row_data['serit_sapmasi']) - 655.35

    return row_data

def reverse_calculate_value(value, value_type):
    if value_type == 'serit_inme_hizi':
        return math.ceil((value / -0.06) + 65535)
    elif value_type == 'serit_kesme_hizi':
        return math.ceil(value / 0.0754)
    else:
        return value

def write_to_modbus_for_speed_adjustment(kesme_hizi, inme_hizi):
    global modbus_client

    kesme_hizi_modbus_value = reverse_calculate_value(kesme_hizi, 'serit_kesme_hizi')
    kesme_hizi_register_address = 2066
    modbus_client.write_register(kesme_hizi_register_address, kesme_hizi_modbus_value)

    inme_hizi_is_negative = inme_hizi < 0
    inme_hizi_modbus_value = reverse_calculate_value(math.ceil(abs(inme_hizi)), 'serit_inme_hizi')
    inme_hizi_register_address = 2041
    write_to_modbus(modbus_client, inme_hizi_register_address, inme_hizi_modbus_value, inme_hizi_is_negative)

def write_to_modbus(modbus_client, address, value, is_negative):
    if not is_negative:
        sign_bit = 1 << 15
    else:
        sign_bit = 0

    modbus_value = sign_bit | value & 0x7FFF
    modbus_client.write_register(address, modbus_value)

def adjust_speeds_based_on_current(processed_speed_data, adjust_time, prev_current):
    global last_speed_adjustment_time
    serit_motor_tork_percentage = processed_speed_data.get('serit_motor_tork_percentage')
    testere_durumu = processed_speed_data.get('testere_durumu')
    serit_motor_akim_a = processed_speed_data.get('serit_motor_akim_a')
    serit_sapmasi = processed_speed_data.get('serit_sapmasi')

    akim_degisim = serit_motor_akim_a - prev_current
    fuzzy_factor = fuzzy_output(serit_motor_akim_a, akim_degisim)

    print(
        f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
        f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}, "
        f"Fuzzy factor: {fuzzy_factor}")

    if processed_speed_data['serit_kesme_hizi'] <= 5:
        return serit_motor_akim_a

    if processed_speed_data['serit_inme_hizi'] < 29 and testere_durumu == 3:
        processed_speed_data['serit_inme_hizi'] = 29
        return serit_motor_akim_a

    if serit_motor_tork_percentage > 7 and testere_durumu == 3:
        processed_speed_data['serit_kesme_hizi'] *= fuzzy_factor
        processed_speed_data['serit_inme_hizi'] *= fuzzy_factor
        write_to_modbus_for_speed_adjustment(processed_speed_data['serit_kesme_hizi'],
                                             processed_speed_data['serit_inme_hizi'])
        print(
            f"Tork yüksek, hızlar fuzzy faktörü ile ayarlanıyor... İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
            f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")

    if serit_motor_akim_a > 34 and testere_durumu == 3:
        processed_speed_data['serit_kesme_hizi'] *= fuzzy_factor
        processed_speed_data['serit_inme_hizi'] *= fuzzy_factor
        print(
            f"Akım çok yüksek, hızlar fuzzy faktörü ile ayarlanıyor... "
            f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
            f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")
        write_to_modbus_for_speed_adjustment(processed_speed_data['serit_kesme_hizi'],
                                             processed_speed_data['serit_inme_hizi'])

    if adjust_time - last_speed_adjustment_time < speed_adjustment_interval:
        return serit_motor_akim_a
    last_speed_adjustment_time = adjust_time

    if abs(serit_sapmasi) > 5:
        processed_speed_data['serit_kesme_hizi'] *= fuzzy_factor
        processed_speed_data['serit_inme_hizi'] *= fuzzy_factor
        write_to_modbus_for_speed_adjustment(processed_speed_data['serit_kesme_hizi'],
                                             processed_speed_data['serit_inme_hizi'])
        print(
            f"Şerit sapması yüksek, hızlar fuzzy faktörü ile ayarlanıyor... "
            f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
            f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")
    elif testere_durumu == 3:
        if serit_motor_akim_a < 24:
            processed_speed_data['serit_kesme_hizi'] *= fuzzy_factor
            processed_speed_data['serit_inme_hizi'] *= fuzzy_factor
            print(
                f"Akım düşük ve şerit sapması kabul edilebilir, hızlar fuzzy faktörü ile artırılıyor... "
                f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
                f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")
        elif serit_motor_akim_a > 28:
            processed_speed_data['serit_kesme_hizi'] *= fuzzy_factor
            processed_speed_data['serit_inme_hizi'] *= fuzzy_factor
            print(
                f"Akım yüksek, hızlar fuzzy faktörü ile azaltılıyor... "
                f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
                f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")
        write_to_modbus_for_speed_adjustment(processed_speed_data['serit_kesme_hizi'],
                                             processed_speed_data['serit_inme_hizi'])
    return serit_motor_akim_a

def read_modbus_data():
    prev_current = 0
    while True:
        current_time = time.time()
        response = modbus_client.read_holding_registers(START_ADDRESS, NUMBER_OF_BITS)
        if not response.isError():
            raw_data = response.registers
            data_dict = dict(zip(columns.keys(), raw_data))
            data_dict["timestamp"] = time.time()
            processed_data = process_row(data_dict)
            prev_current = adjust_speeds_based_on_current(processed_data, current_time, prev_current)
            insert_to_database(TOTAL_DATABASE_PATH, list(processed_data.values()))
            raw_data.append(time.time())
            insert_to_database(RAW_DATABASE_PATH, raw_data)
            write_to_text_file(raw_data)
            print(json.dumps(processed_data, indent=4))
        time.sleep(0.1)

def mqtt_publisher():
    while True:
        time.sleep(1)
        # Bu kısımda MQTT için gerekli olan verileri alın ve publish_message fonksiyonu ile gönderin

def speed_controller():
    while True:
        time.sleep(speed_adjustment_interval)
        # Bu kısımda hız ayarlaması yapılacak verileri alın ve adjust_speeds_based_on_current fonksiyonu ile işlemleri yapın

if __name__ == "__main__":
    modbus_thread = Thread(target=read_modbus_data)
    #mqtt_thread = Thread(target=mqtt_publisher)
    speed_thread = Thread(target=speed_controller)

    modbus_thread.start()
    #mqtt_thread.start()
    speed_thread.start()

    modbus_thread.join()
    #mqtt_thread.join()
    speed_thread.join()
