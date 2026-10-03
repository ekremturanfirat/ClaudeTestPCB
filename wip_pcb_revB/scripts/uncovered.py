import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1]); O = 50.0; T = pcbnew.ToMM
zones = {}
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname() == 'GND': continue
    zones.setdefault(z.GetNetname(), []).append(z)
for net, zl in zones.items():
    unc = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != net: continue
            cov = any(z.Outline().Collide(p.GetPosition()) or z.HitTestFilledArea(z.GetLayer(), p.GetPosition()) for z in zl)
            if not cov:
                q = p.GetPosition(); unc.append(f'{fp.GetReference()}.{p.GetNumber()}({T(q.x)-O:.1f},{T(q.y)-O:.1f})')
    print(net.split('/')[-1], ':', ' '.join(sorted(set(unc))))
