#!/usr/bin/env python3
"""Hinglish narration: Piper + the warm storyteller chain.

    python scripts/hinglish_voice.py --script narration.json --out public/audio

Devanagari in, English loanwords transliterated into Devanagari. Fixes the े/ै -> ॅ loanword trap,
stretches the silences so the read breathes, then applies the owner's chain:

    pitch -2 semitones by resampling (duration restored) -> rumble cut 55 Hz -> low-mid lift under
    200 Hz -> presence softened 2.4-4.2 kHz -> sibilance rolled off above 6.5 kHz -> 3:1 compression
    -> light saturation -> 13% plate -> -18 dB loudness -> 22.05 kHz mono

Durations are measured AFTER the chain, so the manifest describes what the viewer hears.
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, wave

SAMPLE_RATE = 22050
SEMITONES = -2.0
PAUSE_SENTENCE = 0.42
PAUSE_BREAK = 0.78
MUSIC_DB = -26

# Verified against espeak-ng -v hi --ipa. Whole tokens only: never inside बेटा, केसर, टेपरिकॉर्डर.
LEXICON = {
    "टेप": "टॅप", "बेस": "बॅस", "ट्रेन": "ट्रॅन", "फेस": "फॅस", "प्लेट": "प्लॅट",
    "केस": "कॅस", "सेफ": "सॅफ", "गेम": "गॅम", "स्टेटस": "स्टॅटस", "मेक": "मॅक",
    "फेमस": "फॅमस", "बेट": "बॅट", "सेल": "सॅल", "वेब": "वॅब", "स्टेप": "स्टॅप",
    "चेक": "चॅक", "प्रेस": "प्रॅस", "टेस्ट": "टॅस्ट", "बेड": "बॅड", "हेड": "हॅड",
    "रेड": "रॅड", "सेट": "सॅट", "बैग": "बॅग", "टैग": "टॅग", "फ्लैट": "फ्लॅट",
    "टैलेंट": "टॅलेंट", "कैमरा": "कॅमेरा", "मैनेजर": "मॅनेजर", "इंटरनेट": "इंटरनॅट",
}


def ffmpeg():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        sys.exit("ffmpeg not found - install it before running this script")


def fix_loanwords(text, log):
    def sub(m):
        w = m.group(0)
        f = LEXICON.get(w)
        if f and f != w:
            log.append(f"{w} -> {f}")
            return f
        return w
    return re.sub(r"[\u0900-\u097F]+", sub, text)


def split_sentences(text):
    parts, buf = [], ""
    for ch in text:
        buf += ch
        if ch in "।.!?":
            if buf.strip():
                parts.append(buf.strip())
            buf = ""
    if buf.strip():
        parts.append(buf.strip())
    return parts or [text.strip()]


def piper_speak(piper, model, text, out_wav, length_scale):
    proc = subprocess.run([piper, "--model", model, "--output_file", out_wav,
                           "--length_scale", str(length_scale)],
                          input=text.encode("utf-8"), capture_output=True)
    if proc.returncode != 0:
        sys.exit(f"piper failed: {proc.stderr.decode('utf-8', 'ignore')[:400]}")


def read_pcm(path):
    with wave.open(path, "rb") as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            sys.exit(f"{path}: expected mono 16-bit WAV from Piper")
        return w.getframerate(), w.readframes(w.getnframes())


def write_pcm(path, rate, frames):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(frames)


def silence(rate, seconds):
    return b"\x00\x00" * int(rate * seconds)


def warm_chain(in_wav, out_wav):
    semis = 2 ** (SEMITONES / 12.0)
    chain = ",".join([
        f"asetrate={SAMPLE_RATE}*{semis:.4f}",
        f"aresample={SAMPLE_RATE}",
        f"atempo={1 / semis:.4f}",
        "highpass=f=55",
        "equalizer=f=160:width_type=q:w=1.0:g=3",
        "equalizer=f=3300:width_type=q:w=1.4:g=-2.5",
        "treble=g=-3:f=6500:width_type=q:w=0.7",
        "acompressor=threshold=0.1:ratio=3:attack=10:release=200:makeup=1.5",
        "asoftclip=type=tanh:threshold=0.85",
        "aecho=0.9:0.85:41|73:0.13|0.08",
        "loudnorm=I=-18:TP=-1.5:LRA=11",
        f"aresample={SAMPLE_RATE}",
    ])
    proc = subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", in_wav,
                           "-af", chain, "-ar", str(SAMPLE_RATE), "-ac", "1", out_wav],
                          capture_output=True)
    if proc.returncode != 0:
        sys.exit(f"ffmpeg chain failed: {proc.stderr.decode('utf-8', 'ignore')[:400]}")


def make_pad(out_wav, seconds):
    src = ("aevalsrc='0.22*sin(2*PI*110*t)+0.18*sin(2*PI*130.81*t)"
           "+0.18*sin(2*PI*164.81*t)+0.10*sin(2*PI*196*t)':s=22050:d=" + f"{seconds:.2f}")
    proc = subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                           "-f", "lavfi", "-i", src,
                           "-af", f"tremolo=f=0.15:d=0.3,lowpass=f=900,volume={MUSIC_DB}dB",
                           "-ar", str(SAMPLE_RATE), "-ac", "1", out_wav], capture_output=True)
    if proc.returncode != 0:
        sys.exit(f"pad failed: {proc.stderr.decode('utf-8', 'ignore')[:400]}")


def mix_voice_music(voice, pad, out_wav):
    proc = subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                           "-i", voice, "-stream_loop", "-1", "-i", pad,
                           "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first",
                           "-ar", str(SAMPLE_RATE), "-ac", "1", out_wav], capture_output=True)
    if proc.returncode != 0:
        sys.exit(f"music mix failed: {proc.stderr.decode('utf-8', 'ignore')[:400]}")


def wav_seconds(path):
    with wave.open(path, "rb") as w:
        return w.getnframes() / float(w.getframerate())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", default="narration.json")
    ap.add_argument("--out", default="public/audio")
    ap.add_argument("--piper", default=".piper/piper/piper")
    ap.add_argument("--voice", default=".piper/hi_IN-pratham-medium.onnx")
    ap.add_argument("--manifest", default="src/manifest.json")
    ap.add_argument("--length-scale", type=float, default=None)
    ap.add_argument("--music", action="store_true")
    a = ap.parse_args()

    cfg = json.load(open(a.script, encoding="utf-8"))
    fps = int(cfg.get("fps", 30))
    pad = float(cfg.get("pad", 0.7))
    min_seconds = float(cfg.get("minSeconds", 4.0))
    length_scale = a.length_scale or float(cfg.get("lengthScale", 1.0))

    os.makedirs(a.out, exist_ok=True)
    os.makedirs(os.path.dirname(a.manifest) or ".", exist_ok=True)

    scenes, total = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for i, scene in enumerate(cfg["scenes"]):
            sid = scene["id"]
            changes = []
            text = fix_loanwords(scene["text"].strip(), changes)
            if changes:
                print(f"  {sid}: lexicon {', '.join(changes)}")
            sentences = split_sentences(text)
            rate, pcm = None, b""
            for j, sentence in enumerate(sentences):
                chunk = os.path.join(tmp, f"{i:03d}-{j}.wav")
                piper_speak(a.piper, a.voice, sentence, chunk, length_scale)
                r, data = read_pcm(chunk)
                rate = rate or r
                if r != rate:
                    sys.exit(f"{sid}: mixed sample rates ({rate} vs {r})")
                pcm += data
                pcm += silence(rate, PAUSE_BREAK if j == len(sentences) - 1 else PAUSE_SENTENCE)
            raw = os.path.join(tmp, f"{i:03d}-raw.wav")
            write_pcm(raw, rate, pcm)
            chained = os.path.join(tmp, f"{i:03d}-chain.wav")
            warm_chain(raw, chained)
            final = os.path.join(a.out, f"{sid}.wav")
            if a.music:
                pad_wav = os.path.join(tmp, f"{i:03d}-pad.wav")
                make_pad(pad_wav, wav_seconds(chained) + 1.0)
                mix_voice_music(chained, pad_wav, final)
            else:
                shutil.copyfile(chained, final)
            seconds = max(wav_seconds(final), min_seconds)
            frames = round((seconds + pad) * fps)
            scenes.append({"id": sid, "seconds": round(seconds, 3), "frames": frames,
                           "caption": scene.get("caption", ""), "lexicon": changes})
            total += frames
            print(f"{sid:24s} {seconds:6.2f}s  {frames:5d} frames")

    with open(a.manifest, "w", encoding="utf-8") as f:
        json.dump({"fps": fps, "pad": pad, "engine": "piper+warm-chain",
                   "voice": os.path.basename(a.voice), "music": bool(a.music),
                   "totalFrames": total, "scenes": scenes}, f, ensure_ascii=False, indent=2)
    print(f"\ntotal {total} frames = {total / fps:.2f}s -> {a.manifest}")


if __name__ == "__main__":
    main()
