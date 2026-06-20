/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["class"],
    content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
  	extend: {
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			leamss: {
  				teal: '#0D9488',
  				orange: '#F97316',
  				red: '#DC2626',
  				bg_white: '#FFFFFF',
  				teal_50: '#F0FDFA',
  				orange_50: '#FFF7ED',
  				red_50: '#FEF2F2',
  				// X4 — shade-aware aliases so legacy indigo-*/purple-*/violet-*
  				// classes can be migrated 1:1. All map to brand tokens.
  				'teal-50': '#F0FDFA', 'teal-100': '#CCFBF1', 'teal-200': '#99F6E4',
  				'teal-300': '#5EEAD4', 'teal-400': '#2DD4BF', 'teal-500': '#14B8A6',
  				'teal-600': '#0D9488', 'teal-700': '#0F766E', 'teal-800': '#115E59',
  				'teal-900': '#134E4A',
  				'orange-50': '#FFF7ED', 'orange-100': '#FFEDD5', 'orange-200': '#FED7AA',
  				'orange-300': '#FDBA74', 'orange-400': '#FB923C', 'orange-500': '#F97316',
  				'orange-600': '#EA580C', 'orange-700': '#C2410C', 'orange-800': '#9A3412',
  				'orange-900': '#7C2D12',
  				'red-50': '#FEF2F2', 'red-100': '#FEE2E2', 'red-200': '#FECACA',
  				'red-300': '#FCA5A5', 'red-400': '#F87171', 'red-500': '#EF4444',
  				'red-600': '#DC2626', 'red-700': '#B91C1C', 'red-800': '#991B1B',
  				'red-900': '#7F1D1D'
  			},
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};