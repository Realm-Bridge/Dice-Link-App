# DLA Dice Tray & Visual Dice Entry Specification

## Overview
The Roll Window needs SVG-based dice buttons instead of manual text entry. This spec covers:
1. **Dice Tray** (idle state) - Clickable dice type buttons (d4, d6, d8, d10, d12, d20, d100)
2. **Dice Entry/Resolution** (diceRequest state) - Clickable SVG dice faces to select rolled values

Both must match DLC's visual style with the Realm Bridge brand colors.

---

## Part 1: CSS Variables (Color Theme)

Add these CSS variables to `style.css`. These are the Realm Bridge brand colors used throughout DLC:

```css
:root {
  /* Background colors */
  --dlc-bg-dark: #212a37;
  --dlc-bg-section: #2a3547;
  --dlc-bg-input: #181f2b;
  
  /* Border and accent - purple/pink Realm Bridge brand colors */
  --dlc-border: #6f2e9a;
  --dlc-accent: #6f2e9a;           /* Purple - primary accent */
  --dlc-accent-pink: #a78bfa;      /* Pink/violet - used in gradients and highlights */
  --dlc-accent-hover: #5d9eca;
  --dlc-accent-glow: rgba(111, 46, 154, 0.3);
  
  /* Text colors */
  --dlc-text-primary: #e7f6ff;
  --dlc-text-secondary: #a0a0b0;
  --dlc-text-muted: #6c6c7c;
  
  /* Status colors */
  --dlc-success: #10b981;
  --dlc-success-hover: #34d399;
  --dlc-warning: #D5D5D6;
  --dlc-warning-hover: #e8e8e8;
  --dlc-danger: #ef4444;
  --dlc-danger-hover: #f87171;
  
  /* Mode colors */
  --dlc-digital: #6366f1;
  --dlc-manual: #10b981;
  --dlc-individual: #6366f1;
}

/* The purple-to-pink gradient used on header/accent elements */
.gradient-accent {
  background: linear-gradient(90deg, var(--dlc-accent) 0%, var(--dlc-accent-pink) 100%);
}
```

---

## Part 2: SVG Dice Assets

DLA already has SVG dice files in `static/DLC Dice/`. The folder structure is:

```
static/DLC Dice/
├── D4/
│   ├── d4-blank.svg          # Blank die for tray button
│   ├── d4 - Outline 1.svg    # Die showing value 1
│   ├── d4 - Outline 2.svg    # Die showing value 2
│   ├── d4 - Outline 3.svg    # etc.
│   └── d4 - Outline 4.svg
├── D6/
│   ├── d6-blank.svg
│   ├── d6 - Outline 1.svg through d6 - Outline 6.svg
├── D8/
│   ├── d8-blank.svg
│   ├── d8 - Outline 1.svg through d8 - Outline 8.svg
├── D10/
│   ├── d10-blank.svg
│   ├── d10 - Outline 1.svg through d10 - Outline 10.svg
├── D12/
│   ├── d12-blank.svg
│   ├── d12 - Outline 1.svg through d12 - Outline 12.svg
├── D20/
│   ├── d20-blank.svg
│   ├── d20 - Outline 1.svg through d20 - Outline 20.svg
└── D100/
    └── d100-blank.svg        # Only blank (use text input for d100)
```

---

## Part 3: Dice Tray (Idle State)

### HTML Structure
Replace the placeholder dice tray with this:

