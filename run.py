from multiprocessing import Process
from modbus import read_modbus_data
from mqtt import mqtt_publisher
from speed_control import adjust_speeds_based_on_current

if __name__ == "__main__":
    modbus_process = Process(target=read_modbus_data)
    mqtt_process = Process(target=mqtt_publisher)
    speed_process = Process(target=adjust_speeds_based_on_current)

    modbus_process.start()
    mqtt_process.start()
    speed_process.start()

    modbus_process.join()
    mqtt_process.join()
    speed_process.join()
