# Windows / macOS 桌面构建与发布

面向使用者的下载入口与签名提示见 [中文 README](../README.zh-CN.md)。桌面包包含 Electron、前端产物和 PyInstaller 后端；用户无需安装开发依赖。

## 构建前准备

- Node.js 22、Python 3.12；在目标系统与目标处理器架构原生构建。
- Windows 10/11 x64；macOS Intel 使用 Intel runner，Apple Silicon 使用 ARM64 runner。
- 不交叉复制后端二进制。Electron 的 `--arm64` 不会把 x64 Python 后端转成 ARM64。
- `npm ci`、`npm --prefix frontend ci` 安装锁定版本。

## Windows

```powershell
npm run dist:win
python scripts/packaging/smoke_desktop.py desktop/dist/win-unpacked/ScholarNova.exe
```

输出 `desktop/dist/ScholarNova-Setup-版本-x64.exe` 与 `ScholarNova-Portable-版本-x64.exe`。安装版包含卸载程序、开始菜单和桌面快捷方式。

## macOS

```bash
python -m pip install -r requirements-lock.txt
python -m pip install -e backend --no-deps
python -m pip install pyinstaller
npm run dist:mac
# Intel 默认为 mac，ARM64 通常为 mac-arm64；以实际输出目录为准
python scripts/packaging/smoke_desktop.py desktop/dist/mac-arm64/ScholarNova.app/Contents/MacOS/ScholarNova
```

输出 `ScholarNova-版本-arm64.dmg/.zip` 或 `ScholarNova-版本-x64.dmg/.zip`。macOS 图标使用 1024px 资源，不能使用 256px Windows 图标代替。

## 自动验收与版本控制

1. 修改源代码、测试和文档，完成一个可复核改动再提交；不要重写已经发布的标签。
2. 统一根 package、前端 package、两个 npm lock、后端 pyproject 和后端应用版本，执行：
   `python scripts/packaging/check_version.py`。
3. 后端非在线集成测试、前端测试/构建、桌面边界测试先通过。
4. 先完成 [桌面发行许可检查](DESKTOP_LICENSE_REVIEW.md)，落实对应许可证、源码材料或依赖替换，并记录所有者选择。确认完成后才设置仓库变量 `DESKTOP_LICENSE_REVIEWED=true`；不可仅为了跳过检查而开启。随后推送 main 与一个新的 `vX.Y.Z` 标签。
5. Desktop Release 工作流先运行回归，再在 Windows x64、macOS Intel、macOS ARM64 分别构建。
6. 每个已打包应用都要使用全新临时用户目录启动，打开五个页面并检查内置服务；失败不发布。
7. 三个平台产物齐全后生成 SHA256SUMS 并发布。许可确认后，手动运行只产生工作流附件，不创建 Release；许可确认前，手动运行仅做验证、不上传二进制附件。

包启动检查不会使用开发者 Key、论文库或桌面快捷方式。它验证独立运行与页面加载，不等价于人工视觉验收、付费模型全量测试或 Apple 公证。

## 签名、更新与备份

当前发布流程为未配置商业证书的社区构建，macOS 未配置 Developer ID 公证。普通用户仍可能遇到系统来源确认；正式商业分发须由发布者提供有效的 Windows 签名与 Apple Developer ID/公证凭据，并在真实目标机验收。不要将“成功生成 DMG”写成“通过公证”。

目前更新方式是从 Releases 下载新版，退出旧应用后安装。尚未实现后台自动更新。数据与 API 配置位于系统用户目录，升级不会主动删除；备份/迁移时先退出应用，复制完整目录。日志位于其 logs 子目录。

源代码中的 `.env`、运行时数据库和授权数据不进入打包资源。运行时仅监听 loopback；外部页面不能导航进入拥有桌面权限的窗口。服务丢失时明确提示重新安装，打包版不会依赖系统 Python。
