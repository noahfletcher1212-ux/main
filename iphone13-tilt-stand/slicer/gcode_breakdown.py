"""Approximate per-feature / per-height time breakdown of a PrusaSlicer G-code file.

Uses a simple trapezoid model (accel from M204, junction speed ~ jerk); only used to
see WHERE time goes - the totals quoted in the README come from PrusaSlicer itself.
"""
import math
import re
import sys
from collections import defaultdict


def analyze(path, jerk=8.0):
    x = y = z = e = 0.0
    f = 1500.0
    acc = 500.0
    typ = "start"
    by_type = defaultdict(float)
    by_z = defaultdict(float)
    retr = 0
    for line in open(path):
        if line.startswith(";TYPE:"):
            typ = line[6:].strip()
            continue
        line = line.split(";")[0].strip()
        if not line:
            continue
        if line.startswith("M204"):
            m = re.search(r"[SP]([\d.]+)", line)
            if m:
                acc = float(m.group(1))
            continue
        if not (line.startswith("G1") or line.startswith("G0")):
            continue
        p = {k: float(v) for k, v in re.findall(r"([XYZEF])([-\d.]+)", line)}
        if "F" in p:
            f = p["F"]
        nx, ny, nz, ne = p.get("X", x), p.get("Y", y), p.get("Z", z), p.get("E", e)
        d = math.dist((x, y, z), (nx, ny, nz))
        v = f / 60.0
        if d < 1e-6:
            de = abs(ne - e)
            t = de / max(v, 1e-6)
            if de > 0.5:
                retr += 1
            key = "retract"
        else:
            a = max(acc, 1.0)
            v0 = min(jerk, v)
            ramp = (v * v - v0 * v0) / a          # accel + decel distance
            t = d / v + (v - v0) ** 2 / (a * v) if d > ramp else 2 * (math.sqrt(v0 * v0 + a * d) - v0) / a
            key = typ if ("E" in p and ne > e) else "travel"
        by_type[key] += t
        by_z[round(nz // 5 * 5)] += t
        x, y, z, e = nx, ny, nz, ne
    return by_type, by_z, retr


if __name__ == "__main__":
    for path in sys.argv[1:]:
        bt, bz, retr = analyze(path)
        tot = sum(bt.values())
        print(f"== {path}: model total {tot/60:.0f} min, retractions {retr}")
        for k, v in sorted(bt.items(), key=lambda kv: -kv[1]):
            print(f"   {k:28s} {v/60:6.1f} min")
        print("   by Z band (mm): " + ", ".join(f"{k}:{v/60:.0f}" for k, v in sorted(bz.items())))
