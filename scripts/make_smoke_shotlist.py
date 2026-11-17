#!/usr/bin/env python3
"""Write a one-shot shotlist that covers the whole manifest, for a smoke test."""
import json

m = json.load(open("src/manifest.json"))
total = m["totalFrames"]
json.dump({
    "fps": m["fps"], "width": 720, "height": 1280, "totalFrames": total,
    "world": "scenes/world.blend",
    "shots": [{"id": "01-hook", "start": 0, "end": total - 1, "camera": "cam-action",
               "stateIn": "cube at rest", "stateOut": "cube spinning, camera pushed in",
               "motion": ["cube rotation", "camera dolly"], "samples": 8}],
}, open("shotlist.json", "w"), indent=2)
print(f"smoke shotlist: 1 shot, 0-{total - 1}, cam-action")
