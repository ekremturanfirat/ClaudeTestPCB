# ESC3Phase — Architecture

3-phase BLDC/PMSM ESC. ESP32-WROOM-32E (soldered SMD, sensorless FOC capable via DRV8323's
integrated current-shunt amplifiers). 12–36V DC input. ~5–10A continuous phase current target.
Control/telemetry: UART (also doubles as the flashing/programming interface) + CAN (TWAI).

All parts below are from PowerLabKiCadLibraries (verified present in the installed 10.0
3rdparty library) except the ESP32-WROOM-32E itself, which is pending merge as
odtu/PowerLabKiCadLibraries#2.

## Sheets

1. **Power Supply** — input protection + regulation
2. **MCU Core** — ESP32-WROOM-32E + support circuitry
3. **Gate Drive** — DRV8323RS 3-phase gate driver
4. **Power Stage** — 6x half-bridge MOSFETs, phase shunts, bulk caps, phase outputs
5. **Current Sensing** — DC-bus total current sense (separate from DRV8323's per-phase sense,
   which lives on the Gate Drive/Power Stage sheets)
6. **Communication** — CAN transceiver + connector, UART header

## Component selections (with rationale)

### Power Supply — as built (schematic-verified, PowerSupply.kicad_sch)

Rail naming: `VIN_RAW` (raw connector input) → `+VBUS` (post reverse-polarity FET,
pre-eFuse) → `+VBUS_PROT` (post-eFuse; feeds Gate Drive/Power Stage VM) → `+5V_LOGIC`
(post-buck) → `+3V3_MCU` (post-LDO). `GND` is common throughout (single star point at
the input connector).

