import math, collections
from sexp import *
B=load('D:/Belgeler/METUPowerLab/PCBDesignWClaude/hardware/ESC3Phase.kicad_pcb')
gen=kid(B,'general'); print('thickness',val(gen,'thickness'))
setup=kid(B,'setup')
for k in ['pad_to_mask_clearance','solder_mask_min_width','allow_soldermask_bridges_in_footprints']:
    print(k, val(setup,k))
st=kid(setup,'stackup')
if st: print('stackup layers',[ (val(l,'type'),val(l,'thickness')) for l in kids(st,'layer')], 'finish',val(st,'copper_finish'))
# footprints
fps=kids(B,'footprint'); print('footprints',len(fps))
libc=collections.Counter(f[1].split(':')[0] for f in fps); print('fp libs',dict(libc))
X0,Y0,X1,Y1=0,0,100,115
pos={}
for f in fps:
    P=props(f); ref=P['Reference']['value']; at=kid(f,'at')
    x,y=float(at[1]),float(at[2]); pos[ref]=(x,y,f)
# pads with absolute positions
def padabs(f):
    at=kid(f,'at'); fx,fy=float(at[1]),float(at[2]); fr=float(at[3]) if len(at)>3 else 0
    out=[]
    for p in kids(f,'pad'):
        pa=kid(p,'at'); px,py=float(pa[1]),float(pa[2])
        r=math.radians(-fr)  # KiCad y-down, rotation ccw
        ax=fx+px*math.cos(r)-py*math.sin(r); ay=fy+px*math.sin(r)+py*math.cos(r)
        net=kid(p,'net'); out.append((p[1],ax,ay,net[2] if net and len(net)>2 else (net[1] if net else ''), val(p,'size') ))
    return out
edge=[]
for ref,(x,y,f) in pos.items():
    for num,ax,ay,net,_ in padabs(f):
        d=min(ax-X0,X1-ax,ay-Y0,Y1-ay)
        if d<3.5 and not ref.startswith('MH'): edge.append((ref,round(d,2))); break
print('parts with pads < 3.5mm from edge:',sorted(set(edge)))
# decoupling distance: cap -> nearest IC pad on same non-GND net
ics=[r for r in pos if r.startswith('U')]
print('\nDECOUPLING / PASSIVE-TO-IC distances (cap pad -> nearest IC pad on same net):')
for ref in sorted(pos,key=lambda r:(r[0],int(''.join(c for c in r if c.isdigit()) or 0))):
    if not ref.startswith('C'): continue
    best=None
    for num,ax,ay,net,_ in padabs(pos[ref][2]):
        if 'GND' in net or not net: continue
        for u in ics:
            for n2,bx,by,net2,_ in padabs(pos[u][2]):
                if net2==net:
                    d=math.hypot(ax-bx,ay-by)
                    if best is None or d<best[0]: best=(d,u,n2,net)
    if best: print(f'  {ref:4} -> {best[1]}.{best[2]:3} net={best[3]:16} {best[0]:6.1f} mm', '  <-- FAR' if best[0]>5 else '')
# tracks
segs=kids(B,'segment'); vias=kids(B,'via'); arcs=kids(B,'arc')
print('\ntracks',len(segs),'vias',len(vias),'arcs',len(arcs))
bad=0; widths=collections.defaultdict(set)
for s in segs:
    a=kid(s,'start'); b=kid(s,'end'); dx=float(b[1])-float(a[1]); dy=float(b[2])-float(a[2])
    ang=math.degrees(math.atan2(dy,dx))%45
    if min(ang,45-ang)>0.5: bad+=1
    widths[val(s,'net')].add(val(s,'width'))
print('track segments not on 0/45/90 angles:',bad,'of',len(segs))
# zones / keepouts
for z in kids(B,'zone'):
    ko=kid(z,'keepout'); print('zone net=',val(z,'net_name'),'layers=',val(z,'layer') or kid(z,'layers')[1:],'keepout=' ,ko[1:] if ko else None, 'priority',val(z,'priority'))
for f in fps:
    for z in kids(f,'zone'):
        ko=kid(z,'keepout'); print('  footprint',props(f)['Reference']['value'],'zone keepout',ko[1:] if ko else None)
# texts on board
print('\nboard gr_text:',[ (t[1][:40],val(t,'layer')) for t in kids(B,'gr_text')])
print('images/logos:',len(kids(B,'image')))
fid=[r for r in pos if r.startswith('FID')]; tp=[r for r in pos if r.startswith('TP')]
print('fiducials:',fid,' test points:',tp)
for r in ['MH1']:
    f=pos[r][2]; print('MH pad types',[ (p[2],val(p,'drill')) for p in kids(f,'pad')])
# silkscreen ref sizes
small=[]
for ref,(x,y,f) in pos.items():
    for p in kids(f,'property'):
        if p[1]=='Reference':
            eff=kid(p,'effects'); font=kid(eff,'font') if eff else None; size=kid(font,'size') if font else None
            if size and float(size[1])<1.0: small.append((ref,size[1]))
print('ref designators < 1.0mm:',small)
