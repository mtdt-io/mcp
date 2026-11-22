const assert = require('assert');
const vscode = require('vscode');

async function run() {
    const extension = vscode.extensions.getExtension('mtdt.salesforce-devops');
    assert.ok(extension, 'extension mtdt.salesforce-devops is not installed');
    await extension.activate();
    assert.strictEqual(extension.isActive, true);

    assert.strictEqual(typeof vscode.lm.registerMcpServerDefinitionProvider, 'function');
    assert.strictEqual(vscode.cursor, undefined);

    const commands = await vscode.commands.getCommands(true);
    assert.ok(commands.includes('mtdt.openGuide'), 'mtdt.openGuide is not registered');
    assert.ok(commands.includes('mtdt.copyServerUrl'), 'mtdt.copyServerUrl is not registered');

    await vscode.commands.executeCommand('mtdt.copyServerUrl');
    assert.strictEqual(await vscode.env.clipboard.readText(), 'https://mcp.mtdt.io');

    console.log(`mtdt-test: vscode ${vscode.version}, extension active, commands registered`);
    console.log(`mtdt-test: mcp commands ${commands.filter((id) => /mcp/i.test(id)).join(', ')}`);
}

module.exports = { run };
