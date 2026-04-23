/**
 * Dice Entry/Resolution UI Module
 * Manages SVG dice face selection for entering roll results
 */

// Track selected values for each die row
let diceEntryValues = [];

/**
 * Render dice entry HTML for the Dice Entry state
 * Respects the `count` property to create multiple rows per die type
 */
function renderDiceEntry(diceRequest) {
  const { dice } = diceRequest;
  
  // Build dice rows - create one row PER die, not per die type
  // e.g., { type: "d20", count: 2 } creates 2 separate rows
  const diceRows = [];
  let rowIndex = 0;
  let totalDiceCount = 0;
  
  for (const dieInfo of dice) {
    const dieType = dieInfo.type.toLowerCase(); // e.g., "d20"
    const faces = parseInt(dieType.replace('d', '')); // e.g., 20
    const count = dieInfo.count || 1; // Default to 1 if not specified
    
    totalDiceCount += count;
    
    // Create one row for each die in the count
    for (let c = 0; c < count; c++) {
      // For d100, use text input (100 buttons is impractical)
      if (faces === 100) {
        diceRows.push(`
          <div class="dice-row dice-row-manual" data-row="${rowIndex}" data-faces="${faces}" data-type="${dieType}">
            <span class="dice-row-label">${dieType.toUpperCase()}</span>
            <input type="number" 
                   class="dice-manual-input" 
                   data-row="${rowIndex}"
                   data-faces="${faces}"
                   data-type="${dieType}"
                   min="1" max="100" 
                   placeholder="1-100">
          </div>
        `);
        rowIndex++;
        continue;
      }
      
      // For other dice, show clickable SVG buttons for each face value
      const diceOptions = [];
      for (let value = 1; value <= faces; value++) {
        const svgPath = `/static/DLC Dice/${dieType.toUpperCase()}/${dieType} - Outline ${value}.svg`;
        diceOptions.push(`
          <button type="button" 
                  class="die-option" 
                  data-row="${rowIndex}" 
                  data-value="${value}" 
                  data-faces="${faces}"
                  data-type="${dieType}"
                  title="${dieType}: ${value}">
            <div class="die-face">
              <img src="${svgPath}" alt="${dieType} ${value}" class="die-image">
            </div>
          </button>
        `);
      }
      
      diceRows.push(`
        <div class="dice-row" data-row="${rowIndex}" data-faces="${faces}" data-type="${dieType}">
          <div class="dice-options">
            ${diceOptions.join('')}
          </div>
        </div>
      `);
      rowIndex++;
    }
  }
  
  return `
    <div class="dice-entry">
      <div class="dice-entry-header">
        <p class="dice-entry-instruction">${totalDiceCount === 1 ? 'Select one value' : 'Select one value from each row'}</p>
      </div>
      <div class="dice-rows">
        ${diceRows.join('')}
      </div>
      <div class="dice-entry-actions">
        <button type="button" class="cancel-dice-btn btn btn-danger">CANCEL</button>
        <button type="button" class="submit-dice-btn btn btn-success">SUBMIT</button>
      </div>
    </div>
  `;
}

/**
 * Initialize dice entry click handlers for the current diceRequest
 * Stores metadata for each row to correctly build results
 */
function initDiceEntry(diceRequest) {
  debugLog('Initializing dice entry');
  
  // Calculate total rows needed (sum of all counts)
  let totalRows = 0;
  const rowMetadata = []; // Track die type for each row
  
  for (const die of diceRequest.dice) {
    const count = die.count || 1;
    for (let c = 0; c < count; c++) {
      rowMetadata.push({ type: die.type });
      totalRows++;
    }
  }
  
  // Reset values array with correct size
  diceEntryValues = new Array(totalRows).fill(null);
  
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
    
    // Build results array using row metadata for correct types
    const results = diceEntryValues.map((value, index) => ({
      type: rowMetadata[index].type,
      value: value
    }));
    
    debugLog('Dice results to send', results);
    
    // Send to DLA via bridge
    sendToDLA({
      type: 'diceResult',
      id: diceRequest.id,
      results: results
    });
    
    // Return to idle state
    resetRollState();
    diceEntryValues = [];
    updateRollWindow('idle');
  });
  
  // Cancel button
  document.querySelector('.cancel-dice-btn')?.addEventListener('click', () => {
    debugLog('Cancel button clicked in dice entry');
    cancelRoll();
  });
}

/**
 * Clear dice entry values (for reset)
 */
function clearDiceEntryValues() {
  diceEntryValues = [];
}
