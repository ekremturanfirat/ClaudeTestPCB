"""Gate Drive sheet: DRV8323RS per TI SLVSDJ3D (datasheet-verified connections)."""
import schgen
from parts import vcap, vres, pin_net, pull, G

DRV = 'METUPowerLab_MotorDrivers_BLDC:DRV8323RSRGZT'


def build(sh):
    u = sh.add('U6', DRV, (129.54, 132.08))

    # ---- left side ----
    pin_net(sh, u, 'VM', '+VBUS_PROT')
    pin_net(sh, u, 'VCP', 'VCP')
    pin_net(sh, u, 'nFAULT', 'NFAULT', kind='global', shape='output')
    pin_net(sh, u, 'ENABLE', 'DRV_ENABLE', kind='global', shape='input')
    pin_net(sh, u, 'CPH', 'CPH')
    pin_net(sh, u, 'CPL', 'CPL')
    pin_net(sh, u, 'DVDD', 'DVDD')
    for pin, net in [('INHA', 'PWM_AH'), ('INLA', 'PWM_AL'), ('INHB', 'PWM_BH'), ('INLB', 'PWM_BL'),
                     ('INHC', 'PWM_CH'), ('INLC', 'PWM_CL')]:
        pin_net(sh, u, pin, net, kind='global', shape='input')
    for pin, net, shp in [('SDI', 'SPI_SDI', 'input'), ('SDO', 'SPI_SDO', 'output'), ('SCLK', 'SPI_SCLK', 'input'),
                          ('nSCS', 'SPI_NSCS', 'input')]:
        pin_net(sh, u, pin, net, kind='global', shape=shp)
    (tip, _, _), = [(e[0], 0, 0) for e in sh.stub(u, 'CAL', 1)]
    u.pin_net.setdefault('34', set()).add('GND')
    sh.path([tip, (tip[0], 104.14), (104.14, 104.14)])
    sh.power_symbol('GND', (104.14, 104.14))
    for pin, net in [('SOC', 'ISENSE_C'), ('SOB', 'ISENSE_B'), ('SOA', 'ISENSE_A')]:
        pin_net(sh, u, pin, net, kind='global', shape='output')
    sh.group(u, ['PGND', 'DGND', 'AGND', 'BGND', 'Shield'], 'GND', length=2)

    # ---- right side ----
    pin_net(sh, u, 'VDRAIN', '+VBUS_PROT')
    for ph in 'ABC':
        pin_net(sh, u, f'GH{ph}', f'GH{ph}', kind='global', shape='output')
        pin_net(sh, u, f'SH{ph}', f'PHASE_{ph}', kind='global', shape='bidirectional')
        pin_net(sh, u, f'GL{ph}', f'GL{ph}', kind='global', shape='output')
        pin_net(sh, u, f'SP{ph}', f'ISENSE_{ph}_P', kind='global', shape='input')
        pin_net(sh, u, f'SN{ph}', f'ISENSE_{ph}_N', kind='global', shape='input')
    pin_net(sh, u, 'VREF', '+3V3_A')
    # integrated buck unused -> SLVSDJ3D Table 9-3: "All Pins: Tie to GND"
    sh.group(u, ['VIN', 'nSHD', 'CB', 'SW', 'FB'], 'GND', length=2)
    sh.nc(u, 'NC')   # pin 46: "float or GND"

    # ---- support parts (left column) ----
    x1, x2, x3 = 25.4, 50.8, 76.2
    vcap(sh, 'C40', '100 nF 100V', (x1, 38.1), '+VBUS_PROT')          # VM HF decoupling
    vcap(sh, 'C41', '10 µF 100V 1206', (x2, 38.1), '+VBUS_PROT')      # VM bulk
    vcap(sh, 'C42', '1 µF 0603', (x3, 38.1), '+VBUS_PROT', 'VCP')     # VCP -> VM, 1 uF
    vcap(sh, 'C43', '47 nF 100V', (x1, 66.04), 'CPH', 'CPL')         # charge-pump flying cap
    vcap(sh, 'C44', '1 µF 0603', (x2, 66.04), 'DVDD')                 # DVDD 1 uF to AGND
    vcap(sh, 'C45', '100 nF', (x3, 66.04), '+3V3_A')                   # VREF decoupling
    # pull-downs: PWM inputs + ENABLE default off (plus IO2/IO12 strap levels on the ESP32)
    for i, net in enumerate(['PWM_AH', 'PWM_AL', 'PWM_BH', 'PWM_BL', 'PWM_CH', 'PWM_CL', 'DRV_ENABLE']):
        pull(sh, f'R{40 + i}', '10 kOhm', (38.1, 93.98 + i * 10.16), net, 'GND')
    # pull-ups: open-drain nFAULT/SDO, nSCS idle-high (also ESP32 IO5 strap)
    for i, net in enumerate(['NFAULT', 'SPI_SDO', 'SPI_NSCS']):
        pull(sh, f'R{47 + i}', '10 kOhm', (83.82, 93.98 + i * 10.16), net, '+3V3_MCU')

    sh.text('LAYOUT: C40/C41 right at U6 VM pin, short wide path to PGND.\n'
            'LAYOUT: C42 (VCP-VM) and C43 (CPH-CPL) as close as possible to U6.\n'
            'LAYOUT: C44 at DVDD, C45 at VREF, both with short return to AGND.\n'
            'LAYOUT: Route GHx/SHx and GLx/PGND as tight pairs; minimize gate loops.\n'
            'LAYOUT: ISENSE_x_P/N as Kelvin pairs from the shunt net ties.\n'
            'LAYOUT: Thermal pad: via array to GND plane.',
            (12.7, 170.18), size=1.27)
    return u
