import json, sys, collections
d = json.load(open(sys.argv[1], encoding='utf-8'))
for k in ('violations', 'unconnected_items', 'schematic_parity'):
    v = d.get(k, [])
    c = collections.Counter((x['type'], x['severity']) for x in v)
    print(k, len(v), dict(c))
show = sys.argv[2] if len(sys.argv) > 2 else ''
for x in d.get('violations', []):
    if show and x['type'] != show: continue
    if not show and x['severity'] != 'error': continue
    its = ' | '.join(i['description'][:70] + f" @({i['pos']['x']-50:.1f},{i['pos']['y']-50:.1f})" for i in x['items'])
    print(' ', x['type'], ':', its)
