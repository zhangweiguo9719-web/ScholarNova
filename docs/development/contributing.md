# 贡献指南

感谢您对 ScholarAgent 项目的关注！本文档介绍如何参与项目贡献。

## 1. 贡献方式

### 1.1 代码贡献

- 修复 Bug
- 添加新功能
- 优化性能
- 改进代码质量

### 1.2 非代码贡献

- 完善文档
- 报告问题
- 提出建议
- 分享项目

## 2. 开发流程

### 2.1 Fork 项目

1. 访问项目 GitHub 页面
2. 点击右上角 "Fork" 按钮
3. 选择你的 GitHub 账号

### 2.2 克隆代码

```bash
# 克隆你的 Fork
git clone https://github.com/your-username/scholar-agent.git
cd scholar-agent

# 添加上游仓库
git remote add upstream https://github.com/original-org/scholar-agent.git

# 验证远程仓库
git remote -v
```

### 2.3 创建分支

```bash
# 同步上游代码
git fetch upstream
git checkout main
git merge upstream/main

# 创建功能分支
git checkout -b feature/your-feature-name

# 或修复分支
git checkout -b fix/your-bug-fix
```

**分支命名规范**:
- `feature/` - 新功能
- `fix/` - Bug 修复
- `docs/` - 文档更新
- `test/` - 测试相关
- `refactor/` - 代码重构

### 2.4 开发代码

```bash
# 搭建开发环境
# 参考 docs/development/setup.md

# 编写代码
# 遵循 docs/development/coding-standards.md

# 编写测试
# 参考 docs/development/testing-guide.md
```

### 2.5 提交代码

```bash
# 查看修改状态
git status

# 添加修改
git add .

# 或添加特定文件
git add path/to/file

# 提交修改
git commit -m "feat: add your feature description"
```

**提交信息规范**:
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**类型说明**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 代码重构
- `style`: 代码格式调整
- `perf`: 性能优化
- `chore`: 构建/工具相关

**示例**:
```
feat(api): add search endpoint

- Add POST /api/v1/search endpoint
- Implement query parsing
- Add input validation

Closes #123
```

### 2.6 推送代码

```bash
# 推送到你的 Fork
git push origin feature/your-feature-name
```

### 2.7 创建 Pull Request

1. 访问你的 Fork 页面
2. 点击 "Compare & pull request"
3. 填写 PR 描述
4. 选择 reviewers
5. 提交 PR

## 3. Pull Request 规范

### 3.1 PR 标题

**格式**: `<type>(<scope>): <description>`

**示例**:
- `feat(api): add search endpoint`
- `fix(database): fix connection timeout`
- `docs(readme): update installation guide`

### 3.2 PR 描述

**模板**:
```markdown
## 描述

简要描述这个 PR 做了什么。

## 修改内容

- 修改 1
- 修改 2
- 修改 3

## 测试

- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试通过

## 相关 Issue

Closes #123

## 截图（如适用）

[截图]
```

### 3.3 PR 检查清单

- [ ] 代码符合项目规范
- [ ] 已添加/更新测试
- [ ] 测试全部通过
- [ ] 已更新文档（如需要）
- [ ] 没有合并冲突
- [ ] PR 描述清晰完整

## 4. 代码审查

### 4.1 审查流程

1. 提交 PR
2. 自动运行 CI 检查
3. 人工代码审查
4. 修复审查意见
5. 审查通过
6. 合并代码

### 4.2 审查要点

**代码质量**:
- 代码风格是否符合规范
- 是否有类型注解
- 是否有文档字符串
- 是否有错误处理

**测试覆盖**:
- 是否有测试覆盖
- 测试是否充分
- 测试是否清晰

**安全性**:
- 是否有安全漏洞
- 敏感信息是否暴露
- 输入是否验证

**性能**:
- 是否有性能问题
- 是否有优化空间

### 4.3 修复审查意见

```bash
# 修改代码
# ...

# 提交修改
git add .
git commit -m "fix: address review comments"

# 推送更新
git push origin feature/your-feature-name
```

## 5. 报告问题

### 5.1 Issue 模板

**Bug 报告**:
```markdown
## Bug 描述

简要描述 bug。

## 复现步骤

1. 步骤 1
2. 步骤 2
3. 步骤 3

## 预期行为

描述预期行为。

## 实际行为

描述实际行为。

## 环境信息

- OS: [例如 Windows 11, macOS 14]
- Python: [例如 3.11.0]
- Node.js: [例如 18.0.0]
- Browser: [例如 Chrome 120]

## 日志/截图

[日志或截图]
```

**功能请求**:
```markdown
## 功能描述

简要描述功能。

## 使用场景

描述使用场景。

## 建议实现

描述建议实现方式。

## 替代方案

描述替代方案。
```

