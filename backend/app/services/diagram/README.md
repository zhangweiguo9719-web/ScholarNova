# 科研框架图提示词引擎（Diagram Prompt Engine）

ScholarNova 的研究路线图/架构图出图链路，采用 **Nature 期刊配图规范** 约束，
按 **双层约束** 设计：规范约束规划层（LLM），纯描述进渲染层（生图模型）。

## 设计动机

早期硬编码模板（`knowledge.py` 内联字符串）出的图信息密度低、占位感强。
改为「GLM 生成结构化提示词 → 商汤出图」后质量显著提升，但发现一个新问题：
**把 COLOR RULES / FORBIDDEN 等元指令直接塞给生图模型，会被渲染成画面乱码**
（实测出现 "GROUND Verified Knowledg"、"LAYOLE"、"BED increase arrowss"）。

因此拆成两层：

```
知识库条目 + 文字分析
        │
        ▼
[规划层] LLM（GLM）遵守 Nature 规范，输出结构化 JSON 规划
        │   { layout, modules:[{name,desc}], flow }
        ▼
[渲染层] build_render_prompt 组装纯描述提示词（无元指令）
        │
        ▼
     商汤 sensenova-u1-fast 出图
```

- **规划层**：`planner.py` 调 LLM 生成结构化规划；失败时回退到启发式布局 + 兜底模块，保证链路永不中断。
- **渲染层**：`prompt_engine.py` 的 `build_render_prompt` 只含可渲染内容（标题 + 模块标签 + 布局 + 视觉风格 + 一句话配色），**绝不包含** "COLOR RULES"/"FORBIDDEN"/"MUST FOLLOW" 等元指令，也不把知识库原文塞进画面（避免被当正文渲染）。

## 文件说明

| 文件 | 职责 |
|---|---|
| `app/services/diagram/prompt_engine.py` | 纯字符串组装：布局模式、配色、视觉风格、渲染提示词、规划层提示词模板 |
| `app/services/diagram/planner.py` | LLM 规划 + 降级兜底，对外暴露 `build_prompt_for_route` |
| `app/services/diagram/route_planner.py` | 科研阶段路线规划：LLM 生成 5 阶段路线（选题→调研→方法→实验→论文），输出结构化阶段 + roadmap 渲染提示词 |
| `app/api/v1/knowledge.py` | 研究路线出图端点，Step 2 架构图 + Step 3 科研阶段路线图 |
| `docs/diagram-skill/nature-figure-prompts/` | 上游参考资产（Aryous/nature-figure-prompts, MIT），论文分析/布局/配色/词汇规范 |
| `docs/diagram-skill/research-planning-architect/` | 上游参考资产（clear0215/research-planning-architect），分层实验矩阵/新颖性诊断/决策门思想 |

## 布局模式

| key | 名称 | 适用 |
|---|---|---|
| `pipeline` | 水平流水线 | 端到端方法 / 系统架构 / 数据流 |
| `hierarchy` | 分层堆叠 | 算法栈 / 框架分层 |
| `radial` | 放射中心 | 核心方法与多数据/多任务交互 |
| `comparison` | 并排对比 | 消融实验 / 基线对照 |
| `roadmap` | 科研阶段路线图 | 选题→调研→方法→实验→论文的 5 阶段横向路线 |

布局由 LLM 规划选择，LLM 失败时按标题/分析文本关键词启发式选择。

## 配色（期刊投稿风格）

- 主模块：藏青 `#1F3A5F`
- 方法强调：青绿 `#2A9D8F`
- 关键高亮：克制金 `#C9A227`
- 背景：米白 `#FAFAFA`

## 质量检查

- 模块标签为短英文（2-3 词），降低生图文字乱码率
- 不注入编造的数值/指标
- 渲染提示词不含元指令（自动化测试断言）
- 知识库条目为内容 ground truth
