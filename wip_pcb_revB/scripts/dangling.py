"""Remove track segments with a free end (router leftovers, e.g. to a removed port via). A track end is
connected if it touches a same-net pad, via, other track end/body, or zone fill on its layer. Repeats until
nothing changes. Single board load. Usage: python.exe dangling.py <board>"""
import sys
import pcbnew
MM = pcbnew.FromMM
b = pcbnew.LoadBoard(sys.argv[1])
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
tracks = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
vias = [v for v in b.GetTracks() if v.Type() == pcbnew.PCB_VIA_T]
pads = [p for fp in b.GetFootprints() for p in fp.Pads()]
zones = [z for z in b.Zones() if not z.GetIsRuleArea()]
alive = set(range(len(tracks)))
removed = 0
while True:
    gone = []
    for i in alive:
        t = tracks[i]
        L, n = t.GetLayer(), t.GetNetCode()
        r = t.GetWidth() // 2                     # an end touches copper within half its own width
        for pt in (t.GetStart(), t.GetEnd()):
            ok = any(p.GetNetCode() == n and p.IsOnLayer(L) and p.HitTest(pt, r) for p in pads) \
                or any(v.GetNetCode() == n and v.IsOnLayer(L) and v.HitTest(pt, r) for v in vias) \
                or any(j != i and tracks[j].GetNetCode() == n and tracks[j].GetLayer() == L and tracks[j].HitTest(pt, r)
                       for j in alive) \
                or any(z.GetNetCode() == n and z.IsOnLayer(L) and z.HitTestFilledArea(L, pt, r) for z in zones)
            if not ok:
                gone.append(i); break
    if not gone:
        break
    for i in gone:
        b.Remove(tracks[i]); alive.discard(i); removed += 1
b.Save(sys.argv[1])
print('dangling track segments removed:', removed)
