import time
import json
from pymodbus.client import ModbusTcpClient
import paho.mqtt.client as mqtt
import math
from threading import Thread

from config import config, DATABASE_PATH, TOTAL_DATABASE_PATH, RAW_DATABASE_PATH, TEXT_FILE_PATH
from database import insert_to_database
from fuzzy_logic import fuzzy_output

MODBUS_IP = config["modbus"]["ip"]
MODBUS_PORT = config["modbus"]["port"]
START_ADDRESS = config["modbus"]["start_address"]
NUMBER_OF_BITS = config["modbus"]["number_of_bits"]

broker_address = config["mqtt"]["broker_address"]
port = config["mqtt"]["port"]
topic = config["mqtt"]["topic"]
username = config["mqtt"]["username"]

modbus_client = ModbusTcpClient(MODBUS_IP, port=MODBUS_PORT)
modbus_client.connect()

client = mqtt.Client()
client.username_pw_set(username)
client.connect(broker_address, port=port)

last_speed_adjustment_time = 0
speed_adjustment_interval = 1


class SpeedBuffer:
    def __init__(self):
        self.kesme_hizi_delta = 0.0
        self.inme_hizi_delta = 0.0

    def add_to_buffer(self, kesme_hizi_increment, inme_hizi_increment):
        self.kesme_hizi_delta += kesme_hizi_increment
        self.inme_hizi_delta += inme_hizi_increment

    def adjust_and_check(self):
        if abs(self.kesme_hizi_delta) >= 1.0 or abs(self.inme_hizi_delta) >= 1.0:
            return True
        return False

    def get_adjustments(self):
        kesme_hizi_adjustment = math.floor(self.kesme_hizi_delta)
        inme_hizi_adjustment = math.floor(self.inme_hizi_delta)
        self.kesme_hizi_delta -= kesme_hizi_adjustment
        self.inme_hizi_delta -= inme_hizi_adjustment
        return kesme_hizi_adjustment, inme_hizi_adjustment


speed_buffer = SpeedBuffer()


def reverse_calculate_value(value, value_type):
    if value_type == 'serit_inme_hizi':
        return math.ceil((value / -0.06) + 65535)
    elif value_type == 'serit_kesme_hizi':
        return math.ceil(value / 0.0754)
    else:
        return value


def write_to_modbus_for_speed_adjustment(processed_speed_data):
    global modbus_client
    kesme_hizi_adjustment, inme_hizi_adjustment = speed_buffer.get_adjustments()
    kesme_hizi_adjustment += processed_speed_data["serit_kesme_hizi"]
    inme_hizi_adjustment += processed_speed_data["serit_inme_hizi"]

    kesme_hizi_modbus_value = reverse_calculate_value(kesme_hizi_adjustment, 'serit_kesme_hizi')
    kesme_hizi_register_address = 2066
    modbus_client.write_register(kesme_hizi_register_address, kesme_hizi_modbus_value)

    inme_hizi_is_negative = inme_hizi_adjustment < 0
    inme_hizi_modbus_value = reverse_calculate_value(math.ceil(abs(inme_hizi_adjustment)), 'serit_inme_hizi')
    inme_hizi_register_address = 2041
    write_to_modbus(modbus_client, inme_hizi_register_address, inme_hizi_modbus_value, inme_hizi_is_negative)


def write_to_modbus(modbus_client, address, value, is_negative):
    if not is_negative:
        sign_bit = 1 << 15
    else:
        sign_bit = 0

    modbus_value = sign_bit | value & 0x7FFF
    modbus_client.write_register(address, modbus_value)


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


def adjust_speeds_based_on_current(processed_speed_data, adjust_time, prev_current):
    global last_speed_adjustment_time
    serit_motor_tork_percentage = processed_speed_data.get('serit_motor_tork_percentage')
    testere_durumu = processed_speed_data.get('testere_durumu')
    serit_motor_akim_a = processed_speed_data.get('serit_motor_akim_a')
    serit_sapmasi = processed_speed_data.get('serit_sapmasi')

    akim_degisim = serit_motor_akim_a - prev_current
    fuzzy_factor = fuzzy_output(serit_motor_akim_a, akim_degisim)

    kesme_hizi_delta = 0.0
    inme_hizi_delta = 0.0

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
        kesme_hizi_delta += (fuzzy_factor * 0.1)
        inme_hizi_delta += (fuzzy_factor * 0.045)
        print(
            f"Tork yüksek, hızlar fuzzy faktörü ile ayarlanıyor... İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
            f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")

    if serit_motor_akim_a > 34 and testere_durumu == 3:
        kesme_hizi_delta += (fuzzy_factor * 0.1)
        inme_hizi_delta += (fuzzy_factor * 0.045)
        print(
            f"Akım çok yüksek, hızlar fuzzy faktörü ile ayarlanıyor... "
            f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
            f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")

    if adjust_time - last_speed_adjustment_time < speed_adjustment_interval:
        return serit_motor_akim_a
    last_speed_adjustment_time = adjust_time

    if abs(serit_sapmasi) > 5:
        kesme_hizi_delta += (fuzzy_factor * 0.1)
        inme_hizi_delta += (fuzzy_factor * 0.045)
        print(
            f"Şerit sapması yüksek, hızlar fuzzy faktörü ile ayarlanıyor... "
            f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
            f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")
    elif testere_durumu == 3:
        if serit_motor_akim_a < 22:
            kesme_hizi_delta += (fuzzy_factor * 0.1)
            inme_hizi_delta += (fuzzy_factor * 0.045)
            print(
                f"Akım düşük ve şerit sapması kabul edilebilir, hızlar fuzzy faktörü ile artırılıyor... "
                f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
                f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")
        elif serit_motor_akim_a > 24:
            kesme_hizi_delta += (fuzzy_factor * 0.1)
            inme_hizi_delta += (fuzzy_factor * 0.045)
            print(
                f"Akım yüksek, hızlar fuzzy faktörü ile azaltılıyor... "
                f"İnme hızı: {processed_speed_data['serit_inme_hizi']}, "
                f"Kesme hızı: {processed_speed_data['serit_kesme_hizi']}")

    speed_buffer.add_to_buffer(kesme_hizi_delta, inme_hizi_delta)
    if speed_buffer.adjust_and_check():
        write_to_modbus_for_speed_adjustment(processed_speed_data)

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
            insert_to_database(TOTAL_DATABASE_PATH, list(processed_data.values()), columns)
            raw_data.append(time.time())
            insert_to_database(RAW_DATABASE_PATH, raw_data, columns)
            write_to_text_file(raw_data)
            # print(json.dumps(processed_data, indent=4))
        time.sleep(0.1)


def mqtt_publisher():
    while True:
        time.sleep(1)
        # Bu kısımda MQTT için gerekli olan verileri alın ve publish_message fonksiyonu ile gönderin


def speed_controller():
    while True:
        time.sleep(speed_adjustment_interval)
        # Bu kısımda hız ayarlaması yapılacak verileri alın ve adjust_speeds_based_on_current fonksiyonu ile işlemleri yapın


def publish_message(data):
    json_data = json.dumps(data)
    client.publish(topic, json_data)


def write_to_text_file(data):
    with open(TEXT_FILE_PATH, "a") as file:
        file.write(", ".join(map(str, data)) + "\n")
