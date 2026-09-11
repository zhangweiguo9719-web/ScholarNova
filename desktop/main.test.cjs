const { test } = require('node:test')
const assert = require('node:assert/strict')
const { EventEmitter } = require('node:events')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')

const mainSource = fs.readFileSync(path.join(__dirname, 'main.cjs'), 'utf8')

test('portable packaging uses direct zip extraction instead of a nested LZMA archive', () => {
  const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'package.json'), 'utf8'))
  assert.equal(manifest.build.portable.useZip, true)
})

function mockWindow({ minimized = false, destroyed = false } = {}) {
  const calls = []
  return {
    calls,
    isDestroyed: () => destroyed,
    isMinimized: () => minimized,
    restore: () => calls.push('restore'),
    show: () => calls.push('show'),
    focus: () => calls.push('focus'),
    loadURL: async url => calls.push(['loadURL', url]),
    webContents: {
      setWindowOpenHandler() {},
      on() {},
      session: { setPermissionRequestHandler() {} },
    },
  }
}

function loadMain({ smoke = false, window = mockWindow() } = {}) {
  const app = new EventEmitter()
  Object.assign(app, {
    isPackaged: false,
    setAppUserModelId() {},
    requestSingleInstanceLock: () => true,
    // Do not bootstrap servers, spawn a backend, or access user data in tests.
    whenReady: () => new Promise(() => {}),
  })
  const constructed = []
  const electron = {
    app,
    BrowserWindow: function (options) { constructed.push(options); return window },
    dialog: {},
    shell: {},
  }
  const context = vm.createContext({
    require: name => name === 'electron' ? electron : require(name),
    process: { argv: smoke ? ['--smoke-test'] : [], env: {}, platform: 'win32' },
    __dirname,
    console,
  })
  vm.runInContext(mainSource, context, { filename: 'main.cjs' })
  return {
    app, context, constructed, window,
    setWindow(value) {
      context.testWindow = value
      vm.runInContext('mainWindow = testWindow', context)
    },
  }
}

test('normal startup explicitly shows and focuses the window after loading', async () => {
  const { context, constructed, window } = loadMain()
  await context.createWindow(18766)
  assert.equal(constructed[0].show, true)
  assert.deepEqual(window.calls, [['loadURL', 'http://127.0.0.1:18766'], 'show', 'focus'])
})

test('second launch explicitly shows a hidden, non-minimized window', () => {
  const { app, setWindow, window } = loadMain()
  setWindow(window)
  app.emit('second-instance')
  assert.deepEqual(window.calls, ['show', 'focus'])
})

test('second launch restores a minimized window before showing and focusing', () => {
  const { app, setWindow, window } = loadMain({ window: mockWindow({ minimized: true }) })
  setWindow(window)
  app.emit('second-instance')
  assert.deepEqual(window.calls, ['restore', 'show', 'focus'])
})

test('missing or destroyed windows are ignored without native window calls', () => {
  const { app, setWindow, window } = loadMain({ window: mockWindow({ destroyed: true }) })
  assert.doesNotThrow(() => app.emit('second-instance'))
  setWindow(window)
  assert.doesNotThrow(() => app.emit('second-instance'))
  assert.deepEqual(window.calls, [])
})

test('smoke mode never restores, shows or focuses its hidden window', () => {
  const { app, context, setWindow, window } = loadMain({ smoke: true, window: mockWindow({ minimized: true }) })
  setWindow(window)
  context.showMainWindow()
  app.emit('second-instance')
  assert.deepEqual(window.calls, [])
})

test('second launch during bootstrap is safe and startup still reveals the window', async () => {
  const { app, context, window } = loadMain()
  app.emit('second-instance')
  await context.createWindow(18766)
  assert.deepEqual(window.calls, [['loadURL', 'http://127.0.0.1:18766'], 'show', 'focus'])
})
