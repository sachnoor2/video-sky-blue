#!/usr/bin/env python3
"""Map a global frame range onto the shots it overlaps, clipped to that range."""
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument("--start", type=int, required=True)
ap.add_argument("--end", type=int, required=True)
ap.add_argument("--shotlist", default="shotlist.json")
a = ap.parse_args()

shots = json.load(open(a.shotlist))["shots"]
out = []
for s in shots:
    lo, hi = max(s["start"], a.start), min(s["end"], a.end)
    if lo <= hi:
        out.append({**s, "start": lo, "end": hi})
print(json.dumps({"shots": out}, indent=2))
