# Dice Link App - Communication Testing Plan

## Overview

This document outlines the changes needed for Dice Link App (DLA) to test real communication with Dice Link Companion (DLC) module in Foundry VTT.

**Important:** This is purely for testing the WebSocket communication. No new functionality is being added - we are verifying the existing Phase 1-3 implementation works with real DLC data.

---

## Port Change Required

**The WebSocket port must be changed from 8765 to 47293.**

This applies to:
- `config.py` - Update the default port constant
- Any hardcoded references to port 8765
- Settings UI default value

---

## What DLC Now Sends

DLC v1.0.8.54 now includes a WebSocket client (`websocket-client.js`) that:

1. **Connects automatically** on Foundry load to `ws://localhost:47293/ws/dlc`
2. **Sends a connect message** with client info:
```json
{
  "type": "connect",
  "client": "dlc",
  "version": "1.0.8.54",
  "user": {
    "id": "foundry-user-id",
    "name": "Player Name",
    "isGM": true
  },
  "id": "dlc-1234567890-1",
  "timestamp": 1699999999999
}
```

3. **Sends rollRequest** when a dialog is intercepted (player triggers attack, skill check, etc.):
```json
{
  "type": "rollRequest",
  "id": "dlc-1234567890-2",
  "timestamp": 1699999999999,
  "player": {
    "id": "foundry-user-id",
    "name": "Player Name"
  },
  "roll": {
    "title": "Longsword Attack",
    "subtitle": "1d20 + 5",
    "formula": "1d20 + 5",
    "dice": [
      { "type": "d20", "count": 1 }
    ]
  },
  "config": {
    "fields": [
      {
        "name": "rollMode",
        "label": "Roll Mode",
        "type": "select",
        "options": [
          { "value": "publicroll", "label": "Public Roll" },
          { "value": "gmroll", "label": "GM Only" }
        ],
        "selected": "publicroll"
      }
    ]
  },
  "buttons": [
    { "id": "advantage", "label": "Advantage" },
    { "id": "normal", "label": "Normal" },
    { "id": "disadvantage", "label": "Disadvantage" }
  ]
}
```

---

## What DLC Expects Back

### Roll Result
When user completes the roll in DLA:
```json
{
  "type": "rollResult",
  "id": "dlc-1234567890-2",
  "timestamp": 1699999999999,
  "button": "normal",
  "configChanges": {
    "rollMode": "gmroll"
  },
  "results": [
    { "type": "d20", "value": 17 }
  ]
}
```

**Important fields:**
- `id` - Must match the original rollRequest id
- `button` - The button id that was clicked (e.g., "advantage", "normal", "disadvantage")
- `configChanges` - Only include fields that changed from the original values
- `results` - Array of dice results with type and value

### Roll Cancelled
If user cancels:
```json
{
  "type": "rollCancelled",
  "id": "dlc-1234567890-2",
  "reason": "User cancelled"
}
```

### Connection Acknowledged
When DLC connects, DLA should respond:
```json
{
  "type": "connected",
  "version": "1.0.0",
  "serverName": "Dice Link"
}
```

---

## Testing Checklist

### 1. Port Configuration
- [ ] Update DLA to use port 47293
- [ ] Verify settings UI shows correct default port

### 2. Connection Test
- [ ] Start DLA (should show "Waiting for connection")
- [ ] Load Foundry with DLC enabled
- [ ] DLA should show "Connected" status
- [ ] Foundry should show notification "Connected to Dice Link App"

### 3. Roll Request Test
- [ ] In Foundry, trigger a roll (e.g., click attack on character sheet)
- [ ] DLA should receive and display the roll request
- [ ] Verify title, formula, dice icons display correctly
- [ ] Verify configuration dropdowns render with correct options
- [ ] Verify action buttons render correctly

### 4. Roll Result Test
- [ ] In DLA, modify a config field (e.g., change Roll Mode)
- [ ] Click an action button (e.g., "Normal")
- [ ] Enter dice results manually
- [ ] Submit the result
- [ ] Verify DLC receives the result (check Foundry console for debug messages)
- [ ] Verify the roll completes in Foundry

### 5. Cancellation Test
- [ ] Trigger a new roll in Foundry
- [ ] In DLA, click Cancel
- [ ] Verify the roll is cancelled in Foundry

### 6. Reconnection Test
- [ ] With connection established, close DLA
- [ ] Foundry should show disconnection
- [ ] Restart DLA
- [ ] DLC should automatically reconnect

---

## Debug Messages to Watch

In **Foundry browser console**, look for:
- `[Dice Link WebSocket] Connecting` - DLC attempting to connect
- `[Dice Link WebSocket] Connected` - Connection successful
- `[Dice Link WebSocket] Sending` - Messages being sent to DLA
- `[Dice Link WebSocket] Received` - Messages received from DLA
- `[Dice Link Debug] Sending roll request to Dice Link App` - Roll data being forwarded
- `[Dice Link Debug] Roll result from Dice Link App` - Result received

In **DLA console/logs**, look for equivalent connection and message logs.

---

## Known Limitations (Current State)

1. **Dice results not yet injected** - DLC receives the results but currently just triggers the button click. Full dice value injection via Foundry's fulfillment API is TODO.

2. **Manual entry only** - DLA Phase 1-3 uses manual dice entry. Camera detection is Phase 4.

3. **No video feed yet** - Video streaming from DLA to DLC is not implemented in this test phase.

---

## Summary of DLA Changes Needed

1. **Change port from 8765 to 47293** in config and settings
2. **Ensure `/ws/dlc` endpoint exists** (DLC connects to `ws://localhost:47293/ws/dlc`)
3. **Send `connected` response** when DLC sends `connect` message
4. **Use `button` field** in rollResult (not `buttonClicked`)
5. **Match message IDs** - rollResult.id must match rollRequest.id

That's it - no new features, just port change and protocol verification.
