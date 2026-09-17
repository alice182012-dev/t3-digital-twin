const { mergeWithRules, CustomizeRule } = require('webpack-merge')
const path = require('path')

const common = require('./webpack.common.js')

const develop = {
    mode: 'development',
    devtool: 'source-map',
    devServer: {
        static: path.resolve(__dirname, 'dist'),
        port: 3000,
        host: '0.0.0.0',
        headers: {
            'Referrer-Policy': 'strict-origin-when-cross-origin',
        },
        // Same two routes nginx.conf proxies in the built image. Targets the compose network's
        // service name, not localhost:8010 — this dev server is meant to run inside a container
        // on the t3-digital-twin_default network (see artifacts/logs for the docker run command),
        // since the host's own npm install is blocked by this repo's .npmrc allow-scripts policy.
        proxy: [
            {
                context: ['/api/gh'],
                target: 'http://floodmap-backend:8010',
                pathRewrite: { '^/api/gh': '' },
            },
            {
                context: ['/api/geocode'],
                target: 'http://floodmap-backend:8010',
                pathRewrite: { '^/api/geocode': '' },
            },
        ],
    },
}

const mergePattern = {
    module: {
        rules: {
            test: CustomizeRule.Match,
            exclude: CustomizeRule.Match,
            use: {
                loader: CustomizeRule.Match,
                options: CustomizeRule.Replace,
            },
        },
    },
}

module.exports = mergeWithRules(mergePattern)(common, develop)
