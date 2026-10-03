"""Import a Freerouting session into the board, keep the pre-routed (locked) copper, refill zones.
KiCad's SES import replaces all tracks, so the locked pre-routing is saved first and re-added if missing.
Usage: python.exe ses_import.py <board> <session.ses> <out board>
"""
import sys
import pcbnew


def key(t):
    if t.Type() == pcbnew.PCB_VIA_T:
        return ('v', t.GetPosition().x, t.GetPosition().y, t.GetNetCode())
    a, b = t.GetStart(), t.GetEnd()
    return ('t', min((a.x, a.y), (b.x, b.y)), max((a.x, a.y), (b.x, b.y)), t.GetLayer(), t.GetNetCode())


def main(board, ses, out):
    b = pcbnew.LoadBoard(board)
    locked = [t.Duplicate() for t in b.GetTracks() if t.IsLocked()]
    assert pcbnew.ImportSpecctraSES(b, ses)
    have = {key(t) for t in b.GetTracks()}
    readded = 0
    for t in locked:
        if key(t) not in have:
            b.Add(t); readded += 1
    fixed = 0                                     # SES import takes the drill from the net class: keep a 0.15 mm ring
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            w, d = t.GetWidth(pcbnew.F_Cu), t.GetDrillValue()
            if w - d < pcbnew.FromMM(0.3) - 10:
                t.SetDrill(w - pcbnew.FromMM(0.3)); fixed += 1
    print(f'via drills restored (annular ring 0.15 mm): {fixed}')
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.Save(out)
    print(f'imported {ses}: {len(list(b.GetTracks()))} track items, re-added {readded} pre-routed items')


if __name__ == '__main__':
    main(*sys.argv[1:4])
