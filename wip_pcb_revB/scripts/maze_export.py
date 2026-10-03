"""Export routing obstacles for one net (KiCad side of the small maze router).
Every copper item of another net is inflated by the clearance it needs to the new track (HV 0.6 mm on outer
layers / 0.2 inner, Power/GND 0.3, default 0.2, + 0.05 margin) plus half the track width (or the via radius).
Pour-net fills count; GND fills don't (they refill around new copper).
Usage: python.exe maze_export.py <board> <net> <track_w> <out.json> [x1 y1 L1 x2 y2 L2]   (board mm, abs)
"""
import sys, json
import pcbnew

MM, T = pcbnew.FromMM, pcbnew.ToMM
LAYERS = [pcbnew.F_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]      # routable; In1 is the GND plane
HV = set()


def clr(b, other, net, layer):
    s = b.GetDesignSettings().m_NetSettings
    c1 = s.GetEffectiveNetClass(other).GetName() if other else 'Default'
    c2 = s.GetEffectiveNetClass(net).GetName()
    hv = 'HV' in c1 or 'HV' in c2
    inner = layer not in (pcbnew.F_Cu, pcbnew.B_Cu)
    if hv:
        return 0.2 if inner else 0.6
    if any(k in c1 or k in c2 for k in ('Power', 'GND')):
        return 0.3
    return 0.2


def polys(sps):
    out = []
    for i in range(sps.OutlineCount()):
        o = sps.Outline(i)
        out.append([(T(o.CPoint(j).x), T(o.CPoint(j).y)) for j in range(o.PointCount())])
    return out


def main(path, net, w, outp, ends):
    b = pcbnew.LoadBoard(path)
    res = {'track': {}, 'via': {}, 'w': w}
    for li, L in enumerate(LAYERS):
        tr, vi = [], []
        items = []
        for fp in b.GetFootprints():
            for p in fp.Pads():
                if p.IsOnLayer(L) and p.GetNetname() != net:
                    items.append(p)
        for t in b.GetTracks():
            if t.GetNetname() != net and t.IsOnLayer(L):
                items.append(t)
        for it in items:
            c = clr(b, it.GetNetname(), net, L) + 0.05
            for extra, dst in ((w / 2, tr), (0.3, vi)):
                sp = pcbnew.SHAPE_POLY_SET()
                it.TransformShapeToPolygon(sp, L, MM(c + extra), MM(0.02), pcbnew.ERROR_OUTSIDE)
                dst += polys(sp)
        for z in b.Zones():
            if z.GetIsRuleArea() or not z.IsOnLayer(L) or z.GetNetname() in (net, 'GND', ''):
                continue
            for extra, dst in ((w / 2, tr), (0.3, vi)):
                sp = z.GetFilledPolysList(L).CloneDropTriangulation()
                c = clr(b, z.GetNetname(), net, L) + 0.05
                sp.Inflate(MM(c + extra), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, MM(0.02))
                dst += polys(sp)
        res['track'][li], res['via'][li] = tr, vi
    # NPTH holes: hole clearance 0.25; mounting holes 3.5 mm keepout
    holes = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                r = 3.5 if fp.GetReference().startswith('H') else T(p.GetDrillSize().x) / 2 + 0.3
                holes.append((T(p.GetPosition().x), T(p.GetPosition().y), r))
    res['holes'] = holes
    eb = b.GetBoardEdgesBoundingBox()
    res['edge'] = (T(eb.GetLeft()) + 0.55, T(eb.GetTop()) + 0.55, T(eb.GetRight()) - 0.55, T(eb.GetBottom()) - 0.55)
    res['ends'] = ends
    # goal: copper of this net that is NOT in the start's island (islands by touching copper, like KiCad's
    # connectivity: track ends in pads/vias/other tracks, vias through layers, pads/tracks inside pour fills)
    sx, sy = ends[0], ends[1]
    sp_ = pcbnew.VECTOR2I(MM(sx), MM(sy))
    items = [p for fp in b.GetFootprints() for p in fp.Pads() if p.GetNetname() == net]
    items += [t for t in b.GetTracks() if t.GetNetname() == net]
    zones = [z for z in b.Zones() if z.GetNetname() == net and not z.GetIsRuleArea()]
    shapes = {}
    for i, it in enumerate(items):
        for L in pcbnew.LSET.AllCuMask().Seq():
            if it.IsOnLayer(L):
                sh = pcbnew.SHAPE_POLY_SET()
                it.TransformShapeToPolygon(sh, L, 0, MM(0.01), pcbnew.ERROR_INSIDE)
                shapes[(i, L)] = sh
    par = list(range(len(items) + len(zones)))
    def f(a):
        while par[a] != a:
            par[a] = par[par[a]]; a = par[a]
        return a
    def u(a, c):
        par[f(a)] = f(c)
    keys = list(shapes)
    for ai in range(len(keys)):
        for bi in range(ai + 1, len(keys)):
            (i, L), (j, M) = keys[ai], keys[bi]
            if L == M and i != j and f(i) != f(j):
                bb1, bb2 = shapes[keys[ai]].BBox(), shapes[keys[bi]].BBox()
                if bb1.Intersects(bb2) and shapes[keys[ai]].Collide(shapes[keys[bi]]):
                    u(i, j)
    for zi, z in enumerate(zones):
        for (i, L), sh in shapes.items():
            if z.IsOnLayer(L) and z.GetFilledPolysList(L).Collide(sh):
                u(len(items) + zi, i)
    start = [i for i, it in enumerate(items) if it.HitTest(sp_, MM(0.05))]
    sroot = {f(i) for i in start}
    goal = {}
    for li, L in enumerate(LAYERS):
        goal[li] = [pt for (i, M), sh in shapes.items() if M == L and f(i) not in sroot for pt in polys(sh)]
    res['goal'] = goal
    json.dump(res, open(outp, 'w'))
    print('exported', net, sum(len(v) for v in res['track'].values()), 'obstacle polygons')


if __name__ == '__main__':
    a = sys.argv
    ends = [float(v) if i % 3 != 2 else int(v) for i, v in enumerate(a[5:11])] if len(a) > 10 else []
    main(a[1], a[2], float(a[3]), a[4], ends)
