import uuid, re
from gen_fps import fprop, U
DS='https://documentation.espressif.com/esp32-wroom-32e_esp32-wroom-32ue_datasheet_en.pdf'
DESC='ESP32-WROOM-32E WiFi+BT Module SMD'
def pad(num,x,y,w,h,layers='"F.Cu" "F.Paste" "F.Mask"'):
    return f'''	(pad "{num}" smd rect
		(at {x:g} {y:g})
		(size {w:g} {h:g})
		(layers {layers})
		(solder_mask_margin 0.1)
		(uuid "{U()}")
	)
'''
def via(num,x,y):
    return f'''	(pad "{num}" thru_hole circle
		(at {x:g} {y:g})
		(size 0.5 0.5)
		(drill 0.3)
		(layers "*.Cu" "*.Mask")
		(remove_unused_layers no)
		(solder_mask_margin 0.1)
		(uuid "{U()}")
	)
'''
def rect(x0,y0,x1,y1,layer,w):
    return f'''	(fp_rect
		(start {x0:g} {y0:g})
		(end {x1:g} {y1:g})
		(stroke
			(width {w:g})
			(type default)
		)
		(fill no)
		(layer "{layer}")
		(uuid "{U()}")
	)
'''
body=''
body+=rect(-9,-12.75,9,12.75,'F.SilkS',0.1)
body+=rect(-9,-12.75,9,12.75,'F.Fab',0.1)
body+=rect(-9,-12.75,9,-6.56,'F.CrtYd',0.05)          # antenna region (datasheet fig.13: 6.19 mm)
body+=f'''	(fp_circle
		(center -10.2 -5.26)
		(end -10.0 -5.26)
		(stroke
			(width 0.2)
			(type default)
		)
		(fill yes)
		(layer "F.SilkS")
		(uuid "{U()}")
	)
	(fp_text user "${{REFERENCE}}"
		(at 0 -14 0)
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
for n in range(1,15):  body+=pad(n,-8.75,-5.26+(n-1)*1.27,1.5,0.9)
for n in range(15,25): body+=pad(n,-5.715+(n-15)*1.27,12.5,0.9,1.5)
for n in range(25,39): body+=pad(n,8.75,11.25-(n-25)*1.27,1.5,0.9)
for x in (-2.9,-1.5,-0.1):
    for y in (1.06,2.46,3.86):
        body+=pad(39,x,y,0.9,0.9)
body+=pad(39,-1.5,2.46,3.7,3.7,'"B.Cu" "B.Paste" "B.Mask"')
for x in (-2.2,-0.8):
    for y in (1.76,3.16):
        body+=via(39,x,y)
allcu=' '.join(f'"{l}"' for l in ['F.Cu','B.Cu']+[f'In{i}.Cu' for i in range(1,31)])
body+=f'''	(zone
		(net 0)
		(net_name "")
		(layers {allcu})
		(uuid "{U()}")
		(name "Antenna Keepout")
		(hatch full 0.5)
		(connect_pads
			(clearance 0)
		)
		(min_thickness 0.25)
		(filled_areas_thickness no)
		(keepout
			(tracks not_allowed)
			(vias not_allowed)
			(pads not_allowed)
			(copperpour not_allowed)
			(footprints not_allowed)
		)
		(placement
			(enabled no)
			(sheetname "")
		)
		(fill
			(thermal_gap 0.5)
			(thermal_bridge_width 0.5)
		)
		(polygon
			(pts
				(xy -9 -12.75) (xy 9 -12.75) (xy 9 -6.56) (xy -9 -6.56)
			)
		)
	)
	(model "${{METUPOWERLAB_3D}}/Microcontrollers/METUPowerLab_Microcontrollers_ESP32_ESP32-WROOM-32E.step"
		(offset
			(xyz 0 0 0)
		)
		(scale
			(xyz 1 1 1)
		)
		(rotate
			(xyz 0 0 0)
		)
	)
'''
txt=f'''(footprint "ESP32-WROOM-32E"
	(version 20241229)
	(generator "pcbnew")
	(generator_version "9.0")
	(layer "F.Cu")
	(descr "{DESC}")
'''+fprop('Reference','REF**',(0,-14),'F.SilkS',True,0.1)+fprop('Value','ESP32-WROOM-32E',(0,14),'F.Fab')+fprop('Datasheet',DS,(0,0),'F.Fab')+fprop('Description',DESC,(0,0),'F.Fab')+f'''	(attr smd)
{body}	(embedded_fonts no)
)
'''
p='PLlib/footprints/METUPowerLab_Microcontrollers_ESP32.pretty/ESP32-WROOM-32E.kicad_mod'
open(p,'w',encoding='utf-8',newline='\n').write(txt)
print('written')
