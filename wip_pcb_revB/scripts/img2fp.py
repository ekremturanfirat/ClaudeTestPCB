"""Bitmap -> KiCad footprint on F.SilkS (like KiCad's Image Converter): dark pixels become filled rectangles
(horizontal runs merged, identical runs on consecutive rows merged into one rectangle).
Usage: python img2fp.py <image> <out.kicad_mod> <name> <width_mm> [threshold] [--invert-alpha]
"""
import sys, uuid
from PIL import Image


def rects(mask, w, h):
    runs_prev = {}
    out = []
    for y in range(h):
        runs = []
        x = 0
        while x < w:
            if mask[y * w + x]:
                s = x
                while x < w and mask[y * w + x]:
                    x += 1
                runs.append((s, x))
            else:
                x += 1
        cur = {}
        for r in runs:
            if r in runs_prev:
                cur[r] = runs_prev.pop(r)
            else:
                cur[r] = y
        for (s, e), y0 in runs_prev.items():
            out.append((s, y0, e, y))
        runs_prev = cur
    for (s, e), y0 in runs_prev.items():
        out.append((s, y0, e, h))
    return out


def main():
    src, out, name, width = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
    thr = int(sys.argv[5]) if len(sys.argv) > 5 else 128
    im = Image.open(src).convert('RGBA')
    px_mm = 0.1                                            # 0.1 mm grid; features stay >= silk minimum 0.15 mm
    cols = int(round(width / px_mm))
    rows = int(round(im.size[1] * cols / im.size[0]))
    im = im.resize((cols, rows), Image.LANCZOS)
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    g = Image.alpha_composite(bg, im).convert('L')
    mask = [1 if v < thr else 0 for v in g.getdata()]
    rs = rects(mask, cols, rows)
    ox, oy = cols * px_mm / 2, rows * px_mm / 2
    L = [f'(footprint "{name}"', '\t(version 20241229)', '\t(generator "pcbnew")', '\t(generator_version "10.0")',
         '\t(layer "F.Cu")', f'\t(descr "{name}, {cols * px_mm:.1f} x {rows * px_mm:.1f} mm, silkscreen")',
         '\t(attr board_only exclude_from_pos_files exclude_from_bom allow_missing_courtyard)',
         f'\t(property "Reference" "G***" (at 0 {oy + 1.0:.2f} 0) (layer "F.SilkS") (hide yes)'
         f' (uuid "{uuid.uuid4()}") (effects (font (size 1 1) (thickness 0.15))))',
         f'\t(property "Value" "{name}" (at 0 {oy + 2.5:.2f} 0) (layer "F.Fab") (hide yes)'
         f' (uuid "{uuid.uuid4()}") (effects (font (size 1 1) (thickness 0.15))))']
    for x0, y0, x1, y1 in rs:
        a, b, c, d = x0 * px_mm - ox, y0 * px_mm - oy, x1 * px_mm - ox, y1 * px_mm - oy
        L.append(f'\t(fp_poly (pts (xy {a:.3f} {b:.3f}) (xy {c:.3f} {b:.3f}) (xy {c:.3f} {d:.3f}) (xy {a:.3f} {d:.3f}))'
                 f' (stroke (width 0) (type solid)) (fill yes) (layer "F.SilkS") (uuid "{uuid.uuid4()}"))')
    L.append('\t(embedded_fonts no)')
    L.append(')')
    open(out, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    print(f'{out}: {cols}x{rows} px -> {len(rs)} rectangles, {cols * px_mm:.1f} x {rows * px_mm:.1f} mm')


if __name__ == '__main__':
    main()
