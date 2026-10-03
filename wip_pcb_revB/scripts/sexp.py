import re

_tok = re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)', re.S)


def parse(text):
    stack = [[]]
    for m in _tok.finditer(text):
        t = m.group(1)
        if t == '(':
            stack.append([])
        elif t == ')':
            node = stack.pop()
            stack[-1].append(node)
        elif t.startswith('"'):
            stack[-1].append(t[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            stack[-1].append(t)
    return stack[0][0]


def load(path):
    with open(path, encoding='utf-8') as f:
        return parse(f.read())


def kids(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def kid(node, name):
    k = kids(node, name)
    return k[0] if k else None


def val(node, name, default=None):
    k = kid(node, name)
    return k[1] if k and len(k) > 1 else default


def props(node):
    out = {}
    for p in kids(node, 'property'):
        eff = kid(p, 'effects')
        hidden = False
        if eff is not None:
            h = kid(eff, 'hide')
            hidden = (h is not None and (len(h) == 1 or h[1] == 'yes')) or 'hide' in eff
        hk = kid(p, 'hide')
        if hk is not None and (len(hk) == 1 or hk[1] == 'yes'):
            hidden = True
        out[p[1]] = {'value': p[2], 'hidden': hidden, 'at': kid(p, 'at')}
    return out
