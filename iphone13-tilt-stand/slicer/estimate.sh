#!/usr/bin/env bash
# Usage: slicer/estimate.sh <config.ini> <outdir> stl...
# Slices each STL with PrusaSlicer CLI and prints time / filament.
cfg=$1; out=$2; shift 2; mkdir -p "$out"
for f in "$@"; do
  n=$(basename "$f" .stl)
  prusa-slicer --export-gcode --load "$cfg" --center 75,75 --dont-arrange -o "$out/$n.gcode" "$f" >/dev/null 2>"$out/$n.log" || { echo "$n FAILED"; tail -3 "$out/$n.log"; continue; }
  t=$(grep -m1 "estimated printing time (normal mode)" "$out/$n.gcode" | sed 's/.*= //')
  g=$(grep -m1 "^; filament used \[g\]" "$out/$n.gcode" | sed 's/.*= //')
  m=$(grep -m1 "^; filament used \[mm\]" "$out/$n.gcode" | sed 's/.*= //')
  printf "%-12s %10s  %6s g  %8s mm\n" "$n" "$t" "$g" "$m"
done
