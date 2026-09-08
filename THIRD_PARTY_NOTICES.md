# Third-party notices / 第三方许可声明

ScholarNova's project-owned code retains [MIT](LICENSE), including `Copyright (c) 2026 Zhang Weiguo`. That grant does not replace the licenses of bundled dependencies.

The selected community desktop distribution includes PyMuPDF / MuPDF and follows the applicable **GNU AGPL v3 terms for the combined app**. Project-owned MIT source and independent third-party notices remain intact. This is an open-source distribution route, not a noncommercial-only license. See the [desktop license record](docs/DESKTOP_LICENSE_REVIEW.md) for the selected route and current release status.

## Where to find exact notices

- In a packaged app, inspect its resources `legal/THIRD_PARTY_NOTICES.md` and `legal/manifest.json`. The build-generated inventory records component names, versions, license declarations and copied notice checksums.
- The adjacent `legal/python/`, `legal/frontend/`, `legal/electron/` and `legal/licenses/` directories hold collected notices and full license texts. Electron's `LICENSE.electron.txt` and `LICENSES.chromium.html` must also remain in the distribution.
- Repository `LICENSES/AGPL-3.0.txt` and `LICENSES/MPL-2.0.txt` contain unmodified upstream license texts. PyMuPDF's short `COPYING` notice is retained in addition to the AGPL text.
- The matching GitHub Release is to include `ScholarNova-VERSION-corresponding-source.zip`, its `SOURCE_MANIFEST.json`, and `SHA256SUMS.txt`. See [Releases](https://github.com/zhangweiguo9719-web/ScholarNova/releases) for assets that have actually been published. The automatically generated repository ZIP is not a substitute for the assembled corresponding-source bundle.

This file is an overview, not the complete per-build inventory or a legal certification. As of 2026-09-08, the selected v1.2.1 release's materials are being assembled and verified. The actual versions and notices in a downloaded package govern that package; do not replace them with this overview.

## 中文说明

项目自有代码继续采用根目录 MIT 许可证并保留原作者声明。包含 PyMuPDF / MuPDF 的桌面组合按 GNU AGPL v3 的适用条款发行，其他独立组件保留各自许可证，不附加“禁止商用”条款。

具体第三方版本、原始声明和许可证全文见安装包资源目录中的 `legal/`；同版本 Release 将同时提供 `ScholarNova-版本-corresponding-source.zip` 和校验值。当前文档记录的是已选择的发行路线，不能替代最终产物核验，也不表示安装包已经公开发布。

模型服务、论文、期刊分区与评测数据受各自条款约束；程序的开源许可不授予这些外部内容或账号的使用权限。源码与安装包不应包含用户凭据或私人研究材料。

## Upstream references

- [PyMuPDF / MuPDF official licensing](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)
- [GNU AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html.en)
- [GNU license FAQ](https://www.gnu.org/licenses/gpl-faq.en.html)
