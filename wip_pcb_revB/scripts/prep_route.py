"""Pre-routing (locked) before Freerouting:
  - Kelvin taps: net-tie pads to the inner edge of their shunt pads
  - short local links at fine-pitch parts (eFuse exposed pad, LM74700 EN/ANODE, VDD filter)
  - "port" stubs + vias so the router can reach pour nets from outside the pour
  - one GND via at every SMD GND pad (plane -> via -> pad), placed only where it clears other copper
Usage: python.exe prep_route.py <board>
"""
import sys, math
import pcbnew
import placement as PL

MM, T = pcbnew.FromMM, pcbnew.ToMM
O = 50.0
F, B = pcbnew.F_Cu, pcbnew.B_Cu


def P(x, y):
    return pcbnew.VECTOR2I(MM(O + x), MM(O + y))


class Router:
    def __init__(self, board):
        self.b = board
        import json, os
        pro = json.load(open(os.path.splitext(board.GetFileName())[0] + '.kicad_pro', encoding='utf-8'))
        self.hv = {p['pattern'] for p in pro['net_settings']['netclass_patterns'] if p['netclass'] == 'HV'}
        self.items = []                                      # (net, x0, y0, x1, y1) copper boxes for clash tests
        self.gnd_vias = []
        for fp in board.GetFootprints():
            for p in fp.Pads():
                bb = p.GetBoundingBox()
                self.items.append((p.GetNetname(), T(bb.GetLeft()) - O, T(bb.GetTop()) - O,
                                   T(bb.GetRight()) - O, T(bb.GetBottom()) - O))

    def track(self, net, pts, w=0.3, layer=F):
        n = self.b.FindNet(net)
        assert n is not None, net
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if abs(x0 - x1) < 1e-4 and abs(y0 - y1) < 1e-4:
                continue
            t = pcbnew.PCB_TRACK(self.b)
            t.SetStart(P(x0, y0)); t.SetEnd(P(x1, y1)); t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(n)
            t.SetLocked(True)
            self.b.Add(t)
            self.items.append((net, min(x0, x1) - w / 2, min(y0, y1) - w / 2, max(x0, x1) + w / 2, max(y0, y1) + w / 2))

    def via(self, net, x, y, d=0.6, drill=0.3):
        v = pcbnew.PCB_VIA(self.b)
        v.SetPosition(P(x, y)); v.SetWidth(MM(d)); v.SetDrill(MM(drill)); v.SetNet(self.b.FindNet(net))
        v.SetLocked(True)
        self.b.Add(v)
        self.items.append((net, x - d / 2, y - d / 2, x + d / 2, y + d / 2))

    def free(self, net, x0, y0, x1, y1, clr):
        for n, a0, b0, a1, b1 in self.items:
            if n == net:
                continue
            c = max(clr, 0.65) if n in self.hv else clr
            if x0 - c < a1 and a0 < x1 + c and y0 - c < b1 and b0 < y1 + c:
                return False
        return 0.6 <= x0 and x1 <= PL.W - 0.6 and 0.6 <= y0 and y1 <= PL.H - 0.6


def ext_max(hw, hh):
    return max(hw, hh)


def pad_c(b, ref, num):
    fp = b.FindFootprintByReference(ref)
    ps = [p for p in fp.Pads() if p.GetNumber() == str(num)]
    x = sum(T(p.GetPosition().x) for p in ps) / len(ps) - O
    y = sum(T(p.GetPosition().y) for p in ps) / len(ps) - O
    return x, y


