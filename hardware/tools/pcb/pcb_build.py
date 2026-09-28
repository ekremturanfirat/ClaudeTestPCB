"""Build ESC3Phase.kicad_pcb from KiCad's netlist with pcbnew (KiCad 10), per METU PowerLab rules.

Usage: python.exe pcb_build.py <netlist> <out.kicad_pcb>
Placement comes from placement.py (board coords, mm, origin = board top-left).
"""
import sys, importlib
import pcbnew
from kisexp import load, kids, kid, val
import placement
importlib.reload(placement)

LIB = 'C:/Users/ekrem/Documents/KiCad/10.0/3rdparty/footprints/METUPowerLab_kicad_library/'
MM = pcbnew.FromMM
OX, OY = 50.0, 50.0            # board top-left in KiCad coordinates


def P(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY + y))


def load_netlist(path):
    nl = load(path)
    comps = []
    for c in kids(kid(nl, 'components'), 'comp'):
        fields = {str(f[1][1]) if isinstance(f[1], list) else '': '' for f in []}
        fl = {}
        for f in kids(kid(c, 'fields') or ['fields'], 'field'):
            name = str(val(f, 'name'))
            fl[name] = str(f[2]) if len(f) > 2 and not isinstance(f[2], list) else ''
        sp = kid(c, 'sheetpath')
        comps.append(dict(ref=str(val(c, 'ref')), value=str(val(c, 'value')), footprint=str(val(c, 'footprint')),
                          fields=fl, tstamps=str(val(sp, 'tstamps')), uuid=str(val(c, 'tstamps')),
                          sheetname=str(val(sp, 'names'))))
    nets = {}
    for n in kids(kid(nl, 'nets'), 'net'):
        nets[str(val(n, 'name'))] = [(str(val(nd, 'ref')), str(val(nd, 'pin'))) for nd in kids(n, 'node')]
    return comps, nets


def place_center(fp, x, y, rot, side):
    fp.SetOrientationDegrees(0)
    if side == 'B':
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(rot)
    bb = fp.GetBoundingBox(False)
    c = bb.GetCenter()
    pos = fp.GetPosition()
    target = P(x, y)
    fp.SetPosition(pcbnew.VECTOR2I(pos.x + target.x - c.x, pos.y + target.y - c.y))


