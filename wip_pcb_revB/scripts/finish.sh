#!/bin/bash
# From the post-route board (before_maze): maze-route the last connections, miter 90 deg corners, DRC.
set -eo pipefail
cd "$(dirname "$0")"
PY="/c/Program Files/KiCad/10.0/bin/python.exe"
CLI="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
B=pcbwork/ESC3Phase.kicad_pcb
cp route/before_maze.kicad_pcb $B
while read i net w x1 y1 l1 x2 y2 l2; do
  "$PY" maze_export.py $B "$net" $w route/maze_$i.json $x1 $y1 $l1 $x2 $y2 $l2 2>&1 | { grep -v leak || true; }
  python maze.py route/maze_$i.json route/maze_path_$i.json
  "$PY" maze_apply.py $B "$net" $w route/maze_path_$i.json 2>&1 | { grep -v leak || true; }
done < route/maze_jobs_final.txt
"$PY" dangling.py $B 2>&1 | { grep -v leak || true; }
"$PY" stub_clean.py $B 2>&1 | { grep -v leak || true; }
"$PY" miter.py $B 2>&1 | { grep -v leak || true; }
"$PY" angle_check.py $B 2>&1 | { grep -v leak || true; } | head -12
"$CLI" pcb drc --schematic-parity --refill-zones --severity-all --format json -o route/drc_final.json $B > /dev/null
python drc_sum.py route/drc_final.json | head -${1:-14}
