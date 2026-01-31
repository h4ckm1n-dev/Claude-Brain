import { useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

interface ThemeConfig {
  theme: Theme;
  resolvedTheme: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
}

/**
 * Theme hook that respects browser/system preferences.
 *
 * Features:
 * - Auto-detects system dark mode preference
 * - Listens for system preference changes
 * - Allows manual override (stored in localStorage)
 * - Applies 'dark' class to document root
 *
 * Usage:
 * ```tsx
 * const { theme, resolvedTheme, setTheme } = useTheme();
 *
 * // Get current effective theme
 * console.log(resolvedTheme); // 'light' or 'dark'
 *
 * // Change theme
 * setTheme('dark');   // Force dark
 * setTheme('light');  // Force light
 * setTheme('system'); // Follow system preference
 * ```
 */
export function useTheme(): ThemeConfig {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Check localStorage for user preference
    const stored = localStorage.getItem('theme');
    if (stored === 'light' || stored === 'dark' || stored === 'system') {
      return stored;
    }
    // Default to system preference
    return 'system';
  });

  const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>(() => {
    if (theme === 'system') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return theme;
  });

  useEffect(() => {
    // Function to resolve the actual theme
    const resolveTheme = (): 'light' | 'dark' => {
      if (theme === 'system') {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      }
      return theme;
    };

    // Apply theme to document
    const applyTheme = (resolved: 'light' | 'dark') => {
      const root = document.documentElement;

      if (resolved === 'dark') {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }

      setResolvedTheme(resolved);
    };

    // Initial theme application
    applyTheme(resolveTheme());

    // Listen for system preference changes (only if theme is 'system')
    if (theme === 'system') {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

      const handleChange = (e: MediaQueryListEvent) => {
        const newResolved = e.matches ? 'dark' : 'light';
        applyTheme(newResolved);
      };

      // Modern browsers
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', handleChange);
        return () => mediaQuery.removeEventListener('change', handleChange);
      }
      // Legacy browsers (Safari < 14)
      else {
        mediaQuery.addListener(handleChange);
        return () => mediaQuery.removeListener(handleChange);
      }
    }
  }, [theme]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem('theme', newTheme);
  };

  return {
    theme,
    resolvedTheme,
    setTheme,
  };
}
