"""Library symbol access + pin geometry for the schematic generator."""
import copy, os
from kisexp import Q, load, kids, kid, val

LIBDIR = os.path.join(os.path.dirname(__file__), 'PLlib', 'symbols')
_cache = {}


class SymDef:
    def __init__(self, nick, name, node):
        self.nick, self.name, self.node = nick, name, node
        self.lib_id = f'{nick}:{name}'
        self.is_power = kid(node, 'power') is not None
        self.props = {}
        for p in kids(node, 'property'):
            self.props[str(p[1])] = str(p[2])
        self.pins = []  # dicts: number, name, type, x, y, ang, length, unit
        for sub in kids(node, 'symbol'):
            parts = str(sub[1]).rsplit('_', 2)
            unit, style = int(parts[-2]), int(parts[-1])
            if style not in (0, 1):
                continue
            for p in kids(sub, 'pin'):
                at = kid(p, 'at')
                self.pins.append(dict(number=str(val(p, 'number')), name=str(val(p, 'name')), type=p[1],
                                      x=float(at[1]), y=float(at[2]), ang=int(float(at[3])) if len(at) > 3 else 0,
                                      length=float(val(p, 'length', 0)), unit=unit,
                                      hidden=kid(p, 'hide') is not None))

    def body_bbox(self):
        """Library-coordinate bbox of drawn graphics (rectangles/polylines/circles), excluding pins."""
        xs, ys = [], []
        def walk(n):
            if not isinstance(n, list) or not n:
                return
            if n[0] in ('rectangle',):
                for k in ('start', 'end'):
                    c = kid(n, k); xs.append(float(c[1])); ys.append(float(c[2]))
            elif n[0] == 'polyline':
                for xy in kids(kid(n, 'pts'), 'xy'):
                    xs.append(float(xy[1])); ys.append(float(xy[2]))
            elif n[0] == 'circle':
                c = kid(n, 'center'); r = float(val(n, 'radius'))
                xs.extend([float(c[1]) - r, float(c[1]) + r]); ys.extend([float(c[2]) - r, float(c[2]) + r])
            elif n[0] == 'pin':
                return
            for c in n[1:]:
                walk(c)
        for sub in kids(self.node, 'symbol'):
            walk(sub)
        if not xs:
            return None
        return min(xs), min(ys), max(xs), max(ys)

    def cache_node(self):
        n = copy.deepcopy(self.node)
        n[1] = Q(self.lib_id)
        return n

    def pins_by_number(self, num):
        return [p for p in self.pins if p['number'] == str(num)]

    def pins_by_name(self, name):
        return [p for p in self.pins if p['name'] == name]


def get(lib_id):
    if lib_id in _cache:
        return _cache[lib_id]
    nick, name = lib_id.split(':', 1)
    path = os.path.join(LIBDIR, nick + '.kicad_sym')
    tree = load(path)
    for s in kids(tree, 'symbol'):
        if str(s[1]) == name:
            if kid(s, 'extends') is not None:
                raise ValueError(f'{lib_id}: extends not supported')
            d = SymDef(nick, name, s)
            _cache[lib_id] = d
            return d
    raise KeyError(f'{lib_id} not found in {path}')


# KiCad symbol transform. Library coords are Y-up, schematic Y-down.
# Matrices are (a, b, c, d): sch_dx = a*x + b*y, sch_dy = c*x + d*y  (x,y in library coords)
_ROT = {0: (1, 0, 0, -1), 90: (0, -1, -1, 0), 180: (-1, 0, 0, 1), 270: (0, 1, 1, 0)}


def matrix(rot=0, mirror=None):
    a, b, c, d = _ROT[rot % 360]
    if mirror == 'x':      # mirror about the X axis (flip vertically)
        c, d = -c, -d
    elif mirror == 'y':    # mirror about the Y axis (flip horizontally)
        a, b = -a, -b
    return a, b, c, d


def xform(pt, at, rot=0, mirror=None):
    a, b, c, d = matrix(rot, mirror)
    x, y = pt
    return (round(at[0] + a * x + b * y, 4), round(at[1] + c * x + d * y, 4))


def pin_dir(pin, rot=0, mirror=None):
    """Unit vector (schematic coords) pointing from the pin tip AWAY from the symbol body."""
    import math
    ang = math.radians(pin['ang'])
    bx, by = math.cos(ang), math.sin(ang)          # tip -> body, library coords
    a, b, c, d = matrix(rot, mirror)
    sx, sy = a * bx + b * by, c * bx + d * by        # tip -> body, schematic coords
    return (-round(sx), -round(sy))
