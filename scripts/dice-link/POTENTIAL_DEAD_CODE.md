# Potential Dead Code - CSS Changes

## Status
These CSS changes were made while debugging the missing header-actions (settings button, connection status) and footer (version number) issue. **NONE of these fixes resolved the problem.** They should be removed once the actual root cause is identified and fixed.

## CSS Changes Made (in style-simple.css)

### 1. .app-container
**Added:**
- `display: flex`
- `flex-direction: column`

**Reason:** Attempted to fix flexbox layout for header/footer/main-content positioning.
**Result:** Did not fix the issue.

---

### 2. .app-header
**Added:**
- `flex-shrink: 0`
- `width: 100%`

**Reason:** Attempted to prevent header from shrinking and ensure it spans full width.
**Result:** Did not fix the issue.

---

### 3. .app-footer
**Added:**
- `flex-shrink: 0`
- `width: 100%`

**Reason:** Attempted to prevent footer from shrinking and ensure it spans full width.
**Result:** Did not fix the issue.

---

### 4. .header-brand
**Added:**
- `flex-shrink: 0`

**Reason:** Attempted to prevent header-brand from expanding and pushing header-actions off-screen.
**Result:** Did not fix the issue.

---

### 5. .header-actions
**Added:**
- `flex-shrink: 0`
- `margin-left: auto`

**Reason:** Attempted to preserve header-actions size and push it to the right side of the header.
**Result:** Did not fix the issue.

---

### 6. .main-content
**Changed from:**
```css
width: 1400px;
height: calc(1500px - 60px - 40px);
position: relative;
```

**Changed to:**
```css
flex: 1;
position: relative;
overflow: hidden;
```

**Reason:** Attempted to allow main-content to fill available space between header and footer using flex layout.
**Result:** Did not fix the issue.

---

## Cache Busters Added
- Incremented CSS link in index.html from `?v=3` → `?v=6`
- These can be reset to `?v=1` or removed once real fix is found.

---

## Next Steps
1. Find the actual root cause of missing header-actions and footer
2. Once fixed, remove ALL of the above CSS changes
3. Re-test to ensure functionality remains intact
4. Delete this file
