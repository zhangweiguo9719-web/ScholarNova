const path = require('path')
const { rcedit } = require('rcedit')

module.exports = async function afterPack(context) {
  if (context.electronPlatformName !== 'win32') return

  const appInfo = context.packager.appInfo
  const executable = path.join(context.appOutDir, `${appInfo.productFilename}.exe`)

  await rcedit(executable, {
    icon: path.join(__dirname, 'assets', 'icon.ico'),
    'file-version': appInfo.version,
    'product-version': appInfo.version,
    'requested-execution-level': 'asInvoker',
    'version-string': {
      CompanyName: 'ScholarNova',
      FileDescription: 'ScholarNova AI Academic Research Workspace',
      InternalName: 'ScholarNova',
      LegalCopyright: 'Copyright © 2026 ScholarNova',
      OriginalFilename: 'ScholarNova.exe',
      ProductName: 'ScholarNova',
    },
  })
}
