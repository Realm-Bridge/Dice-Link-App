# DLA Roll Window Implementation Specification

## Overview
Add a permanent "Roll Window" section to DLA's dashboard that displays one of three internal states:
1. **Dice Tray** (idle) - Basic dice buttons when no roll is pending
2. **Roll Request** (config) - Shows roll details and action buttons when DLC sends a roll
3. **Dice Entry** (resolution) - Input fields to enter dice results when DLC requests dice values

**Important:** This is a dashboard layout - the Roll Window is ONE section that remains visible alongside other sections (camera feed, connection status, settings, etc.). Only the Roll Window's internal content changes between states.

## Integration with Existing DLA Patterns

### State Object Additions
Add to the existing `state` object in `client.js`:
```javascript
const state = {
    // ... existing properties ...
    
    // Roll Window state
    rollWindowState: 'idle', // 'idle' | 'rollRequest' | 'diceEntry'
    currentRollRequest: null, // Data from DLC's rollRequest message
    currentDiceRequest: null, // Data from DLC's diceRequest message
    enteredDiceValues: [],    // User's clicked dice values
};
```

### Dashboard Integration
The Roll Window is a **permanent visible section** on the dashboard (not a full-page panel swap). It sits alongside other dashboard sections. Only its internal content changes between the three states:

```javascript
function updateRollWindow(newState) {
    state.rollWindowState = newState;
    
    const idleView = document.getElementById('roll-window-idle');
    const requestView = document.getElementById('roll-window-request');
    const entryView = document.getElementById('roll-window-entry');
    
    idleView.style.display = newState === 'idle' ? 'block' : 'none';
    requestView.style.display = newState === 'rollRequest' ? 'block' : 'none';
    entryView.style.display = newState === 'diceEntry' ? 'block' : 'none';
}
```

---

## HTML Structure (add to index.html)

```html
<!-- Roll Window - Always visible on main page -->
<div id="roll-window" class="roll-window">
    
    <!-- State 1: Idle - Dice Tray -->
    <div id="roll-window-idle" class="roll-window-state">
        <div class="dice-tray">
            <div class="dice-tray-dice">
                <button class="dice-btn" data-die="d4">
                    <img src="/static/DLC Dice/D4.svg" alt="D4">
                </button>
                <button class="dice-btn" data-die="d6">
                    <img src="/static/DLC Dice/D6.svg" alt="D6">
                </button>
                <button class="dice-btn" data-die="d8">
                    <img src="/static/DLC Dice/D8.svg" alt="D8">
                </button>
                <button class="dice-btn" data-die="d10">
                    <img src="/static/DLC Dice/D10.svg" alt="D10">
                </button>
                <button class="dice-btn" data-die="d12">
                    <img src="/static/DLC Dice/D12.svg" alt="D12">
                </button>
                <button class="dice-btn" data-die="d20">
                    <img src="/static/DLC Dice/D20.svg" alt="D20">
                </button>
                <button class="dice-btn" data-die="d100">
                    <img src="/static/DLC Dice/D100.svg" alt="D100">
                </button>
            </div>
            <div class="dice-tray-controls">
                <button class="modifier-btn" data-mod="-1">-</button>
                <span class="modifier-display">+0</span>
                <button class="modifier-btn" data-mod="+1">+</button>
            </div>
            <div class="dice-tray-actions">
                <button class="roll-type-btn active" data-type="normal">Normal</button>
                <button class="roll-type-btn" data-type="advantage">ADV</button>
                <button class="roll-type-btn" data-type="disadvantage">DIS</button>
            </div>
            <button class="dice-tray-roll-btn">Roll</button>
            <p class="idle-message">Waiting for roll from Foundry...</p>
        </div>
    </div>
    
    <!-- State 2: Roll Request - Configuration -->
    <div id="roll-window-request" class="roll-window-state" style="display: none;">
        <div class="roll-request">
            <h2 class="roll-title" id="roll-request-title">Roll Title</h2>
            <p class="roll-formula" id="roll-request-formula">1d20 + 5</p>
            
            <div class="roll-config">
                <!-- Situational Bonus -->
                <div class="config-field">
                    <label for="situational-bonus">Situational Bonus</label>
                    <input type="text" id="situational-bonus" name="Roll.0.situational" placeholder="e.g. +2 or 1d4">
                </div>
                
                <!-- Dynamic config fields inserted here by JS -->
                <div id="roll-config-fields"></div>
            </div>
            
            <div class="roll-actions" id="roll-action-buttons">
                <!-- Buttons inserted by JS based on rollRequest.buttons -->
            </div>
            
            <button class="cancel-btn" id="roll-request-cancel">Cancel Roll</button>
        </div>
    </div>
    
    <!-- State 3: Dice Entry - Resolution -->
    <div id="roll-window-entry" class="roll-window-state" style="display: none;">
        <div class="dice-entry">
            <h2 class="entry-title">Enter Dice Results</h2>
            <p class="entry-roll-type" id="dice-entry-roll-type">Normal</p>
            <p class="entry-instruction">Roll these dice:</p>
            
            <div class="dice-to-roll" id="dice-to-roll">
                <!-- Dice SVGs and value inputs inserted by JS -->
            </div>
            
            <div class="entry-actions">
                <button class="submit-btn" id="dice-entry-submit" disabled>Submit Results</button>
                <button class="back-btn" id="dice-entry-back">Back</button>
            </div>
        </div>
    </div>
    
</div>
```

