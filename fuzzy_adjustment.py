import time
from datetime import datetime
from time import strftime

from fuzzy_control import fuzzy_output
from speed_utility import reverse_calculate_value, write_to_modbus

cutting_start_timestamp = None


def adjust_speeds_based_on_current(processed_speed_data, prev_current, cikis_sim, modbus_client,
                                   adaptive_speed_control_enabled, speed_buffer, last_modbus_write_time,
                                   speed_adjustment_interval, kesme_hizi_tracker):
    """
    Fuzzy kontrol algoritması ile hız ayarlamaları yapan fonksiyon.

    :param processed_speed_data: İşlenmiş veri (sensörlerden alınan ve normalize edilmiş)
    :param prev_current: Önceki motor akımı
    :param cikis_sim: Fuzzy kontrol sistemi simülasyonu
    :param modbus_client: Modbus istemcisi
    :param adaptive_speed_control_enabled: Adaptif kontrol aktif mi?
    :param speed_buffer: Hız değişimlerini tamponlayan yardımcı sınıf
    :param last_modbus_write_time: Son modbus yazma zamanı
    :param speed_adjustment_interval: Modbus yazma aralığı
    :param kesme_hizi_tracker: Kesme hızı oranını takip eden yardımcı sınıf
    :return: Mevcut motor akımı, fuzzy faktörü, akım değişimi, son yazma zamanı
    """
    testere_durumu = processed_speed_data.get('testere_durumu')
    global cutting_start_timestamp

    # Testere aktif değilse veya adaptif kontrol kapalıysa oranı sıfırla
    if not adaptive_speed_control_enabled or testere_durumu != 3:
        if cutting_start_timestamp is not None:
            cutting_start_timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"\n\nKesim işlemi bitti: {cutting_start_timestamp}\n\n")
            cutting_start_timestamp = None
            kesme_hizi_tracker.kesme_orani = (55.0 / 78.0) * 100
        return processed_speed_data.get('serit_motor_akim_a'), None, None, last_modbus_write_time

    # Kesim işlemi başlamışsa zaman damgasını oluştur
    if cutting_start_timestamp is None:
        cutting_start_timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"\n\nKesim işlemi başladı: {cutting_start_timestamp}\n\n")

    current_time = time.time()
    if current_time - last_modbus_write_time < speed_adjustment_interval:
        return processed_speed_data.get('serit_motor_akim_a'), None, None, last_modbus_write_time

    # Fuzzy kontrol parametrelerini hesapla
    serit_motor_akim_a = processed_speed_data.get('serit_motor_akim_a')
    akim_degisim = serit_motor_akim_a - prev_current
    fuzzy_factor = fuzzy_output(cikis_sim, serit_motor_akim_a, akim_degisim)
    print(f"Fuzzy Factor: {fuzzy_factor}, Akım: {serit_motor_akim_a}, Akım Değişim: {akim_degisim}")

    # Fuzzy faktöre göre katsayılar belirle
    if fuzzy_factor < 0:
        inme_carpan = 0.1
        kesme_carpan = (kesme_hizi_tracker.kesme_orani / 1000) * 0.7
    else:
        inme_carpan = (kesme_hizi_tracker.kesme_orani / 1000)
        kesme_carpan = 0.1 * 0.7

    kesme_hizi_delta = fuzzy_factor * kesme_carpan
    inme_hizi_delta = fuzzy_factor * inme_carpan

    # Hız sınırlarını kontrol et ve sınırlamalar uygula
    if processed_speed_data['serit_inme_hizi'] <= 20 and fuzzy_factor < 0 and testere_durumu == 3:
        processed_speed_data['serit_inme_hizi'] = 20
        return serit_motor_akim_a, fuzzy_factor, akim_degisim, last_modbus_write_time

    elif processed_speed_data['serit_kesme_hizi'] >= 100 and fuzzy_factor > 0 and testere_durumu == 3:
        processed_speed_data['serit_kesme_hizi'] = 100
        return serit_motor_akim_a, fuzzy_factor, akim_degisim, last_modbus_write_time

    # Değişiklikleri tamponla
    speed_buffer.add_to_buffer(kesme_hizi_delta, inme_hizi_delta)
    print(f"Tampona Eklenen Kesme Hızı Değişimi: {kesme_hizi_delta}, İnme Hızı Değişimi: {inme_hizi_delta}")

    # Tampon dolduğunda değişiklikleri uygula
    if speed_buffer.adjust_and_check():
        print("Tampon doldu, hızlar güncelleniyor.")
        kesme_hizi_adjustment, inme_hizi_adjustment = speed_buffer.get_adjustments()
        new_serit_kesme_hizi = processed_speed_data['serit_kesme_hizi']
        new_serit_inme_hizi = processed_speed_data['serit_inme_hizi'] + inme_hizi_adjustment

        kesme_hizi_tracker.check_and_update_orani(new_serit_kesme_hizi)

        # Hız oranlarını düzelt
        ratio = (new_serit_inme_hizi / new_serit_kesme_hizi) * 100
        while ratio < (kesme_hizi_tracker.kesme_orani - 1.0):
            new_serit_inme_hizi += 0.1
            ratio = (new_serit_inme_hizi / new_serit_kesme_hizi) * 100
        while ratio > (kesme_hizi_tracker.kesme_orani + 1.0):
            new_serit_inme_hizi -= 0.1
            ratio = (new_serit_inme_hizi / new_serit_kesme_hizi) * 100

        inme_hizi_is_negative = new_serit_inme_hizi < 0

        # Hızları Modbus üzerinden yaz
        reverse_calculate_value(modbus_client, new_serit_kesme_hizi, 'serit_kesme_hizi')
        reverse_calculate_value(modbus_client, new_serit_inme_hizi, 'serit_inme_hizi', inme_hizi_is_negative)

        last_modbus_write_time = current_time

    return serit_motor_akim_a, fuzzy_factor, akim_degisim, last_modbus_write_time
