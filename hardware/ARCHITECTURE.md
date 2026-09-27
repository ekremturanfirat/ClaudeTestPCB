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

### Power Supply
| Part | Library | Role |
|---|---|---|
| 7770 (M3, 15A) ×2 | Connectors_ScrewTerminals | VIN+, GND input terminals |
| SMBJ48CA-13-F | Diodes_TVSDiodes | VBUS transient/surge protection (48V standoff, safely above 36V max, ~77V clamp) |
| LM5050-1 | CircuitProtections_IdealDiodes | OR-ing/ideal-diode controller driving an external FET → reverse-polarity protection (low loss vs. a series diode) |
| NTMFS006N08MC | Transistors_MOSFETs | Reverse-polarity series FET (80V, 82A, 6mΩ — same part reused from Power Stage BOM line) |
| PTPS16890VMAR (TI TPS1689x) | CircuitProtections_eFuses | Input eFuse/hot-swap: 20A, 9–80V — inrush limiting + hardware overcurrent/short-circuit protection independent of firmware |
| 100µF Al-polymer ×2–3 | Capacitors_AluminumPolymers_ThroughHoles | DC bus bulk capacitance |
| LMR38020FSDDAR | Regulators_BuckConverters | VBUS (12–36V) → +5V_LOGIC, 2A (4.2–80V in, handles ESP32 WiFi current bursts + CAN txcvr + driver logic) |
| 6.8µH | Inductors_SurfaceMounts | LMR38020 buck inductor |
| NCP1117ST33T3G | Regulators_LDOs | +5V_LOGIC → +3V3_MCU (linear, quiet rail for MCU/CAN/driver logic) |

Rails: `+VBUS` (post-eFuse, 12–36V) → `+5V_LOGIC` → `+3V3_MCU`. `PGND` used for the
high-current power path, `GND` for logic (tied together at one star point).

### MCU Core
- U: **ESP32-WROOM-32E** (METUPowerLab_Microcontrollers_ESP32, pending PR merge). No external
  crystal/flash/antenna needed — all integrated in the module.
- Decoupling on 3V3/EN per module + LAYOUT notes.
- EN pull-up + RESET tactile switch, GPIO0 pull-up + BOOT tactile switch (**TL6330AF200Q** ×2,
  Switches_TactileSwitches) — manual flashing entry (no auto-DTR/RTS circuit; no onboard USB).
- 1x4 header (Connectors_SignalConnectors, `2147210040`) for UART0 (TX0/RX0/GND/3V3) — doubles
  as the programming header and the runtime UART control/telemetry link.

### Gate Drive
- U: **DRV8323RSRGZT** (MotorDrivers_BLDC) — 48-pin, integrated 3× current-shunt amps + internal
  buck (buck left **unused/shut down**; DVDD fed from +3V3_MCU instead, so driver logic and MCU
  share one clean 3.3V rail — simpler than running two independent 3.3V rails).
- Bootstrap caps (CPH/CPL charge pump, one per half-bridge bootstrap SHx) — ceramic, from
  Capacitors_Ceramics_SurfaceMounts (values per DRV8323 datasheet reference design, TBD at
  placement).
- SPI (SCLK/SDI/SDO/nSCS) + nFAULT + ENABLE + nSLEEP to ESP32 GPIOs (global labels).
- SOA/SOB/SOC (per-phase current-sense amp outputs) → ESP32 ADC-capable GPIOs.

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
| 7 | IO35 (ADC1_CH7, in-only) | spare (no_connect) |
| 8 | IO32 (ADC1_CH4) | SOA (DRV8323 phase-A current sense) |
| 9 | IO33 (ADC1_CH5) | SOB (DRV8323 phase-B current sense) |
| 10 | IO25 | EXP1 (expansion header — encoder/hall A) |
| 11 | IO26 | EXP2 (encoder/hall B) |
| 12 | IO27 | EXP3 (encoder/hall Z) |
| 13 | IO14 | ENABLE (DRV8323) |
| 14 | IO12 (MTDI, strap) | spare (no_connect — avoid driving at boot) |
| 15 | GND | GND |
| 16 | IO13 | nSLEEP (DRV8323) |
| 17–22 | NC ×6 | no_connect (internal SPI flash, not led out) |
| 23 | IO15 (MTDO, strap) | nFAULT (DRV8323, pull-up — matches safe strap default) |
| 24 | IO2 (strap, don't-care in SPI boot mode) | CAL (DRV8323) |
| 25 | IO0 (strap) | BOOT button + pull-up |
| 26 | IO4 | spare (no_connect) |
| 27 | IO16 | spare (no_connect) |
| 28 | IO17 | spare (no_connect) |
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
