"""S-expression reader/writer that round-trips KiCad files (keeps quoted vs bare tokens)."""
import re


class Q(str):
    """A quoted string token."""


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
            stack[-1].append(Q(t[1:-1].replace('\\"', '"').replace('\\\\', '\\')))
        else:
            stack[-1].append(t)
    return stack[0][0]


def load(path):
    with open(path, encoding='utf-8') as f:
        return parse(f.read())


def _atom(a):
    if isinstance(a, Q):
        return '"' + a.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'
    if isinstance(a, bool):
        return 'yes' if a else 'no'
    if isinstance(a, float):
        s = f'{a:.4f}'.rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(a)


def dumps(node, indent=0):
    if not isinstance(node, list):
        return _atom(node)
    simple = all(not isinstance(c, list) for c in node)
    if simple:
        return '(' + ' '.join(_atom(c) for c in node) + ')'
    pad = '\t' * (indent + 1)
    out = '(' + _atom(node[0])
    for c in node[1:]:
        if isinstance(c, list):
            out += '\n' + pad + dumps(c, indent + 1)
        else:
            out += ' ' + _atom(c)
    return out + '\n' + '\t' * indent + ')'


def kids(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def kid(node, name):
    k = kids(node, name)
    return k[0] if k else None


def val(node, name, default=None):
    k = kid(node, name)
    return k[1] if k and len(k) > 1 else default
