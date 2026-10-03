"""Power copper for ESC3Phase (rules 3.3/3.5): pours for the high-current nets, GND on both layers,
no-pour areas around the Kelvin net ties, and named rule areas where the 0.6 mm HV clearance is relaxed to the
IC's own pin pitch (used by ESC3Phase.kicad_dru).

Usage: python.exe power.py <board>      (adds zones/areas in place; removes any previous ones first)
"""
import sys
import pcbnew
import placement as PL

MM = pcbnew.FromMM
FINAL = '--final' in sys.argv
O = 50.0
XC = PL.XC


def pt(x, y):
    return pcbnew.VECTOR2I(MM(O + x), MM(O + y))


def zone(board, net, layer, poly, prio, name='', full=True, thermal_gap=0.5, spoke=0.5):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    if net:
        z.SetNet(board.FindNet(net))
    ol = z.Outline()
    ol.NewOutline()
    for x, y in poly:
        ol.Append(MM(O + x), MM(O + y))
    z.SetAssignedPriority(prio)
    z.SetMinThickness(MM(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if full else pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(MM(thermal_gap))
    z.SetThermalReliefSpokeWidth(MM(spoke))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    if name:
        z.SetZoneName(name)
    board.Add(z)
    return z


def rule_area(board, name, poly, layers=('F.Cu', 'B.Cu'), no_pour=False):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetZoneName(name)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(board.GetLayerID(l))
    z.SetLayerSet(ls)
    z.SetDoNotAllowZoneFills(no_pour)
    z.SetDoNotAllowTracks(False)
    z.SetDoNotAllowVias(False)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in poly:
        ol.Append(MM(O + x), MM(O + y))
    board.Add(z)
    return z


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def fp_box(board, ref, grow):
    fp = board.FindFootprintByReference(ref)
    bb = fp.GetBoundingBox(False)
    T = pcbnew.ToMM
    return rect(T(bb.GetLeft()) - O - grow, T(bb.GetTop()) - O - grow, T(bb.GetRight()) - O + grow,
                T(bb.GetBottom()) - O + grow)


def build(board):
    for z in list(board.Zones()):
        board.Remove(z)
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    W, H = PL.W, PL.H

    # ---- +VBUS_PROT: band over the bridge, drain tabs, bulk-cap spur (top) ----
    band = [(26.75, 36.3), (97.0, 36.3), (97.0, 44.2)]
    for ph in ('C', 'B', 'A'):
        xc = XC[ph]
        band += [(xc + 3.2, 44.2), (xc + 3.2, 49.9), (xc - 3.2, 49.9), (xc - 3.2, 44.2)]
    band += [(42.3, 44.2), (42.3, 65.6), (38.3, 65.6), (38.3, 50.0), (36.5, 50.0), (36.5, 44.2), (26.75, 44.2)]
    zone(board, '+VBUS_PROT', F, band, 2, 'VBUS_PROT band')

    for ph in ('A', 'B', 'C'):
        xc = XC[ph]
        # phase node between the FETs, 5.6 mm lane on the left, terminal pads at the bottom edge
        zone(board, f'PHASE_{ph}', F,
             [(xc - 8.6, 50.6), (xc + 1.1, 50.6), (xc + 1.1, 53.4), (xc + 3.2, 53.4), (xc + 3.2, 60.6),
              (xc - 3.0, 60.6), (xc - 3.0, 77.4), (xc - 0.5, 77.4), (xc - 0.5, H - 0.5), (xc - 9.3, H - 0.5),
              (xc - 9.3, 77.4), (xc - 8.6, 77.4)], 2, f'PHASE_{ph}')
        # low-side source to the shunt's top pad
        zone(board, f'/Power Stage/Half Bridge {ph}/LS_SRC', F,
             [(xc - 2.6, 61.0), (xc + 1.1, 61.0), (xc + 1.1, 63.4), (xc + 1.9, 63.4), (xc + 1.9, 67.6),
              (xc - 2.3, 67.6)], 2, f'LS_SRC_{ph}')

    # ---- input chain (top): VIN_RAW -> Q1 -> +VBUS -> eFuse -> +VBUS_EFUSE -> R30 ----
    zone(board, 'VIN_RAW', F,
         [(17.6, 70.2), (19.2, 70.2), (19.2, 72.3), (26.8, 72.3), (26.8, 74.35), (29.6, 74.35), (29.6, 73.0),
          (31.25, 73.0), (31.25, 75.2), (31.6, 75.2), (31.6, 77.0), (27.2, 77.0), (27.2, H - 0.5),
          (17.9, H - 0.5), (17.9, 76.3), (17.4, 76.3), (17.4, 72.3), (17.6, 72.3)], 2, 'VIN_RAW')
    zone(board, '+VBUS', F,
         [(22.3, 62.0), (27.4, 62.0), (27.4, 57.5), (28.35, 57.5), (28.35, 58.75), (30.3, 58.75), (30.3, 61.6),
          (37.6, 61.6), (37.6, 66.2), (40.8, 66.2), (40.8, 69.4), (31.4, 69.4), (31.4, 71.5), (29.6, 71.5),
          (29.6, 69.4), (28.7, 69.4), (28.7, 71.7), (22.3, 71.7)], 2, 'VBUS')
    zone(board, '+VBUS_EFUSE', F,
         [(26.6, 46.6), (32.4, 46.6), (32.4, 50.9), (31.3, 50.9), (31.3, 53.4), (28.7, 53.4), (28.7, 55.9),
          (26.3, 55.9), (26.3, 50.6), (26.6, 50.6)], 2, 'VBUS_EFUSE')

    # ---- GND: both layers, whole board (lowest priority), thermal reliefs for hand soldering ----
    outline = rect(0.3, 0.3, W - 0.3, H - 0.3)
    zone(board, 'GND', F, outline, 0, 'GND top', full=False)
    zone(board, 'GND', B, outline, 0, 'GND bottom', full=False)
    zone(board, 'GND', pcbnew.In1_Cu, outline, 0, 'GND plane L2', full=False)
    if FINAL:
        zone(board, 'GND', pcbnew.In2_Cu, outline, 0, 'GND fill L3', full=False)

    # ---- no pour at the Kelvin net ties: taps are tracks from the shunt pad edge ----
    for ref in ('NT1', 'NT2', 'NT3', 'NT4', 'NT5', 'NT6', 'NT7', 'NT8'):
        rule_area(board, f'KELVIN_{ref}', fp_box(board, ref, 0.35), layers=('F.Cu',), no_pour=True)

    # ---- HV fan-out areas: the part's own pin pitch is below 0.6 mm (see ESC3Phase.kicad_dru) ----
    # U6: the gate-driver cluster between the DRV8323 and the bus band, including its CP/VCP/VM caps
    rule_area(board, 'HV_FANOUT_U6', rect(60.5, 19.5, 81.5, 36.0))
    for ref, grow in (('U3', 1.0), ('U2', 0.8), ('Q1', 0.3), ('U8', 0.6), ('U4', 3.0)):
        rule_area(board, f'HV_FANOUT_{ref}', fp_box(board, ref, grow))
    for ph, (qh, ql) in (('A', ('Q2', 'Q3')), ('B', ('Q4', 'Q5')), ('C', ('Q6', 'Q7'))):
        xc = XC[ph]
        for q, y in ((qh, 51.55), (ql, 61.95)):                 # gate pin next to the source pins
            rule_area(board, f'HV_FANOUT_{q}', rect(xc + 0.4, y - 1.1, xc + 3.2, y + 1.1))


if __name__ == '__main__':
    b = pcbnew.LoadBoard(sys.argv[1])
    build(b)
    filler = pcbnew.ZONE_FILLER(b)
    filler.Fill(b.Zones())
    b.Save(sys.argv[1])
    print('zones:', len(list(b.Zones())))