```html
<div id="roll-window-idle" class="roll-window-state">
  <div class="dice-tray">
    <!-- Formula input row -->
    <div class="dice-formula-row">
      <input type="text" class="dice-formula-input" placeholder="/r 1d20" value="/r ">
    </div>
    
    <!-- Dice buttons row -->
    <div class="dice-buttons-row">
      <button type="button" class="dice-btn" data-die="4" title="d4">
        <img src="/static/DLC Dice/D4/d4-blank.svg" alt="d4" class="die-svg-icon">
        <span class="die-count" style="display:none;">0</span>
      </button>
      <button type="button" class="dice-btn" data-die="6" title="d6">
        <img src="/static/DLC Dice/D6/d6-blank.svg" alt="d6" class="die-svg-icon">
        <span class="die-count" style="display:none;">0</span>
      </button>
      <button type="button" class="dice-btn" data-die="8" title="d8">
        <img src="/static/DLC Dice/D8/d8-blank.svg" alt="d8" class="die-svg-icon">
        <span class="die-count" style="display:none;">0</span>
      </button>
      <button type="button" class="dice-btn" data-die="10" title="d10">
        <img src="/static/DLC Dice/D10/d10-blank.svg" alt="d10" class="die-svg-icon">
        <span class="die-count" style="display:none;">0</span>
      </button>
      <button type="button" class="dice-btn" data-die="12" title="d12">
        <img src="/static/DLC Dice/D12/d12-blank.svg" alt="d12" class="die-svg-icon">
        <span class="die-count" style="display:none;">0</span>
      </button>
      <button type="button" class="dice-btn" data-die="20" title="d20">
        <img src="/static/DLC Dice/D20/d20-blank.svg" alt="d20" class="die-svg-icon">
        <span class="die-count" style="display:none;">0</span>
      </button>
      <button type="button" class="dice-btn" data-die="100" title="d100">
        <img src="/static/DLC Dice/D100/d100-blank.svg" alt="d100" class="die-svg-icon">
        <span class="die-count" style="display:none;">0</span>
      </button>
    </div>
    
    <!-- Controls row: modifier, ADV/DIS, Roll button -->
    <div class="dice-controls-row">
      <button type="button" class="dice-mod-btn dice-minus" title="Decrease modifier">−</button>
      <span class="dice-modifier">0</span>
      <button type="button" class="dice-mod-btn dice-plus" title="Increase modifier">+</button>
      <button type="button" class="dice-adv-btn" data-mode="normal" title="Toggle Advantage/Disadvantage">ADV/DIS</button>
      <button type="button" class="dice-roll-btn btn-success" title="Roll dice">Roll</button>
    </div>
  </div>
</div>
```

### CSS for Dice Tray

```css
/* ============================================================================
   DICE TRAY STYLES
   ============================================================================ */

.dice-tray {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 8px;
  background: var(--dlc-bg-input);
  border-radius: 6px;
}

.dice-formula-row {
  width: 100%;
}

.dice-formula-input {
  width: 100%;
  padding: 10px 12px;
  background: var(--dlc-bg-dark);
  border: 1px solid var(--dlc-border);
  border-radius: 4px;
  color: var(--dlc-text-primary);
  font-family: monospace;
  font-size: 14px;
  box-sizing: border-box;
}

.dice-formula-input:focus {
  outline: none;
  border-color: var(--dlc-accent);
}

.dice-buttons-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: center;
}

.dice-btn {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: auto;
  height: auto;
  background: transparent;
  border: none;
  border-radius: 0;
  color: var(--dlc-text-secondary);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s ease;
  padding: 0;
}

.dice-btn:hover {
  opacity: 0.8;
}

.die-svg-icon {
  width: 48px;
  height: 48px;
  object-fit: contain;
  display: block;
}

/* Per-die size adjustments */
.dice-btn[data-die="4"] .die-svg-icon {
  width: 40px;
  height: 40px;
}

.dice-btn[data-die="100"] .die-svg-icon {
  width: 52px;
  height: 52px;
}

.die-count {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: var(--dlc-warning);
  color: #1a1a1a;
  font-size: 10px;
  font-weight: 700;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dice-controls-row {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: center;
}

.dice-mod-btn {
  width: 32px;
  height: 32px;
  background: var(--dlc-bg-section);
  border: 1px solid var(--dlc-border);
  border-radius: 4px;
  color: var(--dlc-text-primary);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dice-mod-btn:hover {
  background: var(--dlc-bg-input);
  border-color: var(--dlc-accent);
}

.dice-modifier {
  min-width: 30px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: var(--dlc-text-primary);
}

.dice-adv-btn {
  padding: 6px 12px;
  background: var(--dlc-bg-section);
  border: 1px solid var(--dlc-border);
  border-radius: 4px;
  color: var(--dlc-text-secondary);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.dice-adv-btn:hover {
  background: var(--dlc-bg-input);
  border-color: var(--dlc-accent);
}

.dice-adv-btn.adv-active {
  background: var(--dlc-success);
  border-color: var(--dlc-success);
  color: #fff;
}

.dice-adv-btn.dis-active {
  background: var(--dlc-danger);
  border-color: var(--dlc-danger);
  color: #fff;
}

.dice-roll-btn {
  padding: 8px 20px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-success {
  background: var(--dlc-success);
  border: 1px solid var(--dlc-success);
  color: #fff;
}

.btn-success:hover {
  background: var(--dlc-success-hover);
}
```

