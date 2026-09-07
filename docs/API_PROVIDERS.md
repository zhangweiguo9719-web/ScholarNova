# API Key 配置 / API setup

[中文首页](../README.zh-CN.md) · [English](../README.md)

先在提供商自己的控制台开通模型访问与 API Key，再在 ScholarNova 设置中选相应提供商。模型名称、区域和地址必须与该账户权限匹配；控制台展示的可用模型和计费政策为准。聊天订阅不必然包含 API 额度。

Create a key and enable model access in the provider's own console. Match the provider, region, endpoint and exact model ID in ScholarNova Settings. A consumer chat subscription does not necessarily include API credits.

| 提供商 / Provider | 官方入口 / Official entry | ScholarNova 用途 / Use |
| --- | --- | --- |
| 智谱 GLM | [BigModel](https://open.bigmodel.cn/) | 文本与支持视觉的模型 / text and supported vision models |
| 阿里千问 / Qwen | [阿里云百炼](https://bailian.console.aliyun.com/) | 文本、视觉、Embedding，分别配置 / configure per task |
| 硅基流动 / SiliconFlow | [控制台](https://cloud.siliconflow.cn/) | 填完整模型标识，例如 Qwen/… / use the full hosted model ID |
| 小米 MiMo | [MiMo](https://platform.xiaomimimo.com/) | 支持保留，按账户套餐选择接口 / choose the endpoint for your plan |
| 商汤 / SenseNova | [控制台](https://platform.sensenova.cn/) | 支持的图像生成任务 / supported diagram generation |
| DeepSeek | [控制台](https://platform.deepseek.com/) | 文本 / text |
| Kimi / Moonshot | [控制台](https://platform.moonshot.cn/) | 文本 / text |
| OpenAI | [API 平台](https://platform.openai.com/) | 文本、视觉、Embedding / task-specific models |
| Anthropic | [Console](https://console.anthropic.com/) | Claude adapter |
| Ollama | [Ollama](https://ollama.com/) | 本地模型 / local models |
| Semantic Scholar | [API](https://www.semanticscholar.org/product/api) | 学术检索 Key，独立于模型 Key / separate scholarly API key |
| OpenAlex | [文档](https://docs.openalex.org/) | 学术数据 / scholarly metadata |
| Hugging Face | [Tokens](https://huggingface.co/settings/tokens) | 可选受限评测数据访问；需单独接受许可 / optional gated benchmarks |

## 设置步骤 / Steps

1. 选择厂商，填写该厂商 Key、模型名称和官方 API 地址。不要把一个厂商的 Key 填到另一个厂商的地址。
2. 点击测试连接；按任务的能力探针可以实际验证 JSON、视觉等能力。探针会发请求，可能收费；保存设置本身不应调用模型。
3. 保存配置。备用文本模型须显式启用；失败尝试与备用成功调用都可能计费，Token 以供应商返回为准。
4. PDF 图表阅读需视觉模型；普通文本模型不自动变成视觉模型。图表生成、Embedding 是另外两个配置。

Choose a provider → enter credentials and a valid model ID → test → save. Optional capability probes make real calls and may incur charges. Fallback attempts can also incur cost. Vision, image generation and embeddings require compatible task profiles.

## 常见问题 / Troubleshooting

| 现象 / Symptom | 检查 / Check |
| --- | --- |
| 401/403 | Key 是否有效、是否有模型/区域权限 / key, model and region access |
| 404 | Base URL 与模型名称是否正确 / endpoint and model ID |
| 429 | 额度、余额或请求速率；等待限流冷却 / quota, balance or cooldown |
| 超时 / Timeout | 网络、代理、服务拥堵、上下文长度 / network, proxy, load, context |
| 图表未读取 / No figures read | 视觉模型权限与实际材料覆盖 / vision profile and coverage |
| 本机服务连接失败 / Local connection | 确保 localhost 与 127.0.0.1 不走代理 / bypass proxy for loopback |

不要在 Issues、截图、README 或视频中展示真实 Key。选择自定义服务地址意味着认证信息和所需材料会发送到该地址。运行时配置目前存为本机配置文件，未加密为系统钥匙串。
