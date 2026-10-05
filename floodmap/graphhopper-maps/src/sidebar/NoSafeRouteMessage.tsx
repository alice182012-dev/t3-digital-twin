import { useEffect, useState } from 'react'
import styles from './RoutingResult.module.css'
import { RoutingArgs } from '@/api/graphhopper'
import { Advice, adviceText, loadAdvice } from '@/floodmap/departureAdvice'
import { BACKEND_BASE } from '@/floodmap/FloodStore'

/**
 * Terminal state, deliberately not an ErrorMessage: nothing failed, there is just no safe way. When the failure was a
 * missing connection (`target`), the box also says when the usual route clears in the forecast, or that the timing check
 * is unavailable (US-054). It keeps its advice to reach the safest location or stay put.
 */
export default function NoSafeRouteMessage({
    target,
    fetchImpl = (...args) => fetch(...args),
    baseUrl = BACKEND_BASE,
}: {
    target: RoutingArgs | null
    fetchImpl?: typeof fetch
    baseUrl?: string
}) {
    const [advice, setAdvice] = useState<Advice | null>(null)

    useEffect(() => {
        setAdvice(null)
        if (!target) return
        const controller = new AbortController()
        setAdvice({ kind: 'loading' })
        loadAdvice(fetchImpl, baseUrl, target, controller.signal)
            .then(result => controller.signal.aborted || setAdvice(result))
            .catch(() => {})
        return () => controller.abort()
    }, [target])

    return (
        <div className={styles.noSafeRoute}>
            No safe route available. Please consider getting to the safest location or stay where you are.
            {advice && <p className={styles.noSafeRouteAdvice}>{adviceText(advice)}</p>}
        </div>
    )
}
