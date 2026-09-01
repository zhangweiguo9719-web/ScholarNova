# ScholarNova 的 FTI 流水线架构

> 参考：Decoding AI 的 [LLM Twin Course](https://github.com/decodingai-magazine/llm-twin-course)
>
> 状态：渐进实施中；本文同时记录现状、目标边界和验收标准。

## 1. 名称与适配原则

LLM Twin 使用的是 **FTI（Feature、Training、Inference）**，不是 FIT。它还在 FTI 前面设置数据采集与 CDC，并用评测、监控和模型注册表形成发布门禁。

ScholarNova 不直接复制其“社交内容采集 + 微调个人写作模型”业务，而采用下面的科研适配：

1. **Collection / Data Pipeline**：采集论文元数据、合法全文、用户知识条目和授权文献管理器记录。
2. **Feature Pipeline**：规范化、去重、正文解析、分块、证据定位、稀疏/向量特征和索引。
3. **Evaluation & Optimization Pipeline**：使用公开基准、黄金问题集和回归样本评估检索、RAG、成本和延迟。现阶段不强制微调模型。
4. **Inference Pipeline**：意图识别、查询规划、多源检索、混合召回、重排、证据打包、模型生成和回答校验。
5. **Observability & Release Gate**：记录数据版本、提示词、模型、Token、延迟、错误和证据覆盖，控制版本发布。

核心约束：**先做模块边界和数据契约，暂不拆成多个网络微服务。** 桌面产品继续保持 Electron + React + 本地 FastAPI 的模块化单体，等确有独立扩缩容需求时再拆服务。

## 2. 当前项目映射

| 流水线 | 当前代码 | 已有能力 | 主要缺口 |
| --- | --- | --- | --- |
| 数据采集 | `services/sources`、`services/search/retriever.py`、`services/pdf`、`services/integrations/zotero.py` | 多学术 API、并发检索、PDF 获取解析、Zotero 读取 | 统一文档契约、授权馆藏连接器、增量同步 |
| 特征 | `deduplicator.py`、`constraint_verifier.py`、`evidence`、`knowledge_chunks`、`paper_chunks`、`services/retrieval` | 去重、约束验证、证据跨度、知识/PDF 分块、中英文 BM25、统一检索片段契约 | 可选向量索引、图像区域级 Chunk |
| 评测优化 | `services/evaluation/benchmark.py`、`tests/evaluation` | F1/Precision/Recall、基准适配、离线回归 | RAG 黄金集、按流水线版本对比、发布阈值 |
| 推理 | `orchestrator.py`、`ranker.py`、`llm/gateway.py`、`api/v1/agent.py` | 查询规划、多源召回、知识库/Zotero 联合排序、统一模型网关、来源约束问答 | 主备模型路由、稀疏+向量混合召回、答案充分性校验 |
| 监控门禁 | `SearchRun`、质量快照、Token 记录、GitHub Actions | 搜索耗时/API 次数、模型用量、275 项离线测试 | 统一 Trace ID、阶段耗时、线上质量抽样与数据漂移 |

## 3. 目标数据流

```mermaid
flowchart LR
    subgraph C[数据采集流水线]
      S1[Semantic Scholar / OpenAlex / Crossref / arXiv]
      S2[用户 PDF / 授权图书馆]
      S3[Zotero / RIS / BibTeX]
      N[规范化论文与文档记录]
      S1 --> N
      S2 --> N
      S3 --> N
    end

    subgraph F[特征流水线]
      D[去重与版本指纹]
      P[正文/章节/图表解析]
      K[稳定分块与证据定位]
      I[稀疏索引 + 向量索引]
      N --> D --> P --> K --> I
    end

    subgraph E[评测与优化流水线]
      G[黄金查询与公开基准]
      M[F1 / Recall / 证据覆盖 / Token / 延迟]
      R[配置与版本门禁]
      G --> M --> R
    end

    subgraph T[在线推理流水线]
      Q[问题与意图路由]
      QP[查询规划]
      H[混合召回与重排]
      EP[证据包]
      L[模型网关]
      V[引用与充分性校验]
      A[带来源回答]
      Q --> QP --> H --> EP --> L --> V --> A
      I --> H
      R --> L
    end

    O[统一追踪与发布门禁] -.监控.-> C
    O -.监控.-> F
    O -.监控.-> E
    O -.监控.-> T
```

## 4. 四类稳定数据契约

### 4.1 DocumentRecord

统一表示 API 论文、PDF、知识条目和文献管理器记录，至少包含：

- `document_id`：内部稳定 ID。
- `source` / `source_id`：来源与来源侧 ID。
- `title`、`authors`、`doi`、`year`、`venue`。
- `content_uri`、许可/访问方式与获取时间。
- `content_hash`、解析器版本和更新时间。

### 4.2 FeatureChunk

统一表示可检索的正文、知识和图表片段，至少包含：

- `chunk_id`、`document_id`、`position`。
- `content`、`content_hash`、`feature_version`。
- 章节、页码、图表编号和字符/Token 数。
- 稀疏特征、向量模型版本和索引状态。

### 4.3 EvaluationRun

记录数据集版本、检索配置、模型、提示词、指标、成本、延迟和失败原因，保证“成绩变化能解释、能复现”。

### 4.4 InferenceTrace

记录一次用户请求经过的意图路由、查询规划、数据源、候选集、重排、证据片段、模型调用、Token 和最终校验结果。隐私内容默认保存在本机。

## 5. 已落地：知识特征流水线与统一稀疏检索

本轮新增 `knowledge_chunks` 特征表和 `services/features/knowledge.py`：

1. 按段落/句子边界将长知识内容切成约 1200 字符的重叠片段。
2. 为每个片段生成由知识 ID、内容哈希、位置和特征版本决定的稳定 ID。
3. 新建、更新、删除知识条目时同步构建或清理特征。
4. 历史知识条目在第一次检索时自动补建，无需用户迁移数据。
5. 智能体检索相关片段而不是截取整条内容；同一知识条目最多占两个片段。
6. 无相关特征命中时明确返回材料不足，不回退到任意最近记录。

FTI-2A 在此基础上新增：

1. 用供应商无关的 `RetrievalChunk` 契约统一知识库和实时 Zotero 候选材料。
2. 采用不依赖外部模型的中英文 BM25，对标题、元数据和正文片段统一计分。
3. 两类来源进入同一候选池后再排序，不再各自固定占用上下文名额。
4. 每篇文档最多保留两个片段，防止一篇长文挤占全部证据位置。
5. 无相关命中时停止在检索层，不调用 LLM，因此该阶段不会新增模型 Token 成本。

FTI-2B 继续把 PDF 接入同一条流水线：

1. 新增 `paper_chunks` 特征表，保存解析器生成的摘要、章节、表格与图注片段。
2. 每个片段保留论文 ID、内容哈希、特征版本、类型、章节标题和可用页码。
3. 用户导入 PDF 时立即建立特征；后续执行全文分析时会确定性校验并同步特征。
4. 科研问答将 PDF、知识库和 Zotero 放入同一 BM25 候选池，而不是把完整长文一次塞给模型。
5. PDF 特征生成失败不会破坏原有上传和摘要分析流程，错误只影响全文检索增强。

目前仍是本地稀疏检索，不宣称已经具备向量语义召回。稳定数据契约建立后，再增加可选的本地/远程 Embedding 与向量索引；未配置向量能力时必须继续使用当前 BM25 兜底。

## 6. 分阶段优化顺序

### FTI-1：特征基线（本轮）

- 知识分块、内容哈希、特征版本、懒回填。
- 智能体片段级检索与来源多样性。
- 验收：确定性测试通过；旧数据无损；无关问题不引用随机材料。

### FTI-2：统一文档与混合检索（2A/2B 稀疏基线已完成）

- 已为知识库与 Zotero 建立统一 `RetrievalChunk`，并完成中英文 BM25 联合排序。
- 已将 PDF 的摘要、章节、表格与图注接入相同契约，并用 `paper_chunks` 持久化版本化特征。
- 下一步补齐通用 DocumentRecord 和 PDF 图像区域证据，再评估向量召回的实际收益。
- Embedding 做成可选能力，不配置时继续使用稀疏检索。
- 引入向量索引前先完成索引版本、删除同步和隐私策略。
- 验收：固定黄金集 Recall@K、MRR、证据命中率不低于基线，延迟与磁盘增长可解释。

### FTI-3：推理管线与模型主备

- 明确 `intent → plan → retrieve → rerank → evidence → generate → verify` 阶段。
- 依据模型能力选择文本、视觉、结构化输出和工具调用模型。
- 主模型失败时切备用模型；模型均不可用时返回确定性检索结果。
- 验收：每一步可观察；任何单个外部服务失败不导致整个搜索不可用。

### FTI-4：评测与发布门禁

- 将 PaSa/AstaBench 子集、产品回归问题和长文证据问题分开管理。
- 同时报 F1、Recall、证据覆盖、Token、首结果延迟、总延迟和失败率。
- 离线回归与真实联网健康检查分开；429 属于外部健康事件，不伪装成代码回归。
- 验收：每个版本自动生成可比较报告，未达到阈值不得发布。

### FTI-5：受控连接器与 MCP

- 图书馆和文献管理器通过统一 Connector/Tool 接口接入。
- 用户登录、授权范围、下载许可与写入操作显式确认。
- 将稳定工具选择性暴露为 MCP Server，核心内部调用不强制 MCP 化。
- 验收：最小权限、可撤销授权、完整操作记录和安全域名白名单。

## 7. 开发规则

1. 每个新功能必须声明属于哪条流水线、输入输出契约和失败兜底。
2. 不让 React 页面直接理解供应商 API；统一通过 FastAPI 与模型/连接器适配层。
3. 不把完整长文一次塞给 LLM；必须先检索相关片段，再分层归纳。
4. 不把 LLM-as-judge 当唯一指标；检索与引用使用确定性指标验证。
5. 不把真实联网测试混入普通回归门禁。
6. 没有黄金集和基线数据之前，不进行昂贵微调。
7. 所有 Key、登录态和个人文献默认只保存在用户本机，不进入日志和公共仓库。
