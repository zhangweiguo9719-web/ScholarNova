const { app, BrowserWindow, dialog, shell } = require('electron')
const fs = require('fs')
const http = require('http')
const net = require('net')
const path = require('path')
const { spawn } = require('child_process')
const { randomBytes } = require('crypto')
const { safeExternalUrl, resolveStaticPath } = require('./security.cjs')

let mainWindow = null
let backendProcess = null
let staticServer = null
let isQuitting = false
let backendRestartCount = 0
const MAX_BACKEND_RESTARTS = 5
// Never exposed to the renderer or written to the user's settings.
const backendSessionToken = randomBytes(32).toString('hex')

const isPackaged = app.isPackaged
const smokeTest = process.argv.includes('--smoke-test')
if (smokeTest && process.env.SCHOLARNOVA_SMOKE_DIR) {
  app.setPath('userData', process.env.SCHOLARNOVA_SMOKE_DIR)
}
app.setAppUserModelId('cn.scholarnova.desktop')

function ensureDesktopShortcut() {
  if (process.platform !== 'win32' || !isPackaged || smokeTest) return
  const target = process.env.PORTABLE_EXECUTABLE_FILE || process.execPath
  const shortcutPath = path.join(app.getPath('desktop'), 'ScholarNova.lnk')
  const markerPath = path.join(app.getPath('userData'), '.desktop-shortcut-initialized')
  try {
    if (fs.existsSync(markerPath)) return
    fs.mkdirSync(app.getPath('userData'), { recursive: true })
    if (fs.existsSync(shortcutPath)) {
      fs.writeFileSync(markerPath, '')
      return
    }
    const created = shell.writeShortcutLink(shortcutPath, 'create', {
      target,
      cwd: path.dirname(target),
      icon: target,
      iconIndex: 0,
      description: 'ScholarNova AI 学术论文检索与研究工作台',
      appUserModelId: 'cn.scholarnova.desktop',
    })
    if (created) fs.writeFileSync(markerPath, '')
  } catch (error) {
    // Shortcut creation is a convenience; it must never block app startup.
    console.warn('Unable to create ScholarNova desktop shortcut:', error.message)
  }
}

function getFreePort(preferredPort) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.once('error', () => {
      const fallback = net.createServer()
      fallback.listen(0, '127.0.0.1', () => {
        const port = fallback.address().port
        fallback.close(() => resolve(port))
      })
    })
    server.listen(preferredPort, '127.0.0.1', () => {
      server.close(() => resolve(preferredPort))
    })
  })
}

function getFrontendDistPath() {
  return isPackaged
    ? path.join(process.resourcesPath, 'frontend', 'dist')
    : path.join(__dirname, '..', 'frontend', 'dist')
}

function getBackendExecutablePath() {
  if (!isPackaged) return null
  const exeName = process.platform === 'win32' ? 'ScholarNovaBackend.exe' : 'ScholarNovaBackend'
  return path.join(process.resourcesPath, 'backend', 'ScholarNovaBackend', exeName)
}

function toSqliteUrl(filePath) {
  return `sqlite+aiosqlite:///${filePath.replace(/\\/g, '/')}`
}

