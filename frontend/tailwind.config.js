/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                'neon-blue': '#00d4ff',
                'neon-green': '#00ff88',
                'neon-purple': '#a855f7',
                'neon-pink': '#f43f5e',
                'neon-yellow': '#facc15',
                'dark-bg': '#0a0e1a',
                'dark-card': '#111827',
                'dark-surface': '#1a1f36',
                'dark-border': '#2a2f45',
            },
            fontFamily: {
                'mono': ['JetBrains Mono', 'Fira Code', 'monospace'],
                'sans': ['Inter', 'system-ui', 'sans-serif'],
            },
            animation: {
                'pulse-neon': 'pulseNeon 2s ease-in-out infinite',
                'slide-up': 'slideUp 0.5s ease-out',
                'glow': 'glow 2s ease-in-out infinite alternate',
            },
            keyframes: {
                pulseNeon: {
                    '0%, 100%': { boxShadow: '0 0 5px rgba(0, 212, 255, 0.5)' },
                    '50%': { boxShadow: '0 0 20px rgba(0, 212, 255, 0.8), 0 0 40px rgba(0, 212, 255, 0.3)' },
                },
                slideUp: {
                    '0%': { transform: 'translateY(20px)', opacity: 0 },
                    '100%': { transform: 'translateY(0)', opacity: 1 },
                },
                glow: {
                    '0%': { boxShadow: '0 0 5px rgba(168, 85, 247, 0.4)' },
                    '100%': { boxShadow: '0 0 20px rgba(168, 85, 247, 0.8)' },
                },
            },
        },
    },
    plugins: [],
}
