import sys, json, subprocess, importlib, collections
from kisexp import dumps
import schgen
CLI=r'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
mod=importlib.import_module(sys.argv[1]); title=sys.argv[2]
S=schgen.Sheet('ESC3Phase.kicad_sch',title)
mod.build(S)
open('esc_new/ESC3Phase.kicad_sch','w',encoding='utf-8').write(dumps(S.node(S.uuid,'/',lambda s,r,p:[('/'+str(s.uuid),r if isinstance(r,str) else r[0])])))
r=subprocess.run([CLI,'sch','upgrade','--force','esc_new/ESC3Phase.kicad_sch'],capture_output=True,text=True); print('upgrade:',r.stdout.strip()[-80:],r.stderr.strip()[-300:])
subprocess.run([CLI,'sch','erc','--format','json','--severity-all','-o','esc_new/erc.json','esc_new/ESC3Phase.kicad_sch'],capture_output=True)
e=json.load(open('esc_new/erc.json',encoding='utf-8'))
c=collections.Counter()
for sh in e['sheets']:
    for v in sh['violations']:
        c[(v['severity'],v['type'])]+=1
        if v['type'] not in ('global_label_dangling',):
            print('  ',v['severity'],v['type'],'|',v['description'],'|','; '.join(i['description'] for i in v['items'])[:160])
print('ERC:',dict(c))
subprocess.run([CLI,'sch','export','pdf','-o','esc_new/sheet.pdf','esc_new/ESC3Phase.kicad_sch'],capture_output=True)
