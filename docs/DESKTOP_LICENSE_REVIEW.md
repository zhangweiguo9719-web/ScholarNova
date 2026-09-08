# Desktop distribution license review / 桌面发行许可检查

Distribution route selected on 2026-09-08: **the combined desktop app follows the applicable GNU AGPL v3 terms. Every release must include verified package notices and matching corresponding-source materials. Download availability is determined by that version's actual GitHub Release assets.**

ScholarNova's own code retains its existing MIT license. This does not relicense bundled third-party components. In particular, the PDF implementation depends on `pymupdf==1.26.3` in `requirements-lock.txt`. PyMuPDF and MuPDF have open-source AGPL and commercial licensing options; see the [official license explanation](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright).

The desktop package bundles a Python runtime and PDF libraries, rather than asking end users to install those dependencies separately. The combined desktop distribution follows the applicable GNU AGPL v3 terms; project-owned source files remain separately available under [MIT](../LICENSE), with existing copyright notices intact. Independent third-party components retain their own terms. No commercial PyMuPDF license is assumed.

维护者已经选择继续开源：包含 PyMuPDF / MuPDF 的完整桌面组合按 GNU AGPL v3 的适用条款发行，项目自有源代码保留 MIT 与原作者声明。“不商业”是维护者当前的运营选择，不是禁止其他人商业使用的附加许可条件；GNU 许可证允许按其条款收费发行。项目不添加“仅非商业使用”限制。[GNU FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#DoesTheGPLAllowMoney)

## Observed package evidence / 实际包核对

- Locked build environment: PyMuPDF `1.26.3`, binding version `1.26.3`, embedded MuPDF `1.26.3`.
- Packaged Windows backend contains `_mupdf.pyd`, `_extra.pyd` and `mupdfcpp64.dll`. This is not merely an unused optional dependency.
- Initial inspection found missing PyMuPDF `COPYING` and certifi MPL notices; the revised collector includes original notices, full applicable license texts and a checked inventory. Each packaged release is checked again, because the wheel's short dual-license notice alone does not include the full AGPL.
- Electron's `LICENSE.electron.txt` and `LICENSES.chromium.html` are present and must be retained. PyInstaller's license includes a bundling exception; do not treat its build-tool license as identical to the PyMuPDF runtime issue.
- Local verification on 2026-09-08: the updated Windows unpacked app passed five-page startup, legal/source entry and exit checks in 21.94 seconds. The source archive had 397 members, with all 396 manifest-listed file hashes verified. These observations do not establish macOS results or public release availability; see the [acceptance report](reports/v1.2.1-consumer-readiness.zh-CN.md) for per-run evidence.

This is a bounded metadata/package inspection, not a complete audit of every native library or a legal opinion.

## Selected distribution route / 已选发行路线

The release is to carry the combined desktop app's AGPL terms, original third-party notices and matching source/build materials. Users must be able to obtain the corresponding source alongside the binary downloads without an extra charge. For modified versions made available to remote network users, review AGPL section 13 and provide the required prominent source access. These are release requirements, not a claim that uploading an MIT repository alone satisfies them. See [GNU AGPL v3, sections 1, 6 and 13](https://www.gnu.org/licenses/agpl-3.0.html.en).

采用同一 Release 提供安装包与相应源码的路线，不依赖“以后再索取源码”的承诺。每次发布均执行材料生成、内容核对及包内检查；本记录不是法律认证，构建测试通过也不等于许可义务已经全部满足。

## Source and notice locations / 源码与声明位置

| Location | Purpose |
| --- | --- |
| [Root LICENSE](../LICENSE) | Existing MIT grant and authorship for project-owned code |
| [Third-party notice overview](../THIRD_PARTY_NOTICES.md) | Scope and how to find the build-specific inventory |
| `LICENSES/AGPL-3.0.txt`, `LICENSES/MPL-2.0.txt` | Unmodified full license texts; original component notices are also retained |
| App resources `legal/THIRD_PARTY_NOTICES.md`, `legal/manifest.json` | Build-specific versions, license declarations, copied texts and checksums; staged from `desktop/release/legal/` |
| Release asset `ScholarNova-VERSION-corresponding-source.zip` | Matching application source, required dependency source and build materials |
| Archive `SOURCE_MANIFEST.json` | Commit/version, source inputs and provenance for the assembled archive |
| Release `SHA256SUMS.txt` | Checksums covering published binaries and corresponding-source archive |

These are the agreed release filenames and locations, not a statement that the assets are already available. GitHub's automatic “Source code” archive contains the repository snapshot; do not present it as the complete corresponding-source bundle without checking dependency sources and build materials. Keep source access available with each distributed version, not only the newest `main` branch.

对应源码和声明不得混入用户的 API Key、个人论文、数据库或受限评测数据。普通使用者无需下载源码即可运行应用，但可以在同版本 Release 中获取；二次修改和分发者需保留声明，并履行适用的源码提供义务。

## Release gate / 发布闸门

The repository's `DESKTOP_LICENSE_REVIEWED` gate records the accepted open-source distribution route and has been enabled. It does not waive verification: every release still must pass source-bundle checks, notice checks and native Windows x64 / macOS x64 / macOS arm64 packaged-app smoke tests. Recheck the inventory when bundled dependencies change. A release is available only when its assets actually appear on GitHub Releases.

Windows commercial code signing and Apple notarization are separate from dependency licensing. Passing build/startup tests proves neither legal clearance nor platform signing.