### JavaScript for Dice Tray

```javascript
// State for dice tray
const diceTrayState = {
  dice: { 4: 0, 6: 0, 8: 0, 10: 0, 12: 0, 20: 0, 100: 0 },
  modifier: 0,
  advMode: 'normal' // 'normal' | 'advantage' | 'disadvantage'
};

function initDiceTray() {
  // Dice button left-click - add one die to formula
  document.querySelectorAll('.dice-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const die = parseInt(btn.dataset.die);
      diceTrayState.dice[die]++;
      updateDiceTrayDisplay();
    });
    
    // Dice button right-click - subtract one die from formula (matches DLC behavior)
    btn.addEventListener('contextmenu', (e) => {
      e.preventDefault(); // Prevent browser context menu
      const die = parseInt(btn.dataset.die);
      if (diceTrayState.dice[die] > 0) {
        diceTrayState.dice[die]--;
        updateDiceTrayDisplay();
      }
    });
  });
  
  // Modifier buttons
  document.querySelector('.dice-minus')?.addEventListener('click', () => {
    diceTrayState.modifier--;
    updateDiceTrayDisplay();
  });
  
  document.querySelector('.dice-plus')?.addEventListener('click', () => {
    diceTrayState.modifier++;
    updateDiceTrayDisplay();
  });
  
  // ADV/DIS toggle (cycles: normal -> advantage -> disadvantage -> normal)
  document.querySelector('.dice-adv-btn')?.addEventListener('click', (e) => {
    const btn = e.currentTarget;
    if (diceTrayState.advMode === 'normal') {
      diceTrayState.advMode = 'advantage';
      btn.classList.add('adv-active');
      btn.classList.remove('dis-active');
    } else if (diceTrayState.advMode === 'advantage') {
      diceTrayState.advMode = 'disadvantage';
      btn.classList.remove('adv-active');
      btn.classList.add('dis-active');
    } else {
      diceTrayState.advMode = 'normal';
      btn.classList.remove('adv-active', 'dis-active');
    }
  });
  
  // Roll button
  document.querySelector('.dice-roll-btn')?.addEventListener('click', () => {
    const formula = buildDiceFormula();
    if (formula) {
      // Send roll command to DLC
      sendMessage({
        type: 'manualRoll',
        formula: formula,
        advMode: diceTrayState.advMode
      });
      // Reset tray
      resetDiceTray();
    }
  });
}

function updateDiceTrayDisplay() {
  // Update formula input
  const formula = buildDiceFormula();
  const input = document.querySelector('.dice-formula-input');
  if (input) {
    input.value = formula ? `/r ${formula}` : '/r ';
  }
  
  // Update die count badges
  document.querySelectorAll('.dice-btn').forEach(btn => {
    const die = parseInt(btn.dataset.die);
    const count = diceTrayState.dice[die];
    const badge = btn.querySelector('.die-count');
    if (badge) {
      badge.textContent = count;
      badge.style.display = count > 0 ? 'flex' : 'none';
    }
  });
  
  // Update modifier display
  const modDisplay = document.querySelector('.dice-modifier');
  if (modDisplay) {
    const mod = diceTrayState.modifier;
    modDisplay.textContent = mod >= 0 ? `+${mod}` : mod.toString();
  }
}

function buildDiceFormula() {
  const parts = [];
  
  // Add dice
  for (const [die, count] of Object.entries(diceTrayState.dice)) {
    if (count > 0) {
      parts.push(`${count}d${die}`);
    }
  }
  
  // Add modifier
  if (diceTrayState.modifier !== 0) {
    if (diceTrayState.modifier > 0) {
      parts.push(`+ ${diceTrayState.modifier}`);
    } else {
      parts.push(`- ${Math.abs(diceTrayState.modifier)}`);
    }
  }
  
  return parts.join(' ');
}

function resetDiceTray() {
  diceTrayState.dice = { 4: 0, 6: 0, 8: 0, 10: 0, 12: 0, 20: 0, 100: 0 };
  diceTrayState.modifier = 0;
  diceTrayState.advMode = 'normal';
  
  document.querySelector('.dice-adv-btn')?.classList.remove('adv-active', 'dis-active');
  updateDiceTrayDisplay();
}

// Call on page load
document.addEventListener('DOMContentLoaded', initDiceTray);
```

