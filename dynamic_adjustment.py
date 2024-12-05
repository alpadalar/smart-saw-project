import time
from speed_utility import reverse_calculate_value


class DynamicAdjustment:
    def __init__(self):
        self.previous_K_kesit = None
        self.current_K_kesit = None
        self.previous_current = None
        self.previous_fuzzy_output = None
        self.coefficient = None

    def calculate_K_kesit(self, current, inme_hizi, kesme_hizi):
        """
        K_kesit değerini hesaplar: K_kesit = Akım / (inme_hızı / kesme_hızı)
        """
        oran = inme_hizi / kesme_hizi if kesme_hizi != 0 else 1  # Kesme hızı sıfırsa oran 1 kabul edilir
        return current / oran if oran != 0 else 0  # Oran sıfırsa K_kesit 0 kabul edilir

    def update_coefficient(self, previous_current, previous_fuzzy_output, current_current):
        """
        Akım ve fuzzy output arasındaki katsayıyı dinamik olarak hesaplar.
        """
        if previous_fuzzy_output is not None and previous_fuzzy_output != 0:
            return (current_current - previous_current) / previous_fuzzy_output
        return None

    def adjust_speeds(self, processed_speed_data, modbus_client, fuzzy_output_value):
        """
        Dinamik ayarlama algoritmasını uygular ve hızları Modbus'a yazar.
        """
        # Sensör verilerini al
        inme_hizi = processed_speed_data.get('serit_inme_hizi', 0)
        kesme_hizi = processed_speed_data.get('serit_kesme_hizi', 0)
        current = processed_speed_data.get('serit_motor_akim_a', 0)

        # Yeni K_kesit değerini hesapla
        self.current_K_kesit = self.calculate_K_kesit(current, inme_hizi, kesme_hizi)

        # Akım ve fuzzy output katsayısını güncelle
        self.coefficient = self.update_coefficient(self.previous_current, self.previous_fuzzy_output, current)

        # Yeni oranı hesapla
        if self.coefficient is not None and fuzzy_output_value is not None:
            new_ratio = self.coefficient * fuzzy_output_value
        else:
            new_ratio = inme_hizi / kesme_hizi if kesme_hizi != 0 else 1

        # Hızları güncelle
        speed_adjustment = fuzzy_output_value * 0.1  # Fuzzy output ile hız değişimi (örnek: 0.1x katsayı)
        new_inme_hizi = inme_hizi + speed_adjustment * 100
        new_kesme_hizi = kesme_hizi + speed_adjustment * 70

        # Hız sınırlarını kontrol et
        new_inme_hizi = max(20, min(new_inme_hizi, 100))  # İnme hızı 20-100 arasında olmalı
        new_kesme_hizi = max(20, min(new_kesme_hizi, 100))  # Kesme hızı 20-100 arasında olmalı

        # Modbus'a yaz
        reverse_calculate_value(modbus_client, new_inme_hizi, 'serit_inme_hizi')
        reverse_calculate_value(modbus_client, new_kesme_hizi, 'serit_kesme_hizi')

        print(f"Dinamik ayarlama yapıldı: Kesme Hızı={new_kesme_hizi}, İnme Hızı={new_inme_hizi}, Katsayı={self.coefficient}")

        # Önceki değerleri güncelle
        self.previous_K_kesit = self.current_K_kesit
        self.previous_current = current
        self.previous_fuzzy_output = fuzzy_output_value


# Dinamik ayarlama için global bir örnek
dynamic_adjustment = DynamicAdjustment()


def adjust_speeds_linear(processed_speed_data, modbus_client, last_modbus_write_time, speed_adjustment_interval, cikis_sim, prev_current):
    """
    Lineer ayarlama yerine dinamik ayarlama fonksiyonunu çalıştırır.
    """
    fuzzy_output_value = cikis_sim.output['cikis_degisim'] if cikis_sim else None
    dynamic_adjustment.adjust_speeds(processed_speed_data, modbus_client, fuzzy_output_value)
    return time.time(), fuzzy_output_value
