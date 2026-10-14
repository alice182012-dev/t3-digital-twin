import styles from './FloodBanner.module.css'

export default function FloodBanner({ text }: { text: string }) {
    return (
        <div className={styles.container} role="status">
            {text}
        </div>
    )
}
