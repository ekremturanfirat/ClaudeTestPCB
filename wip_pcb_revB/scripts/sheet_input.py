"""Power Input: connectors, TVS, reverse-polarity ideal diode (LM74700-Q1), eFuse (TPS16890).

LM74700-Q1 per TI SNOSD17G: ANODE/EN on the input, MOSFET source to input, drain to output,
CVCAP >= 0.1 uF between VCAP and ANODE.
TPS16890 per TI SLVSHO1A (standalone): VDD 150 Ohm/0.22 uF recommended (120 Ohm/100 nF used, nearest
library values), EN/UVLO 866k/118k -> 10.1 V rising (internal VIN_UV_FLT default 10.66 V dominates),
IMON 3.65k -> IOCP = 1 V / (18.18 uA/A x 3.65k) = 15.1 A, ILIM 1.33k (Eq. 25), IREF 1 nF, IMON 22 pF,
dVdT 100 nF -> 0.5 V/ms (inrush << 0.5 A startup limit), WP# to GND, ADDR0/1 open (addr 0x40).
"""
from parts import vcap, vres, pin_net, pull, G, R, FP_R0603
from sheet_mcu import testpoint

TERM = 'METUPowerLab_Connectors_ScrewTerminals:7770'
TVS = 'METUPowerLab_Diodes_TVSDiodes:SMBJ36CA-13-F'
LM = 'METUPowerLab_CircuitProtections_IdealDiodes:LM74700QDBVRQ1'
FET = 'METUPowerLab_Transistors_MOSFETs:NTMFS006N08MC'
EFUSE = 'METUPowerLab_CircuitProtections_eFuses:PTPS16890VMAR'


