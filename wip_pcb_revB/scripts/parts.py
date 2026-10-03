"""Library part shortcuts + small placement helpers used by the sheet builders."""
import schgen

G = schgen.G
R = 'METUPowerLab_Resistors_ChipResistors:'
C = 'METUPowerLab_Capacitors_Ceramics_SurfaceMounts:'
GLOBAL_NETS = set()
POWER_NETS = {'GND', '+VBUS', '+VBUS_PROT', '+VBUS_EFUSE', '+3V3_MCU', '+3V3_A', 'VIN_RAW'}
GLOBAL_NETS.add('EFUSE_NFLT')

FP_R0603 = 'METUPowerLab_Resistors_ChipResistors:0603_Medium'
FP_C = {'0603': 'METUPowerLab_Capacitors_Ceramics_SurfaceMounts:0603_Medium',
        '0805': 'METUPowerLab_Capacitors_Ceramics_SurfaceMounts:0805_Medium',
        '1206': 'METUPowerLab_Capacitors_Ceramics_SurfaceMounts:1206_Medium',
        '1210': 'METUPowerLab_Capacitors_Ceramics_SurfaceMounts:1210_Medium',
        '2220': 'METUPowerLab_Capacitors_Ceramics_SurfaceMounts:2220'}


def cap_fp(value):
    import schlib
    pkg = schlib.get(C + value).props.get('Package', '')
    for k, fp in FP_C.items():
        if pkg.startswith(k):
            return fp
    raise ValueError(f'no footprint for cap {value!r} package {pkg!r}')


def _end(sh, part, pin, net, jog):
    if net in POWER_NETS:
        sh.conn(part, pin, net, style='power', length=1, jog=jog)
    else:
        kind = 'global' if net in GLOBAL_NETS else 'label'
        sh.conn(part, pin, net, style='label', kind=kind, shape='passive' if kind == 'global' else 'bidirectional',
                length=1, jog=jog)


HV_NETS = ('+VBUS', 'VIN', 'VCP', 'CPH', 'CPL')


def cap_value(value, nets):
    """Library value; add the voltage rating when the cap sits on a high-voltage net (rule 1.8)."""
    import schlib
    d = schlib.get(C + value)
    v = d.props.get('Value', value).strip()
    if any(n.startswith(HV_NETS) for n in nets):
        rating = d.props.get('Voltage Rating', '').strip()
        if rating and rating not in v:
            v = f'{v} {rating}'
    return v


def vcap(sh, ref, value, at, top, bottom='GND', jog=1):
    """Vertical ceramic capacitor: pin 1 on top."""
    p = sh.add(ref, C + value, at, footprint=cap_fp(value), value=cap_value(value, (top, bottom)))
    _end(sh, p, '1', top, jog)
    _end(sh, p, '2', bottom, jog)
    return p


def vres(sh, ref, value, at, top, bottom='GND', jog=1):
    """Vertical 0603 resistor: pin 1 on top."""
    p = sh.add(ref, R + value, at, rot=270, footprint=FP_R0603)
    _end(sh, p, '1', top, jog)
    _end(sh, p, '2', bottom, jog)
    return p


def hres(sh, ref, value, at, left, right):
    p = sh.add(ref, R + value, at, footprint=FP_R0603)
    _end(sh, p, '1', left, -1)
    _end(sh, p, '2', right, 1)
    return p


def pin_net(sh, part, pin, net, kind='label', shape='bidirectional', length=2, which=None):
    """Connect an IC pin to a net: power symbol for rails, label otherwise (global if kind='global')."""
    if net in POWER_NETS:
        return sh.conn(part, pin, net, style='power', length=length, which=which)
    if kind == 'global':
        GLOBAL_NETS.add(net)
    return sh.conn(part, pin, net, style='label', kind=kind, shape=shape, length=length, which=which)


def pull(sh, ref, value, at, net, rail):
    """Horizontal resistor row: net label on the left, rail (power symbol) on the right."""
    p = sh.add(ref, R + value, at, footprint=FP_R0603)
    kind = 'global' if net in GLOBAL_NETS else 'label'
    sh.conn(p, '1', net, style='label', kind=kind, shape='passive' if kind == 'global' else 'bidirectional', length=1)
    sh.conn(p, '2', rail, style='power', length=3 if rail != 'GND' else 1)
    return p
