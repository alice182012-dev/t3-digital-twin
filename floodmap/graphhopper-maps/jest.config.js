module.exports = {
    preset: 'ts-jest',
    testEnvironment: 'jsdom',
    moduleNameMapper: {
        '@/(.*)$': '<rootDir>/src/$1',
        config: '<rootDir>/config.js',
    },
    transform: {
        '\\.svg$': '<rootDir>/test/svgFileName.js',
        '\\.css$': '<rootDir>/test/cssModuleClassNames.js',
    },
}
