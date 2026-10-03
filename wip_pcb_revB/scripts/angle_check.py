"""Rule 3.3: 45 deg corners only, no 90 / acute corners. Reports track joints by angle, per net."""
import sys, math, collections
import pcbnew
T = pcbnew.ToMM
b = pcbnew.LoadBoard(sys.argv[1])
ends = collections.defaultdict(list)
for t in b.GetTracks():
    if t.Type() != pcbnew.PCB_TRACE_T:
        continue
    for p, q in ((t.GetStart(), t.GetEnd()), (t.GetEnd(), t.GetStart())):
        ends[(t.GetLayer(), p.x, p.y)].append((t, q, p))
bad = collections.Counter(); ex = {}
tiny = collections.Counter()
for t in b.GetTracks():
    if t.Type() == pcbnew.PCB_TRACE_T and T(t.GetLength()) < 0.25:
        tiny[t.GetNetname()] += 1
buried = []                                   # pads and vias: a joint inside their copper is not an exposed corner
for fp in b.GetFootprints():
    for pd in fp.Pads():
        buried.append(pd)
for v in b.GetTracks():
    if v.Type() == pcbnew.PCB_VIA_T:
        buried.append(v)
for k, lst in ends.items():
    if len(lst) != 2:
        continue
    (t1, q1, p), (t2, q2, _) = lst
    if any(it.GetNetCode() == t1.GetNetCode() and it.IsOnLayer(k[0]) and it.HitTest(p) for it in buried):
        continue
    a1 = math.atan2(q1.y - p.y, q1.x - p.x); a2 = math.atan2(q2.y - p.y, q2.x - p.x)
    ang = abs(math.degrees(a1 - a2)) % 360
    ang = min(ang, 360 - ang)                 # angle between the two segments at the joint (180 = straight)
    if ang < 134:                             # 135 = 45 deg bend; less = 90 deg or acute
        bad[(t1.GetNetname(), round(ang))] += 1
        ex[(t1.GetNetname(), round(ang))] = (round(T(p.x) - 50, 2), round(T(p.y) - 50, 2), b.GetLayerName(k[0]))
print('joints sharper than 45 deg:', sum(bad.values()))
for k, v in bad.most_common(25):
    print(' ', v, k, ex[k])
print('tiny segments (<0.25 mm) by net:', dict(tiny.most_common(10)))