---

## JavaScript Implementation (add to client.js)

### Message Handler Updates
In the existing `handleMessage(message)` switch statement, add/update these cases:

```javascript
case 'rollRequest':
    handleRollRequest(message);
    break;

case 'diceRequest':
    handleDiceRequest(message);
    break;
```

### Roll Request Handler (Phase A - Config)
```javascript
function handleRollRequest(message) {
    state.currentRollRequest = message;
    state.enteredDiceValues = [];
    
    // Update title and formula
    document.getElementById('roll-request-title').textContent = message.title || 'Roll';
    document.getElementById('roll-request-formula').textContent = message.formula || '';
    
    // Build config fields from message.config
    const configContainer = document.getElementById('roll-config-fields');
    configContainer.innerHTML = '';
    
    if (message.config) {
        for (const [name, fieldData] of Object.entries(message.config)) {
            if (name === 'Roll.0.situational') continue; // Already have this field
            
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'config-field';
            
            if (fieldData.type === 'select' && fieldData.options) {
                // Dropdown field
                fieldDiv.innerHTML = `
                    <label for="config-${name}">${fieldData.label || name}</label>
                    <select id="config-${name}" name="${name}">
                        ${fieldData.options.map(opt => 
                            `<option value="${opt.value}" ${opt.selected ? 'selected' : ''}>${opt.label}</option>`
                        ).join('')}
                    </select>
                `;
            } else {
                // Text field
                fieldDiv.innerHTML = `
                    <label for="config-${name}">${fieldData.label || name}</label>
                    <input type="text" id="config-${name}" name="${name}" value="${fieldData.value || ''}">
                `;
            }
            
            configContainer.appendChild(fieldDiv);
        }
    }
    
    // Build action buttons from message.buttons
    const buttonsContainer = document.getElementById('roll-action-buttons');
    buttonsContainer.innerHTML = '';
    
    const buttons = message.buttons || ['normal'];
    buttons.forEach(btn => {
        const button = document.createElement('button');
        button.className = 'action-btn';
        button.dataset.action = btn.toLowerCase();
        button.textContent = btn.charAt(0).toUpperCase() + btn.slice(1);
        button.addEventListener('click', () => handleButtonClick(btn));
        buttonsContainer.appendChild(button);
    });
    
    // Show roll request state
    updateRollWindow('rollRequest');
}
```

### Button Click Handler (Phase A - Send to DLC)
```javascript
function handleButtonClick(buttonName) {
    // Collect config values from form
    const configChanges = {};
    const inputs = document.querySelectorAll('#roll-window-request input, #roll-window-request select');
    inputs.forEach(input => {
        if (input.name && input.value) {
            configChanges[input.name] = input.value;
        }
    });
    
    // Send buttonSelect to DLC
    sendMessage({
        type: 'buttonSelect',
        id: state.currentRollRequest?.id,
        button: buttonName.toLowerCase(),
        configChanges: configChanges
    });
    
    state.selectedButton = buttonName;
    // Don't change state yet - wait for diceRequest from DLC
}
```

