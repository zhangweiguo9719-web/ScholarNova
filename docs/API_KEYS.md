# ScholarNova API Key 申请与配置指南

[中文](#中文指南) · [English](#english-guide)

> 平台入口、模型名称、计费和限流可能调整。本文只链接官方页面，填写前请再次核对平台控制台。会员订阅通常不等于 API 额度。

## 中文指南

### 最少需要什么

要使用完整 AI 分析，至少配置一个 LLM。学术搜索本身可以使用免 Key 数据源，但建议申请 Semantic Scholar 和 OpenAlex Key，以获得更稳定的限额。

### LLM 平台

| 平台 | 官方申请入口 | ScholarNova 配置 |
| --- | --- | --- |
| OpenAI | [API Keys](https://platform.openai.com/api-keys) / [Quickstart](https://platform.openai.com/docs/quickstart) | Provider=`openai`，Base URL=`https://api.openai.com/v1` |
| Anthropic | [Console API Keys](https://console.anthropic.com/settings/keys) / [文档](https://docs.anthropic.com/) | Provider=`anthropic`，使用 `ANTHROPIC_API_KEY` |
| 小米 MiMo | [开放平台](https://platform.xiaomimimo.com/) / [官方获取说明](https://mimo.mi.com/docs/en-US/quick-start/faq/api-integration) | Provider=`mimo`；按量付费 Key 与 Token Plan Key 不可混用 |
| DeepSeek | [API Keys](https://platform.deepseek.com/api_keys) / [官方文档](https://api-docs.deepseek.com/) | Provider=`deepseek`，Base URL=`https://api.deepseek.com/v1` |
| 智谱 GLM | [开放平台](https://open.bigmodel.cn/) / [快速开始](https://docs.bigmodel.cn/cn/guide/start/quick-start) | Provider=`zhipu`，Base URL=`https://open.bigmodel.cn/api/paas/v4` |
| 阿里云百炼 Qwen | [百炼控制台](https://bailian.console.aliyun.com/) / [获取 Key](https://help.aliyun.com/zh/model-studio/get-api-key) | Provider=`qwen`，Base URL=`https://dashscope.aliyuncs.com/compatible-mode/v1` |
| Moonshot Kimi | [API Keys](https://platform.moonshot.cn/console/api-keys) / [平台文档](https://platform.moonshot.cn/docs/) | Provider=`moonshot`，中国区 Base URL=`https://api.moonshot.cn/v1` |
| SenseNova | [日日新 Token Plan](https://www.sensenova.cn/token-plan) / [SenseCore 文档](https://console.sensecore.cn/micro/help/en/docs/model-as-a-service/nova/) | Provider=`sensenova`；项目主要将 U1 用于研究框架图 |
| Ollama | [官方下载](https://ollama.com/download) | Provider=`ollama`，无需云端 Key，默认本地地址 `http://localhost:11434` |
| 自定义兼容服务 | 由对应服务商提供 | Provider=`custom`，填写其 OpenAI 兼容 Base URL、模型名和 Key |

#### 通用 OpenAI 兼容环境变量

MiMo、DeepSeek、智谱、Qwen、Kimi 或其他 OpenAI 兼容服务可以复用：

```dotenv
OPENAI_API_KEY=your-provider-key
OPENAI_API_BASE=https://provider.example.com/v1
OPENAI_DEFAULT_MODEL=provider-model-name
DEFAULT_LLM_PROVIDER=deepseek
```

`DEFAULT_LLM_PROVIDER` 应改成实际 Provider，例如 `mimo`、`deepseek`、`zhipu`、`qwen`、`moonshot` 或 `custom`。

Anthropic 使用：

```dotenv
ANTHROPIC_API_KEY=your-anthropic-key
ANTHROPIC_DEFAULT_MODEL=your-claude-model
DEFAULT_LLM_PROVIDER=anthropic
```

SenseNova 框架图：

```dotenv
SENSENOVA_API_KEY=your-sensenova-key
SENSENOVA_API_BASE=https://token.sensenova.cn/v1
SENSENOVA_DEFAULT_MODEL=sensenova-u1-fast
```

### 学术数据源

| 数据源 | 是否需要 Key | 官方入口与操作 |
| --- | --- | --- |
| Semantic Scholar | 推荐 | 打开[官方 API 页面](https://www.semanticscholar.org/product/api)，填写 API Key 申请表；获批后配置 `SEMANTIC_SCHOLAR_API_KEY`。请求头由 ScholarNova 自动设置。 |
| OpenAlex | 推荐 | 登录 [OpenAlex API Key 页面](https://openalex.org/settings/api-key) 创建免费 Key，配置 `OPENALEX_API_KEY`；同时建议保留 `OPENALEX_EMAIL`。 |
| Crossref | 不需要 | 无需注册。配置 `CROSSREF_EMAIL` 进入官方推荐的 polite pool；参见[访问与鉴权](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)。 |
| arXiv | 不需要 | 使用公开 API，不需要 Key；应遵守访问频率和缓存要求。参见 [arXiv API 用户手册](https://info.arxiv.org/help/api/user-manual.html)。 |

推荐配置：

```dotenv
SEMANTIC_SCHOLAR_API_KEY=your-s2-key
OPENALEX_API_KEY=your-openalex-key
OPENALEX_EMAIL=you@example.com
CROSSREF_EMAIL=you@example.com
```

### 配置位置

Docker 部署编辑项目根目录 `.env`；本地后端开发编辑 `backend/.env`。也可以在网页“设置”中选择 Provider、模型和 Base URL。

服务端部署推荐使用 `.env`，便于容器重建后保持配置。不要把 `.env` 上传到 Git。

### 常见问题

1. **401 / Unauthorized**：Key、Base URL、区域或计费方案不匹配。
2. **429 / Too Many Requests**：等待限流窗口，降低并发，并确认 Key 的真实配额。
3. **搜索可用但 AI 分析失败**：学术 API 与 LLM API 是两类独立配置。
4. **Token 一直是 0**：确定性查询不调用模型时 Token 应为 0；执行 AI 查询规划或论文分析后才会产生模型 Token。
5. **会员已经付费但 API 不可用**：聊天产品会员和开发者 API 通常独立计费。

## English guide

ScholarNova is BYOK. Configure at least one LLM provider and, for more stable scholarly retrieval, obtain Semantic Scholar and OpenAlex credentials.

- OpenAI: [API keys](https://platform.openai.com/api-keys)
- Anthropic: [Console keys](https://console.anthropic.com/settings/keys)
- Xiaomi MiMo: [official API key guide](https://mimo.mi.com/docs/en-US/quick-start/faq/api-integration)
- DeepSeek: [platform keys](https://platform.deepseek.com/api_keys)
- Zhipu: [quickstart](https://docs.bigmodel.cn/cn/guide/start/quick-start)
- Alibaba Model Studio: [get an API key](https://help.aliyun.com/zh/model-studio/get-api-key)
- Moonshot Kimi: [API keys](https://platform.moonshot.cn/console/api-keys)
- SenseNova: [SenseNova service guide](https://console.sensecore.cn/micro/help/en/docs/model-as-a-service/nova/)
- Semantic Scholar: [API product and key request](https://www.semanticscholar.org/product/api)
- OpenAlex: [API key settings](https://openalex.org/settings/api-key)
- Crossref: [access and authentication](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)
- arXiv: [API user manual](https://info.arxiv.org/help/api/user-manual.html)

Keep every credential in `.env` or another secret store. Never commit keys, screenshots containing keys, licensed datasets, or runtime configuration.
