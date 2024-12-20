import os
import time
import yaml
from threading import Thread
from queue import Queue
from modbus_reader import read_modbus_data
from fuzzy_adjustment import adjust_speeds_based_on_current
from lineer_adjustment import adjust_speeds_linear
# from dynamic_adjustment import adjust_speeds_linear
from data_handler import process_row, insert_to_database, write_to_text_file
from mqtt_publisher import mqtt_publisher
from ui_control import UIControl
from pymodbus.client import ModbusTcpClient
import tkinter as tk
from datetime import datetime
from camera_module import CameraModule
from speed_utility import SpeedBuffer, KesmeHiziTracker
from fuzzy_control import create_fuzzy_system

# Global variables
config_path = "config.yaml"
base_path = os.path.join(os.getcwd(), "sensor_data")
stop_threads = False  # Global flag to stop threads

fuzzy_control_enabled = False
linear_control_enabled = False


def read_config(file_path):
    with open(file_path, 'r') as config_file:
        config_data = yaml.safe_load(config_file)
    return config_data


def get_daily_folder(base_path):
    today = datetime.now().strftime('%Y-%m-%d')
    daily_folder = os.path.join(base_path, today)
    os.makedirs(daily_folder, exist_ok=True)
    return daily_folder


def on_closing():
    global stop_threads
    print("Uygulama kapatılıyor...")
    stop_threads = True
    root.quit()  # Tkinter ana döngüsünü durdurur
    root.destroy()  # Pencereyi yok eder


# Load configuration
config = read_config(config_path)

# Set up paths
daily_folder = get_daily_folder(base_path)
DATABASE_PATH = os.path.join(daily_folder, config["database"]["database_path"].format(time.strftime("%Y%m%d%H%M%S")))
TOTAL_DATABASE_PATH = os.path.join(daily_folder, config["database"]["total_database_path"])
RAW_DATABASE_PATH = os.path.join(daily_folder, config["database"]["raw_database_path"])
TEXT_FILE_PATH = os.path.join(daily_folder, config["database"]["text_file_path"])

columns = config["database"]["columns"]
columns["fuzzy_output"] = "REAL"
columns["akim_degisim"] = "REAL"
columns["fuzzy_control"] = "INTEGER"

data_queue = Queue()
processed_data_queue = Queue()
plot_queue = Queue()

# Initialize fuzzy control system and utilities
speed_buffer = SpeedBuffer()
kesme_hizi_tracker = KesmeHiziTracker()
cikis_sim = create_fuzzy_system()

MODBUS_IP = config["modbus"]["ip"]
MODBUS_PORT = config["modbus"]["port"]
modbus_client = ModbusTcpClient(MODBUS_IP, port=MODBUS_PORT)

last_modbus_write_time = time.time()
speed_adjustment_interval = 0.2

# Camera Module Initialization
raspberry_pi_ip = "192.168.13.97"
camera_module = CameraModule(raspberry_pi_ip)

conn_status = 0


