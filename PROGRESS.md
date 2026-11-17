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
