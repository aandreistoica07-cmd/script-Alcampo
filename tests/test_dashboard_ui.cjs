// Offline UI regressions: no scraper execution, credentials, or remote writes.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');

for (const folder of ['dashboard', 'docs']) {
    const html = fs.readFileSync(path.join(__dirname, '..', folder, 'index.html'), 'utf8');
    for (const [, source] of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)) {
        new vm.Script(source); // Check every inline script, without executing page startup.
    }
    const progress = html.slice(html.indexOf('        let accountProgressState'), html.indexOf('        async function fetchLiveProgress'));
    const merge = html.slice(html.indexOf('        function mergeVisibleAccounts'), html.indexOf('        async function fetchTop10Accounts'));
    const context = vm.createContext({});
    vm.runInContext(progress + merge, context);
    const calculate = context.calculateAccountProgress;
    const first = { run_id: 'run1', total: 100, vms: {
        VM_0: { run_id: 'run1', processed: 100, success: 72, last_update: 10 },
        VM_old: { run_id: 'old', processed: 500, success: 500 }
    }};
    assert.equal(calculate(first).processed, 72);
    const retry = { ...first, cycle: 2, retry_total: 28 };
    const queue = Object.fromEntries(Array.from({ length: 28 }, (_, i) => [i, {
        email: `account${i}@example.test`, timestamp: 20,
        claimed_by: i < 3 ? 'VM_0_t1' : null
    }]));
    assert.equal(calculate(retry, queue).processed, 72, 'old pass-one workers must not count as retries');
    retry.vms.VM_0 = { run_id: 'run1', processed: 3, success: 1, error: 2, last_update: 25 };
    assert.equal(calculate(retry, queue).processed, 75, 'final retry failures also count');
    assert.equal(calculate(retry, null).processed, 75, 'temporary queue failure must not reduce progress');
    assert.equal(calculate({ ...retry, is_finished: true }).processed, 100, 'final summary wins');
    assert.equal(calculate({ ...first, run_id: 'run2', vms: {} }).processed, 0, 'new runs reset');
    assert.equal(calculate(retry, queue).processed, 75, 'opening directly in pass two works');
    const result = context.mergeVisibleAccounts(
        [{ email: 'user@example.test', password: 'local:password', balance: 10, card_number: '123' }],
        [{ email: 'user@example.test', balance: 12 }, { email: 'fake@example.test', balance: 99 },
         { email: 'live@example.test', balance: 3 }],
        [{ email: 'live@example.test', password: 'queue-password' }],
        new Set(['fake@example.test'])
    );
    assert.equal(result.size, 2);
    assert.equal(result.get('user@example.test').password, 'local:password');
    assert.equal(result.get('user@example.test').balance, 12);
    assert.equal(result.get('user@example.test').card_number, '123');
    assert.equal(result.get('live@example.test').password, 'queue-password');
    const final = context.mergeVisibleAccounts(
        [{ email: 'user@example.test', balance: 2, password: 'final-password' }],
        [{ email: 'user@example.test', balance: 20, password: 'old-password' },
         { email: 'old@example.test', balance: 99 }],
        [], new Set(), true
    );
    assert.equal(final.size, 1, 'finished runs ignore stale live-only accounts');
    assert.equal(final.get('user@example.test').balance, 2, 'final balance wins over older larger balance');
    assert.equal(final.get('user@example.test').password, 'final-password');
    console.log(`${folder}: syntax and UI regressions passed`);
}
