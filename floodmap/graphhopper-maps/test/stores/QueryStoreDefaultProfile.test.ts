import QueryStore from '@/stores/QueryStore'
import { InfoReceived } from '@/actions/Actions'
import Api from '@/api/Api'

jest.mock('config', () => ({
    profiles: { car: {}, motorbike: {}, foot: {}, truck: {} },
    default_profile: 'motorbike',
    profile_group_mapping: {},
}))

describe('QueryStore default profile', () => {
    it('lists profiles in config order and selects default_profile', () => {
        const store = new QueryStore({} as Api)
        const state = store.reduce(
            store.state,
            new InfoReceived({
                profiles: [{ name: 'other' }],
                elevation: false,
                version: '',
                bbox: [0, 0, 0, 0],
                encoded_values: [],
            }),
        )
        expect(state.profiles.map(p => p.name)).toEqual(['car', 'motorbike', 'foot', 'truck'])
        expect(state.routingProfile.name).toEqual('motorbike')
    })
})