### Dice Request Handler (Phase B - Entry)
```javascript
function handleDiceRequest(message) {
    state.currentDiceRequest = message;
    state.enteredDiceValues = [];
    
    // Show roll type
    document.getElementById('dice-entry-roll-type').textContent = 
        message.rollType ? message.rollType.charAt(0).toUpperCase() + message.rollType.slice(1) : 'Normal';
    
    // Build dice entry UI
    const container = document.getElementById('dice-to-roll');
    container.innerHTML = '';
    
    const dice = message.dice || [];
    dice.forEach((die, groupIndex) => {
        // Each die entry: { type: "d20", count: 2 }
        for (let i = 0; i < (die.count || 1); i++) {
            const dieIndex = state.enteredDiceValues.length;
            state.enteredDiceValues.push(null); // Placeholder
            
            const dieDiv = document.createElement('div');
            dieDiv.className = 'die-entry';
            dieDiv.dataset.index = dieIndex;
            dieDiv.dataset.type = die.type;
            
            // Get max value for this die type
            const maxValue = getDieMaxValue(die.type);
            
            dieDiv.innerHTML = `
                <img src="/static/DLC Dice/${die.type.toUpperCase()}.svg" alt="${die.type}" class="die-svg">
                <input type="number" 
                       class="die-value-input" 
                       min="1" 
                       max="${maxValue}" 
                       placeholder="1-${maxValue}"
                       data-index="${dieIndex}"
                       data-type="${die.type}">
                <span class="die-range">(1-${maxValue})</span>
            `;
            
            container.appendChild(dieDiv);
        }
    });
    
    // Add input listeners
    container.querySelectorAll('.die-value-input').forEach(input => {
        input.addEventListener('input', handleDieValueInput);
    });
    
    // Disable submit until all values entered
    document.getElementById('dice-entry-submit').disabled = true;
    
    // Show dice entry state
    updateRollWindow('diceEntry');
}

function getDieMaxValue(dieType) {
    const maxValues = {
        'd4': 4, 'd6': 6, 'd8': 8, 'd10': 10,
        'd12': 12, 'd20': 20, 'd100': 100
    };
    return maxValues[dieType.toLowerCase()] || 20;
}

function handleDieValueInput(event) {
    const input = event.target;
    const index = parseInt(input.dataset.index);
    const value = parseInt(input.value);
    const max = parseInt(input.max);
    
    // Validate and store
    if (value >= 1 && value <= max) {
        state.enteredDiceValues[index] = {
            type: input.dataset.type,
            value: value
        };
        input.classList.remove('invalid');
        input.classList.add('valid');
    } else {
        state.enteredDiceValues[index] = null;
        input.classList.remove('valid');
        input.classList.add('invalid');
    }
    
    // Enable submit if all values entered
    const allFilled = state.enteredDiceValues.every(v => v !== null);
    document.getElementById('dice-entry-submit').disabled = !allFilled;
}
```

### Submit Results (Phase B - Send to DLC)
```javascript
function handleDiceEntrySubmit() {
    if (state.enteredDiceValues.some(v => v === null)) {
        return; // Not all values entered
    }
    
    // Send diceResult to DLC
    sendMessage({
        type: 'diceResult',
        originalRollId: state.currentDiceRequest?.originalRollId || state.currentRollRequest?.id,
        results: state.enteredDiceValues
    });
    
    // Return to idle
    resetRollWindow();
}

function resetRollWindow() {
    state.currentRollRequest = null;
    state.currentDiceRequest = null;
    state.enteredDiceValues = [];
    state.selectedButton = null;
    updateRollWindow('idle');
}
```

### Cancel Handler
```javascript
function handleRollCancel() {
    sendMessage({
        type: 'rollCancelled',
        id: state.currentRollRequest?.id || state.currentDiceRequest?.originalRollId
    });
    resetRollWindow();
}
```

### Event Listeners (add to DOMContentLoaded)
```javascript
document.getElementById('roll-request-cancel').addEventListener('click', handleRollCancel);
document.getElementById('dice-entry-submit').addEventListener('click', handleDiceEntrySubmit);
document.getElementById('dice-entry-back').addEventListener('click', () => {
    // Go back to roll request if we have one
    if (state.currentRollRequest) {
        updateRollWindow('rollRequest');
    } else {
        resetRollWindow();
    }
});
```

---

## CSS Styling (add to style.css)

