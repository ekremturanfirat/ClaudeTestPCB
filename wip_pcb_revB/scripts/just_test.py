import schgen
from kisexp import Q
import parts
def build(sh):
    combos=[(270,270,'left'),(270,270,'right'),(270,90,'left'),(270,90,'right'),(270,0,'left'),(90,90,'left'),(90,270,'left'),(90,0,'left')]
    for i,(rot,fa,j) in enumerate(combos):
        p=sh.add(f'R{i+1}','METUPowerLab_Resistors_ChipResistors:10 kOhm',(30.48+i*25.4,60.96),rot=rot,footprint=parts.FP_R0603)
        p.fields={'_fa':str(fa),'_j':j}
        sh.text(f'rot{rot} fa{fa} {j}',(20.32+i*25.4,45.72),size=1.0)
