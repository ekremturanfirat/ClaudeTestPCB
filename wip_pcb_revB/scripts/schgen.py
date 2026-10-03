"""Rule-compliant KiCad schematic generator (METU PowerLab rules).

Every pin gets its own wire stub on the 2.54 mm grid; nets are joined by drawn wires,
power symbols (GND down / rails up) or labels at the stub ends. Nothing touches a pin
directly. The intended netlist is recorded so it can be compared to KiCad's own netlist.
"""
import uuid, math, collections
from kisexp import Q, dumps
import schlib

G = 2.54
PROJECT = 'ESC3Phase'


def U():
    return Q(str(uuid.uuid4()))


def snap(v):
    return round(round(v / G) * G, 4)


def ongrid(p):
    return all(abs(c / G - round(c / G)) < 1e-6 for c in p)


def font(size=1.27, bold=False):
    f = ['font', ['size', size, size]]
    if bold:
        f.append(['bold', 'yes'])
    return f


def effects(size=1.27, justify=None, hide=False, bold=False):
    e = ['effects', font(size, bold)]
    if justify:
        e.append(['justify'] + justify.split())
    if hide:
        e.append(['hide', 'yes'])
    return e


class Part:
    def __init__(self, sheet, ref, lib_id, at, rot=0, mirror=None, value=None, footprint=None, fields=None,
                 dnp=False, unit=1):
        self.sheet, self.ref, self.lib_id = sheet, ref, lib_id
        self.sym = schlib.get(lib_id)
        assert ongrid(at), f'{ref} not on grid: {at}'
        self.at, self.rot, self.mirror, self.unit, self.dnp = at, rot, mirror, unit, dnp
        self.value = value if value is not None else self.sym.props.get('Value')
        self.footprint = footprint if footprint is not None else self.sym.props.get('Footprint', '')
        self.fields = fields or {}
        self.uuid = U()
        self.pin_net = {}

    def pins(self, key):
        """All physical pin instances matching a pin number or name."""
        ps = self.sym.pins_by_number(key) or self.sym.pins_by_name(key)
        ps = [p for p in ps if p['unit'] in (0, self.unit)]
        if not ps:
            raise KeyError(f'{self.ref}: no pin {key!r}')
        return ps

    def pin_pos(self, p):
        return schlib.xform((p['x'], p['y']), self.at, self.rot, self.mirror)

    def pin_out(self, p):
        return schlib.pin_dir(p, self.rot, self.mirror)


