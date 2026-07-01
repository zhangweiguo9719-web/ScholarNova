# ScholarNova 质量分析、官方数据集与完整验收报告

日期：2026-07-01

## 1. 最终结论

- 产品主链路可用：搜索、论文详情、真实 AI 分析、知识库、研究路线、SenseNova-U1 架构图、明暗主题均已通过浏览器实测。
- 论文结果不再只显示标题：当前卡片包含作者、年份、发表源、摘要、引用数、相关度、质量分、候选集引用百分位、年均引用和影响力标签。
- 知识库现有 13 条记录，其中交通流预测专题 12 篇；研究路线关联 12 篇论文。
- “全面分析”已真实调用模型并成功返回六部分结构化结果，约 52 秒完成，未复现此前的 HTTP 500 / Connection error。
- 已获得并验证 PaSa 与 AstaBench 官方数据集访问，四个评测文件均已下载到本机。
- PaSa RealScholarQuery 50 条已完成一次全量、可复现的 Crossref 基线评测：F1 = 0.006030。该结果较低，但是真实指标，不做粉饰。
- Semantic Scholar Key 本身有效；其搜索端点在本轮持续出现 429/500，导致 Asta 的 CorpusId 检索无法形成可信全集分数。报告明确记录为外部限流，不伪造指标。

## 2. 实际优化内容

### 搜索与排序

- 复杂查询拆解、查询压缩与关键词扩展。
- 多来源检索状态、失败来源和 API 调用量可观察。
- Semantic Scholar 全局节流，按批准额度保守设置调用间隔。
- 查询中的连字符和低价值词归一化，降低 Semantic Scholar 无结果概率。
- 批量数据库查重，减少 N+1 查询。
- 结果先返回、长尾持久化后置，降低用户等待时间。
- MMR 多样性重排限制在 Top-50，避免不必要的二次复杂度。

### 论文质量分析

每篇论文展示：

- 原始引用数、年份、发表源、开放获取状态。
- 查询相关度与高度相关/部分相关/探索结果分层。
- `quality_score`：75% 候选集引用百分位 + 25% 归一化年均引用。
- `citation_percentile`：在当前候选结果集内计算，界面明确标注口径。
- `citation_velocity`：按论文年龄计算年均引用。
- 高被引、引用表现优秀、引用表现稳定、新近成果、引用信号有限等标签。

JCR、中科院分区和 Web of Science 收录状态没有开放可靠数据时显示“分区待授权核验”。系统没有用引用数猜测 SCI 分区。

### AI 分析稳定性

- 分析接口增加稳定的重试和安全降级。
- 浏览器真实点击“全面分析”，约 52 秒后返回：
  1. 核心研究问题
  2. 创新点和主要贡献
  3. 研究方法和技术路线
  4. 实验设计和结果
  5. 优点和局限性
  6. 与当前研究方向的关联
- 本次真实调用未出现 HTTP 500。

### 知识库与研究路线

- 知识库 API 和页面均恢复正常，现有 13 条记录。
- “Traffic Flow Prediction”专题包含 12 篇论文。
- 研究路线 `LLM-Driven Traffic Flow Prediction Research Framework` 关联 12 个知识点。
- MiMo 文字分析与 SenseNova-U1 研究架构图均已真实生成。
- 架构图为 2752×1536、5,883,689 bytes，并持久化到本地，避免临时签名链接失效。

### UI 与主题

- 明暗模式均使用独立主题变量，不再只是图标切换。
- 浏览器验证：
  - 深色模式：`html.dark` 生效，页面背景为 `rgb(6, 11, 20)`。
  - 浅色模式：`dark` 类移除，页面背景为 `rgb(230, 228, 223)`。
- 搜索框、论文卡片、质量徽章、详情侧栏、知识库和研究路线统一为科研工作台风格。

## 3. 官方数据集状态

### PaSa

- 数据集：`CarlanLark/pasa-dataset`
- RealScholarQuery test：50 条。
- AutoScholarQuery test：1000 条。
- RealScholarQuery gold 平均相关论文数：15.82，范围 1–65。

已下载：

