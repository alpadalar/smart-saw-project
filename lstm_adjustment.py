import time
import numpy as np
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
from speed_utility import reverse_calculate_value


class LSTMAdjustment:
    def __init__(self, model_path):
        # LSTM modelini yükle ve ölçekleyicileri başlat
        self.model = load_model(model_path, compile=False)
        self.scaler_x = MinMaxScaler()
        self.scaler_y = MinMaxScaler()
        self.time_steps = 30
        self.future_offset = 0.5  # 500 ms (5 adım sonrasını tahmin)
        self.buffer = []  # [(zaman_damgası, tahmin_değerleri), ...]
        self.last_modbus_write_time = time.time()

    def prepare_data(self, data_window):
        """
        Zaman serisi verisini modele uygun şekilde hazırlar.
        """
        normalized_data = self.scaler_x.transform(data_window)
        X = np.expand_dims(normalized_data, axis=0)
        return X

    def predict_speeds(self, data_window):
        """
        LSTM modelini kullanarak hızları tahmin eder.
        """
        X = self.prepare_data(data_window)
        y_pred = self.model.predict(X)
        y_pred_inv = self.scaler_y.inverse_transform(y_pred)
        return y_pred_inv[0]

    def store_predictions(self, predicted_speeds):
        """
        Tahmini hedef zaman damgası ile birlikte tamponda saklar.
        """
        current_time = time.time()
        target_time = current_time + self.future_offset
        self.buffer.append((target_time, predicted_speeds))

    def send_to_modbus(self, modbus_client):
        """
        Tampondaki tahminleri kontrol eder ve zamanı gelen tahminleri Modbus'a gönderir.
        """
        current_time = time.time()
        new_buffer = []
        for target_time, predicted_speeds in self.buffer:
            if current_time >= target_time:
                serit_kesme_hizi, serit_inme_hizi = predicted_speeds
                # Modbus'a yaz
                reverse_calculate_value(modbus_client, serit_kesme_hizi, 'serit_kesme_hizi')
                reverse_calculate_value(modbus_client, serit_inme_hizi, 'serit_inme_hizi')
                print(f"Modbus'a yazıldı: Kesme Hızı={serit_kesme_hizi}, İnme Hızı={serit_inme_hizi}, Zaman={target_time}")
            else:
                new_buffer.append((target_time, predicted_speeds))  # Zamanı gelmeyenleri koru
        self.buffer = new_buffer

    def adjust_speeds(self, processed_speed_data, modbus_client, speed_adjustment_interval):
        """
        LSTM tahminine göre hız ayarlarını yapar ve zamanı geldiğinde Modbus'a gönderir.
        """
        # Zaman serisi tamponunu güncelle
        self.buffer.append([
            processed_speed_data['serit_motor_akim_a'],
            processed_speed_data['serit_kesme_hizi'],
            processed_speed_data['serit_inme_hizi']
        ])
        if len(self.buffer) > self.time_steps:
            self.buffer.pop(0)

        # Tampon yeterli veri içeriyorsa tahmin yap
        if len(self.buffer) >= self.time_steps:
            predicted_speeds = self.predict_speeds(self.buffer)
            self.store_predictions(predicted_speeds)

        # Zamanı gelen tahminleri Modbus'a gönder
        self.send_to_modbus(modbus_client)

        return self.last_modbus_write_time, None


# LSTM modeli için global bir örnek
lstm_adjustment = LSTMAdjustment("akim_kesme_inme_filtresiz.keras")


def adjust_speeds_linear(processed_speed_data, modbus_client, last_modbus_write_time, speed_adjustment_interval, cikis_sim, prev_current):
    """
    Lineer ayarlama yerine LSTM modeli ile hız ayarlarını yapar.
    """
    return lstm_adjustment.adjust_speeds(processed_speed_data, modbus_client, speed_adjustment_interval)
