import sys, collections, os
from sexp import *
H='D:/Belgeler/METUPowerLab/PCBDesignWClaude/hardware/'
sheets=['ESC3Phase','PowerSupply','MCUCore','GateDrive','PowerStage','CurrentSensing','Communication']
def ongrid(x,g=2.54): return abs(round(float(x)/g)*g-float(x))<0.01
libs=collections.Counter(); issues=collections.defaultdict(list)
allsyms=[]
for s in sheets:
    t=load(H+s+'.kicad_sch')
    paper=val(t,'paper'); tb=kid(t,'title_block')
    tbd={c[0]:c[1:] for c in tb[1:]} if tb else {}
    print(f'== {s}: paper={paper} title_block={ {k:v for k,v in tbd.items()} }')
    imgs=kids(t,'image'); print('   images:',len(imgs))
    texts=[x for x in kids(t,'text')]
    lay=[x[1] for x in texts if 'LAYOUT' in x[1]]
    print('   LAYOUT notes:',len(lay))
    for l in lay: print('     -',l.replace('\n',' ')[:110])
    gl=kids(t,'global_label'); ll=kids(t,'label'); hl=kids(t,'hierarchical_label')
    wires=kids(t,'wire'); junc=kids(t,'junction'); nc=kids(t,'no_connect')
    print(f'   wires={len(wires)} junctions={len(junc)} global_labels={len(gl)} local_labels={len(ll)} hier_labels={len(hl)} no_connects={len(nc)}')
    offg=[ (x[0],x[1]) for x in gl+ll+junc+nc if kid(x,'at') and not (ongrid(kid(x,'at')[1]) and ongrid(kid(x,'at')[2]))]
    for sym in kids(t,'symbol'):
        lib=val(sym,'lib_id'); P=props(sym); at=kid(sym,'at')
        ref=P.get('Reference',{}).get('value'); v=P.get('Value',{}).get('value')
        libs[lib.split(':')[0]]+=1
        vis=[k for k,p in P.items() if not p['hidden'] and k not in ('Reference','Value')]
        allsyms.append(dict(sheet=s,ref=ref,val=v,lib=lib,fp=P.get('Footprint',{}).get('value'),vis=vis,rot=at[3] if len(at)>3 else '0',x=at[1],y=at[2],ds=P.get('Datasheet',{}).get('value')))
        if not (ongrid(at[1],1.27) and ongrid(at[2],1.27)): offg.append(('symbol',ref))
    print('   off-grid items:',len(offg), offg[:8])
print()
print('LIBRARIES USED:',dict(libs))
print()
print('SYMBOLS (non-power):')
for a in sorted(allsyms,key=lambda a:(a['ref'] or '')):
    if a['lib'].startswith('power:'): continue
    print(f"  {a['ref']:6} {a['sheet']:15} {a['lib'].split(':')[1][:28]:28} val={a['val']!r:34} fp={(a['fp'] or '').split(':')[-1][:22]:22} visible_extra={a['vis']}")
print()
print('POWER-LIB SYMBOLS:')
for a in allsyms:
    if a['lib'].startswith('power:'): print(f"  {a['ref']} {a['lib']} val={a['val']} rot={a['rot']} sheet={a['sheet']}")