### 5.2 提交 Issue

1. 访问项目 Issues 页面
2. 点击 "New issue"
3. 选择模板
4. 填写内容
5. 提交 Issue

## 6. 文档贡献

### 6.1 文档结构

```
docs/
├── api/                    # API 文档
├── architecture/           # 架构文档
├── deployment/             # 部署文档
├── development/            # 开发指南
├── demo/                   # 演示材料
└── adr/                    # 架构决策记录
```

### 6.2 文档规范

**语言**: 使用中文

**格式**: 使用 Markdown

**风格**: 简洁明了，易于理解

**示例**: 提供实际可运行的命令和示例

### 6.3 文档提交

```bash
# 修改文档
# ...

# 提交文档
git add docs/
git commit -m "docs: update documentation"

# 推送
git push origin docs/your-doc-update
```

## 7. 社区参与

### 7.1 交流方式

- **GitHub Issues**: 问题讨论和功能请求
- **GitHub Discussions**: 一般性讨论
- **Pull Requests**: 代码贡献

### 7.2 行为准则

**尊重他人**:
- 使用友善的语言
- 尊重不同观点
- 避免人身攻击

**专业态度**:
- 提供有价值的反馈
- 遵循项目规范
- 保持积极态度

### 7.3 获得帮助

**提问方式**:
1. 先搜索已有 Issue
2. 使用清晰的标题
3. 提供详细信息
4. 保持耐心

**示例**:
```
标题: [BUG] 搜索功能返回空结果

描述:
- 操作系统: Windows 11
- Python 版本: 3.11.0
- 复现步骤: ...
- 预期结果: ...
- 实际结果: ...
- 日志信息: ...
```

## 8. 发布流程

### 8.1 版本号规范

**语义化版本**: `MAJOR.MINOR.PATCH`

- `MAJOR`: 不兼容的 API 修改
- `MINOR`: 向后兼容的功能性新增
- `PATCH`: 向后兼容的问题修正

**示例**:
- `1.0.0` - 初始版本
- `1.1.0` - 添加新功能
- `1.1.1` - 修复 bug

### 8.2 发布步骤

```bash
# 更新版本号
# 编辑 backend/app/__init__.py
# 编辑 frontend/package.json

# 更新 CHANGELOG
# 编辑 CHANGELOG.md

# 提交版本更新
git add .
git commit -m "release: v1.1.0"

# 创建标签
git tag -a v1.1.0 -m "Release v1.1.0"

# 推送标签
git push upstream v1.1.0
```

### 8.3 CHANGELOG 格式

```markdown
# Changelog

## [1.1.0] - 2025-06-27

### Added
- 添加搜索 API 端点
- 添加论文分析功能
- 添加推荐系统

### Changed
- 优化查询解析性能
- 改进用户界面

### Fixed
- 修复数据库连接问题
- 修复前端显示 bug

## [1.0.0] - 2025-06-01

### Added
- 初始版本发布
- 基础搜索功能
- 论文展示功能
```

## 9. 贡献者指南

### 9.1 新贡献者

**入门步骤**:
1. 阅读项目 README
2. 搭建开发环境
3. 阅读代码规范
4. 查看 "good first issue" 标签
5. 选择一个简单任务开始

**推荐任务**:
- 修复文档错误
- 添加测试用例
- 改进错误消息
- 优化代码注释

### 9.2 经验贡献者

**高级任务**:
- 实现新功能
- 优化性能
- 重构代码
- 指导新贡献者

### 9.3 核心贡献者

**职责**:
- 审查 Pull Request
- 回答问题
- 维护项目
- 规划路线图

## 10. 常见问题

### 10.1 如何开始贡献？

1. Fork 项目
2. 克隆到本地
3. 搭建开发环境
4. 查看 "good first issue"
5. 选择任务开始

### 10.2 如何提交 PR？

1. 创建功能分支
2. 编写代码和测试
3. 提交代码
4. 推送到 Fork
5. 创建 Pull Request

### 10.3 如何报告 Bug？

1. 访问 Issues 页面
2. 使用 Bug 报告模板
3. 提供详细信息
4. 提交 Issue

### 10.4 如何提出建议？

1. 访问 Issues 页面
2. 使用功能请求模板
3. 描述使用场景
4. 提交 Issue

## 11. 联系方式

- **GitHub Issues**: 问题讨论和功能请求
- **GitHub Discussions**: 一般性讨论
- **Email**: team@scholar-agent.dev

## 12. 致谢

感谢所有贡献者的努力！您的贡献让项目变得更好。

### 贡献者列表

<!-- 贡献者列表将自动生成 -->

[![Contributors](https://contrib.rocks/image?repo=original-org/scholar-agent)](https://github.com/original-org/scholar-agent/graphs/contributors)
