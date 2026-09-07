const { test } = require('node:test')
const assert = require('node:assert/strict')
const http = require('node:http')
const { once } = require('node:events')
const { proxyToBackend } = require('./proxy.cjs')

async function listen(t, handler) {
  const server = http.createServer(handler)
  server.listen(0, '127.0.0.1')
  await once(server, 'listening')
  t.after(() => new Promise(resolve => { server.closeAllConnections(); server.close(resolve) }))
  return server.address().port
}

async function proxy(t, handler) {
  const backend = await listen(t, handler)
  return listen(t, (req, res) => proxyToBackend(req, res, backend, 'test-session-token'))
}

test('desktop proxy preserves a normal response and injects its session token', async (t) => {
  const port = await proxy(t, (req, res) => {
    assert.equal(req.headers['x-scholarnova-session'], 'test-session-token')
    res.writeHead(201, { 'content-type': 'text/plain' })
    res.end('saved')
  })
  const result = await fetch(`http://127.0.0.1:${port}/api/test`)
  assert.equal(result.status, 201)
  assert.equal(await result.text(), 'saved')
})

test('backend failure before headers produces one 502 response', async (t) => {
  const port = await proxy(t, (req) => req.socket.destroy())
  const result = await fetch(`http://127.0.0.1:${port}/api/test`)
  assert.equal(result.status, 502)
  assert.match((await result.json()).detail, /interrupted/)
})

test('backend disconnect after streamed headers closes the response without throwing', { timeout: 5000 }, async (t) => {
  const port = await proxy(t, (_req, res) => {
    res.writeHead(200, { 'content-type': 'text/event-stream' })
    res.write('data: started\n\n')
    setTimeout(() => res.destroy(), 30)
  })
  await new Promise((resolve, reject) => {
    const request = http.get(`http://127.0.0.1:${port}/api/test`, response => {
      assert.equal(response.statusCode, 200)
      response.on('data', () => {})
      response.on('aborted', resolve)
      response.on('error', () => {})
      response.on('end', () => reject(new Error('Expected interrupted stream')))
    })
    request.on('error', reject)
  })
})

test('closing the browser response also closes its upstream request', { timeout: 5000 }, async (t) => {
  let upstreamClosed
  const closed = new Promise(resolve => { upstreamClosed = resolve })
  const port = await proxy(t, (_req, res) => {
    res.on('close', upstreamClosed)
    res.writeHead(200, { 'content-type': 'text/event-stream' })
    res.write('data: started\n\n')
  })
  const request = http.get(`http://127.0.0.1:${port}/api/test`, response => {
    response.once('data', () => response.destroy())
    response.on('error', () => {})
  })
  request.on('error', () => {})
  await closed
})
