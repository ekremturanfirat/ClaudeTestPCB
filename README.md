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
- [x] ESP32-WROOM-32E added to PowerLabKiCadLibraries (odtu/PowerLabKiCadLibraries#2, merged)
- [x] Library additions + fixes (power symbols, mounting holes, fiducials, test pads, net ties, ESP32 footprint fix): odtu/PowerLabKiCadLibraries#3 (open)
- [x] Schematic Rev B: full rebuild per the PowerLab rules; kicad-cli ERC 0 errors, netlist verified (see [hardware/ARCHITECTURE.md](hardware/ARCHITECTURE.md))
- [ ] PCB layout (Rev B)
- [ ] DRC clean, fab outputs

## Layout
- `hardware/` — KiCad project
