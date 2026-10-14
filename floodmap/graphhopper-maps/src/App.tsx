import { useCallback, useContext, useEffect, useRef, useState } from 'react'
import ElevationInfoBar from '@/pathDetails/ElevationInfoBar'
import styles from './App.module.css'
import {
    getApiInfoStore,
    getErrorStore,
    getMapFeatureStore,
    getMapOptionsStore,
    getPathDetailsStore,
    getPOIsStore,
    getQueryStore,
    getRouteStore,
    getSettingsStore,
    getCurrentLocationStore,
} from '@/stores/Stores'
import MapComponent from '@/map/MapComponent'
import mapStyles from '@/map/Map.module.css'
import MapOptions from '@/map/MapOptions'
import MobileSidebar from '@/sidebar/MobileSidebar'
import { useMediaQuery } from 'react-responsive'
import RoutingResults from '@/sidebar/RoutingResults'
import { milliSecondsToText, metersToText } from '@/Converters'
import { Path } from '@/api/graphhopper'
import { QueryStoreState, RequestState } from '@/stores/QueryStore'
import { RouteStoreState } from '@/stores/RouteStore'
import { MapOptionsStoreState, StyleOption } from '@/stores/MapOptionsStore'
import { ErrorStoreState } from '@/stores/ErrorStore'
import { CurrentLocationStoreState } from '@/stores/CurrentLocationStore'
import Search from '@/sidebar/search/Search'
import ErrorMessage from '@/sidebar/ErrorMessage'
import useBackgroundLayer from '@/layers/UseBackgroundLayer'
import useQueryPointsLayer from '@/layers/UseQueryPointsLayer'
import usePathsLayer from '@/layers/UsePathsLayer'
import ContextMenu from '@/layers/ContextMenu'
import usePathDetailsLayer from '@/layers/UsePathDetailsLayer'
import { Map } from 'ol'
import { getMap } from '@/map/map'
import CustomModelBox from '@/sidebar/CustomModelBox'
import useRoutingGraphLayer from '@/layers/UseRoutingGraphLayer'
import useUrbanDensityLayer from '@/layers/UseUrbanDensityLayer'
import useMapBorderLayer from '@/layers/UseMapBorderLayer'
import RoutingProfiles from '@/sidebar/search/routingProfiles/RoutingProfiles'
import MapPopups from '@/map/MapPopups'
import Cross from '@/sidebar/times-solid.svg'
import PlainButton from '@/PlainButton'
import useAreasLayer from '@/layers/UseAreasLayer'
import useExternalMVTLayer from '@/layers/UseExternalMVTLayer'
import LocationButton from '@/map/LocationButton'
import { SettingsContext } from '@/contexts/SettingsContext'
import usePOIsLayer from '@/layers/UsePOIsLayer'
import maptoolkitImg from '@/map/maptoolkit-attribution.png'
import useCurrentLocationLayer from '@/layers/UseCurrentLocationLayer'
import useFloodExtentLayer from '@/floodmap/FloodExtentLayer'
import { useFloodBootstrap, useFloodState } from '@/floodmap/useFloodState'
import { FloodStoreState, SetMapMode } from '@/floodmap/FloodStore'
import MapModeToggle from '@/floodmap/MapModeToggle'
import FloodLegend from '@/floodmap/FloodLegend'
import RouteDepthBadges from '@/floodmap/RouteDepthBadges'
import { namedDestination, namedStart, pointsForRoute, startForTap } from '@/floodmap/routeToPlace'
import PlaceDepthPopup from '@/floodmap/PlaceDepthPopup'
import { Coordinate } from '@/utils'
import { ProfileTimes, useProfileTimes } from '@/sidebar/search/routingProfiles/profileTimes'
import Dispatcher from '@/stores/Dispatcher'
import { SetPoint } from '@/actions/Actions'

// the Maptoolkit logo is only shown for their map styles
function isMaptoolkitStyle(styleOption: StyleOption) {
    const url = Array.isArray(styleOption.url) ? styleOption.url.join(' ') : styleOption.url
    return url.includes('maptoolkit.')
}

export const POPUP_CONTAINER_ID = 'popup-container'
export const SIDEBAR_CONTENT_ID = 'sidebar-content'

