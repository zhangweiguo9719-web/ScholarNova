# ScholarNova Windows 桌面版发布说明

桌面版用于降低普通用户的本地部署成本。发布者在 Windows 上执行打包命令后，GitHub Releases 可以提供 `.exe` 安装包和便携版，使用者下载后直接运行。

## 使用者怎么用

1. 从 [GitHub Releases](https://github.com/zhangweiguo9719-web/ScholarNova/releases/latest) 下载 `ScholarNova-Setup-版本号-x64.exe`，或下载无需安装的 `ScholarNova-Portable-版本号-x64.exe`。
2. 安装并启动 ScholarNova；便携版直接双击运行。
3. 打开“设置”，填写自己的模型服务 API Key，例如 OpenAI 兼容接口、MiMo、SenseNova、Semantic Scholar Key 等。
4. 回到搜索页开始检索、分析、保存知识库和生成研究路线。

首次启动时需要解压内置运行时，便携版窗口通常会在 10–30 秒内出现；后续启动更快。

桌面版不会内置作者本人的 API Key，也不会内置受限数据集。

## 发布者怎么打包

环境要求：

- Windows 10/11
- Node.js 18+
- Python 3.11+
- 项目依赖已可正常安装

首次准备：

```powershell
npm ci
npm --prefix frontend ci
```

构建 Windows 安装包和便携版：

```powershell
npm run dist:win
```

如果当前 Python 环境被 Anaconda 或旧依赖污染，可以单独使用隔离构建命令：

```powershell
npm run build:backend:venv
```

产物位置：

```text
desktop/dist/
```

生成文件：

- `ScholarNova-Setup-版本号-x64.exe`：带卸载程序、桌面快捷方式和开始菜单入口。
- `ScholarNova-Portable-版本号-x64.exe`：无需安装，适合临时体验或移动存储。

## GitHub 自动发布

仓库内的 `Windows Desktop Release` 工作流支持手动构建和版本标签发布。推送 `v*` 标签后，GitHub Actions 会在 Windows 环境重新构建两个 `.exe`，创建对应 Release 并上传文件：

```powershell
git tag v1.0.0
git push origin v1.0.0
```

公开 Release 使用干净的 GitHub 构建环境，不会读取开发者电脑中的 `.env` 或 API Key。

## 桌面版运行机制

- Electron 作为桌面应用外壳。
- 应用启动时自动拉起内置 FastAPI 后端。
- 前端静态资源由本地 127.0.0.1 服务加载。
- `/api/*` 和 `/generated/*` 请求会转发到内置后端。
- 数据库、模型配置和生成图片保存在用户 AppData 目录，不写入安装目录。

## 注意事项

- GitHub 公开仓库不要提交 `.env`、数据库、个人 API Key、授权数据集。
- 如果用户需要调用付费模型，必须在设置页填自己的 Key。
- Windows Defender 可能会对未签名 exe 提示风险，这是未做代码签名的常见情况；正式发布建议配置代码签名证书。
- 本地构建不要求管理员权限；项目使用独立资源编辑步骤写入应用图标和版本信息。
