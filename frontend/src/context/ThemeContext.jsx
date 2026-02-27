import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const ThemeContext = createContext(null);

export const useTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error('useTheme must be used within ThemeProvider');
    }
    return context;
};

export const ThemeProvider = ({ children }) => {
    const [theme, setTheme] = useState('light');
    const [forceDark, setForceDark] = useState(false);

    useEffect(() => {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark' || savedTheme === 'light') {
            setTheme(savedTheme);
        } else {
            const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            setTheme(prefersDark ? 'dark' : 'light');
        }

        const savedForce = localStorage.getItem('force_dark');
        if (savedForce === '1') setForceDark(true);
    }, []);

    useEffect(() => {
        const root = document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
        } else {
            root.classList.remove('dark');
        }

        if (forceDark) {
            root.classList.add('force-dark');
        } else {
            root.classList.remove('force-dark');
        }

        localStorage.setItem('theme', theme);
        localStorage.setItem('force_dark', forceDark ? '1' : '0');
    }, [theme, forceDark]);

    const value = useMemo(() => ({
        theme,
        isDark: theme === 'dark',
        toggleTheme: () => setTheme((prev) => (prev === 'dark' ? 'light' : 'dark')),
        forceDark,
        toggleForceDark: () => setForceDark((prev) => !prev),
    }), [theme, forceDark]);

    return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
};
