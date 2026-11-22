const path = require('path');
const { runTests } = require('@vscode/test-electron');

async function main() {
    await runTests({
        version: process.env.VSCODE_TEST_VERSION || 'stable',
        extensionDevelopmentPath: path.resolve(__dirname, '..'),
        extensionTestsPath: path.resolve(__dirname, 'suite.js'),
        launchArgs: ['--disable-extensions', '--disable-workspace-trust', '--log', 'trace'],
    });
}

main().catch((error) => {
    console.error(error);
    process.exit(1);
});
