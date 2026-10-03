import pcbnew, sys
b=pcbnew.LoadBoard(sys.argv[1]); O=50.0; T=pcbnew.ToMM
for fp in b.GetFootprints():
    if fp.GetReference() not in sys.argv[2].split(','): continue
    print('==', fp.GetReference(), 'rot', fp.GetOrientationDegrees())
    rows={}
    for p in fp.Pads():
        bb=p.GetBoundingBox(); n=p.GetNetname().split('/')[-1]
        rows.setdefault((p.GetNumber(),n),[]).append((round(T(bb.GetLeft())-O,2),round(T(bb.GetTop())-O,2),round(T(bb.GetRight())-O,2),round(T(bb.GetBottom())-O,2)))
    for (num,n),l in rows.items():
        xs=[a for r in l for a in (r[0],r[2])]; ys=[a for r in l for a in (r[1],r[3])]
        print(f'   {num:>6} {n[:14]:14} n={len(l)} x {min(xs):.2f}..{max(xs):.2f} y {min(ys):.2f}..{max(ys):.2f}')
