const path = require('node:path')

function safeExternalUrl(value) {
  try {
    const url = new URL(value)
    return ['https:', 'http:', 'mailto:', 'zotero:'].includes(url.protocol)
  } catch { return false }
}

function resolveStaticPath(root, url) {
  try {
    const pathname = decodeURIComponent((url || '/').split('?')[0])
    const target = path.resolve(root, '.' + (pathname.startsWith('/') ? pathname : '/' + pathname))
    const relative = path.relative(path.resolve(root), target)
    if (relative.startsWith('..') || path.isAbsolute(relative)) return null
    return target
  } catch { return null }
}

module.exports = { safeExternalUrl, resolveStaticPath }
