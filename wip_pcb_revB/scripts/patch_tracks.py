"""Replace hand-routed tracks whose geometry changed after the routing session was made (SES carries the old
copy). Usage: python.exe patch_tracks.py <board>"""
import sys
import pcbnew
MM, T = pcbnew.FromMM, pcbnew.ToMM
O = 50.0
PATCHES = [  # (net, old points, new points, width)
    ('VIN_RAW', [(32.53, 71.5), (31.78, 72.0), (31.78, 72.9), (31.03, 73.4)],
     [(32.53, 71.5), (31.78, 72.25), (31.78, 72.65), (31.03, 73.4)], 0.3),
]
b = pcbnew.LoadBoard(sys.argv[1])
for net, old, new, w in PATCHES:
    olds = {(round(x, 2), round(y, 2)) for x, y in old[1:-1]}
    gone = 0
    for t in list(b.GetTracks()):
        if t.Type() == pcbnew.PCB_TRACE_T and t.GetNetname() == net:
            pts = {(round(T(p.x) - O, 2), round(T(p.y) - O, 2)) for p in (t.GetStart(), t.GetEnd())}
            if pts & olds:
                b.Remove(t); gone += 1
    n = b.FindNet(net)
    for (x0, y0), (x1, y1) in zip(new, new[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(MM(O + x0), MM(O + y0))); t.SetEnd(pcbnew.VECTOR2I(MM(O + x1), MM(O + y1)))
        t.SetWidth(MM(w)); t.SetLayer(pcbnew.F_Cu); t.SetNet(n); t.SetLocked(True); b.Add(t)
    print(f'patched {net}: removed {gone}, added {len(new) - 1}')
b.Save(sys.argv[1])
