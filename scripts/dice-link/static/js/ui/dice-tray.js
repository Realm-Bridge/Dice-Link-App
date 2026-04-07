/**
 * Dice Tray UI Module
 * Manages the idle state with dice selection, modifiers, and quick roll
 */

/**
 * Initialize dice tray event listeners
 */
function initDiceTray() {
  debugLog('Initializing dice tray');
  
  // Dice button left-click - add one die to formula
  document.querySelectorAll('.dice-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const die = parseInt(btn.dataset.die);
      updateDiceTrayDie(die, getDiceTrayState().dice[die] + 1);
      updateDiceTrayDisplay();
    });
    
    // Dice button right-click - subtract one die from formula
    btn.addEventListener('contextmenu', (e) => {
      e.preventDefault(); // Prevent browser context menu
      const die = parseInt(btn.dataset.die);
      const currentCount = getDiceTrayState().dice[die];
      if (currentCount > 0) {
        updateDiceTrayDie(die, currentCount - 1);
        updateDiceTrayDisplay();
      }
    });
  });
  
  // Modifier buttons
  document.getElementById('dice-modifier-minus')?.addEventListener('click', () => {
    const currentMod = getDiceTrayState().modifier;
    updateDiceTrayModifier(currentMod - 1);
    updateDiceTrayDisplay();
  });
  
  document.getElementById('dice-modifier-plus')?.addEventListener('click', () => {
    const currentMod = getDiceTrayState().modifier;
    updateDiceTrayModifier(currentMod + 1);
    updateDiceTrayDisplay();
  });
  
  // ADV/DIS toggle (cycles: normal -> advantage -> disadvantage -> normal)
  document.querySelector('.dice-adv-btn')?.addEventListener('click', (e) => {
    const btn = e.currentTarget;
    const currentMode = getDiceTrayState().advMode;
    let newMode;
    
    if (currentMode === 'normal') {
      newMode = 'advantage';
      btn.classList.add('adv-active');
      btn.classList.remove('dis-active');
    } else if (currentMode === 'advantage') {
      newMode = 'disadvantage';
      btn.classList.remove('adv-active');
      btn.classList.add('dis-active');
    } else {
      newMode = 'normal';
      btn.classList.remove('adv-active', 'dis-active');
    }
    
    updateDiceTrayAdvMode(newMode);
    debugLog(`ADV/DIS mode changed to: ${newMode}`);
  });
  
  // Roll button
  document.getElementById('dice-roll-btn')?.addEventListener('click', () => {
    const formula = buildDiceFormula();
    if (formula) {
      debugLog(`Rolling manual formula: ${formula}`);
      
      // Send roll command to DLC
      sendMessage({
        type: 'manualRoll',
        formula: formula,
        advMode: getDiceTrayState().advMode
      });
      
      // Reset tray
      resetDiceTrayUI();
    } else {
      debugLog('Cannot roll: no dice selected');
    }
  });
}

/**
 * Update dice tray display with current state
 */
function updateDiceTrayDisplay() {
  const state = getDiceTrayState();
  
  // Update formula input
  const formula = buildDiceFormula();
  const input = document.getElementById('dice-formula-input');
  if (input) {
    input.value = formula ? `/r ${formula}` : '/r ';
  }
  
  // Update die count badges
  document.querySelectorAll('.dice-btn').forEach(btn => {
    const die = parseInt(btn.dataset.die);
    const count = state.dice[die];
    const badge = btn.querySelector('.die-count');
    
    if (badge) {
      badge.textContent = count;
      if (count > 0) {
        badge.classList.add('show');
      } else {
        badge.classList.remove('show');
      }
    }
  });
  
  // Update modifier display
  const modDisplay = document.getElementById('dice-modifier-value');
  if (modDisplay) {
    const mod = state.modifier;
    modDisplay.textContent = mod >= 0 ? `+${mod}` : mod.toString();
  }
}

/**
 * Build dice formula from current state
 */
function buildDiceFormula() {
  const state = getDiceTrayState();
  const parts = [];
  
  // Add dice in order
  for (const die of DICE_ORDER) {
    const count = state.dice[die];
    if (count > 0) {
      parts.push(`${count}d${die}`);
    }
  }
  
  // Add modifier
  if (state.modifier !== 0) {
    if (state.modifier > 0) {
      parts.push(`+${state.modifier}`);
    } else {
      parts.push(`${state.modifier}`);
    }
  }
  
  return parts.join(' ');
}

/**
 * Reset dice tray UI and state
 */
function resetDiceTrayUI() {
  resetDiceTray();
  
  // Reset UI elements
  document.querySelector('.dice-adv-btn')?.classList.remove('adv-active', 'dis-active');
  updateDiceTrayDisplay();
  
  debugLog('Dice tray reset');
}
