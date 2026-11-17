#!/usr/bin/env python3
"""Render every shot that overlaps a global frame range, one Blender process per shot.

Every shot renders from the same world file; only the camera changes.
"""
import argparse, json, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("--start", type=int, required=True)
ap.add_argument("--end", type=int, required=True)
ap.add_argument("--shotlist", default="shotlist.json")
ap.add_argument("--out", default="public/out")
ap.add_argument("--samples", type=int, default=None)
a = ap.parse_args()

cfg = json.load(open(a.shotlist))
world = cfg.get("world", "scenes/world.blend")
shots = cfg["shots"]

todo = []
for s in shots:
    lo, hi = max(s["start"], a.start), min(s["end"], a.end)
    if lo <= hi:
        todo.append((s, lo, hi))

if not todo:
    print(f"no shots overlap {a.start}-{a.end}")
    sys.exit(0)

for s, lo, hi in todo:
    samples = a.samples if a.samples is not None else s.get("samples", 32)
    cmd = ["blender", "-b", world, "-P", "scenes/render.py", "--",
           "--camera", s["camera"], "--start", str(lo), "--end", str(hi),
           "--out", a.out, "--samples", str(samples)]
    print(" ".join(cmd), flush=True)
    if subprocess.run(cmd).returncode != 0:
        print(f"FAILED shot {s['id']} ({s['camera']}) frames {lo}-{hi}")
        sys.exit(1)

print(f"rendered {len(todo)} shot(s) for {a.start}-{a.end}")
