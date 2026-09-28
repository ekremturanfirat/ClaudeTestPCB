"""After routing: GND fill on L3 (In2) and stitching vias between the GND layers, then refill all zones.
Usage: python.exe finish_copper.py <board>
"""
import sys, math
import pcbnew
import placement as PL

MM, T = pcbnew.FromMM, pcbnew.ToMM
O = 50.0


def main(path):
    b = pcbnew.LoadBoard(path)
    gnd = b.FindNet('GND')
    allv = [v for v in b.GetTracks() if v.Type() == pcbnew.PCB_VIA_T]   # stale stitching vias (from an older
    dropped = 0                                                          # routing session) next to a newer via
    for v in allv:
        if v.GetNetname() == 'GND' and not v.IsLocked():
            p = v.GetPosition()
            if any(w is not v and (w.GetPosition() - p).EuclideanNorm() < MM(0.9) for w in allv
                   if w.GetNetname() == 'GND' and (w.IsLocked() or id(w) < id(v))):
                b.Remove(v); dropped += 1
    print('stale stitching vias dropped:', dropped)
    ports = {(round(O + PL.XC[ph] + 4.5, 2), round(O + 57.2, 2)) for ph in ('A', 'C')}   # old router ports, unused
    for v in [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]:
        if (round(T(v.GetPosition().x), 2), round(T(v.GetPosition().y), 2)) in ports:
            b.Remove(v)
    if not any(z.GetLayer() == pcbnew.In2_Cu and z.GetNetname() == 'GND' for z in b.Zones()):
        z = pcbnew.ZONE(b)
        z.SetLayer(pcbnew.In2_Cu); z.SetNet(gnd); z.SetZoneName('GND fill L3')
        ol = z.Outline(); ol.NewOutline()
        for x, y in ((0.3, 0.3), (PL.W - 0.3, 0.3), (PL.W - 0.3, PL.H - 0.3), (0.3, PL.H - 0.3)):
            ol.Append(MM(O + x), MM(O + y))
        z.SetAssignedPriority(0); z.SetMinThickness(MM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(MM(0.5)); z.SetThermalReliefSpokeWidth(MM(0.5))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        b.Add(z)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())

    # stitching vias (rule 3.4: ~5 mm grid, denser at the edges) where all four GND layers are filled
    fills = [z for z in b.Zones() if z.GetNetname() == 'GND' and not z.GetIsRuleArea()]
    layers = {pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu}
    items = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            bb = p.GetBoundingBox(); items.append((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())))
    for t in b.GetTracks():
        bb = t.GetBoundingBox(); items.append((T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())))
    for h in PL.HOLES:
        items.append((O + h[0] - 3.6, O + h[1] - 3.6, O + h[0] + 3.6, O + h[1] + 3.6))
    for f in PL.FIDUCIALS:
        items.append((O + f[0] - 1.6, O + f[1] - 1.6, O + f[0] + 1.6, O + f[1] + 1.6))

    def free(x, y, c=1.0):                            # via radius + HV clearance + margin
        return all(not (x - c < a1 and a0 < x + c and y - c < b1 and b0 < y + c) for a0, b0, a1, b1 in items)

    def filled_all(x, y):
        pt = pcbnew.VECTOR2I(MM(x), MM(y))
        got = {z.GetLayer() for z in fills if z.HitTestFilledArea(z.GetLayer(), pt, MM(0.45))}
        return layers <= got

    n = 0
    pts = []
    for gx in [i * 5.0 + 2.5 for i in range(int(PL.W // 5))]:
        for gy in [j * 5.0 + 2.5 for j in range(int(PL.H // 5))]:
            pts.append((gx, gy))
    for gx in [i * 2.5 + 1.5 for i in range(int((PL.W - 2) // 2.5) + 1)]:          # edges
        pts += [(gx, 1.5), (gx, PL.H - 1.5)]
    for gy in [j * 2.5 + 1.5 for j in range(int((PL.H - 2) // 2.5) + 1)]:
        pts += [(1.5, gy), (PL.W - 1.5, gy)]
    for bx, by in pts:
        x, y = O + bx, O + by
        if free(x, y) and filled_all(x, y):
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(gnd)
            b.Add(v); items.append((x - 0.3, y - 0.3, x + 0.3, y + 0.3)); n += 1
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(path)
    print(f'L3 GND fill added, {n} stitching vias')


if __name__ == '__main__':
    main(sys.argv[1])
