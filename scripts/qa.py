#!/usr/bin/env python3
"""QA gate. Prints verdicts, not logs; the full output goes to qa.log."""
import json, pathlib, re, subprocess, sys

VIDEO = "out/video.mp4"
LOG = "qa.log"

def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    return r.stdout + r.stderr

def main():
    m = json.load(open("src/manifest.json"))
    total, fps = m["totalFrames"], m["fps"]
    expected = total / fps
    out, ok = [], True

    s = run(["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,codec_name", "-of", "default=nw=1", VIDEO])
    out.append(s)
    has_v = "codec_name=h264" in s
    has_a = "codec_type=audio" in s and "codec_name=aac" in s
    dur = float(re.search(r"duration=([0-9.]+)", s).group(1)) if re.search(r"duration=([0-9.]+)", s) else 0.0
    drift = abs(dur - expected)
    tol = max(1.0, expected * 0.02)
    out.append(f"1 streams: {'PASS' if has_v and has_a else 'FAIL'} (h264={has_v} aac={has_a})")
    out.append(f"2 duration: {'PASS' if drift < tol else 'FAIL'} ({dur:.2f}s vs {expected:.2f}s)")
    ok = ok and has_v and has_a and drift < tol

    s = run(["ffmpeg", "-hide_banner", "-i", VIDEO, "-t", "20", "-af", "volumedetect", "-f", "null", "-"])
    out.append(s)
    mv = float(re.search(r"mean_volume: (-?[0-9.]+) dB", s).group(1)) if "mean_volume" in s else -99.0
    pv = float(re.search(r"max_volume: (-?[0-9.]+) dB", s).group(1)) if "max_volume" in s else -99.0
    lvl = -22 <= mv <= -14 and pv <= -1
    out.append(f"3 audio level: {'PASS' if lvl else 'FAIL'} (mean {mv} dB, peak {pv} dB)")
    ok = ok and lvl

    s = run(["ffmpeg", "-hide_banner", "-i", VIDEO, "-vf", "blackdetect=d=0.02:pix_th=0.10",
             "-an", "-f", "null", "-"])
    out.append(s)
    blacks = s.count("black_start")
    out.append(f"4 black frames: {'PASS' if blacks == 0 else 'FAIL'} ({blacks} segments)")
    ok = ok and blacks == 0

    s = run(["ffmpeg", "-hide_banner", "-i", VIDEO, "-af", "silencedetect=n=-45dB:d=0.15",
             "-f", "null", "-"])
    out.append(s)
    out.append(f"5 dead air: {s.count('silence_start')} silences (deliberate beats are fine)")

    pathlib.Path(LOG).write_text("\n".join(out))
    print(f"QA: {'PASS' if ok else 'FAIL'}")
    for line in out:
        if line[:1].isdigit() and len(line) < 200:
            print("  " + line)
    print(f"  full log: {LOG}")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
