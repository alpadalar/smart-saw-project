import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


def create_fuzzy_system():
    """
    Fuzzy kontrol sistemini oluşturur.
    Akım ve akım değişimine bağlı olarak çıkış değişimini hesaplar.
    """
    # Giriş değişkenleri
    akim = ctrl.Antecedent(np.arange(10, 25.5, 0.5), 'akim')  # Akım aralığı
    akim_degisim = ctrl.Antecedent(np.arange(-10, 11, 1), 'akim_degisim')  # Akım değişimi aralığı

    # Çıkış değişkeni
    cikis_degisim = ctrl.Consequent(np.arange(-3, 4, 1), 'cikis_degisim')  # Çıkış değişimi aralığı

    # Akım için üyelik fonksiyonları
    akim['NB'] = fuzz.trapmf(akim.universe, [10, 10, 12.5, 14.5])  # Negatif Büyük
    akim['NK'] = fuzz.trimf(akim.universe, [12.5, 14.5, 16.5])  # Negatif Küçük
    akim['ideal'] = fuzz.trimf(akim.universe, [14.5, 16.5, 18.5])  # İdeal
    akim['PK'] = fuzz.trimf(akim.universe, [16.5, 18.5, 20.5])  # Pozitif Küçük
    akim['PB'] = fuzz.trapmf(akim.universe, [18.5, 20.5, 25, 25])  # Pozitif Büyük

    # Akım değişimi için üyelik fonksiyonları
    akim_degisim['NB'] = fuzz.trapmf(akim_degisim.universe, [-10, -10, -4, -2])  # Negatif Büyük
    akim_degisim['NK'] = fuzz.trimf(akim_degisim.universe, [-3, -2, -1])  # Negatif Küçük
    akim_degisim['Z'] = fuzz.trimf(akim_degisim.universe, [-2, 0, 2])  # Sıfır
    akim_degisim['PK'] = fuzz.trimf(akim_degisim.universe, [1, 2, 3])  # Pozitif Küçük
    akim_degisim['PB'] = fuzz.trapmf(akim_degisim.universe, [2, 4, 10, 10])  # Pozitif Büyük

    # Çıkış değişimi için üyelik fonksiyonları
    cikis_degisim['NB'] = fuzz.trimf(cikis_degisim.universe, [-3, -3, -2])  # Negatif Büyük
    cikis_degisim['NO'] = fuzz.trimf(cikis_degisim.universe, [-3, -2, -1])  # Negatif Orta
    cikis_degisim['NK'] = fuzz.trimf(cikis_degisim.universe, [-2, -1, 0])  # Negatif Küçük
    cikis_degisim['Z'] = fuzz.trimf(cikis_degisim.universe, [-1, 0, 1])  # Sıfır
    cikis_degisim['PK'] = fuzz.trimf(cikis_degisim.universe, [0, 1, 2])  # Pozitif Küçük
    cikis_degisim['PO'] = fuzz.trimf(cikis_degisim.universe, [1, 2, 3])  # Pozitif Orta
    cikis_degisim['PB'] = fuzz.trimf(cikis_degisim.universe, [2, 3, 3])  # Pozitif Büyük

    # Fuzzy kuralları
    rules = [
        ctrl.Rule(akim['NB'] & akim_degisim['NB'], cikis_degisim['PO']),
        ctrl.Rule(akim['NB'] & akim_degisim['NK'], cikis_degisim['PO']),
        ctrl.Rule(akim['NB'] & akim_degisim['Z'], cikis_degisim['PO']),
        ctrl.Rule(akim['NB'] & akim_degisim['PK'], cikis_degisim['PO']),
        ctrl.Rule(akim['NB'] & akim_degisim['PB'], cikis_degisim['PO']),
        ctrl.Rule(akim['NK'] & akim_degisim['NB'], cikis_degisim['PK']),
        ctrl.Rule(akim['NK'] & akim_degisim['NK'], cikis_degisim['PK']),
        ctrl.Rule(akim['NK'] & akim_degisim['Z'], cikis_degisim['PK']),
        ctrl.Rule(akim['NK'] & akim_degisim['PK'], cikis_degisim['PK']),
        ctrl.Rule(akim['NK'] & akim_degisim['PB'], cikis_degisim['PK']),
        ctrl.Rule(akim['ideal'] & akim_degisim['NB'], cikis_degisim['Z']),
        ctrl.Rule(akim['ideal'] & akim_degisim['NK'], cikis_degisim['Z']),
        ctrl.Rule(akim['ideal'] & akim_degisim['Z'], cikis_degisim['Z']),
        ctrl.Rule(akim['ideal'] & akim_degisim['PK'], cikis_degisim['Z']),
        ctrl.Rule(akim['ideal'] & akim_degisim['PB'], cikis_degisim['Z']),
        ctrl.Rule(akim['PK'] & akim_degisim['NB'], cikis_degisim['NK']),
        ctrl.Rule(akim['PK'] & akim_degisim['NK'], cikis_degisim['NK']),
        ctrl.Rule(akim['PK'] & akim_degisim['Z'], cikis_degisim['NK']),
        ctrl.Rule(akim['PK'] & akim_degisim['PK'], cikis_degisim['NK']),
        ctrl.Rule(akim['PK'] & akim_degisim['PB'], cikis_degisim['NK']),
        ctrl.Rule(akim['PB'] & akim_degisim['NB'], cikis_degisim['NO']),
        ctrl.Rule(akim['PB'] & akim_degisim['NK'], cikis_degisim['NO']),
        ctrl.Rule(akim['PB'] & akim_degisim['Z'], cikis_degisim['NO']),
        ctrl.Rule(akim['PB'] & akim_degisim['PK'], cikis_degisim['NO']),
        ctrl.Rule(akim['PB'] & akim_degisim['PB'], cikis_degisim['NO']),
    ]

    # Kontrol sistemi ve simülasyonu oluştur
    cikis_ctrl = ctrl.ControlSystem(rules)
    cikis_sim = ctrl.ControlSystemSimulation(cikis_ctrl)
    return cikis_sim


def fuzzy_output(cikis_sim, input_akim, input_akim_degisim):
    """
    Fuzzy sistemini kullanarak çıkış değerini hesaplar.
    :param cikis_sim: Fuzzy kontrol sistemi simülasyonu
    :param input_akim: Akım değeri
    :param input_akim_degisim: Akım değişimi değeri
    :return: Çıkış değişim değeri
    """
    cikis_sim.input['akim'] = input_akim
    cikis_sim.input['akim_degisim'] = input_akim_degisim
    cikis_sim.compute()
    return cikis_sim.output['cikis_degisim']
