import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import math
import time

kesme_orani = 50.0


def create_fuzzy_system():
    akim = ctrl.Antecedent(np.arange(10, 35, 1), 'akim')
    akim_degisim = ctrl.Antecedent(np.arange(-10, 11, 1), 'akim_degisim')
    cikis_degisim = ctrl.Consequent(np.arange(-3, 4, 1), 'cikis_degisim')

    akim['NB'] = fuzz.trapmf(akim.universe, [10, 10, 12, 17])
    akim['NK'] = fuzz.trimf(akim.universe, [16, 18, 20])
    akim['ideal'] = fuzz.trimf(akim.universe, [19, 20.5, 22])
    akim['PK'] = fuzz.trimf(akim.universe, [21, 23, 25])
    akim['PB'] = fuzz.trapmf(akim.universe, [24, 30, 34, 34])

    akim_degisim['NB'] = fuzz.trapmf(akim_degisim.universe, [-10, -10, -3, -1])
    akim_degisim['NK'] = fuzz.trimf(akim_degisim.universe, [-3, -1, 1])
    akim_degisim['Z'] = fuzz.trimf(akim_degisim.universe, [-1, 0, 1])
    akim_degisim['PK'] = fuzz.trimf(akim_degisim.universe, [-1, 1, 3])
    akim_degisim['PB'] = fuzz.trapmf(akim_degisim.universe, [1, 3, 10, 10])

    cikis_degisim['NB'] = fuzz.trimf(cikis_degisim.universe, [-3, -3, -2])
    cikis_degisim['NO'] = fuzz.trimf(cikis_degisim.universe, [-3, -2, -1])
    cikis_degisim['NK'] = fuzz.trimf(cikis_degisim.universe, [-2, -1, 0])
    cikis_degisim['Z'] = fuzz.trimf(cikis_degisim.universe, [-1, 0, 1])
    cikis_degisim['PK'] = fuzz.trimf(cikis_degisim.universe, [0, 1, 2])
    cikis_degisim['PO'] = fuzz.trimf(cikis_degisim.universe, [1, 2, 3])
    cikis_degisim['PB'] = fuzz.trimf(cikis_degisim.universe, [2, 3, 3])

    rules = [
        ctrl.Rule(akim['NB'] & akim_degisim['NB'], cikis_degisim['PB']),
        ctrl.Rule(akim['NB'] & akim_degisim['NK'], cikis_degisim['PB']),
        ctrl.Rule(akim['NB'] & akim_degisim['Z'], cikis_degisim['PB']),
        ctrl.Rule(akim['NB'] & akim_degisim['PK'], cikis_degisim['PO']),
        ctrl.Rule(akim['NB'] & akim_degisim['PB'], cikis_degisim['PK']),
        ctrl.Rule(akim['NK'] & akim_degisim['NB'], cikis_degisim['PO']),
        ctrl.Rule(akim['NK'] & akim_degisim['NK'], cikis_degisim['PK']),
        ctrl.Rule(akim['NK'] & akim_degisim['Z'], cikis_degisim['PK']),
        ctrl.Rule(akim['NK'] & akim_degisim['PK'], cikis_degisim['PK']),
        ctrl.Rule(akim['NK'] & akim_degisim['PB'], cikis_degisim['Z']),
        ctrl.Rule(akim['ideal'] & akim_degisim['NB'], cikis_degisim['PK']),
        ctrl.Rule(akim['ideal'] & akim_degisim['NK'], cikis_degisim['Z']),
        ctrl.Rule(akim['ideal'] & akim_degisim['Z'], cikis_degisim['Z']),
        ctrl.Rule(akim['ideal'] & akim_degisim['PK'], cikis_degisim['Z']),
        ctrl.Rule(akim['ideal'] & akim_degisim['PB'], cikis_degisim['NK']),
        ctrl.Rule(akim['PK'] & akim_degisim['NB'], cikis_degisim['Z']),
        ctrl.Rule(akim['PK'] & akim_degisim['NK'], cikis_degisim['NK']),
        ctrl.Rule(akim['PK'] & akim_degisim['Z'], cikis_degisim['NK']),
        ctrl.Rule(akim['PK'] & akim_degisim['PK'], cikis_degisim['NK']),
        ctrl.Rule(akim['PK'] & akim_degisim['PB'], cikis_degisim['NO']),
        ctrl.Rule(akim['PB'] & akim_degisim['NB'], cikis_degisim['NK']),
        ctrl.Rule(akim['PB'] & akim_degisim['NK'], cikis_degisim['NO']),
        ctrl.Rule(akim['PB'] & akim_degisim['Z'], cikis_degisim['NB']),
        ctrl.Rule(akim['PB'] & akim_degisim['PK'], cikis_degisim['NB']),
        ctrl.Rule(akim['PB'] & akim_degisim['PB'], cikis_degisim['NB']),
    ]

    cikis_ctrl = ctrl.ControlSystem(rules)
    cikis_sim = ctrl.ControlSystemSimulation(cikis_ctrl)
    return cikis_sim


