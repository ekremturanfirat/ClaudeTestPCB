"""Board information and connector labels (rule 3.6), silkscreen, collision-checked.
  - title block: revision / date (PCB text variables ${REVISION} ${ISSUE_DATE} follow it)
  - top: voltage/polarity at the power input, phase letters, connector pin names
  - bottom: METU PowerLab logo, QR code, project / revision / date / designer / website (largest free areas)
Usage: python.exe board_info.py <board>
"""
import sys, math
import pcbnew

MM, T = pcbnew.FromMM, pcbnew.ToMM
O = 50.0
LIB = 'C:/Users/ekrem/Documents/KiCad/10.0/3rdparty/footprints/METUPowerLab_kicad_library/'
REV, DATE = 'B', '2026-09-28'


def box(bb, g=0.0):
    return (T(bb.GetLeft()) - O - g, T(bb.GetTop()) - O - g, T(bb.GetRight()) - O + g, T(bb.GetBottom()) - O + g)


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class Silk:
    def __init__(self, b):
        self.b = b
        self.obst = {pcbnew.F_SilkS: [], pcbnew.B_SilkS: []}
        for fp in b.GetFootprints():
            if fp.GetReference().startswith(('LOGO', 'QR')):
                continue
            body = box(fp.GetBoundingBox(False, False))
            for p in fp.Pads():
                pb = box(p.GetBoundingBox(), 0.15)
                self.obst[pcbnew.F_SilkS].append(pb)
                if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) or p.IsOnLayer(pcbnew.B_Cu):
                    self.obst[pcbnew.B_SilkS].append(pb)
            if not fp.GetReference().startswith(('FID', 'H')):
                self.obst[pcbnew.F_SilkS].append(body)          # never under a part
            self.obst[pcbnew.F_SilkS].append(box(fp.Reference().GetBoundingBox(), 0.1))
        for h in ((4, 4), (96, 4), (4, 86), (96, 86)):
            for L in self.obst:
                self.obst[L].append((h[0] - 3.6, h[1] - 3.6, h[0] + 3.6, h[1] + 3.6))
        self.edge = (0.8, 0.8, 99.2, 89.2)

    def free(self, bx, layer):
        e = self.edge
        return (e[0] <= bx[0] and bx[2] <= e[2] and e[1] <= bx[1] and bx[3] <= e[3]
                and not any(hit(bx, o) for o in self.obst[layer]))

    def text(self, s, x, y, layer, size=1.0, thick=0.15, ang=0, search=6.0, angles=None):
        for a in (angles or [ang]):
            t = self._text(s, x, y, layer, size, thick, a, search, quiet=True)
            if t:
                return t
        print('  no room for text', repr(s), 'near', (round(x, 1), round(y, 1)))
        return None

    def _text(self, s, x, y, layer, size=1.0, thick=0.15, ang=0, search=6.0, quiet=False):
        t = pcbnew.PCB_TEXT(self.b)
        t.SetText(s); t.SetLayer(layer)
        t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); t.SetTextThickness(MM(thick))
        t.SetTextAngleDegrees(ang)
        if layer == pcbnew.B_SilkS:
            t.SetMirrored(True)
        best = None
        steps = [i * 0.25 for i in range(int(search / 0.25) + 1)]
        for r in steps:
            for k in range(max(1, int(2 * math.pi * r / 0.5))):
                a = 2 * math.pi * k / max(1, int(2 * math.pi * r / 0.5))
                px, py = x + r * math.cos(a), y + r * math.sin(a)
                t.SetPosition(pcbnew.VECTOR2I(MM(O + px), MM(O + py)))
                bx = box(t.GetBoundingBox(), 0.1)
                if self.free(bx, layer):
                    best = (px, py, bx)
                    break
            if best:
                break
        if not best:
            return None
        t.SetPosition(pcbnew.VECTOR2I(MM(O + best[0]), MM(O + best[1])))
        self.b.Add(t)
        self.obst[layer].append(best[2])
        return t

    def graphic(self, name, ref, x, y, bottom, search=12.0):
        fp = pcbnew.FootprintLoad(LIB + 'METUPowerLab_Graphics.pretty', name)
        fp.SetFPID(pcbnew.LIB_ID('METUPowerLab_Graphics', name))
        fp.SetReference(ref); fp.Reference().SetVisible(False)
        self.b.Add(fp)
        if bottom:
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        layer = pcbnew.B_SilkS if bottom else pcbnew.F_SilkS
        for r in [i * 0.5 for i in range(int(search / 0.5) + 1)]:
            n = max(1, int(2 * math.pi * r / 1.0))
            for k in range(n):
                a = 2 * math.pi * k / n
                fp.SetPosition(pcbnew.VECTOR2I(MM(O + x + r * math.cos(a)), MM(O + y + r * math.sin(a))))
                bx = box(fp.GetBoundingBox(False, False), 0.3)
                if self.free(bx, layer):
                    self.obst[layer].append(bx)
                    return fp
        print('  no room for', name)
        self.b.Remove(fp)
        return None


