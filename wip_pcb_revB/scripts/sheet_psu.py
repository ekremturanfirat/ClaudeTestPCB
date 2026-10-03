"""Power Supply: LMR38020 buck to 3.3 V (TI SNVSC40E), ferrite-filtered +3V3_A rail."""
from parts import vcap, vres, pin_net, pull, G, R, FP_R0603
from sheet_mcu import testpoint, LED_G, FP_LED

BUCK = 'METUPowerLab_Regulators_BuckConverters:LMR38020FSDDAR'
IND = 'METUPowerLab_Inductors_SurfaceMounts:4.7µH'
FB = 'METUPowerLab_CircuitProtections_FerriteBeads:BLM18EG221SN1D'
FP_FB = 'METUPowerLab_CircuitProtections_FerriteBeads:0603_Medium'


def build(sh):
    u = sh.add('U4', BUCK, (101.6, 88.9))
    sh.group(u, ['VIN', 'EN'], '+VBUS_PROT', length=2)  # SNVSC40E: EN may tie directly to VIN
    pin_net(sh, u, 'RT/SYNC', 'BUCK_RT')
    sh.group(u, ['GND', 'Shield'], 'GND', length=2)
    pin_net(sh, u, 'BOOT', 'BUCK_BOOT')
    pin_net(sh, u, 'SW', 'BUCK_SW')
    pin_net(sh, u, 'FB', 'BUCK_FB')
    pin_net(sh, u, 'PG', 'BUCK_PG')
    # input caps (>= 4.7 uF effective, rated 2x VIN) + 100 nF at the pins
    vcap(sh, 'C20', '4.7 µF', (25.4, 45.72), '+VBUS_PROT')
    vcap(sh, 'C21', '100 nF 100V', (50.8, 45.72), '+VBUS_PROT')
    vres(sh, 'R20', '54.9 kOhm', (50.8, 106.68), 'BUCK_RT')          # ~480 kHz (SNVSC40E Eq. 2)
    vcap(sh, 'C22', '100 nF', (160.02, 50.8), 'BUCK_BOOT', 'BUCK_SW')  # CBOOT 0.1 uF, >= 16 V
    l1 = sh.add('L1', IND, (175.26, 76.2))
    sh.conn(l1, '1', 'BUCK_SW', style='label', length=1, jog=-1)
    sh.power_turn(l1, '2', '+3V3_MCU', out=2, turn=2)
    # output caps + feedback divider: Vout = 1.0 V x (1 + 110k / 47k) = 3.34 V
    vcap(sh, 'C23', '47 µF', (200.66, 88.9), '+3V3_MCU')
    vcap(sh, 'C24', '47 µF', (220.98, 88.9), '+3V3_MCU')
    vcap(sh, 'C25', '100 nF', (241.3, 88.9), '+3V3_MCU')
    vres(sh, 'R21', '110 kOhm', (175.26, 109.22), '+3V3_MCU', 'BUCK_FB')
    vres(sh, 'R22', '47 kOhm', (175.26, 134.62), 'BUCK_FB')
    pull(sh, 'R23', '100 kOhm', (200.66, 124.46), 'BUCK_PG', '+3V3_MCU')
    # +3V3_A: ferrite-filtered analog rail (DRV8323 VREF, INA240, TMP235)
    fb = sh.add('FB1', FB, (38.1, 139.7), footprint=FP_FB)
    sh.power_turn(fb, '1', '+3V3_MCU', out=3, turn=2)
    sh.power_turn(fb, '2', '+3V3_A', out=3, turn=2)
    vcap(sh, 'C26', '10 µF', (63.5, 142.24), '+3V3_A')
    vcap(sh, 'C27', '100 nF', (83.82, 142.24), '+3V3_A')
    # power LED
    r = sh.add('R24', R + '1 kOhm', (116.84, 139.7), footprint=FP_R0603)
    sh.power_turn(r, '1', '+3V3_MCU', out=2, turn=2)
    d = sh.add('D20', LED_G, (137.16, 139.7), footprint=FP_LED)
    sh.wire(r.pin_pos(r.pins('2')[0]), d.pin_pos(d.pins('1')[0]))
    r.pin_net['2'] = {'PWR_LED_A'}
    d.pin_net['1'] = {'PWR_LED_A'}
    sh.conn(d, '2', 'GND', style='power', length=1)
    for i, (net, x) in enumerate((('+3V3_MCU', 213.36), ('+3V3_A', 236.22), ('BUCK_PG', 259.08), ('GND', 279.4))):
        testpoint(sh, f'TP{20 + i}', net, (x, 147.32))
    sh.flag_net('+3V3_MCU', (218.44, 50.8))
    sh.flag_net('+3V3_A', (218.44, 63.5))
    sh.text('LAYOUT: C21 (100 nF) and C20 right at U4 VIN/GND, smallest input loop (SNVSC40E 9.5).\n'
            'LAYOUT: C22 close to BOOT/SW with short wide traces. Keep the SW node (U4 pin 8 - L1) small.\n'
            'LAYOUT: R21/R22 at the FB pin; route the 3V3 sense line away from SW.\n'
            'LAYOUT: Thermal pad: >= 4x3 via array to GND.',
            (12.7, 162.56))