def modbus_thread_func():
    global fuzzy_control_enabled, linear_control_enabled, last_modbus_write_time, stop_threads, conn_status
    prev_current = 0
    while not stop_threads:
        if not modbus_client.is_socket_open():
            try:
                modbus_client.connect()
                if stop_threads:
                    print("Modbus thread stopping...")
                    break
                print("Modbus connection established")
                conn_status = 1
            except Exception as e:
                if stop_threads:
                    print("Modbus thread stopping during connection...")
                    break
                print(f"Modbus connection failed: {e}")
                time.sleep(1)
                continue

        while not stop_threads:
            try:
                for raw_data in read_modbus_data(modbus_client, config["modbus"]["start_address"],
                                                 config["modbus"]["number_of_bits"],
                                                 stop_threads_flag=lambda: stop_threads, conn_status=conn_status):
                    if stop_threads:
                        print("Modbus thread stopping...")
                        break

                    data_dict = dict(zip(columns.keys(), raw_data))
                    data_dict["timestamp"] = time.time()
                    processed_data = process_row(data_dict)
                    prev_prev_current = prev_current
                    prev_current = processed_data.get('serit_motor_akim_a', None)

                    fuzzy_output_value = None
                    akim_degisim = None

                    if fuzzy_control_enabled:
                        # Fuzzy kontrol ile ayarlama
                        prev_current, fuzzy_output_value, akim_degisim, last_modbus_write_time = adjust_speeds_based_on_current(
                            processed_speed_data=processed_data,
                            prev_current=prev_current,
                            modbus_client=modbus_client,
                            adaptive_speed_control_enabled=fuzzy_control_enabled,
                            speed_buffer=speed_buffer,
                            last_modbus_write_time=last_modbus_write_time,
                            speed_adjustment_interval=speed_adjustment_interval,
                            kesme_hizi_tracker=kesme_hizi_tracker,
                            cikis_sim=cikis_sim
                        )
                        processed_data["fuzzy_control"] = 1

                    elif linear_control_enabled:
                        # Lineer kontrol ile ayarlama
                        last_modbus_write_time, fuzzy_output_value = adjust_speeds_linear(
                            processed_speed_data=processed_data,
                            modbus_client=modbus_client,
                            last_modbus_write_time=last_modbus_write_time,
                            speed_adjustment_interval=speed_adjustment_interval,
                            cikis_sim=cikis_sim,
                            prev_current = prev_prev_current
                        )
                        processed_data["fuzzy_control"] = 0

                    else:
                        # Sadece veri kaydı
                        processed_data["fuzzy_control"] = 0

                    processed_data["fuzzy_output"] = fuzzy_output_value
                    processed_data["akim_degisim"] = akim_degisim

                    data_queue.put(processed_data)
                    processed_data_queue.put(processed_data)
                    prev_current = processed_data.get('serit_motor_akim_a', None)

                conn_status = 1
            except Exception as e:
                if stop_threads:
                    print("Modbus thread stopping...")
                    break
                print(f"Error reading Modbus data: {e}")
                time.sleep(1)
                continue
        if stop_threads:
            break
        time.sleep(0.1)


def db_thread_func():
    global stop_threads
    while not stop_threads:
        if not data_queue.empty():
            processed_data = data_queue.get()
            insert_to_database(TOTAL_DATABASE_PATH, list(processed_data.values()), columns)
            write_to_text_file(processed_data, TEXT_FILE_PATH)
        time.sleep(0.1)
    print("DB thread stopping...")


def mqtt_thread_func():
    global stop_threads
    while not stop_threads:
        if not processed_data_queue.empty():
            mqtt_publisher(processed_data_queue)
        time.sleep(0.1)
    print("MQTT thread stopping...")


def toggle_fuzzy_control():
    global fuzzy_control_enabled
    fuzzy_control_enabled = not fuzzy_control_enabled
    print(f"Fuzzy Control Enabled: {fuzzy_control_enabled}")
    return fuzzy_control_enabled


def toggle_linear_control():
    global linear_control_enabled
    linear_control_enabled = not linear_control_enabled
    print(f"Linear Control Enabled: {linear_control_enabled}")
    return linear_control_enabled


if __name__ == "__main__":
    modbus_thread = Thread(target=modbus_thread_func)
    db_thread = Thread(target=db_thread_func)
    mqtt_thread = Thread(target=mqtt_thread_func)

    modbus_thread.start()
    db_thread.start()
    mqtt_thread.start()

    root = tk.Tk()
    root.protocol("WM_DELETE_WINDOW", on_closing)

    ui_control = UIControl(
        root=root,
        toggle_fuzzy_control_callback=toggle_fuzzy_control,
        toggle_linear_control_callback=toggle_linear_control,
        start_camera_callback=camera_module.start_camera,
        stop_camera_callback=camera_module.stop_camera,
        plot_queue=plot_queue,
        close_app_callback=on_closing,
        conn_status=conn_status
    )

    root.mainloop()

    print("Main thread waiting for other threads to stop...")
    modbus_thread.join()
    db_thread.join()
    mqtt_thread.join()
    print("All threads stopped.")
