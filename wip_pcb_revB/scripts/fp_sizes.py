import pcbnew, sys, collections
from kisexp import load, kids, kid, val
LIB='C:/Users/ekrem/Documents/KiCad/10.0/3rdparty/footprints/METUPowerLab_kicad_library/'
nl=load('esc_new/net.net')
comps=kids(kid(nl,'components'),'comp')
seen={}
for c in comps:
    fp=str(val(c,'footprint')); ref=str(val(c,'ref'))
    seen.setdefault(fp,[]).append(ref)
for fp,refs in sorted(seen.items()):
    lib,name=fp.split(':',1)
    m=pcbnew.FootprintLoad(LIB+lib+'.pretty',name)
    if m is None: print('LOAD FAIL',fp); continue
    bb=m.GetBoundingBox(False)   # without text
    print(f'{fp:70} {pcbnew.ToMM(bb.GetWidth()):6.2f} x {pcbnew.ToMM(bb.GetHeight()):6.2f}  n={len(refs):2} {",".join(refs[:6])}')
print('total components', len(comps))