def main(path):
    b = pcbnew.LoadBoard(path)
    for d in list(b.Drawings()):
        if isinstance(d, pcbnew.PCB_TEXT) and d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            b.Remove(d)
    for fp in list(b.GetFootprints()):
        if fp.GetReference().startswith(('LOGO', 'QR')):
            b.Remove(fp)
    tb = b.GetTitleBlock()
    tb.SetTitle('${PROJECT_NAME}'); tb.SetRevision(REV); tb.SetDate(DATE); tb.SetCompany('METU PowerLab')
    b.SetTitleBlock(tb)
    S = Silk(b)
    F, B = pcbnew.F_SilkS, pcbnew.B_SilkS
    pc = lambda ref: box(b.FindFootprintByReference(ref).GetBoundingBox(False, False))

    # ---- top: power input voltage + polarity, phase letters, connector pins ----
    for ref, s in (('J3', '+12-36V'), ('J4', 'GND')):
        bx = pc(ref)
        S.text(s, (bx[0] + bx[2]) / 2, bx[1] - 1.2, F, size=1.5, thick=0.25, search=12.0, angles=[0, 90])
    for ref, s in (('J5', 'A'), ('J6', 'B'), ('J7', 'C')):
        bx = pc(ref)
        S.text(s, (bx[0] + bx[2]) / 2, bx[1] - 1.4, F, size=2.0, thick=0.3)
    legend = []
    for ref, s in (('J1', '3V3 TX RX GND'), ('J2', '3V3 IO25 IO26 GND'), ('J8', 'CANH CANL GND GND')):
        bx = pc(ref)
        if not S.text(s, (bx[0] + bx[2]) / 2, bx[3] + 1.2, F, size=1.2, thick=0.2, search=6.0):   # rule 2.4: 1.2 mm
            p1 = [q for q in b.FindFootprintByReference(ref).Pads() if q.GetNumber() == '1'][0]
            S.text('1', T(p1.GetPosition().x) - O, T(p1.GetPosition().y) - O, F, size=1.2, thick=0.2, search=4.0)
            legend.append(f'{ref}: ' + ' '.join(f'{i + 1}={n}' for i, n in enumerate(s.split())))

    # ---- bottom: logo, QR, board information ----
    S.graphic('METUPowerLab_QRCode_13.3mm', 'QR1', 12.0, 60.0, True)
    S.graphic('METUPowerLab_Logo_30mm', 'LOGO1', 70.0, 12.0, True, search=25.0)
    lines = [('${PROJECT_NAME}', 1.5, 0.25), ('Rev ${REVISION}  ${ISSUE_DATE}', 1.2, 0.2),
             ('Design: ${DESIGNER}', 1.0, 0.15), ('METU PowerLab', 1.0, 0.15),
             ('power.eee.odtu.edu.tr', 1.0, 0.15), ('github.com/odtu', 1.0, 0.15)]
    lines += [(l.replace('J1:', 'J1 UART:').replace('J8:', 'J8 CAN:'), 1.0, 0.15) for l in legend]
    y = 42.0
    for s, sz, th in lines:
        t = S.text(s, 14.0, y, B, size=sz, thick=th, search=30.0)
        y = (T(t.GetPosition().y) - O if t else y) + sz * 1.6
    b.Save(path)
    print('board info added')


if __name__ == '__main__':
    main(sys.argv[1])
