"""Before mitering (rule 3.3): clean the router's leftover stubs. One board load, cached track list.
  - zero-length tracks are deleted
  - a stub < 0.1 mm whose far end is inside its own pad: removed, the neighbour extended into the pad
  - a stub < 0.1 mm between two segments: removed, the neighbours joined at the intersection of their lines
Usage: python.exe stub_clean.py <board>
"""
import sys, math, collections
import pcbnew
MM = pcbnew.FromMM


def main(path):
    b = pcbnew.LoadBoard(path)
    tracks = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
    vias = {(v.GetPosition().x, v.GetPosition().y) for v in b.GetTracks() if v.Type() == pcbnew.PCB_VIA_T}
    pads = [pd for fp in b.GetFootprints() for pd in fp.Pads()]
    alive = set(range(len(tracks)))

    def ends_map():
        m = collections.defaultdict(list)
        for i in alive:
            t = tracks[i]
            m[(t.GetLayer(), t.GetStart().x, t.GetStart().y)].append((i, 'S'))
            m[(t.GetLayer(), t.GetEnd().x, t.GetEnd().y)].append((i, 'E'))
        return m

    zero = [i for i in alive if tracks[i].GetLength() < MM(0.001)]
    for i in zero:
        b.Remove(tracks[i]); alive.discard(i)
    merged = inter = 0
    for i in sorted(alive, key=lambda k: tracks[k].GetLength()):
        if i not in alive:
            continue
        t = tracks[i]
        if not (0 < t.GetLength() < MM(0.1)):
            continue
        m = ends_map()
        L = t.GetLayer()
        ka, kb = (L, t.GetStart().x, t.GetStart().y), (L, t.GetEnd().x, t.GetEnd().y)
        sa = [(o, e) for o, e in m[ka] if o != i]
        sb = [(o, e) for o, e in m[kb] if o != i]
        # (a) far end inside its own pad
        for near, far_k, far_pt in ((sa, kb, t.GetEnd()), (sb, ka, t.GetStart())):
            if len(near) == 1 and not m[far_k][1:] and tracks[near[0][0]].GetLength() > MM(0.2):
                if any(pd.GetNetCode() == t.GetNetCode() and pd.IsOnLayer(L) and pd.HitTest(far_pt) for pd in pads):
                    o, e = near[0]
                    (tracks[o].SetStart if e == 'S' else tracks[o].SetEnd)(far_pt)
                    b.Remove(t); alive.discard(i); merged += 1
                    break
        if i not in alive:
            continue
        # (b) between two segments: join at the line intersection
        if len(sa) != 1 or len(sb) != 1 or ka[1:] in vias or kb[1:] in vias:
            continue
        (a, ea), (c, ec) = sa[0], sb[0]
        A, C = tracks[a], tracks[c]
        if A.GetNetCode() != t.GetNetCode() or C.GetNetCode() != t.GetNetCode():
            continue
        pa, qa = (A.GetStart(), A.GetEnd()) if ea == 'E' else (A.GetEnd(), A.GetStart())
        pc, qc = (C.GetStart(), C.GetEnd()) if ec == 'E' else (C.GetEnd(), C.GetStart())
        d1 = (qa.x - pa.x, qa.y - pa.y); d2 = (qc.x - pc.x, qc.y - pc.y)
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-6:
            continue
        u = ((pc.x - pa.x) * d2[1] - (pc.y - pa.y) * d2[0]) / den
        ix, iy = pa.x + u * d1[0], pa.y + u * d1[1]
        mx, my = (t.GetStart().x + t.GetEnd().x) / 2, (t.GetStart().y + t.GetEnd().y) / 2
        if math.hypot(ix - mx, iy - my) > MM(0.3):
            continue
        ip = pcbnew.VECTOR2I(int(round(ix)), int(round(iy)))
        (A.SetEnd if ea == 'E' else A.SetStart)(ip)
        (C.SetEnd if ec == 'E' else C.SetStart)(ip)
        b.Remove(t); alive.discard(i); inter += 1
    b.Save(path)
    print(f'stubs: {len(zero)} zero-length removed, {merged} merged into pads, {inter} replaced by a line intersection')


if __name__ == '__main__':
    main(sys.argv[1])
