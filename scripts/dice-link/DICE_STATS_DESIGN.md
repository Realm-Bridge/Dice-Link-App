# Dice Roll Stats Panel — Design Document

Source of truth for the dice stats dashboard. Update this file as decisions are made or revised.
Last updated: 2026-05-25

---

## Panel Location

Sits inside the stats/combat tracker flip panel in `index.html`.
- Outer flipper: `#stats-panel-flipper`
- Front face (stats): `.stats-panel-face` (front)
- Content area: `.stats-content-area` — flex row containing filter column and chart column

---

## Layout Structure

```
stats-panel-face (front)
└── stats-content-area (flex row)
    ├── stats-filter-col (left, full height, 175px wide)
    │   ├── [globe icon]  [World multi-select trigger]
    │   ├── [clock icon]  [Session plain-select]
    │   ├── [user icon]   [Player multi-select trigger]
    │   └── stats-cascade-group
    │       ├── [dice icon]        [Roll Type multi-select trigger]
    │       ├── [tag icon]         [Label multi-select trigger]
    │       └── [code-branch icon] [Variant multi-select trigger] (hidden by default)
    └── stats-chart-col (right, flex: 1)
        ├── stats-controls-bar (top of right column)
        │   ├── Die picker (custom: SVG image, single-select, d20 default)
        │   ├── Chart type buttons (bar / donut / line — icon only, tooltips)
        │   ├── Stat pills: Rolls count + Average
        │   ├── Data buttons (trash / export / import — icon only, tooltips)
        │   └── Flip button (exchanges-alt icon — flips to Combat Tracker)
        ├── stats-chart-area
        │   ├── stats-chart-canvas-wrap (flex:1, position:relative)
        │   │   ├── canvas#statsChart
        │   │   └── stats-chart-expand-btn (visible only in donut mode)
        │   └── stats-donut-legend (visible only in donut mode)
        └── stats-clear-confirm (hidden by default — shown when trash clicked)
```

---

## Filter System

Filters apply cumulatively. Each level narrows what the levels below it show.

### 1. Die Type — always present
Custom die picker in the controls bar (top of chart column).
- Shows the SVG die image for the selected die + a down-arrow caret
- Single-select. Default: d20.
- Options: d4, d6, d8, d10, d12, d20, d100 (shown as SVG images from `/static/DLC Dice/`)
- Selecting a die immediately re-fetches and re-renders the chart.

> **Discrepancy from original spec:** Original design called for multiple dice selectable simultaneously ("persistent toggles, multiple can be active"). This was changed to single-select during the UI build session (2026-05-23) to fit the available space. The design document was not updated at the time. The current single-select behaviour stands unless explicitly revisited.

### 2. World / Campaign — multi-select dropdown
- Options: ALL (default) + each unique world_title from the campaigns table.
- Populated from `data.worlds` in the API response.
- Multiple worlds can be selected simultaneously.

### 3. Session Scope — single-select dropdown
Options:
- All Sessions (default)
- Last 10 Sessions
- Last 5 Sessions
- Last Session
- Current Session

### 4. Player — multi-select dropdown
- Options: ALL (default) + unique player_name values from rolls matching current filters.
- Populated from `data.players` in the API response.
- Multiple players can be selected simultaneously.

### 5. Cascade Group (Roll Type / Label / Variant)

These three dropdowns sit together in a `stats-cascade-group` div below the Player filter.
They form a cascading label grouping system. The cascade is data-driven — no categories are hardcoded.

#### Roll Type
- Multi-select dropdown. Always visible.
- Icon: dice (`fa-dice`)
- Populated automatically from roll_label data — the first level of grouping.
- Groups emerge by finding word-sequence phrases (bigrams, trigrams) that appear in 2+ labels.
  Example: if rolls include "Strength Saving Throw", "Wisdom Saving Throw", "Charisma Saving Throw",
  the phrase "Saving Throw" surfaces as a group.
- Selecting one or more groups narrows the Label dropdown to labels matching those groups.

> **Current state:** Roll Type has hardcoded fake placeholder options in the HTML.
> These must be removed. Real options will be populated from the API.
> The back-end grouping algorithm is not yet built.

#### Label — multi-select dropdown
- Icon: tag (`fa-tag`)
- Second level of the cascade.
- Shows labels that contain the selected Roll Type phrase(s), or all labels if Roll Type is at ALL.
- Populated from `data.labels` in the API response.
- Selecting specific labels narrows to those exact roll_label values.

> **Current state:** Populated from API correctly. Fake hardcoded options in HTML must be removed.

#### Variant — multi-select dropdown
- Icon: code-branch (`fa-code-branch`)
- Hidden by default (`display: none`). Appears only when the data warrants a third grouping level.
- Tooltip: "Variant (auto-grouped)"
- Third level of the cascade — sub-grouping within the selected Label(s).

> **DESIGN PENDING CONFIRMATION** — see notes below.

---

## Variant — Design To Be Confirmed

The Variant dropdown was designed and built during the 2026-05-23 session but its detailed
design was not written into this document at the time. The following is the current understanding
based on what was built, pending owner confirmation:

