from gen_fps import fprop, footprint, write, U
DS='https://www.ti.com/lit/ds/symlink/lm74700-q1.pdf'
pads=''
for n,(x,y) in {1:(-1.3,-0.95),2:(-1.3,0),3:(-1.3,0.95),4:(1.3,0.95),5:(1.3,0),6:(1.3,-0.95)}.items():
    pads+=f'''	(pad "{n}" smd rect
		(at {x} {y})
		(size 1.1 0.6)
		(layers "F.Cu" "F.Paste" "F.Mask")
		(solder_mask_margin 0.1)
		(uuid "{U()}")
	)
'''
def line(x0,y0,x1,y1,layer,w=0.1):
    return f'''	(fp_line
		(start {x0} {y0})
		(end {x1} {y1})
		(stroke
			(width {w})
			(type default)
		)
		(layer "{layer}")
		(uuid "{U()}")
	)
'''
body=line(-0.8,-1.55,0.8,-1.55,'F.SilkS')+line(-0.8,1.55,0.8,1.55,'F.SilkS')
body+=f'''	(fp_circle
		(center -2.1 -1.5)
		(end -1.95 -1.5)
		(stroke
			(width 0.1)
			(type default)
		)
		(fill yes)
		(layer "F.SilkS")
		(uuid "{U()}")
	)
	(fp_rect
		(start -0.8 -1.45)
		(end 0.8 1.45)
		(stroke
			(width 0.1)
			(type default)
		)
		(fill no)
		(layer "F.Fab")
		(uuid "{U()}")
	)
	(fp_text user "${{REFERENCE}}"
		(at 0 -2.5 0)
		(unlocked yes)
		(layer "F.SilkS")
		(uuid "{U()}")
		(effects
			(font
				(size 1 1)
				(thickness 0.1)
			)
		)
	)
'''+pads+'''	(model "${METUPOWERLAB_3D}/CircuitProtections/IdealDiodes/METUPowerLab_CircuitProtections_IdealDiodes_SOT-23-6.step"
		(offset
			(xyz 0 0 0)
		)
		(scale
			(xyz 1 1 1)
		)
		(rotate
			(xyz -90 -0 -0)
		)
	)
'''
t=footprint('SOT-23-6_DBV','SOT-23-6 DBV (TI DBV0006A land pattern)','SOT-23-6_DBV','smd',body)
t=t.replace('(property "Datasheet" "https://github.com/odtu/Powerlab/blob/master/KiCAD/PCB_DESIGN_RULES.md"',f'(property "Datasheet" "{DS}"')
write('METUPowerLab_CircuitProtections_IdealDiodes','SOT-23-6_DBV',t)
print('fp ok')
