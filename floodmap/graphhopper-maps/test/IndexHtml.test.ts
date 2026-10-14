import fs from 'fs'
import path from 'path'

describe('index.html', function () {
    const html = fs.readFileSync(path.resolve(__dirname, '../src/index.html'), 'utf8')

    it('names the page Floodmap', function () {
        expect(html).toContain('<title>Floodmap</title>')
        expect(html).toContain('<meta property="og:title" content="Floodmap" />')
    })

    it('does not point at graphhopper.com', function () {
        expect(html).not.toContain('graphhopper.com')
    })
})
