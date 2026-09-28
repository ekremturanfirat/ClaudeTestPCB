# ESC3Phase Rev B — fabrication and assembly files

Generated with kicad-cli 10.0.5 from `../ESC3Phase.kicad_pcb`. DRC with schematic parity passed with
0 errors, 0 unconnected items and 0 parity issues. Two warnings remain: the ESP32 silk outline runs over the
antenna overhang.

## Files
| File | Use |
|---|---|
| `ESC3Phase_Gerber_Drill_RevB.zip` | Upload this to PCBWay. It contains the Gerbers, the Excellon drill files (PTH and NPTH), the drill maps and the Gerber job file. |
| `gerber/` | The same files unzipped. |
| `ESC3Phase_BOM.csv` | BOM grouped by value, footprint and MPN. Columns: reference, quantity, value, manufacturer, MPN, package, SMD/THT, Digi-Key, Mouser, footprint, note. UTF-8 with BOM, so Excel shows "µ" correctly. |
| `ESC3Phase_pos.csv` | Position file (centroids) for the 102 SMD parts, top side. Units are mm; the origin is the bottom-left board corner and Y points up. |
| `ESC3Phase_assembly_top.pdf` / `_bottom.pdf` | Assembly drawings: Fab + silk + outline at 1.4×. They show the 25 references that have no room on the silkscreen. |

All outputs share one origin, the board's bottom-left corner (the drill/place origin).

## PCB order (PCBWay)
| Option | Value |
|---|---|
| Size | 100 × 90 mm, 1 mm corner radius |
| Layers | **4** (the only option above the standard-price spec, approved) |
| Stackup | 1.6 mm FR-4 TG150–160: L1 / 0.2 mm prepreg / L2 / 1.04 mm core / L3 / 0.2 mm prepreg / L4 |
| Copper | 1 oz outer, 1 oz inner |
| Min track / space | 0.15 / 0.2 mm (6/6 mil class). One 0.15 mm neck-down; everything else is ≥ 0.2 mm |
| Min hole | 0.3 mm (445 plated holes, 8 non-plated) |
| Solder mask / silk | green / white |
| Surface finish | HASL lead-free |
| Vias | tented, except the thermal vias in exposed pads, which are open on the pad side |
| Extras | none: no impedance control, castellations or blind vias |

## Assembly
- **Parts:** 109 in total, 102 SMD (all on top) and 7 THT: C56/C57 bulk caps and J3–J7 screw terminals. Only top-side paste is needed; the bottom paste layer is empty.
- **Breakaway rails needed for machine assembly.** The ESP32 antenna overhangs the top edge, and the connectors and terminals sit within 3.5 mm of the top and bottom edges. Add the rails when panelizing.
- **Fiducials:** 3 global fiducials on top.
- **BOM notes:**
  - **C3, C44 and C42 (1 µF):** order by the MPN (Murata GRM188D72A105KE01D, 0603, 100 V). The Digi-Key and Mouser numbers in the library point to a different part (a Samsung 1210). That's a library data issue.
  - **R60, R61 and C61 (CAN split termination):** fit them only on the two nodes at the ends of the bus. Leave them unfitted (DNP) on every other node.
- **Hand soldering:** power pads and the screw terminals connect solid to their pours, so use a large iron tip.

## Before ordering
- Check the Gerbers in a Gerber viewer (KiCad GerbView or PCBWay's online viewer).
- Print the layout 1:1 and check the footprints against the real parts (rule 3.7).
- Scan the QR code on the bottom silk (see `../docs/ESC3Phase_bottom.png`).
