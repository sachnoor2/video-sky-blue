# Progress

Resume file. A fresh session reads this instead of replaying history.

- [x] brief.json decided — "Aasman Neela Kyun Hai?", Rayleigh scattering, Hinglish, 720x1280
- [x] narration.json written (Devanagari text + Roman captions), 13 scenes
- [x] shotplan.json written: 13 shots, 3 sets, 4 cameras, 4 simulation types
- [x] scenes/make_world.py written: one world file, three sets, all motion keyed from the shot list
- [x] scripts/build_shotlist.py added: the shot list is derived from the measured manifest at render time
- [x] typecheck passes (tsc --noEmit)
- [ ] benchmark run, seconds per frame recorded
- [ ] render dispatched
- [ ] stitch verified
- [ ] QA passed
- [ ] delivered

## Decisions

- **Topic.** Why the sky is blue: I ∝ 1/λ⁴, so blue at 450 nm scatters ≈ 5.9× more than red at 700 nm
  (700/450)^4 = 5.86. At sunset the beam crosses ≈ 38× more air, blue is scattered out, red survives.
  Above the air there is nothing to scatter, so space is black. Mechanism, number, consequence.
- **Why the shot list is generated, not committed.** Scene length comes from measured audio, so a
  hard-coded frame range would not match the narration. `scripts/build_shotlist.py` runs in the `plan`
  job on the measured `src/manifest.json` and writes `shotlist.json`; the committed one is an estimate
  and is overwritten by CI.
- **Why render.yml changed.** Three additions: the `plan` job builds the shot list, every render job
  builds `scenes/world.blend` from `scenes/make_world.py` before rendering (the world is generated, not
  a binary in git), and a `stills` job renders one frame per shot at 12 samples for a cheap visual check.
  The template's original flow assumed a committed world file and a committed shot list.
- **Sky colour change without animating ramp elements.** Two domes at 119.2 and 120 units cross-fade on
  a Mix Shader's Fac, which is a plain animatable socket. Day sky and sunset sky are separate materials.
- **16 samples**, Cycles CPU, seed pinned to 0 so a partial re-render matches its neighbours.

## Pass 2 — after looking at the stills

The first run's `stills` artifact was rendered and read frame by frame. What it showed:

- the opening and the closing sky shots work: person in silhouette, blue gradient, sun disc;
- the beam set was unusable: the shaft and molecule blew out to a white blob, and the 5.9x / 1x bars
  and labels sat off the bottom-left of the frame;
- the sunset macro put the camera so close the figure filled the frame;
- the orbit set had the Earth so large and close it read as a grey floor, and shot 12 was an empty
  grey frame.

Fixes in this pass: every emission strength halved or better (Standard view transform clips above 1.0),
molecules from 0.30 to 0.085 radius so they read as specks and not soap bubbles, the beam set rebuilt
around a 0.18-radius shaft with the bars brought inside a 32 mm frame, the sunset macro pulled back to
40 mm, and the orbit set rebuilt with a 6-unit Earth seen from 28 units so the limb curves.

Rendering now goes to a Lightning AI Studio when `LIGHTNING_AI_API_KEY` is set on this repository
(`scripts/render_on_lightning.py`); the runner-sharded Cycles path stays as the fallback.