export default function App() {
    const [settings, setSettings] = useState(getSettingsStore().state)
    const [query, setQuery] = useState(getQueryStore().state)
    const [info, setInfo] = useState(getApiInfoStore().state)
    const [route, setRoute] = useState(getRouteStore().state)
    const [error, setError] = useState(getErrorStore().state)
    const [mapOptions, setMapOptions] = useState(getMapOptionsStore().state)
    const [pathDetails, setPathDetails] = useState(getPathDetailsStore().state)
    const [mapFeatures, setMapFeatures] = useState(getMapFeatureStore().state)
    const [pois, setPOIs] = useState(getPOIsStore().state)
    const [currentLocation, setCurrentLocation] = useState(getCurrentLocationStore().state)
    const flood = useFloodState()
    useFloodBootstrap()
    const [placeCoordinate, setPlaceCoordinate] = useState<Coordinate | null>(null)
    // Set when the route button closes the popup before the lookup has a name, so the name can still reach the box.
    const [namingCoordinate, setNamingCoordinate] = useState<Coordinate | null>(null)
    const floodMode = flood.mapMode === 'flood'
    // the popup reads the flood layer's depth, so it goes away with the layer
    useEffect(() => {
        if (!floodMode) setPlaceCoordinate(null)
    }, [floodMode])
    const closePlacePopup = useCallback(() => setPlaceCoordinate(null), [])
    // Lifted from LargeScreenLayout so the place popup's route button can open the panel.
    const [showSidebar, setShowSidebar] = useState(false)
    const routeToPlace = useCallback(
        (placeName: string | undefined) => {
            if (!placeCoordinate) return
            pointsForRoute(query.queryPoints, placeCoordinate, placeName).forEach(point =>
                Dispatcher.dispatch(new SetPoint(point, false)),
            )
            setShowSidebar(true)
            setPlaceCoordinate(null)
            setNamingCoordinate(placeName ? null : placeCoordinate)
        },
        [placeCoordinate, query.queryPoints],
    )
    const tapPlace = useCallback(
        (coordinate: Coordinate) => {
            setPlaceCoordinate(coordinate)
            setNamingCoordinate(null)
            const start = startForTap(query.queryPoints, coordinate)
            if (!start) return
            Dispatcher.dispatch(new SetPoint(start, false))
            setShowSidebar(true)
        },
        [query.queryPoints],
    )
    const namePlace = useCallback(
        (placeName: string) => {
            const coordinate = placeCoordinate ?? namingCoordinate
            if (!coordinate) return
            const named = [
                namedStart(query.queryPoints, coordinate, placeName),
                namedDestination(query.queryPoints, coordinate, placeName),
            ]
            named.forEach(point => point && Dispatcher.dispatch(new SetPoint(point, false)))
            setNamingCoordinate(null)
        },
        [placeCoordinate, namingCoordinate, query.queryPoints],
    )
    const profileTimes = useProfileTimes(query, flood, route.routingResult.paths.length > 0)

    const map = getMap()

    useEffect(() => {
        const onSettingsChanged = () => setSettings(getSettingsStore().state)
        const onQueryChanged = () => setQuery(getQueryStore().state)
        const onInfoChanged = () => setInfo(getApiInfoStore().state)
        const onRouteChanged = () => setRoute(getRouteStore().state)
        const onErrorChanged = () => setError(getErrorStore().state)
        const onMapOptionsChanged = () => setMapOptions(getMapOptionsStore().state)
        const onPathDetailsChanged = () => setPathDetails(getPathDetailsStore().state)
        const onMapFeaturesChanged = () => setMapFeatures(getMapFeatureStore().state)
        const onPOIsChanged = () => setPOIs(getPOIsStore().state)
        const onCurrentLocationChanged = () => setCurrentLocation(getCurrentLocationStore().state)

        getSettingsStore().register(onSettingsChanged)
        getQueryStore().register(onQueryChanged)
        getApiInfoStore().register(onInfoChanged)
        getRouteStore().register(onRouteChanged)
        getErrorStore().register(onErrorChanged)
        getMapOptionsStore().register(onMapOptionsChanged)
        getPathDetailsStore().register(onPathDetailsChanged)
        getMapFeatureStore().register(onMapFeaturesChanged)
        getPOIsStore().register(onPOIsChanged)
        getCurrentLocationStore().register(onCurrentLocationChanged)

        onQueryChanged()
        onInfoChanged()
        onRouteChanged()
        onErrorChanged()
        onMapOptionsChanged()
        onPathDetailsChanged()
        onMapFeaturesChanged()
        onPOIsChanged()
        onCurrentLocationChanged()

        return () => {
            getSettingsStore().deregister(onSettingsChanged)
            getQueryStore().deregister(onQueryChanged)
            getApiInfoStore().deregister(onInfoChanged)
            getRouteStore().deregister(onRouteChanged)
            getErrorStore().deregister(onErrorChanged)
            getMapOptionsStore().deregister(onMapOptionsChanged)
            getPathDetailsStore().deregister(onPathDetailsChanged)
            getMapFeatureStore().deregister(onMapFeaturesChanged)
            getPOIsStore().deregister(onPOIsChanged)
            getCurrentLocationStore().deregister(onCurrentLocationChanged)
        }
    }, [])

    // our different map layers
    useBackgroundLayer(map, mapOptions.selectedStyle)
    useExternalMVTLayer(map, mapOptions.externalMVTEnabled)
    useMapBorderLayer(map, info.bbox)
    useAreasLayer(map, settings.drawAreasEnabled, query.customModelStr, query.customModelEnabled)
    useRoutingGraphLayer(map, mapOptions.routingGraphEnabled)
    useUrbanDensityLayer(map, mapOptions.urbanDensityEnabled)
    usePathsLayer(
        map,
        route.routingResult.paths,
        route.selectedPath,
        query.queryPoints,
        true,
        settings.drawAreasEnabled,
    )
    useQueryPointsLayer(map, query.queryPoints)
    usePathDetailsLayer(map, pathDetails)
    usePOIsLayer(map, pois)
    useCurrentLocationLayer(map, currentLocation)
    useFloodExtentLayer(map, flood.mapMode === 'flood', flood.timesteps[flood.selectedIndex])

    const isSmallScreen = useMediaQuery({ query: '(max-width: 44rem)' })
    return (
        <SettingsContext.Provider value={settings}>
            <div className={styles.appWrapper}>
                <MapPopups
                    map={map}
                    pathDetails={pathDetails}
                    mapFeatures={mapFeatures}
                    poiState={pois}
                    query={query}
                />
                <PlaceDepthPopup
                    map={map}
                    coordinate={placeCoordinate}
                    nameCoordinate={namingCoordinate}
                    timestep={flood.timesteps[flood.selectedIndex]}
                    onClose={closePlacePopup}
                    onRoute={routeToPlace}
                    onPlaceName={namePlace}
                />
                <RouteDepthBadges
                    map={map}
                    coordinates={route.selectedPath.points.coordinates}
                    timestep={floodMode ? flood.timesteps[flood.selectedIndex] : undefined}
                />
                <ContextMenu
                    map={map}
                    route={route}
                    queryPoints={query.queryPoints}
                    onPlaceClick={floodMode ? tapPlace : undefined}
                />
                {isSmallScreen ? (
                    <SmallScreenLayout
                        query={query}
                        route={route}
                        map={map}
                        mapOptions={mapOptions}
                        error={error}
                        encodedValues={info.encoded_values}
                        drawAreas={settings.drawAreasEnabled}
                        currentLocation={currentLocation}
                        flood={flood}
                        profileTimes={profileTimes}
                    />
                ) : (
                    <LargeScreenLayout
                        showSidebar={showSidebar}
                        setShowSidebar={setShowSidebar}
                        query={query}
                        route={route}
                        map={map}
                        mapOptions={mapOptions}
                        error={error}
                        encodedValues={info.encoded_values}
                        drawAreas={settings.drawAreasEnabled}
                        currentLocation={currentLocation}
                        flood={flood}
                        profileTimes={profileTimes}
                    />
                )}
            </div>
        </SettingsContext.Provider>
    )
}