def build(netlist, out):
    comps, nets = load_netlist(netlist)
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)                   # user-approved 4 layers: L1 signal, L2 GND, L3 signal, L4 signal
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(MM(1.6))
    # ---- DRC constraints: METU PowerLab rules 2.6 (1 oz) ----
    ds.m_MinClearance = MM(0.2)
    ds.m_TrackMinWidth = MM(0.15)                  # PCBWay floor; the 0.2 mm lab default is a DRU rule
    ds.m_MinConn = MM(0.2)
    ds.m_ViasMinAnnularWidth = MM(0.15)
    ds.m_ViasMinSize = MM(0.6)
    ds.m_HoleClearance = MM(0.25)
    ds.m_CopperEdgeClearance = MM(0.5)
    ds.m_MinThroughDrill = MM(0.3)
    ds.m_HoleToHoleMin = MM(0.4)
    ds.m_MicroViasMinSize = MM(0.6)
    ds.m_MicroViasMinDrill = MM(0.3)
    ds.m_SolderMaskExpansion = MM(0.05)
    ds.m_SolderMaskMinWidth = MM(0.1)
    ds.m_MinSilkTextHeight = MM(1.0)
    ds.m_MinSilkTextThickness = MM(0.15)
    ds.m_TentViasFront = True
    ds.m_TentViasBack = True

    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netinfo[name] = ni
    pad_net = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            pad_net[(ref, pin)] = name

    placed = {}
    for c in comps:
        lib, name = c['footprint'].split(':', 1)
        fp = pcbnew.FootprintLoad(LIB + lib + '.pretty', name)
        if fp is None:
            raise RuntimeError(f"cannot load {c['footprint']} for {c['ref']}")
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.SetReference(c['ref'])
        fp.SetValue(c['value'])
        for k, v in c['fields'].items():
            if k in ('Reference', 'Value', 'Footprint'):
                continue
            fp.SetField(k, v)
            fp.GetField(k).SetVisible(False)
        for f in fp.GetFields():
            if f.GetName() != 'Reference':
                f.SetVisible(False)
        ref = fp.Reference()
        ref.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
        ref.SetTextThickness(MM(0.15))
        for item in [it for it in fp.GraphicalItems()]:   # a second, user '${REFERENCE}' text on the silk
            if isinstance(item, pcbnew.PCB_TEXT) and item.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                fp.Remove(item)                             # outline: only the Reference field is kept
        fp.SetPath(pcbnew.KIID_PATH(c['tstamps'] + c['uuid']))
        fp.SetSheetname(c['sheetname'])
        board.Add(fp)
        for pad in fp.Pads():
            n = pad_net.get((c['ref'], pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
            bbp = pad.GetBoundingBox()
            if n == 'GND' and min(bbp.GetWidth(), bbp.GetHeight()) > MM(1.5):
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)   # exposed / thermal pads: solid to GND
        placed[c['ref']] = fp
    # pass 1: absolute placements; pass 2: 'near' placements relative to an already placed pad
    todo = dict(placement.PLACE)
    for ref, spec in todo.items():
        if spec[0] != 'near' and ref in placed:
            x, y, rot = spec[:3]
            place_center(placed[ref], x, y, rot, spec[3] if len(spec) > 3 else 'F')
    for ref, spec in todo.items():
        if spec[0] == 'near' and ref in placed:
            _, oref, opad, dx, dy, rot = spec[:6]
            pads = [p for p in placed[oref].Pads() if p.GetNumber() == str(opad)]
            if not pads:
                raise KeyError(f'{ref}: {oref} has no pad {opad}')
            qx = sum(pcbnew.ToMM(p.GetPosition().x) for p in pads) / len(pads)   # centroid of the pin's pads
            qy = sum(pcbnew.ToMM(p.GetPosition().y) for p in pads) / len(pads)
            x, y = qx - OX + dx, qy - OY + dy
            fp = placed[ref]
            best = None
            for r in ((rot, (rot + 180) % 360) if len(fp.Pads()) == 2 else (rot,)):
                place_center(fp, x, y, r, 'F')        # 2-pin parts: pick the rotation whose pads face the anchor's same-net pads
                cost = 0.0
                for pd in fp.Pads():
                    tgt = [a for a in placed[oref].Pads() if a.GetNetname() == pd.GetNetname() and pd.GetNetname()]
                    if tgt:
                        cost += min((a.GetPosition() - pd.GetPosition()).EuclideanNorm() for a in tgt)
                if best is None or cost < best[0] - 1:
                    best = (cost, r)
            place_center(fp, x, y, best[1], 'F')
    unplaced = [r for r in placed if r not in todo]
    for i, r in enumerate(unplaced):
        place_center(placed[r], 120 + (i % 10) * 8, (i // 10) * 8, 0, 'F')
    if unplaced:
        print('UNPLACED:', unplaced)

    # ---- board outline: rectangle with 1 mm corner radius ----
    W, H, R = placement.W, placement.H, 1.0
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(P(*a)); s.SetEnd(P(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); board.Add(s)
    def arc(c, start, ang):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_ARC)
        s.SetCenter(P(*c)); s.SetStart(P(*start)); s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T), True)
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); board.Add(s)
    seg((R, 0), (W - R, 0)); seg((W, R), (W, H - R)); seg((W - R, H), (R, H)); seg((0, H - R), (0, R))
    arc((W - R, R), (W - R, 0), 90); arc((W - R, H - R), (W, H - R), 90)
    arc((R, H - R), (R, H), 90); arc((R, R), (0, R), 90)

    # ---- mechanical: M3 NPTH mounting holes + fiducials (board-only footprints) ----
    extra = [('H1', 'METUPowerLab_Mechanicals_MountingHoles', 'M3_NPTH', xy) for xy in placement.HOLES]
    extra += [('FID', 'METUPowerLab_Mechanicals_Fiducials', 'Fiducial_1mm_Mask2mm', xy) for xy in placement.FIDUCIALS]
    counters = {}
    for pre, lib, name, (x, y) in extra:
        fp = pcbnew.FootprintLoad(LIB + lib + '.pretty', name)
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        counters[pre] = counters.get(pre, 0) + 1
        fp.SetReference(f'{pre[0] if pre == "H1" else pre}{counters[pre]}')
        board.Add(fp)
        fp.SetPosition(P(x, y))
    board.Save(out)
    return board


if __name__ == '__main__':
    import os, shutil, subprocess
    build(sys.argv[1], sys.argv[2])
    pro = os.path.splitext(sys.argv[2])[0] + '.kicad_pro'
    shutil.copy(pro, 'board_saved.kicad_pro')        # pcbnew writes a fresh project: merge it into the schematic's
    subprocess.run([sys.executable if False else 'python', 'pro_merge.py', 'esc_new/ESC3Phase.kicad_pro',
                    'board_saved.kicad_pro', pro], check=True)
    print('saved', sys.argv[2])
