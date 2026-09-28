"""Export the board to Specctra DSN and adapt it for Freerouting:
  - rule areas (fan-out / Kelvin areas) are not keepouts for routing: removed
  - power pours on F.Cu become keepouts (signals cross them on B.Cu), their planes are removed
  - the B.Cu GND plane stays: GND pads already have their vias, the router treats them as connected
  - pour-net pins that the pour already covers are removed from the netlist, so the router only connects
    the pads outside the pour (to the pre-placed port vias)
Usage: python.exe dsn_prep.py <board> <out.dsn>
"""
import sys, re
import pcbnew

T = pcbnew.ToMM


def blocks(text, key):
    """Yield (start, end) of every '(key ...)' block (balanced parentheses, quote-aware)."""
    i = 0
    pat = re.compile(r'\(' + re.escape(key) + r'[\s)]')
    while True:
        m = pat.search(text, i)
        if not m:
            return
        s = m.start(); depth = 0; j = s; q = False
        while j < len(text):
            c = text[j]
            if c == '"':
                q = not q
            elif not q:
                if c == '(':
                    depth += 1
                elif c == ')':
                    depth -= 1
                    if depth == 0:
                        break
            j += 1
        yield s, j + 1
        i = j + 1


def covered_pins(board):
    zones = {}
    for z in board.Zones():
        if z.GetIsRuleArea() or z.GetNetname() in ('', 'GND'):
            continue
        zones.setdefault(z.GetNetname(), []).append(z)
    cov = {}
    for fp in board.GetFootprints():
        for p in fp.Pads():
            zl = zones.get(p.GetNetname())
            if zl and any(z.HitTestFilledArea(z.GetLayer(), p.GetPosition()) for z in zl):
                cov.setdefault(p.GetNetname(), set()).add(f'{fp.GetReference()}-{p.GetNumber()}')
    return cov


def main(board_path, out, relax_hv=0):
    b = pcbnew.LoadBoard(board_path)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    tmp = out + '.raw'
    assert pcbnew.ExportSpecctraDSN(b, tmp)
    t = open(tmp, encoding='utf-8').read()

    # structure: drop keepouts (rule areas), turn non-GND planes into F.Cu keepouts, keep the B.Cu GND plane
    out_parts, last = [], 0
    spans = sorted(list(blocks(t, 'keepout')) + list(blocks(t, 'plane')))
    n_ko = n_pl = 0
    for s, e in spans:
        out_parts.append(t[last:s])
        blk = t[s:e]
        if blk.startswith('(plane'):
            m = re.match(r'\(plane\s+("[^"]*"|\S+)\s+\(polygon\s+(\S+)', blk)
            net, layer = m.group(1).strip('"'), m.group(2)
            if net == 'GND':
                if layer == 'In1.Cu':              # every GND pad has its via: the router sees them joined on L2
                    out_parts.append(blk)
            else:
                out_parts.append('(keepout "" ' + blk[blk.index('(polygon'):])
                n_pl += 1
        else:
            n_ko += 1
        last = e
    out_parts.append(t[last:])
    t = ''.join(out_parts)

    # NPTH holes (mounting holes: 7 mm keepout per rule 3.1; connector pegs: hole + 2 x 0.35 mm) on every copper layer
    ko = []
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                x, y = pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y)
                r = 3.5 if fp.GetReference().startswith('H') else pcbnew.ToMM(p.GetDrillSize().x) / 2 + 0.35
                for L in ('F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'):
                    pts = ' '.join(f'{(x + dx) * 1000:.0f} {-(y + dy) * 1000:.0f}' for dx, dy in ((-r, -r), (r, -r), (r, r), (-r, r)))
                    ko.append(f'    (keepout "" (polygon {L} 0 {pts}))')
    st = t.index('(structure')
    i = t.index('(via ', st)                       # after the layer definitions, before the via list
    i = t.rindex('\n', st, i) + 1
    t = t[:i] + '\n'.join(ko) + '\n' + t[i:]

    # network: remove pour-covered pins; nets that are already complete (pre-routing + pours) are not routed
    import subprocess, json as _j
    subprocess.run(['C:/Program Files/KiCad/10.0/bin/kicad-cli.exe', 'pcb', 'drc', '--severity-error', '--format',
                    'json', '-o', out + '.drc.json', board_path], check=True, capture_output=True)
    open_nets = set()
    for x in _j.load(open(out + '.drc.json', encoding='utf-8'))['unconnected_items']:
        for it in x['items']:
            mm = re.search(r'\[(.*?)\]', it['description'])
            if mm:
                open_nets.add(mm.group(1))
    cov = covered_pins(b)
    net_spans = list(blocks(t, 'net'))
    parts, last, pruned = [], 0, 0
    for s, e in net_spans:
        blk = t[s:e]
        m = re.match(r'\(net\s+("[^"]*"|\S+)', blk)
        if not m or '(pins' not in blk:
            continue
        name = m.group(1).strip('"')
        pour_nets = {z.GetNetname() for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname() not in ('', 'GND')}
        if name not in open_nets and name in pour_nets:   # complete via its pour (a keepout here): one pin only
            ps = blk.index('(pins') + 5
            pe = blk.index(')', ps)
            pins = blk[ps:pe].split()
            blk = blk[:ps] + ' ' + (pins[0] if pins else '') + blk[pe:]
            parts.append(t[last:s]); parts.append(blk); last = e
            continue
        if name in cov:
            ps = blk.index('(pins') + 5
            pe = blk.index(')', ps)
            pins = blk[ps:pe].split()
            keep = [p for p in pins if p.strip('"').split('@')[0] not in cov[name]]   # 'Q2-3@2' = copy of pad 3
            pruned += len(pins) - len(keep)
            blk = blk[:ps] + ' ' + ' '.join(keep) + blk[pe:]
        parts.append(t[last:s]); parts.append(blk); last = e
    parts.append(t[last:])
    t = ''.join(parts)
    if relax_hv:                              # router: IC pins can't be escaped at 0.6 mm; KiCad DRC checks the real rules
        t = re.sub(r'(\(class HV[^(]*(?:\([^()]*(?:\([^()]*\))*[^()]*\)[^(]*)*?\(rule\s*\(width \d+\)\s*\(clearance )600', r'\g<1>' + str(relax_hv), t)
    open(out, 'w', encoding='utf-8').write(t)
    print(f'{out}: removed {n_ko} rule-area keepouts, {n_pl} pours -> keepouts, pruned {pruned} covered pins')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 0)
