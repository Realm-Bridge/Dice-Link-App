/**
 * Roll Window UI Module
 * Manages the Roll Window states: idle, request, dice-entry
 */

/**
 * Cache Roll Window elements
 */
let rwElements = {};

/**
 * Initialize Roll Window event listeners and cache elements
 */
function initRollWindow() {
  debugLog('Initializing Roll Window');
  
  // Cache elements
  rwElements = {
    rollWindow: document.getElementById('roll-window'),
    idleState: document.getElementById('roll-window-idle'),
    requestState: document.getElementById('roll-window-request'),
    diceEntryState: document.getElementById('roll-window-dice-entry'),
    rwTitle: document.getElementById('rw-title'),
    rwSubtitle: document.getElementById('rw-subtitle'),
    rwConfigSection: document.getElementById('rw-config-section'),
    rwButtons: document.getElementById('rw-action-buttons'),
    rwDiceInputs: document.getElementById('rw-dice-inputs'),
    cancelBtn: document.getElementById('rw-cancel-btn'),
    // Also cache footer cancel button as fallback
    footerCancelBtn: document.getElementById('cancel-roll')
  };
  
  // Cancel button in Roll Window
  if (rwElements.cancelBtn) {
    rwElements.cancelBtn.addEventListener('click', cancelRoll);
  }
  
  // Footer cancel button (legacy)
  if (rwElements.footerCancelBtn) {
    rwElements.footerCancelBtn.addEventListener('click', cancelRoll);
  }
}

/**
 * Update Roll Window state (idle, request, dice-entry)
 */
function updateRollWindow(newState) {
  debugLog(`updateRollWindow: ${newState}`);
  
  if (!rwElements.idleState || !rwElements.requestState || !rwElements.diceEntryState) {
    debugError('Roll Window elements not cached');
    return;
  }
  
  // Hide all states
  rwElements.idleState.classList.remove('active');
  rwElements.requestState.classList.remove('active');
  rwElements.diceEntryState.classList.remove('active');
  
  // Show requested state
  switch(newState) {
    case 'idle':
      rwElements.idleState.classList.add('active');
      break;
    case 'request':
      rwElements.requestState.classList.add('active');
      break;
    case 'dice-entry':
      rwElements.diceEntryState.classList.add('active');
      break;
    default:
      debugLog(`Unknown Roll Window state: ${newState}`);
  }
}

/**
 * Render roll request with action buttons
 */
function renderRWActionButtons(buttons) {
  debugLog('renderRWActionButtons called', buttons);
  
  if (!rwElements.rwButtons) {
    debugError('rwButtons element not found');
    return;
  }
  
  rwElements.rwButtons.innerHTML = '';
  
  if (!buttons || buttons.length === 0) {
    debugLog('No action buttons to render');
    return;
  }
  
  buttons.forEach(btn => {
    const button = document.createElement('button');
    button.className = 'rw-action-btn';
    button.dataset.actionId = btn.id;
    button.textContent = btn.label;
    button.addEventListener('click', () => selectActionButton(btn.id));
    rwElements.rwButtons.appendChild(button);
  });
}

/**
 * Map button IDs from DLC to Foundry-expected values
 * DLC may send "critical" but Foundry expects "critical hit"
 */
function mapButtonId(buttonId) {
  const buttonMap = {
    'critical': 'critical hit',  // Damage rolls
    'crit': 'critical hit',
    'normal': 'normal',
    'advantage': 'advantage',
    'adv': 'advantage',
    'disadvantage': 'disadvantage',
    'dis': 'disadvantage'
  };
  
  return buttonMap[buttonId] || buttonId;
}

/**
 * Handle action button selection
 */
function selectActionButton(actionId) {
  debugLog(`Action button selected: ${actionId}`);
  
  const currentRoll = getCurrentRoll();
  if (!currentRoll) {
    debugError('No current roll');
    return;
  }
  
  // Map button ID to Foundry-expected value
  const mappedActionId = mapButtonId(actionId);
  debugLog(`Mapped button ID: ${actionId} -> ${mappedActionId}`);
  
  setSelectedButton(mappedActionId);
  
  // Collect config values from Roll Window
  const configChanges = {};
  
  if (rwElements.rwConfigSection) {
    rwElements.rwConfigSection.querySelectorAll('select, input').forEach(input => {
      const fieldName = input.dataset.field;
      if (fieldName) {
        configChanges[fieldName] = input.value;
      }
    });
  }
  
  // Send button selection to DLC (use mapped ID)
  sendMessage({
    type: 'buttonSelect',
    rollId: currentRoll.id,
    button: mappedActionId,
    configChanges: configChanges
  });
  
  debugLog('Button selection sent to DLC');
}

