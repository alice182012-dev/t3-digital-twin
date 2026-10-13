import {
    FORECAST_REQUEST_STEPS,
    ForecastColumn,
    forecastRequestPoints,
    forecastWindowStart,
    shapeDepthChart,
} from '@/floodmap/depthForecast'

function column(hours: number, minutes: number, meanDepthM: number | null): ForecastColumn {
    return {
        valid_time: new Date(2026, 8, 25, hours, minutes).toISOString(),
        run: '20260925T140000',
        mean_depth_m: meanDepthM,
        max_depth_m: meanDepthM,
        wet_fraction: meanDepthM === null ? null : 1,
    }
}

describe('shapeDepthChart', () => {
    const at = (hours: number, minutes: number, seconds = 0) => new Date(2026, 8, 25, hours, minutes, seconds).getTime()
    const quarterHours = [
        column(13, 45, 0.01),
        column(14, 0, 0.05),
        column(14, 15, 0.1),
        column(14, 30, 0.2),
        column(14, 45, 0.3),
        column(15, 0, 0.4),
        column(15, 15, 0.5),
        column(15, 30, 0.6),
        column(15, 45, 0.7),
        column(16, 0, null),
    ]

    it('selects five columns on the half hour, the second one being the current half hour', () => {
        const chart = shapeDepthChart(quarterHours, at(14, 35))
        expect(chart.bars.map(b => [b.timeLabel, b.depthCm, b.isNow])).toEqual([
            ['14:00', 5, false],
            ['14:30', 20, true],
            ['15:00', 40, false],
            ['15:30', 60, false],
            ['16:00', null, false],
        ])
        expect([chart.nowDepthCm, chart.nowLinePercent]).toEqual([20, (20 / 60) * 100])
    })

    it('uses the same half hour for every minute until the next one', () => {
        for (const [h, m, s] of [
            [14, 30, 0],
            [14, 44, 59],
            [14, 59, 59],
        ]) {
            expect(shapeDepthChart(quarterHours, at(h, m, s)).bars.map(b => b.timeLabel)).toEqual([
                '14:00',
                '14:30',
                '15:00',
                '15:30',
                '16:00',
            ])
        }
    })

    it('labels only full hours and the now bar', () => {
        expect(shapeDepthChart(quarterHours, at(14, 35)).bars.map(b => b.label)).toEqual([
            '14:00',
            'Now',
            '15:00',
            '',
            '16:00',
        ])
        expect(shapeDepthChart(quarterHours, at(14, 5)).bars.map(b => b.label)).toEqual(['Now', '', '15:00', ''])
    })

    it('labels a now bar that falls on the hour as Now', () => {
        const chart = shapeDepthChart(quarterHours, at(14, 0))
        expect(chart.bars.map(b => [b.timeLabel, b.label])).toEqual([
            ['14:00', 'Now'],
            ['14:30', ''],
            ['15:00', '15:00'],
            ['15:30', ''],
        ])
    })

    it('gives no bar for a slot the backend omitted', () => {
        const withoutOne = quarterHours.filter(c => c.valid_time !== column(15, 0, 0).valid_time)
        const chart = shapeDepthChart(withoutOne, at(14, 35))
        expect(chart.bars.map(b => b.timeLabel)).toEqual(['14:00', '14:30', '15:30', '16:00'])
    })

    it('ignores columns that fall between the selected slots', () => {
        const chart = shapeDepthChart([column(14, 15, 0.1), column(14, 30, 0.2)], at(14, 35))
        expect(chart.bars.map(b => b.timeLabel)).toEqual(['14:30'])
    })

    it('has no now bar and no line when every selected column is in the future', () => {
        const chart = shapeDepthChart([column(14, 30, 0.2), column(15, 0, 0.4)], at(14, 10))
        expect(chart.bars.map(b => b.isNow)).toEqual([false, false])
        expect(chart.bars.map(b => b.label)).toEqual(['', '15:00'])
        expect([chart.nowDepthCm, chart.nowLinePercent]).toEqual([null, null])
    })

    it('scales a nearly dry route to 10 cm instead of its own maximum', () => {
        const chart = shapeDepthChart([column(14, 0, 0.01), column(14, 30, 0)], at(14, 0))
        expect(chart.bars.map(b => b.heightPercent)).toEqual([10, 0])
        expect(chart.nowLinePercent).toEqual(10)
    })
})

describe('forecastWindowStart', () => {
    it('starts 30 minutes before the current half hour', () => {
        expect(forecastWindowStart(Date.parse('2026-09-25T07:29:59.999Z'))).toEqual('2026-09-25T06:30:00.000Z')
        expect(forecastWindowStart(Date.parse('2026-09-25T07:30:00Z'))).toEqual('2026-09-25T07:00:00.000Z')
    })

    it('requests enough 15-minute steps to reach 90 minutes past the current half hour', () => {
        expect(FORECAST_REQUEST_STEPS).toEqual(9)
    })
})

describe('forecastRequestPoints', () => {
    it('drops elevation', () => {
        expect(
            forecastRequestPoints([
                [105.8, 21.0, 12],
                [105.81, 21.01, 14],
            ]),
        ).toEqual([
            [105.8, 21.0],
            [105.81, 21.01],
        ])
    })

    it('thins a long route to 2000 points and keeps both ends', () => {
        const coordinates = Array.from({ length: 4001 }, (_, i) => [i, 0])
        const points = forecastRequestPoints(coordinates)
        expect(points.length).toEqual(2000)
        expect([points[0], points[1], points[1999]]).toEqual([
            [0, 0],
            [2, 0],
            [4000, 0],
        ])
    })
})