function startBackend(port) {
  const runtimeDir = app.getPath('userData')
  fs.mkdirSync(runtimeDir, { recursive: true })
  const logsDir = path.join(runtimeDir, 'logs')
  fs.mkdirSync(logsDir, { recursive: true })
  const outLog = fs.openSync(path.join(logsDir, 'backend.stdout.log'), 'a')
  const errLog = fs.openSync(path.join(logsDir, 'backend.stderr.log'), 'a')

  const env = {
    ...process.env,
    APP_ENV: 'desktop',
    SCHOLARNOVA_DESKTOP_TOKEN: backendSessionToken,
    DEBUG: 'false',
    PORT: String(port),
    HOST: '127.0.0.1',
    RUNTIME_DIR: runtimeDir,
    DATABASE_URL: toSqliteUrl(path.join(runtimeDir, 'scholarnova.db')),
    REDIS_URL: '',
    CORS_ORIGINS: JSON.stringify([`http://127.0.0.1:${port}`, `http://localhost:${port}`]),
    ALLOWED_HOSTS: JSON.stringify(['localhost', '127.0.0.1']),
  }

  const spawnOpts = { env, cwd: runtimeDir, stdio: ['ignore', outLog, errLog] }
  if (process.platform === 'win32') spawnOpts.windowsHide = true

  const backendExe = getBackendExecutablePath()
  if (isPackaged && !fs.existsSync(backendExe)) {
    fs.closeSync(outLog)
    fs.closeSync(errLog)
    throw new Error('Bundled backend is missing. Please reinstall ScholarNova from GitHub Releases.')
  }
  if (backendExe && fs.existsSync(backendExe)) {
    backendProcess = spawn(backendExe, [], spawnOpts)
  } else {
    backendProcess = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)], {
      ...spawnOpts,
      cwd: path.join(__dirname, '..', 'backend'),
    })
  }
  fs.closeSync(outLog)
  fs.closeSync(errLog)
  backendProcess.on('error', (error) => {
    console.error('Backend failed to start:', error.message)
    if (!smokeTest) dialog.showErrorBox('ScholarNova 启动失败', error.message)
    app.quit()
  })

  // 崩溃自愈：本地服务意外退出时自动拉起，避免“后端挂了”导致整个应用不可用
  backendProcess.on('exit', (code, signal) => {
    if (isQuitting) return
    backendRestartCount += 1
    if (backendRestartCount > MAX_BACKEND_RESTARTS) {
      if (!smokeTest) dialog.showErrorBox(
        'ScholarNova 本地服务异常',
        `本地服务连续异常退出 ${MAX_BACKEND_RESTARTS} 次，请查看日志后重启应用。\n日志目录：${logsDir}`
      )
      app.quit()
      return
    }
    console.error(`ScholarNova backend exited (code=${code}, signal=${signal}); restarting (${backendRestartCount}/${MAX_BACKEND_RESTARTS})`)
    setTimeout(() => { if (!isQuitting) startBackend(port) }, 1000)
  })
}

async function waitForBackend(port, timeoutMs = 30000) {
  const start = Date.now()
  const url = `http://127.0.0.1:${port}/api/v1/health/live`
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url, {
        signal: AbortSignal.timeout(2000),
        headers: { 'x-scholarnova-session': backendSessionToken },
      })
      if (response.ok && (await response.json()).status === 'ok') return
    } catch (_) {
      // Wait and retry.
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`ScholarNova backend did not start within ${timeoutMs / 1000}s.`)
}

function contentTypeFor(filePath) {
  const ext = path.extname(filePath).toLowerCase()
  if (ext === '.html') return 'text/html; charset=utf-8'
  if (ext === '.js') return 'text/javascript; charset=utf-8'
  if (ext === '.css') return 'text/css; charset=utf-8'
  if (ext === '.svg') return 'image/svg+xml'
  if (ext === '.png') return 'image/png'
  if (ext === '.ico') return 'image/x-icon'
  if (ext === '.json') return 'application/json; charset=utf-8'
  return 'application/octet-stream'
}

function proxyToBackend(req, res, backendPort) {
  const proxyReq = http.request(
    {
      hostname: '127.0.0.1',
      port: backendPort,
      method: req.method,
      path: req.url,
      headers: {
        ...req.headers,
        host: `127.0.0.1:${backendPort}`,
        'x-scholarnova-session': backendSessionToken,
      },
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 500, proxyRes.headers)
      proxyRes.pipe(res)
    }
  )

  proxyReq.on('error', (error) => {
    res.writeHead(502, { 'content-type': 'application/json; charset=utf-8' })
    res.end(JSON.stringify({ detail: `Backend proxy failed: ${error.message}` }))
  })

  req.pipe(proxyReq)
}

