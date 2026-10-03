from kisexp import dumps
import schgen
S=schgen.Sheet('ESC3Phase.kicad_sch','Root test')
open('esc_new/ESC3Phase.kicad_sch','w',encoding='utf-8').write(dumps(S.node(S.uuid,'/',lambda s,r,p:[('/'+str(s.uuid),r)])))
