/**
 * Settings Panel UI Module
 * Manages settings loading, saving, and UI interactions
 */

/**
 * Load settings from localStorage and apply to UI
 */
function loadSettings() {
  debugLog('Loading settings');
  
  try {
    const saved = localStorage.getItem(STORAGE_KEYS.SETTINGS);
    if (saved) {
      const parsed = JSON.parse(saved);
      setSettings(parsed);
      debugLog('Settings loaded from storage');
    }
  } catch (error) {
    debugError('Failed to load settings', error);
  }
  
  // Apply settings to UI
  const settings = getSettings();
  
  const hostInput = document.getElementById('settings-host');
  const portInput = document.getElementById('settings-port');
  const themeSelect = document.getElementById('settings-theme');
  
  if (hostInput) hostInput.value = settings.host;
  if (portInput) portInput.value = settings.port;
  if (themeSelect) themeSelect.value = settings.theme;
  
  debugLog('Settings applied to UI');
}

/**
 * Save settings to localStorage and state
 */
function saveSettings() {
  debugLog('Saving settings');
  
  const hostInput = document.getElementById('settings-host');
  const portInput = document.getElementById('settings-port');
  const themeSelect = document.getElementById('settings-theme');
  
  const newSettings = {
    host: hostInput?.value || DEFAULT_SETTINGS.host,
    port: parseInt(portInput?.value) || DEFAULT_SETTINGS.port,
    theme: themeSelect?.value || DEFAULT_SETTINGS.theme
  };
  
  setSettings(newSettings);
  
  try {
    localStorage.setItem(STORAGE_KEYS.SETTINGS, JSON.stringify(newSettings));
    debugLog('Settings saved to storage');
  } catch (error) {
    debugError('Failed to save settings', error);
  }
  
  closeSettings();
}

/**
 * Open settings panel
 */
function openSettings() {
  debugLog('Opening settings panel');
  
  const elements = cacheElements();
  if (elements.settingsPanel) {
    elements.settingsPanel.classList.add('visible');
  }
  
  const overlay = document.getElementById('settings-overlay');
  if (overlay) {
    overlay.classList.add('visible');
  }
}

/**
 * Close settings panel
 */
function closeSettings() {
  debugLog('Closing settings panel');
  
  const elements = cacheElements();
  if (elements.settingsPanel) {
    elements.settingsPanel.classList.remove('visible');
  }
  
  const overlay = document.getElementById('settings-overlay');
  if (overlay) {
    overlay.classList.remove('visible');
  }
}

/**
 * Initialize settings UI event listeners
 */
function initSettingsUI() {
  debugLog('Initializing settings UI');
  
  const settingsBtn = document.getElementById('settings-btn');
  const settingsClose = document.getElementById('settings-close');
  const settingsSave = document.getElementById('settings-save');
  const settingsOverlay = document.getElementById('settings-overlay');
  
  if (settingsBtn) {
    settingsBtn.addEventListener('click', openSettings);
  }
  
  if (settingsClose) {
    settingsClose.addEventListener('click', closeSettings);
  }
  
  if (settingsSave) {
    settingsSave.addEventListener('click', saveSettings);
  }
  
  // Close settings when clicking outside the panel
  if (settingsOverlay) {
    settingsOverlay.addEventListener('click', (e) => {
      if (e.target === settingsOverlay) {
        closeSettings();
      }
    });
  }
}
