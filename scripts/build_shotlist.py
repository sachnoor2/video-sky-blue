#!/usr/bin/env python3
"""Turn the measured manifest plus the shot plan into shotlist.json with absolute frames.

    python3 scripts/build_shotlist.py --manifest src/manifest.json --plan shotplan.json --out shotlist.json

The manifest is the only source of truth for length: scene length is measured from the rendered
narration, never typed. One shot per narration scene, so the frame chain has no gaps by construction.
"""
import argparse
import json
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="src/manifest.json")
    ap.add_argument("--plan", default="shotplan.json")
    ap.add_argument("--out", default="shotlist.json")
    ap.add_argument("--brief", default="brief.json")
    a = ap.parse_args()

    m = json.load(open(a.manifest, encoding="utf-8"))
    brief = json.load(open(a.brief, encoding="utf-8"))
    plan = {p["id"]: p for p in json.load(open(a.plan, encoding="utf-8"))["shots"]}

    scenes = m["scenes"]
    missing = [s["id"] for s in scenes if s["id"] not in plan]
    if missing:
        sys.exit(f"no shot plan for: {', '.join(missing)}")
    extra = [i for i in plan if i not in {s["id"] for s in scenes}]
    if extra:
        sys.exit(f"shot plan has ids the narration does not: {', '.join(extra)}")

    shots, at = [], 0
    for sc in scenes:
        p = plan[sc["id"]]
        frames = int(sc["frames"])
        if frames <= 0:
            sys.exit(f"{sc['id']}: zero frames in the manifest")
        shots.append({
            "id": sc["id"],
            "start": at,
            "end": at + frames - 1,
            "camera": p["camera"],
            "set": p["set"],
            "sim": p["sim"],
            "character": p.get("character", "none"),
            "stateIn": p.get("stateIn", ""),
            "stateOut": p.get("stateOut", ""),
            "motion": p.get("motion", []),
            "samples": int(p.get("samples", 24)),
        })
        at += frames

    if at != int(m["totalFrames"]):
        sys.exit(f"chain covers {at} frames, manifest says {m['totalFrames']}")

    # the ledger has to be a chain: every stateOut is the next stateIn
    for a_, b_ in zip(shots, shots[1:]):
        if a_["stateOut"] and b_["stateIn"] and a_["stateOut"] != b_["stateIn"]:
            print(f"note: {a_['id']} -> {b_['id']} states differ (allowed, but check the cut)")

    sets = []
    for s in shots:
        if s["set"] not in sets:
            sets.append(s["set"])

    out = {
        "fps": int(m["fps"]),
        "width": int(brief.get("width", 720)),
        "height": int(brief.get("height", 1280)),
        "world": "scenes/world.blend",
        "totalFrames": at,
        "sets": sets,
        "shots": shots,
    }
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    cams = sorted({s["camera"] for s in shots})
    sims = sorted({s["sim"] for s in shots})
    print(f"{len(shots)} shots, {at} frames = {at / out['fps']:.2f}s")
    print(f"sets: {', '.join(sets)}")
    print(f"cameras: {', '.join(cams)}")
    print(f"sims: {', '.join(sims)}")


if __name__ == "__main__":
    main()