---

## Part 4: Dice Entry/Resolution (diceRequest State)

When DLC sends a `diceRequest` message, show clickable SVG dice faces for each die needed.

### HTML Structure (generated dynamically)

```javascript
function renderDiceEntry(diceRequest) {
  const { dice, formula, rollType } = diceRequest;
  
  // Build dice rows - each die gets a row with all possible face values
  const diceRows = [];
  
  for (let i = 0; i < dice.length; i++) {
    const dieInfo = dice[i];
    const dieType = dieInfo.type.toLowerCase(); // e.g., "d20"
    const faces = parseInt(dieType.replace('d', '')); // e.g., 20
    
    // For d100, use text input (100 buttons is impractical)
    if (faces === 100) {
      diceRows.push(`
        <div class="dice-row dice-row-manual" data-row="${i}" data-faces="${faces}">
          <span class="dice-row-label">${dieType}</span>
          <input type="number" 
                 class="dice-manual-input" 
                 data-row="${i}"
                 data-faces="${faces}"
                 min="1" max="100" 
                 placeholder="1-100">
        </div>
      `);
      continue;
    }
    
    // For other dice, show clickable SVG buttons for each face value
    const diceOptions = [];
    for (let value = 1; value <= faces; value++) {
      const svgPath = `/static/DLC Dice/${dieType.toUpperCase()}/${dieType} - Outline ${value}.svg`;
      diceOptions.push(`
        <button type="button" 
                class="die-option" 
                data-row="${i}" 
                data-value="${value}" 
                data-faces="${faces}"
                title="${dieType}: ${value}">
          <div class="die-face">
            <img src="${svgPath}" alt="${dieType} ${value}" class="die-image">
          </div>
        </button>
      `);
    }
    
    diceRows.push(`
      <div class="dice-row" data-row="${i}" data-faces="${faces}">
        <span class="dice-row-label">${dieType}</span>
        <div class="dice-options">
          ${diceOptions.join('')}
        </div>
      </div>
    `);
  }
  
  return `
    <div class="dice-entry">
      <div class="dice-entry-header">
        <h4 class="dice-entry-title">Enter Dice Results</h4>
        <p class="dice-entry-formula">${formula || ''}</p>
      </div>
      <div class="dice-rows">
        ${diceRows.join('')}
      </div>
      <div class="dice-entry-actions">
        <button type="button" class="submit-dice-btn btn-success">SUBMIT</button>
      </div>
    </div>
  `;
}
```

### CSS for Dice Entry

```css
/* ============================================================================
   DICE ENTRY/RESOLUTION STYLES
   ============================================================================ */

.dice-entry {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: var(--dlc-bg-input);
  border-radius: 6px;
}

.dice-entry-header {
  text-align: center;
}

.dice-entry-title {
  margin: 0 0 4px 0;
  color: var(--dlc-text-primary);
  font-size: 16px;
  font-weight: 600;
}

.dice-entry-formula {
  margin: 0;
  color: var(--dlc-text-secondary);
  font-family: monospace;
  font-size: 14px;
}

.dice-rows {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.dice-row {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dice-row-label {
  color: var(--dlc-text-secondary);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
}

.dice-options {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-height: 180px;
  overflow-y: auto;
  padding: 4px;
}

/* Custom scrollbar for dice options */
.dice-options::-webkit-scrollbar {
  width: 6px;
}

.dice-options::-webkit-scrollbar-track {
  background: transparent;
}

.dice-options::-webkit-scrollbar-thumb {
  background: var(--dlc-border);
  border-radius: 3px;
}

.die-option {
  position: relative;
  width: 52px;
  height: 52px;
  padding: 0;
  border: none;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s ease, filter 0.15s ease;
  flex-shrink: 0;
}

.die-option:hover {
  transform: scale(1.12);
  filter: brightness(1.3);
}

.die-option.selected {
  filter: brightness(1.4) drop-shadow(0 0 6px var(--dlc-success));
}

.die-face {
  position: relative;
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.die-image {
  width: 52px;
  height: 52px;
  display: block;
  pointer-events: none;
}

/* d100 manual text input */
.dice-row-manual {
  flex-direction: row;
  align-items: center;
  gap: 12px;
}

.dice-manual-input {
  width: 80px;
  padding: 6px 10px;
  background: var(--dlc-bg-input);
  border: 1px solid var(--dlc-border);
  border-radius: 4px;
  color: var(--dlc-text-primary);
  font-size: 14px;
  text-align: center;
}

.dice-manual-input:focus {
  outline: none;
  border-color: var(--dlc-accent);
}

.dice-entry-actions {
  margin-top: 8px;
}

.submit-dice-btn {
  width: 100%;
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
}
```

