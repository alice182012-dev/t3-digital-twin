import { ReactElement } from 'react'

function OutlineIcon({ children }: { children: ReactElement | ReactElement[] }) {
    return (
        <svg
            width="30"
            height="30"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.75"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
        >
            {children}
        </svg>
    )
}

const Car = () => (
    <OutlineIcon>
        <path d="M3 13l2-5h14l2 5v5H3z" />
        <path d="M3 13h18M7 8V6M17 8V6" />
        <circle cx="7" cy="18" r="1.5" />
        <circle cx="17" cy="18" r="1.5" />
    </OutlineIcon>
)

const Motorbike = () => (
    <OutlineIcon>
        <circle cx="5.5" cy="17" r="3" />
        <circle cx="18.5" cy="17" r="3" />
        <path d="M5.5 17l4-6h4l3 6M13.5 11l2-4h3" />
    </OutlineIcon>
)

const Foot = () => (
    <OutlineIcon>
        <circle cx="13" cy="4" r="2" />
        <path d="M10 21l2-6 3 2v4M12 15l-2-4 3-3 3 3 2 1M10 11l-3 2" />
    </OutlineIcon>
)

const Truck = () => (
    <OutlineIcon>
        <rect x="2" y="7" width="12" height="9" />
        <path d="M14 10h5l3 4v2h-8z" />
        <circle cx="6" cy="19" r="1.5" />
        <circle cx="18" cy="19" r="1.5" />
    </OutlineIcon>
)

/** The outline mode icons of the mockup (screens 2c to 2f). A mode without one keeps its stock icon. */
export const framedProfileIcons: Record<string, () => ReactElement> = {
    car: Car,
    motorbike: Motorbike,
    foot: Foot,
    truck: Truck,
}