/**
 * Render config fields from roll request
 */
function renderRWConfigFields(fields) {
  debugLog('renderRWConfigFields called', fields);
  
  if (!rwElements.rwConfigSection) {
    debugError('rwConfigSection not found');
    return;
  }
  
  rwElements.rwConfigSection.innerHTML = '';
  
  if (!fields || fields.length === 0) {
    return;
  }
  
  fields.forEach(field => {
    const fieldDiv = document.createElement('div');
    fieldDiv.className = 'rw-config-field';
    
    const label = document.createElement('label');
    label.htmlFor = `rw-${field.name}`;
    label.textContent = field.label || field.name;
    fieldDiv.appendChild(label);
    
    let input;
    
    if (field.type === 'text') {
      input = document.createElement('input');
      input.type = 'text';
      input.id = `rw-${field.name}`;
      input.dataset.field = field.name;
      input.value = field.value || '';
    } else if (field.type === 'select' && field.options) {
      input = document.createElement('select');
      field.options.forEach(opt => {
        const option = document.createElement('option');
        const optValue = typeof opt === 'object' ? opt.value : opt;
        const optLabel = typeof opt === 'object' ? opt.label : opt;
        option.value = optValue;
        option.textContent = optLabel;
        if (optValue === field.selected) option.selected = true;
        input.appendChild(option);
      });
      input.id = `rw-${field.name}`;
      input.dataset.field = field.name;
    }
    
    if (input) {
      fieldDiv.appendChild(input);
    }
    
    rwElements.rwConfigSection.appendChild(fieldDiv);
  });
}

/**
 * Cancel the current roll
 */
function cancelRoll() {
  debugLog('Cancel roll clicked');
  
  const rollId = getCurrentRoll()?.id || getPendingDiceRequest()?.originalRollId;
  
  if (!rollId) {
    debugLog('No active roll to cancel');
    return;
  }
  
  // Clear state immediately
  resetRollState();
  updateRollWindow('idle');
  
  // Hide cancel button
  if (rwElements.cancelBtn) {
    rwElements.cancelBtn.classList.add('hidden');
  }
  
  // Check if this is a test roll
  const isTestRoll = rollId.startsWith('test-');
  
  if (!isTestRoll) {
    // Send cancel message to server
    sendMessage({
      type: 'rollCancelled',
      id: rollId,
      reason: 'User cancelled'
    });
  }
}

/**
 * Update Roll Window Submit button state
 */
function updateRWSubmitButton() {
  // This is handled in dice-entry.js for validation
  // Kept here for future use if needed
}

/**
 * Update Roll Window for request state
 */
function renderRWRequest(rollData) {
  debugLog('Rendering Roll Window request state', rollData);
  
  // Unwrap nested data structure if present
  // DLC sends { type: "rollRequest", data: { roll: {...}, config: {...}, buttons: [...] } }
  const data = rollData.data || rollData;
  
  // Make sure elements are cached
  if (!rwElements.rwTitle) {
    rwElements.rwTitle = document.getElementById('rw-title');
  }
  if (!rwElements.rwSubtitle) {
    rwElements.rwSubtitle = document.getElementById('rw-subtitle');
  }
  if (!rwElements.rwConfigSection) {
    rwElements.rwConfigSection = document.getElementById('rw-config-section');
  }
  if (!rwElements.rwButtons) {
    rwElements.rwButtons = document.getElementById('rw-action-buttons');
  }
  
  if (!rwElements.rwTitle || !rwElements.rwSubtitle) {
    debugError('Roll Window title/subtitle elements not found');
    return;
  }
  
  // Set title and subtitle from roll data
  const title = data.roll?.title || data.title || 'Roll Request';
  const subtitle = data.roll?.subtitle || data.roll?.formula || data.subtitle || '';
  
  rwElements.rwTitle.textContent = title;
  rwElements.rwSubtitle.textContent = subtitle;
  
  // Render config fields - DLC sends config.fields array
  if (data.config && data.config.fields) {
    renderRWConfigFields(data.config.fields);
  }
  
  // Render action buttons
  if (data.buttons) {
    renderRWActionButtons(data.buttons);
  }
  
  // Show cancel button
  if (rwElements.cancelBtn) {
    rwElements.cancelBtn.classList.remove('hidden');
  }
}
