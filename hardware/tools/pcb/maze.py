"""Grid A* router for one connection (system-Python side). Reads maze_export.py JSON, rasterises obstacles at
0.05 mm, searches on 3 routable layers (L1, L3, L4) with 8-direction moves and vias (cost 40), writes the path
as straight segments + via points. Usage: python maze.py <in.json> <out.json>
"""
import sys, json, heapq, math
import numpy as np
from PIL import Image, ImageDraw

G = 0.05


def main(inp, outp):
    d = json.load(open(inp))
    x0, y0, x1, y1 = d['edge']
    nx, ny = int((x1 - x0) / G) + 1, int((y1 - y0) / G) + 1
    toc = lambda x, y: (int(round((x - x0) / G)), int(round((y - y0) / G)))

    def raster(key):
        grids = []
        for li in range(3):
            im = Image.new('1', (nx, ny), 0)
            dr = ImageDraw.Draw(im)
            for poly in d[key][str(li)]:
                if len(poly) >= 3:
                    dr.polygon([((x - x0) / G, (y - y0) / G) for x, y in poly], fill=1)
            for hx, hy, r in d['holes']:
                rr = (r + (d['w'] / 2 if key == 'track' else 0.3)) / G
                cx, cy = (hx - x0) / G, (hy - y0) / G
                dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=1)
            grids.append(np.array(im, dtype=bool))
        return grids

    blk, vblk = raster('track'), raster('via')
    vfree = ~(vblk[0] | vblk[1] | vblk[2])
    xa, ya, la, xb, yb, lb = d['ends']
    s, g = toc(xa, ya) + (la,), toc(xb, yb) + (lb,)
    for (cx, cy, L) in (s, g):                        # the end item is ours: clear a small disc on its own layer
        rr = int(0.35 / G)
        blk[L][max(0, cy - rr):cy + rr + 1, max(0, cx - rr):cx + rr + 1] = False
    goal = []                                         # goal cells: any copper of the other island
    for li in range(3):
        im = Image.new('1', (nx, ny), 0); dr = ImageDraw.Draw(im)
        for poly in d.get('goal', {}).get(str(li), []):
            if len(poly) >= 3:
                dr.polygon([((x - x0) / G, (y - y0) / G) for x, y in poly], fill=1)
        gm = np.array(im, dtype=bool)
        if d.get('goal'):
            blk[li] &= ~gm                            # reaching our own copper is allowed
        goal.append(gm)
    from scipy.ndimage import distance_transform_edt
    anyg = goal[0] | goal[1] | goal[2]
    hmap = distance_transform_edt(~anyg) if anyg.any() else None
    moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    h = (lambda p: hmap[p[1], p[0]]) if hmap is not None else (lambda p: math.hypot(p[0] - g[0], p[1] - g[1]))
    # state = (x, y, layer, dir); turning costs extra so paths are long straight runs with 45 deg bends (rule 3.3);
    # 90 deg turns in one step are not allowed
    s4 = s + (8,)
    openq = [(h(s), 0.0, s4, None)]
    came, cost = {}, {s4: 0.0}
    found = None
    TURN45, VIA = 3.0, 40.0
    while openq:
        f, c, p, par = heapq.heappop(openq)
        if p in came:
            continue
        came[p] = par
        x, y, L, dd = p
        if (hmap is not None and goal[L][y, x]) or (hmap is None and (x, y, L) == g):
            found = p
            break
        for k, (dx, dy, mc) in enumerate(moves):
            if dd != 8 and dd != k:
                turn = abs(math.atan2(dy, dx) - math.atan2(moves[dd][1], moves[dd][0]))
                turn = min(turn, 2 * math.pi - turn)
                if turn > math.pi / 4 + 1e-6:
                    continue
                mc = mc + TURN45
            q = (x + dx, y + dy, L, k)
            if 0 <= q[0] < nx and 0 <= q[1] < ny and not blk[L][q[1], q[0]]:
                nc = c + mc
                if nc < cost.get(q, 1e18):
                    cost[q] = nc
                    heapq.heappush(openq, (nc + h(q), nc, q, p))
        if vfree[y, x]:
            for L2 in range(3):
                if L2 != L and not blk[L2][y, x]:
                    q = (x, y, L2, 8)
                    nc = c + VIA
                    if nc < cost.get(q, 1e18):
                        cost[q] = nc
                        heapq.heappush(openq, (nc + h(q), nc, q, p))
    if not found:
        json.dump({'ok': False}, open(outp, 'w'))
        print('no path')
        return
    pts = []
    p = found
    while p:
        pts.append(p[:3])
        p = came[p]
    pts.reverse()
    segs, vias = [], []
    cur = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        if a[2] != b[2]:
            segs.append(cur); vias.append(a); cur = [b]
        else:
            cur.append(b)
    segs.append(cur)
    out = []
    for sg in segs:
        L = sg[0][2]
        simp = [sg[0]]
        for i in range(1, len(sg) - 1):
            d1 = (sg[i][0] - simp[-1][0], sg[i][1] - simp[-1][1])
            d2 = (sg[i + 1][0] - sg[i][0], sg[i + 1][1] - sg[i][1])
            if d1[0] * d2[1] - d1[1] * d2[0] != 0:
                simp.append(sg[i])
        simp.append(sg[-1])
        out.append({'layer': L, 'pts': [(x0 + q[0] * G, y0 + q[1] * G) for q in simp]})
    json.dump({'ok': True, 'segs': out, 'vias': [(x0 + v[0] * G, y0 + v[1] * G) for v in vias]}, open(outp, 'w'))
    print('path:', sum(len(s_['pts']) - 1 for s_ in out), 'segments,', len(vias), 'vias')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
