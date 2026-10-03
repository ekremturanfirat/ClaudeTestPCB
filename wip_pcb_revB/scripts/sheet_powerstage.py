"""Power Stage: DC-bus bulk capacitors, board temperature sensor, 3x Half Bridge sub-sheet."""
import schgen
from parts import vcap, pin_net, G, GLOBAL_NETS
from sheet_mcu import testpoint

AL = 'METUPowerLab_Capacitors_AluminumPolymers_ThroughHoles:100 µF'
FP_AL = 'METUPowerLab_Capacitors_AluminumPolymers_ThroughHoles:8.00x13.50mm'
TMP = 'METUPowerLab_Sensors_Temperature:TMP235A4DCKR'
HB_PINS = [('GH', 'input', 'L', 0), ('GL', 'input', 'L', 2), ('SH', 'bidirectional', 'R', 0),
           ('SP', 'passive', 'R', 2), ('SN', 'passive', 'R', 3)]


def build(sh, hb_sheet):
    syms = []
    for i, ph in enumerate('ABC'):
        x, y = 101.6, 40.64 + i * 38.1
        ss = schgen.SheetSymbol(sh, hb_sheet, f'Half Bridge {ph}', (x, y), (38.1, 15.24), HB_PINS, page=0)
        sh.sheets_syms.append(ss)
        for pname, shape, side, idx in HB_PINS:
            p = ss.pin_point(pname)
            d = -1 if side == 'L' else 1
            e = (round(p[0] + d * G * 3, 4), p[1])
            sh.wire(p, e)
            net = {'GH': f'GH{ph}', 'GL': f'GL{ph}', 'SH': f'PHASE_{ph}', 'SP': f'ISENSE_{ph}_P',
                   'SN': f'ISENSE_{ph}_N'}[pname]
            GLOBAL_NETS.add(net)
            sh.label(net, e, kind='global', shape='passive', angle=180 if side == 'L' else 0)
            ss.pin_nets = getattr(ss, 'pin_nets', {})
            ss.pin_nets[pname] = net
        syms.append(ss)
    # DC-bus bulk capacitance
    for ref, x in (('C56', 205.74), ('C57', 231.14)):
        c = sh.add(ref, AL, (x, 60.96), footprint=FP_AL, value='100 µF 63V')
        sh.conn(c, '1', '+VBUS_PROT', style='power', length=1)
        sh.conn(c, '2', 'GND', style='power', length=1)
    # board temperature sensor next to the power stage
    u = sh.add('U8', TMP, (205.74, 116.84))
    pin_net(sh, u, 'VDD', '+3V3_A', length=1)
    pin_net(sh, u, 'GND', 'GND', length=1)
    pin_net(sh, u, 'VOUT', 'TEMP_SENSE', kind='global', shape='output')
    vcap(sh, 'C58', '100 nF', (185.42, 124.46), '+3V3_A')
    testpoint(sh, 'TP50', '+VBUS_PROT', (218.44, 152.4))
    testpoint(sh, 'TP51', 'GND', (243.84, 152.4))
    sh.text('LAYOUT: C56/C57 between the half bridges, on the +VBUS_PROT / GND pours.\n'
            'LAYOUT: U8 close to the low-side MOSFETs (hottest parts), away from the shunts.',
            (12.7, 165.1))
    return syms
