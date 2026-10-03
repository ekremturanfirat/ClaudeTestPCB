import pcbnew
LIB='C:/Users/ekrem/Documents/KiCad/10.0/3rdparty/footprints/METUPowerLab_kicad_library/'
for lib,name in [('METUPowerLab_Connectors_ScrewTerminals','7770'),('METUPowerLab_Connectors_SignalConnectors','384471-E'),('METUPowerLab_Connectors_SignalConnectors','2147210040'),('METUPowerLab_Capacitors_AluminumPolymers_ThroughHoles','8.00x13.50mm'),('METUPowerLab_Resistors_ShuntResistors','2512'),('METUPowerLab_Switches_TactileSwitches','TL6330AF200Q'),('METUPowerLab_MotorDrivers_BLDC','48-VQFN'),('METUPowerLab_Inductors_SurfaceMounts','6x5_7mm')]:
    m=pcbnew.FootprintLoad(LIB+lib+'.pretty',name)
    bb=m.GetBoundingBox(False)
    print(f'== {name}: bbox x[{pcbnew.ToMM(bb.GetLeft()):.2f},{pcbnew.ToMM(bb.GetRight()):.2f}] y[{pcbnew.ToMM(bb.GetTop()):.2f},{pcbnew.ToMM(bb.GetBottom()):.2f}] attr={m.GetAttributes()}')
    for p in list(m.Pads())[:8]:
        pos=p.GetPosition(); sz=p.GetSize()
        print(f'    pad {p.GetNumber():>6} ({pcbnew.ToMM(pos.x):6.2f},{pcbnew.ToMM(pos.y):6.2f}) {pcbnew.ToMM(sz.x):.2f}x{pcbnew.ToMM(sz.y):.2f} drill={pcbnew.ToMM(p.GetDrillSize().x):.2f}')
