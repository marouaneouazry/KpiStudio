/**
 * Theme Toggle Component (Phase 8A)
 * Manages dark/light theme state with localStorage persistence.
 */
export function getSavedTheme() {
    return localStorage.getItem('theme') || 
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
}

export function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    const themeIcon = document.getElementById('theme-icon');
    if (themeIcon) {
        themeIcon.className = theme === 'dark' ? 'ti ti-sun' : 'ti ti-moon';
    }
}

export function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || getSavedTheme();
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    return newTheme;
}

export function initTheme() {
    const theme = getSavedTheme();
    setTheme(theme);

    const themeToggleBtn = document.getElementById('theme-toggle');
    if (themeToggleBtn && !themeToggleBtn.dataset.themeInitialized) {
        themeToggleBtn.dataset.themeInitialized = "true";
        themeToggleBtn.addEventListener('click', toggleTheme);
    }
}

// Auto-initialize when loaded
if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTheme);
    } else {
        initTheme();
    }
}