| Ref | Part | Library | Role / value notes |
|---|---|---|---|
| J3, J4 | 7770 (M3, 15A) | Connectors_ScrewTerminals | VIN_RAW+, GND input terminals (one pole each) |
| D1 | SMBJ48CA-13-F | Diodes_TVSDiodes | VIN_RAW transient/surge protection (48V standoff, ~77V clamp) |
| U2 | LM5050-1 | CircuitProtections_IdealDiodes | High-side N-ch ORing/ideal-diode controller → reverse-polarity block |
| Q1 | NTMFS006N08MC | Transistors_MOSFETs | Reverse-polarity series FET, D=VIN_RAW, S=+VBUS, G=U2.GATE (80V/82A/6mΩ, shared BOM line with Power Stage) |
| U3 | PTPS16890VMAR (TI TPS1689x eFuse) | CircuitProtections_eFuses | +VBUS→+VBUS_PROT, 20A/9–80V. **Fully wired per the real TI TPS1689 datasheet** (SLVSHO1A, fetched directly), standalone/non-parallel config: R4=120Ω/C10=100nF (VDD R-C filter — datasheet spec is 150Ω/0.22µF, substituted to nearest library values), R5=866kΩ/R6=118kΩ (EN/UVLO divider, trips ≈10.0V, formula-derived) + C11=100pF noise cap, C12=1nF (IREF), C13=10nF (DVDT, placeholder — tune per Eq.16/17 against actual bulk C once inrush target is set), C14=1nF (TEMP), R7=1.2kΩ (ILIM) + R8=3kΩ (IMON) + C15=22pF → sets circuit-breaker OCP ≈18.3A (formula-derived, library's nearest values to the datasheet-recommended 1.24k/3.4k), R9=10kΩ pulldown (AUX), R10/R11=10kΩ pull-ups to +3V3_MCU (SDA/SCL, PMBus unused), ADDR0/ADDR1/SWEN/WP#→GND direct (standalone/address-0/PMBus-write-disabled), FLT/PGOOD left unconnected (no external pull-up available pre-buck without exceeding their 6V abs-max if pulled to +VBUS_PROT) |
| C16/C17 | 4.7µF / 100nF | Capacitors_Ceramics_SurfaceMounts | eFuse/buck input bypass |
| U4 | LMR38020FSDDAR | Regulators_BuckConverters | +VBUS_PROT→+5V_LOGIC, 2A. **Per TI datasheet (SNVSC40E)**: EN tied directly to VIN (precision-enable, "do not float" but explicitly may tie to VIN), R12=22.1kΩ RT (≈1.1MHz switching — nearest library value to the table's 1MHz/25.5kΩ row), R13=88.7kΩ/R14=22.1kΩ FB divider (gives 5.01V, computed from VREF=1V), C18=100nF BOOT-to-SW (16V+ rating), R15=100kΩ PG pull-up to +5V_LOGIC |
| L1 | 6.8µH | Inductors_SurfaceMounts | Buck inductor (matches the datasheet's own 1MHz/24V/5V design-table row) |
| C19/C20 | 22µF ×2 | Capacitors_Ceramics_SurfaceMounts | Buck output caps (datasheet table: 2×22µF nominal) |
| U5 | NCP1117ST33T3G | Regulators_LDOs | +5V_LOGIC→+3V3_MCU, standard 3-pin LDO app circuit |
| C21/C22 | 1µF / 10µF | Capacitors_Ceramics_SurfaceMounts | LDO input/output caps |
| #FLG1–4 | power:PWR_FLAG | (stock KiCad, annotation-only) | ERC power-source markers on VIN_RAW/+VBUS/EFUSE_VDD/GND — these pass-through/sense-only nets have no pin typed `power_out` in this sheet, which otherwise trips ERC's "undriven power net" check even though they're genuinely driven in the real circuit |

**Flagged for the user / future review:**
- eFuse VDD R-C filter (120Ω/100nF) and DVDT cap (10nF) are the closest available
  library values / a placeholder pending a defined inrush-current target — not exact
  datasheet values (150Ω/0.22µF was requested but isn't in the Resistors/Capacitors
  library).
- Two residual ERC items on `PowerSupply.kicad_sch` after a full pass: (1) U3's two
  `OUT` pins (7/8) both tied to +VBUS_PROT trips "power output tied to power output" —
  expected/harmless, this is the datasheet's own recommended parallel-pin connection;
  (2) one more `Output`/`Power output` pairing on pin 2 (IMON) I could not fully
  root-cause in the time available — worth a look in KiCad's ERC dialog directly.
- The vendor's own `PTPS16890VMAR` symbol (in PowerLabKiCadLibraries) has a real
  authoring defect: pin 20 is defined **twice** (once named `SWEN`, once named `WP#`,
  at two different physical locations) and pin 21 (`WP#`'s real datasheet pin number)
  doesn't exist in the symbol at all. Worth reporting upstream; I worked around it here
  by labeling both physical pin-20 instances to GND directly by position.

### MCU Core
- U: **ESP32-WROOM-32E** (METUPowerLab_Microcontrollers_ESP32, pending PR merge). No external
  crystal/flash/antenna needed — all integrated in the module.
- Decoupling on 3V3/EN per module + LAYOUT notes.
- EN pull-up + RESET tactile switch, GPIO0 pull-up + BOOT tactile switch (**TL6330AF200Q** ×2,
  Switches_TactileSwitches) — manual flashing entry (no auto-DTR/RTS circuit; no onboard USB).
- 1x4 header (Connectors_SignalConnectors, `2147210040`) for UART0 (TX0/RX0/GND/3V3) — doubles
  as the programming header and the runtime UART control/telemetry link.

### Gate Drive — as built (GateDrive.kicad_sch), wired per the real TI DRV8323R datasheet
(SLVSDJ3D, fetched directly — this is a single-charge-pump architecture, **not**
per-phase bootstrap capacitors; that assumption in the original plan was wrong)

- U6: **DRV8323RSRGZT** (= DRV8323R, RGZ 48-pin VQFN, SPI variant). DVDD is the chip's
  own internal 3.3V logic LDO **output** (not something you feed externally) — just
  decoupled with C27=1µF to AGND, left otherwise unconnected. The digital I/O (SPI +
  PWM pins) are DVDD-referenced, which is compatible with the ESP32's 3.3V logic
  directly.
- Charge pump (shared across all 3 high sides — no per-phase bootstrap caps needed):
  C23=47nF/100V between CPH/CPL, C24=1µF between VCP and +VBUS_PROT.
- VM decoupling: C25=100nF + C26=10µF/75V across VM/PGND. VDRAIN tied to +VBUS_PROT
  (common high-side drain sense node).
- VREF: self-generated reference, C28=100nF decouple to AGND only.
- Optional integrated 600mA buck (VIN/SW/CB/FB) **disabled** — nSHD tied directly to
  GND (it has an internal pull-up, so floating would enable it; must be actively
  pulled low), VIN/SW/CB/FB left no_connect.
- CAL tied directly to GND (auto offset calibration also runs automatically; the
  dedicated pin is only needed for manual re-trigger, not implemented here to save a
  GPIO — see the MCU pin-map correction below).
- 6× hardware PWM pins (INHA/INLA/INHB/INLB/INHC/INLC) to ESP32 GPIOs — **these are
  required even on the SPI variant** (SPI is config/telemetry only, PWM switching is
  always via these dedicated pins) — each with its own 10kΩ pull-down so gates default
  off before the MCU's firmware configures its GPIOs.
- ENABLE: 10kΩ pull-down (defaults to sleep/safe) + ESP32 GPIO (global label).
- SPI (SCLK/SDI/SDO/nSCS) to ESP32 GPIOs; SDO (open-drain) gets its own 10kΩ pull-up
  to +3V3_MCU.
- nFAULT → ESP32 GPIO (pull-up already placed on the MCU Core sheet, shared net).
- SOA/SOB/SOC (per-phase current-sense amp outputs) → ESP32 ADC-capable GPIOs.
- SPA/SNA/SPB/SNB/SPC/SNC + GHx/SHx/GLx → Power Stage sheet (global labels).

### Power Stage
- Q1–Q6: **NTMFS006N08MC** (80V, 82A, 6mΩ) — 3× half-bridges (2 FETs each), driven by DRV8323's
  GHx/GLx/SHx.
- 3× phase shunts: **2 mOhm 1Watt** (Resistors_ShuntResistors), Kelvin-connected into DRV8323's
  SPx/SNx pins (`LAYOUT: Kelvin connection` note required on schematic).
- **TMP235A4DCKR** (Sensors_Temperature) near the FET cluster for thermal monitoring.
- 3× phase output terminals: **7770** (M3, 15A) screw terminals.
- Local bulk + decoupling ceramics across VM/PGND at the half-bridges (hot loop, `LAYOUT` note).

### Current Sensing (DC bus, independent of per-phase sensing)
- DC-bus shunt: **5 mOhm** (Resistors_ShuntResistors), in series with +VBUS after the eFuse.
- **INA240A4DR** (200V/V gain, enhanced PWM rejection) → ESP32 ADC — total input current for
  telemetry/redundant protection alongside the eFuse's own hardware limit.

### Communication
- **SN65HVD230DR** (3.3V-native CAN transceiver) — TXD/RXD to ESP32 TWAI-capable GPIOs, CANH/CANL
  to bus connector.
- **SP0115-01UTG** (TVS diode array) on CANH/CANL for ESD/bus-fault protection.
- 1x4 header (Connectors_SignalConnectors, `384471-E`) for CANH/CANL/GND/+VBUS (or unpowered,
  TBD) bus connector.

## ESP32-WROOM-32E pin map

| Pad | Name | Assignment |
|---|---|---|
| 1 | GND | GND |
| 2 | 3V3 | +3V3_MCU |
| 3 | EN | EN (pull-up + RESET button) |
| 4 | SENSOR_VP (ADC1_CH0) | INA240 OUT (DC-bus current) |
| 5 | SENSOR_VN (ADC1_CH3) | TMP235 OUT (temperature) |
| 6 | IO34 (ADC1_CH6, in-only) | SOC (DRV8323 phase-C current sense) |
| 7 | IO35 (ADC1_CH7, in-only) | spare (no_connect — input-only pin, can't drive a PWM output) |
| 8 | IO32 (ADC1_CH4) | SOA (DRV8323 phase-A current sense) |
| 9 | IO33 (ADC1_CH5) | SOB (DRV8323 phase-B current sense) |
| 10 | IO25 | EXP1 (expansion header — encoder/hall A) |
| 11 | IO26 | EXP2 (encoder/hall B) |
| 12 | IO27 | EXP3 (encoder/hall Z) |
| 13 | IO14 | ENABLE (DRV8323) |
| 14 | IO12 (MTDI, strap) | INLB → DRV8323 PWM (safe: DRV8323 input is high-Z, doesn't disturb the boot-strap read) |
| 15 | GND | GND |
| 16 | IO13 | INHA → DRV8323 PWM |
| 17–22 | NC ×6 | no_connect (internal SPI flash, not led out) |
| 23 | IO15 (MTDO, strap) | nFAULT (DRV8323, pull-up — matches safe strap default) |
| 24 | IO2 (strap, don't-care in SPI boot mode) | INLA → DRV8323 PWM |
| 25 | IO0 (strap) | BOOT button + pull-up |
| 26 | IO4 | INHB → DRV8323 PWM |
| 27 | IO16 | INHC → DRV8323 PWM |
| 28 | IO17 | INLC → DRV8323 PWM |
| 29 | IO5 (VSPICS0) | nSCS → DRV8323 SPI |
| 30 | IO18 (VSPICLK) | SCLK → DRV8323 SPI |
| 31 | IO19 (VSPIQ/MISO) | SDO ← DRV8323 SPI |
| 32 | NC | no_connect |
| 33 | IO21 | CAN_TX → SN65HVD230 |
| 34 | RXD0 (GPIO3) | UART0 RX (header + control link) |
| 35 | TXD0 (GPIO1) | UART0 TX (header + control link) |
| 36 | IO22 | CAN_RX ← SN65HVD230 |
| 37 | IO23 (VSPID/MOSI) | SDI → DRV8323 SPI |
| 38 | GND | GND |

## Correction after reading the real DRV8323R datasheet (TI SLVSDJ3D)

The initial MCU pin map (above, now corrected) was wrong in two ways, caught only after
fetching the actual DRV8323R datasheet before wiring Gate Drive:
- **DRV8323R has no separate "nSLEEP" pin.** `ENABLE` alone controls sleep (low = sleep).
  What I'd labeled `nSLEEP` on IO13 was fictitious; IO13 is reassigned to `INHA`.
- **DRV8323R needs 6 direct hardware PWM pins** (INHA/INLA/INHB/INLB/INHC/INLC) —
  separate from SPI, and required even on the "S" (SPI) variant, since SPI is only for
  configuration/telemetry, not per-cycle switching. I'd completely missed these in the
  first pass. Freed up by tying `CAL` directly to GND instead of routing it to a
  dedicated MCU pin (auto-offset-calibration also runs automatically per the datasheet;
  a hardware CAL pulse is an optional extra, not required), and reassigning the
  now-nonexistent-nSLEEP pin. All 6 PWM pins get their own 10kΩ pull-down (Gate Drive
  sheet) so the driver's gate inputs default low/safe before the MCU's firmware
  configures its GPIOs as outputs.

## Deviations / notes flagged to the user
- **Power symbols vs. global labels**: the design rules say power rails should use KiCad power
  symbols (GND, etc.) and only signal nets use global labels. Stock KiCad power symbols only
  cover generic names (`+3.3V`, `+5V`, `GND`); our rail names are domain-specific
  (`+3V3_MCU`, `+5V_LOGIC`, `+VBUS`) per the naming rule. Rather than author new power-symbol
  parts, I'm using **global labels** for the named rails (electrically identical — both are
  hierarchy-wide nets) and the stock `power:GND` symbol for ground. Flagging this as a
  pragmatic reading of the rule, not a silent substitution.
- Inductor value (6.8µH) and bootstrap cap values are reasonable defaults pending a datasheet
  cross-check against TI's LMR38020 / DRV8323 reference designs during placement.
- ESP32-WROOM-32E symbol/footprint is pending PR merge (see PR #2) — using it locally already
  since it's registered in the local KiCad 10 library path.
