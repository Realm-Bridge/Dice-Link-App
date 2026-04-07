/**
 * Dice Tray UI Module
 * Handles idle state dice tray: formula input, dice buttons, modifier, ADV/DIS, Roll
 */

/**
 * Initialize dice tray event listeners
 */
function initDiceTray() {
  debugLog('Initializing Dice Tray');

  // Dice button left-click: add one die
  document.querySelectorAll('.dice-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const die = parseInt(btn.dataset.die);
      updateDiceTrayDie(die, getDiceTrayState().dice[die] + 1);
      updateDiceTrayDisplay();
    });

    // Dice button right-click: subtract one die
    btn.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      const die = parseInt(btn.dataset.die);
      const current = getDiceTrayState().dice[die];
      if (current > 0) {
        updateDiceTrayDie(die, current - 1);
        updateDiceTrayDisplay();
      }
    });
  });

  // Modifier minus button
  const minusBtn = document.getElementById('dice-modifier-minus');
  if (minusBtn) {
    minusBtn.addEventListener('click', () => {
      const current = getDiceTrayState().modifier;
      updateDiceTrayModifier(current - 1);
      updateDiceTrayDisplay();
    });
  }

  // Modifier plus button
  const plusBtn = document.getElementById('dice-modifier-plus');
  if (plusBtn) {
    plusBtn.addEventListener('click', () => {
      const current = getDiceTrayState().modifier;
      updateDiceTrayModifier(current + 1);
      updateDiceTrayDisplay();
    });
  }

  // ADV/DIS toggle (cycles: normal -> advantage -> disadvantage -> normal)
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
      debugLog(`ADV/DIS mode: ${next}`);
    });
  }

  // Roll button
  const rollBtn = document.getElementById('dice-roll-btn');
  if (rollBtn) {
    rollBtn.addEventListener('click', () => {
      const formula = buildDiceFormula();
      if (!formula) {
        debugLog('No dice selected, nothing to roll');
        return;
      }
      const advMode = getDiceTrayState().advMode;
      debugLog(`Rolling formula: ${formula}, advMode: ${advMode}`);
      sendMessage({
        type: 'manualRoll',
        formula: formula,
        advMode: advMode
      });
      // Reset tray after sending
      resetDiceTray();
      updateDiceTrayDisplay();
    });
  }

  // Set initial display
  updateDiceTrayDisplay();
}

/**
 * Build dice formula string from current tray state
 * @returns {string} Formula string e.g. "2d20+1d6" or empty string
 */
function buildDiceFormula() {
  const { dice, modifier } = getDiceTrayState();
  const parts = [];

  for (const die of DICE_ORDER) {
    const count = dice[die];
    if (count > 0) {
      parts.push(`${count}d${die}`);
    }
  }

  if (modifier !== 0) {
    parts.push(modifier > 0 ? `+${modifier}` : `${modifier}`);
  }

  return parts.join('+');
}

/**
 * Update dice tray display with current state
 */
function updateDiceTrayDisplay() {
  const { dice, modifier } = getDiceTrayState();

  // Update formula input
  const formulaInput = document.getElementById('dice-formula-input');
  if (formulaInput) {
    const formula = buildDiceFormula();
    formulaInput.value = formula ? `/r ${formula}` : '/r ';
  }

  // Update die count badges
  document.querySelectorAll('.dice-btn').forEach(btn => {
    const die = parseInt(btn.dataset.die);
    const count = dice[die] || 0;
    const badge = btn.querySelector('.die-count');
    if (badge) {
      badge.textContent = count;
      if (count > 0) {
        badge.classList.add('show');
        badge.style.display = 'flex';
      } else {
        badge.classList.remove('show');
        badge.style.display = 'none';
      }
    }
  });

  // Update modifier display
  const modDisplay = document.getElementById('dice-modifier-value');
  if (modDisplay) {
    modDisplay.textContent = modifier > 0 ? `+${modifier}` : `${modifier}`;
  }
}
