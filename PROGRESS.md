# Progress

Resume file. A fresh session reads this instead of replaying history.

**Film: "Time Aapke Pairon Mein Dheere Chalta Hai"** — gravitational time dilation, Hinglish,
720x1280, 18 shots, 2712 frames = 90.4 s measured.

- [x] brief.json — payload: 1.1e-16 per metre, 470 ns head-to-feet over 80 years, 1 mm measured at
      JILA (Nature 2022), GPS 38 microseconds a day = 10 km of drift a day
- [x] narration.json — 18 scenes, Devanagari text + Roman captions
- [x] shotplan.json — 18 shots with cameraIn/cameraOut hand-offs
- [x] voice generated locally with Piper hi_IN-pratham-medium through the chain; manifest measured
- [x] shotlist.json derived from the measured manifest
- [x] scenes/make_world.py — three sets, six cameras, continuous carry
- [ ] stills pass looked at
- [ ] render dispatched
- [ ] stitch verified, QA passed
- [ ] delivered

## Decisions

- **The move.** One camera never resets: base of the tower (eye level, tilting up) → up the wall
  past the pendulum → the two clock faces at different heights → into the gap between them → the
  millimetre set where the two atoms sit a hair apart → out to the GPS constellation → the drifting
  fix on the ground → back to the tower. Every shot's `cameraIn` equals the previous shot's
  `cameraOut`; the CAMS table in `scenes/make_world.py` encodes those positions literally, so shots
  03→04→05→06→07 share a continuous path.
- **One hard stop**, on the twist (14-twist), and nowhere else.
- **Two clocks, one tower.** The lower face ticks at rate r, the upper at 1.15–1.4 r, so the drift is
  visible in a single frame rather than explained.
- **This repository** is the workbench for this film; the name still says sky-blue from the previous
  one. It holds `LIGHTNING_AI_API_KEY`, so renders run on a Lightning Studio.
- The private `video-3d-template` cannot run workflows at all — a job dispatched there dies with zero
  steps. Everything runs from this public repo.
