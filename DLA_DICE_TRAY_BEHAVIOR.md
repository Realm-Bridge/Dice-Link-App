# DLA Dice Tray - Complete Behavior Specification

## Overview

The dice tray in idle mode allows users to build a dice formula and send it to DLC for rolling. This document explains exactly how DLC's dice tray works and how DLA should replicate it.

**Important: Maintain modular, clean code. Each responsibility should be in its own module/file.**

---

## UI Components

### 1. Formula Input Field
- Text input showing the current formula
- Starts with `/r ` prefix (Foundry chat command)
- Example: `/r 2d20kh+1d6+3`

### 2. Dice Buttons (7 buttons)
- d4, d6, d8, d10, d12, d20, d100
- Each shows an SVG icon of the blank die
- Each has a count badge (hidden when 0)

### 3. Modifier Controls
- Minus button (−)
- Modifier display (starts at 0)
- Plus button (+)

### 4. ADV/DIS Toggle Button
- Cycles through 3 states: Normal → Advantage → Disadvantage → Normal
- Button text changes: "ADV/DIS" → "ADV" → "DIS" → "ADV/DIS"

### 5. Roll Button
- Sends the formula to DLC

---

## State Variables

```javascript
// Dice tray state
const diceTrayState = {
  diceCounts: { 4: 0, 6: 0, 8: 0, 10: 0, 12: 0, 20: 0, 100: 0 },
  modifier: 0,
  advMode: 'normal' // 'normal' | 'advantage' | 'disadvantage'
};
```

---

## Button Behaviors

### Dice Buttons (d4, d6, d8, d10, d12, d20, d100)

**Left-click:** Add one die of that type
```javascript
function onDiceButtonClick(dieType) {
  diceTrayState.diceCounts[dieType]++;
  updateCountBadge(dieType);
  rebuildFormula();
}
```

**Right-click:** Remove one die of that type (minimum 0)
```javascript
function onDiceButtonRightClick(dieType, event) {
  event.preventDefault(); // Prevent browser context menu
  if (diceTrayState.diceCounts[dieType] > 0) {
    diceTrayState.diceCounts[dieType]--;
    updateCountBadge(dieType);
    rebuildFormula();
  }
}
```

**Count Badge:**
- Hidden when count is 0
- Shows count number when > 0

---

### Modifier Buttons

**Minus (−):**
```javascript
function onMinusClick() {
  diceTrayState.modifier--;
  updateModifierDisplay();
  rebuildFormula();
}
```

**Plus (+):**
```javascript
function onPlusClick() {
  diceTrayState.modifier++;
  updateModifierDisplay();
  rebuildFormula();
}
```

---

### ADV/DIS Toggle Button

This button cycles through 3 states and modifies d20 rolls in the formula:

| Current Text | Next State | Action | New Text |
|--------------|------------|--------|----------|
| "ADV/DIS" | advantage | Add `kh` to d20s | "ADV" |
| "ADV" | disadvantage | Change `kh` to `kl` | "DIS" |
| "DIS" | normal | Remove `kh`/`kl` | "ADV/DIS" |

**How kh/kl works:**
- `kh` = "keep highest" (advantage: roll 2d20, keep highest)
- `kl` = "keep lowest" (disadvantage: roll 2d20, keep lowest)
- When advantage is active: `1d20` becomes `1d20kh` (Foundry interprets this as 2d20kh1)
- When disadvantage is active: `1d20` becomes `1d20kl`

```javascript
function onAdvDisToggle() {
  // Determine next state
  if (diceTrayState.advMode === 'normal') {
    diceTrayState.advMode = 'advantage';
  } else if (diceTrayState.advMode === 'advantage') {
    diceTrayState.advMode = 'disadvantage';
  } else {
    diceTrayState.advMode = 'normal';
  }
  
  updateAdvDisButton();
  rebuildFormula();
}

function updateAdvDisButton() {
  const btn = document.getElementById('adv-dis-btn');
  btn.classList.remove('adv-active', 'dis-active');
  
  if (diceTrayState.advMode === 'advantage') {
    btn.textContent = 'ADV';
    btn.classList.add('adv-active');
  } else if (diceTrayState.advMode === 'disadvantage') {
    btn.textContent = 'DIS';
    btn.classList.add('dis-active');
  } else {
    btn.textContent = 'ADV/DIS';
  }
}
```

---

### Roll Button

Sends the formula to DLC via WebSocket:

```javascript
function onRollClick() {
  const formula = document.getElementById('formula-input').value;
  
  // Remove the /r prefix for sending
  const cleanFormula = formula.replace(/^\/r\s*/, '').trim();
  
  if (!cleanFormula) {
    // No dice selected
    return;
  }
  
  // Send to DLC
  sendToDLC({
    type: 'diceTrayRoll',
    formula: cleanFormula,
    flavor: 'Manual Dice Roll'
  });
  
  // Reset the tray after sending
  resetDiceTray();
}
```

---

## Formula Building Logic

The formula is rebuilt whenever any dice count, modifier, or ADV/DIS state changes:

