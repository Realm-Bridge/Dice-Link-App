# Dice Isolation Research — Post-MVP Feature

## Goal
Remove the tray background from the camera feed so only the dice appear floating on the Foundry canvas — similar to how Dice So Nice works but with real physical dice.

## Why It Was Deferred
Getting a clean, reliable dice-only image is significantly more complex than anticipated due to the combination of variable user tray colours, phone camera EIS, dynamic resolution changes, and the fundamental conflict between excluding tray walls (which cuts off edge dice) and including them (which bleeds wall colour through). Accepted as a post-MVP aspiration.

---

## What We Tried

### Approach 1 — Baseline Diff (Original)
**How it works:** Capture an empty tray frame as a reference. For each streaming frame, subtract the reference and threshold the difference. Areas that changed (dice) are kept; areas that didn't (tray) are made transparent.

**What worked:** Concept is sound. Dice were detectable.

**What failed:**
- Phone camera EIS (electronic image stabilisation) causes the entire frame to shift slightly between frames, making the whole image look like it changed. This flooded the diff mask and made the entire tray appear as foreground.
- When calibration frame resolution differed from streaming frame resolution, resizing the baseline introduced interpolation artefacts that again flooded the mask.
- Convex hull was used to fill detected dice shapes — this filled in concavities (pip gaps, face edges) causing felt colour to bleed in around dice edges.

**Verdict:** Unreliable with phone cameras due to EIS. Resolution mismatch is a hard problem.

---

### Approach 2 — Hybrid Chroma Key + Baseline Diff
**How it works:** Primary method keys out pixels matching the tray colour in HSV space. Baseline diff used as fallback to catch dice whose colour closely matches the tray.

**What worked:** The concept of combining both methods is correct.

**What failed:**
- Initial implementation keyed on all three HSV channels (hue, saturation, value). Including value was wrong — shadows and highlights on the felt share the same hue but different brightness, so dark/bright tray areas were not keyed out and bled through.
- Fixed range offsets (±15 hue, ±40 sat, ±40 val) were arbitrary and did not reflect actual tray variation.
- Baseline diff fallback continued to cause flooding from EIS movement.
- Convex hull still in use at this stage — same edge bleed problem.

**Verdict:** Correct direction but wrong implementation details.

---

### Approach 3 — Chroma Key Only, Percentile Bounds, Raw Contour Fill
**How it works:** Key on hue and saturation only (value ignored, per standard chroma key practice). Bounds calculated from 5th/95th percentile of actual tray pixel distribution at calibration — no guessing at ranges. Baseline diff disabled. Raw contour fill replaces convex hull.

**What worked:**
- Ignoring value was the correct call — removed the shadow/highlight bleed problem significantly.
- Percentile bounds from actual pixel data better than fixed offsets.
- Convex hull removal improved edge quality.
- Tray background largely removed successfully.

**What failed:**
- Calibration timing: phone camera auto-exposure was still adjusting at the moment of calibration, capturing a bad frame with wildly wrong colours (hue 23–179 instead of 174–176). The 30-second re-sampler corrected this but the damage was done for that session.
- Dice not fully appearing: some dice colours overlap with the felt hue/saturation range and are partially keyed out as background.
- Tray walls: if polygon excludes walls (to avoid wall colour bleed), dice that roll up against the wall are cut off. If polygon includes walls, wall colour bleeds through. No clean solution without knowing wall colour per user.
- Some residual bleed-through at the edges of rolling dice — sub-pixel accuracy limit of the approach.
- Image still not crisp enough for MVP — too many variables affecting quality across different user setups.

**Verdict:** Best results achieved so far but not good enough for MVP. The wall/boundary conflict is the fundamental unsolved problem.

---

## Root Causes of the Core Problem

1. **EIS and resolution instability** — Phone cameras dynamically change resolution and apply image stabilisation, making frame-to-frame comparison unreliable.

2. **Calibration timing** — A single frame captured at the wrong moment (auto-exposure adjusting) gives wrong bounds. Needs multi-frame averaging or stabilisation delay.

3. **Dice colour overlap** — Users may have dice whose colour closely matches their tray felt. No keying method can distinguish these without semantic understanding (ML).

4. **Tray wall conflict** — Including walls in the polygon bleeds wall colour; excluding them cuts off edge dice. Requires either knowing the wall colour (unreliable across users) or ML-based object detection.

5. **Without ML, true dice isolation is very difficult** — The only robust solution is object detection that understands "this is a die, this is not a die" regardless of colour or position.

---

## What Would Be Needed for a Post-MVP Implementation

- **Stable calibration:** Average multiple frames (5–10) before computing bounds, ensuring auto-exposure has settled. Add a warm-up delay.
- **Polygon covers full tray including walls:** Rely on chroma key to remove wall colour rather than polygon exclusion.
- **Per-region keying:** Sample felt colour and wall colour separately, key out both independently.
- **ML object detection:** The only truly robust solution. Detect dice as objects regardless of colour, position, or tray. Segment only the dice pixels. This was always the long-term plan (inference.py stub exists).
- **Feathered edges:** Soft alpha blending at contour edges to reduce hard pixel-level bleed.

---

## Current State of the Code (at time of deferral)

All chroma key and background removal code is removed for MVP. `get_processed_frame()` returns the full tray region crop — whatever is inside the defined polygon — as a clean PNG sent to the Foundry canvas. No background removal attempted.

The infrastructure that remains and will be useful for the post-MVP implementation:
- `calibrate()` — captures baseline frame, samples tray colour bounds (percentile-based HSV)
- `_sample_tray_colour()` — percentile HSV bounds from polygon pixels
- `_resample_loop()` — periodic lighting re-adaptation
- `tray_polygon` — user-defined tray boundary
- `get_processed_frame()` — pipeline to Foundry canvas (simplified for MVP)
