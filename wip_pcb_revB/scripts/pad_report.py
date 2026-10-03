import pcbnew, sys
b=pcbnew.LoadBoard(sys.argv[1]); OX=OY=50.0
want=sys.argv[2].split(',')
for fp in b.GetFootprints():
    if fp.GetReference() in want:
        bb=fp.GetBoundingBox(False); c=bb.GetCenter()
        print(f'== {fp.GetReference()} center ({pcbnew.ToMM(c.x)-OX:.2f},{pcbnew.ToMM(c.y)-OY:.2f}) size {pcbnew.ToMM(bb.GetWidth()):.1f}x{pcbnew.ToMM(bb.GetHeight()):.1f}')
        rows={}
        for p in fp.Pads():
            q=p.GetPosition(); rows.setdefault(p.GetNetname(),[]).append((p.GetNumber(),round(pcbnew.ToMM(q.x)-OX,2),round(pcbnew.ToMM(q.y)-OY,2)))
        for n,l in sorted(rows.items()): print('   ',n.split('/')[-1][:18].ljust(18),l[:4])