def gate_drive(b, r):
    """DRV8323 fan-out and the three gate bundles (hand-routed: 0.5 mm pitch pins carry 36 V nets).
    Per phase: gate (GH) paired with its phase sense (SH), then GL, SP, SN. 0.6 mm between the HV pairs and
    the rest outside the U6 fan-out area; inside it the pin pitch rules (waiver 2)."""
    XC = PL.XC
    U = lambda n: pad_c(b, 'U6', n)
    W = 0.25
    VIA = lambda net, x, y: r.via(net, x, y, 0.6, 0.3)
    x0 = U(8)[0]
    # -- charge pump, VCP, VM caps (up-left of pins 3..7) --
    cph, cpl = pad_c(b, 'C43', 1), pad_c(b, 'C43', 2)
    r.track('/Gate Drive/CPH', [U(4), (68.7, U(4)[1]), cph], w=0.2)
    r.track('/Gate Drive/CPL', [U(3), (69.0, U(3)[1]), (68.6, U(3)[1] - 0.4), (68.6, cpl[1]), cpl], w=0.2)
    vcp = pad_c(b, 'C42', 2)
    r.track('/Gate Drive/VCP', [U(5), (vcp[0] + 0.8, U(5)[1]), vcp], w=0.2)
    vm42, vm40, vm41 = pad_c(b, 'C42', 1), pad_c(b, 'C40', 1), pad_c(b, 'C41', 1)
    ym = (U(6)[1] + U(7)[1]) / 2
    r.track('+VBUS_PROT', [(x0, ym), (vm42[0], ym)], w=0.4)
    r.track('+VBUS_PROT', [vm42, (vm40[0] + 0.4, vm40[1]), vm40, (vm41[0] + 1.2, vm40[1]), vm41], w=0.4)
    r.track('+VBUS_PROT', [vm41, (59.8, vm41[1]), (59.8, 36.9)], w=0.5)   # VM feed from the band

    VY, LY = 35.35, 45.3                         # vias above / below the +VBUS_PROT band (bundle crosses on B.Cu)
    nets = lambda ph: (f'GH{ph}', f'PHASE_{ph}', f'GL{ph}', f'ISENSE_{ph}_P', f'ISENSE_{ph}_N')
    VO = (4.0, 4.9, 6.2, 7.0, 7.8)              # via x offsets from the column centre: GH SH GL SP SN
    LO = (4.0, 4.5, 5.75, 6.25, 6.75)           # lane x offsets (top)

    def lane_top(ph):
        xc = XC[ph]
        gh, sh, gl, sp, sn = nets(ph)
        qh, ql = {'A': ('Q2', 'Q3'), 'B': ('Q4', 'Q5'), 'C': ('Q6', 'Q7')}[ph]
        ntp, ntn = {'A': ('NT3', 'NT4'), 'B': ('NT5', 'NT6'), 'C': ('NT7', 'NT8')}[ph]
        g_h, g_l = pad_c(b, qh, 2), pad_c(b, ql, 2)
        p_p, p_n = pad_c(b, ntp, 1), pad_c(b, ntn, 1)
        for i, net in enumerate(nets(ph)):
            VIA(net, xc + VO[i], LY)
        r.track(gh, [(xc + VO[0], LY), (xc + LO[0], g_h[1]), g_h], w=W)
        D = LY + 0.8                              # leave each via straight down before converging on the lane
        r.track(sh, [(xc + VO[1], LY), (xc + VO[1], D), (xc + LO[1], D + VO[1] - LO[1]), (xc + LO[1], 57.2)], w=W)
        r.track(gl, [(xc + VO[2], LY), (xc + VO[2], D), (xc + LO[2], D + VO[2] - LO[2]), (xc + LO[2], g_l[1]), g_l], w=W)
        r.track(sp, [(xc + VO[3], LY), (xc + VO[3], D), (xc + LO[3], D + VO[3] - LO[3]), (xc + LO[3], p_p[1]), p_p], w=W)
        r.track(sn, [(xc + VO[4], LY), (xc + VO[4], D), (xc + LO[4], D + VO[4] - LO[4]), (xc + LO[4], p_n[1]), p_n], w=W)
        for i, net in enumerate(nets(ph)):       # band crossing on B.Cu
            VIA(net, xc + VO[i], VY) if ph == 'C' else None
            r.track(net, [(xc + VO[i] if ph == 'C' else AX[i], VY), (xc + VO[i], LY)], w=W, layer=B)
        r.track(sh, [(xc + 2.7, 57.2), (xc + LO[1], 57.2)], w=0.6)             # phase sense taps the low-side drain

    # -- phase A: left pins 8..12, west on top, down to vias above the band --
    AX = (61.0, 61.9, 63.2, 64.0, 64.8)
    ys = [U(n)[1] for n in (8, 9, 10, 11, 12)]
    r.track('GHA', [U(8), (AX[0] + 0.4, ys[0]), (AX[0], ys[0] + 0.4), (AX[0], VY)], w=W)
    r.track('PHASE_A', [U(9), (AX[1] + 0.4, ys[1]), (AX[1], ys[1] + 0.4), (AX[1], VY)], w=W)
    for k, (n, net, jx) in enumerate(((10, 'GLA', 0.9), (11, 'ISENSE_A_P', 0.6), (12, 'ISENSE_A_N', 0.3))):
        y = ys[2 + k]
        r.track(net, [U(n), (x0 - jx, y), (x0 - jx - 0.45, y + 0.45), (AX[2 + k] + 0.4, y + 0.45),
                      (AX[2 + k], y + 0.85), (AX[2 + k], VY)], w=W)
    for i, net in enumerate(nets('A')):
        VIA(net, AX[i], VY)
    lane_top('A')

    # -- phase C: bottom pins 18..22 down, east on top above the band, vias at the column --
    xc = XC['C']
    cy = (35.35, 34.7, 33.85, 33.4, 32.95)       # GH SH GL SP SN run heights (0.6 mm between the HV pair and GL)
    for i, (n, net) in enumerate(zip((18, 19, 20, 21, 22), nets('C'))):
        px, py = U(n)
        r.track(net, [(px, py), (px, cy[i]), (xc + VO[i], cy[i]), (xc + VO[i], VY)], w=W)
    lane_top('C')

    # -- phase B: bottom pins 13..17 fan SW to vias, then B.Cu the whole way, popping up at each target --
    xc = XC['B']
    gh, sh, gl, sp, sn = nets('B')
    fan = {sn: (13, 68.9), sp: (14, 69.7), gl: (15, 70.5), sh: (16, 71.3), gh: (17, 72.1)}
    for k, (net, (n, vx)) in enumerate(fan.items()):
        px, py = U(n)
        ys = 30.95 + 0.2 * k                      # staggered 45 deg fan: parallel diagonals stay 0.2 mm apart
        r.track(net, [(px, py), (px, ys), (vx, ys + abs(px - vx)), (vx, 33.2)], w=W)
        VIA(net, vx, 33.2)
    run = {gh: 33.2, sh: 33.9, gl: 34.85, sp: 35.35, sn: 35.85}
    lane = {sn: xc + 3.95, sp: xc + 4.7, gl: xc + 5.45, sh: xc + 6.5, gh: xc + 7.2}
    qh, ql = pad_c(b, 'Q4', 2), pad_c(b, 'Q5', 2)
    src = pad_c(b, 'Q4', 1)
    ends = {sh: 50.5, gh: qh[1], gl: ql[1], sp: pad_c(b, 'NT5', 1)[1], sn: pad_c(b, 'NT6', 1)[1] + 0.7}
    for net in (gh, sh, gl, sp, sn):
        vx = fan[net][1]
        r.track(net, [(vx, 33.2), (vx, run[net]), (lane[net], run[net]), (lane[net], ends[net])], w=W, layer=B)
        VIA(net, lane[net], ends[net])
    r.track(sh, [(lane[sh], 50.5), (xc + 0.95, 50.5), (xc + 0.64, 50.81), (xc + 0.64, 51.3)], w=W)  # QH source
    r.track(gh, [(lane[gh], qh[1]), qh], w=W)
    r.track(gl, [(lane[gl], ql[1]), ql], w=W)
    r.track(sp, [(lane[sp], ends[sp]), pad_c(b, 'NT5', 1)], w=W)
    r.track(sn, [(lane[sn], ends[sn]), (lane[sn], pad_c(b, 'NT6', 1)[1]), pad_c(b, 'NT6', 1)], w=W)

    # -- right side (SPI, ENABLE, NFAULT, ISENSE_A): staggered two-column via fan; VREF and DVDD caps direct --
    C1, C2 = 78.0, 79.2
    fan_r = [(33, 'DRV_ENABLE', [(77.2, None), (77.97, 25.0)], (C1, 25.0)),
             (32, 'SPI_NSCS', [(77.5, None), (78.02, 25.75)], (C2, 25.75)),
             (31, 'SPI_SCLK', [(78.03, None), (78.3, 26.5)], (78.3, 26.5)),
             (30, 'SPI_SDI', [], (C2, None)),
             (29, 'SPI_SDO', [(77.77, None), (78.0, 28.0)], (C1, 28.0)),
             (28, 'NFAULT', [(77.2, None), (77.68, 28.75)], (C2, 28.75)),
             (25, 'ISENSE_A', [(77.2, None), (77.68, 30.25)], (C2, 30.25))]
    for n, net, mid, (vx, vy) in fan_r:
        px, py = U(n)
        vy = py if vy is None else vy
        pts = [(px, py)] + [(x, py if y is None else y) for x, y in mid] + [(vx, vy)]
        r.track(net, pts, w=0.2)
        VIA(net, vx, vy)
    c45 = [pad_c(b, 'C45', k) for k in (1, 2)
           if [q for q in b.FindFootprintByReference('C45').Pads() if q.GetNumber() == str(k)][0].GetNetname() == '+3V3_A'][0]
    r.track('+3V3_A', [U(26), (77.73, U(26)[1]), (77.96, 29.5), (c45[0], 29.5), c45], w=0.2)
    c44 = [pad_c(b, 'C44', k) for k in (1, 2)
           if [q for q in b.FindFootprintByReference('C44').Pads() if q.GetNumber() == str(k)][0].GetNetname().endswith('DVDD')][0]
    r.track('/Gate Drive/DVDD', [U(36), c44], w=0.2)
    # top side (PWM inputs): 45 deg fan to a via row at 1.1 mm pitch below the pull-down resistor row
    top = [(42, 'PWM_CL', 71.4, 23.0), (41, 'PWM_CH', 72.5, 22.8), (40, 'PWM_BL', 73.6, 22.6),
           (39, 'PWM_BH', 74.7, 22.4), (38, 'PWM_AL', 75.8, 22.8), (37, 'PWM_AH', 76.9, 23.0)]
    for n, net, vx, ys in top:
        px, py = U(n)
        r.track(net, [(px, py), (px, ys), (vx, ys - abs(vx - px)), (vx, 20.6)], w=0.2)
        VIA(net, vx, 20.6)

    # -- ISENSE_C / ISENSE_B (pins 23/24): short escapes above the phase C run; the router continues --
    px, py = U(24)
    r.track('ISENSE_B', [(px, py), (px, 31.25), (78.6, 31.25)], w=0.2)
    VIA('ISENSE_B', 78.6, 31.25)
    px, py = U(23)                                 # ISENSE_C via sits between the ISENSE_B escape and the SN_C run
    r.track('ISENSE_C', [(px, py), (px, 31.75), (76.55, 31.75), (77.0, 32.2)], w=0.2)
    VIA('ISENSE_C', 77.0, 32.2)
    # NFAULT: from its fan-out via round the right of the DRV8323 on B.Cu to the pull-up row
    r47 = [pad_c(b, 'R47', k) for k in (1, 2)
           if [q for q in b.FindFootprintByReference('R47').Pads() if q.GetNumber() == str(k)][0].GetNetname() == 'NFAULT'][0]
    r.track('NFAULT', [(C2, 28.75), (80.1, 28.75), (80.1, 22.0), (r47[0], 22.0), (r47[0], 21.0)], w=0.2, layer=B)
    VIA('NFAULT', r47[0], 21.0)
    r.track('NFAULT', [(r47[0], 21.0), r47], w=0.2)


