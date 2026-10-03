"""Component placement, board coordinates in mm (origin = board top-left, x right, y down).

Floor plan (rule 3.2): logic along the top (ESP32 with the antenna over the top edge, UART/expansion/CAN
connectors facing out), 3.3 V buck on the left, power input at the left edge flowing up through the reverse-
polarity FET, eFuse and DC shunt into a +VBUS_PROT band that runs right over three half-bridge columns; phase
terminals on the bottom edge. DRV8323 centred above the bridge.

Entry formats:
  ref: (x_center, y_center, rotation_deg[, side])
  ref: ('near', anchor_ref, anchor_pad, dx, dy, rotation_deg)  -> centre = anchor pad + (dx, dy); 2-pin parts
       are turned 180 deg automatically if that brings their pads closer to the anchor's same-net pads.
"""
W, H = 100.0, 90.0
HOLES = [(4.0, 4.0), (96.0, 4.0), (4.0, 86.0), (96.0, 86.0)]            # M3 NPTH, >= 4 mm from the edges
FIDUCIALS = [(3.0, 20.0), (97.0, 30.0), (40.0, 87.0)]                   # 3, non-collinear, not symmetric

N = lambda a, p, dx, dy, r=0: ('near', a, p, dx, dy, r)

PLACE = {
    # ---------------- MCU core: top, antenna region (6.19 mm) outside the top edge ----------------
    'U1': (37.0, 6.44, 0),
    'C2': N('U1', 2, -3.3, 0, 0), 'C1': N('U1', 2, -6.5, -1.3, 0),           # 3V3: 100 nF at the pin, 22 uF next
    'C3': N('U1', 3, -6.5, 0.3, 0), 'R1': N('U1', 3, -9.7, 0.3, 0),         # EN RC
    'C4': N('U1', 4, -3.3, 0, 0), 'C5': N('U1', 5, -6.5, 0.3, 0),            # ADC filters at their pins
    'C8': N('U1', 6, -3.3, 0, 0), 'C6': N('U1', 8, -3.3, 0, 0), 'C7': N('U1', 9, -6.5, 0, 0),
    'R3': N('U1', 12, -3.3, 0, 0), 'D1': N('U1', 12, -7.3, 0, 0),
    'SW1': (15.5, 8.0, 0), 'TP1': (15.5, 13.0, 0),
    'J1': (51.6, 2.3, 180),                                                   # UART, next to TXD0/RXD0
    'R2': N('U1', 25, 3.0, 0.8, 0), 'SW2': (51.0, 23.0, 0), 'TP2': (46.5, 23.0, 0),
    'J2': (64.2, 6.73, 0),                                                    # expansion, top edge
    # ---------------- Communication: top right ----------------
    'J8': (83.2, 6.73, 0),
    'U10': (83.4, 19.4, 90), 'C60': N('U10', 3, 0.6, 2.9, 0),
    'R60': (90.3, 17.5, 0), 'R61': (90.3, 20.0, 0), 'C61': (90.3, 22.5, 0),       # split termination
    'D60': (77.5, 15.8, 90), 'D61': (87.3, 15.8, 90),                             # ESD at the connector
    'TP60': (92.0, 25.5, 0), 'TP61': (95.0, 25.5, 0),
    # ---------------- 3.3 V buck: left ----------------
    'U4': (15.0, 28.5, 180),
    'C21': N('U4', 2, 2.4, 0.6, 90), 'C20': N('U4', 2, 5.6, 0.6, 90),           # input caps across VIN/GND pins
    'R20': N('U4', 4, 2.6, -1.5, 0),                                         # RT
    'C22': N('U4', 7, -2.55, 0.63, 90),                                        # CBOOT across BOOT/SW
    'L1': N('U4', 8, -1.2, 6.0, 90),
    'R22': N('U4', 5, -2.55, -0.9, 90), 'R21': N('U4', 5, -4.9, -0.9, 90),     # FB divider at the FB pin
    'R23': (7.2, 31.2, 90), 'TP22': (5.0, 25.0, 0),
    'C23': (16.8, 38.3, 90), 'C24': (20.6, 38.3, 90), 'C25': (23.6, 38.3, 90),   # output caps at L1 pad 2
    'R24': (6.0, 42.0, 90), 'D20': (6.0, 46.5, 90), 'TP20': (10.5, 45.5, 0), 'TP23': (6.0, 52.0, 0),
    'FB1': (33.0, 24.5, 0), 'C26': (36.5, 24.5, 90), 'C27': (39.0, 24.5, 90), 'TP21': (42.5, 24.8, 0),
    # ---------------- Power input + eFuse: terminals on the bottom edge, power flowing up ----------------
    'J4': (12.0, 83.4, 0), 'J3': (22.5, 83.4, 0),                               # GND, VIN+
    'D10': (17.5, 74.5, 180), 'C10': (17.5, 71.0, 180), 'TP10': (23.0, 76.3, 0),
    'Q1': (25.5, 70.0, 0),                                                    # source (VIN_RAW) down, drain (+VBUS) up
    'U2': (32.0, 72.5, 180), 'C11': N('U2', 1, -1.3, 2.6, 0),
    'C12': (34.5, 66.8, 0), 'C13': (31.5, 63.3, 0), 'TP11': (39.5, 68.0, 0),
    'U3': (27.0, 57.5, 180),                                                  # IN from below, OUT row on top
    'R10': N('U3', 9, -1.1, -2.2, 0), 'C14': (24.3, 50.87, 180),
    # eFuse setting parts in two columns in pin order (DVDT, IREF, IMON, ILIM)
    'C18': N('U3', 4, 2.78, -1.1, 0), 'C17': N('U3', 3, 6.38, -0.1, 0), 'R17': N('U3', 2, 2.78, 0.6, 0),
    'C16': N('U3', 2, 2.78, 2.8, 0), 'R18': N('U3', 1, 6.38, 1.6, 0),
    'R13': (19.9, 55.4, 0), 'R14': (19.9, 57.8, 0), 'R16': (19.9, 60.2, 0), 'R11': (19.9, 62.6, 180),  # left-side pins
    'C15': (16.4, 60.2, 0), 'R12': (16.4, 62.6, 0),
    'R15': (19.9, 65.0, 0), 'TP13': (14.0, 57.0, 0),
    'C19': N('U3', 7, 1.3, -2.9, 0), 'TP12': (30.9, 48.2, 0),
    # ---------------- DC-bus shunt (vertical, into the band) + INA240 ----------------
    'R30': (28.0, 45.5, 90), 'NT1': N('R30', 1, -2.3, 0.0, 0), 'NT2': N('R30', 2, -2.3, 0.0, 0),
    'U9': (21.0, 45.5, 270), 'C30': N('U9', 6, 0.6, 2.3, 0),
    # ---------------- Gate drive: centred above the bridge ----------------
    'U6': (73.25, 27.0, 0),
    # charge pump / VM caps up-left of the pins (pad 1 at the bottom): the phase A gate bundle leaves below them
    'C43': (67.8, 24.75, 90), 'C42': (66.0, 26.3, 90), 'C40': (64.2, 26.1, 90), 'C41': (61.8, 24.4, 90),
    'C44': N('U6', 36, 3.3, 0.0, 0), 'C45': N('U6', 26, 4.03, 0.23, 0), 'TP3': (86.0, 31.0, 0),
    **{r: (53.5 + 2.4 * i, 18.8, 90) for i, r in
       enumerate(['R40', 'R41', 'R42', 'R43', 'R44', 'R45', 'R46', 'R47', 'R48', 'R49'])},   # pull-ups/downs
    # ---------------- Power stage: bulk caps at the band's left end ----------------
    'C56': (43.0, 48.5, 0), 'C57': (43.0, 57.5, 0),
    'TP50': (40.0, 64.5, 0), 'TP51': (43.5, 64.5, 0),
    'U8': (77.9, 76.0, 0), 'C58': (75.6, 76.0, 90),
}

