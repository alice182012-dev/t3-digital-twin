import { ReactElement } from 'react'

const outline = {
    width: 20,
    height: 20,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
} as const

const Pin = ({ color }: { color: string }) => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill={color} aria-hidden="true">
        <path d="M12 22s7-7.2 7-12a7 7 0 1 0-14 0c0 4.8 7 12 7 12z" />
        <circle cx="12" cy="10" r="2.6" fill="#fff" />
    </svg>
)

const Ahead = () => (
    <svg {...outline}>
        <path d="M12 4v16M6 14l6 6 6-6" />
    </svg>
)

const TurnRight = () => (
    <svg {...outline}>
        <path d="M4 12h12a4 4 0 0 1 4 4v4M8 8l-4 4 4 4" />
    </svg>
)

const TurnLeft = () => (
    <svg {...outline}>
        <path d="M20 12H8a4 4 0 0 0-4 4v4M16 8l4 4-4 4" />
    </svg>
)

export type StepIconKind = 'origin' | 'destination' | 'left' | 'right' | 'ahead'

/**
 * The icon of a step in mockup screen 2e. The first row is the origin pin and the destination sign (4) is the red
 * pin. Left turns, keep left and u-turns point left, right turns and keep right point right, and every other
 * sign points ahead.
 */
export function stepIconKind(sign: number, isFirst: boolean): StepIconKind {
    if (isFirst) return 'origin'
    if (sign === 4) return 'destination'
    if (sign === -98 || sign === -8 || sign === -7 || (sign < 0 && sign >= -3)) return 'left'
    if (sign === 8 || sign === 7 || (sign > 0 && sign <= 3)) return 'right'
    return 'ahead'
}

const icons: Record<StepIconKind, () => ReactElement> = {
    origin: () => <Pin color="#111" />,
    destination: () => <Pin color="#d61f1f" />,
    left: TurnLeft,
    right: TurnRight,
    ahead: Ahead,
}

export function FramedStepIcon({ sign, isFirst }: { sign: number; isFirst: boolean }) {
    const Icon = icons[stepIconKind(sign, isFirst)]
    return <Icon />
}