- `outputs/benchmarks/data/pasa-real-scholar-query-test.jsonl`
- `outputs/benchmarks/data/pasa-auto-scholar-query-test.jsonl`

### AstaBench Paper Finder

- 数据集：`allenai/asta-bench`
- validation：66 条，其中 semantic 48、specific 10、metadata 8。
- test：267 条，其中 semantic 194、specific 38、metadata 35。

已下载：

- `outputs/benchmarks/data/asta-paper-finder-validation-2025-05.json`
- `outputs/benchmarks/data/asta-paper-finder-test-2025-05.json`

Asta semantic 类型需要官方 LLM relevance judge，不能用简单集合交集冒充官方分数；specific/metadata 类型可以用 CorpusId 做确定性评测。

## 4. PaSa 50 条全量基线

评测源：Crossref  
数据集：PaSa RealScholarQuery test  
样例数：50/50

| 指标 | 实测值 |
|---|---:|
| Precision | 0.003542 |
| Recall | 0.020253 |
| F1 | 0.006030 |
| Recall@20 | 0.008861 |
| Recall@50 | 0.017722 |
| Recall@100 | 0.020253 |
| 平均 API 调用 | 1.02 |
| 平均端到端延时 | 9.226 秒 |
| 检索 LLM Token | 0 |

可复现文件：

- `outputs/benchmarks/predictions/pasa-real-crossref-2026-07-01.json`
- `outputs/benchmarks/pasa-real-crossref-metrics-2026-07-01.json`
- `outputs/benchmarks/pasa-real-crossref-run.log`

### 指标解读

- 这是 Crossref 单源规则检索基线，不代表当前多源产品的最终上限。
- F1 较低的核心原因是 PaSa 查询通常需要细粒度语义、全文证据和引用网络，而 Crossref 主要提供元数据匹配。
- 该基线的价值是建立了可复现的真实下界。后续优化必须在同一数据和口径上证明增益。
- 竞赛参考系统 SPAR 报告 F1=0.38；当前 Crossref 基线与该水平有显著差距，不能宣称已达到参考系统水平。

## 5. Asta 与 Semantic Scholar 实测状态

- Semantic Scholar Key 已通过精确论文查询验证，能返回正确 CorpusId。
- 已按批准的 1 request/second 限额实施全局节流，并进一步使用约 2.05 秒安全间隔。
- 搜索端点在本轮仍反复返回 429，个别请求返回 500。
- Asta smoke query 因搜索端点持续限流返回 0 个候选，因此没有把 F1=0 写成模型能力结论。
- Asta 全集指标当前状态是“外部搜索端点阻塞”，不是“未知且未测试”；请求、限流和失败原因均已实际验证。

下一次稳定窗口应优先执行：

1. Asta specific/metadata validation 的 18 条确定性 CorpusId 评测。
2. PaSa Semantic Scholar 单源 50 条评测。
3. 多源召回 + CorpusId 回填。
4. 相关度排序与“相关度 + 质量”排序消融。

## 6. F1 与论文质量的关系

论文质量分析不能直接等同于 F1。

- Precision = 检出的相关论文数 / 检出的论文总数
- Recall = 检出的相关论文数 / 官方标注的相关论文总数
- F1 = Precision 与 Recall 的调和平均

SCI/JCR/中科院分区、引用量和引用速度衡量影响力或来源质量，不表示论文是否满足具体查询。正确做法是：

1. 使用官方 gold relevant-paper 集计算 Precision、Recall、F1 和 Recall@K。
2. 把质量特征加入排序，做前后消融。
3. 额外报告 Top-K 高质量论文占比、质量均值或 nDCG。
4. 只有 F1/Recall@K 确有提升，才能说明质量特征改善了比赛检索效果。

## 7. 浏览器真实验收

| 场景 | 结果 |
|---|---|
| 搜索复杂查询 | 通过，44 篇结果 |
| 查询规划 | 通过，2 个子查询 |
| API/轮次统计 | 通过，2 次 API / 1 轮 |
| 端到端搜索耗时 | 16.6 秒 |
| 标题/作者/年份/来源 | 通过 |
| 摘要展示 | 通过 |
| 质量分析 badges | 通过 |
| 论文详情 | 通过 |
| 全面分析真实模型调用 | 通过，约 52 秒 |
| 知识库 | 通过，13 条 |
| 研究路线 | 通过，3 条 |
| 路线关联论文 | 通过，12 篇 |
| SenseNova-U1 架构图 | 通过 |
| 明暗主题 | 通过 |

