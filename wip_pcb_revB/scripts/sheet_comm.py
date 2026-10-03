"""Communication: SN65HVD230 CAN transceiver per TI SLOS346O."""
from parts import vcap, pin_net, G, R, FP_R0603
from sheet_mcu import testpoint

CAN = 'METUPowerLab_Interfaces_CANBusBridges:SN65HVD230DR'
TVS = 'METUPowerLab_Diodes_TVSDiodes:CDSOD323-T24SC'
JCAN = 'METUPowerLab_Connectors_SignalConnectors:384471-E'


def build(sh):
    u = sh.add('U10', CAN, (101.6, 106.68))
    pin_net(sh, u, 'VCC', '+3V3_MCU')
    sh.nc(u, 'VREF')                                   # SLOS346O 10.3.1: may be left floating
    pin_net(sh, u, 'D', 'CAN_TX', kind='global', shape='input')
    pin_net(sh, u, 'R', 'CAN_RX', kind='global', shape='output')
    sh.group(u, ['RS', 'GND'], 'GND', length=2)      # RS strong pull-down = high-speed mode
    pin_net(sh, u, 'CANH', 'CANH', length=4)
    pin_net(sh, u, 'CANL', 'CANL', length=4)
    vcap(sh, 'C60', '100 nF', (50.8, 55.88), '+3V3_MCU')
    # split termination (optional per TI 11.2.1.1): 2 x 56 Ohm + 4.7 nF to GND
    r1 = sh.add('R60', R + '56 Ohm', (160.02, 76.2), rot=270, footprint=FP_R0603)
    r2 = sh.add('R61', R + '56 Ohm', (160.02, 101.6), rot=270, footprint=FP_R0603)
    for p_, top, bot in ((r1, 'CANH', 'CAN_SPLIT'), (r2, 'CAN_SPLIT', 'CANL')):
        sh.conn(p_, '1', top, style='label', length=1)
        sh.conn(p_, '2', bot, style='label', length=1)
    vcap(sh, 'C61', '4.7 nF', (185.42, 88.9), 'CAN_SPLIT')
    # ESD: 24 V bidirectional TVS per line
    for ref, net, x in (('D60', 'CANH', 160.02), ('D61', 'CANL', 190.5)):
        d = sh.add(ref, TVS, (x, 134.62), rot=270)
        sh.conn(d, '1', net, style='label', length=1)
        sh.conn(d, '2', 'GND', style='power', length=1)
    # bus connector J8: 1 CANH, 2 CANL, 3 GND, 4 GND
    j = sh.add('J8', JCAN, (228.6, 99.06), value='CAN')
    sh.conn(j, '1', 'CANH', style='label', length=2)
    sh.conn(j, '2', 'CANL', style='label', length=2)
    sh.group(j, ['3', '4', 'Shield'], 'GND', length=2)
    testpoint(sh, 'TP60', 'CANH', (215.9, 147.32))
    testpoint(sh, 'TP61', 'CANL', (241.3, 147.32))
    sh.text('LAYOUT: C60 right at U10 VCC pin.\n'
            'LAYOUT: CANH/CANL as a tightly coupled pair to J8, same layer, no stubs.\n'
            'LAYOUT: D60/D61 at the connector, short path to GND. R60/R61/C61 near J8.',
            (12.7, 160.02))
