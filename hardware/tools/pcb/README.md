# PCB generation scripts (Rev B)

The Rev B board was built from KiCad's netlist with these scripts (KiCad 10.0.5 Python + kicad-cli,
Freerouting 2.4.1 on Java 25). They document how every placement, pour, hand-routed net and rule came about.

| Step | Script |
|---|---|
| Placement (floor plan, parts at their pins) | `placement.py`, `pcb_build.py`, `place_check.py` |
| Project file: schematic settings + board settings + net classes (HV) | `pro_merge.py` |
| Power pours, GND planes, Kelvin keep-outs, fan-out rule areas | `power.py` |
| Hand routing: DRV8323 gate drive and fan-outs, Kelvin taps, local links, GND vias | `prep_route.py` |
| Freerouting input (pours as keepouts, complete nets reduced) / session import | `dsn_prep.py`, `ses_import.py` |
| Post-route: widths, L3 GND fill + stitching, stackup, silk, board info | `fix_widths.py`, `finish_copper.py`, `stackup.py`, `silk.py`, `board_info.py` |
| Last connections (grid router with exact clearances), cleanup, 45° mitering | `maze_*.py`, `dangling.py`, `stub_clean.py`, `miter.py`, `angle_check.py` |
| Pipelines | `pipeline.sh` (build → pre-route → DRC), `post.sh`, `finish.sh` |

Paths inside the scripts point to the session working folder and the local KiCad/library install; adjust
them before re-running. Every result was verified with `kicad-cli pcb drc --schematic-parity`.
