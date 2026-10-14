const FONT = '600 13px sans-serif'
const PADDING_X = 8
const HEIGHT = 24
const SHADOW = 4

// a white rounded label with a soft shadow, drawn at the device pixel ratio so the text stays sharp
export function createLabelCanvas(text: string, pixelRatio: number) {
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')!
    context.font = FONT
    const textWidth = Math.ceil(context.measureText(text).width)
    const width = textWidth + 2 * PADDING_X
    const size: [number, number] = [width + 2 * SHADOW, HEIGHT + 2 * SHADOW]
    canvas.width = size[0] * pixelRatio
    canvas.height = size[1] * pixelRatio
    context.scale(pixelRatio, pixelRatio)
    context.shadowColor = 'rgba(0, 0, 0, 0.25)'
    context.shadowBlur = SHADOW
    context.shadowOffsetY = 1
    context.fillStyle = '#fff'
    context.beginPath()
    context.roundRect(SHADOW, SHADOW, width, HEIGHT, HEIGHT / 2)
    context.fill()
    context.shadowColor = 'transparent'
    context.font = FONT
    context.fillStyle = '#222'
    context.textBaseline = 'middle'
    context.fillText(text, SHADOW + PADDING_X, SHADOW + HEIGHT / 2 + 1)
    return { canvas, size }
}
