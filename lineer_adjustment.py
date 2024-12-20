import time
from datetime import datetime

from speed_utility import reverse_calculate_value, write_to_modbus
from fuzzy_control import fuzzy_output

# Speed matrix tanımı
speed_matrix = [
    [300, 78, 55],
    [290, 76, 52],
    [280, 74, 45],
    [270, 72, 42],
    [260, 70, 36],
    [250, 69, 33],
    [240, 68, 30],
    [230, 68, 28.5],
    [220, 67, 27],
    [210, 66, 25.5],
    [200, 66, 24.8],
    [190, 66, 24.2],
    [180, 65, 23.6],
    [170, 65, 23.6],
    [160, 65, 23.4],
    [150, 65, 23.4],
    [140, 65, 23.4],
    [130, 65, 23.6],
    [120, 65, 23.6],
    [110, 66, 24.2],
    [100, 66, 24.8],
    [90, 66, 25.5],
    [80, 67, 27],
    [70, 68, 28.5],
    [60, 68, 30],
    [50, 69, 33],
    [40, 70, 36],
    [30, 72, 42],
    [20, 74, 45],
    [10, 76, 52],
    [0, 78, 55],
]
katsayi = 1.2

def interpolate_speeds_by_height(height):
    """
    Verilen yükseklik için kesme ve inme hızlarını lineer interpolasyon ile hesaplar.

    :param height: Yükseklik (mm)
    :return: Kesme hızı ve inme hızı
    """

    if height >= speed_matrix[0][0]:
        return speed_matrix[0][1], speed_matrix[0][2]
    elif height <= speed_matrix[-1][0]:
        return speed_matrix[-1][1], speed_matrix[-1][2]

    for i in range(len(speed_matrix) - 1):
        high = speed_matrix[i][0]
        low = speed_matrix[i + 1][0]
        if high >= height > low:
            high_speeds = speed_matrix[i][1], speed_matrix[i][2]
            low_speeds = speed_matrix[i + 1][1], speed_matrix[i + 1][2]

            kesme_hizi = ((height - low) / (high - low)) * (high_speeds[0] - low_speeds[0]) + low_speeds[0]
            inme_hizi = ((height - low) / (high - low)) * (high_speeds[1] - low_speeds[1]) + low_speeds[1]
            return kesme_hizi, inme_hizi

    return (speed_matrix[-1][1]), (speed_matrix[-1][2])

cutting_start_timestamp = None

def adjust_speeds_linear(processed_speed_data, modbus_client, last_modbus_write_time, speed_adjustment_interval, cikis_sim, prev_current):
    """
    Lineer kontrol algoritması ile hız ayarlamaları yapan fonksiyon.

    :param processed_speed_data: İşlenmiş veri (sensörlerden alınan ve normalize edilmiş)
    :param modbus_client: Modbus istemcisi
    :param last_modbus_write_time: Son modbus yazma zamanı
    :param speed_adjustment_interval: Modbus yazma aralığı
    :param cikis_sim: Fuzzy kontrol sistemi simülasyonu
    :return: Son yazma zamanı ve fuzzy output değeri
    """
    testere_durumu = processed_speed_data.get('testere_durumu')
    global katsayi
    global cutting_start_timestamp

    # Testere durumu aktif değilse çıkış yap
    if testere_durumu != 3:
        if cutting_start_timestamp is not None:
            cutting_end_timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\n\nKesim işlemi bitti: {cutting_end_timestamp}\n\n")
            cutting_start_timestamp = None
        return last_modbus_write_time, None

    if cutting_start_timestamp is None:
        cutting_start_timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\n\nKesim işlemi başladı: {cutting_start_timestamp}\n\n")

    current_time = time.time()

    # Modbus yazma aralığı kontrolü
    if current_time - last_modbus_write_time < speed_adjustment_interval:
        return last_modbus_write_time, None

    # Kafa yüksekliğine göre hızları lineer olarak hesapla
    kafa_yuksekligi_mm = processed_speed_data.get('kafa_yuksekligi_mm', 0)
    serit_kesme_hizi, serit_inme_hizi = interpolate_speeds_by_height(kafa_yuksekligi_mm)
    serit_inme_hizi = serit_inme_hizi * katsayi
    serit_kesme_hizi = serit_kesme_hizi * katsayi

    # Sınır kontrolü (20 alt sınır, 100 üst sınır)
    new_serit_inme_hizi = max(5, min(serit_inme_hizi, 101))
    new_serit_kesme_hizi = max(5, min(serit_kesme_hizi, 101))

    # Hız değerlerini güncelle
    processed_speed_data['serit_kesme_hizi'] = new_serit_kesme_hizi
    processed_speed_data['serit_inme_hizi'] = new_serit_inme_hizi

    inme_hizi_is_negative = new_serit_inme_hizi < 0

    # Fuzzy output hesapla
    serit_motor_akim_a = processed_speed_data.get('serit_motor_akim_a', 0)

    akim_degisim = serit_motor_akim_a - prev_current
    fuzzy_output_value = fuzzy_output(cikis_sim, serit_motor_akim_a, akim_degisim)

    # Hızları Modbus üzerinden yaz
    reverse_calculate_value(modbus_client, new_serit_kesme_hizi, 'serit_kesme_hizi')
    reverse_calculate_value(modbus_client, new_serit_inme_hizi, 'serit_inme_hizi', inme_hizi_is_negative)

    print(f"Lineer hız ayarlandı: Kesme Hızı={new_serit_kesme_hizi}, İnme Hızı={new_serit_inme_hizi}, Fuzzy Output={fuzzy_output_value}")
    last_modbus_write_time = current_time

    return last_modbus_write_time, fuzzy_output_value
