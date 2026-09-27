# ClaudeTestPCB — 3-Phase BLDC ESC (ESP32-WROOM-32E)

KiCad project for a 3-phase brushless motor ESC.

- **MCU:** ESP32-WROOM-32E, soldered SMD directly onto the PCB (no plug-in module)
- **Input:** 12–36V DC
- **Target continuous phase current:** ~5–10A
- **Control/telemetry:** UART + CAN bus
- Design follows [METU PowerLab PCB design rules](https://github.com/odtu/Powerlab/blob/master/KiCAD/PCB_DESIGN_RULES.md)
  and uses parts exclusively from [PowerLabKiCadLibraries](https://github.com/odtu/PowerLabKiCadLibraries).

## Status
- [x] GitHub repo created
- [x] ESP32-WROOM-32E symbol/footprint added to PowerLabKiCadLibraries (PR: odtu/PowerLabKiCadLibraries#2, pending merge)
- [x] KiCad 10 project scaffolded (`hardware/ESC3Phase.kicad_pro`)
- [x] Schematic (power supply, MCU core, gate drive, power stage, current sensing, communication) — see [hardware/ARCHITECTURE.md](hardware/ARCHITECTURE.md)
- [~] PCB layout — in progress, see [hardware/ARCHITECTURE.md](hardware/ARCHITECTURE.md#pcb-layout-status-in-progress-not-fabrication-ready) (outline/stackup/mounting holes/all footprints placed/GND+power pours/phase-output traces done; ~50 signal nets still unrouted, 21 courtyard overlaps to resolve, no autorouter available in this environment)
- [ ] DRC / ERC clean, fab outputs — not yet: 732 DRC violations remain (469 errors / 263 warnings)

## Layout
- `hardware/` — KiCad project
