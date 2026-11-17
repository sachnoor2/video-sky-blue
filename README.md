# video-3d-template

The master template for every 3D video. **Clone it, edit a handful of files, never delete it.**

```bash
gh repo clone sachnoor2/video-3d-template video-<slug>
```

## The one rule that matters

**One world, one film.** Every shot renders from a single `scenes/world.blend` — geometry, lights,
materials and the camera set built once — and `shotlist.json` names a **camera**, never a scene file.
One scene file per shot is how you get a slideshow of pretty frames that have nothing to do with each
other.

## Edit per video (and nothing else)

| File | What changes |
|---|---|
| `brief.json` | title, genre, language, length, palette - the decisions |
| `world.json` | the continuity bible: palette, lenses, light, character, props |
| `narration.json` | one scene per shot: `text` (Devanagari, spoken) + `caption` (Roman Hinglish, burned in) |
| `shotlist.json` | absolute frame ranges, **camera name**, `stateIn`/`stateOut`, motion per shot |
| `scenes/world.blend` | the set, the props, the lights, the cameras - one file |
| `src/theme.ts` | palette + fonts for the genre preset |
| `src/scenes.tsx` | only the 2D scene components that actually changed |

## Never touch

`package.json`, `tsconfig.json`, `remotion.config.ts`, `src/Video.tsx`, `src/Root.tsx`,
`src/manifest.ts`, `src/components/Bits.tsx`, `scripts/*`, `.github/workflows/*`.
Those are the parts that already work. If one genuinely must change, change it here in the template,
with a commit message saying why.

## The state ledger

Every shot declares what is true before it and after it:

```json
{"id": "03-mechanism", "camera": "cam-action",
 "stateIn": "section opened, air cavity visible",
 "stateOut": "blocks compressing, load path shown"}
```

Two rules, both checkable:

1. `stateOut` must differ from `stateIn` - a shot where nothing changes is a still with a camera move.
2. `stateOut(N)` must equal `stateIn(N+1)` - the chain has no gaps.

If you cannot write the chain, the film has no plot yet. Write the chain before the render.

## Cameras are a grammar

Three to five cameras for the whole film, reused: `cam-wide` (geography), `cam-action` (the subject
doing the thing), `cam-macro` (the detail that proves it), `cam-pov` (the character's eyes). One lens
family, one height band. Inventing a new angle per shot is exactly what makes frames feel unrelated -
every new angle is a new place.

## Waking the agent — two paths, one delivery

Both are armed at dispatch. Whichever fires first does the work; the other stands down.

**Fast path — `.github/workflows/notify.yml`.** Fires on `workflow_run: [completed]` for `render` and
`smoke` (success, failure or cancellation). Commits `STATUS.json`, then POSTs it to `AGENT_WEBHOOK_URL`
with five retries and backoff. `continue-on-error`, so a dead endpoint never hides the run's own result.

**Guarantee — the six-hour timer.** At dispatch + 6 h 10 min the run cannot still be going, so the outcome
exists. The agent reads the status then, delivers if resolved, and deletes the timer. If it is still
unresolved it re-checks every ten minutes, silently, up to twelve times, then stops and says so.

**One delivery only.** The first resolved wake writes `delivered: run <id>` into `PROGRESS.md` and deletes
the timer before anything else. Any later wake sees the marker, replies with nothing and deletes itself.

Set the secret once per repository (never commit the URL):

```bash
gh secret set AGENT_WEBHOOK_URL --repo sachnoor2/video-3d-template --body "https://..."
```

## Pipeline

1. `scripts/hinglish_voice.py` - Piper + warm chain -> `public/audio/*.wav` + `src/manifest.json`
2. `scripts/plan_shards.py` - measured seconds/frame -> shards -> matrix JSON
3. `scripts/render_shard.py` -> `scenes/render.py` - Blender, Cycles CPU, one world, one camera per shot
4. `scripts/stitch.py` - verify every frame index 0..N-1 exactly once, then assemble
5. `scripts/qa.py` - ffprobe, blackdetect, silencedetect, contact sheet

`smoke.yml` proves the pipeline end to end on a synthetic world (three cameras, a spinning cube) before
any art exists. Run it first.

720p (720x1280 vertical) unless the brief says otherwise. English only when asked; Hinglish is the
default, voiced by Piper `hi_IN-pratham-medium` through the chain in `scripts/hinglish_voice.py`.
