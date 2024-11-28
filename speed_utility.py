import math
import time

# Statik register adresleri
KESME_HIZI_REGISTER_ADDRESS = 2066
INME_HIZI_REGISTER_ADDRESS = 2041


class SpeedBuffer:
    """
    Hız değişimlerini geçici olarak saklayan bir tampon sınıfı.
    Belirli bir eşiğe ulaşıldığında değişim bilgilerini verir ve tamponu sıfırlar.
    """
    def __init__(self):
        self.kesme_hizi_delta = 0.0
        self.inme_hizi_delta = 0.0

    def add_to_buffer(self, kesme_hizi_increment, inme_hizi_increment):
        """
        Hız değişimlerini tampon bölgesine ekler.
        :param kesme_hizi_increment: Kesme hızı değişimi
        :param inme_hizi_increment: İnme hızı değişimi
        """
        self.kesme_hizi_delta += kesme_hizi_increment
        self.inme_hizi_delta += inme_hizi_increment

    def adjust_and_check(self):
        """
        Hız değişimlerinin belirli bir eşiğe ulaşıp ulaşmadığını kontrol eder.
        :return: Eşik aşıldıysa True, aksi halde False
        """
        if abs(self.kesme_hizi_delta) >= 1.0 or abs(self.inme_hizi_delta) >= 1.0:
            return True
        return False

    def get_adjustments(self):
        """
        Tampondaki hız değişimlerini alır ve tamponu sıfırlar.
        :return: Kesme ve inme hızı ayarlamaları
        """
        kesme_hizi_adjustment = math.floor(self.kesme_hizi_delta)
        inme_hizi_adjustment = math.floor(self.inme_hizi_delta)
        self.kesme_hizi_delta -= kesme_hizi_adjustment
        self.inme_hizi_delta -= inme_hizi_adjustment
        return kesme_hizi_adjustment, inme_hizi_adjustment


class KesmeHiziTracker:
    """
    Kesme hızı oranını izleyen ve değişimleri kontrol eden bir sınıf.
    """
    def __init__(self):
        self.last_time_checked = time.time()
        self.initial_speed = None
        self.kesme_orani = (55.0 / 78.0) * 100  # Başlangıç kesme oranı

    def check_and_update_orani(self, current_speed):
        """
        Kesme hızındaki değişimi kontrol eder ve oranı günceller.
        :param current_speed: Anlık kesme hızı
        """
        current_time = time.time()
        if self.initial_speed is None:
            self.initial_speed = current_speed

        if current_time - self.last_time_checked >= 0.5:
            speed_difference = current_speed - self.initial_speed
            if abs(speed_difference) >= 0.5:
                if speed_difference > 0:
                    self.kesme_orani += 3
                else:
                    self.kesme_orani -= 3
                self.initial_speed = current_speed
                self.last_time_checked = current_time


def reverse_calculate_value(modbus_client, value, value_type, inme_hizi_is_negative=False):
    """
    Hız değerlerini makine tarafından beklenen değerlere dönüştürür.
    :param value: Girdi hız değeri
    :param value_type: Değer tipi ('serit_inme_hizi' veya 'serit_kesme_hizi')
    :return: Dönüştürülmüş hız değeri
    """
    if value_type == 'serit_inme_hizi':
        inme_hizi_modbus_value = math.ceil((value / -0.06) + 65535)
        write_to_modbus(modbus_client, INME_HIZI_REGISTER_ADDRESS, inme_hizi_modbus_value, inme_hizi_is_negative)
    elif value_type == 'serit_kesme_hizi':
        kesme_hizi_modbus_value = math.ceil(value / 0.0754)
        write_to_modbus(modbus_client, KESME_HIZI_REGISTER_ADDRESS, kesme_hizi_modbus_value)
    else:
        return value


def write_to_modbus(modbus_client, address, value, is_negative=False):
    """
    Modbus cihazına hız değerlerini yazan yardımcı fonksiyon.
    :param modbus_client: Modbus istemcisi
    :param address: Yazılacak Modbus adresi
    :param value: Yazılacak değer
    :param is_negative: Değer negatif mi?
    """
    if address == 2041:  # İnme hızı adresi
        if not is_negative:
            sign_bit = 1 << 15
        else:
            sign_bit = 0

        modbus_value = sign_bit | value & 0x7FFF
        modbus_client.write_register(address, modbus_value)

    elif address == 2066:  # Kesme hızı adresi
        modbus_client.write_register(address, value)
