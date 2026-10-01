import { RouteTab } from '@/sidebar/routingResultsView'
import styles from './RoutingResult.module.css'
import PlainButton from '@/PlainButton'

/** Tab strip over the returned alternatives. Presentational; index-keyed. */
export default function RouteTabs({
    tabs,
    activeIndex,
    onSelect,
}: {
    tabs: readonly RouteTab[]
    activeIndex: number
    onSelect: (index: number) => void
}) {
    return (
        <div className={styles.routeTabs} role="tablist">
            {tabs.map(tab => (
                <PlainButton
                    key={tab.index}
                    role="tab"
                    aria-selected={tab.index === activeIndex}
                    className={tab.index === activeIndex ? styles.routeTabActive : styles.routeTab}
                    onClick={() => onSelect(tab.index)}
                >
                    {tab.label}
                </PlainButton>
            ))}
        </div>
    )
}
