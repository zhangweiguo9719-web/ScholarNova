<p align="center"><img src="docs/assets/scholarnova-cover-en.svg" width="800" alt="ScholarNova — AI Research Workspace"></p>
<p align="center"><a href="https://github.com/zhangweiguo9719-web/ScholarNova/releases/latest">Download / 下载</a> · <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a> · <a href="CHANGELOG.md">Changelog</a></p>
<p align="center"><a href="https://github.com/zhangweiguo9719-web/ScholarNova/actions/workflows/ci.yml"><img src="https://github.com/zhangweiguo9719-web/ScholarNova/actions/workflows/ci.yml/badge.svg" alt="CI"></a> <a href="https://github.com/zhangweiguo9719-web/ScholarNova/actions/workflows/desktop-release.yml"><img src="https://github.com/zhangweiguo9719-web/ScholarNova/actions/workflows/desktop-release.yml/badge.svg" alt="Desktop builds"></a> <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-d4a84f" alt="MIT"></a></p>

# ScholarNova

一个面向个人研究者的桌面科研工作台：**找论文 → 读全文 → 存知识 → 基于证据问答 → 规划研究路线**。支持中文 / English、明暗主题和自带模型 API Key（BYOK）。

## 下载与安装

到 **[GitHub Releases 下载已发布安装包](https://github.com/zhangweiguo9719-web/ScholarNova/releases/latest)**，展开 Assets，按你的电脑选择。源码中的版本号或 Git 标签不代表安装包已经发布；以 Release 中实际存在的文件为准。

| 你的电脑 | 选择文件 | 安装方法 |
| --- | --- | --- |
| Windows 10/11，64 位 | `ScholarNova-Setup-版本-x64.exe` | 运行安装向导，创建桌面与开始菜单快捷方式 |
| Windows 免安装 | `ScholarNova-Portable-版本-x64.exe` | 放在固定目录后双击运行 |
| Mac，Apple Silicon（M 系列） | `ScholarNova-版本-arm64.dmg` | 拖入“应用程序” |
| Mac，Intel | `ScholarNova-版本-x64.dmg` | 拖入“应用程序” |

桌面版自带界面、本地后端和 SQLite，无需安装 Python、Node.js 或 Docker。首次启动可能因解压运行时稍慢。升级前退出应用，安装新版本；个人数据位于用户目录，不在安装目录内。

**签名状态：当前构建未配置商业代码签名与 Apple 公证。** Windows 可能显示 SmartScreen 提示；macOS 可能需要在“系统设置 → 隐私与安全性”允许打开。仅在确认下载来源和校验值后操作，不需要关闭系统安全保护。正式零干预安装体验仍需要发布者完成签名与公证。

## 第一次使用

1. **设置模型**：打开“设置”，选择 GLM、千问、硅基流动或其他已支持厂商，填写自己的 Key 和该平台可用的模型名称，测试后保存。无需更改代码。
2. **搜索论文**：输入研究问题。界面显示检索耗时、真实数据源、结果数量和来源状态；同一关键词可以再次搜索。
3. **分析全文**：选择论文并分析。找不到开放全文时，可上传自己有权使用的 PDF；界面会区分全文、摘要及实际读取的图表页。
4. **积累知识**：将分析整理保存为知识条目，再在“智能体”中按研究方向建立文件夹与独立对话。
5. **生成路线**：从知识库进行研究分析，再生成研究路线和架构图。文本、视觉和出图可分别选用不同模型。

普通关键词检索不要求 LLM Key；学术源是否可用取决于各源政策、Key、额度与网络。需要 AI 的操作会调用你配置的模型，费用由相应提供商计收。

## 产品预览

截图展示产品工作流；点击可查看原尺寸。中英文与明暗主题均可在应用中切换。

<table>
<tr>
<td width="50%" valign="top"><strong>多源检索与论文详情</strong><br><a href="docs/assets/screenshots/search-results-zh.png"><img src="docs/assets/screenshots/search-results-zh.png" width="100%" alt="论文检索"></a></td>
<td width="50%" valign="top"><strong>研究分析</strong><br><a href="docs/assets/screenshots/knowledge-analysis-zh.png"><img src="docs/assets/screenshots/knowledge-analysis-zh.png" width="100%" alt="知识库分析"></a></td>
</tr>
<tr>
<td width="50%" valign="top"><strong>个人知识库</strong><br><a href="docs/assets/screenshots/knowledge-zh.png"><img src="docs/assets/screenshots/knowledge-zh.png" width="100%" alt="知识条目"></a></td>
<td width="50%" valign="top"><strong>研究路线与架构图</strong><br><a href="docs/assets/screenshots/route-zh.png"><img src="docs/assets/screenshots/route-zh.png" width="100%" alt="研究路线"></a></td>
</tr>
</table>

<details>
<summary>更多界面：主页、模型设置、英文深色模式</summary>

点击查看完整截图，避免长图占用首页空间。

[主页](docs/assets/screenshots/home-zh.png) · [模型设置](docs/assets/screenshots/settings-zh.png) · [English / dark](docs/assets/screenshots/search-results-en-dark.png)

</details>

## 你能用它做什么

| 场景 | 已有能力 |
| --- | --- |
| 复杂文献检索 | 查询分解、多源并行召回、去重、条件过滤与综合排序；相关度和引用影响力分别展示 |
| 论文阅读 | 正文、章节、表格、图注和可用图表页；本地 PDF 导入；标题中文翻译；可拖宽的侧栏 |
| 个人研究积累 | 知识条目、研究路线、结构化架构图；按研究方向组织智能体对话 |
| 有来源的问答 | BM25，或可选 Embedding + RRF；提供文献/片段定位、引用检查和工具记录 |
| 多模型使用 | 主模型、备用模型及任务配置；统计供应商返回的 Token，控制超时与重试 |
| 文献工具联动 | 检测本机 Zotero、读取集合和导入元数据；论文页可显式请求导出，写入能力由本机接口实际决定 |

**回答有边界**：引用检查验证来源编号与逐句覆盖，不能证明每个结论都被原文支持。证据不足会提示补充材料；模型失败或引用修订未通过时返回有来源的原文摘录，明确说明原因。

**缓存有边界**：搜索结果和临时分析在离开搜索页时清理，最近检索词只保留在当前窗口会话；知识条目与智能体对话属于用户保存的资料。

## 配置与连接

- [API Key 申请入口与配置说明](docs/API_PROVIDERS.md)：GLM、千问 / 百炼、硅基流动、MiMo、SenseNova、OpenAI、Ollama 等。
- **Zotero**：先启动 Zotero，在“设置 → 高级”打开“允许此计算机上的其他应用程序与 Zotero 通讯”，然后到 ScholarNova 设置中检测并选择集合。读取成功不等于写入授权；写入失败时请按提示使用标准文献导出。
- **学校图书馆**：提供门户跳转和检索词传递。统一身份认证、校园网或学校认可的 VPN 仍由用户完成，当前不自动代登录或批量下载订阅全文。
- **期刊分区**：开放引用指标可直接展示；JCR / 中科院分区需要导入有授权且注明年份的数据。缺失显示未知，不能用引用次数猜分区。
- **代理与网络**：不同 API、图书馆和本机 Zotero 的网络需求不同。确保 `localhost`、`127.0.0.1` 不走代理；按实际报错检查地址、模型权限、额度与网络。

## 本地数据与隐私

数据位于 Windows 的 `%APPDATA%/scholarnova-desktop` 或 macOS 的 `~/Library/Application Support/scholarnova-desktop`。迁移或备份前退出应用，并复制完整用户数据目录。Key 保存在本机后端配置，不写入浏览器持久存储、公开仓库或安装包；当前配置文件不是系统钥匙串加密存储，请保护好备份。

调用云模型会把当前操作所需的问题和选中材料发给所选提供商；Key 也会随认证请求发送到所配置的服务地址。使用第三方或自定义地址前应核对来源与隐私政策。

## 开发、架构与验证

React + TypeScript 构建界面，Electron 提供桌面外壳，FastAPI 编排本地服务，SQLite 保存数据。多源搜索、PDF 解析、模型路由和检索增强问答分别实现，便于替换提供商与排查问题。

- [源码部署与开发](docs/DEVELOPMENT.zh-CN.md)
- [Windows / macOS 打包、测试和版本发布](docs/desktop-release.zh-CN.md)
- [FTI 流水线架构](docs/FTI_PIPELINE_ARCHITECTURE.zh-CN.md) · [产品路线图](docs/AI_APPLICATION_ROADMAP.zh-CN.md)
- [本轮改进与验收报告](docs/reports/v1.2.1-consumer-readiness.zh-CN.md) · [版本记录](CHANGELOG.md)

历史 Asta 18 题验证子集 F1 为 **0.341379**；66 题中具备二元标签的 27 题 F1 为 **0.283713**。这不是完整竞赛成绩，也不表示超过其他数据集上的 SPAR。此次产品修复不把历史分数当成新版本测评结果。[原始评测报告](outputs/competition-benchmark-report-2026-07-02.md)

## 反馈与参与

欢迎通过 [Issues](https://github.com/zhangweiguo9719-web/ScholarNova/issues) 提交使用问题，附上系统版本、应用版本、操作步骤和脱敏错误信息。不要附上 API Key 或私有论文。开发贡献见 [CONTRIBUTING](CONTRIBUTING.md)，安全反馈见 [SECURITY](SECURITY.md)。

[MIT License](LICENSE)。第三方模型、数据源和论文受各自条款约束。
