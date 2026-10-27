import { setTranslation } from '@/translation/Translation'

describe('translate', () => {
    it('should translate', () => {
        const tr = setTranslation('de', true)
        expect(tr.get('unknownKEY')).toEqual('unknownKEY')
        expect(tr.get('racingbike')).toEqual('Rennrad')
        expect(tr.get('route_info', ['27km', '18min'])).toEqual('27km werden 18min brauchen')
    })

    it('should translate if language and locale is known', () => {
        const tr = setTranslation('de-DE', true)
        expect(tr.get('racingbike')).toEqual('Rennrad')
    })

    it('should translate if only language is known', () => {
        const tr = setTranslation('de-XX', true)
        expect(tr.get('racingbike')).toEqual('Rennrad')
    })

    it('should fallback', () => {
        const trFI = setTranslation('fil', true)
        expect(trFI.get('drag_to_reorder')).toEqual('Drag to reorder')

        // empty string
        const trBN = setTranslation('bn_BN', true)
        expect(trBN.get('truck')).toEqual('Truck')
    })

    it('finland', () => {
        let trFI = setTranslation('fi', true)
        expect(trFI.get('car')).toEqual('Auto')

        trFI = setTranslation('fi-fi', true)
        expect(trFI.get('car')).toEqual('Auto')

        trFI = setTranslation('Fi-fi', true)
        expect(trFI.get('car')).toEqual('Auto')
    })
})

describe('empty routing panel placeholders', () => {
    it('reads the mockup text in English', () => {
        const tr = setTranslation('en_US', true)
        expect(tr.get('from_hint')).toEqual('Choose starting point, or click on the map')
        expect(tr.get('to_hint')).toEqual('Choose destination')
        expect(tr.get('via_hint')).toEqual('Via')
    })

    it('keeps other languages unchanged', () => {
        const tr = setTranslation('de', true)
        expect(tr.get('from_hint')).toEqual('Von')
        expect(tr.get('to_hint')).toEqual('Nach')
    })
})
