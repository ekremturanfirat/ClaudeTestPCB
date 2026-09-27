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

## PCB
Not started in Rev B yet (next step): fresh board from this netlist, placement per rule §3.2, pours for the
power paths, Freerouting for signals, full DRC with kicad-cli.
