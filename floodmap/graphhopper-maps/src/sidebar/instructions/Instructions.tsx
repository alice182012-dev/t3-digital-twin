import styles from '@/sidebar/instructions/Instructions.module.css'

import uTurn from './u_turn.png'
import uTurnLeft from './u_turn_left.png'
import keepLeft from './keep_left.png'
import sharpLeft from './sharp_left.png'
import left from './left.png'
import slightLeft from './slight_left.png'
import continueImg from './continue.png'
import slightRight from './slight_right.png'
import right from './right.png'
import sharpRight from './sharp_right.png'
import roundabout from './roundabout.png'
import keepRight from './keep_right.png'
import ferry from './ferry.png'
import unknown from './unknown.png'
import uTurnRight from './u_turn_right.png'
import ptStartTrip from './pt_start_trip.png'
import ptTransferTo from './pt_transfer_to.png'
import ptEndTrip from './pt_end_trip.png'
import { metersToText } from '@/Converters'
import { Instruction } from '@/api/graphhopper'
import { CircleComponent, MarkerComponent } from '@/map/Marker'
import QueryStore, { QueryPointType } from '@/stores/QueryStore'
import Dispatcher from '@/stores/Dispatcher'
import { InstructionClicked, PathDetailsElevationSelected, SetBBox } from '@/actions/Actions'
import { stepHighlight } from '@/sidebar/instructions/stepHighlight'
import { useContext } from 'react'
import { FloodTimestep } from '@/floodmap/FloodStore'
import { deepestStepIndexes, stepDepthText } from '@/floodmap/placeDepth'
import { FramedStepIcon } from '@/sidebar/instructions/FramedStepIcon'
import { useStepDepths } from '@/floodmap/useStepDepths'
import { SettingsContext } from '@/contexts/SettingsContext'

/**
 * `timestep` is set in Flood mode. Each step then shows the water depth at its start point.
 * `framed` is the desktop panel list of mockup screen 2e: one row per step, the distance at the right.
 */
export default function (props: {
    instructions: Instruction[]
    us: boolean
    timestep?: FloodTimestep
    framed?: boolean
}) {
    const depths = useStepDepths(
        props.instructions.map(instruction => ({ lng: instruction.points[0][0], lat: instruction.points[0][1] })),
        props.timestep,
    )
    const deepest = deepestStepIndexes(depths)
    return (
        <ul className={props.framed ? styles.framedList : styles.instructionsList}>
            {props.instructions.map((instruction, i) => (
                <Line
                    key={i}
                    instruction={instruction}
                    index={i}
                    us={props.us}
                    depthText={stepDepthText(depths[i])}
                    isDeepest={deepest.has(i)}
                    framed={props.framed}
                />
            ))}
        </ul>
    )
}

const Line = function ({
    instruction,
    index,
    us,
    depthText,
    isDeepest,
    framed,
}: {
    instruction: Instruction
    index: number
    us: boolean
    depthText: string | null
    isDeepest: boolean
    framed?: boolean
}) {
    const settings = useContext(SettingsContext)
    return (
        <li
            className={styles.instruction}
            onClick={() => {
                Dispatcher.dispatch(
                    new InstructionClicked(
                        { lng: instruction.points[0][0], lat: instruction.points[0][1] },
                        instruction.text,
                    ),
                )
                const { segment, bbox } = stepHighlight(instruction)
                Dispatcher.dispatch(new PathDetailsElevationSelected([segment]))
                if (bbox) Dispatcher.dispatch(new SetBBox(bbox))
            }}
        >
            {framed ? (
                <div className={styles.sign}>
                    <FramedStepIcon sign={instruction.sign} isFirst={index === 0} />
                </div>
            ) : (
                getTurnSign(instruction.sign, index)
            )}
            <span className={framed && (index === 0 || instruction.sign === 4) ? styles.placeText : styles.mainText}>
                {instruction.text}
            </span>
            {instruction.motorway_junction && (
                <span style={{ background: us ? '#00674c' : '#003399' }} className={styles.motorwayJunction}>
                    {instruction.motorway_junction}
                </span>
            )}
            <span className={styles.distance}>
                {metersToText(instruction.distance, settings.showDistanceInMiles)}
                {depthText && ' · depth '}
                {depthText && <span className={isDeepest ? styles.deepestDepth : undefined}>{depthText}</span>}
            </span>
        </li>
    )
}

function getTurnSign(sign: number, index: number) {
    // from, via and to signs are special
    if (index === 0 || sign === 4 || sign === 5) {
        let icon
        if (index === 0) {
            icon = <MarkerComponent color={QueryStore.getMarkerColor(QueryPointType.From)} />
        } else if (sign === 4) {
            icon = <MarkerComponent color={QueryStore.getMarkerColor(QueryPointType.To)} />
        } else {
            icon = <CircleComponent color={QueryStore.getMarkerColor(QueryPointType.Via)} />
        }

        return <div className={styles.sign}>{icon}</div>
    }
    return <img className={styles.sign} src={getSignName(sign)} alt={'turn instruction'} />
}

function getSignName(sign: number) {
    switch (sign) {
        case -98:
            return uTurn
        case -8:
            return uTurnLeft
        case -7:
            return keepLeft
        case -3:
            return sharpLeft
        case -2:
            return left
        case -1:
            return slightLeft
        case 0:
            return continueImg
        case 1:
            return slightRight
        case 2:
            return right
        case 3:
            return sharpRight
        case 6:
        case -6:
            return roundabout
        case 7:
            return keepRight
        case 8:
            return uTurnRight
        case 9:
            return ferry
        case 101:
            return ptStartTrip
        case 102:
            return ptTransferTo
        case 103:
            return ptEndTrip
        default:
            return unknown
    }
}
