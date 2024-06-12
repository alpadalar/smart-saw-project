import time
from pymodbus.client import ModbusTcpClient
from config import config, TOTAL_DATABASE_PATH, RAW_DATABASE_PATH, TEXT_FILE_PATH, columns
from database import insert_to_database
from speed_control import adjust_speeds_based_on_current, process_row

MODBUS_IP = config["modbus"]["ip"]
MODBUS_PORT = config["modbus"]["port"]
START_ADDRESS = config["modbus"]["start_address"]
NUMBER_OF_BITS = config["modbus"]["number_of_bits"]

modbus_client = ModbusTcpClient(MODBUS_IP, port=MODBUS_PORT)
modbus_client.connect()


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
        time.sleep(0.1)


def write_to_text_file(data):
    with open(TEXT_FILE_PATH, "a") as file:
        file.write(", ".join(map(str, data)) + "\n")