```javascript
function rebuildFormula() {
  const parts = [];
  
  // Add dice in standard order (d20 first, then descending, d100 last)
  const dieOrder = [20, 12, 10, 8, 6, 4, 100];
  
  for (const die of dieOrder) {
    const count = diceTrayState.diceCounts[die];
    if (count > 0) {
      let dieNotation = `${count}d${die}`;
      
      // Apply advantage/disadvantage ONLY to d20s
      if (die === 20) {
        if (diceTrayState.advMode === 'advantage') {
          dieNotation = `${count}d20kh`;
        } else if (diceTrayState.advMode === 'disadvantage') {
          dieNotation = `${count}d20kl`;
        }
      }
      
      parts.push(dieNotation);
    }
  }
  
  // Build formula string
  let formula = parts.join('+');
  
  // Add modifier
  if (diceTrayState.modifier !== 0) {
    if (diceTrayState.modifier > 0) {
      formula += `+${diceTrayState.modifier}`;
    } else {
      formula += `${diceTrayState.modifier}`; // Negative already has minus sign
    }
  }
  
  // Update the input field with /r prefix
  document.getElementById('formula-input').value = `/r ${formula}`;
}
```

---

## Reset Function

Called after a roll is sent or when manually clearing:

```javascript
function resetDiceTray() {
  // Reset all counts to 0
  Object.keys(diceTrayState.diceCounts).forEach(die => {
    diceTrayState.diceCounts[die] = 0;
  });
  
  // Reset modifier
  diceTrayState.modifier = 0;
  
  // Reset ADV/DIS to normal
  diceTrayState.advMode = 'normal';
  
  // Update UI
  document.querySelectorAll('.die-count-badge').forEach(badge => {
    badge.textContent = '0';
    badge.style.display = 'none';
  });
  
  document.getElementById('modifier-display').textContent = '0';
  document.getElementById('formula-input').value = '/r ';
  
  const advBtn = document.getElementById('adv-dis-btn');
  advBtn.textContent = 'ADV/DIS';
  advBtn.classList.remove('adv-active', 'dis-active');
}
```

---

## Communication Flow (DLA Dice Tray → DLC → Foundry → DLC → DLA)

### Step 1: User builds formula in DLA dice tray
User clicks: d20, d20, d6, +, +, + (modifier = 3), ADV
Formula shows: `/r 2d20kh+1d6+3`

### Step 2: User clicks Roll
DLA sends to DLC:
```json
{
  "type": "diceTrayRoll",
  "formula": "2d20kh+1d6+3",
  "flavor": "Manual Dice Roll"
}
```

### Step 3: DLC receives and triggers Foundry roll
DLC creates the roll in Foundry, which shows the dice resolver dialog.

### Step 4: DLC sends diceRequest to DLA
```json
{
  "type": "diceRequest",
  "id": "dlc-123456789",
  "dice": [
    { "type": "d20", "count": 2 },
    { "type": "d6", "count": 1 }
  ],
  "formula": "2d20kh+1d6+3",
  "rollType": "normal"
}
```

### Step 5: DLA shows dice entry UI (Roll Resolution state)
User enters the values they rolled on physical dice.

### Step 6: DLA sends results back to DLC
```json
{
  "type": "diceResult",
  "originalRollId": "dlc-123456789",
  "results": [
    { "type": "d20", "value": 18 },
    { "type": "d20", "value": 7 },
    { "type": "d6", "value": 4 }
  ]
}
```

### Step 7: DLC injects results into Foundry
Foundry completes the roll with the provided values.

---

## CSS Classes for Visual States

```css
/* ADV/DIS button states */
.adv-dis-btn.adv-active {
  background-color: var(--dlc-success);
  color: white;
}

.adv-dis-btn.dis-active {
  background-color: var(--dlc-danger);
  color: white;
}

/* Die count badge */
.die-count-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: var(--dlc-accent);
  color: white;
  border-radius: 50%;
  min-width: 18px;
  height: 18px;
  font-size: 12px;
  display: none; /* Hidden when 0 */
}

.die-count-badge.visible {
  display: flex;
  align-items: center;
  justify-content: center;
}
```

---

## Testing Checklist

1. **Dice Buttons:**
   - [ ] Left-click d20 → count shows 1, formula shows `/r 1d20`
   - [ ] Left-click d20 again → count shows 2, formula shows `/r 2d20`
   - [ ] Right-click d20 → count shows 1, formula shows `/r 1d20`
   - [ ] Right-click d20 → count shows 0 (hidden), formula shows `/r `
   - [ ] Right-click when count is 0 → nothing happens

2. **Modifier:**
   - [ ] Click + → modifier shows 1, formula shows `/r +1`
   - [ ] Click + again → modifier shows 2, formula shows `/r +2`
   - [ ] Click − → modifier shows 1, formula shows `/r +1`
   - [ ] Click − twice more → modifier shows -1, formula shows `/r -1`

3. **ADV/DIS Toggle:**
   - [ ] Add d20, click ADV/DIS → button shows "ADV", formula shows `/r 1d20kh`
   - [ ] Click again → button shows "DIS", formula shows `/r 1d20kl`
   - [ ] Click again → button shows "ADV/DIS", formula shows `/r 1d20`
   - [ ] ADV/DIS only affects d20s, not other dice (d6, d8, etc.)

4. **Combined:**
   - [ ] Add d20, d20, d6, modifier +3, ADV → formula shows `/r 2d20kh+1d6+3`

5. **Roll Button:**
   - [ ] Clicking Roll sends the formula to DLC
   - [ ] After Roll, tray resets to empty state

6. **Communication:**
   - [ ] DLC receives diceTrayRoll message
   - [ ] DLC sends back diceRequest with correct dice breakdown
   - [ ] DLA shows dice entry for the correct dice
   - [ ] Results sent back complete the roll in Foundry
