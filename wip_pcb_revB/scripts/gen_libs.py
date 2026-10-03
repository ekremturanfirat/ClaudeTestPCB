import uuid, os
L='PLlib/'
DS='https://github.com/odtu/Powerlab/blob/master/KiCAD/PCB_DESIGN_RULES.md'
def prop(name,value,at=(0,0),hide=True,size=1.27):
    h='\n\t\t\t\t(hide yes)' if hide else ''
    return f'''		(property "{name}" "{value}"
			(at {at[0]} {at[1]} 0)
			(effects
				(font
					(size {size} {size})
				){h}
			)
		)
'''
def pin(num,x,y,ang,length,ptype='passive'):
    return f'''			(pin {ptype} line
				(at {x} {y} {ang})
				(length {length})
				(name "~"
					(effects
						(font
							(size 1.27 1.27)
						)
					)
				)
				(number "{num}"
					(effects
						(font
							(size 1.27 1.27)
						)
					)
				)
			)
'''
def symbol(name,fields,graphics,pins,in_bom='yes'):
    body=f'''	(symbol "{name}"
		(pin_numbers
			(hide yes)
		)
		(pin_names
			(offset 0)
			(hide yes)
		)
		(exclude_from_sim no)
		(in_bom {in_bom})
		(on_board yes)
'''+''.join(fields)+f'''		(symbol "{name}_0_1"
{graphics}		)
		(symbol "{name}_1_1"
{''.join(pins)}		)
		(embedded_fonts no)
	)
'''
    return body
def lib(symbols):
    return '(kicad_symbol_lib\n\t(version 20241209)\n\t(generator "kicad_symbol_editor")\n\t(generator_version "9.0")\n'+''.join(symbols)+')\n'

tp_g='''			(circle
				(center 0 3.302)
				(radius 0.762)
				(stroke
					(width 0)
					(type default)
				)
				(fill
					(type none)
				)
			)
'''
tp=symbol('TestPoint_Pad',[
    prop('Reference','TP',(1.524,3.302),False),
    prop('Value','TestPoint_Pad',(1.524,1.524),False),
    prop('Footprint',''),prop('Datasheet',DS),
    prop('Description','Bare copper SMD test pad'),
    prop('Mounting Type','Surface Mount'),
    prop('ki_keywords','test point tp probe pad'),
    prop('ki_fp_filters','METUPowerLab_TestPoints_SurfaceMounts:Pad_*'),
  ], tp_g, [pin('1',0,0,90,2.54)], in_bom='no')
open(L+'symbols/METUPowerLab_TestPoints_SurfaceMounts.kicad_sym','w',encoding='utf-8',newline='\n').write(lib([tp]))

nt_g='''			(rectangle
				(start -1.27 0.508)
				(end 1.27 -0.508)
				(stroke
					(width 0)
					(type default)
				)
				(fill
					(type outline)
				)
			)
'''
nt=symbol('NetTie_2_0.5mm',[
    prop('Reference','NT',(0,2.032),False),
    prop('Value','NetTie_2_0.5mm',(0,-2.032),False),
    prop('Footprint','METUPowerLab_NetTies_SurfaceMounts:NetTie_2_0.5mm'),prop('Datasheet',DS),
    prop('Description','2-pin net tie SMD 0.5mm'),
    prop('Mounting Type','Surface Mount'),
    prop('ki_keywords','net tie short kelvin star ground'),
  ], nt_g, [pin('1',-3.81,0,0,2.54),pin('2',3.81,0,180,2.54)], in_bom='no')
open(L+'symbols/METUPowerLab_NetTies_SurfaceMounts.kicad_sym','w',encoding='utf-8',newline='\n').write(lib([nt]))
print('ok')
