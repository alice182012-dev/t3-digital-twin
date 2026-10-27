// Replaces a CSS module import with an object that maps each class name to itself, so a component
// test can render without a CSS loader. __esModule stays undefined so the default import is this object.
module.exports = {
    process() {
        return {
            code: `module.exports = new Proxy({}, { get: (_, key) => (key === '__esModule' ? undefined : key) })`,
        }
    },
}
