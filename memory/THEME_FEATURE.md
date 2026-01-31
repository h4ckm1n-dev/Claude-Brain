# Dark Mode Feature - Browser/System Based

## ✨ What's New

The memory dashboard now automatically respects your browser/system dark mode preference!

### Features

**🌓 Three Theme Modes:**
1. **Light** - Always light theme
2. **Dark** - Always dark theme
3. **System** (Default) - Follows your browser/OS preference

**⚡ Automatic Detection:**
- Detects `prefers-color-scheme` media query
- Listens for system preference changes in real-time
- No page reload needed when you change OS theme

**🚫 No Flash:**
- Theme applied before React loads
- Prevents flash of unstyled content (FOUC)
- Instant dark mode on page load

**💾 Persistent:**
- Choice saved to localStorage
- Remembers your preference across sessions
- Per-browser storage (not synced)

---

## 🎨 How to Use

### Via Settings Page

1. Open **http://localhost:5173/settings**
2. See "Appearance" card at the top
3. Click one of three options:
   - ☀️ **Light** - Force light mode
   - 🌙 **Dark** - Force dark mode
   - 🖥️ **System** - Follow OS preference (default)

### Via Browser DevTools

```javascript
// Check current theme
localStorage.getItem('theme')  // 'light', 'dark', or 'system'

// Set theme manually
localStorage.setItem('theme', 'dark')
window.location.reload()

// Check resolved theme (what's actually shown)
document.documentElement.classList.contains('dark')  // true/false
```

---

## 🔧 Technical Details

### Implementation

**1. Theme Hook (`useTheme.ts`):**
```typescript
const { theme, resolvedTheme, setTheme } = useTheme();

// theme: User preference ('light' | 'dark' | 'system')
// resolvedTheme: Actual theme shown ('light' | 'dark')
// setTheme: Change preference
```

**2. Auto-Detection:**
- Checks `window.matchMedia('(prefers-color-scheme: dark)')`
- Listens for OS theme changes via `change` event
- Updates immediately without reload

**3. FOUC Prevention:**
- Inline `<script>` in `index.html` runs before React
- Reads localStorage and applies `dark` class
- Zero flash, instant correct theme

**4. CSS Integration:**
- Uses Tailwind's `dark:` variant
- All components support dark mode
- WCAG AA contrast ratios maintained

---

## 🧪 Testing

### Test System Preference Following

```bash
# macOS
# 1. System Preferences → Appearance → Dark
# 2. Reload dashboard
# Expected: Dark mode applied (if theme = 'system')

# 3. Switch to Light
# Expected: Dashboard switches immediately (no reload)

# Windows 10/11
# Settings → Personalization → Colors → Choose your mode
# Dashboard updates in real-time
```

### Test Manual Override

```bash
# 1. Set theme to 'dark' in Settings
# 2. Change OS to light mode
# Expected: Dashboard stays dark (manual override active)

# 3. Set theme to 'system'
# Expected: Dashboard switches to light (follows OS)
```

### Test Persistence

```bash
# 1. Set theme to 'dark'
# 2. Close browser completely
# 3. Reopen dashboard
# Expected: Still in dark mode (localStorage persisted)
```

### Test No Flash

```bash
# 1. Set theme to 'dark'
# 2. Hard reload (Cmd+Shift+R / Ctrl+Shift+R)
# Expected: No white flash, immediately dark
```

---

## 🎯 Use Cases

**System-Based (Default):**
- Users who work day/night with different OS themes
- Automatic adaptation to environment
- Battery saving on OLED screens (auto dark at night)

**Manual Light:**
- Users who prefer light mode always
- Presentations and screen sharing
- High ambient light environments

**Manual Dark:**
- Users who prefer dark mode always
- Late-night coding sessions
- Reduced eye strain

---

## 🔍 Troubleshooting

### Theme Not Applying

**Check localStorage:**
```javascript
// Open Console
localStorage.getItem('theme')
// Should be: 'light', 'dark', or 'system'

// If null or invalid, reset:
localStorage.setItem('theme', 'system')
window.location.reload()
```

**Check CSS Class:**
```javascript
// Should have 'dark' class if in dark mode
document.documentElement.classList.contains('dark')
```

**Force Refresh:**
```bash
# Clear cache and reload
# Chrome: Cmd+Shift+R (Mac) / Ctrl+Shift+R (Windows)
```

### System Theme Not Detected

**Test Detection:**
```javascript
// Open Console
window.matchMedia('(prefers-color-scheme: dark)').matches
// Should return: true (dark) or false (light)

// Test listener
const mq = window.matchMedia('(prefers-color-scheme: dark)');
mq.addEventListener('change', (e) => console.log('Theme changed:', e.matches));
// Change OS theme, should log immediately
```

**Browser Support:**
- Chrome 76+
- Firefox 67+
- Safari 12.1+
- Edge 79+

(All modern browsers support this)

### Flash of White on Load

**Verify Script:**
```bash
# Check index.html has inline script
cat frontend/index.html | grep -A 10 "Prevent flash"

# Should see script before </head>
```

**Cache Issue:**
```bash
# Hard reload to clear cache
# Or disable cache in DevTools (Network tab)
```

---

## 📊 Browser Compatibility

| Feature | Chrome | Firefox | Safari | Edge |
|---------|--------|---------|--------|------|
| `prefers-color-scheme` | ✅ 76+ | ✅ 67+ | ✅ 12.1+ | ✅ 79+ |
| MediaQuery events | ✅ | ✅ | ✅ | ✅ |
| localStorage | ✅ | ✅ | ✅ | ✅ |
| CSS dark variant | ✅ | ✅ | ✅ | ✅ |

**Mobile Support:**
- iOS Safari 13+
- Android Chrome 76+
- All modern mobile browsers

---

## 🎨 Design Tokens

The theme uses these Tailwind CSS variables:

**Light Mode:**
- Background: `hsl(0 0% 100%)` - White
- Foreground: `hsl(222.2 84% 4.9%)` - Dark gray

**Dark Mode:**
- Background: `hsl(0 0% 4%)` - Near black (#0a0a0a)
- Foreground: `hsl(0 0% 98%)` - Near white (#fafafa)

**WCAG AA Compliance:**
- All text meets 4.5:1 contrast ratio
- Interactive elements: 3:1 minimum
- Tested with axe DevTools

---

## 🚀 Future Enhancements

**Potential Additions:**
- [ ] Custom accent color picker
- [ ] Multiple dark theme variants (true black, gray, blue)
- [ ] Scheduled theme switching (dark 6pm-6am)
- [ ] Per-page theme overrides
- [ ] Theme preview before applying

---

## 📝 Code Reference

**Files Modified:**
1. `frontend/index.html` - FOUC prevention script
2. `frontend/src/hooks/useTheme.ts` - Theme detection hook
3. `frontend/src/App.tsx` - Theme initialization
4. `frontend/src/pages/Settings.tsx` - Theme selector UI

**Key Functions:**
- `useTheme()` - Main theme hook
- `setTheme(mode)` - Change theme preference
- `resolvedTheme` - Current effective theme

---

**Enjoy your automatically themed dashboard!** 🌓✨
