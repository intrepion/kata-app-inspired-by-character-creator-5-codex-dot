import test from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';

// Use an ephemeral HTTP port, never a file:// page or a second browser preview.
test('HTTP server honors CLI port and serves safe static responses', {timeout: 10000}, async t => {
  const child = spawn(process.execPath, ['server.mjs', '--port', '0', '--host', '127.0.0.1'], {cwd: new URL('..', import.meta.url), stdio: ['ignore','pipe','pipe']});
  t.after(() => child.kill());
  const origin = await new Promise((resolve, reject) => {
    let output = '';
    child.stdout.on('data', chunk => {
      output += chunk;
      const match = output.match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) resolve(match[0]);
    });
    child.once('error', reject);
    child.once('exit', code => reject(new Error('Server exited: ' + code)));
  });
  const page = await fetch(origin + '/');
  assert.equal(page.status, 200);
  assert.match(page.headers.get('content-type'), /text\/html/);
  assert.match(await page.text(), /<canvas/);
  const script = await fetch(origin + '/src/app.js');
  assert.equal(script.status, 200);
  assert.match(script.headers.get('content-type'), /javascript/);
  const head = await fetch(origin + '/', {method:'HEAD'});
  assert.equal(head.status, 200);
  assert.equal(await head.text(), '');
  assert.equal((await fetch(origin + '/.git/config')).status, 404);
  assert.equal((await fetch(origin + '/does-not-exist')).status, 404);
  assert.equal((await fetch(origin + '/', {method:'POST'})).status, 405);
});
