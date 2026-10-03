"""Half Bridge (one sub-sheet, instantiated 3x): 2x NTMFS006N08MC, 2 mOhm shunt, Kelvin net ties.

Refs per instance (A, B, C) are given as lists.
"""
from parts import vcap, G, cap_value, cap_fp, C

FET = 'METUPowerLab_Transistors_MOSFETs:NTMFS006N08MC'
SHUNT = 'METUPowerLab_Resistors_ShuntResistors:2 mOhm'
NT = 'METUPowerLab_NetTies_SurfaceMounts:NetTie_2_0.5mm'
TERM = 'METUPowerLab_Connectors_ScrewTerminals:7770'

REFS = dict(QH=['Q2', 'Q4', 'Q6'], QL=['Q3', 'Q5', 'Q7'], RS=['R50', 'R51', 'R52'],
            NTP=['NT3', 'NT5', 'NT7'], NTN=['NT4', 'NT6', 'NT8'], J=['J5', 'J6', 'J7'],
            CB=['C50', 'C52', 'C54'], CH=['C51', 'C53', 'C55'])


def build(sh):
    qh = sh.add(REFS['QH'], FET, (101.6, 60.96))
    ql = sh.add(REFS['QL'], FET, (101.6, 91.44))
    # high side: D -> +VBUS_PROT, S -> PHASE ; low side: D -> PHASE, S -> LS_SRC
    (d_end, _, _), = sh.stub(qh, 'D', 1)
    qh.pin_net['3'] = {'+VBUS_PROT'}
    sh.power_symbol('+VBUS_PROT', d_end)
    s_tip = qh.pin_pos(qh.pins('S')[0])
    d2_tip = ql.pin_pos(ql.pins('D')[0])
    sh.wire(s_tip, d2_tip)                                    # switch node
    qh.pin_net['1'] = {'PHASE'}; ql.pin_net['3'] = {'PHASE'}
    node = (s_tip[0], 76.2)
    sh.junction(node)
    j = sh.add(REFS['J'], TERM, (132.08, 73.66), rot=180, value='PHASE', fields={'_rv': (129.54, 81.28, 129.54, 83.82)})
    jt = j.pin_pos(j.pins('1')[0])
    sh.wire(node, jt)
    j.pin_net['1'] = {'PHASE'}
    tap = (116.84, 76.2)
    sh.junction(tap)
    sh.path([tap, (116.84, 71.12), (121.92, 71.12)])
    sh.label('SH', (121.92, 71.12), kind='hier', shape='bidirectional', angle=0)
    sh.label('PHASE', (121.92, 76.2), kind='label', angle=0) if False else None
    # gates
    for q, pin_name, net in ((qh, 'G', 'GH'), (ql, 'G', 'GL')):
        (e, _, _), = sh.stub(q, pin_name, 2)
        q.pin_net['2'] = {net}
        sh.label(net, e, kind='hier', shape='input', angle=180)
    # low-side source -> shunt (rot 270: force pin 1 on top)
    rs = sh.add(REFS['RS'], SHUNT, (104.14, 114.3), rot=270)
    f1 = [p for p in rs.pins('1') if p['ang'] == 0][0]
    f2 = [p for p in rs.pins('2') if p['ang'] == 180][0]
    s1 = [p for p in rs.pins('1') if p['ang'] == 90][0]
    s2 = [p for p in rs.pins('2') if p['ang'] == 90][0]
    ls = ql.pin_pos(ql.pins('S')[0])
    f1t = rs.pin_pos(f1)
    mid = (ls[0], round((ls[1] + f1t[1]) / 2 / G) * G)
    mid = (mid[0], round(mid[1], 4))
    sh.wire(ls, mid); sh.wire(mid, f1t)
    sh.label('LS_SRC', mid, kind='label', angle=0)
    ql.pin_net['1'] = {'LS_SRC'}; rs.pin_net['1'] = {'LS_SRC'}
    f2t = rs.pin_pos(f2)
    g_end = (f2t[0], round(f2t[1] + G * 2, 4))
    sh.wire(f2t, g_end)
    sh.power_symbol('GND', g_end)
    rs.pin_net['2'] = {'GND'}
    # Kelvin taps through net ties to the hierarchical sense pins
    ntp = sh.add(REFS['NTP'], NT, (78.74, 106.68))
    ntn = sh.add(REFS['NTN'], NT, (78.74, 121.92))
    for sp, nt, y, hl, net1 in ((s1, ntp, 106.68, 'SP', 'LS_SRC'), (s2, ntn, 121.92, 'SN', 'GND')):
        tip = rs.pin_pos(sp)
        p2 = nt.pin_pos(nt.pins('2')[0])
        corner = (96.52, tip[1])
        midp = (99.06, tip[1])
        sh.path([tip, midp, corner, (96.52, y), p2])
        if net1 == 'GND':
            sh.power_symbol('GND', midp)
        else:
            sh.label(net1, corner, kind='label', angle=180)
        nt.pin_net['2'] = {net1}
        rs.pin_net.setdefault(sp['number'], set()).add(net1)
        (e, _, _), = sh.stub(nt, '1', 2)
        nt.pin_net['1'] = {hl}
        sh.label(hl, e, kind='hier', shape='passive', angle=180)
    # local hot-loop decoupling, right at the half bridge
    vcap(sh, REFS['CB'], '10 µF 100V 1206', (149.86, 96.52), '+VBUS_PROT')
    vcap(sh, REFS['CH'], '100 nF 100V', (170.18, 96.52), '+VBUS_PROT')
    sh.text('LAYOUT: Hot loop: C(10 uF)/C(100 nF) directly across high-side drain and\n'
            '        low-side source (shunt GND end); keep this loop as small as possible.\n'
            'LAYOUT: PHASE, +VBUS_PROT and GND as pours on both layers with via arrays (5-10 A).\n'
            'LAYOUT: Kelvin: net ties at the shunt pads, SP/SN as a tight pair to the DRV8323.\n'
            'LAYOUT: Short gate loops: GH with SH, GL with SN/GND return, no layer changes.\n'
            'LAYOUT: MOSFET drain pad: thermal vias, copper on both layers.',
            (12.7, 147.32))
