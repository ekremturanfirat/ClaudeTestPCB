"""Current Sensing: DC-bus shunt + INA240A1 (TI SBOS662C), unidirectional, Kelvin via net ties.

Gain 20 V/V x 5 mOhm = 100 mV/A -> 1.5 V at 15 A (usable <= 3.1 V on a 3.3 V supply).
"""
from parts import vcap, pin_net, G

SHUNT = 'METUPowerLab_Resistors_ShuntResistors:5 mOhm '
NT = 'METUPowerLab_NetTies_SurfaceMounts:NetTie_2_0.5mm'
INA = 'METUPowerLab_Amplifiers_CurrentSenses:INA240A1DR'
FP_SHUNT = 'METUPowerLab_Resistors_ShuntResistors:2010'


def build(sh):
    rs = sh.add('R30', SHUNT, (101.6, 60.96), footprint=FP_SHUNT)
    force1, force2 = [p for p in rs.pins('1') if p['ang'] == 0][0], [p for p in rs.pins('2') if p['ang'] == 180][0]
    sense1, sense2 = [p for p in rs.pins('1') if p['ang'] == 90][0], [p for p in rs.pins('2') if p['ang'] == 90][0]
    sh.power_turn(rs, '1', '+VBUS_EFUSE', out=2, turn=2) if False else None
    # force pins -> power rails (stub out, turn up)
    for pin, net, idx in ((force1, '+VBUS_EFUSE', 0), (force2, '+VBUS_PROT', 1)):
        tip = rs.pin_pos(pin)
        dx, dy = rs.pin_out(pin)
        end = (round(tip[0] + dx * G * 2, 4), tip[1])
        top = (end[0], round(end[1] - G * 2, 4))
        sh.path([tip, end, top])
        sh.power_symbol(net, top)
        rs.pin_net.setdefault(pin['number'], set()).add(net)
    # Kelvin taps -> net ties -> INA240 inputs
    nt_p = sh.add('NT1', NT, (91.44, 78.74), rot=270)
    nt_n = sh.add('NT2', NT, (111.76, 78.74), rot=270)
    for pin, nt, x in ((sense1, nt_p, 91.44), (sense2, nt_n, 111.76)):
        tip = rs.pin_pos(pin)
        ntp1 = nt.pin_pos(nt.pins('1')[0])
        net = '+VBUS_EFUSE' if nt is nt_p else '+VBUS_PROT'
        sh.path([tip, (tip[0], 68.58), (x, 68.58), ntp1])
        sh.power_symbol(net, (x, 68.58))
        nt.pin_net['1'] = {net}
        rs.pin_net.setdefault(pin['number'], set()).add(net)
    sh.conn(nt_p, '2', 'IBUS_SNS_P', style='label', length=1, jog=1)
    sh.conn(nt_n, '2', 'IBUS_SNS_N', style='label', length=1, jog=1)

    u = sh.add('U9', INA, (165.1, 104.14), fields={'_rv': (172.72, 95.25, 172.72, 97.79)})
    pin_net(sh, u, '8', 'IBUS_SNS_P')
    pin_net(sh, u, '1', 'IBUS_SNS_N')
    pin_net(sh, u, '6', '+3V3_A', length=1)
    sh.group(u, ['2', '3', '7'], 'GND', length=1)
    u.pin_net.setdefault('4', set()).add('GND')        # pin 4 (NC) stacked on GND in the library symbol
    pin_net(sh, u, '5', 'IBUS_SENSE', kind='global', shape='output')
    vcap(sh, 'C30', '100 nF', (137.16, 81.28), '+3V3_A')
    sh.flag_net('+VBUS_PROT', (205.74, 60.96))
    sh.text('LAYOUT: R30 in the +VBUS_EFUSE -> +VBUS_PROT pour, full width.\n'
            'LAYOUT: Kelvin: NT1/NT2 at the R30 pads; route IBUS_SNS_P/N as a tight pair to U9.\n'
            'LAYOUT: C30 right at U9 V+ (pin 6).',
            (12.7, 160.02))
