import pcbnew, sys
b=pcbnew.LoadBoard(sys.argv[1]); OX=OY=50.0
big=('U','Q','J','L','SW','D1','D2','R30','R50','R51','R52')
fps={f.GetReference():f for f in b.GetFootprints()}
netpads={}
for r,f in fps.items():
    for p in f.Pads():
        q=p.GetPosition(); netpads.setdefault(p.GetNetname(),[]).append((r,p.GetNumber(),round(pcbnew.ToMM(q.x)-OX,1),round(pcbnew.ToMM(q.y)-OY,1)))
def sz(f):
    bb=f.GetBoundingBox(False); return f'{pcbnew.ToMM(bb.GetWidth()):.1f}x{pcbnew.ToMM(bb.GetHeight()):.1f}'
for r in sorted(fps, key=lambda s:(s.rstrip('0123456789'),int(''.join(c for c in s if c.isdigit()) or 0))):
    f=fps[r]
    if r.startswith(('H','FID')): continue
    nets=sorted({p.GetNetname() for p in f.Pads()})
    out=[]
    for n in nets:
        if n in ('GND','') : out.append(n or 'nc'); continue
        others=[x for x in netpads[n] if x[0]!=r]
        out.append(f"{n.split('/')[-1]}->"+(",".join(f"{a}.{p}" for a,p,_,_ in others[:5])+('..' if len(others)>5 else '')))
    print(f"{r:6s} {sz(f):9s} {f.GetValue()[:14]:14s} | "+' | '.join(out))
