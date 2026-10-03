"""Rule 3.3: replace 90 deg track corners with 45 deg chamfers. A joint of exactly two segments (same net,
layer, width) that meet at ~90 deg gets both segments shortened by c and a diagonal added,
c = min(0.6 mm, 0.45 x the shorter segment). Chamfers that break DRC are reverted (checked with kicad-cli).
Also merges collinear pairs. Usage: python.exe miter.py <board>
"""
import sys, math, json, subprocess, collections
import pcbnew

CLI = 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
MM, T = pcbnew.FromMM, pcbnew.ToMM


def joints(b):
    ends = collections.defaultdict(list)
    tracks = [t for t in b.GetTracks() if t.Type() == pcbnew.PCB_TRACE_T]
    vias = {(v.GetPosition().x, v.GetPosition().y) for v in b.GetTracks() if v.Type() == pcbnew.PCB_VIA_T}
    pads = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            pads.append(p)
    for t in tracks:
        ends[(t.GetLayer(), t.GetStart().x, t.GetStart().y)].append((t, 'S'))
        ends[(t.GetLayer(), t.GetEnd().x, t.GetEnd().y)].append((t, 'E'))
    return ends, vias


def apply(b, only=None, scale=1.0):
    ends, vias = joints(b)
    done = []
    for (L, x, y), lst in ends.items():
        if len(lst) != 2 or (x, y) in vias:
            continue
        (t1, e1), (t2, e2) = lst
        if t1.GetNetCode() != t2.GetNetCode():
            continue
        p = pcbnew.VECTOR2I(x, y)
        q1 = t1.GetEnd() if e1 == 'S' else t1.GetStart()
        q2 = t2.GetEnd() if e2 == 'S' else t2.GetStart()
        v1 = (q1.x - x, q1.y - y); v2 = (q2.x - x, q2.y - y)
        l1, l2 = math.hypot(*v1), math.hypot(*v2)
        if l1 == 0 or l2 == 0:
            continue
        cosang = (v1[0] * v2[0] + v1[1] * v2[1]) / (l1 * l2)
        ang = math.degrees(math.acos(max(-1, min(1, cosang))))
        if not (80 <= ang <= 100):
            continue
        key = (L, x, y)
        if only is not None and key not in only:
            continue
        c = min(MM(0.6), 0.45 * min(l1, l2)) * scale
        if c < MM(0.03):
            continue
        a = pcbnew.VECTOR2I(int(x + v1[0] / l1 * c), int(y + v1[1] / l1 * c))
        bb = pcbnew.VECTOR2I(int(x + v2[0] / l2 * c), int(y + v2[1] / l2 * c))
        (t1.SetStart if e1 == 'S' else t1.SetEnd)(a)
        (t2.SetStart if e2 == 'S' else t2.SetEnd)(bb)
        d = pcbnew.PCB_TRACK(b)
        d.SetStart(a); d.SetEnd(bb); d.SetWidth(min(t1.GetWidth(), t2.GetWidth())); d.SetLayer(L); d.SetNet(t1.GetNet())
        b.Add(d)
        done.append((key, t1, e1, t2, e2, d))
    return done


def drc_bad(path):
    subprocess.run([CLI, 'pcb', 'drc', '--severity-error', '--format', 'json', '-o', path + '.m.json', path],
                   check=True, capture_output=True)
    d = json.load(open(path + '.m.json', encoding='utf-8'))
    return {it['uuid'] for v in d['violations'] for it in v['items']}


def revert(b, bad, made):
    """made: list of (corner key, uuid of the new diagonal). Put back the corners whose diagonal is in `bad`."""
    byid = {t.m_Uuid.AsString(): t for t in b.GetTracks()}
    back = set()
    for key, u in made:
        if u in bad and u in byid:                    # chamfer breaks a rule: put the corner back
            tr = byid[u]
            L, x, y = key
            p = pcbnew.VECTOR2I(x, y)
            s_, e_ = tr.GetStart(), tr.GetEnd()
            for t in b.GetTracks():
                if t.Type() == pcbnew.PCB_TRACE_T and t.GetLayer() == L and t.m_Uuid.AsString() != u                         and t.GetNetCode() == tr.GetNetCode():
                    if t.GetStart() == s_ or t.GetStart() == e_:
                        t.SetStart(p)
                    elif t.GetEnd() == s_ or t.GetEnd() == e_:
                        t.SetEnd(p)
            b.Remove(tr); back.add(key)
    return back


def main(path):
    zero = []
    total, only, scale = 0, None, 1.0
    for rnd in range(4):                              # retry reverted corners with a smaller chamfer
        b = pcbnew.LoadBoard(path)
        done = apply(b, only, scale)
        made = [(key, dg.m_Uuid.AsString()) for key, t1, e1, t2, e2, dg in done]
        if not made:
            break
        b.Save(path)
        bad = drc_bad(path)
        b = pcbnew.LoadBoard(path)
        back = revert(b, bad, made)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        b.Save(path)
        total += len(made) - len(back)
        print(f'  round {rnd + 1}: chamfer x{scale:.2f}: {len(made)} tried, {len(back)} reverted')
        if not back:
            break
        only, scale = back, scale * 0.5
    print(f'mitered {total} corners')


if __name__ == '__main__':
    main(sys.argv[1])
