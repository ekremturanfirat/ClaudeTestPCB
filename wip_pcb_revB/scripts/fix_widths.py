"""Post-route clean-up (rule 2.2): Freerouting necks tracks down to 0.15 mm at some pads. Widen every track
below the 0.2 mm lab default to 0.2 mm, then give back 0.15 mm (PCBWay standard-price floor) only to segments
where the wider track would break clearance (checked with kicad-cli DRC).
Usage: python.exe fix_widths.py <board>
"""
import sys, json, subprocess, os
import pcbnew

CLI = 'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
MM, T = pcbnew.FromMM, pcbnew.ToMM


def drc(path, out):
    subprocess.run([CLI, 'pcb', 'drc', '--severity-error', '--format', 'json', '-o', out, path],
                   check=True, capture_output=True)
    return json.load(open(out, encoding='utf-8'))


def main(path):
    b = pcbnew.LoadBoard(path)
    thin = []
    for t in b.GetTracks():
        if t.Type() == pcbnew.PCB_TRACE_T and t.GetWidth() < MM(0.2) - 10 and not t.IsLocked():
            thin.append((t.m_Uuid.AsString(), t.GetWidth()))
            t.SetWidth(MM(0.2))
    b.Save(path)
    d = drc(path, path + '.drc.json')
    bad = set()
    for v in d['violations']:
        if v['type'] in ('clearance', 'shorting_items', 'hole_clearance'):
            for it in v['items']:
                bad.add(it['uuid'])
    b = pcbnew.LoadBoard(path)
    back = 0
    ids = {u for u, _ in thin}
    for t in b.GetTracks():
        u = t.m_Uuid.AsString()
        if u in ids and u in bad:
            t.SetWidth(MM(0.15)); back += 1
    b.Save(path)
    print(f'{len(thin)} thin segments widened to 0.2 mm; {back} kept at 0.15 mm (no room at the pad)')


if __name__ == '__main__':
    main(sys.argv[1])