def build(b):
    for t in list(b.GetTracks()):
        b.Remove(t)
    r = Router(b)
    XC = PL.XC

    # ---- Kelvin taps (0.3 mm) from the net tie to the inner edge of its shunt pad ----
    for nt, rs, rp in (('NT1', 'R30', 1), ('NT2', 'R30', 2)):
        x, y = pad_c(b, nt, 1)
        r.track(b.FindFootprintByReference(nt).Pads()[0].GetNetname() if False else
                [p for p in b.FindFootprintByReference(nt).Pads() if p.GetNumber() == '1'][0].GetNetname(),
                [(x, y), (27.1, y)])
    for ph, (rs, ntp, ntn) in (('A', ('R50', 'NT3', 'NT4')), ('B', ('R51', 'NT5', 'NT6')), ('C', ('R52', 'NT7', 'NT8'))):
        xc = XC[ph]
        for nt, net in ((ntp, f'/Power Stage/Half Bridge {ph}/LS_SRC'), (ntn, 'GND')):
            x, y = pad_c(b, nt, 2)
            r.track(net, [(x, y), (xc + 1.4, y)])

    # ---- eFuse U3: exposed pad (IN) to pin 10; VDD filter R10/C14 ----
    r.track('+VBUS', [(25.0, 55.6), (25.3, 56.5)], w=0.25)                 # pin 10 corner -> exposed pad
    x, y = pad_c(b, 'R10', 1)
    r.track('+VBUS', [(x, y), (x, 54.4), (23.9, 55.3)], w=0.3)             # R10 (+VBUS side) -> pin 10
    x2, y2 = pad_c(b, 'R10', 2)
    r.track('/Power Input & Protection/EFUSE_VDD', [(x2, y2), (25.5, 54.2), (25.5, 55.1)], w=0.25)
    xc14, yc14 = [pad_c(b, 'C14', n) for n in (1, 2)
                  if [p for p in b.FindFootprintByReference('C14').Pads() if p.GetNumber() == str(n)][0]
                  .GetNetname().endswith('EFUSE_VDD')][0]
    r.track('/Power Input & Protection/EFUSE_VDD', [(xc14, yc14), (x2, y2)], w=0.25)
    x, y = pad_c(b, 'R11', 1)
    r.track('+VBUS', [(x, y), (22.8, y)], w=0.4)                           # EN divider top -> +VBUS pour
    p4, p5 = pad_c(b, 'U3', 4), pad_c(b, 'U3', 5)
    r.track('GND', [p5, (p5[0] + 0.63, p5[1]), (30.55, 55.7)], w=0.2)
    r.via('GND', 30.55, 55.7, 0.6, 0.3); r.gnd_vias.append((30.55, 55.7))
    p16 = pad_c(b, 'U3', 16)
    r11en = [pad_c(b, 'R11', k) for k in (1, 2)
             if [q for q in b.FindFootprintByReference('R11').Pads() if q.GetNumber() == str(k)][0].GetNetname().endswith('EFUSE_EN')][0]
    r.track('/Power Input & Protection/EFUSE_EN', [p16, (22.0, p16[1]), (21.7, p16[1] + 0.3), (21.7, 61.3),
                                                   (r11en[0], 61.3), r11en], w=0.2)
    p1 = pad_c(b, 'U3', 1)
    r18 = [pad_c(b, 'R18', k) for k in (1, 2)
           if [q for q in b.FindFootprintByReference('R18').Pads() if q.GetNumber() == str(k)][0].GetNetname().endswith('EFUSE_ILIM')][0]
    I2 = pcbnew.In2_Cu
    r.track('/Power Input & Protection/EFUSE_ILIM', [p1, (30.3, p1[1]), (30.6, 58.3), (30.6, 58.45)], w=0.2)
    r.via('/Power Input & Protection/EFUSE_ILIM', 30.6, 58.45, 0.6, 0.3)
    r.track('/Power Input & Protection/EFUSE_ILIM', [(30.6, 58.45), (32.75, 60.6), (34.5, 60.6)], w=0.2, layer=I2)
    r.via('/Power Input & Protection/EFUSE_ILIM', 34.5, 60.6, 0.6, 0.3)
    r.track('/Power Input & Protection/EFUSE_ILIM', [(34.5, 60.6), r18], w=0.2)
    imr = [pad_c(b, 'R17', k) for k in (1, 2)
           if [q for q in b.FindFootprintByReference('R17').Pads() if q.GetNumber() == str(k)][0].GetNetname().endswith('EFUSE_IMON')][0]
    imc = [pad_c(b, 'C16', k) for k in (1, 2)
           if [q for q in b.FindFootprintByReference('C16').Pads() if q.GetNumber() == str(k)][0].GetNetname().endswith('EFUSE_IMON')][0]
    r.track('/Power Input & Protection/EFUSE_IMON', [imr, imc], w=0.2)
    c18 = pad_c(b, 'C18', 1)
    r.track('/Power Input & Protection/EFUSE_DVDT', [p4, (c18[0] - 0.35, p4[1]), (c18[0], p4[1] - 0.35), c18], w=0.2)
    for pin, nt in ((8, 'NT1'), (1, 'NT2')):                              # INA240 inputs to the Kelvin taps
        net = [q for q in b.FindFootprintByReference('U9').Pads() if q.GetNumber() == str(pin)][0].GetNetname()
        up, tp = pad_c(b, 'U9', pin), pad_c(b, nt, 2)
        r.track(net, [up, (up[0], tp[1]), tp], w=0.25)

    # ---- LM74700 U2: EN (pin 3) to ANODE (pin 6) under the body; VCAP to C11 ----
    r.track('VIN_RAW', [(32.53, 71.5), (31.78, 72.25), (31.78, 72.65), (31.03, 73.4)], w=0.3)   # 45 deg bends
    qg, ug = pad_c(b, 'Q1', 2), pad_c(b, 'U2', 5)
    r.track('/Power Input & Protection/REVPOL_GATE', [qg, (qg[0], ug[1]), ug], w=0.3)
    xv, yv = pad_c(b, 'U2', 1)
    xc11 = [pad_c(b, 'C11', n) for n in (1, 2)
            if [p for p in b.FindFootprintByReference('C11').Pads() if p.GetNumber() == str(n)][0]
            .GetNetname().endswith('LM_VCAP')][0]
    r.track('/Power Input & Protection/LM_VCAP', [(xv, yv), (xv, 74.9), xc11], w=0.3)

    # ---- ports: the router connects pads outside a pour to these vias ----
    c20, c21 = pad_c(b, 'C20', 1), pad_c(b, 'C21', 1)                    # buck input from the band's left end
    u2p, u3p = pad_c(b, 'U4', 2), pad_c(b, 'U4', 3)
    r.track('+VBUS_PROT', [(27.2, 36.9), (27.2, c20[1]), c20], w=0.6)
    r.track('+VBUS_PROT', [c20, (c21[0] + 1.0, c21[1]), c21, (u2p[0] + 0.4, c21[1]), u2p], w=0.5)
    r.track('+VBUS_PROT', [u2p, u3p], w=0.4)

    gate_drive(b, r)

    # ---- GND: a via at every SMD GND pad ----
    skip_fp = {'J4', 'C56', 'C57', 'H1', 'H2', 'H3', 'H4'}
    ep_ics = {'U6', 'U4', 'U1'}                   # exposed GND pad with vias in the footprint: pins stub to it
    big = {'R50', 'R51', 'R52', 'C50', 'C52', 'C54', 'C12', 'C19', 'C20', 'C41', 'C23', 'C24', 'D10'}
    placed, failed = 0, []
    for fp in b.GetFootprints():
        ref = fp.GetReference()
        if ref in skip_fp or ref.startswith(('FID', 'NT')):
            continue
        cc = fp.GetBoundingBox(False).GetCenter()          # library origins are not always the part centre
        cx, cy = T(cc.x) - O, T(cc.y) - O
        pads = list(fp.Pads())
        for p in pads:
            if p.GetNetname() != 'GND' or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                continue
            px, py = T(p.GetPosition().x) - O, T(p.GetPosition().y) - O
            bb = p.GetBoundingBox()
            hw, hh = T(bb.GetWidth()) / 2, T(bb.GetHeight()) / 2
            if ref in ep_ics and (max(hw, hh) > 1.5 or (ref == 'U1' and p.GetNumber() == '39')):
                continue                           # the exposed pad itself already has vias
            if ref in ('U6', 'U4') or (ref, p.GetNumber()) in (('U3', '5'),):
                continue                           # joined to the exposed pad / hand-routed
            if len(pads) == 2:
                o = [q for q in pads if q is not p][0]
                dx, dy = px - (T(o.GetPosition().x) - O), py - (T(o.GetPosition().y) - O)
            elif abs(hw - hh) > 0.05:              # IC pin: leave straight out, along the pad's long axis
                dx, dy = ((px - cx), 0) if hw > hh else (0, (py - cy))
            else:
                dx, dy = px - cx, py - cy
            n = math.hypot(dx, dy) or 1
            dx, dy = dx / n, dy / n
            if ref == 'J8':                            # CAN connector: via behind the pin, clear of the ESD diodes
                dx, dy = -dx, -dy
            d, drill = (0.8, 0.4) if ref in big else (0.6, 0.3)
            ok = False
            dirs = [(dx, dy), (dy, -dx), (-dy, dx), (-dx, -dy)] if len(pads) == 2 else [(dx, dy)]
            if abs(dx) > abs(dy):
                dirs += [(0, 1), (0, -1)]
            else:
                dirs += [(1, 0), (-1, 0)]
            def _gap(v):                               # via edge to pad edge (negative = overlapping)
                gx = max(abs(v[0] - px) - hw, 0); gy = max(abs(v[1] - py) - hh, 0)
                return math.hypot(gx, gy) - 0.3
            near = [(vx, vy) for vx, vy in r.gnd_vias if math.hypot(vx - px, vy - py) < ext_max(hw, hh) + 1.1
                    and not (-0.1 < _gap((vx, vy)) < 0.2)]   # share only with a clean gap or a real overlap
            if near:                                   # a GND via right next to this pad already: share it
                vx, vy = min(near, key=lambda v: math.hypot(v[0] - px, v[1] - py))
                r.track('GND', [(px, py), (vx, vy)], w=(0.4 if 2 * min(hw, hh) >= 0.3 else 0.25))
                placed += 1
                continue
            for ux, uy in dirs:
                ext = abs(ux) * hw + abs(uy) * hh
                for extra in (0.25, 0.45, 0.7, 1.0):
                    vx, vy = px + ux * (ext + extra + d / 2), py + uy * (ext + extra + d / 2)
                    if r.free('GND', vx - d / 2, vy - d / 2, vx + d / 2, vy + d / 2, 0.3) and                             all(math.hypot(vx - gx, vy - gy) >= 0.9 for gx, gy in r.gnd_vias):   # hole-to-hole
                        r.track('GND', [(px, py), (vx, vy)], w=(0.4 if 2 * min(hw, hh) >= 0.3 else 0.25))
                        r.via('GND', vx, vy, d, drill)
                        r.gnd_vias.append((vx, vy))
                        ok = True
                        break
                if ok:
                    break
            if ok:
                placed += 1
            else:
                failed.append(f'{ref}.{p.GetNumber()}')
    # DRV8323 / buck / ESP32 GND pins that sit next to their exposed pad: short stub inward
    for ref in ('U6', 'U4'):
        fp = b.FindFootprintByReference(ref)
        ep = max((q for q in fp.Pads() if q.GetNetname() == 'GND'), key=lambda q: q.GetBoundingBox().GetWidth())
        ex, ey = T(ep.GetPosition().x) - O, T(ep.GetPosition().y) - O
        for p in fp.Pads():
            if p.GetNetname() == 'GND' and p is not ep and p.GetBoundingBox().GetWidth() < MM(1.5):
                px, py = T(p.GetPosition().x) - O, T(p.GetPosition().y) - O
                if abs(px - ex) < 1e-3 and abs(py - ey) < 1e-3:
                    continue
                hw = T(p.GetBoundingBox().GetWidth()) / 2
                hh = T(p.GetBoundingBox().GetHeight()) / 2
                eb = ep.GetBoundingBox()
                el, er, et, ebt = T(eb.GetLeft()) - O, T(eb.GetRight()) - O, T(eb.GetTop()) - O, T(eb.GetBottom()) - O
                if hw > hh:                         # left/right pin row: stub inward along x onto the exposed pad
                    x_end = el + 0.3 if px < el else er - 0.3
                    if et < py < ebt:
                        r.track('GND', [(px, py), (x_end, py)], w=0.2)
                else:
                    y_end = et + 0.3 if py < et else ebt - 0.3
                    if el < px < er:
                        r.track('GND', [(px, py), (px, y_end)], w=0.2)
                    else:                           # corner pin: join the next GND pin in the row
                        nb = [q for q in fp.Pads() if q.GetNetname() == 'GND' and q is not p
                              and abs(T(q.GetPosition().y) - O - py) < 0.01
                              and abs(T(q.GetPosition().x) - O - px) < 0.6]
                        if nb:
                            r.track('GND', [(px, py), (T(nb[0].GetPosition().x) - O, py)], w=0.2)
    r.track('GND', [pad_c(b, 'U6', 1), pad_c(b, 'U6', 2)], w=0.2)
    failed = [f for f in failed if f != 'U6.1']
    print(f'GND vias: {placed} placed, not placed: {failed}')


if __name__ == '__main__':
    bd = pcbnew.LoadBoard(sys.argv[1])
    build(bd)
    pcbnew.ZONE_FILLER(bd).Fill(bd.Zones())
    bd.Save(sys.argv[1])
