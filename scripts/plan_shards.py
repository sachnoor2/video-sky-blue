#!/usr/bin/env python3
"""Turn a measured seconds-per-frame into a shard plan. Never guess a shard size."""
import argparse, json, pathlib

SHARD_MINUTES = 60.0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shotlist", default="shotlist.json")
    ap.add_argument("--seconds-per-frame", type=float, required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    shots = json.load(open(a.shotlist))["shots"]
    total = sum(s["end"] - s["start"] + 1 for s in shots)
    size = max(1, int(SHARD_MINUTES * 60.0 / max(a.seconds_per_frame, 1e-6)))
    shards = []
    for i in range(0, total, size):
        shards.append({"index": len(shards) + 1, "start": i, "end": min(i + size, total) - 1})
    pathlib.Path("shards.json").write_text(json.dumps(
        {"secondsPerFrame": a.seconds_per_frame, "totalFrames": total,
         "shardFrames": size, "shards": shards}, indent=2))
    if a.json:
        print(json.dumps(shards))
    else:
        print(f"total {total} frames at {a.seconds_per_frame:.2f}s/frame -> {len(shards)} shards of {size}")

if __name__ == "__main__":
    main()
