import React from 'react';

// Simple avatar that shows image if provided, otherwise a gradient initial
const Avatar = ({ src, name = '', size = 40, className = '' }) => {
    const initial = (name || 'B').trim().charAt(0).toUpperCase();

    // deterministic color based on name
    const hash = [...(name || initial)].reduce((acc, ch) => acc + ch.charCodeAt(0), 0);
    const hue = (hash * 37) % 360;
    const gradient = `linear-gradient(135deg, hsl(${hue} 85% 55%) 0%, hsl(${(hue + 60) % 360} 85% 50%) 100%)`;

    if (src) {
        const srcUrl = src.startsWith('http') ? src : src;
        return (
            <img src={srcUrl} alt={name || 'Avatar'} width={size} height={size} className={`rounded-xl object-cover ${className}`} />
        );
    }

    return (
        <div style={{ width: size, height: size, background: gradient }} className={`rounded-xl flex items-center justify-center text-white font-semibold ${className}`}>
            <span style={{ fontSize: Math.floor(size / 2.2) }}>{initial}</span>
        </div>
    );
};

export default Avatar;
