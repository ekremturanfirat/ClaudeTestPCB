"""Write the PCBWay standard 4-layer stackup into the board's setup section (1.6 mm, 1 oz all layers, FR-4,
lead-free HASL, green mask / white silk). Text edit of the saved .kicad_pcb (KiCad's Python stackup API is
not exposed). Usage: python stackup.py <board>
"""
import sys

STACK = '''		(stackup
			(layer "F.SilkS" (type "Top Silk Screen") (color "White"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (color "Green") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 1" (type "prepreg") (thickness 0.2) (material "FR4") (epsilon_r 4.4) (loss_tangent 0.02))
			(layer "In1.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 2" (type "core") (thickness 1.04) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
			(layer "In2.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 3" (type "prepreg") (thickness 0.2) (material "FR4") (epsilon_r 4.4) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.035))
			(layer "B.Mask" (type "Bottom Solder Mask") (color "Green") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
			(copper_finish "HAL lead-free")
			(dielectric_constraints no)
		)
'''

p = sys.argv[1]
t = open(p, encoding='utf-8').read()
if '(stackup' not in t:
    i = t.index('(setup')
    j = t.index('\n', i) + 1
    t = t[:j] + STACK + t[j:]
    open(p, 'w', encoding='utf-8').write(t)
    print('stackup written (total 1.6 mm)')
else:
    print('stackup already present')
