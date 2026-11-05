// Offline checks: never log into Alcampo, start scraping, or access stored accounts.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');

for (const folder of ['dashboard', 'docs']) {
    const html = fs.readFileSync(path.join(__dirname, '..', folder, 'index.html'), 'utf8');
    const main = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)]
        .map(m => m[1]).find(s => s.includes('function clubQrPayload'));
    const nodes = new Map();
    function node(id) {
        if (!nodes.has(id)) nodes.set(id, {
            innerHTML: '', textContent: '', value: '', disabled: false, style: {}, addEventListener() {},
            classList: { add() {}, remove() {} },
        });
        return nodes.get(id);
    }
    const renders = [];
    const writes = [];
    function QRCode(element, options) { renders.push({ element, options }); }
    QRCode.CorrectLevel = { H: 2 };
    const sandbox = {
        console, QRCode,
        window: { addEventListener() {}, innerWidth: 390, innerHeight: 844 },
        document: {
            addEventListener() {}, getElementById: node, querySelectorAll: () => [],
            documentElement: { classList: { add() {}, remove() {} } },
            body: { classList: { add() {}, remove() {} }, dataset: { accountsView: 'true' } },
        },
        localStorage: { getItem: () => null, setItem: (...args) => writes.push(args) },
        setTimeout: callback => callback(), clearTimeout() {},
        requestAnimationFrame: callback => callback(),
        fetch: () => { throw new Error('Unexpected network access in QR test'); },
    };
    const context = vm.createContext(sandbox);
    vm.runInContext(main, context);
    const run = code => vm.runInContext(code, context);
    const testCard = '4000000000000'; // Synthetic fixture; never submitted to a service.
    assert.equal(context.clubQrPayload(testCard), '?clif=' + testCard);
    assert.equal(context.clubQrPayload('4 000000 000000'), '?clif=' + testCard);
    assert.equal(context.clubQrPayload('2800000000000'), '?clif=2800000000000');
    for (const invalid of ['', null, undefined, 'undefined', '1234', 'abc4000000000000', '?clif=4000000000000', '<img src=x>']) {
        assert.equal(context.clubQrPayload(invalid), '');
    }
    const btn = { getAttribute: key => ({ 'data-card': testCard, 'data-email': 'fixture@example.invalid' })[key] || '' };
    context.openAccountQr(btn);
    assert.equal(renders.at(-1).options.text, '?clif=' + testCard);
    assert.equal(renders.at(-1).options.correctLevel, QRCode.CorrectLevel.H);
    context.showQrModal(btn);
    assert.equal(renders.at(-1).options.text, '?clif=' + testCard);
    node('manual-card-input').value = testCard;
    context.liveGenerateFromInput();
    assert.equal(renders.at(-1).options.text, '?clif=' + testCard);
    context.renderClubQr(node('catalog'), testCard, 140);
    assert.equal(renders.at(-1).options.text, '?clif=' + testCard);
    run(`top10Data = [
        {email: 'fixture@example.invalid', card_number: '${testCard}', balance: 0},
        {email: 'missing@example.invalid', card_number: '', balance: 0}
    ]`);
    const beforeCatalog = renders.length;
    context.renderCardsCatalog();
    assert.equal(renders.length, beforeCatalog + 1, 'Catalog renders only available cards');
    assert.equal(renders.at(-1).options.text, '?clif=' + testCard);

    const beforeMissing = renders.length;
    context.openAccountQr({ getAttribute: key => key === 'data-email' ? 'missing@example.invalid' : '' });
    assert.equal(renders.length, beforeMissing, 'Missing card must not produce a QR');
    assert.equal(node('fullscreen-btn').disabled, true);
    assert.equal(node('barcode-svg').innerHTML, '', 'Missing card clears previous barcode');
    assert.equal(node('copy-card-btn').disabled, true);
    assert.equal(node('scanner-white-card').style.display, 'none');
    assert.equal(writes.length, 0, 'Opening a QR must not persist invented cards');
    // Legacy auto-generated local overrides must be ignored, while actual data wins.
    run(`{
        const email = 'legacy@example.invalid';
        let hash = 0;
        for (const ch of email) hash = ((hash << 5) - hash + ch.charCodeAt(0)) | 0;
        const prefix = '400200' + Math.abs(hash).toString().padStart(6, '0').slice(0, 6);
        customCardsStore[email] = prefix + calculateEan13Checksum(prefix);
    }`);
    assert.equal(context.getAccountCard('', 'legacy@example.invalid'), '');
    assert.equal(context.getAccountCard(testCard, 'legacy@example.invalid'), testCard);
    run(`customCardsStore['manual@example.invalid'] = '${testCard}'`);
    assert.equal(context.getAccountCard('', 'manual@example.invalid'), testCard);
    context.showQrModal(btn);
    assert.equal(node('fullscreen-btn').disabled, false);
    assert.equal(node('scanner-white-card').style.display, '');
    // A renderer failure leaves useful text and never sends the card to an image service.
    sandbox.QRCode = function () { throw new Error('Renderer unavailable'); };
    sandbox.QRCode.CorrectLevel = { H: 2 };
    assert.equal(context.renderClubQr(node('broken'), testCard, 140), false);
    assert.match(node('broken').textContent, /Recarga/);
    assert.doesNotMatch(html, /api\.qrserver\.com|generateDeterministicCardForEmail|generateRandomCardNumber/);
    assert.equal((html.match(/new QRCode\(/g) || []).length, 1, 'Every QR entry point uses one renderer');
    console.log(`${folder}: official payload, QR actions, missing cards, legacy overrides and renderer errors passed`);
}
