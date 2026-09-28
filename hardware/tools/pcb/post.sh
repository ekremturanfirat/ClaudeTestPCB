#!/bin/bash
# After Freerouting: import SES -> widen necks -> L3 GND + stitching -> stackup -> silkscreen -> DRC (kicad-cli)
set -eo pipefail
cd "$(dirname "$0")"
PY="/c/Program Files/KiCad/10.0/bin/python.exe"
CLI="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
B=pcbwork/ESC3Phase.kicad_pcb
cp route/pre_routed.kicad_pcb $B
"$PY" ses_import.py $B "$1" $B 2>&1 | { grep -v leak || true; }
"$PY" fix_widths.py $B 2>&1 | { grep -v leak || true; }
"$PY" finish_copper.py $B 2>&1 | { grep -v leak || true; }
python stackup.py $B
"$PY" board_info.py $B 2>&1 | { grep -v leak || true; }
"$PY" silk.py $B 2>&1 | { grep -v leak || true; }
"$CLI" pcb drc --schematic-parity --refill-zones --severity-all --format json -o route/drc_post.json $B > /dev/null
python drc_sum.py route/drc_post.json | head -${2:-30}
