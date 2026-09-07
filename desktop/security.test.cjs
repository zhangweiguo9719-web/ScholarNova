const { test } = require('node:test')
const assert = require('node:assert/strict')
const path = require('node:path')
const { safeExternalUrl, resolveStaticPath } = require('./security.cjs')

test('external navigation only permits supported user-facing protocols', () => {
  for (const url of ['https://doi.org/10.1/test', 'http://localhost:23119', 'zotero://select/library/items/ABC']) {
    assert.equal(safeExternalUrl(url), true)
  }
  for (const url of ['file:///etc/passwd', 'javascript:alert(1)', 'data:text/html,hi', 'ms-excel:ofe|u|x', 'bad url']) {
    assert.equal(safeExternalUrl(url), false)
  }
})

test('static handler rejects malformed and traversal URLs', () => {
  const root = path.resolve('test-dist')
  for (const url of ['/../test-dist-secret/key', '/%2e%2e/secret', '/%zz', '/..%5csecret']) {
    if (url.includes('%5c') && process.platform !== 'win32') continue
    assert.equal(resolveStaticPath(root, url), null)
  }
  assert.equal(resolveStaticPath(root, '/assets/main.js'), path.join(root, 'assets', 'main.js'))
})