interface LayoutProps {
    query: QueryStoreState
    route: RouteStoreState
    map: Map
    mapOptions: MapOptionsStoreState
    currentLocation: CurrentLocationStoreState
    error: ErrorStoreState
    encodedValues: object[]
    drawAreas: boolean
    flood: FloodStoreState
    profileTimes: ProfileTimes
}

function LargeScreenLayout({
    query,
    route,
    map,
    error,
    mapOptions,
    encodedValues,
    drawAreas,
    currentLocation,
    flood,
    profileTimes,
    showSidebar,
    setShowSidebar,
}: LayoutProps & { showSidebar: boolean; setShowSidebar: (show: boolean) => void }) {
    const showMaptoolkitLogo = isMaptoolkitStyle(mapOptions.selectedStyle)
    const [showCustomModelBox, setShowCustomModelBox] = useState(false)
    const [elevationState, setElevationState] = useState<'compact' | 'expanded' | 'closed'>('closed')
    const hasRoute = route.selectedPath.points.coordinates.length > 0
    const routeRequestPending = query.currentRequest.subRequests.some(r => r.state === RequestState.SENT)
    // Show elevation widget when a route arrives, hide when route is gone
    // (but not during transient empty states like via point addition where a new request is already pending)
    useEffect(() => {
        if (hasRoute) {
            setElevationState(s => (s === 'closed' ? 'compact' : s))
        } else if (!routeRequestPending) {
            setElevationState('closed')
        }
    }, [hasRoute, routeRequestPending])
    // Hide map attribution when elevation widget is expanded (it would be covered)
    useEffect(() => {
        const el = map.getTargetElement()?.querySelector('.' + mapStyles.customAttribution) as HTMLElement | null
        if (el) el.style.display = elevationState === 'expanded' ? 'none' : ''
    }, [elevationState, map])
    return (
        <>
            {showSidebar ? (
                <div className={styles.sidebar}>
                    <div className={styles.sidebarContent} id={SIDEBAR_CONTENT_ID}>
                        <PlainButton onClick={() => setShowSidebar(false)} className={styles.sidebarCloseButton}>
                            <Cross />
                        </PlainButton>
                        <RoutingProfiles
                            routingProfiles={query.profiles}
                            selectedProfile={query.routingProfile}
                            memorizedProfilePerGroup={query.memorizedProfilePerGroup}
                            showCustomModelBox={showCustomModelBox}
                            toggleCustomModelBox={() => setShowCustomModelBox(!showCustomModelBox)}
                            customModelBoxEnabled={query.customModelEnabled}
                            profileTimes={profileTimes}
                        />
                        {showCustomModelBox && (
                            <CustomModelBox
                                customModelEnabled={query.customModelEnabled}
                                encodedValues={encodedValues}
                                customModelStr={query.customModelStr}
                                queryOngoing={query.currentRequest.subRequests[0]?.state === RequestState.SENT}
                                drawAreas={drawAreas}
                            />
                        )}
                        <Search points={query.queryPoints} profile={query.routingProfile} map={map} />
                        <div>{!error.isDismissed && <ErrorMessage error={error} />}</div>
                        <RoutingResults
                            info={route.routingResult.info}
                            limitCm={route.routingResult.hints?.['td.limit_cm']}
                            paths={route.routingResult.paths}
                            selectedPath={route.selectedPath}
                            currentRequest={query.currentRequest}
                            allPointsSet={query.queryPoints.every(point => point.isInitialized)}
                            profile={query.routingProfile.name}
                            floodActive={flood.mapMode === 'flood'}
                            timestep={flood.timesteps[flood.selectedIndex]}
                        />
                    </div>
                </div>
            ) : (
                <div className={styles.sidebarWhenClosed} onClick={() => setShowSidebar(true)}>
                    <span className={styles.sidebarOpenLabel}>Search Floodmap</span>
                    <PlainButton className={styles.sidebarOpenButton}>
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M6 20V10a4 4 0 0 1 4-4h8" stroke="#111" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                            <path d="M15 3l3 3-3 3" stroke="#111" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                    </PlainButton>
                </div>
            )}
            <div className={styles.popupContainer} id={POPUP_CONTAINER_ID} />
            <div className={styles.onMapRightSide}>
                <MapOptions {...mapOptions} />
                <LocationButton currentLocation={currentLocation} />
            </div>
            <div className={styles.map}>
                <MapComponent map={map} />
            </div>
            <MapModeToggle mode={flood.mapMode} onChange={mode => Dispatcher.dispatch(new SetMapMode(mode))} />
            {flood.mapMode === 'flood' && <FloodLegend timestep={flood.timesteps[flood.selectedIndex]} />}

            {/* the logo is only shown when the elevation widget is closed, because it would cover it otherwise */}
            {elevationState === 'closed' && (hasRoute || showMaptoolkitLogo) && (
                <div className={styles.pathDetails + ' ' + styles.bottomLeftBar}>
                    {hasRoute && (
                        <button
                            className={styles.elevationReopenButton}
                            onClick={() => setElevationState('compact')}
                            title="Show elevation"
                        >
                            <svg width="16" height="16" viewBox="0 0 1792 1792" fill="#666">
                                <path d="M1920 1536v128h-2048v-1536h128v1408h1920zm-384-1024l256 896h-1664v-576l448-576 576 576z" />
                            </svg>
                        </button>
                    )}
                    {showMaptoolkitLogo && (
                        <img className={styles.maptoolkitLogo} src={maptoolkitImg} alt="Maptoolkit" />
                    )}
                </div>
            )}
            <div
                className={elevationState === 'expanded' ? styles.pathDetailsExpanded : styles.pathDetails}
                style={{ display: elevationState === 'closed' ? 'none' : undefined }}
            >
                <ElevationInfoBar
                    selectedPath={route.selectedPath}
                    alternativePaths={route.routingResult.paths}
                    profile={query.routingProfile.name}
                    isExpanded={elevationState === 'expanded'}
                    onToggleExpanded={() => setElevationState(s => (s === 'expanded' ? 'compact' : 'expanded'))}
                    onClose={() => setElevationState('closed')}
                />
            </div>
        </>
    )
}

