import { pinLabel, textToCoordinate, nominatimHitToItem, hitToItem, milliSecondsToText, suggestionLine } from '@/Converters'

describe('Converters', function () {
    describe('pinLabel', function () {
        const coordinate = { lat: 21.0123456, lng: 105.7234567 }
        it('should return the place name', function () {
            expect(pinLabel({ coordinate, queryText: 'GO Thang Long' })).toEqual('GO Thang Long')
        })
        it('should return undefined for empty text', function () {
            expect(pinLabel({ coordinate, queryText: '' })).toBeUndefined()
        })
        it('should return undefined for the text of the coordinate', function () {
            expect(pinLabel({ coordinate, queryText: '21.012346,105.723457' })).toBeUndefined()
        })
        it('should return undefined for other coordinate text', function () {
            expect(pinLabel({ coordinate, queryText: '21.0, 105.7' })).toBeUndefined()
        })
    })

    describe('milliSecondsToText', function () {
        it('should convert ms to text', function () {
            expect(milliSecondsToText(59 * 1000)).toEqual('1 min')

            expect(milliSecondsToText(63 * 60 * 1000)).toEqual('1 h 3 min')

            expect(milliSecondsToText(7198000)).toEqual('2 h')
        })
    })

    describe('textToCoordinate', function () {
        it('should convert 2 digits separated by ","', function () {
            expect(textToCoordinate('1.2345, 2.6534')).toEqual({ lat: 1.2345, lng: 2.6534 })
        })
        it('should convert 2 digits separated by " "', function () {
            expect(textToCoordinate('1.2345   2.6534')).toEqual({ lat: 1.2345, lng: 2.6534 })
        })
        it('should return null if not 2 elements are found', function () {
            expect(textToCoordinate('first second third')).toBeNull()
            expect(textToCoordinate('1.2345')).toBeNull()
        })
        it('should return null if any of the elements is NaN', function () {
            expect(textToCoordinate('2.6534 second')).toBeNull()
        })
    })

    describe('suggestionLine', function () {
        it('uses the district as the right-edge text', function () {
            expect(
                suggestionLine({
                    name: 'Đường Vành đai 3 C5',
                    district: 'Quận Cầu Giấy',
                    suburb: 'Phường Dịch Vọng',
                    city: 'Hà Nội',
                    country: 'Việt Nam',
                } as any),
            ).toEqual({ name: 'Đường Vành đai 3 C5', district: 'Quận Cầu Giấy' })
        })

        it('falls back to city_district, then suburb', function () {
            expect(
                suggestionLine({
                    name: 'Ngõ 5 C5',
                    city_district: 'Quận Nam Từ Liêm',
                    suburb: 'Phường Mỹ Đình',
                    city: 'Hà Nội',
                } as any),
            ).toEqual({ name: 'Ngõ 5 C5', district: 'Quận Nam Từ Liêm' })
            expect(suggestionLine({ name: 'Tòa nhà C5', suburb: 'Phường Mỹ Đình', city: 'Hà Nội' } as any)).toEqual({
                name: 'Tòa nhà C5',
                district: 'Phường Mỹ Đình',
            })
        })

        it('falls back to the city when no district is present', function () {
            expect(suggestionLine({ name: 'Hồ Gươm', city: 'Hà Nội', country: 'Việt Nam' } as any)).toEqual({
                name: 'Hồ Gươm',
                district: 'Hà Nội',
            })
        })

        it('returns an empty district when the hit has no area at all', function () {
            expect(suggestionLine({ name: 'Việt Nam', country: 'Việt Nam' } as any)).toEqual({
                name: 'Việt Nam',
                district: '',
            })
        })

        it('shortens the name to the street and house number like the address rows', function () {
            expect(
                suggestionLine({
                    name: 'Nhà C5, Phố Trần Thái Tông',
                    street: 'Phố Trần Thái Tông',
                    housenumber: '12',
                    district: 'Quận Cầu Giấy',
                } as any),
            ).toEqual({ name: 'Phố Trần Thái Tông 12', district: 'Quận Cầu Giấy' })
        })
    })

    describe('hitToItem', function () {
        it('default city', function () {
            expect(
                hitToItem({
                    name: 'Hoyerswerda - Wojerecy',
                    country: 'Germany',
                    state: 'Saxony',
                    postcode: '02977',
                } as any),
            ).toEqual({ mainText: 'Hoyerswerda - Wojerecy', secondText: '02977, Saxony, Germany' })
        })

        it('default address', function () {
            expect(
                hitToItem({
                    name: 'somestreet',
                    country: 'Germany',
                    state: 'Berlin',
                    city: 'Berlin',
                    street: 'somestreet',
                    housenumber: '6',
                    postcode: '10117',
                } as any),
            ).toEqual({ mainText: 'somestreet 6', secondText: '10117 Berlin, Germany' })
        })

        it('default poi', function () {
            expect(
                hitToItem({
                    name: 'Wasserturm Hoyerswerda Bahnhof',
                    country: 'Germany',
                    city: 'Hoyerswerda - Wojerecy',
                    state: 'Saxony',
                    street: 'Am Bahnhofsvorplatz',
                    postcode: '02977',
                } as any),
            ).toEqual({
                mainText: 'Wasserturm Hoyerswerda Bahnhof',
                secondText: 'Am Bahnhofsvorplatz, 02977 Hoyerswerda - Wojerecy, Saxony, Germany',
            })
        })

        it('default poi 2', function () {
            expect(
                hitToItem({
                    name: 'An der Schule',
                    country: 'Germany',
                    city: 'Hoyerswerda - Wojerecy',
                    state: 'Saxony',
                    county: 'Bautzen',
                    postcode: '02977',
                } as any),
            ).toEqual({ mainText: 'An der Schule', secondText: '02977 Hoyerswerda - Wojerecy, Saxony, Germany' })
        })

        it('default poi 3', function () {
            expect(
                hitToItem({
                    name: 'Am Wasserturm',
                    country: 'Germany',
                    city: 'Hoyerswerda - Wojerecy',
                    state: 'Saxony',
                    postcode: '02977',
                } as any),
            ).toEqual({ mainText: 'Am Wasserturm', secondText: '02977 Hoyerswerda - Wojerecy, Saxony, Germany' })
        })
    })

    describe('nominatimHitToItem', function () {
        it('nominatim city', function () {
            expect(
                nominatimHitToItem({
                    name: '02977 Hoyerswerda - Wojerecy, Germany',
                    country: 'Germany',
                    city: 'Hoyerswerda - Wojerecy',
                    state: 'Saxony',
                    county: 'Bautzen',
                    postcode: '02977',
                } as any),
            ).toEqual({ mainText: '02977 Hoyerswerda - Wojerecy', secondText: 'Saxony, Germany' })
        })

        it('nominatim poi', function () {
            expect(
                nominatimHitToItem({
                    name: 'GraphHopper GmbH, Kirchstraße 17, 02977 Hoyerswerda - Wojerecy, Germany',
                    country: 'Germany',
                    city: 'Hoyerswerda - Wojerecy',
                    state: 'Saxony',
                    street: 'Kirchstraße',
                    housenumber: '17',
                    county: 'Bautzen',
                    postcode: '02977',
                } as any),
            ).toEqual({
                mainText: 'GraphHopper GmbH',
                secondText: 'Kirchstraße 17, 02977 Hoyerswerda - Wojerecy, Saxony, Germany',
            })
        })

        it('nominatim poi - ignore name', function () {
            expect(
                nominatimHitToItem({
                    name: 'An der Schule, 02977 Hoyerswerda - Wojerecy, Germany',
                    country: 'Germany',
                    city: 'Hoyerswerda - Wojerecy',
                    state: 'Saxony',
                    street: 'An der Schule',
                    county: 'Bautzen',
                    postcode: '02977',
                } as any),
            ).toEqual({ mainText: 'An der Schule', secondText: '02977 Hoyerswerda - Wojerecy, Saxony, Germany' })
        })

        it('nominatim city 2', function () {
            expect(
                nominatimHitToItem({
                    name: '02977 Hoyerswerda, Deutschland',
                    country: 'Deutschland',
                    city: 'Hoyerswerda',
                    state: 'Saxony',
                    county: 'Bautzen',
                    postcode: '02977',
                } as any),
            ).toEqual({ mainText: '02977 Hoyerswerda', secondText: 'Saxony, Deutschland' })
        })

        it('nominatim city 3', function () {
            expect(
                nominatimHitToItem({
                    name: 'Wittensee, something else',
                    country: 'Deutschland',
                    city: 'Groß Wittensee',
                    state: 'Schleswig-Holstein',
                    county: 'Rendsburg-Eckernförde',
                } as any),
            ).toEqual({ mainText: 'Wittensee', secondText: 'Groß Wittensee, Schleswig-Holstein, Deutschland' })
        })
    })
})
