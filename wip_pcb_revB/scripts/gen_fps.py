import uuid, os
L='PLlib/footprints/'
DS='https://github.com/odtu/Powerlab/blob/master/KiCAD/PCB_DESIGN_RULES.md'
U=lambda: str(uuid.uuid4())
def fprop(name,value,at,layer,hide=True,thick=0.15):
    h='\n\t\t(hide yes)' if hide else ''
    return f'''	(property "{name}" "{value}"
		(at {at[0]} {at[1]} 0)
		(unlocked yes)
		(layer "{layer}"){h}
		(uuid "{U()}")
		(effects
			(font
				(size 1 1)
				(thickness {thick})
			)
		)
	)
'''
def circle(r,layer,width=0.1):
    return f'''	(fp_circle
		(center 0 0)
		(end {r} 0)
		(stroke
			(width {width})
			(type default)
		)
		(fill no)
		(layer "{layer}")
		(uuid "{U()}")
	)
'''
def reftext(y):
    return f'''	(fp_text user "${{REFERENCE}}"
		(at 0 {y} 0)
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
'''
def footprint(name,descr,value,attr,body,ref_hidden=True,extra_head=''):
    return f'''(footprint "{name}"
	(version 20241229)
	(generator "pcbnew")
	(generator_version "9.0")
	(layer "F.Cu")
	(descr "{descr}")
{extra_head}'''+fprop('Reference','REF**',(0,-0.5),'F.SilkS',ref_hidden,0.1)+fprop('Value',value,(0,1),'F.Fab')+fprop('Datasheet',DS,(0,0),'F.Fab')+fprop('Description',descr,(0,0),'F.Fab')+f'''	(attr {attr})
{body}	(embedded_fonts no)
)
'''
def write(lib,name,text):
    os.makedirs(L+lib+'.pretty',exist_ok=True)
    open(L+lib+'.pretty/'+name+'.kicad_mod','w',encoding='utf-8',newline='\n').write(text)

# --- mounting holes ---
MH='METUPowerLab_Mechanicals_MountingHoles'
for m,hole,keep,pad in [('M2.5',2.7,5.5,5.0),('M3',3.2,6.5,6.0)]:
    npth=f'''	(pad "" np_thru_hole circle
		(at 0 0)
		(size {hole} {hole})
		(drill {hole})
		(layers "*.Cu" "*.Mask")
		(remove_unused_layers no)
		(solder_mask_margin 0.1)
		(uuid "{U()}")
	)
'''
    write(MH,f'{m}_NPTH',footprint(f'{m}_NPTH',f'{m} Mounting Hole NPTH {hole}mm',f'{m}_NPTH','board_only exclude_from_pos_files exclude_from_bom',
          circle(keep/2,'F.SilkS')+circle(hole/2,'F.Fab')+npth))
    pth=f'''	(pad "1" thru_hole circle
		(at 0 0)
		(size {pad} {pad})
		(drill {hole})
		(layers "*.Cu" "*.Mask")
		(remove_unused_layers no)
		(solder_mask_margin 0.1)
		(uuid "{U()}")
	)
'''
    write(MH,f'{m}_Plated',footprint(f'{m}_Plated',f'{m} Mounting Hole Plated {hole}mm',f'{m}_Plated','through_hole board_only exclude_from_pos_files exclude_from_bom',
          circle(keep/2,'F.SilkS')+circle(hole/2,'F.Fab')+pth))

# --- fiducial: 1mm copper dot, 2mm mask opening, 3mm copper keepout (lab rule 3.2) ---
FD='METUPowerLab_Mechanicals_Fiducials'
fid=f'''	(pad "" smd circle
		(at 0 0)
		(size 1 1)
		(layers "F.Cu" "F.Mask")
		(solder_mask_margin 0.5)
		(clearance 1)
		(uuid "{U()}")
	)
'''
write(FD,'Fiducial_1mm_Mask2mm',footprint('Fiducial_1mm_Mask2mm','Fiducial 1mm Copper 2mm Mask 3mm Keepout','Fiducial_1mm_Mask2mm','smd board_only exclude_from_pos_files exclude_from_bom',
      circle(0.5,'F.Fab')+fid))

# --- bare SMD test pads ---
TP='METUPowerLab_TestPoints_SurfaceMounts'
for d,silk in [(1.0,0.85),(1.5,1.1)]:
    pad=f'''	(pad "1" smd circle
		(at 0 0)
		(size {d} {d})
		(layers "F.Cu" "F.Mask")
		(solder_mask_margin 0.1)
		(uuid "{U()}")
	)
'''
    n=f'Pad_D{d}mm'
    write(TP,n,footprint(n,f'Test Point Bare Pad D{d}mm',n,'smd exclude_from_pos_files exclude_from_bom',
          circle(silk,'F.SilkS')+reftext(silk+1.1)+pad))

# --- net tie ---
NT='METUPowerLab_NetTies_SurfaceMounts'
body=f'''	(fp_poly
		(pts
			(xy -0.5 -0.15) (xy 0.5 -0.15) (xy 0.5 0.15) (xy -0.5 0.15)
		)
		(stroke
			(width 0)
			(type solid)
		)
		(fill yes)
		(layer "F.Cu")
		(uuid "{U()}")
	)
	(pad "1" smd rect
		(at -0.5 0)
		(size 0.5 0.5)
		(layers "F.Cu")
		(solder_mask_margin 0.1)
		(uuid "{U()}")
	)
	(pad "2" smd rect
		(at 0.5 0)
		(size 0.5 0.5)
		(layers "F.Cu")
		(solder_mask_margin 0.1)
		(uuid "{U()}")
	)
'''
write(NT,'NetTie_2_0.5mm',footprint('NetTie_2_0.5mm','2-Pin Net Tie SMD 0.5mm','NetTie_2_0.5mm','smd exclude_from_pos_files exclude_from_bom',body,
      extra_head='\t(net_tie_pad_groups "1, 2")\n'))
print('ok')