function SmallScreenLayout({
    query,
    route,
    map,
    error,
    mapOptions,
    encodedValues,
    drawAreas,
    currentLocation,
    flood,
    profileTimes,
}: LayoutProps) {
    const hasPath = route.selectedPath.points.coordinates.length > 0
    const settings = useContext(SettingsContext)

    const [isFooterCollapsed, setIsFooterCollapsed] = useState(false)
    const footerRef = useRef<HTMLDivElement>(null)

    // Auto-expand when new route arrives
    useEffect(() => {
        if (hasPath) setIsFooterCollapsed(false)
    }, [route.routingResult.paths])

    return (
        <>
            <div className={styles.smallScreenSidebar}>
                <MobileSidebar
                    query={query}
                    route={route}
                    error={error}
                    encodedValues={encodedValues}
                    drawAreas={drawAreas}
                    map={map}
                    profileTimes={profileTimes}
                />
            </div>
            <div className={styles.smallScreenMap}>
                <MapComponent map={map} />
            </div>
            {isMaptoolkitStyle(mapOptions.selectedStyle) && (
                <img
                    className={styles.smallScreenMaptoolkit + ' ' + styles.maptoolkitLogo}
                    src={maptoolkitImg}
                    alt="Maptoolkit"
                />
            )}
            <div className={styles.smallScreenMapOptions}>
                <div className={styles.onMapRightSide}>
                    <MapOptions {...mapOptions} />
                    <LocationButton currentLocation={currentLocation} />
                </div>
            </div>
            <MapModeToggle mode={flood.mapMode} onChange={mode => Dispatcher.dispatch(new SetMapMode(mode))} />
            {flood.mapMode === 'flood' && <FloodLegend timestep={flood.timesteps[flood.selectedIndex]} />}

            <div className={styles.smallScreenFooter} ref={footerRef}>
                {hasPath && isFooterCollapsed && (
                    <CollapsedFooter
                        path={route.selectedPath}
                        showDistanceInMiles={settings.showDistanceInMiles}
                        onClick={() => setIsFooterCollapsed(false)}
                    />
                )}
                <div style={{ display: hasPath && isFooterCollapsed ? 'none' : undefined }}>
                    {hasPath && (
                        <div className={styles.smallScreenFooterHandle} onClick={() => setIsFooterCollapsed(true)}>
                            <div className={styles.handleBar} />
                        </div>
                    )}
                    <RoutingResults
                        info={route.routingResult.info}
                        limitCm={route.routingResult.hints?.['td.limit_cm']}
                        paths={route.routingResult.paths}
                        selectedPath={route.selectedPath}
                        currentRequest={query.currentRequest}
                        allPointsSet={query.queryPoints.every(point => point.isInitialized)}
                        profile={query.routingProfile.name}
                        floodActive={flood.mapMode === 'flood'}
                        timestep={flood.timesteps[flood.selectedIndex]}
                    />
                </div>
            </div>
        </>
    )
}

function CollapsedFooter({
    path,
    showDistanceInMiles,
    onClick,
}: {
    path: Path
    showDistanceInMiles: boolean
    onClick: () => void
}) {
    return (
        <div className={styles.collapsedFooter} onClick={onClick}>
            <div className={styles.handleBar} />
            <div className={styles.collapsedFooterSummary}>
                <span className={styles.collapsedFooterTime}>{milliSecondsToText(path.time)}</span>
                {' - '}
                <span className={styles.collapsedFooterDistance}>
                    {metersToText(path.distance, showDistanceInMiles)}
                </span>
            </div>
        </div>
    )
}