控制台中保留了一批后端曾停止运行时产生的旧 `API Error` 记录；恢复服务后，知识库加载和本轮论文分析均成功。浏览器插件自身的 Statsig 网络超时与产品接口无关。

## 8. 自动化回归

本轮最终回归：

- 后端专项：35/35 通过。
  - 查询规划
  - Semantic Scholar 数据源
  - 官方 benchmark adapter
  - AI 分析 fallback
- 前端 TypeScript 类型检查：通过。
- 前端测试：16/16 通过。
- 前端生产构建：通过。
- Vite 生产包：JS gzip 112.69 kB，CSS gzip 14.00 kB。
- 运行时健康检查：healthy。

后端测试有 3 条 Pydantic V2 弃用警告，不影响本轮功能；建议后续将 class-based `Config` 迁移为 `ConfigDict`。

## 9. Token 与调用成本

可精确核验：

- PaSa 50 条 Crossref 基线：0 LLM Token。
- 搜索页面本次 44 篇结果：规则查询规划，检索阶段不调用文本模型。
- SenseNova-U1 图像接口未返回文本 Token usage。

当前无法精确核验：

- 本次论文“全面分析”的模型响应没有持久化 prompt/completion/total token。
- MiMo 研究路线调用没有把 usage 保存到数据库。
- Codex 会话没有向本地项目暴露精确 token 计数接口。

因此报告不提供猜测数字。后续应在统一 LLM Gateway 中记录 `provider/model/prompt_tokens/completion_tokens/total_tokens/latency/cost`，才能形成比赛要求的成本报表。

## 10. 安全与交付注意

- Hugging Face 和 Semantic Scholar 凭据只保存在 git 忽略的 `backend/.env` 中，没有写入源码、测试报告或 benchmark 输出。
- Hugging Face S3 兼容访问密钥未写入项目。
- 由于凭据曾在聊天中明文发送，建议完成本轮工作后在对应平台轮换全部已暴露凭据。
- 本轮没有伪造业务数据，没有用引用数推断 JCR/中科院分区，也没有把外部 API 限流写成产品已达到的比赛分数。

## 11. 2026-07-02 限流与精确检索专项优化

### 限流治理

- Semantic Scholar 配额由“单进程锁”升级为“跨进程共享配额闸门”，后端、健康检查和 benchmark 不再各自独立抢占同一个 1 RPS 配额。
- 每次真实 HTTP 请求（包括重试）都必须先取得全局时隙，安全间隔为 1.10 秒。
- 429 和暂时性 5xx 均支持指数退避；`Retry-After` 同时支持秒数和 HTTP 日期。
- 相同 Semantic Scholar 搜索、详情和 batch 结果加入 24 小时磁盘缓存；空结果缓存 10 分钟。缓存可跨后端重启和 benchmark 进程复用。
- 连续两次 429/5xx 后，生产检索器对该来源断路 60 秒，避免持续轰击失效服务。
- benchmark 中同样加入来源断路；本轮 OpenAlex 首次 503 后，后续两条样例不再各等待 10 秒。

官方依据：

- Semantic Scholar API Key 初始配额为全端点合计 1 RPS：
  https://www.semanticscholar.org/product/api/tutorial
- API Key 使用 `x-api-key` 请求头；论文 batch 接口支持一次查询多个标识：
  https://api.semanticscholar.org/api-docs/

### CorpusId 回填与合法降级

- 多源召回结果优先使用 Semantic Scholar 官方 `/paper/batch` 一次性回填 DOI/arXiv 论文的 CorpusId。
- batch 被限流时，精确查询只对排名第 1 的 DOI/arXiv 候选使用一次 exact paper 请求，不逐篇调用。
- 所有成功回填结果进入跨进程缓存。
- OpenAlex 或 Semantic Scholar 暂时失败时，Crossref/arXiv 结果仍正常返回。

