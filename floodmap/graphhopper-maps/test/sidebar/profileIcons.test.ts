import { readFileSync } from 'fs'
import { join } from 'path'
import { findIcon, icons } from '@/sidebar/search/routingProfiles/profileIcons'

// Evaluated by hand because jest's `config` moduleNameMapper rewrites any require of this path to config.js.
function loadExampleConfig() {
    const source = readFileSync(join(__dirname, '../../config-local.js.example'), 'utf8')
    const module = { exports: {} as any }
    new Function('module', source)(module)
    return module.exports
}

describe('profile icons', () => {
    it('draws the motorcycle for the motorbike profile', () => {
        expect(icons.motorbike).toBe('motorcycle.svg')
        expect(findIcon('motorbike')).toBe('motorcycle.svg')
    })

    it('has an icon for every profile in config-local.js.example', () => {
        const profiles = Object.keys(loadExampleConfig().profiles)
        expect(profiles).toContain('motorbike')
        expect(profiles.filter(name => findIcon(name) === 'question_mark.svg')).toEqual([])
    })

    it('lists the modes as car, motorbike, walking, truck in config-local.js.example', () => {
        expect(Object.keys(loadExampleConfig().profiles)).toEqual(['car', 'motorbike', 'foot', 'truck'])
    })

    it('keeps motorbike as the default profile in config-local.js.example', () => {
        expect(loadExampleConfig().default_profile).toBe('motorbike')
    })
})
