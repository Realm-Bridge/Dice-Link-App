/**
 * Dice Entry/Resolution UI Module
 * Manages SVG dice face selection for entering roll results
 */

// Track selected values for each die row
let diceEntryValues = [];

/**
 * Render dice entry HTML for the Dice Entry state
 */
function renderDiceEntry(diceRequest) {
  const { dice } = diceRequest;
  
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
        <p class="dice-entry-formula">${dice.length} dice to enter</p>
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

/**
 * Initialize dice entry click handlers for the current diceRequest
 */
function initDiceEntry(diceRequest) {
  debugLog('Initializing dice entry');
  
  // Reset values array
  diceEntryValues = new Array(diceRequest.dice.length).fill(null);
  
  // Click handlers for die options (SVG dice faces)
  document.querySelectorAll('.die-option').forEach(btn => {
    btn.addEventListener('click', () => {
      const row = parseInt(btn.dataset.row);
      const value = parseInt(btn.dataset.value);
      
      debugLog(`Die option clicked: row=${row}, value=${value}`);
      
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
        debugLog(`Manual input: row=${row}, value=${value}`);
        diceEntryValues[row] = value;
      } else {
        debugLog(`Invalid d100 value: ${value}`);
      }
    });
  });
  
  // Submit button
  document.querySelector('.submit-dice-btn')?.addEventListener('click', () => {
    // Check all dice have values
    const allFilled = diceEntryValues.every(v => v !== null && v !== undefined);
    if (!allFilled) {
      debugError('Not all dice values filled', diceEntryValues);
      return;
    }
    
    debugLog('Submitting dice results');
    
    // Build results array
    const results = diceEntryValues.map((value, index) => ({
      type: diceRequest.dice[index].type,
      value: value
    }));
    
    debugLog('Dice results to send', results);
    
    // Send to DLC
    sendMessage({
      type: 'diceResult',
      originalRollId: diceRequest.originalRollId,
      results: results
    });
    
    // Return to idle state
    resetRollState();
    diceEntryValues = [];
    updateRollWindow('idle');
  });
}

/**
 * Clear dice entry values (for reset)
 */
function clearDiceEntryValues() {
  diceEntryValues = [];
}
