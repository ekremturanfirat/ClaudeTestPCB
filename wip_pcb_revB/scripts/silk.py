"""Silkscreen reference placement (rules 2.4 / 3.6): 1.0 mm / 0.15 mm text, 0 or 90 deg only, never on pads,
never under another part, inside the board. Tries positions around the part, nearest first.
Usage: python.exe silk.py <board>
"""
import sys, math
import pcbnew

MM, T = pcbnew.FromMM, pcbnew.ToMM


def box(bb, g=0.0):
    return (T(bb.GetLeft()) - g, T(bb.GetTop()) - g, T(bb.GetRight()) + g, T(bb.GetBottom()) + g)


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def main(path):
    b = pcbnew.LoadBoard(path)
    eb = b.GetBoardEdgesBoundingBox()
    edge = box(eb, -0.6)                               # text must stay 0.6 mm inside the outline
    pads, bodies = [], {}
    for fp in b.GetFootprints():
        for p in fp.Pads():
            pads.append(box(p.GetBoundingBox(), 0.15))
        bodies[fp.GetReference()] = box(fp.GetBoundingBox(False, False))
    for v in b.GetTracks():
        if v.Type() == pcbnew.PCB_VIA_T:
            pads.append(box(v.GetBoundingBox(), 0.1))     # vias are tented, but keep text off them for legibility
    placed = []
    for d in b.Drawings():                              # connector labels / board info go first: refs avoid them
        if isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() == pcbnew.F_SilkS:   # same side as the refs
            placed.append(box(d.GetBoundingBox(), 0.1))
    fails = []
    fps = sorted(b.GetFootprints(), key=lambda f: -len(f.Pads()))    # big parts first
    for fp in fps:
        ref = fp.GetReference()
        txt = fp.Reference()
        if ref.startswith(('H', 'FID', 'NT', 'LOGO', 'QR', 'G')):
            txt.SetVisible(False)
            continue
        txt.SetVisible(True)                           # library hides the field (it used a duplicate user text)
        txt.SetLayer(pcbnew.B_SilkS if fp.IsFlipped() else pcbnew.F_SilkS)
        txt.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
        txt.SetTextThickness(MM(0.15))
        own = bodies[ref]
        cx, cy = (own[0] + own[2]) / 2, (own[1] + own[3]) / 2
        others = [v for k, v in bodies.items() if k != ref and not k.startswith('FID')]
        best = None
        for gap in (0.25, 0.6, 1.0, 1.6, 2.4, 3.2):
            cands = []
            for ang in (0, 90):
                txt.SetTextAngleDegrees(ang)
                txt.SetPosition(pcbnew.VECTOR2I(MM(cx), MM(cy)))
                tb = box(txt.GetBoundingBox())
                hw, hh = (tb[2] - tb[0]) / 2, (tb[3] - tb[1]) / 2
                cands += [(ang, cx, own[1] - gap - hh), (ang, cx, own[3] + gap + hh),
                          (ang, own[0] - gap - hw, cy), (ang, own[2] + gap + hw, cy),
                          (ang, own[0] - gap - hw, own[1] - gap - hh), (ang, own[2] + gap + hw, own[1] - gap - hh),
                          (ang, own[0] - gap - hw, own[3] + gap + hh), (ang, own[2] + gap + hw, own[3] + gap + hh)]
            for ang, x, y in cands:
                txt.SetTextAngleDegrees(ang)
                txt.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
                tb = box(txt.GetBoundingBox(), 0.1)
                if not (edge[0] <= tb[0] and tb[2] <= edge[2] and edge[1] <= tb[1] and tb[3] <= edge[3]):
                    continue
                if any(hit(tb, p) for p in pads) or any(hit(tb, o) for o in others) or any(hit(tb, q) for q in placed):
                    continue
                d = math.hypot(x - cx, y - cy) + (0.3 if ang == 90 else 0)
                if best is None or d < best[0]:
                    best = (d, ang, x, y)
            if best:
                break
        if best:
            _, ang, x, y = best
            txt.SetTextAngleDegrees(ang)
            txt.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            placed.append(box(txt.GetBoundingBox(), 0.1))
        else:                                          # no legal spot at 1.0 mm: reference on the assembly
            fails.append(ref)                          # drawing (F.Fab) only, not on the silkscreen
            txt.SetPosition(pcbnew.VECTOR2I(MM(cx), MM(cy)))
            txt.SetTextAngleDegrees(0)
            txt.SetLayer(pcbnew.B_Fab if fp.IsFlipped() else pcbnew.F_Fab)
    b.Save(path)
    print('silk refs placed; no free spot for:', fails)


if __name__ == '__main__':
    main(sys.argv[1])