def fuzzy_output(cikis_sim, input_akim, input_akim_degisim):
    cikis_sim.input['akim'] = input_akim
    cikis_sim.input['akim_degisim'] = input_akim_degisim
    cikis_sim.compute()
    return cikis_sim.output['cikis_degisim']


def reverse_calculate_value(value, value_type):
    if value_type == 'serit_inme_hizi':
        return math.ceil((value / -0.06) + 65535)
    elif value_type == 'serit_kesme_hizi':
        return math.ceil(value / 0.0754)
    else:
        return value


class SpeedBuffer:
    def __init__(self):
        self.kesme_hizi_delta = 0.0
        self.inme_hizi_delta = 0.0

    def add_to_buffer(self, kesme_hizi_increment, inme_hizi_increment):
        self.kesme_hizi_delta += kesme_hizi_increment
        self.inme_hizi_delta += inme_hizi_increment

    def adjust_and_check(self):
        if abs(self.kesme_hizi_delta) >= 1.0 or abs(self.inme_hizi_delta) >= 1.0:
            return True
        return False

    def get_adjustments(self):
        kesme_hizi_adjustment = math.floor(self.kesme_hizi_delta)
        inme_hizi_adjustment = math.floor(self.inme_hizi_delta)
        self.kesme_hizi_delta -= kesme_hizi_adjustment
        self.inme_hizi_delta -= inme_hizi_adjustment
        return kesme_hizi_adjustment, inme_hizi_adjustment


class KesmeHiziTracker:
    def __init__(self):
        self.last_time_checked = time.time()
        self.initial_speed = None
        self.kesme_orani = 50.0

    def check_and_update_orani(self, current_speed):
        current_time = time.time()
        if self.initial_speed is None:
            self.initial_speed = current_speed

        if current_time - self.last_time_checked >= 10:
            speed_difference = current_speed - self.initial_speed
            if abs(speed_difference) >= (0.1 * self.initial_speed):
                if speed_difference > 0:
                    self.kesme_orani += 1
                else:
                    self.kesme_orani -= 1
                self.initial_speed = current_speed
                self.last_time_checked = current_time


tracker = KesmeHiziTracker()


