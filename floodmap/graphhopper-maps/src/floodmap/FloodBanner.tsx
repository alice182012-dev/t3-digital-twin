import type { CSSProperties } from 'react'
import styles from './FloodBanner.module.css'

/** `offsetLeft` is the width in px of the panel at the left, the same value MapModeToggle takes. */
export default function FloodBanner({ text, offsetLeft = 0 }: { text: string; offsetLeft?: number }) {
    return (
        <div
            className={styles.container}
            style={{ '--banner-offset': `${offsetLeft}px` } as CSSProperties}
            role="status"
        >
            {text}
        </div>
    )
}
