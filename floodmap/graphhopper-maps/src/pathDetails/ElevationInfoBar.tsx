import { useCallback, useContext, useMemo, useRef } from 'react'
import { Path } from '@/api/graphhopper'
import { SettingsContext } from '@/contexts/SettingsContext'
import Dispatcher from '@/stores/Dispatcher'
import { PathDetailsHover } from '@/actions/Actions'
import { buildChartData } from './elevationWidget/pathDetailData'
import { ChartHoverResult } from './elevationWidget/types'
import ElevationWidget from './elevationWidget/ElevationWidget'
import { tr } from '@/translation/Translation'

interface ElevationInfoBarProps {
    selectedPath: Path
    alternativePaths: Path[]
    profile: string
    isExpanded: boolean
    onToggleExpanded: () => void
    onClose?: () => void
}

export default function ElevationInfoBar({
    selectedPath,
    alternativePaths,
    profile,
    isExpanded,
    onToggleExpanded,
    onClose,
}: ElevationInfoBarProps) {
    const settings = useContext(SettingsContext)

    const chartData = useMemo(
        () =>
            selectedPath.points.coordinates.length > 0
                ? buildChartData(selectedPath, alternativePaths, tr, profile)
                : null,
        [selectedPath, alternativePaths, profile],
    )

    // Original 1-based route numbers for each alternative (e.g. if route 2 is selected, alts are [1, 3])
    const alternativeRouteNumbers = alternativePaths
        .map((p, i) => ({ path: p, num: i + 1 }))
        .filter(x => x.path !== selectedPath && x.path.points.coordinates.length > 0)
        .map(x => x.num)

    const hoverRaf = useRef(0)
    const handleHover = useCallback((result: ChartHoverResult | null) => {
        cancelAnimationFrame(hoverRaf.current)
        hoverRaf.current = requestAnimationFrame(() => {
            if (result) {
                const description = result.segment ? String(result.segment.value) : ''
                Dispatcher.dispatch(
                    new PathDetailsHover({
                        point: result.point,
                        elevation: result.elevation,
                        description,
                    }),
                )
            } else {
                Dispatcher.dispatch(new PathDetailsHover(null))
            }
        })
    }, [])

    return (
        <ElevationWidget
            data={chartData}
            showDistanceInMiles={settings.showDistanceInMiles}
            onHover={handleHover}
            isExpanded={isExpanded}
            onToggleExpanded={onToggleExpanded}
            onClose={onClose}
            alternativeRouteNumbers={alternativeRouteNumbers}
            elevationLabel={tr('elevation')}
        />
    )
}