def adjust_speeds_based_on_current(processed_speed_data, prev_current, cikis_sim, modbus_client,
                                   adaptive_speed_control_enabled, speed_buffer, last_modbus_write_time,
                                   speed_adjustment_interval, a_mm, kesme_hizi_tracker=tracker):
    testere_durumu = processed_speed_data.get('testere_durumu')
    kafa_yuksekligi_mm = processed_speed_data.get('kafa_yuksekligi_mm')

    if not adaptive_speed_control_enabled or testere_durumu != 3:
        return processed_speed_data.get('serit_motor_akim_a'), None, None, last_modbus_write_time

    serit_motor_akim_a = processed_speed_data.get('serit_motor_akim_a')
    akim_degisim = serit_motor_akim_a - prev_current
    fuzzy_factor = fuzzy_output(cikis_sim, serit_motor_akim_a, akim_degisim)
    # print(fuzzy_factor)

    if fuzzy_factor < 0:
        inme_carpan = 0.1
        kesme_carpan = (kesme_hizi_tracker.kesme_orani / 1000)
    else:
        inme_carpan = (kesme_hizi_tracker.kesme_orani / 1000)
        kesme_carpan = 0.1

    kesme_hizi_delta = 0.0
    inme_hizi_delta = 0.0

    if processed_speed_data['serit_inme_hizi'] <= 20 and fuzzy_factor < 0 and testere_durumu == 3:
        processed_speed_data['serit_inme_hizi'] = 20
        return serit_motor_akim_a, fuzzy_factor, akim_degisim, last_modbus_write_time

    kesme_hizi_delta += (fuzzy_factor * kesme_carpan)
    inme_hizi_delta += (fuzzy_factor * inme_carpan)

    current_time = time.time()
    if current_time - last_modbus_write_time < speed_adjustment_interval:
        return serit_motor_akim_a, fuzzy_factor, akim_degisim, last_modbus_write_time

    speed_buffer.add_to_buffer(kesme_hizi_delta, inme_hizi_delta)

    if speed_buffer.adjust_and_check():
        kesme_hizi_adjustment, inme_hizi_adjustment = speed_buffer.get_adjustments()
        new_serit_kesme_hizi = processed_speed_data['serit_kesme_hizi'] + kesme_hizi_adjustment
        new_serit_inme_hizi = processed_speed_data['serit_inme_hizi'] + inme_hizi_adjustment

        kesme_hizi_tracker.check_and_update_orani(new_serit_kesme_hizi)

        # Hızların oranını koruma
        ratio = (new_serit_inme_hizi / new_serit_kesme_hizi) * 100
        if ratio < (kesme_hizi_tracker.kesme_orani - 1.0):
            while ratio < (kesme_hizi_tracker.kesme_orani - 1.0):
                if fuzzy_factor < 0:
                    new_serit_kesme_hizi -= 0.1
                elif fuzzy_factor > 0:
                    new_serit_inme_hizi += 0.1
                ratio = (new_serit_inme_hizi / new_serit_kesme_hizi) * 100
        elif ratio > (kesme_hizi_tracker.kesme_orani + 1.0):
            while ratio > (kesme_hizi_tracker.kesme_orani + 1.0):
                if fuzzy_factor < 0:
                    new_serit_inme_hizi -= 0.1
                elif fuzzy_factor > 0:
                    new_serit_kesme_hizi += 0.1
                ratio = (new_serit_inme_hizi / new_serit_kesme_hizi) * 100

        print("KESME HIZI ORANI: ", ratio)

#         print("yeni kesme hız: ", new_serit_kesme_hizi)
        kesme_hizi_modbus_value = reverse_calculate_value(new_serit_kesme_hizi, 'serit_kesme_hizi')
#         print("hesaplanan kesme hız: ", kesme_hizi_modbus_value)
#         print("yeni inme hız: ", new_serit_inme_hizi)
        inme_hizi_modbus_value = reverse_calculate_value(new_serit_inme_hizi, 'serit_inme_hizi')
#         print("hesaplanan inme hız: ", inme_hizi_modbus_value)

        kesme_hizi_register_address = 2066
        inme_hizi_register_address = 2041

        inme_hizi_is_negative = new_serit_inme_hizi < 0
        write_to_modbus(modbus_client, kesme_hizi_register_address, kesme_hizi_modbus_value)
        write_to_modbus(modbus_client, inme_hizi_register_address, inme_hizi_modbus_value, inme_hizi_is_negative)

        last_modbus_write_time = current_time

    return serit_motor_akim_a, fuzzy_factor, akim_degisim, last_modbus_write_time


def write_to_modbus(modbus_client, address, value, is_negative=False):
    if address == 2041:
        if not is_negative:
            sign_bit = 1 << 15
        else:
            sign_bit = 0

        modbus_value = sign_bit | value & 0x7FFF
        modbus_client.write_register(address, modbus_value)

    elif address == 2066:
        modbus_client.write_register(address, value)
