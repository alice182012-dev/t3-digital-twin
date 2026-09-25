const path = require('path')

// Replaces an svg import with its file name, so a test can assert which icon a lookup resolved to.
module.exports = {
    process(_source, filePath) {
        return { code: `module.exports = ${JSON.stringify(path.basename(filePath))}` }
    },
}