class Sheet:
    def __init__(self, filename, title, page_title=None):
        self.filename, self.title = filename, title
        self.uuid = U()
        self.parts, self.wires, self.junctions, self.labels, self.nocons = [], [], [], [], []
        self.texts, self.images, self.power, self.sheets = [], [], [], []
        self.pwr_count = 0
        self.stub_ends = []   # (point, net, part_ref, pin_number)

    # ---- placement ----
    def add(self, ref, lib_id, at, **kw):
        p = Part(self, ref, lib_id, (snap(at[0]), snap(at[1])), **kw)
        self.parts.append(p)
        return p

    # ---- low level drawing ----
    def wire(self, a, b):
        assert ongrid(a) and ongrid(b), f'wire off grid {a}->{b}'
        assert a[0] == b[0] or a[1] == b[1], f'wire not orthogonal {a}->{b}'
        if a != b:
            self.wires.append((a, b))

    def path(self, pts):
        for a, b in zip(pts, pts[1:]):
            self.wire(a, b)

    def label(self, name, at, kind='label', shape='bidirectional', angle=0):
        assert ongrid(at), f'label off grid {name} {at}'
        self.labels.append(dict(name=name, at=at, kind=kind, shape=shape, angle=angle))

    def power_symbol(self, net, at):
        assert ongrid(at)
        lib = 'METUPowerLab_Schematic_PowerSymbols:' + ('GND' if net == 'GND' else '+V_RAIL')
        self.power.append(dict(net=net, at=at, lib=lib))

    def flag(self, at):
        self.power.append(dict(net='PWR_FLAG', at=at, lib='METUPowerLab_Schematic_PowerSymbols:PWR_FLAG'))

    def flag_label(self, net, at):
        """Local label at `at`, wire to the right, PWR_FLAG at the end."""
        end = (round(at[0] + G * 4, 4), at[1])
        self.label(net, at, kind='label', angle=180)
        self.wire(at, end)
        self.flag(end)

    def flag_net(self, net, at):
        """Power symbol at `at`, short wire to the right, PWR_FLAG at the wire end (no overlapping symbols)."""
        end = (round(at[0] + G * 4, 4), at[1])
        self.power_symbol(net, at)
        self.wire(at, end)
        self.flag(end)

    def text(self, s, at, size=1.27, bold=False):
        self.texts.append(dict(text=s, at=at, size=size, bold=bold))

    # ---- pin level helpers ----
    def stub(self, part, key, length=2, which=None):
        """Draw a wire stub from pin tip outward; return stub end point(s)."""
        ends = []
        pins = part.pins(key)
        if which is not None:
            pins = [pins[which]]
        for p in pins:
            tip = part.pin_pos(p)
            dx, dy = part.pin_out(p)
            end = (round(tip[0] + dx * G * length, 4), round(tip[1] + dy * G * length, 4))
            self.wire(tip, end)
            ends.append((end, (dx, dy), p))
        return ends

    def conn(self, part, key, net, style='label', length=2, kind=None, shape='bidirectional', which=None, jog=1):
        """Connect pin(s) to a net with a stub + power symbol / label."""
        out = []
        for end, (dx, dy), p in self.stub(part, key, length, which):
            part.pin_net.setdefault(p['number'], set()).add(net)
            self.stub_ends.append((end, net, part.ref, p['number']))
            if style == 'power':
                self.power_symbol(net, end)
            elif style == 'label':
                if dx == 0:   # vertical stub: jog sideways so the label text reads horizontally
                    side = 1 if jog >= 0 else -1
                    end2 = (round(end[0] + side * G * abs(jog or 1), 4), end[1])
                    self.wire(end, end2)
                    end = end2
                    ang = 0 if side > 0 else 180
                else:
                    ang = 0 if dx > 0 else 180
                self.label(net, end, kind=kind or 'label', shape=shape, angle=ang)
            elif style == 'none':
                pass
            out.append(end)
        return out

    def group(self, part, keys, net, style='power', length=1, end_extra=1, kind=None, shape='passive'):
        """Join several pins (same side, same direction) with a wire, junctions at Ts, one symbol/label."""
        ends = []
        for k in keys:
            for e in self.stub(part, k, length):
                ends.append(e)
                part.pin_net.setdefault(e[2]['number'], set()).add(net)
                self.stub_ends.append((e[0], net, part.ref, e[2]['number']))
        dx, dy = ends[0][1]
        assert all(e[1] == (dx, dy) for e in ends), 'group pins must point the same way'
        pts = sorted([e[0] for e in ends], key=lambda p: (p[1], p[0]))
        if dx != 0:   # pins on a vertical line -> vertical joining wire; GND below, rails above
            x = pts[0][0]
            ys = [p[1] for p in pts]
            if style == 'power' and net != 'GND':
                top = (x, round(min(ys) - G * end_extra, 4))
                self.wire(top, (x, max(ys)))
                for p in pts:
                    if p[1] != max(ys):
                        self.junction(p)
                tip = top
            else:
                bottom = (x, round(max(ys) + G * end_extra, 4))
                self.wire((x, min(ys)), bottom)
                for p in pts:
                    if p[1] not in (min(ys),):
                        self.junction(p)
                tip = bottom
        else:
            y = pts[0][1]
            xs = [p[0] for p in pts]
            right = (round(max(xs) + G * end_extra, 4), y)
            self.wire((min(xs), y), right)
            for p in pts:
                if p[0] != min(xs):
                    self.junction(p)
            tip = right
        if style == 'power':
            self.power_symbol(net, tip)
        else:
            self.label(net, tip, kind=kind or 'label', shape=shape, angle=0 if dx != 0 else 0)
        return tip

    def power_turn(self, part, key, net, out=2, turn=2):
        """Stub out, then turn up (rails) or down (GND) so the power symbol clears neighbouring pins."""
        (end, (dx, dy), p), = self.stub(part, key, out)
        part.pin_net.setdefault(p['number'], set()).add(net)
        self.stub_ends.append((end, net, part.ref, p['number']))
        sign = 1 if net == 'GND' else -1
        tip = (end[0], round(end[1] + sign * G * turn, 4))
        self.wire(end, tip)
        self.power_symbol(net, tip)
        return tip

    def nc(self, part, key):
        for p in part.pins(key):
            tip = part.pin_pos(p)
            part.pin_net.setdefault(p['number'], set()).add(None)
            self.nocons.append(tip)

    def junction(self, at):
        assert ongrid(at)
        self.junctions.append(at)

    # ---- serialization ----
    def node(self, root_uuid, path_prefix, instances_for):
        out = ['kicad_sch', ['version', 20250114], ['generator', Q('eeschema')], ['generator_version', Q('9.0')],
               ['uuid', self.uuid], ['paper', Q('A4')],
               ['title_block', ['title', Q(self.title)], ['date', Q('2026-09-27')], ['rev', Q('B')],
                ['company', Q('METU PowerLab')],
                ['comment', 2, Q('Designer: ${DESIGNER}')], ['comment', 3, Q('Project No: ${PROJECTNUMBER}')]]]
        libs = ['lib_symbols']
        seen = set()
        for lid in [p.lib_id for p in self.parts] + [pw['lib'] for pw in self.power]:
            if lid not in seen:
                seen.add(lid)
                libs.append(schlib.get(lid).cache_node())
        out.append(libs)
        for j in self.junctions:
            out.append(['junction', ['at', j[0], j[1]], ['diameter', 0], ['color', 0, 0, 0, 0], ['uuid', U()]])
        for n in self.nocons:
            out.append(['no_connect', ['at', n[0], n[1]], ['uuid', U()]])
        for a, b in self.wires:
            out.append(['wire', ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]],
                        ['stroke', ['width', 0], ['type', 'default']], ['uuid', U()]])
        for t in self.texts:
            out.append(['text', Q(t['text']), ['exclude_from_sim', 'no'], ['at', t['at'][0], t['at'][1], 0],
                        effects(t['size'], 'left top', bold=t['bold']), ['uuid', U()]])
        for im in self.images:
            out.append(['image', ['at', im['at'][0], im['at'][1]], ['scale', im.get('scale', 1)], ['uuid', U()],
                        ['data', Q(im['data'])]])
        for l in self.labels:
            ang = l['angle']
            just = 'left bottom' if ang in (0, 90) else 'right bottom'
            if l['kind'] == 'label':
                out.append(['label', Q(l['name']), ['at', l['at'][0], l['at'][1], ang], effects(1.27, just), ['uuid', U()]])
            elif l['kind'] == 'hier':
                hj = 'left' if ang in (0, 90) else 'right'
                out.append(['hierarchical_label', Q(l['name']), ['shape', l['shape']], ['at', l['at'][0], l['at'][1], ang],
                            effects(1.27, hj), ['uuid', U()]])
            else:
                gj = 'left' if ang in (0, 90) else 'right'
                out.append(['global_label', Q(l['name']), ['shape', l['shape']], ['at', l['at'][0], l['at'][1], ang],
                            ['fields_autoplaced', 'yes'], effects(1.27, gj), ['uuid', U()],
                            ['property', Q('Intersheetrefs'), Q('${INTERSHEET_REFS}'), ['at', l['at'][0], l['at'][1], 0],
                             effects(1.27, gj, hide=True)]])
        # power symbols
        for pw in self.power:
            self.pwr_count += 1
            sd = schlib.get(pw['lib'])
            ref = ('#FLG' if pw['net'] == 'PWR_FLAG' else '#PWR') + f"{self.pwr_count:03d}"
            pw['ref'] = ref
            val = 'PWR_FLAG' if pw['net'] == 'PWR_FLAG' else pw['net']
            vy = pw['at'][1] + (3.81 if pw['lib'].endswith(':GND') else -3.81)
            out.append(self._symbol_node(pw['lib'], pw['at'], 0, None, ref, val, '', {}, sd, root_uuid, path_prefix,
                                         instances_for, value_at=(pw['at'][0], vy), ref_hidden=True))
        for p in self.parts:
            out.append(self._symbol_node(p.lib_id, p.at, p.rot, p.mirror, p.ref, p.value, p.footprint, p.fields, p.sym,
                                         root_uuid, path_prefix, instances_for, part=p))
        for pw in self.power:
            pass
        for sh in self.sheets:
            out.append(sh)
        if path_prefix == '/':
            out.append(['sheet_instances', ['path', Q('/'), ['page', Q('1')]]])
        out.append(['embedded_fonts', 'no'])
        return out

    def _symbol_node(self, lib_id, at, rot, mirror, ref, value, footprint, fields, sd, root_uuid, path_prefix,
                     instances_for, part=None, value_at=None, ref_hidden=False):
        uid = part.uuid if part else U()
        n = ['symbol', ['lib_id', Q(lib_id)], ['at', at[0], at[1], rot]]
        if mirror:
            n.append(['mirror', mirror])
        n += [['unit', part.unit if part else 1], ['exclude_from_sim', 'no'],
              ['in_bom', 'no' if sd.is_power or kid_bool(sd, 'in_bom') == 'no' else 'yes'],
              ['on_board', 'no' if sd.is_power else 'yes'], ['dnp', 'yes' if part and part.dnp else 'no'],
              ['uuid', uid]]
        # properties: copy all library props, override Reference/Value/Footprint + custom fields
        lib_props = [(str(p[1]), str(p[2]), p) for p in sd.node if isinstance(p, list) and p and p[0] == 'property']
        rx, ry, vx, vy = ref_value_pos(part, at) if part else (at[0], at[1], value_at[0], value_at[1])
        if part and '_rv' in part.fields:
            rx, ry, vx, vy = part.fields['_rv']
        fa = ((rot + 180) % 360 if rot in (90, 270) else 0) if part else 0
        jj = 'left'
        if part and '_fa' in part.fields:
            fa = int(part.fields['_fa']); jj = part.fields['_j']
        for name, v, pnode in lib_props:
            if name in ('ki_keywords', 'ki_fp_filters', 'ki_description'):
                continue
            if name == 'Reference':
                n.append(['property', Q('Reference'), Q(ref if isinstance(ref, str) else ref[0]), ['at', rx, ry, fa], effects(1.27, jj if part else None, hide=ref_hidden)])
            elif name == 'Value':
                n.append(['property', Q('Value'), Q(value), ['at', vx, vy, fa], effects(1.27, jj if part else None)])
            elif name == 'Footprint':
                n.append(['property', Q('Footprint'), Q(footprint or ''), ['at', at[0], at[1], 0], effects(1.27, hide=True)])
            else:
                n.append(['property', Q(name), Q(fields.get(name, v)), ['at', at[0], at[1], 0], effects(1.27, hide=True)])
        for name, v in fields.items():
            if name.startswith('_'):
                continue
            if name not in [x[0] for x in lib_props]:
                n.append(['property', Q(name), Q(v), ['at', at[0], at[1], 0], effects(1.27, hide=True)])
        for pn in sorted({p['number'] for p in sd.pins}):
            n.append(['pin', Q(pn), ['uuid', U()]])
        inst = ['instances', ['project', Q(PROJECT)]]
        for path, r in instances_for(self, ref, part):
            inst[1].append(['path', Q(path), ['reference', Q(r)], ['unit', part.unit if part else 1]])
        n.append(inst)
        return n