```css
/* Roll Window - Always visible */
.roll-window {
    background: var(--panel-bg, #1a1a2e);
    border-radius: 8px;
    padding: 16px;
    margin: 16px;
    min-height: 300px;
}

.roll-window-state {
    animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

/* Dice Tray (Idle State) */
.dice-tray {
    text-align: center;
}

.dice-tray-dice {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
    margin-bottom: 16px;
}

.dice-btn {
    background: var(--btn-bg, #2a2a4a);
    border: 2px solid transparent;
    border-radius: 8px;
    padding: 8px;
    cursor: pointer;
    transition: all 0.2s;
}

.dice-btn:hover {
    border-color: var(--accent, #4a9eff);
    transform: scale(1.05);
}

.dice-btn img {
    width: 40px;
    height: 40px;
}

.dice-tray-controls {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
}

.modifier-btn {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: none;
    background: var(--btn-bg, #2a2a4a);
    color: white;
    font-size: 18px;
    cursor: pointer;
}

.modifier-display {
    font-size: 18px;
    min-width: 40px;
}

.dice-tray-actions {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-bottom: 16px;
}

.roll-type-btn {
    padding: 8px 16px;
    border: 2px solid var(--border, #3a3a5a);
    border-radius: 4px;
    background: transparent;
    color: white;
    cursor: pointer;
}

.roll-type-btn.active {
    background: var(--accent, #4a9eff);
    border-color: var(--accent, #4a9eff);
}

.dice-tray-roll-btn {
    padding: 12px 32px;
    background: var(--accent, #4a9eff);
    border: none;
    border-radius: 4px;
    color: white;
    font-size: 16px;
    cursor: pointer;
}

.idle-message {
    margin-top: 16px;
    color: var(--text-muted, #888);
    font-style: italic;
}

/* Roll Request (Config State) */
.roll-request {
    text-align: center;
}

.roll-title {
    margin: 0 0 8px 0;
    font-size: 20px;
}

.roll-formula {
    color: var(--text-muted, #888);
    margin-bottom: 16px;
}

.roll-config {
    text-align: left;
    margin-bottom: 16px;
}

.config-field {
    margin-bottom: 12px;
}

.config-field label {
    display: block;
    margin-bottom: 4px;
    font-size: 14px;
    color: var(--text-muted, #888);
}

.config-field input,
.config-field select {
    width: 100%;
    padding: 8px;
    border: 1px solid var(--border, #3a3a5a);
    border-radius: 4px;
    background: var(--input-bg, #2a2a4a);
    color: white;
}

.roll-actions {
    display: flex;
    justify-content: center;
    gap: 8px;
    margin-bottom: 16px;
}

.action-btn {
    padding: 12px 24px;
    background: var(--btn-bg, #2a2a4a);
    border: 2px solid var(--border, #3a3a5a);
    border-radius: 4px;
    color: white;
    cursor: pointer;
    transition: all 0.2s;
}

.action-btn:hover {
    background: var(--accent, #4a9eff);
    border-color: var(--accent, #4a9eff);
}

.cancel-btn {
    padding: 8px 16px;
    background: var(--danger, #ff4a4a);
    border: none;
    border-radius: 4px;
    color: white;
    cursor: pointer;
}

/* Dice Entry (Resolution State) */
.dice-entry {
    text-align: center;
}

.entry-title {
    margin: 0 0 8px 0;
}

.entry-roll-type {
    color: var(--accent, #4a9eff);
    margin-bottom: 8px;
}

.entry-instruction {
    color: var(--text-muted, #888);
    margin-bottom: 16px;
}

.dice-to-roll {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 16px;
    margin-bottom: 16px;
}

.die-entry {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
}

.die-svg {
    width: 48px;
    height: 48px;
}

.die-value-input {
    width: 80px;
    padding: 8px;
    text-align: center;
    border: 2px solid var(--border, #3a3a5a);
    border-radius: 4px;
    background: var(--input-bg, #2a2a4a);
    color: white;
    font-size: 18px;
}

.die-value-input.valid {
    border-color: var(--success, #4aff4a);
}

.die-value-input.invalid {
    border-color: var(--danger, #ff4a4a);
}

.die-range {
    font-size: 12px;
    color: var(--text-muted, #888);
}

.entry-actions {
    display: flex;
    justify-content: center;
    gap: 12px;
}

.submit-btn {
    padding: 12px 32px;
    background: var(--success, #4aff4a);
    border: none;
    border-radius: 4px;
    color: black;
    font-size: 16px;
    cursor: pointer;
}

.submit-btn:disabled {
    background: var(--btn-bg, #2a2a4a);
    color: var(--text-muted, #888);
    cursor: not-allowed;
}

.back-btn {
    padding: 12px 24px;
    background: var(--btn-bg, #2a2a4a);
    border: 2px solid var(--border, #3a3a5a);
    border-radius: 4px;
    color: white;
    cursor: pointer;
}
```

---

## Message Flow Summary

```
DLC                                    DLA
 |                                      |
 |-------- rollRequest --------------->|  (Phase A: Show config)
 |                                      |  User clicks button
 |<------- buttonSelect ---------------|
 |                                      |
 |  (Foundry processes, determines dice)|
 |                                      |
 |-------- diceRequest --------------->|  (Phase B: Show entry)
 |                                      |  User enters values
 |<------- diceResult -----------------|
 |                                      |
 |  (Foundry completes roll)           |  (Returns to idle)
```

---

## Testing Checklist

1. **Idle state displays** when app loads
2. **Roll Request state** appears when DLC sends `rollRequest`
3. **Config fields** populate from message data
4. **Button click** sends `buttonSelect` with config changes
5. **Dice Entry state** appears when DLC sends `diceRequest`
6. **Correct dice count** shown (e.g., 2d20 for advantage)
7. **Value validation** works (1-max for each die type)
8. **Submit enabled** only when all values entered
9. **Submit sends** correct `diceResult` format
10. **Cancel** sends `rollCancelled` and returns to idle
11. **Back button** returns to roll request state
