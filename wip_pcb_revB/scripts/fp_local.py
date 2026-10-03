import pcbnew, sys
b=pcbnew.LoadBoard(sys.argv[1])
for fp in b.GetFootprints():
    r=fp.GetReference()
    if r not in sys.argv[2].split(','): continue
    fp.SetOrientationDegrees(0)
    c=fp.GetBoundingBox(False).GetCenter(); bb=fp.GetBoundingBox(False)
    print(f'== {r} {fp.GetFPID().GetLibItemName()} size {pcbnew.ToMM(bb.GetWidth()):.2f}x{pcbnew.ToMM(bb.GetHeight()):.2f}')
    rows={}
    for p in fp.Pads():
        q=p.GetPosition(); n=p.GetNetname().split('/')[-1]
        rows.setdefault(n,[]).append(f'{p.GetNumber()}({pcbnew.ToMM(q.x-c.x):.2f},{pcbnew.ToMM(q.y-c.y):.2f})')
    for n,l in sorted(rows.items()): print('   ',n[:16].ljust(16),' '.join(l[:6]))
