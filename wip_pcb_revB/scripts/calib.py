import json, subprocess, os
from kisexp import dumps, Q
import schgen, schlib
S=schgen.Sheet('calib.kicad_sch','calib')
cases=[]
x=25.4
for rot in (0,90,180,270):
    for mir in (None,'x','y'):
        for lib in ('METUPowerLab_Resistors_ChipResistors:10 kOhm','METUPowerLab_Transistors_MOSFETs:NTMFS006N08MC'):
            ref=f"{'R' if 'Resist' in lib else 'Q'}{len(cases)+1}"
            p=S.add(ref,lib,(x,50.8 if 'Resist' in lib else 101.6),rot=rot,mirror=mir)
            cases.append(p)
        x+=20.32
def inst(sheet,ref,part): return [('/'+str(sheet.uuid),ref)]
open('calib/calib.kicad_sch','w',encoding='utf-8').write(dumps(S.node(S.uuid,'/',inst)))
cli=r'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
r=subprocess.run([cli,'sch','erc','--format','json','--severity-all','-o','calib/erc.json','calib/calib.kicad_sch'],capture_output=True,text=True)
print(r.stdout[-200:],r.stderr[-300:])
e=json.load(open('calib/erc.json',encoding='utf-8'))
got={}
import re
for sh in e['sheets']:
    for v in sh['violations']:
        if v['type']=='pin_not_connected':
            for it in v['items']:
                m=re.match(r'Symbol (\S+) Pin (\S+)',it['description'])
                if m: got[(m.group(1),m.group(2))]=(it["pos"]["x"]*100,it["pos"]["y"]*100)
bad=0;n=0
for p in cases:
    for pin in p.sym.pins:
        exp=p.pin_pos(pin); k=(p.ref,pin['number'])
        if k in got:
            n+=1
            g=got[k]
            if abs(g[0]-exp[0])>0.06 or abs(g[1]-exp[1])>0.06:
                bad+=1; print('MISMATCH',p.ref,p.rot,p.mirror,pin['number'],'exp',exp,'got',g)
print('checked',n,'mismatches',bad, 'units', e.get('coordinate_units'))
