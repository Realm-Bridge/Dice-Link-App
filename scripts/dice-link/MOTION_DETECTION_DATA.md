# Motion Detection Data — Session 2026-06-14

## What was tested

10–11 dice requests per die type: d4, d6, d8, d10, d12, d20.
User reported events using the False Trigger and Missed Roll buttons in the camera panel.
All 15 optical-flow data points were logged per frame.

Full per-frame log archived in: `logs/dla_archive.log` (session starting 2026-06-14)

---

## Confirmed false trigger (1 event)

Die: d20 — the detection fired when it should not have.

| metric  | value  |
|---------|--------|
| mean    | 0.512  |
| std     | 0.586  |
| **max** | **2.408** |
| median  | 0.155  |
| p75     | 1.068  |
| p90     | 1.425  |
| p95     | 1.583  |
| af02    | 0.473  |
| af05    | 0.385  |
| net_x   | —      |
| net_y   | —      |
| coh     | 0.963  |
| x_std   | 0.328  |
| y_std   | 0.504  |
| agl_std | 0.326  |
| delta   | +0.113 |

---

## Confirmed missed rolls (6 events)

All 6 failed because the old trigger metric (`mean > 0.4`) never reached threshold.
Values shown are the peak frame for each missed roll.

| roll | die | mean (peak) | max (peak) | std (peak) |
|------|-----|-------------|------------|------------|
| 1    | d10 | 0.370       | 26.993     | 2.031      |
| 2    | d8  | 0.396       | 28.720     | 1.880      |
| 3+4  | d4  | 0.306       | 30.386     | 1.697      |
| 5    | d4  | 0.396       | 34.093     | 1.709      |
| 6    | d4  | 0.352       | 24.282     | 1.955      |

---

## Separation analysis — all 15 metrics

| metric   | false trigger | missed roll range    | separation        |
|----------|---------------|----------------------|-------------------|
| **max**  | **2.408**     | **24.282 – 34.093**  | **10x gap — best** |
| std      | 0.586         | 1.697 – 2.031        | clean             |
| x_std    | 0.328         | higher in real rolls | clean             |
| y_std    | 0.504         | higher in real rolls | clean             |
| agl_std  | 0.326         | higher in real rolls | clean             |
| mean     | 0.512         | 0.306 – 0.396        | **REVERSED** — false trigger is higher |
| median   | 0.155         | lower in real rolls  | reversed          |
| p75–p95  | higher        | lower in real rolls  | reversed          |
| af02/05  | 0.473 / 0.385 | lower in real rolls  | reversed          |
| coh      | 0.963         | up to 0.809          | partial overlap   |
| delta    | +0.113        | no pattern           | unusable          |

`mean` was the old trigger metric and is the **worst** discriminator — the false trigger had
a *higher* mean than every single missed roll.

`max` has zero overlap and a 10x gap. It is the correct metric to trigger on.

---

## Detection method change

**Old:** `flow_mean > 0.4`
**New:** `flow_max > 5.0`

Threshold rationale:
- 5.0 is 2.1× above the confirmed false-trigger peak (2.408)
- 5.0 is 4.9× below the lowest confirmed real-roll peak (24.282)
- Based on limited data (1 false trigger, 6 missed rolls); threshold should be revisited
  once motion_data.csv has 100+ labelled events.

Exit condition (Rolling → Still) is unchanged: `flow_mean < 0.4` sustained for 15 frames.
This was never the source of problems so was left alone.

---

## Persistent data log

All future roll events are recorded to: `logs/motion_data.csv`

Format: one CSV row per event — STILL_TO_ROLLING, ROLLING_TO_STILL,
USER_REPORT_FALSE, USER_REPORT_MISSED, SESSION_START.

Each row carries: timestamp, event, roll_id, die formula, and all 15 optical-flow values.
USER_REPORT rows carry roll_id and die so they can be matched to their trigger row.
roll_id increments once per dice request (i.e. per arm), not per trigger event.
