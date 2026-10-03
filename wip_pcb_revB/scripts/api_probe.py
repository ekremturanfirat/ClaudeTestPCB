import pcbnew
LIB='C:/Users/ekrem/Documents/KiCad/10.0/3rdparty/footprints/METUPowerLab_kicad_library/'
b=pcbnew.BOARD()
m=pcbnew.FootprintLoad(LIB+'METUPowerLab_Resistors_ChipResistors.pretty','0603_Medium')
print([x for x in dir(m) if 'Field' in x or 'Path' in x or 'Property' in x][:60])
print('fields:', [f.GetName() for f in m.GetFields()])
f=pcbnew.PCB_FIELD(m, pcbnew.FIELD_T_USER, 'Manufacturer Number') if hasattr(pcbnew,'FIELD_T_USER') else None
print('FIELD_T attrs', [a for a in dir(pcbnew) if a.startswith('FIELD_T')][:10])
ds=[a for a in dir(pcbnew.BOARD_DESIGN_SETTINGS) if not a.startswith('_')]
print('DS', [a for a in ds if 'm_' in a][:80])
print([a for a in dir(pcbnew) if 'Specctra' in a or 'SES' in a.upper() and 'Import' in a])
