import { Moon, Sun, Square } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

const ThemeToggle = () => {
    const { isDark, toggleTheme, forceDark, toggleForceDark } = useTheme();

    return (
        <div className="flex items-center gap-3">
            <button
                onClick={toggleTheme}
                className="btn-ghost flex items-center gap-2"
                aria-label="Toggle dark mode"
                title="Theme settings"
            >
                {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                <span className="hidden sm:inline">{isDark ? 'Light' : 'Dark'} Mode</span>
            </button>

            <button
                onClick={toggleForceDark}
                className={`btn-ghost flex items-center gap-2 ${forceDark ? 'text-gemini-500' : ''}`}
                aria-label="Force pure black"
                title="Force pure black background across app"
            >
                <Square className="w-4 h-4" />
                <span className="hidden sm:inline">Force Black</span>
            </button>
        </div>
    );
};

export default ThemeToggle;
