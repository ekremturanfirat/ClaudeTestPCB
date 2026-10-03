"""Placement checks the DRC can't do (library parts have no courtyards): pad gaps between parts, body overlaps,
mounting-hole keepouts, parts near the edge."""
import pcbnew, sys, math, itertools
b = pcbnew.LoadBoard(sys.argv[1]); OX = OY = 50.0
import placement
T = pcbnew.ToMM
fps = [f for f in b.GetFootprints()]
def body(f):
    bb = f.GetBoundingBox(False)       # pads + graphics, no text
    return (T(bb.GetLeft()) - OX, T(bb.GetTop()) - OY, T(bb.GetRight()) - OX, T(bb.GetBottom()) - OY)
def padbox(p):
    bb = p.GetBoundingBox()
    return (T(bb.GetLeft()) - OX, T(bb.GetTop()) - OY, T(bb.GetRight()) - OX, T(bb.GetBottom()) - OY)
def gap(a, b):
    dx = max(a[0] - b[2], b[0] - a[2], 0); dy = max(a[1] - b[3], b[1] - a[3], 0)
    return math.hypot(dx, dy)
def ovl(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
fine = {'U6', 'U3'}                            # QFN/LQFN: 2 mm rework clearance to non-decoupling parts
issues = []
for f, g in itertools.combinations(fps, 2):
    rf, rg = f.GetReference(), g.GetReference()
    A, B = body(f), body(g)
    if gap(A, B) > 3: continue
    o = ovl(A, B)
    if o > 0.05 and not (rf.startswith('NT') or rg.startswith('NT')):
        issues.append(f'OVERLAP {rf}-{rg} {o:.2f}mm2')
    for p in f.Pads():
        for q in g.Pads():
            if p.GetNetname() and p.GetNetname() == q.GetNetname():
                continue
            d = gap(padbox(p), padbox(q))
            if d < 1.0:
                issues.append(f'PADGAP {rf}.{p.GetNumber()}-{rg}.{q.GetNumber()} {d:.2f}')
for f in fps:
    r = f.GetReference()
    if r.startswith('H'): continue
    A = body(f)
    for hx, hy in placement.HOLES:
        cx = min(max(hx, A[0]), A[2]); cy = min(max(hy, A[1]), A[3])
        if math.hypot(cx - hx, cy - hy) < 3.5:
            issues.append(f'HOLE keepout {r} vs ({hx},{hy}) {math.hypot(cx-hx, cy-hy):.2f}')
    if A[0] < -0.01 or A[1] < -0.01 or A[2] > placement.W + .01 or A[3] > placement.H + .01:
        if r != 'U1': issues.append(f'OFFBOARD {r} {A}')
seen = set()
for i in issues:
    k = i.split(' ')[0] + i.split(' ')[1].split('-')[0].split('.')[0] + '-' + (i.split(' ')[1].split('-')[1].split('.')[0] if '-' in i.split(' ')[1] else '')
    if k in seen: continue
    seen.add(k); print(i)
print(len(seen), 'distinct issues')
edge = sorted(f.GetReference() for f in fps if not f.GetReference().startswith(('H', 'FID')) and
              min(body(f)[0], body(f)[1], placement.W - body(f)[2], placement.H - body(f)[3]) < 3.5)
print('within 3.5 mm of the edge:', ' '.join(edge))
