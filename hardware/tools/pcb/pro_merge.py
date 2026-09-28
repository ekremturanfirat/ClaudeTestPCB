"""Merge the board settings pcbnew wrote into the schematic's project file (keeps sheets, text variables,
schematic net-class styling) and add the board net classes / HV class."""
import json, sys
sch_pro, board_pro, out = sys.argv[1:4]
base = json.load(open(sch_pro, encoding='utf-8'))
brd = json.load(open(board_pro, encoding='utf-8'))
for k in ('board', 'pcbnew', 'boards'):
    if k in brd:
        base[k] = brd[k]
HV_NETS = ['VIN_RAW', '+VBUS', '+VBUS_EFUSE', '+VBUS_PROT', 'PHASE_A', 'PHASE_B', 'PHASE_C',
           'GHA', 'GHB', 'GHC', '/Gate Drive/VCP', '/Gate Drive/CPH', '/Gate Drive/CPL',
           '/DC-Bus Current Sensing/IBUS_SNS_P', '/DC-Bus Current Sensing/IBUS_SNS_N',
           '/Power Input & Protection/EFUSE_VDD', '/Power Input & Protection/REVPOL_GATE',
           '/Power Input & Protection/LM_VCAP', '/Power Supply 3.3 V/BUCK_SW', '/Power Supply 3.3 V/BUCK_BOOT']
ns = base['net_settings']
cls = {c['name']: c for c in ns['classes']}
for name in ('Power', 'GND'):                      # rules 2.6: Power/GND 0.5 mm track, 0.3 mm clearance, 0.4/0.8 via
    cls[name].update(track_width=0.5, clearance=0.3, via_diameter=0.8, via_drill=0.4)
cls['Power']['priority'], cls['GND']['priority'] = 1, 2
cls['HV'] = {'name': 'HV', 'priority': 0, 'clearance': 0.6, 'track_width': 0.3, 'via_diameter': 0.8,
             'via_drill': 0.4, 'pcb_color': 'rgba(0, 0, 0, 0.000)', 'tuning_profile': ''}
ns['classes'] = [cls['Default'], cls['HV'], cls['Power'], cls['GND']]
pats = [p for p in ns['netclass_patterns'] if p['netclass'] != 'HV']
ns['netclass_patterns'] = [{'netclass': 'HV', 'pattern': n} for n in HV_NETS] + pats
json.dump(base, open(out, 'w', encoding='utf-8'), indent=2)
print('merged ->', out)
