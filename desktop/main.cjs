const { app, BrowserWindow, dialog, shell } = require('electron')
const fs = require('fs')
const http = require('http')
const net = require('net')
const path = require('path')
const { spawn } = require('child_process')

let mainWindow = null
let backendProcess = null
let staticServer = null

const isPackaged = app.isPackaged
app.setAppUserModelId('cn.scholarnova.desktop')

function ensureDesktopShortcut() {
  if (process.platform !== 'win32' || !isPackaged) return
  const target = process.env.PORTABLE_EXECUTABLE_FILE || process.execPath
  const shortcutPath = path.join(app.getPath('desktop'), 'ScholarNova.lnk')
  try {
    shell.writeShortcutLink(shortcutPath, 'create', {
      target,
      cwd: path.dirname(target),
      icon: target,
      iconIndex: 0,
      description: 'ScholarNova AI 学术论文检索与研究工作台',
      appUserModelId: 'cn.scholarnova.desktop',
    })
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
  if (isPackaged) {
    return path.join(process.resourcesPath, 'backend', 'ScholarNovaBackend', 'ScholarNovaBackend.exe')
  }
  return null
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
    DEBUG: 'false',
    PORT: String(port),
    HOST: '127.0.0.1',
    RUNTIME_DIR: runtimeDir,
    DATABASE_URL: toSqliteUrl(path.join(runtimeDir, 'scholarnova.db')),
    REDIS_URL: '',
    CORS_ORIGINS: JSON.stringify([`http://127.0.0.1:${port}`, `http://localhost:${port}`]),
    ALLOWED_HOSTS: JSON.stringify(['localhost', '127.0.0.1']),
  }

  const backendExe = getBackendExecutablePath()
  if (backendExe && fs.existsSync(backendExe)) {
    backendProcess = spawn(backendExe, [], {
      env,
      windowsHide: true,
      stdio: ['ignore', outLog, errLog],
    })
    return
  }

  backendProcess = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', String(port)], {
    cwd: path.join(__dirname, '..', 'backend'),
    env,
    windowsHide: true,
    stdio: 'inherit',
  })
}

async function waitForBackend(port, timeoutMs = 30000) {
  const start = Date.now()
  const url = `http://127.0.0.1:${port}/api/v1/health/live`
  while (Date.now() - start < timeoutMs) {
    try {
      const response = await fetch(url)
      if (response.ok) return
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
    if (req.url.startsWith('/api/') || req.url.startsWith('/generated/')) {
      proxyToBackend(req, res, backendPort)
      return
    }

    const cleanUrl = decodeURIComponent((req.url || '/').split('?')[0])
    const requested = cleanUrl === '/' ? '/index.html' : cleanUrl
    let filePath = path.normalize(path.join(frontendDist, requested))

    if (!filePath.startsWith(frontendDist)) {
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

function createWindow(uiPort) {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 1180,
    minHeight: 760,
    title: 'ScholarNova',
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    backgroundColor: '#0b1220',
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  mainWindow.loadURL(`http://127.0.0.1:${uiPort}`)
}

async function bootstrap() {
  const backendPort = await getFreePort(18765)
  const uiPort = await getFreePort(18766)
  startBackend(backendPort)
  await waitForBackend(backendPort)
  await startStaticServer(uiPort, backendPort)
  createWindow(uiPort)
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
      dialog.showErrorBox('ScholarNova 启动失败', error.message)
      app.quit()
    })
  })
}

app.on('window-all-closed', () => {
  app.quit()
})

app.on('before-quit', () => {
  if (staticServer) staticServer.close()
  if (backendProcess && !backendProcess.killed) backendProcess.kill()
})