### JavaScript for Dice Entry

```javascript
// Track selected values for each die row
let diceEntryValues = [];

function initDiceEntry(diceRequest) {
  // Reset values array
  diceEntryValues = new Array(diceRequest.dice.length).fill(null);
  
  // Click handlers for die options
  document.querySelectorAll('.die-option').forEach(btn => {
    btn.addEventListener('click', () => {
      const row = parseInt(btn.dataset.row);
      const value = parseInt(btn.dataset.value);
      
      // Deselect previous selection in this row
      document.querySelectorAll(`.die-option[data-row="${row}"]`).forEach(b => {
        b.classList.remove('selected');
      });
      
      // Select this one
      btn.classList.add('selected');
      diceEntryValues[row] = value;
    });
  });
  
  // Manual input handlers (for d100)
  document.querySelectorAll('.dice-manual-input').forEach(input => {
    input.addEventListener('change', () => {
      const row = parseInt(input.dataset.row);
      const value = parseInt(input.value);
      if (value >= 1 && value <= 100) {
        diceEntryValues[row] = value;
      }
    });
  });
  
  // Submit button
  document.querySelector('.submit-dice-btn')?.addEventListener('click', () => {
    // Check all dice have values
    const allFilled = diceEntryValues.every(v => v !== null && v !== undefined);
    if (!allFilled) {
      alert('Please select a value for each die');
      return;
    }
    
    // Build results array
    const results = diceEntryValues.map((value, index) => ({
      type: diceRequest.dice[index].type,
      value: value
    }));
    
    // Send to DLC
    sendMessage({
      type: 'diceResult',
      originalRollId: diceRequest.originalRollId,
      results: results
    });
    
    // Return to idle state
    state.rollWindowState = 'idle';
    state.currentDiceRequest = null;
    diceEntryValues = [];
    updateRollWindow();
  });
}
```

---

## Part 5: Integration

When handling `diceRequest` messages:

```javascript
function handleDiceRequest(message) {
  state.rollWindowState = 'diceEntry';
  state.currentDiceRequest = message;
  
  // Render the dice entry UI
  const container = document.getElementById('roll-window-dice-entry');
  container.innerHTML = renderDiceEntry(message);
  
  // Initialize click handlers
  initDiceEntry(message);
  
  // Show this state
  updateRollWindow();
}
```

---

## Testing Checklist

1. **Idle State:**
   - [ ] Dice tray displays with all 7 dice type buttons
   - [ ] Left-click adds one die to formula
   - [ ] Right-click subtracts one die from formula (minimum 0)
   - [ ] +/- modifier buttons work
   - [ ] ADV/DIS toggle cycles through states
   - [ ] Roll button builds and sends formula

2. **Dice Entry State:**
   - [ ] Receives diceRequest and shows SVG dice grid
   - [ ] Clicking a die face selects it (highlighted)
   - [ ] Only one value per row can be selected
   - [ ] d100 shows text input instead of 100 buttons
   - [ ] Submit sends diceResult with correct values
   - [ ] Returns to idle after submit

3. **Visual:**
   - [ ] Purple accent color `#6f2e9a` used on borders and highlights
   - [ ] Pink/violet `#a78bfa` used in gradients
   - [ ] Dark backgrounds `#212a37` / `#2a3547` / `#181f2b`
   - [ ] SVG dice display correctly
   - [ ] Hover/selected states visible
