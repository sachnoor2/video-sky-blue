# Standing rules — video production

Rules Rahul has set for this agent. They override the skill's defaults wherever the two disagree.
They live here rather than in a conversation because the repo is the durable state: a fresh
session reads this file first, and the chat history can be thrown away.

## 1. Template failures

If `sachnoor2/video-3d-template` cannot be reached:

- Do **not** start a from-scratch build of the video.
- Rebuild or repair the template repo first.
- Say so plainly, and remind Rahul to review the template before anything is made with it.

Never delete or rename the template repo.

## 2. Failed renders — narrow fix before full rebuild

Order of work when a render fails:

1. **Read the log first, cheaply.** `gh run view <id> --log-failed` filtered through
   `rg -i "error|traceback|FAILED|missing" | tail -30`. Never pull the whole run log into
   context — a four-shard log is tens of thousands of tokens and the cause is three lines in it.
2. **Classify the cause, then scope the fix to it:**
   - *Missing frames* (runner eviction, OOM, a shard dying mid-range) — refill only the gaps.
     `stitch.py --verify-only` prints the missing indices and exits 2; `render_shard.py --start N
     --end M` renders an arbitrary range.
   - *Content defect* (clipped text, wrong asset, scene bug) — re-render that shot's whole frame
     range, not just the failed frames.
   - *Upstream* (voice, manifest, typecheck) — nothing downstream is valid; do the full pass. A
     subset re-render is meaningless here.
3. **Cap it at two narrow attempts.** If the second re-render fails the same way, rebuild the whole
   thing. Chasing a stubborn narrow fix across five loops is how a one-rupee video becomes a
   four-rupee one.
4. **The stitch and the QA gate always run over the whole assembled file**, join checks included.
   Never QA only the repaired part. The seam between a patched chunk and an original one is the one
   place this approach can quietly break the video.

## 3. Cost discipline

Target: model tokens of roughly ₹1.50 or less per video (Sarvam 105B rates, ₹15 in / ₹5 cached /
₹60 out). That is about 100–150k input tokens — a 10-turn session at 15k average context.

- **One session per video.** The repo carries the state (`brief.json`, `narration.json`,
  `shotlist.json`), so any session can be abandoned at any point without losing work.
- **Ten turns or fewer**, average context under ~15k tokens. Turn count is the variable that moves
  the bill most: 3 turns ≈ ₹0.56, 10 turns ≈ ₹1.77, 40 turns ≈ ₹16.
- **Never let a large tool result into context.** `--log-failed` + `rg`, `jq -c`, `tail`,
  `ffprobe -show_entries`, and `run_program` that prints only its conclusion.
- **Deterministic checks belong in scripts, not in the model's judgement.** `qa.py` asserts the
  thresholds (duration drift, −22 to −14 dB mean, max ≤ −1 dB, missing frames, seams) and prints a
  one-line verdict plus a compact block. The model reads the verdict, not the log.

## 4. Render determinism (open item)

Pin the Cycles seed in `scenes/render.py`. A partial re-render that does not match its neighbours
leaves a visible seam, which is worse than a full re-render. This has not yet been verified in the
template.
