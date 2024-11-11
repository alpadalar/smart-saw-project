import time
from pymodbus.client import ModbusTcpClient
from datetime import datetime


def read_modbus_data(client, start_address, number_of_bits, interval=0.1, stop_threads_flag=None, conn_status=0):
    while True:
        # stop_threads_flag kontrolü: Thread sonlanması için kontrol yapıyoruz
        if stop_threads_flag and stop_threads_flag():
            print(f"{datetime.now()}: Stopping modbus data reading...")
            break

        if client.is_socket_open():
            conn_status = 1
            try:
                response = client.read_holding_registers(start_address, number_of_bits)
                if not response.isError():
                    yield response.registers
                time.sleep(interval)
            except Exception as e:
                print(f"{datetime.now()}: Error reading modbus data: {e}")
                time.sleep(interval)
        else:
            current_time = datetime.now()
            print(f"{current_time}: Connection lost, waiting...")
            conn_status = 0
            time.sleep(1)
