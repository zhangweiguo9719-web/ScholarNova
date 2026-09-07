const http = require('node:http')

function proxyToBackend(req, res, backendPort, sessionToken) {
  const upstream = http.request({
    hostname: '127.0.0.1',
    port: backendPort,
    method: req.method,
    path: req.url,
    headers: { ...req.headers, host: `127.0.0.1:${backendPort}`, 'x-scholarnova-session': sessionToken },
  }, (response) => {
    if (res.destroyed || res.writableEnded) {
      response.destroy()
      return
    }
    // A backend can disconnect after sending headers (including during quit).
    // A streamed response cannot be replaced with a second HTTP status line.
    response.on('error', () => res.destroy())
    response.on('aborted', () => res.destroy())
    res.writeHead(response.statusCode || 502, response.headers)
    response.pipe(res)
  })

  upstream.on('error', () => {
    if (res.destroyed || res.writableEnded) return
    if (res.headersSent) {
      res.destroy()
      return
    }
    res.writeHead(502, { 'content-type': 'application/json; charset=utf-8' })
    res.end(JSON.stringify({ detail: 'The local service connection was interrupted. Please retry.' }))
  })
  const abortUpstream = () => upstream.destroy()
  req.on('aborted', abortUpstream)
  req.on('error', abortUpstream)
  res.on('close', abortUpstream)
  req.pipe(upstream)
}

module.exports = { proxyToBackend }