### 精确论文查询优化

- 识别 `BART by Lewis et al.` 这类“简称 + 作者”查询为 `exact_lookup`。
- 识别 `the MS^2 DeYong2021 paper` 这类“论文简称 + BibTeX key”查询。
- BibTeX key 不再作为严格 AND 检索词；`MS^2` 会规范化为 `MS2`。
- 精确查询的标题与作者匹配权重提升，引用量和新近程度不再压过真正的目标论文。
- 精确查询结果限制为 Top-10，减少噪声并提高 Precision。

### Asta 小样本实测

三条官方 Asta specific validation 样例：

| 指标 | 优化前 | 优化后 |
|---|---:|---:|
| Precision | 0.009091 | 0.066667 |
| Recall | 0.333333 | 0.666667 |
| F1 | 0.017699 | 0.121212 |
| Recall@20 | 0.333333 | 0.666667 |
| 平均 API 调用 | 3.333 | 3.667 |
| 平均延时 | 16.50s | 13.25s |
| LLM Token | 0 | 0 |

单条 `BART by Lewis et al.`：

- 正确论文排名：第 1。
- 正确 CorpusId：命中。
- Precision：0.10。
- Recall：1.00。
- F1：0.181818。
- 即使 batch 返回 429，Top-1 exact fallback 仍成功完成 CorpusId 对齐。

`MS^2 DeYong2021` 的后续排序专项验证中，目标论文已由第 4 提升至第 1；由于 Semantic Scholar 当时处于持续 429 窗口，本轮未把未完成 CorpusId 回填的结果计入新的三条正式分数。

### 产品 API 端到端复测

查询：`BART by Lewis et al.`  
来源：Semantic Scholar + arXiv + Crossref

- 状态：completed。
- 返回：10 篇。
- Top-1：`BART: Denoising Sequence-to-Sequence Pre-training for Natural Language Generation, Translation, and Comprehension`。
- Top-1 CorpusId：正确命中官方 gold。
- Top-1 相关度：0.9852。
- 数据源失败：0。
- 首次请求：40.18 秒。
- 相同查询第二次请求：16.92 秒，缓存后延时降低约 57.9%。
- 第二次请求仍保持正确论文 Top-1 和正确 CorpusId。

可复现文件：

- `outputs/benchmarks/predictions/asta-hybrid-3case-2026-07-02.json`
- `outputs/benchmarks/predictions/asta-hybrid-3case-v2-2026-07-02.json`
- `outputs/benchmarks/predictions/asta-hybrid-smoke-v6-2026-07-02.json`

### 回归结果

- 限流、缓存、查询规划、排序、benchmark adapter 和分析 fallback 专项：55/55 通过。
- Python 编译检查：通过。
- 后端已使用新代码重启，健康状态：`healthy`。
- 前端继续运行，`/search` 返回 HTTP 200。

## 12. 2026-07-02 Asta 官方验证集 18 条专项复测

本轮使用 AstaBench 官方验证集中的 18 条确定性 Paper Finder 查询进行前后对照，包括 10 条 specific 查询与 8 条 metadata 查询。该结果是当前可复现的专项验证子集，不等同于完整 66 条评测，也不能直接与 SPAR 在 AutoScholar 上公布的 F1=0.38 横向比较。

| 指标 | 优化前 | 优化后 |
| --- | ---: | ---: |
| Precision | 0.004762 | 0.175725 |
| Recall | 0.006689 | 0.324415 |
| F1 | 0.005563 | 0.227967 |
| Recall@20 | 0.006689 | 0.117057 |
| Recall@50 | 0.006689 | 0.160535 |
| Recall@100 | 0.006689 | 0.230769 |
| 平均 API 调用数 | 3.889 | 5.500 |
| 平均端到端延时 | 10.685 秒 | 10.714 秒 |
| LLM Token | 0 | 0 |

F1 相比基线约提升 40.98 倍，平均延时仅增加约 0.27%。提升主要来自精确标题/作者/BibTeX 别名识别、Semantic Scholar CorpusId 批量补全、作者论文与引文网络检索，以及部分 metadata 查询的结构化执行。

