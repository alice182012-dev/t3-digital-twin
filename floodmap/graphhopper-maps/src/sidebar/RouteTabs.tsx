import { KeyboardEvent, useRef } from 'react'
import { RouteTab } from '@/sidebar/routingResultsView'
import { routeTabKeyTarget } from '@/sidebar/routeTabKeys'
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
    // One ref on the strip instead of one per tab, because PlainButton does not take a ref.
    // Its children are the tab buttons in tab.index order.
    const tablistRef = useRef<HTMLDivElement>(null)

    function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
        const target = routeTabKeyTarget(event.key, activeIndex, tabs.length)
        if (target === null) return
        event.preventDefault()
        onSelect(target)
        ;(tablistRef.current?.children[target] as HTMLElement | undefined)?.focus()
    }

    return (
        <div ref={tablistRef} className={styles.routeTabs} role="tablist">
            {tabs.map(tab => (
                <PlainButton
                    key={tab.index}
                    role="tab"
                    aria-selected={tab.index === activeIndex}
                    tabIndex={tab.index === activeIndex ? 0 : -1}
                    className={tab.index === activeIndex ? styles.routeTabActive : styles.routeTab}
                    onClick={() => onSelect(tab.index)}
                    onKeyDown={onKeyDown}
                >
                    <span className={styles.routeTabText}>
                        <span>{tab.label}</span>
                        <span className={styles.routeTabDetail}>{tab.detail}</span>
                    </span>
                </PlainButton>
            ))}
        </div>
    )
}
