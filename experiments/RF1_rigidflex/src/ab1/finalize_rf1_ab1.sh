#!/bin/bash
# RF1 phase 3: export a routed RF1 AB1 layout to KiCad (the baseline exporter, run on the RF1 generator copies) and run KiCad's DRC and the repo's independent DRC.
# usage (repo root): experiments/RF1_rigidflex/src/ab1/finalize_rf1_ab1.sh BOARD SCRATCH_DIR "RF1_PUT" ; SCRATCH_DIR holds late.json and out_board/AB1<B>_layout.json
set -e
B=$1; SRC=$(cd "$2" && pwd); P=$3; ROOT=$(pwd); EXP=$ROOT/experiments/RF1_rigidflex; F=$EXP/build_ab1/final_$B
mkdir -p $F/out_board; cp $SRC/out_board/AB1${B}_layout.json $F/out_board/; cp $SRC/late.json $F/
LATE=$(python3 -c "import json; print(json.load(open('$F/late.json'))['late'])")
cd $F
BOARD=$B RF1_J2=15.6,0.0,90 RF1_PUT="$P" RF1_LATE="$LATE" PYTHONPATH=$EXP/src/ab1:$ROOT/work python3 $EXP/src/ab1/afe_export.py > export.log 2>&1 || { tail -5 export.log; exit 1; }
cd $ROOT
python3 src/pcb/kicad_drc.py $F/kit_v3/PCB_AB1$B/PF233-AB1$B.kicad_pcb $F/kicad_drc.json AB1$B | head -c 300; echo
python3 src/pcb/indep_drc.py AB1$B $F/kit_v3/PCB_AB1$B/PF233-AB1$B.kicad_pcb $F/indep_drc.json | tail -2
