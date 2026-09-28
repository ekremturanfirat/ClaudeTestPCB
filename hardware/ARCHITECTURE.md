# ESC3Phase — Architecture (Rev B)

3-phase BLDC/PMSM ESC with an ESP32-WROOM-32E soldered directly on the board. Input 12–36 V DC,
5–10 A continuous phase current, UART + CAN. Designed to the
[METU PowerLab PCB design rules](https://github.com/odtu/Powerlab/blob/master/KiCAD/PCB_DESIGN_RULES.md),
parts only from [PowerLabKiCadLibraries](https://github.com/odtu/PowerLabKiCadLibraries) (additions in
[PR #3](https://github.com/odtu/PowerLabKiCadLibraries/pull/3)).

Rev A (first attempt) was withdrawn: its schematic had real net shorts (+5V_LOGIC merged with the 36 V bus,
INHA and EFUSE_IMON merged with GND), did not follow the drawing rules, and had several datasheet errors
(listed at the end). Rev B is a full rebuild.

## Verification (kicad-cli 10.0.5)
- **ERC: 0 errors.** 11 warnings, all `pin_to_pin` "Bidirectional and Power output": the library's connector
  pins (J1, J2, J3, J4, J8) are typed `bidirectional` and sit on a net that has a `power_out` pin — a PWR_FLAG
  (VIN_RAW, +3V3_MCU) or DRV8323 pin 45 (SW of the unused internal buck, tied to GND as TI requires).
  Not a wiring fault; reported upstream as a library observation.
- **Netlist check:** KiCad's exported netlist was compared net-by-net with the intended connections of every
  pin: 79 nets, 0 shorts, 0 opens.
- Every sheet was exported to PDF and reviewed visually.

## Sheets
| Page | Sheet | Content |
|---|---|---|
| 1 | Overview (root) | specs, block diagram, revision history, sheet symbols |
| 2 | Power Input & Protection | J3/J4, SMBJ36CA, LM74700-Q1 + Q1, TPS16890 eFuse |
| 3 | Power Supply 3.3 V | LMR38020 buck, +3V3_MCU, ferrite-filtered +3V3_A, power LED |
| 4 | DC-Bus Current Sensing | 5 mΩ shunt, net-tie Kelvin taps, INA240A1 |
| 5 | MCU Core | ESP32-WROOM-32E, EN/BOOT, UART J1, expansion J2, status LED, ADC filters |
| 6 | Gate Drive | DRV8323RS with charge pump, CSA reference, pull-ups/downs |
| 7 | Power Stage | bulk caps, TMP235, 3× Half Bridge (one sub-sheet reused) |
| 8–10 | Half Bridge A/B/C | 2× NTMFS006N08MC, 2 mΩ shunt, 2 net ties, phase terminal, hot-loop caps |
| 11 | Communication | SN65HVD230, split termination, CAN ESD, J8 |

## Rails
`VIN_RAW` (connector) → `+VBUS` (after reverse-polarity FET) → `+VBUS_EFUSE` (eFuse out) → DC shunt →
`+VBUS_PROT` (motor bus, DRV8323 VM, buck input) → `+3V3_MCU` (buck) → `+3V3_A` (ferrite-filtered: DRV8323
VREF, INA240, TMP235). Single `GND`.

## Design details (datasheet references)
### Power Input — TI SNOSD17G (LM74700-Q1), SLVSHO1A (TPS1689x), Diodes DS19002 (SMBJ)
- **D10 SMBJ36CA:** 36 V standoff, 58.1 V clamp at 10.3 A. That stays below the 65 V limits of LM74700 ANODE
  and DRV8323 VM. SMBJ48CA (77.4 V clamp) was too high.
- **U2 LM74700-Q1 + Q1:** MOSFET source on the input (ANODE), drain on the output (CATHODE). EN is tied to
  ANODE. C11 100 nF sits between VCAP and ANODE; it is rated 16 V because VCAP–ANODE ≤ 15 V.
- **U3 TPS16890 eFuse** (standalone):
  - VDD filter: R10 120 Ω + C14 100 nF/100 V. TI recommends 150 Ω / 0.22 µF; these are the nearest library values.
  - UVLO: R11 866 k / R12 118 k → 10.1 V rising. The internal VIN_UV_FLT default of 10.66 V dominates.
  - Circuit breaker: R17 IMON 3.65 k → IOCP = 1 V / (18.18 µA/A × 3.65 k) = 15.1 A (Eq. 4–6). C16 22 pF.
  - ILIM: R18 1.33 k (Eq. 25, N = 1). IREF: C17 1 nF.
  - dVdT: C18 100 nF → 0.5 V/ms, about 0.13 A inrush into ~250 µF, below the 0.5 A start-up limit.
  - WP# → GND. ADDR0/ADDR1 open (address 0x40). SWEN, AUX, TEMP and NC left open.
  - SDA/SCL and PGOOD pulled up to 3.3 V. FLT → `EFUSE_NFLT` → ESP32 IO35.
  - The exposed pad is **IN**, not GND.
- Residual risk: during a surge clamped at 58 V, EN/UVLO reaches about 7 V, above its 6 V absolute maximum
  (surge only; no zener in the library).

### Power Supply — TI SNVSC40E (LMR38020)
- **Output 3.3 V directly.** The Rev A 5 V rail and NCP1117 were removed: NCP1117 needs 33 mΩ–2.2 Ω output ESR,
  which ceramic caps don't give.
- FB divider 110 k / 47 k → 3.34 V (VFB = 1.0 V).
- RT 54.9 k → about 480 kHz. At 36 V in, the on-time is 191 ns, above the 131 ns minimum.
- L1 4.7 µH / 8.1 A (Isat 7.4 A), above the 3.8 A high-side current limit.
- C23/C24 47 µF/25 V + 100 nF out; C20 4.7 µF/100 V + C21 100 nF/100 V in; CBOOT 100 nF.
- EN tied to VIN. PG pulled up to 3.3 V (TP22).

### Current Sensing — TI SBOS662C (INA240)
- R30 5 mΩ (VMP 2010) in the bus. INA240**A1** (20 V/V) → 100 mV/A, 1.5 V at 15 A.
- A4 (200 V/V) would saturate at 3.1 A. REF1/REF2 go to GND (unidirectional).
- Kelvin taps through net ties NT1/NT2.

### MCU Core — Espressif ESP32-WROOM-32E datasheet v2.1 + hardware design guidelines
- 22 µF + 100 nF at 3V3. EN: 10 k / 1 µF plus the RESET button. IO0: 10 k pull-up plus the BOOT button.
- ADC inputs are all on ADC1. Filters are 220 pF, because the INA240 and TMP235 allow at most 1 nF load.
- Strapping pins:
  - IO12 (MTDI) and IO2 carry PWM lines with 10 k pull-downs, so they read low at boot (3.3 V flash, download mode possible).
  - IO5 has a 10 k pull-up on nSCS. The DRV8323 has an internal pull-down that would otherwise fight the strap.
  - IO15 carries NFAULT with a pull-up (high = boot log enabled).
- Module pin 39 (exposed GND pad) is included in the footprint.

| Pin | Name | Net | | Pin | Name | Net |
|---|---|---|---|---|---|---|
| 2 | 3V3 | +3V3_MCU | | 23 | IO15 | NFAULT |
| 3 | EN | EN | | 24 | IO2 | PWM_AL |
| 4 | SENSOR_VP | IBUS_SENSE | | 25 | IO0 | BOOT |
| 5 | SENSOR_VN | TEMP_SENSE | | 26 | IO4 | PWM_BH |
| 6 | IO34 | ISENSE_C | | 27 | IO16 | PWM_CH |
| 7 | IO35 | EFUSE_NFLT | | 28 | IO17 | PWM_CL |
| 8 | IO32 | ISENSE_A | | 29 | IO5 | SPI_NSCS |
| 9 | IO33 | ISENSE_B | | 30 | IO18 | SPI_SCLK |
| 10 | IO25 | EXP1 | | 31 | IO19 | SPI_SDO |
| 11 | IO26 | EXP2 | | 33 | IO21 | CAN_TX |
| 12 | IO27 | LED_STATUS | | 34 | RXD0 | UART_RXD |
| 13 | IO14 | DRV_ENABLE | | 35 | TXD0 | UART_TXD |
| 14 | IO12 | PWM_BL | | 36 | IO22 | CAN_RX |
| 16 | IO13 | PWM_AH | | 37 | IO23 | SPI_SDI |
| 1, 15, 38, 39 | GND | GND | | 17–22, 32 | NC | not connected |

### Gate Drive — TI SLVSDJ3D (DRV8323RS)
- VM decoupling: 100 nF/100 V + 10 µF/100 V. VDRAIN → +VBUS_PROT.
- Charge pump: CPH–CPL 47 nF/100 V; VCP–VM 1 µF.
- DVDD: 1 µF only. It is an internal LDO output (30 mA max) and cannot supply anything else.
- **VREF is an input.** It is driven from +3V3_A with 100 nF. Rev A left it floating.
- The unused integrated buck (VIN, SW, CB, FB, nSHDN, BGND) is tied to GND (Table 9-3). CAL → GND
  (calibration is done over SPI).
- nFAULT and SDO are open-drain, with 10 k pull-ups. PWM inputs and ENABLE have 10 k pull-downs, so they
  default off.
- CSA: the default gain is 20 V/V. With 2 mΩ that gives ±0.6 V around VREF/2 at ±15 A, i.e. 1.05–2.25 V.

### Power Stage / Half Bridge — onsemi NTMFS006N08MC
- 80 V MOSFETs with 4.9 mΩ typical RDS(on). Gate drive is IDRIVE (no gate resistors).
- Low-side shunt: 2 mΩ SSA2512. Kelvin sense goes through two net ties per phase to SPx/SNx.
- Hot-loop caps per leg: 10 µF/100 V + 100 nF/100 V. Bulk: 2× 100 µF/63 V Al-polymer.
- TMP235 near the power stage, 10 mV/°C.

### Communication — TI SLOS346O (SN65HVD230)
- RS → GND (high speed). VREF open.
- Split termination 2× 56 Ω + 4.7 nF. For a multi-drop bus, mark R60/R61/C61 DNP on every node except the two ends.
- ESD: CDSOD323-T24SC (24 V) per line. SP0115 (1 V working voltage) was unsuitable.
- J8: 1 CANH, 2 CANL, 3–4 GND.

## Rev A errors fixed in Rev B
| Rev A | Problem | Rev B |
|---|---|---|
| Labels on pins, off-grid | real net shorts (+5V↔36 V bus, INHA↔GND, IMON↔GND) | wires + power symbols on the 2.54 mm grid, netlist check |
| DRV8323 VREF floating | current-sense amplifiers can't work | VREF = +3V3_A |
| DRV8323 buck pins NC | datasheet says tie to GND | tied to GND |
| INA240A4 | saturates at 3.1 A | INA240A1 |
| LM5050-1, FET reversed | not reverse-polarity protection | LM74700-Q1, source on input |
| SMBJ48CA | 77 V clamp > 65 V limits | SMBJ36CA (58 V) |
| eFuse VDD cap 16 V, pin 20/21 mix-up | over-voltage, wrong straps | 100 V cap, pins per SLVSHO1A |
| NCP1117 + 5 V rail | unstable with ceramic output caps | buck makes 3.3 V directly |
| 6.8 µH / 1.87 A inductor | below the 3.8 A current limit | 4.7 µH / 8.1 A |
| 0805 shunt part on 2010 footprint | footprint/part mismatch, no Kelvin | 2512 part, net-tie Kelvin |
| SP0115 on CAN | conducts at 1.4 V | 24 V TVS |
| Descriptions in Value fields | breaks BOM, rule 1.8 | library values |

## PCB (Rev B)
![Top](docs/ESC3Phase_top.png)

### Verification (kicad-cli 10.0.5, zones refilled, schematic parity on)
- **DRC: 0 errors, 0 unconnected, 0 parity issues.**
- **Corners:** no track corner is sharper than 45° (rule 3.3). A script checks every track joint.
- **2 warnings, both explained:** the ESP32 silk outline extends past the board edge. The antenna overhangs
  the top edge on purpose, and silk off the board is simply not printed.

### Board
- **Size:** 100 × 90 mm, 1 mm corner radius, 4 × M3 NPTH holes, 3 fiducials.
- **Layers (4, approved by the user for routing density and a solid ground reference):**

  | Layer | Use |
  |---|---|
  | L1 | parts and signals |
  | L2 | solid GND plane |
  | L3 | signals, then a GND fill |
  | L4 | signals, then a GND fill |

- **Stackup:** 1.6 mm, 1 oz copper on all layers, FR-4, lead-free HASL, green mask and white silk. This is the
  PCBWay standard 4-layer spec. The 4 layers themselves are the only surcharge.

### Floor plan (rule 3.2)
- **Top edge:**
  - ESP32 module, with the antenna over the edge
  - UART header J1
  - expansion header J2
  - CAN connector J8, with the SN65HVD230 transceiver, ESD diodes and split termination below it
- **Left side:** the 3.3 V buck (LMR38020), then the INA240 with its DC-bus shunt R30.
- **Bottom left:** input terminals J4 (GND) and J3 (VIN). Power flows up through the TVS, the
  reverse-polarity FET Q1 with the LM74700 and the TPS16890 eFuse, then R30, into the bus.
- **Right side:** the DRV8323 sits above three half-bridge columns at 16.25 mm pitch. Each column has the
  high-side FET, the low-side FET, and a 2512 shunt with net-tie Kelvin taps.
  - Hot-loop caps (10 µF + 100 nF) sit right above each high-side drain.
  - Two 100 µF bulk caps sit at the left end of the bus.
  - Phase terminals J5–J7 (A/B/C) are on the bottom edge.
- **Decoupling:** every cap is at its IC pin. A placement checker enforces 1 mm pad-to-pad between parts and
  the mounting-hole keepouts, because the library parts have no courtyards.

### Copper
- **Pours (L1):**
  - `+VBUS_PROT`: a 7.5 mm band over all three drains, with a spur to the bulk caps
  - phase node plus a ~5.5 mm lane to each terminal
  - low-side source into each shunt
  - `VIN_RAW`, `+VBUS` and `+VBUS_EFUSE` along the input chain
- **GND:** L2 is solid; L1, L3 and L4 are filled. Every SMD GND pad has its own via to the plane. There are
  stitching vias on a 5 mm grid and along the edges.
- **Hand-routed DRV8323 gate drive.** Each gate runs as a pair with its own phase-sense return, with 0.6 mm to
  everything else.
  - Phase A: left pins → L1 → under the bus band on L4 → back up into the lane beside its FETs.
  - Phase C: east on L1 above the band, then the same crossing.
  - Phase B: its pins leave in the reverse order of its lane, so it runs on L4 and pops up with a via at each
    target.
  - The charge-pump, VCP and VM caps sit at their pins.
- **Other routing:**
  - Freerouting 2.4.1 routed the logic; a small grid router with exact clearances did the last four
    connections.
  - 90° corners were mitered to 45°.
  - Router neck-downs were widened to the 0.2 mm lab default, except where a fine-pitch pad needs PCBWay's
    0.15 mm floor. That applies to one segment.

### 36 V clearance (rules 2.6 / 3.3) — `ESC3Phase.kicad_dru`
- **Net class `HV`:** 0.6 mm clearance (IPC-2221B B2, outer layers, 31–100 V). It covers the bus nets
  (`VIN_RAW`, `+VBUS*`), the phases, and the gate, bootstrap and charge-pump nets. Inner layers use 0.2 mm
  (B1 allows 0.1 mm, so the fab minimum applies).
- **Waivers (documented in the rules file):**
  1. **Pads within one part.** The parts' own pad geometry is below 0.6 mm (0603 caps across the bus,
     0.5 mm-pitch QFN). Pads of different parts are ≥ 1.0 mm apart.
  2. **Fine-pitch fan-out areas (`HV_FANOUT_*` rule areas).** These cover the DRV8323 cluster, the eFuse,
     the LM74700, the buck, the TMP235 and the MOSFET gate pins. The user said to ignore the ICs for this
     rule.
  3. **HV net pairs with ≤ ~12 V between them:** gate ↔ its own phase, VCP ↔ VM, BOOT ↔ SW, LM74700 gate/VCAP
     ↔ input, shunt sense ↔ bus.

### Silkscreen and board information (rule 3.6)
- **Top:**
  - reference designators, 1.0 mm, at 0° or 90°, placed so they never cross pads, parts or labels
  - `+12-36V` / `GND` at the input
  - `A` / `B` / `C` at the phases
  - J2 pin names, and pin-1 marks on J1 and J8
- **25 references on the assembly drawing only.** In the densest spots (the ESP32 caps, eFuse passives and CAN
  ESD diodes) no legal 1.0 mm silk position exists, so these are on the F.Fab (assembly) layer only.
- **Bottom:**
  - METU PowerLab logo
  - project, Rev B and date (text variables `${PROJECT_NAME}`, `${REVISION}`, `${ISSUE_DATE}`)
  - designer, website and GitHub
  - UART and CAN pinout
  - the lab QR code, 13.3 mm, with the light modules printed so it reads with normal polarity on dark
    mask. **Scan it on a real board or render.**

### Library fixes made for this board — [PowerLabKiCadLibraries PR #5](https://github.com/odtu/PowerLabKiCadLibraries/pull/5)
| Footprint | Fix |
|---|---|
| DRV8323, TPS16890 | Mask margin 0.1 → 0.05 mm. On 0.5 mm pitch this fixes the mask bridges. |
| LMR38020 | The exposed pad was opened on both sides; it is now top only. |
| LMR38020, TPS16890, ESP32 | Thermal vias now 0.6 mm (a 0.15 mm annular ring), open on the pad side and tented underneath. |
| MOSFETs | Stray bottom paste removed. |
| New | `METUPowerLab_Graphics` library (logo, QR code) and the ESP32 STEP model from Espressif (CC-BY-SA 4.0). |

### Assembly notes
- **Breakaway rails needed.** The antenna overhang and the edge-mounted connectors put parts within 3.5 mm of
  the top and bottom edges. Machine assembly at PCBWay therefore needs breakaway rails, which are added during
  panelization.
- **Hand soldering:** power pads connect solid to their pours. The screw terminals are THT with solid
  connections, so a larger soldering iron is needed.

### Fab outputs
Gerber + drill zip, BOM, position file and assembly drawings are in [fab/](fab/README.md). All share one
origin, the board's bottom-left corner. Before ordering: check the Gerbers in a viewer, print the layout 1:1
to check the footprints, and scan the QR code.
