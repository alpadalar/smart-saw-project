import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl

# Fuzzy logic için girişlerin tanımlanması
akim = ctrl.Antecedent(np.arange(10, 29, 1), 'akim')
akim_degisim = ctrl.Antecedent(np.arange(-3, 4, 1), 'akim_degisim')

# Çıkışın tanımlanması
cikis_degisim = ctrl.Consequent(np.arange(-3, 4, 1), 'cikis_degisim')

# Üyelik fonksiyonlarının tanımlanması
akim['NB'] = fuzz.trimf(akim.universe, [10, 10, 18])
akim['NK'] = fuzz.trimf(akim.universe, [10, 18, 22])
akim['ideal'] = fuzz.trimf(akim.universe, [18, 20, 22])
akim['PK'] = fuzz.trimf(akim.universe, [18, 22, 28])
akim['PB'] = fuzz.trimf(akim.universe, [22, 28, 28])

akim_degisim['NB'] = fuzz.trimf(akim_degisim.universe, [-3, -3, -1])
akim_degisim['NK'] = fuzz.trimf(akim_degisim.universe, [-3, -1, 1])
akim_degisim['Z'] = fuzz.trimf(akim_degisim.universe, [-1, 0, 1])
akim_degisim['PK'] = fuzz.trimf(akim_degisim.universe, [-1, 1, 3])
akim_degisim['PB'] = fuzz.trimf(akim_degisim.universe, [1, 3, 3])

cikis_degisim['NB'] = fuzz.trimf(cikis_degisim.universe, [-3, -3, -2])
cikis_degisim['NO'] = fuzz.trimf(cikis_degisim.universe, [-3, -2, -1])
cikis_degisim['NK'] = fuzz.trimf(cikis_degisim.universe, [-2, -1, 0])
cikis_degisim['Z'] = fuzz.trimf(cikis_degisim.universe, [-1, 0, 1])
cikis_degisim['PK'] = fuzz.trimf(cikis_degisim.universe, [0, 1, 2])
cikis_degisim['PO'] = fuzz.trimf(cikis_degisim.universe, [1, 2, 3])
cikis_degisim['PB'] = fuzz.trimf(cikis_degisim.universe, [2, 3, 3])

# Kuralların tanımlanması
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

# Kuralların sisteme eklenmesi
cikis_ctrl = ctrl.ControlSystem(rules)
cikis_sim = ctrl.ControlSystemSimulation(cikis_ctrl)


def fuzzy_output(input_akim, input_akim_degisim):
    cikis_sim.input['akim'] = input_akim
    cikis_sim.input['akim_degisim'] = input_akim_degisim
    cikis_sim.compute()
    return cikis_sim.output['cikis_degisim']