def build(sh):
    # ---- input connectors ----
    j3 = sh.add('J3', TERM, (17.78, 50.8), value='VIN+')
    sh.power_turn(j3, '1', 'VIN_RAW', out=2, turn=2)
    j4 = sh.add('J4', TERM, (17.78, 71.12), value='GND')
    sh.conn(j4, '1', 'GND', style='power', length=2)
    sh.flag_net('VIN_RAW', (254.0, 124.46))
    sh.flag_label('EFUSE_VDD', (254.0, 144.78))
    # ---- surge TVS + input cap ----
    d = sh.add('D10', TVS, (50.8, 60.96), rot=270)
    sh.conn(d, '1', 'VIN_RAW', style='power', length=1)
    sh.conn(d, '2', 'GND', style='power', length=1)
    vcap(sh, 'C10', '100 nF 100V', (78.74, 60.96), 'VIN_RAW')
    # ---- reverse polarity: Q1 source = input side ----
    q1 = sh.add('Q1', FET, (111.76, 50.8), rot=270, mirror='x')      # S left (input), D right, G down
    sh.power_turn(q1, 'S', 'VIN_RAW', out=2, turn=2)
    sh.power_turn(q1, 'D', '+VBUS', out=2, turn=2)
    pin_net(sh, q1, 'G', 'REVPOL_GATE', length=1)
    u2 = sh.add('U2', LM, (111.76, 88.9))
    sh.group(u2, ['ANODE', 'EN'], 'VIN_RAW', length=2)
    pin_net(sh, u2, 'GND', 'GND', length=1)
    pin_net(sh, u2, 'GATE', 'REVPOL_GATE')
    pin_net(sh, u2, 'CATHODE', '+VBUS')
    pin_net(sh, u2, 'VCAP', 'LM_VCAP')
    vcap(sh, 'C11', '100 nF', (86.36, 111.76), 'VIN_RAW', 'LM_VCAP')     # CVCAP between VCAP and ANODE
    sh.text('C11: VCAP-ANODE, <= 15 V (SNOSD17G)', (104.14, 114.3), size=1.0)
    vcap(sh, 'C12', '4.7 µF', (144.78, 60.96), '+VBUS')
    vcap(sh, 'C13', '100 nF 100V', (165.1, 60.96), '+VBUS')
    sh.flag_net('+VBUS', (254.0, 134.62))

    # ---- eFuse ----
    u3 = sh.add('U3', EFUSE, (210.82, 132.08))
    sh.group(u3, ['10', '22', '23', '24'], '+VBUS', length=2)
    pin_net(sh, u3, 'VDD', 'EFUSE_VDD')
    pin_net(sh, u3, 'EN/UVLO', 'EFUSE_EN')
    sh.nc(u3, 'SWEN')
    pin_net(sh, u3, 'SDA', 'EFUSE_SDA')
    pin_net(sh, u3, 'SCL', 'EFUSE_SCL')
    pin_net(sh, u3, 'GND', 'GND', length=1)
    sh.group(u3, ['7', '8'], '+VBUS_EFUSE', length=2)
    pin_net(sh, u3, 'PGOOD', 'EFUSE_PGOOD')
    pin_net(sh, u3, 'FLT', 'EFUSE_NFLT', kind='global', shape='output')
    pin_net(sh, u3, 'IMON', 'EFUSE_IMON')
    pin_net(sh, u3, 'ILIM', 'EFUSE_ILIM')
    pin_net(sh, u3, 'IREF', 'EFUSE_IREF')
    pin_net(sh, u3, 'dV/dT', 'EFUSE_DVDT')
    pin_net(sh, u3, 'WP#', 'GND', length=1)
    for n in ('17', 'AUX/EEDATA/_GPIO2', 'TEMP/EECLK/_GPIO1', 'ADDR0', 'ADDR1'):
        sh.nc(u3, n)
    # eFuse support parts (left column)
    vres(sh, 'R10', '120 Ohm', (25.4, 106.68), '+VBUS', 'EFUSE_VDD')
    vcap(sh, 'C14', '100 nF 100V', (25.4, 132.08), 'EFUSE_VDD')
    vres(sh, 'R11', '866 kOhm', (50.8, 106.68), '+VBUS', 'EFUSE_EN')
    vres(sh, 'R12', '118 kOhm', (50.8, 132.08), 'EFUSE_EN')
    vcap(sh, 'C15', '220 pF', (68.58, 132.08), 'EFUSE_EN')
    pull(sh, 'R13', '10 kOhm', (134.62, 127.0), 'EFUSE_SDA', '+3V3_MCU')
    pull(sh, 'R14', '10 kOhm', (134.62, 137.16), 'EFUSE_SCL', '+3V3_MCU')
    pull(sh, 'R15', '10 kOhm', (134.62, 147.32), 'EFUSE_PGOOD', '+3V3_MCU')
    pull(sh, 'R16', '10 kOhm', (134.62, 157.48), 'EFUSE_NFLT', '+3V3_MCU')
    # eFuse support parts (right column)
    vres(sh, 'R17', '3.65 kOhm', (261.62, 50.8), 'EFUSE_IMON')
    vcap(sh, 'C16', '22 pF', (279.4, 50.8), 'EFUSE_IMON')
    vres(sh, 'R18', '1.33 kOhm', (261.62, 76.2), 'EFUSE_ILIM')
    vcap(sh, 'C17', '1 nF ', (279.4, 76.2), 'EFUSE_IREF')
    vcap(sh, 'C18', '100 nF', (243.84, 50.8), 'EFUSE_DVDT')
    vcap(sh, 'C19', '10 µF 100V 1206', (193.04, 38.1), '+VBUS_EFUSE')
    for i, (net, x) in enumerate((('VIN_RAW', 33.02), ('+VBUS', 63.5), ('+VBUS_EFUSE', 93.98))):
        testpoint(sh, f'TP{10 + i}', net, (x, 157.48))
    testpoint(sh, 'TP13', 'EFUSE_PGOOD', (185.42, 157.48))
    sh.text('LAYOUT: D10 and C10 directly at J3/J4. Wide pours for VIN_RAW, +VBUS, +VBUS_EFUSE (up to 15 A).\n'
            'LAYOUT: C11 at U2 VCAP/ANODE. U2 close to Q1 gate/source.\n'
            'LAYOUT: C14 at U3 VDD, C16/C17/C18/R17/R18 at their U3 pins, returns to U3 GND.\n'
            'LAYOUT: U3 exposed pad is IN (not GND): via array into the +VBUS pour.',
            (12.7, 170.18))
