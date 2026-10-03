"""MCU Core: ESP32-WROOM-32E per Espressif datasheet v2.1 / hardware design guidelines."""
from parts import vcap, vres, pin_net, pull, G, R, FP_R0603, cap_fp, C, GLOBAL_NETS
import parts

ESP = 'METUPowerLab_Microcontrollers_ESP32:ESP32-WROOM-32E'
SW = 'METUPowerLab_Switches_TactileSwitches:TL6330AF200Q'
J1x4 = 'METUPowerLab_Connectors_SignalConnectors:2147210040'
JEXP = 'METUPowerLab_Connectors_SignalConnectors:384471-E'
LED_G = 'METUPowerLab_LEDs_SurfaceMounts:Green '
TP = 'METUPowerLab_TestPoints_SurfaceMounts:TestPoint_Pad'
FP_LED = 'METUPowerLab_LEDs_SurfaceMounts:0603_Medium'
FP_TP = 'METUPowerLab_TestPoints_SurfaceMounts:Pad_D1.5mm'


def testpoint(sh, ref, net, at):
    tp = sh.add(ref, TP, at, footprint=FP_TP, value=net)
    kind = 'global' if net in GLOBAL_NETS else 'label'
    if net == 'GND':
        sh.conn(tp, '1', net, style='power', length=1)
    elif net in parts.POWER_NETS:            # rail: go down, then sideways, arrow clear of the TP circle
        (end, _, pin), = sh.stub(tp, '1', 1)
        tp.pin_net.setdefault('1', set()).add(net)
        side = (round(end[0] - G * 3, 4), end[1])
        sh.wire(end, side)
        sh.power_symbol(net, side)
    else:
        sh.conn(tp, '1', net, style='label', kind=kind, shape='passive' if kind == 'global' else 'bidirectional',
                length=1, jog=-1)
    return tp


