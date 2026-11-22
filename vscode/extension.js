const vscode = require('vscode');

const SERVER_NAME = 'mtdt';
const SERVER_LABEL = 'mtdt.io';
const SERVER_URL = 'https://mcp.mtdt.io';
const GUIDE_URL = 'https://docs.mtdt.io/docs/mcp';
const PROVIDER_ID = 'mtdt.mcp';
const MANUAL_HINT_KEY = 'mtdt.manualSetupHintShown';

function openGuide() {
    return vscode.env.openExternal(vscode.Uri.parse(GUIDE_URL));
}

async function copyServerUrl() {
    await vscode.env.clipboard.writeText(SERVER_URL);
    vscode.window.showInformationMessage(`Copied ${SERVER_URL}`);
}

function cursorMcpApi() {
    const api = vscode.cursor && vscode.cursor.mcp;
    if (api && typeof api.registerServer === 'function') return api;
    return null;
}

function registerInCursor(context, api) {
    api.registerServer({ name: SERVER_NAME, server: { url: SERVER_URL } });
    context.subscriptions.push({
        dispose: () => {
            if (typeof api.unregisterServer === 'function') api.unregisterServer(SERVER_NAME);
        },
    });
}

function registerInVsCode(context) {
    const provider = {
        provideMcpServerDefinitions: () => [
            new vscode.McpHttpServerDefinition(SERVER_LABEL, vscode.Uri.parse(SERVER_URL)),
        ],
    };
    context.subscriptions.push(vscode.lm.registerMcpServerDefinitionProvider(PROVIDER_ID, provider));
}

function vsCodeMcpSupported() {
    return Boolean(
        vscode.lm
        && typeof vscode.lm.registerMcpServerDefinitionProvider === 'function'
        && typeof vscode.McpHttpServerDefinition === 'function'
    );
}

async function showManualSetupHint(context) {
    if (context.globalState.get(MANUAL_HINT_KEY)) return;
    await context.globalState.update(MANUAL_HINT_KEY, true);
    const choice = await vscode.window.showInformationMessage(
        `This editor does not let extensions add MCP servers. Add ${SERVER_URL} in its MCP settings to connect your agent to mtdt.io.`,
        'Copy URL',
        'Open guide'
    );
    if (choice === 'Copy URL') await copyServerUrl();
    if (choice === 'Open guide') await openGuide();
}

function activate(context) {
    context.subscriptions.push(
        vscode.commands.registerCommand('mtdt.openGuide', openGuide),
        vscode.commands.registerCommand('mtdt.copyServerUrl', copyServerUrl)
    );

    const cursorApi = cursorMcpApi();
    if (cursorApi) {
        try {
            registerInCursor(context, cursorApi);
            return;
        } catch (error) {
            console.error('mtdt.io: Cursor MCP registration failed', error);
        }
    }

    if (vsCodeMcpSupported()) {
        registerInVsCode(context);
        return;
    }

    showManualSetupHint(context);
}

function deactivate() {}

module.exports = { activate, deactivate };