代表性结果：

- `metadata_4`：3/3 命中，单例 F1=1.000。
- `metadata_14`：6/6 命中，单例 F1=1.000。
- `metadata_15`：6/6 命中，10 条预测，单例 F1=0.750。
- `metadata_25`：66/172 命中，259 条预测，单例 F1=0.306265。
- `metadata_26`：10/10 命中，104 条预测，单例 F1=0.181818。

仍需继续优化的部分：

- 5 条 specific 查询仍未命中，主要涉及标题别名与稀有论文覆盖。
- `metadata_31`、`metadata_33` 尚未命中。
- `metadata_42` 受 Semantic Scholar “最近 10000 条引用”窗口与数据随时间漂移影响，2022/2023 年目标论文在 2026 年实时接口中已难以完整回溯。
- 当前指标应表述为“18 条官方验证子集结果”，不能包装为完整赛事总分。

可复现结果文件：

- 基线：`outputs/benchmarks/predictions/asta-hybrid-validation18-baseline-2026-07-02.json`
- 优化后：`outputs/benchmarks/predictions/asta-hybrid-validation18-final-2026-07-02.json`

最新定向回归测试为 61/61 通过；Python 编译检查通过。模型配置方面，小米 MiMo 使用 OpenAI 兼容接口变量接入，当前默认模型为 `mimo-v2.5-pro`；SenseNova 用于研究路线中的框架图生成。报告与仓库中均不记录任何 API Key 明文。

## 13. 2026-07-02 Token 计量与 Semantic Scholar 主链路复测

本轮修复了此前 benchmark 将 Token 固定写为 0 的问题。LLM 网关现在累计供应商返回的 `prompt_tokens`、`completion_tokens`、`total_tokens` 和请求次数；搜索记录与 benchmark 输出均使用真实 usage。精确论文查询仍走确定性规则，因此其 Token 为 0 是真实的成本优化，不再代表“未实现统计”。

实际 MiMo 连通性请求记录：

- 请求次数：1
- Prompt Token：261
- Completion Token：20
- Total Token：281

复杂查询规划的异常回退压力测试也成功记录了 3 次请求、11202 Total Token。该结果暴露出推理模型在未产生可见 JSON 时的成本风险，因此已将查询规划输出上限从 2048 下调为 1024，并继续保留规则回退。

考虑到 OpenAlex 持续返回 503、arXiv 出现读取超时，本轮使用已获 API Key 的 Semantic Scholar 作为稳定主链路，对同一 18 条官方验证子集正式重跑：

| 指标 | 上一版 Hybrid | Semantic Scholar v2 |
| --- | ---: | ---: |
| Precision | 0.175725 | 0.259434 |
| Recall | 0.324415 | 0.367893 |
| F1 | 0.227967 | 0.304288 |
| Recall@20 | 0.117057 | 0.160535 |
| Recall@50 | 0.160535 | 0.204013 |
| Recall@100 | 0.230769 | 0.274247 |
| 平均 API 调用数 | 5.500 | 3.667 |
| 平均端到端延时 | 10.714 秒 | 5.904 秒 |

与上一正式版本相比，F1 提升约 33.5%，平均延时下降约 44.9%，平均 API 调用数下降约 33.3%。新增有效结果包括：

- `specific_15` AlphaGeometry：0/1 提升到 1/1。
- `specific_20` CNN：0/2 提升到 1/2。
- `specific_24` GPT-2：0/1 提升到 1/1。
- `metadata_31`：0/16 提升到 4/16，5 条返回中 4 条正确。
- `metadata_42`：0/70 提升到 7/70，10 条返回中 7 条正确。

当前 `F1=0.304288` 已明显提升，但尚未超过 SPAR 公布的 0.38 参考值，而且两者并非同一评测设置。后续重点应是提升 citation graph 的覆盖率，同时控制 `metadata_25`、`metadata_26` 的额外候选数量，而不是无约束增加模型调用。

可复现结果：

- `outputs/benchmarks/predictions/asta-s2-validation18-v2-2026-07-02.json`
- 后端定向回归：95/95 通过。
- 前端测试：16/16 通过。
- 前端生产构建：通过。
