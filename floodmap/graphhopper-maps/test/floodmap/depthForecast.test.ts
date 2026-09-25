import { ForecastColumn, forecastRequestPoints, forecastWindowStart, shapeDepthChart } from '@/floodmap/depthForecast'

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
    const columns = [column(14, 0, 0.05), column(14, 15, 0.2), column(14, 30, 0.4), column(14, 45, null)]

    it('marks the latest column at or before now, never a later one', () => {
        const chart = shapeDepthChart(columns, new Date(2026, 8, 25, 14, 29, 59).getTime())
        expect(chart.bars.map(b => [b.timeLabel, b.depthCm, b.heightPercent, b.isNow])).toEqual([
            ['14:00', 5, 12.5, false],
            ['14:15', 20, 50, true],
            ['14:30', 40, 100, false],
            ['14:45', null, 0, false],
        ])
        expect([chart.nowDepthCm, chart.nowLinePercent]).toEqual([20, 50])
    })

    it('marks a column whose valid_time equals now', () => {
        const chart = shapeDepthChart(columns, new Date(2026, 8, 25, 14, 30).getTime())
        expect(chart.bars.map(b => b.isNow)).toEqual([false, false, true, false])
        expect(chart.nowDepthCm).toEqual(40)
    })

    it('has no now bar and no line when every column is in the future', () => {
        const chart = shapeDepthChart(columns, new Date(2026, 8, 25, 13, 59).getTime())
        expect(chart.bars.map(b => b.isNow)).toEqual([false, false, false, false])
        expect([chart.nowDepthCm, chart.nowLinePercent]).toEqual([null, null])
    })

    it('scales a nearly dry route to 10 cm instead of its own maximum', () => {
        const chart = shapeDepthChart([column(14, 0, 0.01), column(14, 15, 0)], new Date(2026, 8, 25, 14, 0).getTime())
        expect(chart.bars.map(b => b.heightPercent)).toEqual([10, 0])
        expect(chart.nowLinePercent).toEqual(10)
    })
})

describe('forecastWindowStart', () => {
    it('starts one 15-minute step before the current step', () => {
        expect(forecastWindowStart(Date.parse('2026-09-25T07:29:59.999Z'))).toEqual('2026-09-25T07:00:00.000Z')
        expect(forecastWindowStart(Date.parse('2026-09-25T07:30:00Z'))).toEqual('2026-09-25T07:15:00.000Z')
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
