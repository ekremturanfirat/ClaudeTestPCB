"""Root sheet: project info, key specs, revision history, block diagram image, sheet symbols."""
import base64, os
import schgen

INFO = ('3-Phase BLDC / PMSM Electronic Speed Controller\n'
        'Revision B - 2026-09-27\n\n'
        'Input voltage:     12-36 V DC (TVS SMBJ36CA, reverse polarity LM74700-Q1,\n'
        '                   eFuse TPS16890: UVLO ~10.7 V, circuit breaker ~15 A)\n'
        'Phase current:     5-10 A continuous (NTMFS006N08MC 80 V, 2 mOhm shunts)\n'
        'Gate driver:       DRV8323RS (SPI, 3x current-sense amplifiers)\n'
        'MCU:               ESP32-WROOM-32E, soldered directly (Wi-Fi/BLE)\n'
        'Interfaces:        UART (programming + control), CAN 2.0 (SN65HVD230)\n'
        'Sensing:           3x phase current, DC-bus current (INA240A1), board temperature\n'
        'Logic supply:      LMR38020 buck, +3V3_MCU / +3V3_A\n'
        'PCB:               2 layers, 1 oz, 1.6 mm FR-4, PCBWay standard spec')
REVS = ('Revision history\n'
        'A  2026-09-27  First version - withdrawn (schematic net shorts, rule violations)\n'
        'B  2026-09-27  Full rebuild per METU PowerLab PCB design rules')


def build(root, children):
    root.text(INFO, (15.24, 22.86), size=1.5)
    root.text(REVS, (15.24, 172.72), size=1.27)
    img = os.path.join(os.path.dirname(__file__), 'block_diagram.png')
    if os.path.exists(img):
        root.images.append(dict(at=(215.9, 60.96), scale=0.85, data=base64.b64encode(open(img, 'rb').read()).decode()))
    syms = []
    layout = [(15.24, 96.52), (68.58, 96.52), (121.92, 96.52), (15.24, 134.62), (68.58, 134.62), (121.92, 134.62),
              (175.26, 134.62)]
    for (key, sh), at in zip(children, layout):
        ss = schgen.SheetSymbol(root, sh, sh.title, at, (43.18, 20.32), [], page=0)
        syms.append(ss)
    return syms
