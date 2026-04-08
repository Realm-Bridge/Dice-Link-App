/**
 * Dice Tray UI Module
 * Handles idle state dice tray: formula input, dice buttons, modifier, ADV/DIS, Roll
 */

/**
 * Initialize dice tray event listeners
 */
function initDiceTray() {
  debugLog('Initializing Dice Tray');

  // Formula input - allow manual typing and submit on Enter
  const formulaInput = document.getElementById('dice-formula-input');
  if (formulaInput) {
    // Submit formula on Enter key by triggering the Roll button
    formulaInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const rollBtn = document.getElementById('dice-roll-btn');
        if (rollBtn) {
          rollBtn.click();
        }
      }
    });
  }

  // Dice button left-click: add one die
  document.querySelectorAll('.dice-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const die = parseInt(btn.dataset.die);
      updateDiceTrayDie(die, (getDiceTrayState().dice[die] || 0) + 1);
      updateDiceTrayBadge(btn, die);
      rebuildFormula();
    });

    // Dice button right-click: subtract one die
    btn.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      const die = parseInt(btn.dataset.die);
      const current = getDiceTrayState().dice[die] || 0;
      if (current > 0) {
        updateDiceTrayDie(die, current - 1);
        updateDiceTrayBadge(btn, die);
        rebuildFormula();
      }
    });
  });

  // Modifier minus button
  const minusBtn = document.getElementById('dice-modifier-minus');
  if (minusBtn) {
    minusBtn.addEventListener('click', () => {
      updateDiceTrayModifier(getDiceTrayState().modifier - 1);
      updateModifierDisplay();
      rebuildFormula();
    });
  }

  // Modifier plus button
  const plusBtn = document.getElementById('dice-modifier-plus');
  if (plusBtn) {
    plusBtn.addEventListener('click', () => {
      updateDiceTrayModifier(getDiceTrayState().modifier + 1);
      updateModifierDisplay();
      rebuildFormula();
    });
  }

  // ADV/DIS toggle: normal -> advantage -> disadvantage -> normal
  const advBtn = document.querySelector('.dice-adv-btn');
  if (advBtn) {
    advBtn.addEventListener('click', () => {
      const current = getDiceTrayState().advMode;
      let next;
      if (current === 'normal') {
        next = 'advantage';
        advBtn.classList.add('adv-active');
        advBtn.classList.remove('dis-active');
        advBtn.textContent = 'ADV';
      } else if (current === 'advantage') {
        next = 'disadvantage';
        advBtn.classList.remove('adv-active');
        advBtn.classList.add('dis-active');
        advBtn.textContent = 'DIS';
      } else {
        next = 'normal';
        advBtn.classList.remove('adv-active', 'dis-active');
        advBtn.textContent = 'ADV/DIS';
      }
      updateDiceTrayAdvMode(next);
      rebuildFormula(); // Rebuilds formula with kh/kl on d20s
      debugLog(`ADV/DIS mode: ${next}`);
    });
  }

  // Roll button - always reads from the formula bar (single source of truth)
  const rollBtn = document.getElementById('dice-roll-btn');
  if (rollBtn) {
    rollBtn.addEventListener('click', () => {
      const formulaInput = document.getElementById('dice-formula-input');
      if (!formulaInput) {
        debugError('Formula input not found');
        return;
      }
      
      let formula = formulaInput.value.trim();
      
      // Strip /r or /roll prefix
      if (formula.toLowerCase().startsWith('/r ')) {
        formula = formula.substring(3).trim();
      } else if (formula.toLowerCase().startsWith('/r')) {
        formula = formula.substring(2).trim();
      } else if (formula.toLowerCase().startsWith('/roll ')) {
        formula = formula.substring(6).trim();
      } else if (formula.toLowerCase().startsWith('/roll')) {
        formula = formula.substring(5).trim();
      }
      
      if (!formula) {
        debugLog('No formula to roll');
        return;
      }
      
      debugLog(`Sending diceTrayRoll: ${formula}`);
      
      if (typeof sendMessage !== 'function') {
        debugError('sendMessage is not defined');
        return;
      }
      
      sendMessage({
        type: 'diceTrayRoll',
        formula: formula,
        flavor: 'Manual Dice Roll'
      });
      
      // Reset tray after sending
      resetDiceTrayUI();
    });
  }

  // Set initial display
  rebuildFormula();
}

/**
 * Build clean formula string from current tray state (no /r prefix).
 * Applies kh/kl to d20s for advantage/disadvantage per Foundry spec.
 * @returns {string} e.g. "2d20kh+1d6+3" or "" if nothing selected
 */
function buildDiceFormula() {
  const { dice, modifier, advMode } = getDiceTrayState();
  const parts = [];

  // Die order per spec: d20 first, then descending, d100 last
  const dieOrder = [20, 12, 10, 8, 6, 4, 100];

  for (const die of dieOrder) {
    const count = dice[die] || 0;
    if (count > 0) {
      let notation = `${count}d${die}`;
      // Apply advantage/disadvantage ONLY to d20s
      if (die === 20) {
        if (advMode === 'advantage') {
          notation = `${count}d20kh`;
        } else if (advMode === 'disadvantage') {
          notation = `${count}d20kl`;
        }
      }
      parts.push(notation);
    }
  }

  let formula = parts.join('+');

  if (modifier > 0) {
    formula += `+${modifier}`;
  } else if (modifier < 0) {
    formula += `${modifier}`;
  }

  return formula;
}

/**
 * Rebuild the formula input field from current state.
 * Called after every state change.
 */
function rebuildFormula() {
  const formulaInput = document.getElementById('dice-formula-input');
  if (!formulaInput) return;
  const formula = buildDiceFormula();
  formulaInput.value = formula ? `/r ${formula}` : '/r ';
}

/**
 * Update the count badge on a single dice button
 * @param {HTMLElement} btn - The dice button element
 * @param {number} die - Die type (4, 6, 8, etc.)
 */
function updateDiceTrayBadge(btn, die) {
  const count = getDiceTrayState().dice[die] || 0;
  const badge = btn.querySelector('.die-count');
  if (badge) {
    badge.textContent = count;
    if (count > 0) {
      badge.classList.add('visible');
      badge.style.display = 'flex';
    } else {
      badge.classList.remove('visible');
      badge.style.display = 'none';
    }
  }
}

/**
 * Update the modifier display element
 */
function updateModifierDisplay() {
  const modifier = getDiceTrayState().modifier;
  const modDisplay = document.getElementById('dice-modifier-value');
  if (modDisplay) {
    modDisplay.textContent = modifier > 0 ? `+${modifier}` : `${modifier}`;
  }
}

/**
 * Reset the dice tray state and refresh all UI elements.
 * Calls resetDiceTray() from state.js to clear data, then updates the DOM.
 */
function resetDiceTrayUI() {
  // Reset state data
  resetDiceTray();

  // Reset badge visuals
  document.querySelectorAll('.dice-btn').forEach(btn => {
    const die = parseInt(btn.dataset.die);
    updateDiceTrayBadge(btn, die);
  });

  // Reset modifier display
  updateModifierDisplay();

  // Reset ADV/DIS button
  const advBtn = document.querySelector('.dice-adv-btn');
  if (advBtn) {
    advBtn.classList.remove('adv-active', 'dis-active');
    advBtn.textContent = 'ADV/DIS';
  }

  // Reset formula
  rebuildFormula();
  debugLog('Dice tray reset');
}
