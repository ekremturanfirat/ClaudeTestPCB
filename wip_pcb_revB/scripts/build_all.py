"""Build the full ESC3Phase schematic hierarchy, then verify with kicad-cli (ERC + netlist compare + PDF)."""
import json, subprocess, collections, sys, base64, os
from kisexp import dumps, load, kids, kid, val
import schgen, parts
import sheet_input, sheet_psu, sheet_sense, sheet_mcu, sheet_gatedrive, sheet_powerstage, sheet_halfbridge, sheet_comm
import sheet_root

CLI = r'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
OUT = 'esc_new'

S = schgen.Sheet
root = S('ESC3Phase.kicad_sch', '3-Phase BLDC ESC - Overview')
sheets = dict(
    input=S('PowerInput.kicad_sch', 'Power Input & Protection'),
    psu=S('PowerSupply.kicad_sch', 'Power Supply 3.3 V'),
    sense=S('CurrentSensing.kicad_sch', 'DC-Bus Current Sensing'),
    mcu=S('MCUCore.kicad_sch', 'MCU Core'),
    gate=S('GateDrive.kicad_sch', 'Gate Drive'),
    pstage=S('PowerStage.kicad_sch', 'Power Stage'),
    comm=S('Communication.kicad_sch', 'Communication'),
)
hb = S('HalfBridge.kicad_sch', 'Half Bridge')
for s in list(sheets.values()) + [root, hb]:
    s.sheets_syms = []

# ---- build sheet contents (order: nets marked global first) ----
sheet_gatedrive.build(sheets['gate'])
sheet_mcu.build(sheets['mcu'])
sheet_input.build(sheets['input'])
sheet_psu.build(sheets['psu'])
sheet_sense.build(sheets['sense'])
sheet_comm.build(sheets['comm'])
sheet_halfbridge.build(hb)
hb_syms = sheet_powerstage.build(sheets['pstage'], hb)
order = ['input', 'psu', 'sense', 'mcu', 'gate', 'pstage', 'comm']
top_syms = sheet_root.build(root, [(k, sheets[k]) for k in order])

# ---- pages + instance paths ----
R = str(root.uuid)
page = 2
paths = {}          # sheet filename -> list of instance paths (for symbol instances)
for k, ss in zip(order, top_syms):
    ss.page = page; page += 1
    paths.setdefault(ss.child.filename, []).append(f'/{R}/{ss.uuid}')
    if k == 'pstage':
        for hs in hb_syms:
            hs.page = page; page += 1
            paths.setdefault(hb.filename, []).append(f'/{R}/{ss.uuid}/{hs.uuid}')
root.sheets = [ss.node(f'/{R}') for ss in top_syms]
pst_path = paths[sheets['pstage'].filename][0]
sheets['pstage'].sheets = [hs.node(pst_path) for hs in hb_syms]
hb.sheets = []
for s in list(sheets.values()):
    s.sheets = getattr(s, 'sheets', []) if s is not sheets['pstage'] else s.sheets


def instances_for(sheet, ref, part):
    if sheet is root:
        return [(f'/{R}', ref if isinstance(ref, str) else ref[0])]
    ps = paths[sheet.filename]
    refs = ref if isinstance(ref, list) else [ref] * len(ps)
    if not isinstance(ref, list) and len(ps) > 1 and not str(ref).startswith('#'):
        raise ValueError(f'{sheet.filename}: {ref} needs per-instance refs')
    if str(ref).startswith('#') and len(ps) > 1:
        refs = [f'{ref}{chr(65 + i)}' for i in range(len(ps))]
    return list(zip(ps, refs))


# power symbol refs must be unique project-wide: offset per sheet
offset = 0
for s in [root] + list(sheets.values()) + [hb]:
    s.pwr_count = offset
    offset += 100

os.makedirs(OUT, exist_ok=True)
for s in [root] + list(sheets.values()) + [hb]:
    node = s.node(root.uuid if s is root else root.uuid, '/' if s is root else '/x', instances_for)
    with open(os.path.join(OUT, s.filename), 'w', encoding='utf-8') as f:
        f.write(dumps(node))
