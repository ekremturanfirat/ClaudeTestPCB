# PCB Rev B — work in progress (saved 2026-09-28)

Not committed to git. Copy of the session working folder, so nothing is lost if Temp is cleaned.

## State
- 4-layer board (user-approved): L1 signal, L2 solid GND, L3 signal, L4 signal + GND fill. 100 x 90 mm.
- `pcbwork/ESC3Phase.kicad_pcb` = pre-routed board (placement, pours, hand-routed DRV8323 gate drive,
  fan-outs, GND vias). kicad-cli DRC: 0 violations, 0 parity issues, 113 connections left for Freerouting.
- Best routing so far: `route/esc7.ses` -> 2 unconnected, 20 errors (mostly GND pads seen as netless by
  the router). Fix already made in `scripts/dsn_prep.py` (GND keeps all pins; true 0.6 mm HV spacing);
  the rerun (`route/esc8.ses`) was stopped before it finished.
- Library changes for PR odtu/PowerLabKiCadLibraries#3 (not committed/pushed): `library_changes/`
  (0.05 mm mask margin on 48-VQFN + TPS16890 LQFN, ESP32 EP via pads 0.6 mm, new METUPowerLab_Graphics
  logo + QR, ESP32 STEP). Installed copies are already in Documents/KiCad/10.0/3rdparty.

## Next steps
1. `scripts/pipeline.sh` (rebuild pre-routed board) -> `dsn_prep.py <board> route/esc.dsn` ->
   Freerouting 2.4.1 (Java 25, headless: `-de route/esc.dsn -do route/esc8.ses -mp 25 -mt 6`) ->
   `scripts/post.sh route/esc8.ses` (import, widths, L3 GND + stitching, stackup, silk, DRC).
2. Fix remaining DRC errors to 0, board info (`board_info.py`: logo, QR, text, connector labels), 3D check,
   fab outputs, docs, then ask before commit/push.
Scripts expect to run from the session scratchpad layout (paths relative to the script folder).
