"""Add a maze.py path to the board. Usage: python.exe maze_apply.py <board> <net> <track_w> <path.json>"""
import sys, json
import pcbnew

MM = pcbnew.FromMM
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]


def main(path, net, w, pj):
    b = pcbnew.LoadBoard(path)
    n = b.FindNet(net)
    d = json.load(open(pj))
    assert d['ok']
    # snap the path ends onto the centre of the same-net via/pad they landed on (full-width joint)
    anchors = [v for v in b.GetTracks() if v.Type() == pcbnew.PCB_VIA_T and v.GetNetname() == net]
    anchors += [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == net]
    for sg, k in ((d['segs'][0], 0), (d['segs'][-1], -1)):
        x, y = sg['pts'][k]
        q = pcbnew.VECTOR2I(MM(x), MM(y))
        for a in anchors:
            if a.IsOnLayer(LAYERS[sg['layer']]) and a.HitTest(q, MM(w / 2)):
                c = a.GetPosition()
                sg['pts'][k] = (pcbnew.ToMM(c.x), pcbnew.ToMM(c.y))
                break
    for sg in d['segs']:
        for (x0, y0), (x1, y1) in zip(sg['pts'], sg['pts'][1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0))); t.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
            t.SetWidth(MM(w)); t.SetLayer(LAYERS[sg['layer']]); t.SetNet(n); b.Add(t)
    for x, y in d['vias']:
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); v.SetWidth(MM(0.6)); v.SetDrill(MM(0.3)); v.SetNet(n); b.Add(v)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(path)
    print('added', net)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4])