The Variant level is the third tier of the label cascade. After Roll Type narrows by category
(e.g. "Saving Throw") and Label narrows by specific label (e.g. "Strength Saving Throw"),
Variant would surface any further sub-groupings within those results — for example, if
"Strength Saving Throw" has multiple variants recorded (perhaps labelled differently by
different systems or homebrew). It is hidden because in most cases the cascade will not
need a third level.

**Owner must confirm:** what exactly Variant represents, when it should appear, and what
data it is populated from. Do not build the back-end for this until confirmed.

---

## Chart Area

### Chart Types
Three types, toggled by icon buttons in the controls bar.
- **Bar chart** (default) — face value distribution
- **Donut chart** — proportion view; shows custom HTML legend alongside
- **Line chart** — reserved for time-based trending

### Expand Button
Visible only in donut mode. Opens a larger modal view of the donut chart with a full legend.

### Custom Donut Legend
Rendered as HTML alongside the canvas (not inside Chart.js).
Splits items into two columns when count exceeds 10.

### Headline Numbers
Displayed as pills in the controls bar.
- Total rolls (matching current filters)
- Average roll value

> **Discrepancy from original spec:** Original design also listed Highest and Lowest as
> headline numbers. These were removed during the UI build session (2026-05-23) as they
> become meaningless over time. Current confirmed metrics: Total and Average only.

---

## Data Management

All three operations are scoped to whatever filters are currently active.

### Clear
- Disabled for now. Will be re-enabled once the rest of the panel is stable.
- Will delete rolls matching the current filter selection from rolls.db.
- Requires a confirmation prompt before executing.

### Export
- Exports rolls matching current filters as a CSV file.
- Calls `GET /api/roll-stats/export` with the current filter parameters.
- Filename should reflect the filter context.

### Import
- Imports a previously exported CSV file.
- Parses CSV in the browser, POSTs rows as JSON to `POST /api/roll-stats/import`.
- Merge strategy — does not replace existing data.
- Duplicate detection required: de-duplication key is rolled_at + player_name + die_type + value.

---

## Database Schema (existing, confirmed working)

```
campaigns:  id | world_id (unique) | world_title
sessions:   id | campaign_id | started_at (local time, ISO)
rolls:      id | session_id | campaign_id | die_type | value | rolled_at | roll_label | player_name
```

- `die_type` is stored as text with a `d` prefix: `d4`, `d6`, `d8`, `d10`, `d12`, `d20`, `d100`.
- Timestamps are local time from DLA commit a9005d3 onwards. Earlier rows are UTC.

---

## Back-end API

### GET /api/roll-stats
Query parameters:
- `die_types` — comma-separated list with `d` prefix (e.g. `d20,d6`) or `all`
- `world_ids` — comma-separated campaign IDs or `all`
- `session_scope` — `all` | `current` | `last1` | `last5` | `last10`
- `player_names` — comma-separated or `all`
- `label_filter` — substring or exact label, comma-separated for multiple, or `all`

Response:
```json
{
  "distribution": {"1": 4, "2": 7, ...},
  "total": 47,
  "average": 11.3,
  "highest": 20,
  "lowest": 1,
  "labels": ["Strength Saving Throw", "Wisdom Saving Throw", ...],
  "players": ["Alice", "Bob", ...],
  "worlds": [{"id": 1, "title": "Curse of Strahd"}, ...]
}
```

> **Known bug:** The front-end was sending `die_types=20` (no `d` prefix). The server stores
> `d20`. This causes zero results. Fix: front-end must send `die_types=d20`.

### GET /api/roll-stats/export
Same filter parameters as above. Returns a CSV file download.

### POST /api/roll-stats/import
Body: `{ "rows": [...] }` — array of roll objects parsed from CSV.

### DELETE /api/roll-stats
Same filter parameters as above. Deletes matching rolls.

---

## Front-end Files

| File | Role |
|------|------|
| `static/js/chart.min.js` | Chart.js bundled locally |
| `static/js/ui/stats.js` | All stats panel logic (v11 as of 2026-05-25) |
| `static/css/style-simple.css` | Stats panel CSS (v86 as of 2026-05-25) |
| `templates/index.html` | Panel HTML (CSS v86, stats.js v11 as of 2026-05-25) |

---

## Open Items

- [ ] Fix die_type prefix bug: front-end must send `d20` not `20`
- [ ] Remove hardcoded fake options from Roll Type dropdown in HTML
- [ ] Remove hardcoded fake options from Label dropdown in HTML
- [ ] Remove hardcoded fake options from World dropdown in HTML
- [ ] Remove hardcoded fake options from Player dropdown in HTML
- [ ] Confirm Variant design with owner (see Variant section above)
- [ ] Build back-end label grouping algorithm (bigrams/trigrams) for Roll Type cascade
- [ ] Build Variant cascade logic once design is confirmed
- [ ] Re-enable Clear button once panel is stable
- [ ] Confirm whether Die Type should remain single-select or revert to multi-select toggles