# half bridges A / B / C: columns at XC (pitch 16.25). High-side drain up onto the +VBUS_PROT band, low side below,
# 2512 shunt below the low side; phase copper on the left of each column down to the terminal, gate/sense lane on
# the right; hot-loop caps on the band right above the high-side drain.
XC = {'A': 57.0, 'B': 73.25, 'C': 89.5}
BRIDGE = {'A': ('Q2', 'Q3', 'R50', 'NT3', 'NT4', 'C50', 'C51', 'J5'),
          'B': ('Q4', 'Q5', 'R51', 'NT5', 'NT6', 'C52', 'C53', 'J6'),
          'C': ('Q6', 'Q7', 'R52', 'NT7', 'NT8', 'C54', 'C55', 'J7')}
for ph, (qh, ql, rs, ntp, ntn, cb, cs, j) in BRIDGE.items():
    xc = XC[ph]
    PLACE.update({
        qh: (xc, 48.2, 0), ql: (xc, 58.6, 0), rs: (xc, 69.2, 270),
        ntp: N(rs, 1, 2.9, 0.0, 0), ntn: N(rs, 2, 2.9, 0.0, 0),
        cb: (xc - 1.4, 41.0, 90), cs: (xc + 1.7, 41.5, 90),
        j: (xc - 5.0, 83.4, 0),
    })