def build(sh):
    u = sh.add('U1', ESP, (139.7, 101.6))
    # ---- left side ----
    pin_net(sh, u, '2', '+3V3_MCU')
    pin_net(sh, u, 'EN', 'EN')
    pin_net(sh, u, '1', 'GND', length=1)
    for pin, net, shp in [('SENSOR_VP', 'IBUS_SENSE', 'input'), ('SENSOR_VN', 'TEMP_SENSE', 'input'),
                          ('IO34', 'ISENSE_C', 'input'), ('IO35', 'EFUSE_NFLT', 'input'),
                          ('IO32', 'ISENSE_A', 'input'), ('IO33', 'ISENSE_B', 'input'),
                          ('IO14', 'DRV_ENABLE', 'output'), ('IO12', 'PWM_BL', 'output'),
                          ('IO13', 'PWM_AH', 'output')]:
        pin_net(sh, u, pin, net, kind='global', shape=shp)
    pin_net(sh, u, 'IO25', 'EXP1')
    pin_net(sh, u, 'IO26', 'EXP2')
    pin_net(sh, u, 'IO27', 'LED_STATUS')
    sh.group(u, ['15', '39'], 'GND', length=2)
    # ---- right side ----
    for pin, net, shp in [('IO15', 'NFAULT', 'input'), ('IO2', 'PWM_AL', 'output'), ('IO4', 'PWM_BH', 'output'),
                          ('IO16', 'PWM_CH', 'output'), ('IO17', 'PWM_CL', 'output'), ('IO5', 'SPI_NSCS', 'output'),
                          ('IO18', 'SPI_SCLK', 'output'), ('IO19', 'SPI_SDO', 'input'), ('IO21', 'CAN_TX', 'output'),
                          ('IO22', 'CAN_RX', 'input'), ('IO23', 'SPI_SDI', 'output')]:
        pin_net(sh, u, pin, net, kind='global', shape=shp)
    pin_net(sh, u, 'IO0', 'BOOT')
    pin_net(sh, u, 'RXD0', 'UART_RXD')
    pin_net(sh, u, 'TXD0', 'UART_TXD')
    pin_net(sh, u, '38', 'GND', length=1)
    for n in ('17', '18', '19', '20', '21', '22', '32'):
        sh.nc(u, n)

    # ---- supply decoupling (DS fig. 9: 22 uF + 0.1 uF at 3V3) ----
    vcap(sh, 'C1', '22 µF', (25.4, 30.48), '+3V3_MCU')
    vcap(sh, 'C2', '100 nF', (45.72, 30.48), '+3V3_MCU')
    # ---- EN reset: 10k pull-up + 1 uF (DS sec. 9), RESET button ----
    vres(sh, 'R1', '10 kOhm', (25.4, 60.96), '+3V3_MCU', 'EN')
    vcap(sh, 'C3', '1 µF 0603', (45.72, 60.96), 'EN')
    s1 = sh.add('SW1', SW, (68.58, 58.42), value='RESET')
    sh.conn(s1, '1', 'EN', style='label', length=1)
    sh.conn(s1, '2', 'GND', style='power', length=1)
    # ---- IO0 boot strap: 10k pull-up, BOOT button to GND ----
    vres(sh, 'R2', '10 kOhm', (25.4, 83.82), '+3V3_MCU', 'BOOT')
    s2 = sh.add('SW2', SW, (68.58, 81.28), value='BOOT')
    sh.conn(s2, '1', 'BOOT', style='label', length=1)
    sh.conn(s2, '2', 'GND', style='power', length=1)
    # ---- ADC input filter caps (<=1 nF: INA240 / TMP235 max capacitive load) ----
    for i, net in enumerate(['IBUS_SENSE', 'TEMP_SENSE', 'ISENSE_A', 'ISENSE_B', 'ISENSE_C']):
        vcap(sh, f'C{4 + i}', '220 pF', (25.4 + i * 17.78, 121.92), net)

    # ---- UART / programming header J1: 1 +3V3, 2 TXD (ESP out), 3 RXD (ESP in), 4 GND ----
    j1 = sh.add('J1', J1x4, (210.82, 45.72), value='UART')
    sh.power_turn(j1, '1', '+3V3_MCU', out=2, turn=2)
    sh.conn(j1, '2', 'UART_TXD', style='label', length=2)
    sh.conn(j1, '3', 'UART_RXD', style='label', length=2)
    sh.group(j1, ['4', 'Shield'], 'GND', length=2)
    # ---- expansion header J2 (hall / encoder): 1 +3V3, 2 EXP1, 3 EXP2, 4 GND ----
    j2 = sh.add('J2', JEXP, (210.82, 83.82), value='EXPANSION')
    sh.power_turn(j2, '1', '+3V3_MCU', out=2, turn=2)
    sh.conn(j2, '2', 'EXP1', style='label', length=2)
    sh.conn(j2, '3', 'EXP2', style='label', length=2)
    sh.group(j2, ['4', 'Shield'], 'GND', length=2)
    # ---- status LED ----
    r = sh.add('R3', R + '1 kOhm', (205.74, 119.38), footprint=FP_R0603)
    sh.conn(r, '1', 'LED_STATUS', style='label', length=1)
    d = sh.add('D1', LED_G, (228.6, 119.38), footprint=FP_LED)
    sh.wire(r.pin_pos(r.pins('2')[0]), d.pin_pos(d.pins('1')[0]))
    r.pin_net['2'] = {'LED_A'}; d.pin_net['1'] = {'LED_A'}
    sh.conn(d, '2', 'GND', style='power', length=1)
    # ---- test points ----
    testpoint(sh, 'TP1', 'EN', (213.36, 149.86))
    testpoint(sh, 'TP2', 'BOOT', (238.76, 149.86))
    testpoint(sh, 'TP3', 'SPI_SCLK', (264.16, 149.86))

    sh.text('LAYOUT: Module antenna at the board edge, antenna outside the board or a cut-out\n'
            '        on both sides (Espressif HDG sec. 1.4.8). Keep copper, parts and traces out of the keepout.\n'
            'LAYOUT: C1/C2 right at U1 pin 2 (3V3), via to GND at the cap pad.\n'
            'LAYOUT: C3/R1 close to U1 pin 3 (EN). C4-C8 close to the ESP32 ADC pins.\n'
            'LAYOUT: Thermal pad (pin 39): via array to the GND plane.',
            (12.7, 142.24))
