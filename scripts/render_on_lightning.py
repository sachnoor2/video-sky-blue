#!/usr/bin/env python3
"""Render a frame range on a Lightning AI Studio instead of on the runner.

    python3 scripts/render_on_lightning.py --shotlist shotlist.json --start 0 --end 2262

The GitHub runner only drives: it authenticates with LIGHTNING_API_KEY, uploads this repo to a Studio,
installs Blender there, builds the one world file, renders, and pulls the PNG sequence back. The frames
are identical to a runner render because the same world, the same camera list and the same seed go up.

Environment: LIGHTNING_API_KEY (required), LIGHTNING_USERNAME / LIGHTNING_TEAMSPACE / LIGHTNING_ORG
(optional, when the key does not imply them).
"""
import argparse
import json
import os
import sys
import tarfile
import tempfile

BLENDER_VERSION = "4.2.3"
BLENDER_URL = (f"https://download.blender.org/release/Blender{'.'.join(BLENDER_VERSION.split('.')[:2])}"
               f"/blender-{BLENDER_VERSION}-linux-x64.tar.xz")

UPLOAD = [
    "scenes", "scripts", "src", "package.json", "tsconfig.json", "remotion.config.ts",
    "shotlist.json", "shotplan.json", "narration.json", "brief.json", "world.json",
]


def pack_repo(dest):
    with tarfile.open(dest, "w:gz") as tar:
        for name in UPLOAD:
            if os.path.exists(name):
                tar.add(name)
    return os.path.getsize(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shotlist", default="shotlist.json")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--end", type=int, default=-1)
    ap.add_argument("--studio", default="sky-blue-render")
    ap.add_argument("--machine", default="CPU_X_4")
    ap.add_argument("--out", default="public/out")
    a = ap.parse_args()

    if not os.environ.get("LIGHTNING_API_KEY"):
        sys.exit("LIGHTNING_API_KEY is not set")

    from lightning_sdk import Machine, Studio

    total = int(json.load(open(a.shotlist))["totalFrames"])
    end = a.end if a.end >= 0 else total - 1
    machine = getattr(Machine, a.machine)

    with tempfile.TemporaryDirectory() as tmp:
        tar_path = os.path.join(tmp, "repo.tar.gz")
        size = pack_repo(tar_path)
        print(f"packed {size / 1e6:.1f} MB; frames {a.start}-{end} of {total}")

        studio = Studio(
            name=a.studio,
            teamspace=os.environ.get("LIGHTNING_TEAMSPACE") or None,
            org=os.environ.get("LIGHTNING_ORG") or None,
            user=os.environ.get("LIGHTNING_USERNAME") or None,
            create_ok=True,
        )
        print("studio:", studio.name)
        studio.start(machine)
        print("machine up:", a.machine)

        studio.upload_file(tar_path, "repo.tar.gz", progress_bar=False)

        # Blender from the official tarball: no root, no apt, no version drift.
        setup = (
            "set -e; "
            "mkdir -p $HOME/work && tar -xzf $HOME/repo.tar.gz -C $HOME/work; "
            f"if [ ! -x $HOME/blender/blender ]; then "
            f"curl -fsSL -o /tmp/blender.tar.xz {BLENDER_URL} && "
            "mkdir -p $HOME/blender && tar -xf /tmp/blender.tar.xz -C $HOME/blender --strip-components=1; "
            "fi; "
            "$HOME/blender/blender --version | head -2"
        )
        print(studio.run(setup)[-800:])

        print(studio.run("cd $HOME/work && $HOME/blender/blender -b -P scenes/make_world.py "
                         "-- --shotlist shotlist.json --out scenes/world.blend")[-800:])

        code, out = studio.run_with_exit_code(
            f"cd $HOME/work && python3 scripts/render_shard.py --start {a.start} --end {end}"
        )
        print(out[-3000:])
        if code != 0:
            sys.exit(f"render failed on the studio (exit {code})")

        os.makedirs(a.out, exist_ok=True)
        studio.download_folder("work/public/out", a.out)
        got = len([f for f in os.listdir(a.out) if f.startswith("frame_") and f.endswith(".png")])
        print(f"downloaded {got} frames into {a.out}")
        if got == 0:
            sys.exit("no frames came back from the studio")
        studio.stop()


if __name__ == "__main__":
    main()