for s in [root] + list(sheets.values()) + [hb]:
    r = subprocess.run([CLI, 'sch', 'upgrade', '--force', os.path.join(OUT, s.filename)], capture_output=True, text=True)
    if r.returncode:
        print('UPGRADE FAILED', s.filename, r.stdout, r.stderr)
        sys.exit(1)

# ---- ERC ----
subprocess.run([CLI, 'sch', 'erc', '--format', 'json', '--severity-all', '-o', f'{OUT}/erc.json', f'{OUT}/ESC3Phase.kicad_sch'],
               capture_output=True)
e = json.load(open(f'{OUT}/erc.json', encoding='utf-8'))
cnt = collections.Counter()
for shv in e['sheets']:
    for v in shv['violations']:
        cnt[(v['severity'], v['type'])] += 1
        print(f"  ERC {v['severity']:7} {v['type']:24} {shv['path']:28} {v['description'][:70]} | "
              + '; '.join(i['description'] for i in v['items'])[:150])
print('ERC summary:', dict(cnt))

# ---- netlist compare ----
subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', f'{OUT}/net.net', f'{OUT}/ESC3Phase.kicad_sch'],
               capture_output=True)
nl = load(f'{OUT}/net.net')
kicad = {}
for n in kids(kid(nl, 'nets'), 'net'):
    name = str(val(n, 'name'))
    for nd in kids(n, 'node'):
        kicad[(str(val(nd, 'ref')), str(val(nd, 'pin')))] = name

# intended: global names for power/global nets; hierarchical labels resolve through the sheet symbol pins
intended = {}
def keyname(sheet, inst_path, net):
    if net in parts.POWER_NETS or net in parts.GLOBAL_NETS:
        return net
    if sheet is hb:
        net = {'PHASE': 'SH'}.get(net, net)
        i = paths[hb.filename].index(inst_path)
        ss = hb_syms[i]
        if net in ss.pin_nets:
            return ss.pin_nets[net]
    return f'{inst_path}::{net}'
for s in list(sheets.values()) + [hb]:
    for ip_i, ip in enumerate(paths[s.filename]):
        for p in s.parts:
            ref = p.ref[ip_i] if isinstance(p.ref, list) else p.ref
            for pin, nets in p.pin_net.items():
                nets = {n for n in nets if n is not None}
                if not nets:
                    continue
                assert len(nets) == 1, f'{ref}.{pin} has several intended nets {nets}'
                intended[(ref, pin)] = keyname(s, ip, next(iter(nets)))
problems = 0
by_kicad = collections.defaultdict(set)
for k, v in kicad.items():
    by_kicad[v].add(k)
for knet, members in by_kicad.items():
    mine = {intended.get(m, 'UNSPECIFIED') for m in members}
    if knet.startswith('unconnected-'):
        extra = [m for m in members if m in intended]
        if extra:
            problems += 1; print('  OPEN (intended connected):', knet, extra)
        continue
    if len(mine) > 1:
        problems += 1
        print(f'  SHORT/MISMATCH: KiCad net {knet} merges intended {sorted(mine)} :', sorted(members)[:8])
by_mine = collections.defaultdict(set)
for k, v in intended.items():
    by_mine[v].add(k)
for mnet, members in by_mine.items():
    kn = {kicad.get(m, 'MISSING') for m in members}
    if len(kn) > 1:
        problems += 1
        print(f'  SPLIT: intended {mnet} ended up in KiCad nets {sorted(kn)}')
    gname = mnet if '::' not in mnet else None
    if gname and kn and next(iter(kn)).lstrip('/') != gname and len(kn) == 1:
        print(f'  name note: intended {gname} -> KiCad {next(iter(kn))}')
print(f'NETLIST COMPARE: {len(by_kicad)} KiCad nets, {len(by_mine)} intended nets, problems = {problems}')

subprocess.run([CLI, 'sch', 'export', 'pdf', '-o', f'{OUT}/ESC3Phase_schematic.pdf', f'{OUT}/ESC3Phase.kicad_sch'], capture_output=True)
print('PDF written')
