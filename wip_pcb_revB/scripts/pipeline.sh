#!/bin/bash
# Full board pipeline from the netlist: place -> pours -> pre-route -> DRC (kicad-cli). Stops before autorouting.
set -eo pipefail
cd "$(dirname "$0")"
PY="/c/Program Files/KiCad/10.0/bin/python.exe"
CLI="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
B=pcbwork/ESC3Phase.kicad_pcb
"$PY" pcb_build.py esc_new/net.net $B > /dev/null
"$PY" place_check.py $B | head -1
"$PY" power.py $B
"$PY" prep_route.py $B 2>&1 | { grep -v "memory leak" || true; }
"$CLI" pcb drc --severity-error --format json -o route/drc_pre.json $B > /dev/null
python drc_sum.py route/drc_pre.json | head -${1:-12}
