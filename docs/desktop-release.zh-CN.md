# Windows / macOS 桌面构建与发布

面向使用者的下载入口与签名提示见 [中文 README](../README.zh-CN.md)。桌面包包含 Electron、前端产物和 PyInstaller 后端；用户无需安装开发依赖。

**v1.2.1 发行状态**：已选择包含 PyMuPDF 的 AGPL 开源桌面发行路线，正在补齐并核验许可声明、对应源码和最终产物；本文不是安装包已公开下载的声明。以 GitHub Release 实际附件为准。

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
4. 本轮已选择 AGPL 开源发行；完成 [桌面发行许可检查](DESKTOP_LICENSE_REVIEW.md) 中的声明、相应源码与最终包内容核验。只有材料验收完成后，才可通过工作流的许可闸门（当前使用 `DESKTOP_LICENSE_REVIEWED=true`），不能只凭选择开源就跳过检查。随后推送 main 与一个新的 `vX.Y.Z` 标签。
5. Desktop Release 工作流先运行回归，再在 Windows x64、macOS Intel、macOS ARM64 分别构建。
6. 每个已打包应用都要使用全新临时用户目录启动，打开五个页面并检查内置服务；失败不发布。
7. 三个平台产物与同版本对应源码齐全后，生成覆盖全部公开文件的 `SHA256SUMS.txt` 再发布。许可材料验收前，手动运行仅用于验证，不公开二进制附件；验收后手动运行是否上传附件与标签发布的区别，以工作流为准。

包启动检查不会使用开发者 Key、论文库或桌面快捷方式。它验证独立运行与页面加载，不等价于人工视觉验收、付费模型全量测试或 Apple 公证。

## 许可与相应源码材料

根目录 [LICENSE](../LICENSE) 的 MIT 条款与作者声明保持不变，适用于项目自有代码。包含 PyMuPDF / MuPDF 的完整桌面发行组合按 GNU AGPL v3 的适用条款提供，独立第三方组件保留原许可。维护者暂不商业运营不构成禁止他人商用的许可条款。

- 原始许可文本与包级清单暂存于 `desktop/release/legal/`，随应用资源打包到 `legal/`。核对 `THIRD_PARTY_NOTICES.md`、`manifest.json` 和原始文本的实际内容；根目录的 [第三方声明概览](../THIRD_PARTY_NOTICES.md) 不能替代它们。
- 在同一 Release 中提供 `ScholarNova-版本-corresponding-source.zip`。归档应对应构建的提交及锁定依赖，包含应用源码、适用的第三方源码、许可证和构建/安装材料；用 `SOURCE_MANIFEST.json` 记录来源并验证。GitHub 自动生成的仓库源码 ZIP 不自动包含依赖源码。
- 安装包、对应源码与校验文件应一同发布、保持可访问。不要让某个版本的入口只指向会变化的 `main`。
- 如将修改版本提供给远程网络用户，还需按适用的 AGPL 第 13 条提供明显的相应源码入口。依据见 [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html.en)。

这套流程是工程发行材料要求，不是法律认证。仍须对实际依赖、产物和源码范围进行核验；用户 Key、个人数据库、私有论文与受限评测数据不属于公开源码包内容。

## 签名、更新与备份

当前发布流程未配置 Windows 代码签名证书与 macOS Developer ID/公证。普通用户仍可能遇到系统来源确认；若要降低安装阻力，需要发布者配置有效凭据并在真实目标机验收，这与是否商业运营、采用何种开源许可是不同问题。不要将“成功生成 DMG”写成“通过公证”。

目前更新方式是从 Releases 下载新版，退出旧应用后安装。尚未实现后台自动更新。数据与 API 配置位于系统用户目录，升级不会主动删除；备份/迁移时先退出应用，复制完整目录。日志位于其 logs 子目录。

源代码中的 `.env`、运行时数据库和授权数据不进入打包资源。运行时仅监听 loopback；外部页面不能导航进入拥有桌面权限的窗口。服务丢失时明确提示重新安装，打包版不会依赖系统 Python。
