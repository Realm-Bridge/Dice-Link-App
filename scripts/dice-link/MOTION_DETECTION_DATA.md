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

---

# Motion Detection Data — Session 2026-06-20

## What was tested

10 dice requests per die type: d20, d12, d10, d8, d6, d4 (60 roll IDs total).
Tested using the False Trigger and Missed Roll buttons (see "Diagnostic buttons" section below).
No per-frame logging this session — data collected was event-level only (motion_data.csv).

Full per-frame log archived in: `logs/dla_archive.log` (session starting 2026-06-20)

---

## Results

**Genuine missed rolls: 0**
Every roll_id from 1–60 produced at least one STILL_TO_ROLLING → ROLLING_TO_STILL pair.

**Genuine false triggers: 0**
No USER_REPORT_FALSE events recorded in the entire session.

**USER_REPORT_MISSED recorded: 1 (roll_id 15, 1d12) — confirmed user error**
The log shows roll_id 15 had already fired four separate detection pairs before the button
was pressed (flow_max values: 13.5, 30.6, 5.8, 41.4), and a fifth fired at flow_max 70.6
immediately after. The system was detecting correctly throughout. The user rolled before
the dice request was live, so there was no roll session to receive the result.

---

## Flow_max values observed

| die  | roll_id range | lowest flow_max trigger | highest flow_max trigger |
|------|---------------|------------------------|--------------------------|
| d20  | 1–10          | 17.5                   | 107.5                    |
| d12  | 11–20         | 6.4                    | 99.7                     |
| d10  | 21–30         | 9.6                    | 100.4                    |
| d8   | 31–40         | 5.5 (pick-up motion)   | 79.8                     |
| d6   | 41–50         | 6.2                    | 133.0                    |
| d4   | 51–60         | 8.0                    | 79.3                     |

Lowest triggering flow_max across all sessions: **5.48** (roll_id 36, 1d8, 11:31:18).
This was a pick-up motion — the actual throw for the same roll_id triggered at 69.2.
The 5.0 threshold held: no false fire, 2.1× headroom below the lowest real trigger.

---

## Double-trigger pattern

Most roll_ids logged two STILL_TO_ROLLING → ROLLING_TO_STILL pairs per dice request:
- First trigger: lower flow_max, short duration — typically the die being picked up or
  the hand moving into frame.
- Second trigger: higher flow_max — the actual throw.

Both are above the 5.0 threshold and both correctly resolve to ROLLING_TO_STILL.
Roll_id 30 (d10) logged four triggers in quick succession after an energetic throw.
This is benign for now; worth revisiting when actual dice-reading is wired up to ensure
only the final settled position is read.

---

## Conclusion

`flow_max > 5.0` is confirmed reliable across all six standard die types.
Detection rate: 100% over 60 labelled rolls.
The diagnostic buttons were retired after this session (see below).

---

# Diagnostic buttons — implementation record

Removed 2026-06-20 after the 60-roll confirmation test. Documented here in full so
they can be recreated for future testing rounds if needed.

## What they were

Two large buttons in the DLA camera panel used to label detection events in real time:
- **False Trigger** (dark red) — pressed when the system fired but no roll had occurred.
- **Missed Roll** (dark blue) — pressed when a real roll was not detected.

Each button POST'd to a server endpoint which wrote a labelled row to motion_data.csv
carrying the current roll_id and die formula so the report could be matched back to
the surrounding STILL_TO_ROLLING / ROLLING_TO_STILL rows.

## HTML — `templates/index.html`

Sat inside the `bottom-right-top` div, above the camera feed panel, as a flex column:

```html
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;flex:1;padding:12px;">
    <button id="camera-false-trigger-btn" style="background:#8b0000;color:#fff;font-size:1.1em;padding:16px 24px;border:none;border-radius:6px;cursor:pointer;">False Trigger</button>
    <button id="camera-missed-roll-btn" style="background:#00008b;color:#fff;font-size:1.1em;padding:16px 24px;border:none;border-radius:6px;cursor:pointer;">Missed Roll</button>
</div>
```

## JS — `static/js/ui/camera.js` (inside `initCameraUI()`)

```js
const falseTriggerBtn = document.getElementById('camera-false-trigger-btn');
if (falseTriggerBtn) {
    falseTriggerBtn.addEventListener('click', () => {
        fetch('/api/camera/false-trigger', { method: 'POST' });
    });
}

const missedRollBtn = document.getElementById('camera-missed-roll-btn');
if (missedRollBtn) {
    missedRollBtn.addEventListener('click', () => {
        fetch('/api/camera/missed-roll', { method: 'POST' });
    });
}
```

## Server — `server.py`

```python
@app.post("/api/camera/false-trigger")
async def camera_false_trigger():
    log_camera_motion(
        f"USER REPORT: false trigger  roll_id={camera_manager.current_roll_id} die={camera_manager.current_die}"
    )
    log_motion_data_event(
        "USER_REPORT_FALSE", camera_manager.current_roll_id, camera_manager.current_die
    )
    return JSONResponse({"success": True})


@app.post("/api/camera/missed-roll")
async def camera_missed_roll():
    log_camera_motion(
        f"USER REPORT: missed roll  roll_id={camera_manager.current_roll_id} die={camera_manager.current_die}"
    )
    log_motion_data_event(
        "USER_REPORT_MISSED", camera_manager.current_roll_id, camera_manager.current_die
    )
    return JSONResponse({"success": True})
```

## debug.py

No changes needed. `log_motion_data_event()` in `debug.py` writes all event types
generically — pass `"USER_REPORT_FALSE"` or `"USER_REPORT_MISSED"` as the event
string with roll_id and die; the function writes the row with flow stats left blank.
The CSV header and format are unchanged.
