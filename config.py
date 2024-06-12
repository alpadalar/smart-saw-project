import yaml
import os
import time


def read_config(file_path):
    with open(file_path, 'r') as config_file:
        config_data = yaml.safe_load(config_file)
    return config_data


def create_sensor_folder():
    nowtime = time.strftime('%d-%m-%Y_%H-%M-%S')
    base_path = os.path.join(os.getcwd(), "sensor_data", nowtime)
    os.makedirs(base_path, exist_ok=True)
    return base_path


def create_files(paths):
    for path in paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            open(path, 'w').close()  # Create empty file


config = read_config("config.yaml")
base_path = create_sensor_folder()
DATABASE_PATH = os.path.join(base_path, config["database"]["database_path"].format(time.strftime("%Y%m%d%H%M%S")))
TOTAL_DATABASE_PATH = os.path.join(base_path, config["database"]["total_database_path"])
RAW_DATABASE_PATH = os.path.join(base_path, config["database"]["raw_database_path"])
TEXT_FILE_PATH = os.path.join(base_path, config["database"]["text_file_path"])
columns = config["database"]["columns"]

create_files([DATABASE_PATH, TOTAL_DATABASE_PATH, RAW_DATABASE_PATH, TEXT_FILE_PATH])
