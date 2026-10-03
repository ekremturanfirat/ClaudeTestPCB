"""Rasterize a KiCad PDF plot and crop a board-coordinate window (mm, board origin top-left)."""
import sys, pymupdf
pdf, out, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:7])
page = pymupdf.open(pdf)[0]
# KiCad plots at 1:1 on A4, board top-left at (50, 50) mm page coords unless centred; find by drawing bbox
d = [p['rect'] for p in page.get_drawings()]
bx0 = min(r.x0 for r in d); by0 = min(r.y0 for r in d)
pt = 72 / 25.4
clip = pymupdf.Rect(bx0 + x0 * pt, by0 + y0 * pt, bx0 + x1 * pt, by0 + y1 * pt)
page.get_pixmap(dpi=int(sys.argv[7]) if len(sys.argv) > 7 else 300, clip=clip).save(out)
print('saved', out)