function startStaticServer(uiPort, backendPort) {
  const frontendDist = getFrontendDistPath()
  staticServer = http.createServer((req, res) => {
    // Reject DNS rebinding and cross-origin requests to the desktop service.
    const origin = req.headers.origin
    if (req.headers.host !== `127.0.0.1:${uiPort}` ||
        (origin && origin !== `http://127.0.0.1:${uiPort}`)) {
      res.writeHead(403)
      res.end('Forbidden')
      return
    }
    if (req.url.startsWith('/api/') || req.url.startsWith('/generated/')) {
      proxyToBackend(req, res, backendPort)
      return
    }

    let filePath = resolveStaticPath(frontendDist, req.url)
    if (!filePath) {
      res.writeHead(403)
      res.end('Forbidden')
      return
    }

    if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      filePath = path.join(frontendDist, 'index.html')
    }

    fs.readFile(filePath, (error, data) => {
      if (error) {
        res.writeHead(500)
        res.end(error.message)
        return
      }
      res.writeHead(200, { 'content-type': contentTypeFor(filePath) })
      res.end(data)
    })
  })

  return new Promise((resolve, reject) => {
    staticServer.once('error', reject)
    staticServer.listen(uiPort, '127.0.0.1', () => resolve())
  })
}

async function createWindow(uiPort) {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 900,
    minHeight: 620,
    show: !smokeTest,
    title: 'ScholarNova',
    icon: process.platform === 'darwin'
      ? path.join(__dirname, 'assets', 'icon.png')
      : path.join(__dirname, 'assets', 'icon.ico'),
    backgroundColor: '#0b1220',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (safeExternalUrl(url)) void shell.openExternal(url)
    return { action: 'deny' }
  })
  const origin = `http://127.0.0.1:${uiPort}`
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (new URL(url).origin !== origin) {
      event.preventDefault()
      if (safeExternalUrl(url)) void shell.openExternal(url)
    }
  })
  mainWindow.webContents.session.setPermissionRequestHandler((wc, permission, callback) => {
    callback(wc === mainWindow.webContents && permission === 'clipboard-sanitized-write')
  })
  await mainWindow.loadURL(origin)
  if (smokeTest) {
    const pages = ['/', '/search', '/knowledge', '/assistant', '/settings']
    const screenshotDir = path.join(app.getPath('userData'), 'smoke-pages')
    fs.mkdirSync(screenshotDir, { recursive: true })
    for (const route of pages) {
      await mainWindow.loadURL(origin + route)
      const visible = await mainWindow.webContents.executeJavaScript(
        "new Promise(resolve => { let n = 0; const t = setInterval(() => { if (document.querySelector('#root')?.innerText.length > 40) { clearInterval(t); resolve(true) } else if (++n > 100) { clearInterval(t); resolve(false) } }, 50) })"
      )
      if (!visible) throw new Error('Empty desktop page: ' + route)
      await new Promise(resolve => setTimeout(resolve, 300))
      const screenshot = await mainWindow.webContents.capturePage()
      fs.writeFileSync(path.join(screenshotDir, (route.slice(1) || 'home') + '.png'), screenshot.toPNG())
    }
    const response = await fetch(origin + '/api/v1/health/live')
    if (!response.ok || (await response.json()).status !== 'ok') throw new Error('Desktop backend health failed')
    fs.writeFileSync(path.join(app.getPath('userData'), 'smoke-result.json'),
      JSON.stringify({ success: true, version: app.getVersion(), platform: process.platform, arch: process.arch, pages }))
    app.quit()
  }
}

async function bootstrap() {
  const backendPort = await getFreePort(18765)
  const uiPort = await getFreePort(18766)
  startBackend(backendPort)
  await waitForBackend(backendPort)
  await startStaticServer(uiPort, backendPort)
  await createWindow(uiPort)
}

const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })

  app.whenReady().then(() => {
    ensureDesktopShortcut()
    bootstrap().catch((error) => {
      console.error(error.message)
      if (!smokeTest) dialog.showErrorBox('ScholarNova 启动失败', error.message)
      app.quit()
    })
  })
}

app.on('window-all-closed', () => {
  app.quit()
})

app.on('before-quit', () => {
  isQuitting = true
  if (staticServer) staticServer.close()
  if (backendProcess && !backendProcess.killed) backendProcess.kill()
})