def kid_bool(sd, name):
    for c in sd.node:
        if isinstance(c, list) and c and c[0] == name:
            return c[1]
    return None


def ref_value_pos(part, at):
    """Reference+Value: right of vertical 2-pin parts, above everything else; always horizontal, left-justified."""
    pts = [schlib.xform((p['x'], p['y']), (0, 0), part.rot, part.mirror) for p in part.sym.pins] or [(0, 0)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    nump = len({p['number'] for p in part.sym.pins})
    if nump <= 2 and max(xs) - min(xs) < 0.01:            # vertical 2-pin part
        return (at[0] + 2.54, at[1] - 1.27, at[0] + 2.54, at[1] + 1.27)
    bb = part.sym.body_bbox()
    if bb:
        corners = [schlib.xform((x, y), (0, 0), part.rot, part.mirror) for x in (bb[0], bb[2]) for y in (bb[1], bb[3])]
        bx0 = min(c[0] for c in corners); by0 = min(c[1] for c in corners)
    else:
        bx0, by0 = min(xs), min(ys)
    x = snap_half(at[0] + bx0)
    top = at[1] + min(by0, min(ys))
    return (x, top - 3.175, x, top - 1.27)


def snap_half(v):
    return round(round(v / 1.27) * 1.27, 4)


class SheetSymbol:
    """A (sheet ...) node placed inside a parent sheet, pointing at a child Sheet file."""
    def __init__(self, parent, child, name, at, size, pins, page):
        self.parent, self.child, self.name, self.at, self.size, self.page = parent, child, name, at, size, page
        self.uuid = U()
        self.pins = pins  # list of (pin_name, shape, side 'L'/'R', index)
        self.pin_nets = {}
        assert ongrid(at)

    def pin_point(self, name):
        for pname, shape, side, idx in self.pins:
            if pname == name:
                x = self.at[0] if side == 'L' else self.at[0] + self.size[0]
                return (x, round(self.at[1] + G * (idx + 1), 4))
        raise KeyError(name)

    def node(self, parent_path):
        n = ['sheet', ['at', self.at[0], self.at[1]], ['size', self.size[0], self.size[1]],
             ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'], ['dnp', 'no'],
             ['fields_autoplaced', 'yes'], ['stroke', ['width', 0.1524], ['type', 'solid']],
             ['fill', ['color', 0, 0, 0, 0.0]], ['uuid', self.uuid],
             ['property', Q('Sheetname'), Q(self.name), ['at', self.at[0], round(self.at[1] - 0.7112, 4), 0],
              effects(1.27, 'left bottom')],
             ['property', Q('Sheetfile'), Q(self.child.filename),
              ['at', self.at[0], round(self.at[1] + self.size[1] + 0.5842, 4), 0], effects(1.27, 'left top')]]
        for pname, shape, side, idx in self.pins:
            x, y = self.pin_point(pname)
            n.append(['pin', Q(pname), shape, ['at', x, y, 180 if side == 'L' else 0], ['uuid', U()],
                      effects(1.27, 'left' if side == 'L' else 'right')])
        n.append(['instances', ['project', Q(PROJECT), ['path', Q(parent_path), ['page', Q(str(self.page))]]]])
        return n
