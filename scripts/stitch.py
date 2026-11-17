#!/usr/bin/env python3
"""Verify the frame sequence before anything encodes, then assemble.

Exit 0 clean, 2 frames missing or duplicated (and names them), 3 assembly failed.
"""
import argparse, json, os, pathlib, subprocess, sys

def verify(frames_dir, total):
    seen = {}
    for p in pathlib.Path(frames_dir).glob("frame_*.png"):
        idx = int(p.stem.split("_")[1])
        seen[idx] = seen.get(idx, 0) + 1
    missing = [i for i in range(total) if seen.get(i, 0) == 0]
    dupes = [i for i, c in seen.items() if c > 1]
    if missing or dupes:
        print(f"FAIL: {len(missing)} missing, {len(dupes)} duplicated")
        if missing:
            print("  missing:", missing[:20])
        if dupes:
            print("  duplicated:", dupes[:20])
        return 2
    print(f"OK: all {total} frames present exactly once")
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="public/out")
    ap.add_argument("--manifest", default="src/manifest.json")
    ap.add_argument("--verify-only", action="store_true")
    a = ap.parse_args()

    rc = verify(a.frames, json.load(open(a.manifest))["totalFrames"])
    if rc or a.verify_only:
        sys.exit(rc)

    r = subprocess.run(["npx", "remotion", "render", "src/index.ts", "Video", "out/video.mp4",
                        "--concurrency=%d" % max(1, min(3, os.cpu_count() or 1)), "--log=error"], capture_output=True, text=True)
    if r.returncode != 0:
        print("assembly failed:", r.stderr[-800:])
        sys.exit(3)
    print("assembled out/video.mp4")

if __name__ == "__main__":
    main()
