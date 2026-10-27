import { stepHighlight } from '@/sidebar/instructions/stepHighlight'

describe('stepHighlight', () => {
    it('turns the step points into a lat/lng segment and its bounding box', () => {
        const { segment, bbox } = stepHighlight({
            points: [
                [105.7573, 21.0051],
                [105.7581, 21.0049],
                [105.759, 21.006],
            ],
        })

        expect(segment).toEqual([
            { lng: 105.7573, lat: 21.0051 },
            { lng: 105.7581, lat: 21.0049 },
            { lng: 105.759, lat: 21.006 },
        ])
        expect(bbox).toEqual([105.7573, 21.0049, 105.759, 21.006])
    })

    it('pads the bounding box of a step that is a single point, such as the arrival', () => {
        const { segment, bbox } = stepHighlight({ points: [[105.75, 21.0]] })

        expect(segment).toEqual([{ lng: 105.75, lat: 21.0 }])
        expect(bbox).toEqual([105.749, 20.999, 105.751, 21.001])
    })

    it('has no bounding box for a step without points', () => {
        expect(stepHighlight({ points: [] })).toEqual({ segment: [], bbox: null })
    })
})
